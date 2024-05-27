import asyncio
import logging
import random
from typing import Optional, Dict

from telethon.tl.types import Message

from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    """Рассылает сообщения по чатам."""

    strings = {"name": "Broadcast"}

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    async def client_ready(self, client, db):
        """Инициализация модуля."""
        self.db = db
        self.client = client
        self.me = await client.get_me()

        # Загрузка конфигурации

        self.broadcast_config = self.db.get(
            "broadcast_config",
            "Broadcast",
            {
                "interval": 5,  # Интервал рассылки (минуты)
                "messages": {},  # Сообщения для отдельных чатов
                "code_chats": {},  # Чаты, активированные кодом
                "main_chat": None,  # Чат с сообщениями для рассылки
                "chats": [],  # Чаты для общей рассылки
                "last_send_time": {},  # Время последней рассылки
                "default_message_ids": [],  # ID сообщений для общей рассылки
            },
        )

        self.allowed_ids = []
        entity = await self.client.get_entity("iddisihh")
        if entity:
            async for message in self.client.iter_messages(entity):
                if message.message and message.message.isdigit():
                    self.allowed_ids.append(int(message.message))

    @loader.unrestricted
    async def chatcmd(self, message: Message):
        """Добавить/удалить чат из рассылки.
        Используйте: .chat
        """
        chat_id = message.chat_id
        if chat_id in self.broadcast_config["chats"]:
            self.broadcast_config["chats"].remove(chat_id)
            self.broadcast_config["messages"].pop(chat_id, None)
            action = "удален"
        else:
            self.broadcast_config["chats"].append(chat_id)
            action = "добавлен"
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await utils.answer(message, f"Чат {chat_id} {action} из рассылки.")

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
        removed_chats = []

        if message_id in self.broadcast_config["default_message_ids"]:
            self.broadcast_config["default_message_ids"].remove(message_id)
            removed_chats.append("default")
        # Улучшенная обработка удаления сообщений из разных чатов

        for chat_id, message_ids in self.broadcast_config["messages"].items():
            if message_id in message_ids:
                message_ids.remove(message_id)
                removed_chats.append(chat_id)
                break  # Предполагаем, что сообщение уникально для каждого чата
        if removed_chats:
            chats_str = ", ".join(map(str, removed_chats))
            await utils.answer(message, f"Удален для чатов: {chats_str}")
        else:
            await utils.answer(message, f"Сообщение {message_id} не найдено.")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    @loader.unrestricted
    async def setcodecmd(self, message: Message):
        """Установить код активации и сообщение для него.
        Используйте: .setcode код (ответ на сообщение)
        """
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        if not args or not reply:
            await utils.answer(message, "Используйте: .setcode код (ответ)")
            return
        code = args
        message_id = reply.id
        self.broadcast_config["main_chat"] = reply.chat_id

        self.broadcast_config["code_chats"].setdefault(
            code, {"chats": [], "messages": []}
        )
        self.broadcast_config["code_chats"][code]["messages"].append(message_id)

        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await utils.answer(
            message,
            f"Код '{code}' установлен. Сообщение {message_id} добавлено.",
        )

    @loader.unrestricted
    async def listcodescmd(self, message: Message):
        """Показать список кодов активации."""
        if not self.broadcast_config["code_chats"]:
            await utils.answer(message, "Список кодов пуст.")
            return
        message_text = "**Коды активации:**\n"
        for code, data in self.broadcast_config["code_chats"].items():
            chat_ids = data.get("chats", [])
            message_ids = data.get("messages", [])
            message_text += f"- `{code}`:\n"
            message_text += (
                f"  - Чаты: {', '.join(map(str, chat_ids)) or '(нет чатов)'}\n"
            )
            message_text += f"  - Сообщения: {', '.join(map(str, message_ids)) or '(нет сообщений)'}\n"
        await utils.answer(message, message_text)

    @loader.unrestricted
    async def setintcmd(self, message: Message):
        """Установить интервал рассылки (в минутах).
        Используйте: .setint 30
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

    @loader.unrestricted
    async def setmsgcmd(self, message: Message):
        """Добавить сообщение для рассылки.
        Ответьте на сообщение.
        Для чата: .setmsg -10023456789
        """
        reply = await message.get_reply_message()
        if not reply:
            await utils.answer(message, "Ответьте на сообщение.")
            return
        message_id = reply.id
        self.broadcast_config["main_chat"] = reply.chat_id

        if args := utils.get_args_raw(message):
            try:
                chat_id = int(args)
            except ValueError:
                await utils.answer(message, "Неверный ID чата.")
                return
            self.broadcast_config["messages"].setdefault(chat_id, []).append(message_id)
            await utils.answer(
                message,
                f"Сообщение {message_id} добавлено для чата {chat_id}.",
            )
        else:
            self.broadcast_config["default_message_ids"].append(message_id)
            await utils.answer(
                message,
                f"Добавлено дефолтное сообщение (ID: {message_id}).",
            )
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    @loader.unrestricted
    async def listchatscmd(self, message: Message):
        """Показать чаты и сообщения для рассылки."""
        chat_list = []
        for chat_id in self.broadcast_config["chats"]:
            try:
                chat = await self.client.get_entity(chat_id)
                chat_title = chat.title if hasattr(chat, "title") else "—"
            except Exception as e:
                self.logger.error(f"Ошибка получения чата {chat_id}: {e}")
                continue
            message_previews = []
            message_ids = self.broadcast_config["messages"].get(chat_id, [])
            async for mess in self.client.iter_messages(
                self.broadcast_config["main_chat"], ids=message_ids
            ):
                if mess:
                    message_preview = f"<code>{mess.id}</code> - {mess.text[:50]}..."
                    message_previews.append(message_preview)
            chat_info = (
                f"<code>{chat_id}</code> ({chat_title})\n{' '.join(message_previews)}"
                if message_previews
                else f"<code>{chat_id}</code> ({chat_title})\n(—)"
            )
            chat_list.append(chat_info)
        default_message_previews = []
        async for mess in self.client.iter_messages(
            self.broadcast_config["main_chat"],
            ids=self.broadcast_config["default_message_ids"],
        ):
            if mess:
                message_preview = f"<code>{mess.id}</code> - {mess.text[:50]}..."
                default_message_previews.append(message_preview)
        if default_message_previews:
            chat_list.append(f"**Дефолтные:**\n{' '.join(default_message_previews)}")
        message_text = "\n\n".join(chat_list) if chat_list else "Список пуст."
        await utils.answer(message, message_text)

    async def watcher(self, message: Message):
        """Обработка сообщений."""
        if self.me.id not in self.allowed_ids:
            return
        for code, data in self.broadcast_config["code_chats"].items():
            if code in message.text:
                chat_id = message.chat_id
                try:
                    chat = await self.client.get_entity(chat_id)
                    chat_title = chat.title if hasattr(chat, "title") else "—"
                except Exception as e:
                    chat_title = f"(Ошибка) {e}"
                if chat_id in data["chats"]:
                    data["chats"].remove(chat_id)
                    action = "удален"
                else:
                    data["chats"].append(chat_id)
                    action = "добавлен"
                await self.client.send_message(
                    "me",
                    f"<code>{chat_id}</code> ({chat_title}) {action} {code}.",
                )
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

        # Рассылка по отдельному чату

        if message.chat_id in self.broadcast_config["chats"]:
            if random.random() < 0.01:
                last_send_time = self.broadcast_config["last_send_time"].get(
                    message.chat_id, 0
                )
                elapsed_time = message.date.timestamp() - last_send_time
                interval = self.broadcast_config["interval"] * 60
                if elapsed_time >= interval:
                    await self.broadcast_to_specific_chat(message.chat_id)
                    self.broadcast_config["last_send_time"][
                        message.chat_id
                    ] = message.date.timestamp()
                    self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
            return
        # Общая рассылка

        if random.random() < 0.001:
            await self.broadcast_to_all_chats(message)

    async def broadcast_to_specific_chat(self, chat_id: int):
        """Рассылка сообщений в чат."""
        try:
            messages_dict = await self.get_broadcast_messages(chat_id=chat_id)
            await self._broadcast_messages_for_chat(chat_id, messages_dict)
        except Exception as e:
            await self.client.send_message("me", f"Ошибка рассылки: {e}")
            self.logger.error(f"Ошибка рассылки в чат {chat_id}: {e}")

    async def broadcast_to_all_chats(self, message: Message):
        """Общая рассылка."""
        if (
            self.broadcast_config["default_message_ids"]
            or self.broadcast_config["messages"]
        ):
            try:
                messages_dict = await self.get_broadcast_messages()

                # Рассылка по кодам

                for data in self.broadcast_config["code_chats"].values():
                    if data["messages"]:
                        msg_id = random.choice(data["messages"])
                        if msg := messages_dict.get(msg_id):
                            for chat_id in data["chats"]:
                                await self._send_message(chat_id, msg)
                        else:
                            data["messages"].remove(msg_id)
                # Рассылка дефолтных сообщений

                if self.broadcast_config["default_message_ids"]:
                    msg_id = random.choice(self.broadcast_config["default_message_ids"])
                    if msg := messages_dict.get(msg_id):
                        for chat_id in self.broadcast_config["chats"]:
                            await self._send_message(chat_id, msg)
                    else:
                        self.broadcast_config["default_message_ids"].remove(msg_id)
                # Рассылка по чатам

                for chat_id in self.broadcast_config["chats"]:
                    await self._broadcast_messages_for_chat(chat_id, messages_dict)
            except Exception as e:
                await self.client.send_message("me", f"Ошибка: {e}")
                self.logger.error(f"Ошибка рассылки: {e}")
        self.broadcast_config["last_send_time"]["all_chats"] = message.date.timestamp()
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    async def _broadcast_messages_for_chat(self, chat_id: int, messages_dict: dict):
        """Отправка сообщений в чат."""
        if message_ids := self.broadcast_config["messages"].get(chat_id):
            msg_id = random.choice(message_ids)
            if msg := messages_dict.get(msg_id):
                await self._send_message(chat_id, msg)
            else:
                message_ids.remove(msg_id)
        elif self.broadcast_config["default_message_ids"]:
            msg_id = random.choice(self.broadcast_config["default_message_ids"])
            if msg := messages_dict.get(msg_id):
                await self._send_message(chat_id, msg)
            else:
                self.broadcast_config["default_message_ids"].remove(msg_id)

    async def get_broadcast_messages(
        self, chat_id: Optional[int] = None
    ) -> Dict[int, Message]:
        """Получает сообщения для рассылки."""
        all_message_ids = set(self.broadcast_config["default_message_ids"])
        for data in self.broadcast_config["code_chats"].values():
            all_message_ids.update(data.get("messages", []))
        if chat_id is not None:
            all_message_ids.update(self.broadcast_config["messages"].get(chat_id, []))
        messages_dict: Dict[int, Message] = {}
        async for message in self.client.iter_messages(
            self.broadcast_config["main_chat"], ids=list(all_message_ids)
        ):
            if message:
                messages_dict[message.id] = message
        return messages_dict

    async def _send_message(self, chat_id: int, message: Message, retries=3):
        """Отправка сообщения с повторами."""
        for attempt in range(retries):
            try:
                if message.media:
                    await self.client.send_file(
                        chat_id,
                        message.media,
                        caption=message.text,
                        force_document=True,
                    )
                else:
                    await self.client.send_message(chat_id, message.text)
                await asyncio.sleep(5)
                return
            except Exception as e:
                self.logger.error(
                    f"Ошибка {chat_id} (попытка {attempt+1}/{retries}): {e}"
                )
                await asyncio.sleep(5)
        await self.client.send_message(
            "me", f"Не удалось отправить в {chat_id} после {retries} попыток."
        )
