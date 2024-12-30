import asyncio
from functools import lru_cache
from typing import Union, Optional
import aiohttp
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Message, Channel, User, UserStatusOnline, UserStatusOffline, UserStatusRecently
from telethon.errors.rpcerrorlist import YouBlockedUserError
from telethon import Button
from .. import loader, utils

@lru_cache(maxsize=100)
async def get_creation_date(user_id: int) -> str:
    """Получение даты регистрации аккаунта с кэшированием"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                "https://restore-access.indream.app/regdate",
                json={"telegramId": user_id},
                headers={
                    "accept": "*/*",
                    "content-type": "application/x-www-form-urlencoded",
                    "user-agent": "Nicegram/92 CFNetwork/1390 Darwin/22.0.0",
                    "x-api-key": "e758fb28-79be-4d1c-af6b-066633ded128",
                    "accept-language": "en-US,en;q=0.9",
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {}).get("date", "Ошибка получения данных")
        except Exception:
            pass
    return "Ошибка получения данных"

@loader.tds
class UserInfoMod(loader.Module):
    """Получение информации о пользователе или канале Telegram"""
    
    strings = {
        "name": "UserInfo",
        "loading": "🕐 <b>Обработка данных...</b>",
        "not_found": "❗ Не удалось найти пользователя или канал",
        "unblock_bot": "❗ Разблокируйте funstat для получения информации",
        "error_fetching": "⚠️ Ошибка при получении данных: {}"
    }

    async def get_entity_safe(self, entity_id: Union[str, int]) -> Optional[Union[User, Channel]]:
        """Безопасное получение сущности"""
        try:
            return await self._client.get_entity(
                int(entity_id) if str(entity_id).isdigit() else entity_id
            )
        except Exception:
            return None

    async def format_user_info(self, user_ent: User, user: GetFullUserRequest) -> str:
        """Форматирование информации о пользователе"""
        registration_date = await get_creation_date(user_ent.id)
        funstat_info = await self.get_funstat_info(user_ent.id)
        
        # Основная информация
        name_parts = []
        if user_ent.first_name:
            name_parts.append(user_ent.first_name)
        if user_ent.last_name:
            name_parts.append(user_ent.last_name)
        full_name = " ".join(name_parts) if name_parts else "🚫"
        
        # Статусы и флаги
        status_flags = []
        if user_ent.bot:
            status_flags.append("🤖 Бот")
        if user_ent.verified:
            status_flags.append("✓ Верифицирован")
        if user_ent.premium:
            status_flags.append("⭐️ Premium")
        if getattr(user_ent, "deleted", False):
            status_flags.append("🗑 Удалён")
        
        status_line = " | ".join(status_flags)
        
        info = (
            f"👤 <b>{full_name}</b>\n"
            f"{f'⚜️ {status_line}\n\n' if status_flags else '\n'}"
            f"├ ID: <code>{user_ent.id}</code>\n"
            f"├ Username: @{user_ent.username or '🚫'}\n"
            f"├ Регистрация: <code>{registration_date}</code>\n"
            f"├ Общие чаты: {user.full_user.common_chats_count}\n"
        )
        
        # Добавляем информацию о последнем онлайне
        if hasattr(user_ent, "status"):
            if isinstance(user_ent.status, UserStatusOnline):
                info += "└ Статус: 🟢 В сети\n\n"
            elif isinstance(user_ent.status, UserStatusOffline):
                last_seen = user_ent.status.was_online.strftime("%d.%m.%Y %H:%M")
                info += f"└ Статус: ⚫️ Был(а) {last_seen}\n\n"
            elif isinstance(user_ent.status, UserStatusRecently):
                info += "└ Статус: 🔵 Недавно\n\n"
            else:
                info += "└ Статус: ⚫️ Давно\n\n"
        else:
            info += "└ Статус: ❔ Неизвестно\n\n"
        
        # Добавляем описание
        if user.full_user.about:
            info += f"📝 <b>О пользователе:</b>\n{user.full_user.about}\n\n"
        
        # Добавляем ссылки
        links = []
        if user_ent.username:
            links.append(f"└ <a href='tg://user?id={user_ent.id}'>Telegram</a>")
        if links:
            info += f"🔗 <b>Ссылки:</b>\n" + "\n".join(links) + "\n\n"
        
        # Добавляем статистику
        if funstat_info and not any(err in funstat_info.lower() for err in ["ошибка", "error", "⚠️"]):
            info += f"📊 <b>Статистика:</b>\n{funstat_info}"
            
        return info

    async def format_channel_info(self, channel_ent: Channel, channel: GetFullChannelRequest) -> str:
        """Форматирование информации о канале"""
        creation_date = await get_creation_date(channel_ent.id)
        
        # Статусы и флаги канала
        status_flags = []
        if channel_ent.verified:
            status_flags.append("✓ Верифицирован")
        if channel_ent.scam:
            status_flags.append("⚠️ Скам")
        
        status_line = " | ".join(status_flags)
        
        info = (
            f"📣 <b>{channel_ent.title}</b>\n"
            f"{f'⚜️ {status_line}\n\n' if status_flags else '\n'}"
            f"├ ID: <code>{channel_ent.id}</code>\n"
            f"├ Username: @{channel_ent.username or '🚫'}\n"
            f"├ Создан: <code>{creation_date}</code>\n"
            f"├ Подписчиков: {channel.full_chat.participants_count:,}\n"
        )
        
        # Добавляем информацию о медленном режиме
        if channel.full_chat.slowmode_seconds:
            info += f"├ Медленный режим: {channel.full_chat.slowmode_seconds} сек.\n"
        
        info += "└ Тип: " + ("Супергруппа" if channel_ent.megagroup else "Канал") + "\n"
        
        # Добавляем описание
        if channel.full_chat.about:
            info += f"\n📝 <b>Описание:</b>\n{channel.full_chat.about}\n"
        
        # Добавляем ссылки
        if channel_ent.username:
            info += f"\n🔗 <b>Ссылки:</b>\n└ https://t.me/{channel_ent.username}"
            
        return info

    async def send_info_message(self, message: Message, entity: Union[User, Channel], info_text: str):
        """Отправка сообщения с информацией и фото"""
        photo = await self._client.download_profile_photo(entity.id)
        
        if photo:
            await self._client.send_file(
                message.chat_id,
                file=photo,
                caption=info_text,
                buttons=[[Button.inline("🔄 Обновить", data=f"refresh:{entity.id}")]]
            )
        else:
            await self._client.send_message(
                message.chat_id,
                info_text,
                buttons=[[Button.inline("🔄 Обновить", data=f"refresh:{entity.id}")]]
            )
        
        await message.delete()

    async def get_funstat_info(self, user_id: int, max_attempts: int = 2) -> str:
        """Получение информации из funstat"""
        chat = "@Suusbdj_bot"
        
        try:
            await self._client.send_message(chat, str(user_id))
            await asyncio.sleep(3)
            
            async for msg in self._client.iter_messages(chat, limit=5):
                if str(user_id) in msg.text:
                    return "\n".join(
                        line for line in msg.text.split("\n")
                        if "ID:" not in line and "Это" not in line
                    )
                    
        except YouBlockedUserError:
            return self.strings["unblock_bot"]
        except Exception as e:
            return self.strings["error_fetching"].format(str(e))
            
        return "⚠️ Нет ответа от funstat"

    async def userinfocmd(self, message: Message):
        """Получить информацию о пользователе или канале: .userinfo <@юзернейм/ID> или ответ на сообщение"""
        await utils.answer(message, self.strings["loading"])
        
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        
        entity = await self.get_entity_safe(
            args or (reply.sender_id if reply else None)
        )
        
        if not entity:
            await utils.answer(message, self.strings["not_found"])
            return
            
        try:
            if isinstance(entity, Channel):
                channel = await self._client(GetFullChannelRequest(entity))
                info_text = await self.format_channel_info(entity, channel)
            else:
                user = await self._client(GetFullUserRequest(entity.id))
                info_text = await self.format_user_info(entity, user)
                
            await self.send_info_message(message, entity, info_text)
            
        except Exception as e:
            await utils.answer(message, self.strings["error_fetching"].format(str(e)))

    async def refresh_callback_handler(self, call):
        """Обработчик нажатия кнопки обновления"""
        try:
            # Получаем ID пользователя/канала из callback data
            entity_id = int(call.data.decode().split(":")[1])
            
            # Получаем сущность
            entity = await self.get_entity_safe(entity_id)
            if not entity:
                await call.answer("❌ Не удалось получить информацию", show_alert=True)
                return
            
            # Получаем обновленную информацию
            if isinstance(entity, Channel):
                channel = await self._client(GetFullChannelRequest(entity))
                info_text = await self.format_channel_info(entity, channel)
            else:
                user = await self._client(GetFullUserRequest(entity.id))
                info_text = await self.format_user_info(entity, user)
            
            # Получаем новое фото профиля
            photo = await self._client.download_profile_photo(entity.id)
            
            # Обновляем сообщение
            if photo:
                await call.edit(
                    file=photo,
                    text=info_text,
                    buttons=[[Button.inline("🔄 Обновить", data=f"refresh:{entity.id}")]]
                )
            else:
                await call.edit(
                    text=info_text,
                    buttons=[[Button.inline("🔄 Обновить", data=f"refresh:{entity.id}")]]
                )
            
            await call.answer("✅ Информация обновлена!")
            
        except Exception as e:
            await call.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

    async def callback_handler(self, call):
        """Маршрутизация callback-запросов"""
        if call.data.decode().startswith("refresh:"):
            await self.refresh_callback_handler(call)