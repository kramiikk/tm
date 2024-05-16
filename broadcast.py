import asyncio
import random
from typing import Optional
from telethon.tl.types import Message
from contextlib import suppress
from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    """Модуль для рассылки сообщений в чаты"""

    strings = {"name": "Broadcast"}

    async def client_ready(self, client, db):
        """Инициализирует модуль при запуске клиента.

        Args:
            client: Клиент Telethon.
            db: База данных для хранения конфигурации модуля.
        """
        self.db = db
        self.client = client
        self.me = await client.get_me()

        self.broadcast_config = db.get(
            "broadcast_config",
            "Broadcast",
            {
                "interval": 5,  # Интервал рассылки в минутах
                "messages": {},  # Сообщения для рассылки по чатам
                "code": "Super Sonic",  # Кодовая фраза для добавления/удаления чата
                "main_chat": None,  # Главный чат, из которого берутся сообщения
                "chats": [],  # Список чатов для рассылки
                "last_send_time": 0,  # Время последней рассылки (unix timestamp)
            },
        )

        try:
            channel_entity = await self.client.get_entity("iddisihh")
            self.allowed_ids = []
            async for message in self.client.iter_messages(channel_entity):
                if message.message and message.message.isdigit():
                    self.allowed_ids.append(int(message.message))
        except ValueError:
            self.allowed_ids = []

    @loader.unrestricted
    async def addchatcmd(self, message: Message):
        """Добавляет чат в список рассылки.

        Используйте: .addchat <chat_id>
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(
                message,
                "Неверное количество аргументов. Используйте: .addchat <chat_id>",
            )
            return
        try:
            chat_id = int(args)
        except ValueError:
            await utils.answer(message, "Неверный формат ID чата")
            return
        if chat_id in self.broadcast_config["chats"]:
            await utils.answer(message, "Чат уже в списке рассылки")
        else:
            self.broadcast_config["chats"].append(chat_id)
            await utils.answer(message, "Чат добавлен в список рассылки")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    @loader.unrestricted
    async def remchatcmd(self, message: Message):
        """Удаляет чат из списка рассылки.

        Используйте: .remchat <chat_id>
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(
                message,
                "Неверное количество аргументов. Используйте: .remchat <chat_id>",
            )
            return
        try:
            chat_id = int(args)
        except ValueError:
            await utils.answer(message, "Неверный формат ID чата")
            return
        if chat_id in self.broadcast_config["chats"]:
            self.broadcast_config["chats"].remove(chat_id)
            await utils.answer(message, "Чат удален из списка рассылки")
        else:
            await utils.answer(message, "Чата нет в списке рассылки")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    @loader.unrestricted
    async def listchatscmd(self, message: Message):
        """Выводит список чатов для рассылки.

        Используйте: .listchats
        """
        chat_list = []
        for chat_id in self.broadcast_config["chats"]:
            try:
                chat = await self.client.get_input_entity(chat_id)
                chat_list.append(f"<code>{chat_id}</code> - {chat.title}")
            except Exception:
                chat_list.append(f"<code>{chat_id}</code>")
        await utils.answer(
            message, "\n".join(chat_list) if chat_list else "Список чатов пуст"
        )

    @loader.unrestricted
    async def setmsgcmd(self, message: Message):
        """Устанавливает сообщение для рассылки.

        Используйте: .setmsg [chat_id] (в ответ на сообщение)
        """
        args = utils.get_args_raw(message)
        reply_msg = await message.get_reply_message()
        if not reply_msg:
            await utils.answer(
                message, "Ответьте на сообщение, которое хотите добавить для рассылки."
            )
            return
        message_id = reply_msg.id

        # Устанавливаем главный чат как чат, из которого взято сообщение

        self.broadcast_config["main_chat"] = reply_msg.chat_id

        if args:  # Если указан ID чата
            try:
                chat_id = int(args)
            except ValueError:
                await utils.answer(message, "Неверный формат ID чата")
                return
            self.broadcast_config["messages"].setdefault(chat_id, []).append(message_id)
            await utils.answer(
                message, f"Сообщение добавлено в список для рассылки в чат {chat_id}"
            )
        else:  # Дефолтное сообщение для всех чатов
            self.broadcast_config["message"] = message_id
            await utils.answer(
                message, "Сообщение установлено как дефолтное для рассылки во все чаты."
            )
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    @loader.unrestricted
    async def delmsgcmd(self, message: Message):
        """Удаляет сообщение из списка для рассылки.

        Используйте: .delmsg (в ответ на сообщение)
        """
        reply_msg = await message.get_reply_message()
        if not reply_msg:
            await utils.answer(
                message, "Ответьте на сообщение, которое хотите удалить."
            )
            return
        message_id = reply_msg.id
        removed_chats = []

        # Удаляем сообщение из списков сообщений для всех чатов

        for chat_id, message_ids in self.broadcast_config["messages"].items():
            if message_id in message_ids:
                message_ids.remove(message_id)
                removed_chats.append(chat_id)
        # Удаляем дефолтное сообщение, если оно совпадает с удаляемым

        if self.broadcast_config.get("message") == message_id:
            del self.broadcast_config["message"]
            removed_chats.append("Default")
        if removed_chats:
            removed_chats_str = ", ".join(map(str, removed_chats))
            await utils.answer(
                message,
                f"Сообщение с ID {message_id} удалено из списка: {removed_chats_str}",
            )
        else:
            await utils.answer(
                message, f"Сообщение с ID {message_id} не найдено в списке рассылки"
            )
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    @loader.unrestricted
    async def setintcmd(self, message: Message):
        """Устанавливает интервал рассылки (в минутах).

        Используйте: .setint <minutes>
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(
                message,
                "Неверное количество аргументов. Используйте: .setint <minutes>",
            )
            return
        try:
            minutes = int(args)
        except ValueError:
            await utils.answer(
                message, "Неверный формат аргумента. Введите число минут от 1 до 59."
            )
            return
        if minutes < 1 or minutes > 59:
            await utils.answer(message, "Введите число минут от 1 до 59.")
            return
        self.broadcast_config["interval"] = minutes
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await utils.answer(message, f"Интервал рассылки установлен на {minutes} минут.")

    @loader.unrestricted
    async def setcodecmd(self, message: Message):
        """Устанавливает кодовую фразу для добавления/удаления чата.

        Используйте: .setcode <phrase>
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(
                message,
                "Неверное количество аргументов. Используйте: .setcode <phrase>",
            )
            return
        new_code = args  # Извлекаем новую кодовую фразу
        self.broadcast_config["code"] = new_code
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await utils.answer(
            message, f"Кодовая фраза установлена: <code>{new_code}</code>"
        )

    async def watcher(self, message: Message):
        """Обрабатывает входящие сообщения."""
        if not isinstance(message, Message) or self.me.id not in self.allowed_ids:
            return
        if (
            self.broadcast_config["code"] in message.text
            and message.sender_id == self.me.id
        ):
            await self.handle_code_message(message)
        # Рассылка сообщений в чаты

        await self.broadcast_messages(message)

    async def handle_code_message(self, message: Message):
        """Обрабатывает сообщение с кодовой фразой."""
        if message.chat_id not in self.broadcast_config["chats"]:
            self.broadcast_config["chats"].append(message.chat_id)
            action = "добавлен"
        else:
            self.broadcast_config["chats"].remove(message.chat_id)
            action = "удален"
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await self.client.send_message(
            "me", f"Чат <code>{message.chat_id}</code> {action} в список рассылки"
        )

    async def broadcast_messages(self, message: Message):
        """Рассылает сообщения с заданным интервалом."""
        elapsed_time = (
            message.date.timestamp() - self.broadcast_config["last_send_time"]
        )
        if elapsed_time < self.broadcast_config["interval"] * 60:
            return
        if (
            not self.broadcast_config.get("message")
            or not self.broadcast_config["chats"]
        ):
            return
        try:
            await self.send_messages_to_chats()
        except Exception as e:
            await self.client.send_message("me", f"Ошибка при отправке сообщения: {e}")
        self.broadcast_config["last_send_time"] = message.date.timestamp()
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    async def send_messages_to_chats(self):
        """Отправляет сообщения в чаты из списка рассылки."""
        for chat_id in self.broadcast_config["chats"]:
            msg_id = self.get_message_id(chat_id)
            if msg_id is None:
                continue
            msg = await self.client.get_messages(
                self.broadcast_config["main_chat"], ids=msg_id
            )

            if msg is None:  # Если сообщение не найдено, удаляем его ID из списка
                self.remove_invalid_message_id(chat_id, msg_id)
                continue
            if msg.media:
                await self.client.send_file(chat_id, msg.media, caption=msg.text)
            else:
                await self.client.send_message(chat_id, msg.text)
            await asyncio.sleep(5)

    def get_message_id(self, chat_id: int) -> Optional[int]:
        """Возвращает ID сообщения для рассылки в указанный чат."""
        if chat_id in self.broadcast_config["messages"]:
            return random.choice(self.broadcast_config["messages"][chat_id])
        elif self.broadcast_config.get("message"):
            return self.broadcast_config["message"]
        else:
            return None

    def remove_invalid_message_id(self, chat_id: int, message_id: int):
        """Удаляет ID несуществующего сообщения из списка."""
        if chat_id in self.broadcast_config["messages"]:
            with suppress(ValueError):
                self.broadcast_config["messages"][chat_id].remove(message_id)
            self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
