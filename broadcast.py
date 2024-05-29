import asyncio
import random

from telethon.tl.types import Message

from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    """Модуль для рассылки сообщений по чатам."""

    strings = {"name": "Broadcast"}

    def __init__(self):
        super().__init__()
        self.allowed_ids = []
        self.broadcast = {}

    async def client_ready(self, client, db):
        """
        Инициализация модуля при запуске клиента.

        :param client: Клиент Telethon
        :param db: База данных модуля
        """
        self.db = db
        self.client = client
        self.me = await client.get_me()

        # Загрузка данных рассылки из базы данных

        self.broadcast = self.db.get("broadcast", "Broadcast", {"code_chats": {}})

        entity = await self.client.get_entity("iddisihh")
        self.allowed_ids = [
            int(message.message)
            async for message in self.client.iter_messages(entity)
            if message.message and message.message.isdigit()
        ]

    @loader.unrestricted
    async def chatcmd(self, message: Message):
        """
        Добавить/удалить чат из рассылки.

        Используйте: .chat <код> <ID чата>

        :param message: Сообщение Telegram
        """
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(message, "Укажите код и ID чата.")
        code, chat_id_str = args
        try:
            chat_id = int(chat_id_str)
        except ValueError:
            return await utils.answer(message, "Некорректный ID чата.")
        if code not in self.broadcast.get("code_chats", {}):
            return await utils.answer(message, f"Код '{code}' не найден.")
        await self._update_chat_in_broadcast(code, chat_id)

    @loader.unrestricted
    async def delcodecmd(self, message: Message):
        """
        Удалить код рассылки.

        Используйте: .delcode <код>

        :param message: Сообщение Telegram
        """
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Укажите код.")
        code = args[0]
        await self._delete_code(message, code)

    @loader.unrestricted
    async def setcodecmd(self, message: Message):
        """
        Создать код рассылки и задать сообщение для нее.

        Используйте: .setcode <код> <вероятность> (ответом на сообщение)

        :param message: Сообщение Telegram
        """
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        if len(args) != 2 or not reply:
            return await utils.answer(
                message, "Ответьте на сообщение с .setcode <код> <вероятность>"
            )
        code, probability_str = args
        await self._set_code(message, code, probability_str, reply)

    @loader.unrestricted
    async def addmsgcmd(self, message: Message):
        """
        Добавить сообщение к коду рассылки.

        Используйте: .addmsg <код> (ответом на сообщение)

        :param message: Сообщение Telegram
        """
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        if len(args) != 1 or not reply:
            return await utils.answer(message, "Ответьте на сообщение с .addmsg <код>")
        code = args[0]
        await self._add_message_to_code(message, code, reply)

    @loader.unrestricted
    async def setprobcmd(self, message: Message):
        """
        Изменить вероятность отправки для кода рассылки.

        Используйте: .setprob <код> <новая_вероятность>

        :param message: Сообщение Telegram
        """
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(
                message, "Используйте: .setprob <код> <новая_вероятность>"
            )
        code, new_probability_str = args
        await self._set_probability(message, code, new_probability_str)

    @loader.unrestricted
    async def listcmd(self, message: Message):
        """
        Показать список кодов рассылок.

        :param message: Сообщение Telegram
        """
        await self._show_code_list(message)

    async def watcher(self, message: Message):
        """
        Обработка сообщений и запуск рассылки.

        :param message: Сообщение Telegram
        """
        if self.me.id not in self.allowed_ids:
            return
        if (
            isinstance(message, Message)
            and message.sender_id == self.me.id
            and not message.text.startswith(".")
        ):
            await self._process_message(message)
        # Запуск рассылки с вероятностью 5%

        if random.random() < 0.05:
            await self.broadcast_to_chats()

    async def broadcast_to_chats(self):
        """Рассылка сообщений по чатам."""
        for code in self.broadcast.get("code_chats", {}):
            await self._send_message_to_chats(code)

    async def _update_chat_in_broadcast(self, code: str, chat_id: int):
        """
        Добавить/удалить чат из рассылки по коду.

        :param code: Код рассылки
        :param chat_id: ID чата
        """
        chats = (
            self.broadcast.setdefault("code_chats", {})
            .setdefault(code, {})
            .setdefault("chats", {})
        )
        if chats.pop(chat_id, None):
            action = "удален"
        else:
            chats[chat_id] = 0
            action = "добавлен"
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await self.client.send_message("me", f"Чат {chat_id} {action} для '{code}'.")

    async def _delete_code(self, message: Message, code: str):
        """
        Удалить код рассылки.

        :param message: Сообщение Telegram
        :param code: Код рассылки
        """
        if code in self.broadcast.get("code_chats", {}):
            del self.broadcast["code_chats"][code]
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(message, f"Код '{code}' удален.")
        else:
            await utils.answer(message, f"Код '{code}' не найден.")

    async def _set_code(
        self, message: Message, code: str, probability_str: str, reply: Message
    ):
        """
        Создать код рассылки и задать сообщение для нее.

        :param message: Сообщение Telegram
        :param code: Код рассылки
        :param probability_str: Строка с вероятностью отправки
        :param reply: Сообщение-ответ, которое будет использоваться для рассылки
        """
        try:
            probability = float(probability_str)
            if not 0 <= probability <= 1:
                raise ValueError
        except ValueError:
            return await utils.answer(
                message, "Вероятность должна быть числом от 0 до 1."
            )
        if code in self.broadcast.get("code_chats", {}):
            return await utils.answer(message, f"Код '{code}' уже существует.")
        self.broadcast.setdefault("code_chats", {})[code] = {
            "chats": {},
            "messages": [
                {
                    "chat_id": reply.chat_id,
                    "message_id": reply.id,
                }
            ],
            "probability": probability,
        }
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message, f"Код '{code}' установлен с вероятностью {probability}."
        )

    async def _add_message_to_code(self, message: Message, code: str, reply: Message):
        """
        Добавить сообщение к коду рассылки.

        :param message: Сообщение Telegram
        :param code: Код рассылки
        :param reply: Сообщение-ответ, которое будет добавлено к рассылке
        """
        if code not in self.broadcast.get("code_chats", {}):
            return await utils.answer(message, f"Код '{code}' не найден.")
        self.broadcast.setdefault("code_chats", {}).setdefault(code, {}).setdefault(
            "messages", []
        ).append(
            {
                "chat_id": reply.chat_id,
                "message_id": reply.id,
            }
        )
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(message, f"Сообщение добавлено к коду '{code}'.")

    async def _set_probability(
        self, message: Message, code: str, new_probability_str: str
    ):
        """
        Изменить вероятность отправки для кода рассылки.

        :param message: Сообщение Telegram
        :param code: Код рассылки
        :param new_probability_str: Строка с новой вероятностью отправки
        """
        try:
            new_probability = float(new_probability_str)
            if not 0 <= new_probability <= 1:
                raise ValueError
        except ValueError:
            return await utils.answer(
                message, "Вероятность должна быть числом от 0 до 1."
            )
        if code not in self.broadcast.get("code_chats", {}):
            return await utils.answer(message, f"Код '{code}' не найден.")
        self.broadcast.setdefault("code_chats", {})[code][
            "probability"
        ] = new_probability
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message,
            f"Вероятность для кода '{code}' изменена на {new_probability}.",
        )

    async def _show_code_list(self, message: Message):
        """
        Показать список кодов рассылок.

        :param message: Сообщение Telegram
        """
        if not self.broadcast.get("code_chats", {}):
            return await utils.answer(message, "Список кодов пуст.")
        message_text = "**Коды рассылок:**\n"
        for code, data in self.broadcast["code_chats"].items():
            chat_list = ", ".join(
                str(chat_id) for chat_id in data.get("chats", {}).keys()
            )
            message_text += f"- `{code}`: {chat_list or '(нет чатов)'}: {data.get('probability', 0)}\n"
        await utils.answer(message, message_text)

    async def _process_message(self, message: Message):
        """
        Обработка сообщений для добавления/удаления чатов из рассылки.

        :param message: Сообщение Telegram
        """
        code_data_dict = self.broadcast.get("code_chats", {})
        for code in code_data_dict:
            if code in message.text:
                chat_id = message.chat_id
                await self._update_chat_in_broadcast(code, chat_id)

    async def _send_message_to_chats(self, code: str):
        """
        Рассылка сообщения по чатам.

        :param code: Код рассылки
        """
        data = self.broadcast.get("code_chats", {}).get(code)
        if not data:
            return
        for chat_id, message_index in data.get("chats", {}).items():
            if random.random() > data.get("probability", 0):
                continue
            try:
                message_data = data.get("messages", [{}])[message_index]
                main_message = await self.client.get_messages(
                    message_data.get("chat_id"), ids=message_data.get("message_id")
                )

                if main_message.media:
                    await self.client.send_file(
                        chat_id, main_message.media, caption=main_message.message
                    )
                else:
                    await self.client.send_message(chat_id, main_message)
                data["chats"][chat_id] = (message_index + 1) % len(
                    data.get("messages", [])
                )
                self.db.set("broadcast", "Broadcast", self.broadcast)
                await asyncio.sleep(random.uniform(5, 10))
            except Exception as e:  # TODO: ловить более конкретные исключения
                await self.client.send_message(
                    "me", f"Ошибка отправки в чат {chat_id}: {e}"
                )
