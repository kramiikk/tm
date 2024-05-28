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
        """Инициализация модуля при запуске клиента."""
        self.db = db
        self.client = client
        self.me = await client.get_me()

        self.broadcast = self.db.get("broadcast", "Broadcast", {"code_chats": {}})

        entity = await self.client.get_entity("iddisihh")
        self.allowed_ids = [
            int(message.message)
            async for message in self.client.iter_messages(entity)
            if message.message and message.message.isdigit()
        ]

    @loader.unrestricted
    async def chatcmd(self, message: Message):
        """Добавить/удалить чат из рассылки.

        Используйте: .chat <код> <ID чата>
        """
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(message, "Укажите код и ID чата.")
        code, chat_id_str = args
        try:
            chat_id = int(chat_id_str)
        except ValueError:
            return await utils.answer(message, "Некорректный ID чата.")
        if code not in self.broadcast["code_chats"]:
            return await utils.answer(message, f"Код '{code}' не найден.")
        await self._update_chat_in_broadcast(code, chat_id)

    @loader.unrestricted
    async def delcodecmd(self, message: Message):
        """Удалить код рассылки.

        Используйте: .delcode <код>
        """
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Укажите код.")
        code = args[0]
        await self._delete_code(message, code)

    @loader.unrestricted
    async def setcodecmd(self, message: Message):
        """Создать код рассылки и задать сообщение для нее.

        Используйте: .setcode <код> <вероятность> (ответом на сообщение)
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
    async def setprobcmd(self, message: Message):
        """Изменить вероятность отправки для кода рассылки.

        Используйте: .setprob <код> <новая_вероятность>
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
        """Показать список кодов рассылок."""
        await self._show_code_list(message)

    async def watcher(self, message: Message):
        """Обработка сообщений и запуск рассылки."""
        if self.me.id not in self.allowed_ids:
            return
        if message.sender_id == self.me.id and not message.text.startswith("."):
            await self._process_message(message)
        if random.random() < 0.05:
            await self.broadcast_to_chats()

    async def broadcast_to_chats(self):
        """Рассылка сообщений по чатам."""
        for code in self.broadcast["code_chats"]:
            await self._send_message_to_chats(code)
        self.db.set("broadcast", "Broadcast", self.broadcast)

    async def _update_chat_in_broadcast(self, code: str, chat_id: int):
        """Добавить/удалить чат из рассылки по коду."""
        chats = self.broadcast["code_chats"][code]["chats"]
        if chat_id in chats:
            chats.remove(chat_id)
            action = "удален"
        else:
            chats.append(chat_id)
            action = "добавлен"
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await self.client.send_message("me", f"Чат {chat_id} {action} для '{code}'.")

    async def _delete_code(self, message: Message, code: str):
        """Удалить код рассылки."""
        if code in self.broadcast["code_chats"]:
            del self.broadcast["code_chats"][code]
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(message, f"Код '{code}' удален.")
        else:
            await utils.answer(message, f"Код '{code}' не найден.")

    async def _set_code(
        self, message: Message, code: str, probability_str: str, reply: Message
    ):
        """Создать код рассылки и задать сообщение для нее."""
        try:
            probability = float(probability_str)
            if not 0 <= probability <= 1:
                raise ValueError
        except ValueError:
            return await utils.answer(
                message, "Вероятность должна быть числом от 0 до 1."
            )
        if code in self.broadcast["code_chats"]:
            return await utils.answer(message, f"Код '{code}' уже существует.")
        self.broadcast["code_chats"][code] = {
            "chats": [],
            "main_chat": reply.chat_id,
            "message_id": reply.id,
            "probability": probability,
        }
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message, f"Код '{code}' установлен с вероятностью {probability}."
        )

    async def _set_probability(
        self, message: Message, code: str, new_probability_str: str
    ):
        """Изменить вероятность отправки для кода рассылки."""
        try:
            new_probability = float(new_probability_str)
            if not 0 <= new_probability <= 1:
                raise ValueError
        except ValueError:
            return await utils.answer(
                message, "Вероятность должна быть числом от 0 до 1."
            )
        if code not in self.broadcast["code_chats"]:
            return await utils.answer(message, f"Код '{code}' не найден.")
        self.broadcast["code_chats"][code]["probability"] = new_probability
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message,
            f"Вероятность для кода '{code}' изменена на {new_probability}.",
        )

    async def _show_code_list(self, message: Message):
        """Показать список кодов рассылок."""
        if not self.broadcast["code_chats"]:
            return await utils.answer(message, "Список кодов пуст.")
        message_text = "**Коды рассылок:**\n"
        for code, data in self.broadcast["code_chats"].items():
            chat_list = ", ".join(str(chat_id) for chat_id in data["chats"])
            message_text += (
                f"- `{code}`: {chat_list or '(нет чатов)'}: {data['probability']}\n"
            )
        await utils.answer(message, message_text)

    async def _process_message(self, message: Message):
        """Обработка сообщений для добавления/удаления чатов из рассылки."""
        code_data_dict = self.broadcast["code_chats"]
        for code in code_data_dict:
            if code in message.text:
                chat_id = message.chat_id
                await self._update_chat_in_broadcast(code, chat_id)

    async def _send_message_to_chats(self, code: str):
        """Рассылка сообщения по чатам."""
        data = self.broadcast["code_chats"][code]
        main_message = await self.client.get_messages(
            data["main_chat"], ids=data["message_id"]
        )
        for chat_id in data.get("chats", []):
            if random.random() < data["probability"]:
                try:
                    await self.client.send_message(chat_id, main_message)
                    await asyncio.sleep(random.uniform(5, 10))
                except Exception as e:
                    await self.client.send_message(
                        "me", f"Ошибка отправки в чат {chat_id}: {e}"
                    )
