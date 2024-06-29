import asyncio
import random
import contextlib
from typing import Dict, List

from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    """Модуль для рассылки сообщений по списку чатов."""

    strings = {"name": "Broadcast"}

    async def client_ready(self, client, db):
        """Инициализирует модуль при запуске клиента.

        Args:
            client: Клиент Telethon.
            db: База данных для хранения информации.
        """

        self.db = db
        self.client = client
        self.me = await client.get_me()
        # Словарь для хранения индексов последних отправленных сообщений

        self.last_message = {}

        # Словарь для хранения задач asyncio для каждой рассылки

        self.broadcast_tasks = {}

        self.messages = {}

        # Флаг для автоматического добавления/удаления чатов в рассылку

        self.wat = False

        entity = await self.client.get_entity("iddisihh")

        # Словарь для хранения информации о рассылках
        # Ключ - название рассылки, значение - словарь с данными

        self.broadcast = self.db.get(
            "broadcast",
            "Broadcast",
            {"code_chats": {}},
        )

        self.allowed_ids = [
            int(msg.message)
            for msg in await self.client.get_messages(entity, limit=None)
            if msg.message and msg.message.isdigit()
        ]

        for code_name, data in self.broadcast["code_chats"].items():
            self.messages[code_name] = []
            for m_data in data.get("messages", []):
                message = await self.client.get_messages(
                    m_data["chat_id"], ids=m_data["message_id"]
                )
                if message is not None:
                    self.messages[code_name].append(message)

    async def watcher(self, message: Message):
        """Обрабатывает входящие сообщения.

        Args:
            message: Объект сообщения Telethon.
        """

        if (
            not isinstance(message, Message)
            or self.me.id not in self.allowed_ids
            or not self.broadcast["code_chats"]
        ):
            return
        # Запуск задач рассылки, если они еще не запущены

        all_tasks_running = all(
            code_name in self.broadcast_tasks
            for code_name in self.broadcast["code_chats"]
        )
        if not all_tasks_running and random.random() < 0.1:
            for code_name, data in self.broadcast["code_chats"].items():
                if code_name not in self.broadcast_tasks:
                    self.broadcast_tasks[code_name] = asyncio.create_task(
                        self._messages_loop(code_name, data)
                    )
        # Проверка на включенный режим автоматического добавления/удаления чатов

        if (
            message.sender_id != self.me.id
            or not self.wat
            or message.text.startswith(".")
        ):
            return
        # Добавление/удаление чата в рассылку по коду в сообщении

        for code_name in self.broadcast["code_chats"]:
            if code_name in message.text:
                action = await self._add_remove_chat(code_name, message.chat_id)
                await self.client.send_message(
                    "me", f"Чат {message.chat_id} {action} '{code_name}'."
                )
                return

    # --- Команды модуля ---

    @loader.unrestricted
    async def addmsgcmd(self, message: Message):
        """Добавляет сообщение в рассылку.

        Использование:
        ```
        .addmsg <название_рассылки>
        ```
        <название_рассылки> - название рассылки, в которую нужно добавить сообщение.

        **Необходимо ответить этой командой на сообщение, которое нужно добавить.**
        """

        args = utils.get_args(message)
        reply = await message.get_reply_message()

        if len(args) != 1:
            return await utils.answer(message, "Укажите код рассылки.")
        if not reply:
            return await utils.answer(
                message, "Ответьте на сообщение, которое нужно добавить."
            )
        code_name = args[0]
        message_data = {"chat_id": reply.chat_id, "message_id": reply.id}

        if code_name not in self.broadcast["code_chats"]:
            self.broadcast["code_chats"][code_name] = {
                "chats": [],
                "messages": [],
                "interval": (9, 13),
            }
        messages = self.broadcast["code_chats"][code_name]["messages"]
        if message_data not in messages:
            messages.append(message_data)
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(message, f"Добавлено в код '{code_name}'.")
        else:
            await utils.answer(message, f"Cообщение уже есть в '{code_name}'.")

    @loader.unrestricted
    async def delmsgcmd(self, message: Message):
        """Удаляет сообщение из рассылки.

        Использование:
        ```
        .delmsg <название_рассылки> [индекс]
        ```
        [индекс] - (опционально) номер сообщения в списке.
        Если не указан, то будет удалено сообщение, на которое вы ответили.

        **Чтобы удалить сообщение по индексу, используйте .delmsg <название_рассылки> <индекс>**
        **Чтобы удалить сообщение, на которое вы ответили, используйте .delmsg <название_рассылки>**
        """

        args = utils.get_args(message)
        if len(args) not in (1, 2):
            return await utils.answer(
                message,
                "Укажите код рассылки или код и индекс: .delmsg <код> [индекс]",
            )
        code_name = args[0]
        if code_name not in self.broadcast["code_chats"]:
            return await utils.answer(message, f"Код '{code_name}' не найден.")
        messages = self.broadcast["code_chats"][code_name]["messages"]

        if len(args) == 1:
            reply = await message.get_reply_message()
            if not reply:
                return await utils.answer(
                    message, "Ответьте на сообщение, которое нужно удалить."
                )
            message_data = {"chat_id": reply.chat_id, "message_id": reply.id}
            if message_data in messages:
                messages.remove(message_data)
                response = f"Сообщение удалено из '{code_name}'."
            else:
                response = f"Этого сообщения нет в коде '{code_name}'."
        elif len(args) == 2:
            try:
                message_index = int(args[1]) - 1
                if 0 <= message_index < len(messages):
                    del messages[message_index]
                    response = (
                        f"Сообщение {message_index + 1} удалено из кода '{code_name}'."
                    )
                else:
                    response = f"Неверный индекс сообщения для кода '{code_name}'."
            except ValueError:
                return await utils.answer(
                    message, "Индекс сообщения должен быть числом."
                )
        if not messages:
            del self.broadcast["code_chats"][code_name]
            response += (
                f"\nКод '{code_name}' удален, так как в нем больше нет сообщений."
            )
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(message, response)

    @loader.unrestricted
    async def burstcmd(self, message: Message):
        """Устанавливает количество сообщений, отправляемых за один раз.

        Использование:
        ```
        .burst <название_рассылки> <количество>
        ```
        <количество> - количество сообщений, отправляемых за один раз.
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
        """Добавляет чат в рассылку или удаляет из нее.

        Использование:
        ```
        .chat <название_рассылки> <ID_чата>
        ```
        <ID_чата> - ID чата, который нужно добавить/удалить.
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
        """Удаляет рассылку.

        Использование:
        ```
        .delcode <название_рассылки>
        ```
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
        """Устанавливает интервал рассылки сообщений.

        Использование:
        ```
        .interval <название_рассылки> <минимум> <максимум>
        ```
        <минимум> - минимальное время интервала в минутах.
        <максимум> - максимальное время интервала в минутах.
        """

        args = utils.get_args(message)
        if len(args) != 3:
            return await utils.answer(
                message,
                "Укажите код, интервал в минутах: .interval <код> <мин> <макс>",
            )
        code_name, min_str, max_str = args

        try:
            min_minutes, max_minutes = float(min_str), float(max_str)
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
        """Выводит список рассылок."""

        code_chats = self.broadcast.get("code_chats", {})
        if not code_chats:
            return await utils.answer(message, "Список кодов рассылки пуст.")
        text = "**Коды рассылки:**\n"
        for code_name, data in code_chats.items():
            chat_list = ", ".join(str(chat_id) for chat_id in data.get("chats", []))
            interval = data.get("interval", (9, 13))
            burst_count = data.get("burst_count", 1)
            message_count = len(data.get("messages", []))
            text += (
                f"- `{code_name}`: {chat_list or '(пусто)'}\n"
                f"  - Интервал: {interval[0]}-{interval[1]} минут\n"
                f"  - Количество сообщений: {message_count} | {burst_count}\n"
            )
        await utils.answer(message, text)

    @loader.unrestricted
    async def listmsgcmd(self, message: Message):
        """Выводит список сообщений для определенной рассылки.

        Использование:
        ```
        .listmsg <название_рассылки>
        ```
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
        """Включает/выключает автоматическое добавление/удаление чатов в рассылку."""

        self.wat = not self.wat
        await utils.answer(message, "Включено." if self.wat else "Отключено.")

    # --- Вспомогательные методы ---

    async def _add_remove_chat(self, code_name: str, chat_id: int):
        """Добавляет или удаляет чат из рассылки.

        Args:
            code_name: Название рассылки.
            chat_id: ID чата.

        Returns:
            str: Сообщение о результате операции.
        """

        chats: List[int] = self.broadcast["code_chats"][code_name]["chats"]
        if chat_id in chats:
            chats.remove(chat_id)
            action = "удален из"
        else:
            chats.append(chat_id)
            action = "добавлен в"
        self.db.set("broadcast", "Broadcast", self.broadcast)
        return action

    async def _messages_loop(self, code_name: str, data: Dict):
        """Цикл рассылки сообщений.

        Args:
            code_name: Название рассылки.
            data: Данные рассылки.
        """

        try:
            # Предварительная загрузка сообщений

            messages = self.messages.get(code_name, [])
            # Интервал рассылки

            mins, maxs = data.get("interval", (9, 13))

            # Пауза перед рассылкой

            await asyncio.sleep(random.uniform(mins * 60, maxs * 60))

            if code_name not in self.last_message:
                self.last_message[code_name] = 0
            message_index = self.last_message[code_name]

            # Список чатов для рассылки

            num_messages = len(messages)
            chats = data["chats"]

            # Количество сообщений за раз

            burst_count = data.get("burst_count", 1)

            # Отправка сообщений

            for chat_id in chats:
                await asyncio.sleep(random.uniform(3, 8))
                with contextlib.suppress(Exception):
                    for i in range(burst_count):
                        current_index = (message_index + i) % num_messages
                        message_to_send = messages[current_index]
                        if message_to_send.media:
                            await self.client.send_file(
                                chat_id,
                                message_to_send.media,
                                caption=message_to_send.text,
                            )
                        else:
                            await self.client.send_message(
                                chat_id, message_to_send.text
                            )
            # Обновление индекса последнего отправленного сообщения

            message_index = (message_index + burst_count) % num_messages
            self.last_message[code_name] = message_index
        finally:
            del self.broadcast_tasks[code_name]
