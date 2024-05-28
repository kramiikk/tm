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
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, "Укажите код и ID чата.")
        code, chat_id_str = args.split(maxsplit=1)
        try:
            chat_id = int(chat_id_str)
        except ValueError:
            return await utils.answer(message, "Некорректный ID чата.")
        if code not in self.broadcast["code_chats"]:
            return await utils.answer(message, f"Код '{code}' не найден.")
        chats = self.broadcast["code_chats"][code]["chats"]
        if chat_id in chats:
            chats.remove(chat_id)
            action = "удален"
        else:
            chats.append(chat_id)
            action = "добавлен"
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(message, f"Чат {chat_id} {action} из рассылки '{code}'.")

    @loader.unrestricted
    async def delcodecmd(self, message: Message):
        """Удалить код рассылки.

        Используйте: .delcode <код>
        """
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, "Укажите код.")
        code = args.strip()

        if code in self.broadcast["code_chats"]:
            del self.broadcast["code_chats"][code]
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(message, f"Код '{code}' удален.")
        else:
            await utils.answer(message, f"Код '{code}' не найден.")

    @loader.unrestricted
    async def setcodecmd(self, message: Message):
        """Создать код рассылки и задать сообщение для нее.

        Используйте: .setcode <код> <вероятность> (ответом на сообщение)
        """
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        if not args or not reply:
            return await utils.answer(
                message, "Ответьте на сообщение с .setcode <код> <вероятность>"
            )
        code, probability_str = args.split(maxsplit=1)
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

    @loader.unrestricted
    async def listcmd(self, message: Message):
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

    async def watcher(self, message: Message):
        """Обработка сообщений и запуск рассылки."""
        if self.me.id not in self.allowed_ids:
            return
        code_data_dict = self.broadcast["code_chats"]

        for code in code_data_dict:
            if code in message.text:
                data = code_data_dict[code]
                chat_id = message.chat_id

                try:
                    chat = await self.client.get_entity(chat_id)
                    chat_title = chat.title if hasattr(chat, "title") else "—"
                except Exception as e:
                    chat_title = f"(Ошибка) {e}"
                chats = data["chats"]
                if chat_id in chats:
                    chats.remove(chat_id)
                    txt = "удален для"
                else:
                    chats.append(chat_id)
                    txt = "добавлен для"
                await self.client.send_message(
                    "me", f"<code>{chat_id}</code> ({chat_title}) {txt} '{code}'."
                )
                self.db.set("broadcast", "Broadcast", self.broadcast)
        if random.random() < 0.003:
            await self.broadcast_to_chats()

    async def broadcast_to_chats(self):
        """Рассылка сообщений по чатам."""
        for code, data in self.broadcast["code_chats"].items():
            main_message = await self.client.get_messages(
                data["main_chat"], ids=data["message_id"]
            )

            for chat_id in data.get("chats", []):
                if random.random() < data["probability"]:
                    try:
                        await self.client.send_message(chat_id, main_message)
                        await asyncio.sleep(9)
                    except Exception as e:
                        await self.client.send_message(
                            "me", f"Ошибка отправки в чат {chat_id}: {e}"
                        )
        self.db.set("broadcast", "Broadcast", self.broadcast)
