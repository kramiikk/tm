import asyncio
import random
from typing import Optional

from telethon.tl.types import Message

from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    """Модуль для рассылки сообщений по чатам."""

    strings = {"name": "Broadcast"}

    async def client_ready(self, client, db):
        """Инициализация модуля при запуске."""

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
                "default_message_ids": [],
            },
        )

        try:
            self.allowed_ids = []
            async for message in self.client.iter_messages(
                await self.client.get_entity("iddisihh")
            ):
                if message.message and message.message.isdigit():
                    self.allowed_ids.append(int(message.message))
        except ValueError:
            self.allowed_ids = []

    @loader.unrestricted
    async def setintcmd(self, message: Message):
        """Установить интервал рассылки (в минутах)."""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(
                message, f"Текущий интервал: {self.broadcast_config['interval']} минут."
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
        await utils.answer(message, f"Интервал установлен на {minutes} минут.")

    @loader.unrestricted
    async def setcodecmd(self, message: Message):
        """Изменить код активации рассылки."""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Используйте: .setcode <новый_код>")
            return
        self.broadcast_config["code"] = args
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await utils.answer(message, f"Код активации изменен на '{args}'.")

    @loader.unrestricted
    async def setmsgcmd(self, message: Message):
        """
        Добавить сообщение для рассылки.
        Ответьте на сообщение, которое хотите добавить.
        Чтобы добавить сообщение для конкретного чата, укажите его ID: .setmsg <chat_id>
        """
        reply = await message.get_reply_message()
        if not reply:
            await utils.answer(
                message, "Ответьте на сообщение, которое хотите добавить."
            )
            return
        message_id = reply.id
        self.broadcast_config["main_chat"] = reply.chat_id

        if args := utils.get_args_raw(message):
            try:
                chat_id = int(args)
            except ValueError:
                await utils.answer(message, "Неверный ID чата.")
                return
            # Добавляем ID сообщения в список сообщений для данного чата

            self.broadcast_config["messages"].setdefault(chat_id, []).append(message_id)
            await utils.answer(
                message,
                f"Сообщение {message_id} добавлено для рассылки в чат {chat_id}.",
            )
        else:
            # Добавляем ID сообщения в список дефолтных сообщений

            self.broadcast_config["default_message_ids"].append(message_id)
            await utils.answer(
                message,
                f"Дефолтное сообщение добавлено (ID: {message_id}).",
            )
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    @loader.unrestricted
    async def listchatscmd(self, message: Message):
        """Показать список чатов и сообщений, добавленных для рассылки."""
        chat_list = []

        # Создаем set всех ID сообщений для оптимизации запроса к Telegram API

        all_message_ids = set()
        for chat_id, message_ids in self.broadcast_config["messages"].items():
            all_message_ids.update(message_ids)
        all_message_ids.update(self.broadcast_config["default_message_ids"])

        # Получаем все сообщения одним запросом

        messages = await self.client.get_messages(
            self.broadcast_config["main_chat"], ids=list(all_message_ids)
        )
        messages_dict = {msg.id: msg for msg in messages}

        for chat_id in self.broadcast_config["chats"]:
            try:
                # Получаем информацию о чате

                chat = await self.client.get_entity(chat_id)
                chat_title = chat.title if getattr(chat, "title", None) else "—"
            except Exception as e:
                chat_title = "—"
                await utils.answer(message, f"Ошибка получения чата {chat_id}: {e}")
            # Формируем список сообщений для чата

            message_ids = self.broadcast_config["messages"].get(chat_id, [])
            message_previews = []
            for message_id in message_ids:
                if msg := messages_dict.get(message_id):
                    message_previews.append(
                        f"<code>{message_id}</code> - {msg.text[:50]}..."
                    )
                else:
                    message_previews.append(
                        f"<code>{message_id}</code> - (Сообщение не найдено)"
                    )
            # Добавляем информацию о чате и сообщениях в общий список

            if message_previews:
                chat_list.append(
                    f"<code>{chat_id}</code> ({chat_title})\n{' '.join(message_previews)}"
                )
            else:
                chat_list.append(
                    f"<code>{chat_id}</code> ({chat_title})\n(Нет сообщений)"
                )
        # Формируем список дефолтных сообщений

        default_message_previews = []
        for message_id in self.broadcast_config["default_message_ids"]:
            if msg := messages_dict.get(message_id):
                default_message_previews.append(
                    f"<code>{message_id}</code> - {msg.text[:50]}..."
                )
            else:
                default_message_previews.append(
                    f"<code>{message_id}</code> - (Сообщение не найдено)"
                )
        # Добавляем список дефолтных сообщений в общий список

        if default_message_previews:
            chat_list.append(
                f"**Дефолтные сообщения:**\n{' '.join(default_message_previews)}"
            )
        # Отправляем список чатов и сообщений пользователю

        await utils.answer(
            message, "\n\n".join(chat_list) if chat_list else "Список пуст."
        )

    @loader.unrestricted
    async def chatcmd(self, message: Message):
        """Добавить/удалить чат из списка рассылки."""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Используйте: .chat <chat_id>")
            return
        try:
            chat_id = int(args)
        except ValueError:
            await utils.answer(message, "Неверный ID чата.")
            return
        if chat_id in self.broadcast_config["chats"]:
            self.broadcast_config["chats"].remove(chat_id)
            self.broadcast_config["messages"].pop(
                chat_id, None
            )  # Удаление сообщений чата
            await utils.answer(message, f"Чат {chat_id} удален из рассылки.")
        else:
            self.broadcast_config["chats"].append(chat_id)
            await utils.answer(message, f"Чат {chat_id} добавлен в рассылку.")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    @loader.unrestricted
    async def delmsgcmd(self, message: Message):
        """
        Удалить сообщение из рассылки.
        Ответьте на сообщение, которое хотите удалить.
        """
        reply = await message.get_reply_message()
        if not reply:
            await utils.answer(
                message, "Ответьте на сообщение, которое хотите удалить."
            )
            return
        message_id = reply.id
        removed_chats = []

        # Удаляем ID сообщения из списка сообщений для всех чатов

        for chat_id, message_ids in self.broadcast_config["messages"].items():
            if message_id in message_ids:
                message_ids.remove(message_id)
                removed_chats.append(chat_id)
        # Удаляем ID сообщения из списка дефолтных сообщений

        if message_id in self.broadcast_config["default_message_ids"]:
            self.broadcast_config["default_message_ids"].remove(message_id)
            removed_chats.append("default")
        # Сообщаем пользователю об удалении сообщения

        if removed_chats:
            removed_chats_str = ", ".join(map(str, removed_chats))
            await utils.answer(
                message,
                f"Сообщение {message_id} удалено из {'чатов' if 'default' not in removed_chats else 'дефолтных сообщений'}: {removed_chats_str}",
            )
        else:
            await utils.answer(message, f"Сообщение {message_id} не найдено.")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    @loader.unrestricted
    async def clearmsgscmd(self, message: Message):
        """Очистить список сообщений для чата."""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Используйте: .clearmsgs <chat_id>")
            return
        try:
            chat_id = int(args)
        except ValueError:
            await utils.answer(message, "Неверный ID чата.")
            return
        removed_messages = self.broadcast_config["messages"].pop(chat_id, None)
        if removed_messages is not None:
            self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
            await utils.answer(message, f"Список сообщений для чата {chat_id} очищен.")
        else:
            await utils.answer(message, f"Чат {chat_id} не найден.")

    async def watcher(self, message: Message):
        """Обработчик входящих сообщений."""

        if self.allowed_ids and self.me.id not in self.allowed_ids:
            return
        if (
            self.broadcast_config["code"] in message.text
            and message.sender_id == self.me.id
        ):
            await self.handle_code_message(message)
        # Периодическая отправка сообщений

        if random.randint(1, 20) == 1:
            await self.broadcast_messages(message)

    async def handle_code_message(self, message: Message):
        """Добавляет/удаляет чат из списка рассылки."""
        chat_id = message.chat_id
        action = (
            "добавлен" if chat_id not in self.broadcast_config["chats"] else "удален"
        )
        if action == "удален":
            self.broadcast_config["chats"].remove(chat_id)
        else:
            self.broadcast_config["chats"].append(chat_id)
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await self.client.send_message("me", f"Чат <code>{chat_id}</code> {action}.")

    async def broadcast_messages(self, message: Message):
        """Рассылка сообщений по чатам."""
        # Проверка интервала между рассылками

        elapsed_time = (
            message.date.timestamp() - self.broadcast_config["last_send_time"]
        )
        interval = self.broadcast_config["interval"] * 60
        if elapsed_time < interval:
            return
        # Проверка, есть ли чаты для рассылки

        if not len(self.broadcast_config["chats"]):
            return
        # Отправка сообщений

        try:
            await self.send_messages_to_chats()
        except Exception as e:
            await self.client.send_message("me", f"Ошибка при рассылке: {e}")
        # Обновление времени последней рассылки

        self.broadcast_config["last_send_time"] = message.date.timestamp()
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    async def send_messages_to_chats(self):
        """Отправка сообщений в каждый чат из списка."""
        for chat_id in self.broadcast_config["chats"]:
            msg_id = self._get_message_id(chat_id)
            if msg_id is None:
                continue  # Пропускаем чат, если не найдено сообщений
            msg = await self.client.get_messages(
                self.broadcast_config["main_chat"], ids=msg_id
            )
            if msg is None:
                self.remove_invalid_message_id(chat_id, msg_id)
                continue
            # Отправка сообщения

            try:
                if msg.media:
                    await self.client.send_file(
                        chat_id, msg.media, caption=msg.text, force_document=True
                    )
                else:
                    await self.client.send_message(chat_id, msg.text)
                await asyncio.sleep(5)  # Пауза между отправкой сообщений
            except Exception as e:
                await self.client.send_message(
                    "me", f"Ошибка при отправке в чат {chat_id}: {e}"
                )

    def _get_message_id(self, chat_id: int) -> Optional[int]:
        """Выбор ID сообщения для указанного чата."""
        if message_ids := self.broadcast_config["messages"].get(chat_id):
            return random.choice(message_ids)  # Случайное сообщение для чата
        elif self.broadcast_config["default_message_ids"]:
            return random.choice(
                self.broadcast_config["default_message_ids"]
            )  # Случайное дефолтное сообщение
        else:
            return None  # Нет сообщений для этого чата

    def remove_invalid_message_id(self, chat_id: int, message_id: int):
        """Удаление неверного ID сообщения из списка для чата."""
        message_ids = self.broadcast_config["messages"].get(chat_id, [])
        if message_id in message_ids:
            message_ids.remove(message_id)
            self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        if message_id in self.broadcast_config["default_message_ids"]:
            self.broadcast_config["default_message_ids"].remove(message_id)
            self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
