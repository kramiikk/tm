import asyncio
import random
from typing import Optional

from telethon.tl.types import Message

from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    """Модуль для рассылки сообщений."""

    strings = {"name": "Broadcast"}

    async def client_ready(self, client, db):
        """Инициализация модуля."""
        self.db = db
        self.client = client
        self.me = await client.get_me()

        # Загрузка настроек из базы данных

        self.broadcast_config = db.get(
            "broadcast_config",
            "Broadcast",
            {
                "interval": 5,  # Интервал между рассылками (мин)
                "messages": {},  # Сообщения для каждого чата
                "code": "Super Sonic",  # Код активации рассылки
                "main_chat": None,  # ID чата с сообщениями
                "chats": [],  # Список чатов для рассылки
                "last_send_time": 0,  # Время последней рассылки
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
        """Установить интервал рассылки.

        .setint <число_минут>
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(
                message, f"Текущий интервал: {self.broadcast_config['interval']} минут."
            )
            return
        try:
            minutes = int(args)
        except ValueError:
            await utils.answer(message, "Введите число минут (1-59).")
            return
        if not 1 <= minutes <= 59:
            await utils.answer(message, "Введите число минут (1-59).")
            return
        self.broadcast_config["interval"] = minutes
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await utils.answer(message, f"Интервал: {minutes} минут.")

    @loader.unrestricted
    async def setcodecmd(self, message: Message):
        """Изменить код активации.

        .setcode <новый_код>
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Используйте: .setcode <новый_код>")
            return
        self.broadcast_config["code"] = args
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await utils.answer(message, f"Код изменен на '{args}'.")

    @loader.unrestricted
    async def setmsgcmd(self, message: Message):
        """Добавить сообщение для рассылки.

        .setmsg <chat_id> (ответ на сообщение)
        или .setmsg (ответ - дефолтное сообщение)
        """
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        if not reply:
            await utils.answer(message, "Ответьте на сообщение.")
            return
        message_id = reply.id
        self.broadcast_config["main_chat"] = reply.chat_id

        if args:
            try:
                chat_id = int(args)
            except ValueError:
                await utils.answer(message, "Неверный ID чата.")
                return
            self.broadcast_config["messages"].setdefault(chat_id, []).append(message_id)
            await utils.answer(message, f"Добавлено для чата {chat_id}.")
        else:
            self.broadcast_config["message"] = message_id
            await utils.answer(message, "Установлено как дефолтное.")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    @loader.unrestricted
    async def listchatscmd(self, message: Message):
        """Показать список чатов и сообщений."""
        chat_list = []
        all_message_ids = set()
        for chat_id, message_ids in self.broadcast_config["messages"].items():
            all_message_ids.update(message_ids)
        if self.broadcast_config.get("message"):
            all_message_ids.add(self.broadcast_config["message"])
        # Получаем все сообщения одним запросом

        messages = await self.client.get_messages(
            self.broadcast_config["main_chat"], ids=list(all_message_ids)
        )
        messages_dict = {msg.id: msg for msg in messages}

        for chat_id in self.broadcast_config["chats"]:
            try:
                chat = await self.client.get_input_entity(chat_id)
                chat_title = chat.title
            except Exception as e:  # Ловим общее исключение
                chat_title = f"<code>{chat_id}</code>"
                await utils.answer(message, f"Ошибка получения чата {chat_id}: {e}")
                # Можно добавить удаление невалидного chat_id из списка
                # self.broadcast_config["chats"].remove(chat_id)
            message_ids = self.broadcast_config["messages"].get(chat_id, [])
            message_previews = []
            for message_id in message_ids:  # Используем словарь для поиска
                if msg := messages_dict.get(message_id):
                    message_previews.append(
                        f"<code>{message_id}</code> - {msg.text[:50]}..."
                    )
                else:
                    message_previews.append(
                        f"<code>{message_id}</code> - (Сообщение не найдено)"
                    )
            if message_previews:
                chat_list.append(f"{chat_title}\n{' '.join(message_previews)}")
            else:
                chat_list.append(f"{chat_title}\n(Нет сообщений)")
        await utils.answer(
            message, "\n\n".join(chat_list) if chat_list else "Список пуст."
        )

    @loader.unrestricted
    async def chatcmd(self, message: Message):
        """Добавить/удалить чат из рассылки.

        .chat <chat_id>
        """
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
            await utils.answer(message, "Чат удален.")
        else:
            self.broadcast_config["chats"].append(chat_id)
            await utils.answer(message, "Чат добавлен.")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    @loader.unrestricted
    async def delmsgcmd(self, message: Message):
        """Удалить сообщение из рассылки.

        Ответ на сообщение, которое нужно удалить.
        """
        reply = await message.get_reply_message()
        if not reply:
            await utils.answer(message, "Ответьте на сообщение.")
            return
        message_id = reply.id
        removed_chats = []

        # Используем словарь для поиска чата

        for chat_id, message_ids in self.broadcast_config["messages"].items():
            if message_id in message_ids:
                message_ids.remove(message_id)
                removed_chats.append(chat_id)
        if self.broadcast_config.get("message") == message_id:
            del self.broadcast_config["message"]
            removed_chats.append("Default")
        if removed_chats:
            removed_chats_str = ", ".join(map(str, removed_chats))
            await utils.answer(message, f"Удалено: {removed_chats_str}")
        else:
            await utils.answer(message, f"Сообщение {message_id} не найдено.")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    @loader.unrestricted
    async def clearmsgscmd(self, message: Message):
        """Очистить список сообщений для чата.

        .clearmsgs <chat_id>
        """
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
            await utils.answer(message, f"Список для чата {chat_id} очищен.")
        else:
            await utils.answer(message, f"Чат {chat_id} не найден.")

    async def watcher(self, message: Message):
        """Обработчик сообщений."""

        if self.allowed_ids and self.me.id not in self.allowed_ids:
            return
        if (
            self.broadcast_config["code"] in message.text
            and message.sender_id == self.me.id
        ):
            await self.handle_code_message(message)
        if random.randint(1, 20) == 1:
            await self.broadcast_messages(message)

    async def handle_code_message(self, message: Message):
        """Обработать код активации."""
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
        """Рассылка сообщений."""
        elapsed_time = (
            message.date.timestamp() - self.broadcast_config["last_send_time"]
        )
        interval = self.broadcast_config["interval"] * 60
        if elapsed_time < interval:
            return
        if not (
            self.broadcast_config.get("message") or len(self.broadcast_config["chats"])
        ):
            return
        try:
            await self.send_messages_to_chats()
        except Exception as e:
            await self.client.send_message("me", f"Ошибка: {e}")
        self.broadcast_config["last_send_time"] = message.date.timestamp()
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    async def send_messages_to_chats(self):
        """Отправить сообщения в каждый чат."""
        for chat_id in self.broadcast_config["chats"]:
            msg_id = self._get_random_message_id(chat_id)

            # Проверить, есть ли сообщения для чата

            if msg_id is None:
                await self.client.send_message(
                    "me", f"Нет сообщений для чата {chat_id}."
                )
                continue
            msg = await self.client.get_messages(
                self.broadcast_config["main_chat"], ids=msg_id
            )
            if msg is None:
                self.remove_invalid_message_id(chat_id, msg_id)
                continue
            try:
                if msg.media:
                    await self.client.send_file(
                        chat_id, msg.media, caption=msg.text, force_document=True
                    )
                else:
                    await self.client.send_message(chat_id, msg.text)
                await asyncio.sleep(5)
            except Exception as e:
                await self.client.send_message("me", f"Ошибка в чате {chat_id}: {e}")

    def _get_random_message_id(self, chat_id: int) -> Optional[int]:
        """Вернуть случайный ID сообщения (или None, если список пуст)."""
        if message_ids := self.broadcast_config["messages"].get(chat_id, []):
            return random.choice(message_ids)
        return self.broadcast_config.get("message")

    def remove_invalid_message_id(self, chat_id: int, message_id: int):
        """Удалить неверный ID сообщения."""
        message_ids = self.broadcast_config["messages"].get(chat_id, [])
        if message_id in message_ids:
            message_ids.remove(message_id)
            self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
