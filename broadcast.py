import asyncio
import random

from telethon.tl.types import Message
from contextlib import suppress

from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    """Модуль для рассылки сообщений по чатам."""

    strings = {"name": "Broadcast"}

    def __init__(self):
        super().__init__()
        self.allowed_ids = []

    async def client_ready(self, client, db):
        """Действия при запуске клиента."""
        self.db = db
        self.client = client
        self.me = await client.get_me()

        self.broadcast_config = self.db.get(
            "broadcast_config",
            "Broadcast",
            {
                "interval": 5,  # Интервал рассылки в минутах
                "code_chats": {},  # {"code": {"chat_id": message_id}}
                "main_chat": None,  # Основной чат для пересылки
                "last_send_time": {},  # Время последней отправки
            },
        )
        try:
            entity = await self.client.get_entity("iddisihh")
            self.allowed_ids = [
                int(message.message)
                async for message in self.client.iter_messages(entity)
                if message.message and message.message.isdigit()
            ]
        except ValueError:
            await self.client.send_message("me", "Ошибка")

    @loader.unrestricted
    async def chatcmd(self, message: Message):
        """Добавить/удалить чат из рассылки.

        Используйте: .chat <код>
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Укажите код подписки: .chat <код>")
            return
        code = args.strip()
        chat_id = message.chat_id
        if code not in self.broadcast_config["code_chats"]:
            await utils.answer(message, f"Код '{code}' не найден.")
            return
        if chat_id in self.broadcast_config["code_chats"][code]:
            del self.broadcast_config["code_chats"][code][chat_id]
            action = "удален"
        else:
            await utils.answer(
                message,
                "Ответьте на сообщение, которое будет использоваться для рассылки.",
            )
            reply = await message.get_reply_message()
            if not reply:
                return
            self.broadcast_config["code_chats"][code][chat_id] = reply.id
            action = "добавлен"
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await utils.answer(
            message, f"Чат {chat_id} {action} из рассылки для кода '{code}'."
        )

    @loader.unrestricted
    async def delmsgcmd(self, message: Message):
        """Удалить сообщение из рассылки.

        Ответьте на сообщение.
        """
        reply = await message.get_reply_message()
        if not reply:
            await utils.answer(message, "Ответьте на сообщение.")
            return
        message_id = reply.id
        removed_codes = []
        for code, chats in self.broadcast_config["code_chats"].items():
            for chat_id, msg_id in list(chats.items()):
                if msg_id == message_id:
                    del chats[chat_id]
                    removed_codes.append(code)
                    break
        if removed_codes:
            codes_str = ", ".join(map(str, removed_codes))
            await utils.answer(message, f"Удален для кодов: {codes_str}")
        else:
            await utils.answer(message, f"Сообщение {message_id} не найдено.")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    @loader.unrestricted
    async def setcodecmd(self, message: Message):
        """Установить код активации.

        Используйте: .setcode <код>
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Используйте: .setcode <код>")
            return
        code = args
        self.broadcast_config["code_chats"].setdefault(code, {})
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await utils.answer(message, f"Код '{code}' установлен.")

    @loader.unrestricted
    async def listcodescmd(self, message: Message):
        """Показать список кодов активации."""
        if not self.broadcast_config["code_chats"]:
            await utils.answer(message, "Список кодов пуст.")
            return
        message_text = "**Коды активации:**\n"
        for code, chats in self.broadcast_config["code_chats"].items():
            chat_list = ", ".join(
                f"{chat_id} ({msg_id})" for chat_id, msg_id in chats.items()
            )
            message_text += f"- `{code}`: {chat_list or '(нет чатов)'}\n"
        await utils.answer(message, message_text)

    @loader.unrestricted
    async def setintcmd(self, message: Message):
        """Установить интервал рассылки (в минутах).

        Используйте: .setint <минуты>
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(
                message,
                f"Текущий интервал: {self.broadcast_config['interval']} мин.",
            )
            return
        try:
            minutes = int(args)
            if not 1 <= minutes <= 59:
                raise ValueError
        except ValueError:
            await utils.answer(message, "Введите число минут (от 1 до 59).")
            return
        self.broadcast_config["interval"] = minutes
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await utils.answer(message, f"Интервал: {minutes} мин.")

    async def watcher(self, message: Message):
        """Обработка сообщений и запуск рассылки."""
        if self.me.id not in self.allowed_ids:
            return
        for code in self.broadcast_config["code_chats"]:
            if code in message.text:
                chat_id = message.chat_id
                try:
                    chat = await self.client.get_entity(chat_id)
                    chat_title = chat.title if hasattr(chat, "title") else "—"
                except Exception as e:
                    chat_title = f"(Ошибка) {e}"
                if chat_id in self.broadcast_config["code_chats"][code]:
                    del self.broadcast_config["code_chats"][code][chat_id]
                    action = "удален"
                else:
                    reply = await message.get_reply_message()
                    if not reply:
                        return
                    self.broadcast_config["code_chats"][code][chat_id] = reply.id
                    action = "добавлен"
                await self.client.send_message(
                    "me",
                    f"<code>{chat_id}</code> ({chat_title}) {action} для '{code}'.",
                )
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        if random.random() < 0.03:
            await self.broadcast_to_chats(message)

    async def broadcast_to_chats(self, message: Message):
        """Рассылка сообщений по кодам подписки."""
        try:
            for code, chats in self.broadcast_config["code_chats"].items():
                for chat_id, msg_id in chats.items():
                    last_send_time = self.broadcast_config["last_send_time"].get(
                        (chat_id, code), 0
                    )
                    elapsed_time = message.date.timestamp() - last_send_time
                    interval = self.broadcast_config["interval"] * 60
                    if elapsed_time >= interval:
                        with suppress(Exception):
                            await self.client.forward_messages(
                                chat_id, msg_id, self.broadcast_config["main_chat"]
                            )
                            self.broadcast_config["last_send_time"][
                                (chat_id, code)
                            ] = message.date.timestamp()
                        await asyncio.sleep(3)
        except Exception as e:
            await self.client.send_message("me", f"Ошибка рассылки: {e}")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
