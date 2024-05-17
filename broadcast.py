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
    async def chatcmd(self, message: Message):
        """Добавить/удалить чат из списка рассылки."""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Используйте: .chat id")
            return
        try:
            chat_id = int(args)
        except ValueError:
            await utils.answer(message, "Неверный ID чата.")
            return
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

        for chat_id, message_ids in self.broadcast_config["messages"].items():
            if message_id in message_ids:
                message_ids.remove(message_id)
                removed_chats.append(chat_id)
        if message_id in self.broadcast_config["default_message_ids"]:
            self.broadcast_config["default_message_ids"].remove(message_id)
            removed_chats.append("default")
        if removed_chats:
            chats_str = ", ".join(map(str, removed_chats))
            await utils.answer(
                message,
                f"Удален для чатов: {chats_str}",
            )
        else:
            await utils.answer(message, f"Сообщение {message_id} не найдено.")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    @loader.unrestricted
    async def setcodecmd(self, message: Message):
        """Изменить код активации рассылки."""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Используйте: .setcode кодовое слово")
            return
        self.broadcast_config["code"] = args
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await utils.answer(message, f"Код активации изменен на '{args}'.")

    @loader.unrestricted
    async def setintcmd(self, message: Message):
        """Установить интервал рассылки по всем чатам (в минутах)."""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(
                message,
                f"Текущий интервал: {self.broadcast_config['interval']} минут.",
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
        await utils.answer(
            message, f"Интервал рассылки по всем чатам установлен на {minutes} минут."
        )

    @loader.unrestricted
    async def setmsgcmd(self, message: Message):
        """
        Добавить сообщение для рассылки.
        Ответьте на сообщение, которое хотите добавить.
        Чтобы добавить сообщение для конкретного чата, укажите его ID: .setmsg id чата
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
            self.broadcast_config["messages"].setdefault(chat_id, []).append(message_id)
            await utils.answer(
                message,
                f"Сообщение {message_id} добавлено для рассылки в чат {chat_id}.",
            )
        else:
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
        all_message_ids = set(self.broadcast_config["default_message_ids"])

        for chat_id, message_ids in self.broadcast_config["messages"].items():
            all_message_ids.update(message_ids)
            try:
                chat = await self.client.get_entity(chat_id)
                chat_title = chat.title if getattr(chat, "title", None) else "—"
            except Exception as e:
                chat_list.append(f"Ошибка получения информации о чате {chat_id}: {e}")
                continue
            message_previews = []
            for message_id in message_ids:
                msg = messages_dict.get(message_id)
                if msg:
                    message_previews.append(
                        f"<code>{message_id}</code> - {msg.text[:50]}..."
                    )
                else:
                    message_previews.append(
                        f"<code>{message_id}</code> - (Сообщение не найдено)"
                    )
            if message_previews:
                chat_list.append(
                    f"<code>{chat_id}</code> ({chat_title})\n{' '.join(message_previews)}"
                )
            else:
                chat_list.append(
                    f"<code>{chat_id}</code> ({chat_title})\n(Нет сообщений)"
                )
        # Получаем все сообщения один раз

        messages = await self.client.get_messages(
            self.broadcast_config["main_chat"], ids=list(all_message_ids)
        )
        messages_dict = {msg.id: msg for msg in messages}

        default_message_previews = []
        for message_id in self.broadcast_config["default_message_ids"]:
            msg = messages_dict.get(message_id)
            if msg:
                default_message_previews.append(
                    f"<code>{message_id}</code> - {msg.text[:50]}..."
                )
            else:
                default_message_previews.append(
                    f"<code>{message_id}</code> - (Сообщение не найдено)"
                )
        if default_message_previews:
            chat_list.append(
                f"**Дефолтные сообщения:**\n{' '.join(default_message_previews)}"
            )
        await utils.answer(
            message, "\n\n".join(chat_list) if chat_list else "Список пуст."
        )

    async def watcher(self, message: Message):
        """Обработчик входящих сообщений."""

        if self.allowed_ids and self.me.id not in self.allowed_ids:
            return
        if (
            self.broadcast_config["code"] in message.text
            and message.sender_id == self.me.id
        ):
            await self.handle_code_message(message)
        # Рассылка в чат из списка

        if message.chat_id in self.broadcast_config["chats"]:
            if random.randint(1, 30) == 13:
                await self.broadcast_to_single_chat(message)
            return
        # Рассылка по всем чатам

        if random.randint(1, 100) == 1:
            await self.broadcast_to_all_chats(message)

    async def handle_code_message(self, message: Message):
        """Добавляет/удаляет чат из списка рассылки."""
        chat_id = message.chat_id

        try:
            chat = await self.client.get_entity(chat_id)
            chat_title = chat.title if getattr(chat, "title", None) else "—"
        except Exception as e:
            chat_title = f"(Ошибка получения названия) {e}"
        if chat_id in self.broadcast_config["chats"]:
            self.broadcast_config["chats"].remove(chat_id)
            action = "удален"
        else:
            self.broadcast_config["chats"].append(chat_id)
            action = "добавлен"
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await self.client.send_message(
            "me", f"Чат <code>{chat_id}</code> ({chat_title}) {action}."
        )

    async def broadcast_to_single_chat(self, message: Message):
        """Рассылка сообщения в один чат, где оно получено."""
        chat_id = message.chat_id

        # Проверка, находится ли чат в списке для рассылки

        if chat_id in self.broadcast_config["chats"]:
            await self._send_message(chat_id, message)

    async def broadcast_to_all_chats(self, message: Message):
        """Периодическая рассылка по всем чатам."""
        elapsed_time = (
            message.date.timestamp() - self.broadcast_config["last_send_time"]
        )
        interval = self.broadcast_config["interval"] * 60
        if elapsed_time < interval:
            return
        if not self.broadcast_config["chats"]:
            return
        # Проверяем наличие дефолтных сообщений

        if self.broadcast_config["default_message_ids"]:
            # Выбираем случайное сообщение из дефолтных сообщений

            msg_id = random.choice(self.broadcast_config["default_message_ids"])
            msg = await self.client.get_messages(
                self.broadcast_config["main_chat"], ids=msg_id
            )
            if not msg:
                self.broadcast_config["default_message_ids"].remove(msg_id)
                self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
                return
            try:
                for chat_id in self.broadcast_config["chats"]:
                    await self._send_message(chat_id, msg)
            except Exception as e:
                await self.client.send_message("me", f"Ошибка при рассылке: {e}")
        self.broadcast_config["last_send_time"] = message.date.timestamp()
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    async def _send_message(self, chat_id: int, message: Message):
        """Отправка сообщения в указанный чат."""
        try:
            if message.media:
                await self.client.send_file(
                    chat_id, message.media, caption=message.text, force_document=True
                )
            else:
                await self.client.send_message(chat_id, message.text)
            await asyncio.sleep(5)
        except Exception as e:
            await self.client.send_message(
                "me", f"Ошибка при отправке в чат {chat_id}: {e}"
            )
