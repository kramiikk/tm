import requests
import asyncio
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Message, Channel
from telethon.errors.rpcerrorlist import YouBlockedUserError
from telethon import Button
from .. import loader, utils

def get_creation_date(user_id: int) -> str:
    url = "https://restore-access.indream.app/regdate"
    headers = {
        "accept": "*/*",
        "content-type": "application/x-www-form-urlencoded",
        "user-agent": "Nicegram/92 CFNetwork/1390 Darwin/22.0.0",
        "x-api-key": "e758fb28-79be-4d1c-af6b-066633ded128",
        "accept-language": "en-US,en;q=0.9",
    }
    data = {"telegramId": user_id}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200 and "data" in response.json():
        return response.json()["data"]["date"]
    else:
        return "Ошибка получения данных"

@loader.tds
class UserInfoMod(loader.Module):
    """Получение информации о пользователе или канале Telegram, включая дату регистрации и данные из @funstat"""

    strings = {
        "name": "UserInfo",
        "loading": "🕐 <b>Обработка данных...</b>",
        "not_chat": "🚫 <b>Это не чат!</b>",
        "unblock_bot": "❗ Разблокируйте @funstat для получения дополнительной информации.",
        "timeout": "⚠️ Время ожидания ответа от @funstat истекло.",
        "no_posts": "🚫 Не удалось получить последние посты с канала.",
    }

    async def userinfocmd(self, message: Message):
        """Получить информацию о пользователе или канале. Использование: .userinfo <@юзернейм/ID> или ответ на сообщение"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        # Редактирование сообщения с уведомлением о загрузке данных
        await utils.answer(message, self.strings("loading"))

        # Получение ID пользователя или канала из аргументов или ответа на сообщение
        try:
            entity = (
                (await self._client.get_entity(args if not args.isdigit() else int(args)))
                if args
                else await self._client.get_entity(reply.sender_id)
            )
        except Exception:
            await utils.answer(message, "❗ Не удалось найти пользователя или канал. Проверьте правильность ID или юзернейма.")
            return

        # Проверка, является ли объект пользователем или каналом
        if isinstance(entity, Channel):
            await self.process_channel_info(entity, message)
        else:
            await self.process_user_info(entity, message)

    async def process_user_info(self, user_ent, message):
        """Обработка информации о пользователе"""
        user = await self._client(GetFullUserRequest(user_ent.id))
        registration_date = get_creation_date(user_ent.id)
        funstat_info = await self.get_funstat_info(user_ent.id)

        user_info = (
            "<b>👤 Информация о пользователе:</b>\n\n"
            f"<b>Имя:</b> <code>{user_ent.first_name or '🚫'}</code>\n"
            f"<b>Фамилия:</b> <code>{user_ent.last_name or '🚫'}</code>\n"
            f"<b>Юзернейм:</b> @{user_ent.username or '🚫'}\n"
            f"<b>Описание:</b>\n{user.full_user.about or '🚫'}\n\n"
            f"<b>Дата регистрации:</b> <code>{registration_date}</code>\n"
            f"<b>Общие чаты:</b> <code>{user.full_user.common_chats_count}</code>\n"
            f"<b>ID:</b> <code>{user_ent.id}</code>\n"
        )

        if user_ent.username:
            user_info += f'<b><a href="tg://user?id={user_ent.id}">🌐 Вечная ссылка</a></b>\n\n'
        else:
            user_info += "Вечная ссылка отсутствует.\n\n"

        user_info += f"<b>📊 Информация из Фанстата:</b>\n{funstat_info}"

        # Получение аватарки пользователя
        photo = await self._client.download_profile_photo(user_ent.id)

        if photo:
            # Отправка информации с аватаркой в одном сообщении
            await self._client.send_file(
                message.chat_id,
                file=photo,
                caption=user_info,
                buttons=[
                    [Button.inline("🔄 Обновить данные", data=f"refresh:{user_ent.id}")]
                ]
            )
        else:
            await self._client.send_message(message.chat_id, user_info)

        await message.delete()  # Удаляем сообщение с командой пользователя

    async def process_channel_info(self, channel_ent, message):
        """Обработка информации о канале"""
        channel = await self._client(GetFullChannelRequest(channel_ent))
        description = channel.full_chat.about or "🚫"
        creation_date = get_creation_date(channel_ent.id)
        subscriber_count = channel.full_chat.participants_count

        channel_info = (
            "<b>📣 Информация о канале:</b>\n\n"
            f"<b>Название:</b> <code>{channel_ent.title}</code>\n"
            f"<b>Юзернейм:</b> @{channel_ent.username or '🚫'}\n"
            f"<b>Описание:</b>\n{description}\n\n"
            f"<b>Дата создания:</b> <code>{creation_date}</code>\n"
            f"<b>Количество подписчиков:</b> <code>{subscriber_count}</code>\n"
            f"<b>ID:</b> <code>{channel_ent.id}</code>\n"
        )

        if channel_ent.username:
            channel_info += f'<b><a href="https://t.me/{channel_ent.username}">Ссылка на канал</a></b>\n\n'
        else:
            channel_info += "Ссылка на канал отсутствует.\n\n"

        # Получение аватарки канала
        photo = await self._client.download_profile_photo(channel_ent.id)

        if photo:
            # Отправка информации о канале с аватаркой в одном сообщении
            await self._client.send_file(
                message.chat_id,
                file=photo,
                caption=channel_info,
                buttons=[
                    [Button.inline("🔄 Обновить данные", data=f"refresh:{channel_ent.id}")]
                ]
            )
        else:
            await self._client.send_message(message.chat_id, channel_info)

        await message.delete()  # Удаляем сообщение с командой пользователя

    async def get_funstat_info(self, user_id: int) -> str:
        """Отправка запроса в @funstat и получение информации"""
        chat = "@Suusbdj_bot"
        attempts = 3  # Количество попыток отправить сообщение
        for attempt in range(attempts):
            try:
                # Отправка сообщения
                await self._client.send_message(chat, str(user_id))

                # Увеличено время ожидания до 5 секунд, чтобы дать время боту ответить
                await asyncio.sleep(5)

                # Получение последних 5 сообщений из канала
                messages = await self._client.get_messages(chat, limit=5)

                # Поиск нужного сообщения от бота
                for message in messages:
                    if f"👤 {user_id}" in message.text or str(user_id) in message.text:
                        # Удаляем строку с ID и именем пользователя
                        lines = message.text.split("\n")
                        filtered_lines = [
                            line for line in lines if "ID:" not in line and "Это" not in line
                        ]
                        return "\n".join(filtered_lines)

                # Если не нашли ответ, попробуем еще раз
                await asyncio.sleep(1)  # Подождем перед повторной попыткой

            except YouBlockedUserError:
                return self.strings("unblock_bot")
            except Exception as e:
                return f"Ошибка при получении данных: {e}"

        return "⚠️ Не удалось получить окончательный ответ от @funstat_obot."