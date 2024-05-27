import asyncio
import random
import logging
from typing import Optional

from telethon.tl.types import Message

from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    """Модуль для рассылки сообщений по чатам."""

    strings = {"name": "Broadcast"}

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

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
                "messages": {},  # Сообщения для рассылки по определённым чатам
                "code": "Super Sonic",  # Код активации рассылки
                "main_chat": None,  # Чат, из которого берутся сообщения для рассылки
                "chats": [],  # Список чатов для рассылки
                "last_send_time": 0,  # Время последней рассылки по всем чатам
                "default_message_ids": [],  # Список ID сообщений для рассылки по всем чатам
            },
        )

        try:
            self.allowed_ids = []
            entity = await self.client.get_entity("iddisihh")
            if entity:
                async for message in self.client.iter_messages(entity):
                    if message.message and message.message.isdigit():
                        self.allowed_ids.append(int(message.message))
        except ValueError:
            self.allowed_ids = []

    @loader.unrestricted
    async def chatcmd(self, message: Message):
        """
        Добавить/удалить чат из списка рассылки.

        Пример:
            .chat -10023456789
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Используйте: .chat ID чата")
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
            )  # Удаляем сообщения для этого чата
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

        # Удаляем сообщение из списка дефолтных сообщений

        if message_id in self.broadcast_config["default_message_ids"]:
            self.broadcast_config["default_message_ids"].remove(message_id)
            removed_chats.append("default")
        # Удаляем сообщение из списков сообщений для каждого чата

        for chat_id, message_ids in self.broadcast_config["messages"].items():
            if message_id in message_ids:
                message_ids.remove(message_id)
                removed_chats.append(chat_id)
        if removed_chats:
            chats_str = ", ".join(map(str, removed_chats))
            await utils.answer(message, f"Удален для чатов: {chats_str}")
        else:
            await utils.answer(message, f"Сообщение {message_id} не найдено.")
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    @loader.unrestricted
    async def setcodecmd(self, message: Message):
        """
        Изменить код активации рассылки.

        Пример:
            .setcode MySecretCode
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Используйте: .setcode кодовое слово")
            return
        self.broadcast_config["code"] = args
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await utils.answer(message, f"Код активации изменен на '{args}'.")

    @loader.unrestricted
    async def setintcmd(self, message: Message):
        """
        Установить интервал рассылки по всем чатам (в минутах).

        Пример:
            .setint 30
        """
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
        Чтобы добавить сообщение для конкретного чата, укажите его ID.

        Пример:
            .setmsg
            .setmsg -10023456789
        """
        reply = await message.get_reply_message()
        if not reply:
            await utils.answer(
                message, "Ответьте на сообщение, которое хотите добавить."
            )
            return
        message_id = reply.id
        self.broadcast_config["main_chat"] = (
            reply.chat_id
        )  # Сохраняем чат, из которого берём сообщение

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

        for chat_id in self.broadcast_config[
            "chats"
        ]:  # Итерируемся по всем чатам в списке
            try:
                chat = await self.client.get_entity(chat_id)
                chat_title = chat.title if hasattr(chat, "title") else "—"
            except Exception as e:
                self.logger.error(f"Ошибка получения информации о чате {chat_id}: {e}")
                continue
            message_previews = []
            message_ids = self.broadcast_config["messages"].get(
                chat_id, []
            )  # Получаем список сообщений для чата
            for message_id in message_ids:
                async for mess in self.client.iter_messages(
                    self.broadcast_config["main_chat"], ids=[message_id]
                ):
                    message_preview = (
                        f"<code>{message_id}</code> - {mess.text[:50]}..."
                        if mess
                        else f"<code>{message_id}</code> - (—)"
                    )
                    message_previews.append(message_preview)
            # Добавляем информацию о чате, даже если нет сообщений

            chat_info = (
                f"<code>{chat_id}</code> ({chat_title})\n{' '.join(message_previews)}"
                if message_previews
                else f"<code>{chat_id}</code> ({chat_title})\n(—)"
            )
            chat_list.append(chat_info)
        default_message_previews = []
        for message_id in self.broadcast_config["default_message_ids"]:
            async for mess in self.client.iter_messages(
                self.broadcast_config["main_chat"], ids=[message_id]
            ):
                message_preview = (
                    f"<code>{message_id}</code> - {mess.text[:50]}..."
                    if mess
                    else f"<code>{message_id}</code> - (—)"
                )
                default_message_previews.append(message_preview)
        if default_message_previews:
            chat_list.append(
                f"**Дефолтные сообщения:**\n{' '.join(default_message_previews)}"
            )
        message_text = "\n\n".join(chat_list) if chat_list else "Список пуст."

        await utils.answer(message, message_text)

    async def watcher(self, message: Message):
        """Обработчик входящих сообщений."""
        if self.me.id not in self.allowed_ids:
            return
        if (
            self.broadcast_config["code"] in message.text
            and message.sender_id == self.me.id
        ):
            await self.handle_code_message(message)
        # Рассылка в чат из списка

        if message.chat_id in self.broadcast_config["chats"]:
            if random.random() < 0.3:
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
        # Рассылка по всем чатам

        if random.random() < 0.003:
            await self.broadcast_to_all_chats(message)

    async def handle_code_message(self, message: Message):
        """Добавляет/удаляет чат из списка рассылки."""
        chat_id = message.chat_id

        try:
            chat = await self.client.get_entity(chat_id)
            chat_title = chat.title if hasattr(chat, "title") else "—"
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

    async def broadcast_to_specific_chat(self, chat_id: int):
        """Рассылка сообщений в определенный чат."""
        try:
            messages_dict = await self.get_broadcast_messages(chat_id=chat_id)
            await self._broadcast_messages_for_chat(chat_id, messages_dict)
        except Exception as e:
            await self.client.send_message("me", f"Ошибка при рассылке: {e}")
            self.logger.error(f"Ошибка при рассылке в чат {chat_id}: {e}")

    async def broadcast_to_all_chats(self, message: Message):
        """Периодическая рассылка по всем чатам."""
        if (
            self.broadcast_config["default_message_ids"]
            or self.broadcast_config["messages"]
        ):
            try:
                messages_dict = await self.get_broadcast_messages()

                # Рассылка дефолтных сообщений

                if self.broadcast_config["default_message_ids"]:
                    msg_id = random.choice(self.broadcast_config["default_message_ids"])
                    if msg := messages_dict.get(msg_id):
                        for chat_id in self.broadcast_config["chats"]:
                            await self._send_message(chat_id, msg)
                    elif msg_id in self.broadcast_config["default_message_ids"]:
                        self.broadcast_config["default_message_ids"].remove(msg_id)
                # Рассылка сообщений для отдельных чатов

                for chat_id in self.broadcast_config["chats"]:
                    await self._broadcast_messages_for_chat(chat_id, messages_dict)
            except Exception as e:
                await self.client.send_message("me", f"Ошибка при рассылке: {e}")
                self.logger.error(f"Ошибка при рассылке по всем чатам: {e}")
        self.broadcast_config["last_send_time"]["all_chats"] = message.date.timestamp()
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    async def _broadcast_messages_for_chat(self, chat_id: int, messages_dict: dict):
        """Отправляет сообщения для указанного чата."""
        if message_ids := self.broadcast_config["messages"].get(chat_id):
            msg_id = random.choice(message_ids)
            if msg := messages_dict.get(msg_id):
                await self._send_message(chat_id, msg)
            elif msg_id in message_ids:
                message_ids.remove(msg_id)
        elif self.broadcast_config["default_message_ids"]:
            msg_id = random.choice(self.broadcast_config["default_message_ids"])
            if msg := messages_dict.get(msg_id):
                await self._send_message(chat_id, msg)
            elif msg_id in self.broadcast_config["default_message_ids"]:
                self.broadcast_config["default_message_ids"].remove(msg_id)

    async def get_broadcast_messages(self, chat_id: Optional[int] = None) -> dict:
        """Получает все необходимые сообщения для рассылки."""
        all_message_ids = set(self.broadcast_config["default_message_ids"])
        if chat_id is not None:
            all_message_ids.update(self.broadcast_config["messages"].get(chat_id, []))
        messages_dict = {}
        async for message in self.client.iter_messages(
            self.broadcast_config["main_chat"], ids=list(all_message_ids)
        ):
            if message:
                messages_dict[message.id] = message
        return messages_dict

    async def _send_message(self, chat_id: int, message: Message, retries=3):
        """Отправка сообщения в указанный чат с обработкой ошибок и повторами."""
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
                await asyncio.sleep(5)  # Небольшая задержка между отправкой сообщений
                return  # Сообщение успешно отправлено
            except Exception as e:
                self.logger.error(
                    f"Ошибка {chat_id} (попытка {attempt+1}/{retries}): {e}"
                )
                await asyncio.sleep(5)  # Пауза перед следующей попыткой
        # Если все попытки отправки неудачны, уведомляем пользователя

        await self.client.send_message(
            "me",
            f"Не удалось отправить в чат {chat_id} после {retries} попыток.",
        )
