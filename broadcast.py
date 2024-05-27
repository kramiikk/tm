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
                "code_chats": {},  # {"code": [chat_id1, chat_id2, ...]}
                "main_chat": None,  # Основной чат для пересылки
                "last_send_time": {},  # {"code": timestamp}
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
            await self.client.send_message("me", "Ошибка получения allowed_ids")

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
            self.broadcast_config["code_chats"][
                code
            ] = []  # Создаем список для кода, если его не было
        if chat_id in self.broadcast_config["code_chats"][code]:
            self.broadcast_config["code_chats"][code].remove(chat_id)
            action = "удален"
        else:
            self.broadcast_config["code_chats"][code].append(chat_id)
            action = "добавлен"
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await utils.answer(
            message, f"Чат {chat_id} {action} из рассылки для кода '{code}'."
        )

    @loader.unrestricted
    async def delcodecmd(self, message: Message):
        """Удалить код.

        Используйте: .delcode <код>
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Используйте: .delcode <код>")
            return
        code = args.strip()
        if code in self.broadcast_config["code_chats"]:
            del self.broadcast_config["code_chats"][code]
            self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
            await utils.answer(message, f"Код '{code}' удален.")
        else:
            await utils.answer(message, f"Код '{code}' не найден.")

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
        if code not in self.broadcast_config["code_chats"]:
            self.broadcast_config["code_chats"][code] = []
            self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
            await utils.answer(message, f"Код '{code}' установлен.")
        else:
            await utils.answer(message, f"Код '{code}' уже существует.")

    @loader.unrestricted
    async def listcodescmd(self, message: Message):
        """Показать список кодов активации."""
        if not self.broadcast_config["code_chats"]:
            await utils.answer(message, "Список кодов пуст.")
            return
        message_text = "**Коды активации:**\n"
        for code, chats in self.broadcast_config["code_chats"].items():
            chat_list = ", ".join(str(chat_id) for chat_id in chats)
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
        for code, chat_ids in self.broadcast_config["code_chats"].items():
            if code in message.text and message.chat_id not in chat_ids:
                chat_id = message.chat_id
                try:
                    chat = await self.client.get_entity(chat_id)
                    chat_title = chat.title if hasattr(chat, "title") else "—"
                except Exception as e:
                    chat_title = f"(Ошибка) {e}"
                self.broadcast_config["code_chats"][code].append(chat_id)
                self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
                await self.client.send_message(
                    "me",
                    f"<code>{chat_id}</code> ({chat_title}) добавлен для '{code}'.",
                )
        if random.random() < 0.03:
            await self.broadcast_to_chats(message)

    async def broadcast_to_chats(self, message: Message):
        """Рассылка сообщений по кодам подписки."""
        current_time = message.date.timestamp()
        for code, chat_ids in self.broadcast_config["code_chats"].items():
            last_send_time = self.broadcast_config["last_send_time"].get(code, 0)
            if current_time - last_send_time >= self.broadcast_config["interval"] * 60:
                for chat_id in chat_ids:
                    with suppress(Exception):
                        await self.client.forward_messages(
                            chat_id, message.id, self.broadcast_config["main_chat"]
                        )
                        await asyncio.sleep(3)
                self.broadcast_config["last_send_time"][code] = current_time
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
