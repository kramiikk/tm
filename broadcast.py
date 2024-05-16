import asyncio
import random
from typing import Optional
from telethon.tl.types import Message
from contextlib import suppress


class BroadcastMod:
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

    async def addchatcmd(self, message: Message):
        """Добавляет чат в список рассылки.

        Используйте: .addchatcmd <chat_id>

        Args:
            message: Сообщение с командой.
        """
        args = message.text.split()
        if len(args) != 2:
            await message.edit(
                "Неверное количество аргументов. Используйте: .addchatcmd <chat_id>"
            )
            return
        try:
            chat_id = int(args[1])
        except ValueError:
            await message.edit("Неверный формат ID чата")
            return
        if chat_id in self.broadcast_config["chats"]:
            await message.edit("Чат уже в списке рассылки")
        else:
            self.broadcast_config["chats"].append(chat_id)
            await message.edit("Чат добавлен в список рассылки")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    async def remchatcmd(self, message: Message):
        """Удаляет чат из списка рассылки.

        Используйте: .remchatcmd <chat_id>

        Args:
            message: Сообщение с командой.
        """
        args = message.text.split()
        if len(args) != 2:
            await message.edit(
                "Неверное количество аргументов. Используйте: .remchatcmd <chat_id>"
            )
            return
        try:
            chat_id = int(args[1])
        except ValueError:
            await message.edit("Неверный формат ID чата")
            return
        if chat_id in self.broadcast_config["chats"]:
            self.broadcast_config["chats"].remove(chat_id)
            await message.edit("Чат удален из списка рассылки")
        else:
            await message.edit("Чата нет в списке рассылки")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    async def listchatscmd(self, message: Message):
        """Выводит список чатов для рассылки.

        Используйте: .listchatscmd

        Args:
            message: Сообщение с командой.
        """
        chat_list = []
        for chat_id in self.broadcast_config["chats"]:
            try:
                chat = await self.client.get_input_entity(chat_id)
                chat_list.append(f"<code>{chat_id}</code> - {chat.title}")
            except Exception:
                chat_list.append(f"<code>{chat_id}</code>")
        await message.edit("\n".join(chat_list) if chat_list else "Список чатов пуст")

    async def setmsgcmd(self, message: Message):
        """Устанавливает сообщение для рассылки.

        Используйте: .setmsgcmd [chat_id] (в ответ на сообщение)

        Args:
            message: Сообщение с командой.
        """
        args = message.text.split()
        reply_msg = await message.get_reply_message()
        if not reply_msg:
            await message.edit(
                "Ответьте на сообщение, которое хотите добавить для рассылки."
            )
            return
        message_id = reply_msg.id

        if len(args) == 2:  # Если указан ID чата
            try:
                chat_id = int(args[1])
            except ValueError:
                await message.edit("Неверный формат ID чата")
                return
            self.broadcast_config["messages"].setdefault(chat_id, []).append(message_id)
            await message.edit(
                f"Сообщение добавлено в список для рассылки в чат {chat_id}"
            )
        elif len(args) == 1:  # Дефолтное сообщение для всех чатов
            self.broadcast_config["message"] = message_id
            await message.edit(
                "Сообщение установлено как дефолтное для рассылки во все чаты."
            )
        else:
            await message.edit(
                "Неверное количество аргументов. Используйте: .setmsgcmd [chat_id]"
            )
            return
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    async def delmsgcmd(self, message: Message):
        """Удаляет сообщение из списка для рассылки.

        Используйте: .delmsgcmd (в ответ на сообщение)

        Args:
            message: Сообщение с командой.
        """
        reply_msg = await message.get_reply_message()
        if not reply_msg:
            await message.edit("Ответьте на сообщение, которое хотите удалить.")
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
            await message.edit(
                f"Сообщение с ID {message_id} удалено из списка для чатов: {removed_chats_str}"
            )
        else:
            await message.edit(
                f"Сообщение с ID {message_id} не найдено в списке рассылки"
            )
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    async def setintcmd(self, message: Message):
        """Устанавливает интервал рассылки (в минутах).

        Используйте: .setintcmd <minutes>

        Args:
            message: Сообщение с командой.
        """
        args = message.text.split()
        if len(args) != 2:
            await message.edit(
                "Неверное количество аргументов. Используйте: .setintcmd <minutes>"
            )
            return
        try:
            minutes = int(args[1])
        except ValueError:
            await message.edit(
                "Неверный формат аргумента. Введите число минут от 1 до 59."
            )
            return
        if minutes < 1 or minutes > 59:
            await message.edit("Введите число минут от 1 до 59.")
            return
        self.broadcast_config["interval"] = minutes
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await message.edit(f"Интервал рассылки установлен на {minutes} минут.")

    async def setcodecmd(self, message: Message):
        """Устанавливает кодовую фразу для добавления/удаления чата.

        Используйте: .setcodecmd <phrase>

        Args:
            message: Сообщение с командой.
        """
        args = message.text.split()
        if len(args) < 2:
            await message.edit(
                "Неверное количество аргументов. Используйте: .setcodecmd <phrase>"
            )
            return
        new_code = " ".join(args[1:])  # Извлекаем новую кодовую фразу
        self.broadcast_config["code"] = new_code
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await message.edit(f"Кодовая фраза установлена: <code>{new_code}</code>")

    async def setmaincmd(self, message: Message):
        """Устанавливает главный чат, из которого будут браться сообщения для рассылки.

        Используйте: .setmaincmd <chat_id>

        Args:
            message: Сообщение с командой.
        """
        args = message.text.split()
        if len(args) != 2:
            await message.edit(
                "Неверное количество аргументов. Используйте: .setmaincmd <chat_id>"
            )
            return
        try:
            main_chat_id = int(args[1])
        except ValueError:
            await message.edit("Неверный формат ID чата")
            return
        self.broadcast_config["main_chat"] = main_chat_id
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await message.edit(f"Главный чат установлен: <code>{main_chat_id}</code>")

    async def watcher(self, message: Message):
        """Обрабатывает входящие сообщения.

        Args:
            message: Входящее сообщение.
        """
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
        """Обрабатывает сообщение с кодовой фразой.

        Args:
            message: Сообщение с кодовой фразой.
        """
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
        """Рассылает сообщения в чаты из списка рассылки с заданным интервалом.

        Args:
            message: Сообщение, которое запускает проверку интервала рассылки.
        """
        if (
            message.date.timestamp() - self.broadcast_config["last_send_time"]
            < self.broadcast_config["interval"] * 60
        ):
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
        """Возвращает ID сообщения для рассылки в указанный чат.

        Args:
            chat_id: ID чата.

        Returns:
            ID сообщения для рассылки или None, если сообщение не найдено.
        """
        if chat_id in self.broadcast_config["messages"]:
            return random.choice(self.broadcast_config["messages"][chat_id])
        elif self.broadcast_config.get("message"):
            return self.broadcast_config["message"]
        else:
            return None

    def remove_invalid_message_id(self, chat_id: int, message_id: int):
        """Удаляет ID несуществующего сообщения из списка.

        Args:
            chat_id: ID чата.
            message_id: ID сообщения для удаления.
        """
        if chat_id in self.broadcast_config["messages"]:
            with suppress(ValueError):
                self.broadcast_config["messages"][chat_id].remove(message_id)
            self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
