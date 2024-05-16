import asyncio
import random
from typing import Optional
from contextlib import suppress
from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    """Модуль для рассылки сообщений в чаты"""

    strings = {"name": "Broadcast"}

    async def client_ready(self, client, db):
        """Инициализирует модуль при запуске клиента."""
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

        try:
            channel_entity = await self.client.get_entity("iddisihh")
            self.allowed_ids = []
            async for message in self.client.iter_messages(channel_entity):
                if message.message and message.message.isdigit():
                    self.allowed_ids.append(int(message.message))
        except ValueError:
            self.allowed_ids = []

    @loader.unrestricted
    async def setmsgcmd(self, message: Message):
        """Устанавливает сообщение для рассылки."""
        args = utils.get_args_raw(message)
        reply_msg = await message.get_reply_message()
        if not reply_msg:
            await utils.answer(
                message, "Ответьте на сообщение, которое хотите добавить для рассылки."
            )
            return
        message_id = reply_msg.id

        self.broadcast_config["main_chat"] = reply_msg.chat_id

        if args:
            try:
                chat_id = int(args)
            except ValueError:
                await utils.answer(message, "Неверный формат ID чата")
                return
            self.broadcast_config["messages"].setdefault(chat_id, []).append(message_id)
            await utils.answer(
                message, f"Сообщение добавлено в список для рассылки в чат {chat_id}"
            )
        else:
            self.broadcast_config["message"] = message_id
            await utils.answer(
                message, "Сообщение установлено как дефолтное для рассылки во все чаты."
            )
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)

    @loader.unrestricted
    async def setintcmd(self, message: Message):
        """Устанавливает интервал рассылки (в минутах)."""
        args = utils.get_args_raw(message)
        if not args:
            current_interval = self.broadcast_config["interval"]
            await utils.answer(
                message, f"Текущий интервал рассылки: {current_interval} минут."
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
        """Устанавливает кодовую фразу для добавления/удаления чата."""
        args = utils.get_args_raw(message)
        if not args:
            current_code = self.broadcast_config["code"]
            await utils.answer(
                message, f"Текущая кодовая фраза: <code>{current_code}</code>"
            )
            return
        new_code = args  # Извлекаем новую кодовую фразу
        self.broadcast_config["code"] = new_code
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await utils.answer(
            message, f"Кодовая фраза установлена: <code>{new_code}</code>"
        )

    @loader.unrestricted
    async def listchatscmd(self, message: Message):
        """Выводит список чатов для рассылки."""
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
    async def addchatcmd(self, message: Message):
        """Добавляет чат в список рассылки."""
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
        """Удаляет чат из списка рассылки."""
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
    async def delmsgcmd(self, message: Message):
        """Удаляет сообщение из списка для рассылки."""
        reply_msg = await message.get_reply_message()
        if not reply_msg:
            await utils.answer(
                message, "Ответьте на сообщение, которое хотите удалить."
            )
            return
        message_id = reply_msg.id
        removed_chats = []

        for chat_id, message_ids in self.broadcast_config["messages"].items():
            if message_id in message_ids:
                message_ids.remove(message_id)
                removed_chats.append(chat_id)
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
    async def listmsgscmd(self, message: Message):
        """Выводит список сообщений для рассылки в указанном чате."""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(
                message,
                "Неверное количество аргументов. Используйте: .listmsgs <chat_id>",
            )
            return
        try:
            chat_id = int(args)
        except ValueError:
            await utils.answer(message, "Неверный формат ID чата")
            return
        if chat_id in self.broadcast_config["messages"]:
            message_list = []
            for message_id in self.broadcast_config["messages"][chat_id]:
                try:
                    msg = await self.client.get_messages(
                        self.broadcast_config["main_chat"], ids=message_id
                    )
                    if msg:
                        message_list.append(
                            f"<code>{message_id}</code> - {msg.text[:50]}..."
                        )
                    else:
                        message_list.append(
                            f"<code>{message_id}</code> - (Сообщение не найдено)"
                        )
                except Exception:
                    message_list.append(
                        f"<code>{message_id}</code> - (Ошибка получения сообщения)"
                    )
            await utils.answer(
                message,
                (
                    "\n".join(message_list)
                    if message_list
                    else f"Нет сообщений для чата {chat_id}"
                ),
            )
        else:
            await utils.answer(
                message,
                f"Чат {chat_id} не найден в списке рассылки или не имеет сообщений",
            )

    @loader.unrestricted
    async def clearmsgscmd(self, message: Message):
        """Очищает список сообщений для рассылки в указанном чате."""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(
                message,
                "Неверное количество аргументов. Используйте: .clearmsgs <chat_id>",
            )
            return
        try:
            chat_id = int(args)
        except ValueError:
            await utils.answer(message, "Неверный формат ID чата")
            return
        if chat_id in self.broadcast_config["messages"]:
            del self.broadcast_config["messages"][chat_id]
            self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
            await utils.answer(message, f"Список сообщений для чата {chat_id} очищен.")
        else:
            await utils.answer(message, f"Чат {chat_id} не найден в списке рассылки.")

    async def watcher(self, message: Message):
        """Обрабатывает входящие сообщения."""
        if not isinstance(message, Message) or self.me.id not in self.allowed_ids:
            return
        if (
            self.broadcast_config["code"] in message.text
            and message.sender_id == self.me.id
        ):
            await self.handle_code_message(message)
        if random.randint(1, 20) == 1:
            await self.broadcast_messages(message)

    async def handle_code_message(self, message: Message):
        """Обрабатывает сообщение с кодовой фразой."""
        chat_id = message.chat_id
        if chat_id in self.broadcast_config["chats"]:
            self.broadcast_config["chats"].remove(chat_id)
            action = "удален"
        else:
            self.broadcast_config["chats"].append(chat_id)
            action = "добавлен"
        self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
        await self.client.send_message(
            "me", f"Чат <code>{chat_id}</code> {action} в список рассылки"
        )

    async def broadcast_messages(self, message: Message):
        """Рассылает сообщения с заданным интервалом."""
        elapsed_time = (
            message.date.timestamp() - self.broadcast_config["last_send_time"]
        )
        interval = self.broadcast_config["interval"] * 60
        if elapsed_time < interval:
            return
        if not self.broadcast_config.get("message") or not len(
            self.broadcast_config["chats"]
        ):
            return
        try:
            await self.send_messages_to_chats()
        except Exception as e:
            await self.client.send_message("me", f"Ошибка: {e}")
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
            if msg is None:
                self.remove_invalid_message_id(chat_id, msg_id)
                continue
            try:
                if msg.media:
                    await self.client.send_file(chat_id, msg.media, caption=msg.text)
                else:
                    await self.client.send_message(chat_id, msg.text)
                await asyncio.sleep(5)
            except Exception as e:
                await self.client.send_message(
                    "me", f"Ошибка при отправке сообщения в чат {chat_id}: {e}"
                )

    def get_message_id(self, chat_id: int) -> Optional[int]:
        """Возвращает ID сообщения для рассылки в указанный чат.
        Приоритет отдается дефолтному сообщению, если оно установлено.
        """
        if self.broadcast_config.get("message"):
            return self.broadcast_config["message"]
        elif chat_id in self.broadcast_config["messages"]:
            return random.choice(self.broadcast_config["messages"][chat_id])
        else:
            return None

    def remove_invalid_message_id(self, chat_id: int, message_id: int):
        """Удаляет ID несуществующего сообщения из списка."""
        if chat_id in self.broadcast_config["messages"]:
            with suppress(ValueError):
                self.broadcast_config["messages"][chat_id].remove(message_id)
                self.db.set("broadcast_config", "Broadcast", self.broadcast_config)
