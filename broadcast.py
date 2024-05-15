import asyncio
import random
from telethon.tl.types import Message
from .. import loader


@loader.tds
class BroadcastMod(loader.Module):
    """Модуль для рассылки сообщений в чаты"""

    strings = {"name": "Broadcast"}

    command_handlers = {
        "add": "manage_chats",
        "rem": "manage_chats",
        "setmsg": "set_message",
        "delmsgchat": "delete_message",
        "setint": "set_interval",
        "list": "list_chats",
        "setcode": "set_code",
        "setmain": "set_main",
    }

    async def client_ready(self, client, db):
        self.db = db
        self.client = client
        self.me = await client.get_me()
        self.broadcast_config = db.get(
            "broadcast_config",
            "Broadcast",
            {
                "interval": 5,
                "messages": {},
                "code": "Super Sonic",
                "main_chat": None,
                "chats": [],
                "last_send_time": 0,
            },
        )

        self.allowed_ids = [
            int(message.message)
            for message in self.client.iter_messages(
                await self.client.get_input_entity("iddisihh"),
                filter=lambda m: bool(m.message),
            )
        ]

    @loader.unrestricted
    async def broadcastcmd(self, message):
        """Управление рассылкой"""
        args = message.text.split(" ", 1)
        if len(args) == 1:
            await self.help(message)
            return
        command = args[1].lower()
        handler = getattr(self, self.command_handlers.get(command, "help"), self.help)
        await handler(message)

    async def help(self, message):
        """Вывод справки"""
        help_text = (
            "<b>Команды управления рассылкой:</b>\n"
            "<code>.broadcast add [id]</code> - Добавить чат в список рассылки\n"
            "<code>.broadcast rem [id]</code> - Удалить чат из списка рассылки\n"
            "<code>.broadcast setmsg</code> - Установить сообщение для рассылки (ответить на сообщение)\n"
            "<code>.broadcast delmsg [id]</code> - Удалить сообщение из списка рассылки\n"
            "<code>.broadcast setint</code> - Установить интервал рассылки\n"
            "<code>.broadcast list</code> - Показать список чатов для рассылки\n"
            "<code>.broadcast setcode</code> - Установить код рассылки\n"
            "<code>.broadcast setmain</code> - Установить главный чат для рассылки"
        )
        await message.edit(help_text)

    async def manage_chats(self, message, add=True):
        """Управление списком чатов для рассылки"""
        args = message.text.split()
        if len(args) <= 2:
            await message.edit("Укажите ID чата")
            return
        chat_id = int(args[2])
        if add and chat_id in self.broadcast_config["chats"]:
            await message.edit("Чат уже в списке рассылки")
        elif add:
            self.broadcast_config["chats"].append(chat_id)
            await message.edit("Чат добавлен в список рассылки")
        elif chat_id in self.broadcast_config["chats"]:
            self.broadcast_config["chats"].remove(chat_id)
            await message.edit("Чат удален из списка рассылки")
        else:
            await message.edit("Чата нет в списке рассылки")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    async def set_message(self, message):
        """Установка сообщения для рассылки"""
        reply_msg = await message.get_reply_message()
        if not reply_msg:
            await message.edit("Ответьте на сообщение")
            return
        args = message.text.split(" ", 2)
        message_id = reply_msg.id

        if len(args) > 2:
            chat_id = int(args[2])
            self.broadcast_config["messages"].setdefault(chat_id, []).append(message_id)
            await message.edit(
                f"Сообщение добавлено в список для рассылки в чат {chat_id}"
            )
        else:
            self.broadcast_config["message"] = message_id
            await message.edit("Сообщение установлено как дефолтное для рассылки")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    async def set_interval(self, message):
        """Установка интервала рассылки"""
        args = message.text.split(" ", 2)
        if len(args) < 3:
            await message.edit(
                f"Отправляет каждые {self.broadcast_config['interval']} минут"
            )
            return
        minutes = args[2]
        if not minutes.isdigit() or not 0 < int(minutes) < 60:
            await message.edit("Введите числовое значение в интервале 1 - 59")
            return
        self.broadcast_config["interval"] = int(minutes)
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await message.edit(f"Будет отправлять каждые {minutes} минут")

    async def delete_message(self, message):
        """Удалить сообщение из списка для рассылки во всех чатах"""
        args = message.text.split(" ", 2)
        if len(args) <= 2:
            await message.edit("Укажите ID сообщения после команды")
            return
        message_id = int(args[2])

        removed_chats = []
        for chat_id, message_ids in self.broadcast_config["messages"].items():
            if message_id in message_ids:
                message_ids.remove(message_id)
                removed_chats.append(chat_id)
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

    async def list_chats(self, message):
        """Вывод списка чатов для рассылки"""
        chat_list = []
        for chat_id in self.broadcast_config["chats"]:
            try:
                chat = await self.client.get_input_entity(chat_id)
                chat_list.append(f"<code>{chat_id}</code> - {chat.title}")
            except Exception:
                chat_list.append(f"<code>{chat_id}</code>")
        await message.edit("\n".join(chat_list) if chat_list else "Список чатов пуст")

    async def set_code(self, message):
        """Установка кодовой фразы для добавления чата"""
        args = message.text.split(" ", 2)
        if len(args) < 3:
            await message.edit(
                f"Фраза для добавления чата: <code>{self.broadcast_config['code']}</code>"
            )
            return
        self.broadcast_config["code"] = args[2]
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await message.edit(f"Установлена фраза: <code>{args[2]}</code>")

    async def set_main(self, message):
        """Установка главного чата"""
        args = message.text.split(" ", 2)
        if len(args) < 3:
            await message.edit("Укажите ID главного чата")
            return
        main_chat_id = int(args[2])
        self.broadcast_config["main_chat"] = main_chat_id
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await message.edit(f"🤙🏾 Главный: <code>{main_chat_id}</code>")

    async def watcher(self, message: Message):
        """
        Обработчик входящих сообщений.
        Выполняет следующие задачи:
        1. Добавление/удаление чата из списка рассылки при получении сообщения с кодовой фразой.
        2. Рассылка сообщений в чаты из списка рассылки с заданным интервалом.
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

    async def handle_code_message(self, message):
        """
        Обработка сообщения с кодовой фразой для добавления/удаления чата в список рассылки.
        """
        chat_id = message.chat_id
        if chat_id not in self.broadcast_config["chats"]:
            self.broadcast_config["chats"].append(chat_id)
            action = "добавлен"
        else:
            self.broadcast_config["chats"].remove(chat_id)
            action = "удален"
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await self.client.send_message(
            "me", f"Чат <code>{chat_id}</code> {action} в список рассылки"
        )

    async def broadcast_messages(self, message):
        """
        Рассылка сообщений в чаты из списка рассылки с заданным интервалом.
        """
        current_time = message.date.timestamp()
        if (
            current_time - self.broadcast_config["last_send_time"]
            < self.broadcast_config["interval"] * 60
        ):
            return
        if (
            not self.broadcast_config["message"]
            or not self.broadcast_config["chats"]
            or message.chat_id not in self.broadcast_config["chats"]
        ):
            return
        try:
            await self.send_messages_to_chats()
        except Exception as e:
            await self.client.send_message("me", f"Ошибка при отправке сообщения: {e}")
        self.broadcast_config["last_send_time"] = current_time
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    async def send_messages_to_chats(self):
        """
        Отправка сообщений в чаты из списка рассылки.
        """
        for chat_id in self.broadcast_config["chats"]:
            message_id = self.get_message_id(chat_id)
            msg = await self.client.get_messages(
                self.broadcast_config["main_chat"], ids=message_id
            )
            if msg.media:
                await self.client.send_file(chat_id, msg.media, caption=msg.text)
            else:
                await self.client.send_message(chat_id, msg.text)
            await asyncio.sleep(3)

    def get_message_id(self, chat_id):
        """
        Получение ID сообщения для рассылки в указанный чат.
        """
        if chat_id in self.broadcast_config["messages"]:
            return random.choice(self.broadcast_config["messages"][chat_id])
        elif self.broadcast_config["messages_list"]:
            return random.choice(self.broadcast_config["messages_list"])
        else:
            return self.broadcast_config["message"]
