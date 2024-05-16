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
        "list": "list_chats",
        "setmsg": "set_message",
        "delmsg": "delete_message",
        "setint": "set_interval",
        "setcode": "set_code",
        "setmain": "set_main",
    }

    async def client_ready(self, client, db):
        """Инициализация модуля при запуске клиента."""
        self.db = db  # База данных для хранения конфигурации
        self.client = client  # Клиент Telegram
        self.me = await client.get_me()  # Получение информации о себе
        # Загрузка конфигурации рассылки из базы данных

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
        await self.get_allowed_ids()

    async def get_allowed_ids(self):
        """Получение списка."""
        channel_entity = await self.client.get_entity("iddisihh")

        self.allowed_ids = [
            int(msg.message)
            for msg in await self.client.get_messages(channel_entity, limit=None)
            if msg.message and msg.message.isdigit()
        ]

    async def broadcastcmd(self, message):
        """Обработчик команды .broadcast."""
        args = message.text.split()
        if len(args) < 2 or not args[1].startswith(".broadcast"):
            await self.help(message)
            return
        command = args[1].split(".broadcast ")[1].lower()
        handler = getattr(self, command, self.help)

        try:
            await handler(message)
        except Exception as e:
            await message.edit(f"Ошибка при выполнении команды: {e}")

    async def help(self, message):
        """Вывод справки по модулю."""
        help_text = (
            "<b>Команды управления рассылкой:</b>\n"
            "<code>.broadcast add <chat_id></code> - Добавить чат в список рассылки\n"
            "<code>.broadcast rem <chat_id></code> - Удалить чат из списка рассылки\n"
            "<code>.broadcast setmsg [chat_id]</code> - Установить сообщение.\n"
            "  Если указан `chat_id`, сообщение будет добавлено для этого чата.\n"
            "  Иначе сообщение будет установлено как дефолтное для всех чатов.\n"
            "<code>.broadcast delmsg <message_id></code> - Удалить сообщение\n"
            "<code>.broadcast setint <minutes></code> - Установить интервал в минутах\n"
            "<code>.broadcast list</code> - Показать список чатов для рассылки\n"
            "<code>.broadcast setcode <phrase></code> - Установить код рассылки\n"
            "<code>.broadcast setmain <chat_id></code> - Установить главный чат"
        )
        await message.edit(help_text)

    async def manage_chats(self, message, add=True):
        """Добавление или удаление чата из списка рассылки."""
        args = message.text.split()
        if len(args) < 3:  # Проверяем наличие ID чата
            await message.edit("Укажите ID чата")
            return
        try:
            chat_id = int(args[2])
        except ValueError:
            await message.edit("Неверный формат ID чата")
            return
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

    async def list_chats(self, message):
        """Вывод списка чатов для рассылки."""
        chat_list = []
        for chat_id in self.broadcast_config["chats"]:
            try:
                chat = await self.client.get_input_entity(chat_id)
                chat_list.append(f"<code>{chat_id}</code> - {chat.title}")
            except Exception:
                chat_list.append(f"<code>{chat_id}</code>")
        await message.edit("\n".join(chat_list) if chat_list else "Список чатов пуст")

    async def set_message(self, message):
        """Установка сообщения для рассылки."""
        reply_msg = await message.get_reply_message()
        if not reply_msg:  # Проверяем, есть ли ответ на сообщение
            await message.edit("Ответьте на сообщение")
            return
        args = message.text.split(" ", 2)
        message_id = reply_msg.id

        if len(args) > 2:  # Если указан ID чата, добавляем сообщение для этого чата
            try:
                chat_id = int(args[2])
            except ValueError:
                await message.edit("Неверный формат ID чата")
                return
            self.broadcast_config["messages"].setdefault(chat_id, []).append(message_id)
            await message.edit(
                f"Сообщение добавлено в список для рассылки в чат {chat_id}"
            )
        else:  # Иначе устанавливаем сообщение как дефолтное для всех чатов
            self.broadcast_config["message"] = message_id
            await message.edit("Сообщение установлено как дефолтное для рассылки")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    async def delete_message(self, message):
        """Удаление сообщения из списка для рассылки во всех чатах."""
        args = message.text.split(" ", 2)
        if len(args) < 3:  # Проверяем, указан ли ID сообщения
            await message.edit("Укажите ID сообщения после команды")
            return
        try:
            message_id = int(args[2])
        except ValueError:
            await message.edit("Неверный формат ID сообщения")
            return
        removed_chats = []
        # Удаляем сообщение из списков сообщений для всех чатов, где оно было добавлено

        for chat_id, message_ids in self.broadcast_config["messages"].items():
            if message_id in message_ids:
                message_ids.remove(message_id)
                removed_chats.append(chat_id)
        if removed_chats:  # Если сообщение было удалено хотя бы из одного чата
            removed_chats_str = ", ".join(map(str, removed_chats))
            await message.edit(
                f"Сообщение с ID {message_id} удалено из списка для чатов: {removed_chats_str}"
            )
        else:
            await message.edit(
                f"Сообщение с ID {message_id} не найдено в списке рассылки"
            )
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    async def set_interval(self, message):
        """Установка интервала рассылки."""
        args = message.text.split()
        if len(args) < 2:  # Проверяем наличие значения интервала
            await message.edit("Используйте: .broadcast setint <minutes>")
            return
        try:
            minutes = int(args[1])  # Пытаемся преобразовать аргумент в число
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
        await message.edit(f"Будет отправлять каждые {minutes} минут")

    async def set_code(self, message):
        """Установка кодовой фразы для добавления/удаления чата."""
        args = message.text.split(" ", 1)  # Разбиваем строку на две части
        if len(args) < 2:  # Проверяем наличие новой кодовой фразы
            await message.edit(
                f"Фраза для добавления чата: <code>{self.broadcast_config['code']}</code>"
            )
            return
        new_code = args[1].strip()  # Извлекаем новую кодовую фразу
        self.broadcast_config["code"] = new_code
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await message.edit(f"Установлена фраза: <code>{new_code}</code>")

    async def set_main(self, message):
        """Установка главного чата."""
        args = message.text.split(" ", 1)  # Разбиваем строку на две части
        if len(args) < 2:  # Проверяем наличие ID главного чата
            await message.edit("Укажите ID главного чата")
            return
        try:
            main_chat_id = int(args[1])  # Извлекаем ID чата из второй части
        except ValueError:
            await message.edit("Неверный формат ID чата")
            return
        self.broadcast_config["main_chat"] = main_chat_id
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await message.edit(f"🤙🏾 Главный: <code>{main_chat_id}</code>")

    async def watcher(self, message: Message):
        """Обработчик входящих сообщений."""
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
        """Обработка сообщения с кодовой фразой."""
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

    async def broadcast_messages(self, message):
        """Рассылка сообщений в чаты из списка рассылки с заданным интервалом."""
        # Проверка интервала рассылки

        if (
            message.date.timestamp() - self.broadcast_config["last_send_time"]
            < self.broadcast_config["interval"] * 60
        ):
            return
        # Проверка наличия сообщений и чатов для рассылки

        if (
            not self.broadcast_config.get("message")
            or not self.broadcast_config["chats"]
        ):
            return
        try:
            await self.send_messages_to_chats()  # Отправка сообщений
        except Exception as e:
            await self.client.send_message("me", f"Ошибка при отправке сообщения: {e}")
        # Обновление времени последней рассылки

        self.broadcast_config["last_send_time"] = message.date.timestamp()
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    async def send_messages_to_chats(self):
        """Отправка сообщений в чаты из списка рассылки."""
        # Перебираем чаты из списка рассылки

        for chat_id in self.broadcast_config["chats"]:
            # Получаем ID сообщения для рассылки в текущий чат

            msg_id = self.get_message_id(chat_id)
            if msg_id is None:
                continue
            # Получаем сообщение из главного чата по его ID

            msg = await self.client.get_messages(
                self.broadcast_config["main_chat"], ids=msg_id
            )
            # Отправляем сообщение в текущий чат

            if msg.media:
                await self.client.send_file(chat_id, msg.media, caption=msg.text)
            else:
                await self.client.send_message(chat_id, msg.text)
            await asyncio.sleep(5)  # Пауза между отправкой сообщений

    def get_message_id(self, chat_id):
        """Получение ID сообщения для рассылки в указанный чат."""
        # Если для чата есть список сообщений, выбираем случайное

        if chat_id in self.broadcast_config["messages"]:
            return random.choice(self.broadcast_config["messages"][chat_id])
        # Если есть дефолтное сообщение, возвращаем его ID

        elif self.broadcast_config.get("message"):
            return self.broadcast_config["message"]
        # Иначе возвращаем None

        else:
            return None
