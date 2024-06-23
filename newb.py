import asyncio
import contextlib
import random
from typing import Dict, List

from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    """Модуль для рассылки сообщений по списку чатов с определенным кодом."""

    strings = {"name": "Broadcast"}

    async def client_ready(self, client, db):
        self.db = db
        self.client = client
        self.me = await client.get_me()
        self.broadcasting = False
        self.wat = False
        self.broadcast = self.db.get(
            "broadcast",
            "Broadcast",
            {"code_chats": {}},
        )
        self.last_message = {}

        entity = await self.client.get_entity("iddisihh")
        self.allowed_ids = [
            int(msg.message)
            for msg in await self.client.get_messages(entity, limit=None)
            if msg.message and msg.message.isdigit()
        ]

    async def watcher(self, message: Message):
        if (
            not isinstance(message, Message)
            or self.me.id not in self.allowed_ids
            or not self.broadcast["code_chats"]
        ):
            return
        if not self.broadcasting:
            asyncio.create_task(self._broadcast_loop())
        if (
            message.sender_id != self.me.id
            or not self.wat
            or message.text.startswith(".")
        ):
            return
        for code_name in self.broadcast["code_chats"]:
            if code_name in message.text:
                action = await self._add_remove_chat(code_name, message.chat_id)
                await self.client.send_message(
                    "me", f"Чат {message.chat_id} {action} '{code_name}'."
                )
                return

    async def _broadcast_loop(self):
        """Создание задач для рассылки сообщений."""
        if self.broadcasting:
            return
        self.broadcasting = True

        # Создание задач для рассылки по каждому коду

        tasks = [
            asyncio.create_task(
                self._messages_loop(code_name, self.broadcast["code_chats"][code_name])
            )
            for code_name in self.broadcast["code_chats"]
        ]

        # Запуск задач и ожидание их завершения

        await asyncio.gather(*tasks)
        self.broadcasting = False

    async def _messages_loop(self, code_name: str, data: Dict):
        """Цикл рассылки сообщений для заданного кода."""
        mins, maxs = data.get("interval", (9, 13))
        await asyncio.sleep(random.uniform(mins * 60, maxs * 60))

        if code_name not in self.last_message:
            self.last_message[code_name] = 0
        message_index = self.last_message[code_name]

        messages = data["messages"]
        num_messages = len(messages)

        chats = data["chats"]
        burst_count = data.get("burst_count", 1)

        for chat_id in chats:
            with contextlib.suppress(Exception):
                for i in range(burst_count):
                    current_index = (message_index + i) % num_messages
                    message_data = messages[current_index]
                    message = await self.client.get_messages(
                        message_data["chat_id"], ids=message_data["message_id"]
                    )
                    if message is None:
                        continue
                    if message.media:
                        await self.client.send_file(
                            chat_id, message.media, caption=message.text
                        )
                    else:
                        await self.client.send_message(chat_id, message.text)
        message_index = (message_index + burst_count) % num_messages
        self.last_message[code_name] = message_index

    # --- Команды модуля ---

    @loader.unrestricted
    async def addmsgcmd(self, message: Message):
        """
        Добавить сообщение в код рассылки.
        Если кода не существует, он будет создан.

        Используйте команду, ответив на сообщение,
        которое нужно добавить в рассылку.

        Пример:
        .addmsg <код>
        """
        await self._message_handler(message, "addmsg")

    @loader.unrestricted
    async def delmsgcmd(self, message: Message):
        """
        Удалить сообщение из кода рассылки.
        Если это последнее сообщение в коде, код будет удален.

        Используйте команду, ответив на сообщение,
        которое нужно удалить из рассылки.

        Пример:
        .delmsg <код>
        """
        await self._message_handler(message, "delmsg")

    @loader.unrestricted
    async def burstcmd(self, message: Message):
        """
        Установить количество сообщений, отправляемых за раз (burst).

        Пример:
        .burst <код> <количество>
        """
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(
                message,
                "Укажите код и количество сообщений: .burst <код> <количество>",
            )
        code_name = args[0]
        try:
            burst_count = int(args[1])
            if burst_count <= 0:
                raise ValueError
        except ValueError:
            return await utils.answer(
                message, "Количество сообщений должно быть положительным числом."
            )
        if code_name not in self.broadcast["code_chats"]:
            return await utils.answer(message, f"Код '{code_name}' не найден.")
        self.broadcast["code_chats"][code_name]["burst_count"] = burst_count
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message,
            f"Для '{code_name}' будет отправлено {burst_count} сообщений за раз.",
        )

    @loader.unrestricted
    async def chatcmd(self, message: Message):
        """
        Добавить/удалить чат.

        Пример:
        .chat <код> <id чата>
        """
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(
                message, "Укажите код рассылки и ID чата: .chat <код> <id>"
            )
        code_name = args[0]
        try:
            chat_id = int(args[1])
        except ValueError:
            return await utils.answer(message, "ID чата должен быть числом.")
        if code_name not in self.broadcast["code_chats"]:
            return await utils.answer(message, f"Код '{code_name}' не найден.")
        action = await self._add_remove_chat(code_name, chat_id)
        await utils.answer(message, f"Чат {chat_id} {action} '{code_name}'.")

    @loader.unrestricted
    async def delcodecmd(self, message: Message):
        """
        Удалить код рассылки.

        Пример:
        .delcode <код>
        """
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Укажите код: .delcode <код>")
        code_name = args[0]

        if code_name in self.broadcast["code_chats"]:
            del self.broadcast["code_chats"][code_name]
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(message, f"Код рассылки '{code_name}' удален.")
        else:
            await utils.answer(message, f"Код рассылки '{code_name}' не найден.")

    @loader.unrestricted
    async def intervalcmd(self, message: Message):
        """
        Установить интервал рассылки для кода.

        Пример:
        .interval <код> <мин> <макс>
        """
        args = utils.get_args(message)
        if len(args) != 3:
            return await utils.answer(
                message,
                "Укажите код, интервал в минутах: .interval <код> <мин> <макс>",
            )
        code_name, min_str, max_str = args

        try:
            min_minutes, max_minutes = int(min_str), int(max_str)
            if min_minutes < 0 or max_minutes <= 0 or min_minutes >= max_minutes:
                raise ValueError
        except ValueError:
            return await utils.answer(message, "Неверные значения интервала.")
        if code_name not in self.broadcast["code_chats"]:
            return await utils.answer(message, f"Код '{code_name}' не найден.")
        self.broadcast["code_chats"][code_name]["interval"] = (
            min_minutes,
            max_minutes,
        )
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message,
            f"Интервал '{code_name}' {min_minutes}-{max_minutes} минут.",
        )

    @loader.unrestricted
    async def listcmd(self, message: Message):
        """Показать список кодов рассылки."""
        code_chats = self.broadcast.get("code_chats", {})
        if not code_chats:
            return await utils.answer(message, "Список кодов рассылки пуст.")
        text = "**Коды рассылки:**\n"
        for code_name, data in code_chats.items():
            chat_list = ", ".join(str(chat_id) for chat_id in data.get("chats", []))
            text += f"- `{code_name}`: {chat_list or '(пусто)'}\n"
        await utils.answer(message, text)

    @loader.unrestricted
    async def listmsgcmd(self, message: Message):
        """Показать список сообщений для кода рассылки.

        Пример:
        .listmsg <код>
        """
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Укажите код: .listmsg <код>")
        code_name = args[0]

        messages = (
            self.broadcast.get("code_chats", {}).get(code_name, {}).get("messages", [])
        )
        if not messages:
            return await utils.answer(
                message, f"Нет сообщений для кода рассылки '{code_name}'."
            )
        message_text = f"**Сообщения для кода '{code_name}':**\n"
        for i, m_data in enumerate(messages):
            message_text += f"{i+1}. {m_data['chat_id']}({m_data['message_id']})\n"
        await utils.answer(message, message_text)

    @loader.unrestricted
    async def watcmd(self, message: Message):
        """
        Включить/отключить добавление чатов.

        Если режим включен, то при отправке сообщения с кодом рассылки
        в чат, этот чат будет автоматически добавлен/удален из списка
        чатов для данного кода рассылки.
        """
        self.wat = not self.wat
        await utils.answer(message, "Включено." if self.wat else "Отключено.")

    # --- Вспомогательные методы ---

    async def _add_remove_chat(self, code_name: str, chat_id: int):
        chats: List[int] = self.broadcast["code_chats"][code_name]["chats"]
        if chat_id in chats:
            chats.remove(chat_id)
            action = "удален из"
        else:
            chats.append(chat_id)
            action = "добавлен в"
        self.db.set("broadcast", "Broadcast", self.broadcast)
        return action

    async def _add_message_to_code(
        self, message: Message, code_name: str, reply: Message
    ):
        if code_name not in self.broadcast["code_chats"]:
            # Создание кода, если его не существует

            self.broadcast["code_chats"][code_name] = {
                "chats": [],
                "messages": [],
                "interval": (9, 13),
            }
        messages = self.broadcast["code_chats"][code_name]["messages"]
        message_data = {"chat_id": reply.chat_id, "message_id": reply.id}
        if message_data not in messages:
            messages.append(message_data)
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(message, f"Добавлено в код '{code_name}'.")
        else:
            await utils.answer(message, f"Cообщение уже есть в '{code_name}'.")

    async def _delete_message_from_code(
        self, message: Message, code_name: str, reply: Message = None
    ):
        """
        Удаляет сообщение из кода рассылки.

        :param message: Сообщение, являющееся командой.
        :param code_name: Код рассылки.
        :param reply: Сообщение, на которое ответили командой.
        """
        if code_name not in self.broadcast["code_chats"]:
            return await utils.answer(message, f"Код '{code_name}' не найден.")
        messages = self.broadcast["code_chats"][code_name]["messages"]

        if reply:
            # Удаление по реплаю

            message_data = {"chat_id": reply.chat_id, "message_id": reply.id}
        else:
            # Удаление по аргументу (ID сообщения)

            args = utils.get_args_raw(message)
            if not args:
                return await utils.answer(message, "Укажите ID для удаления.")
            try:
                message_id = int(args)
            except ValueError:
                return await utils.answer(message, "Неверный ID сообщения.")
            message_data = {"chat_id": message.chat_id, "message_id": message_id}
        if message_data in messages:
            messages.remove(message_data)
            if not messages:
                del self.broadcast["code_chats"][code_name]
                await utils.answer(
                    message,
                    f"Код '{code_name}' удален, так как в нем больше нет сообщений.",
                )
            else:
                await utils.answer(message, f"Сообщение удалено из '{code_name}'.")
            self.db.set("broadcast", "Broadcast", self.broadcast)
        else:
            await utils.answer(message, f"Этого сообщения нет в коде '{code_name}'.")

    async def _message_handler(self, message: Message, command: str):
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        if len(args) != 1:
            return await utils.answer(message, "Укажите код рассылки.")
        if not reply:
            return await utils.answer(
                message, "Ответьте на сообщение, которое нужно добавить/удалить."
            )
        code_name = args[0]

        if command == "addmsg":
            await self._add_message_to_code(message, code_name, reply)
        elif command == "delmsg":
            if code_name in self.broadcast["code_chats"]:
                await self._delete_message_from_code(message, code_name, reply)
            else:
                return await utils.answer(message, f"Код '{code_name}' не найден.")
