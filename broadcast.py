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
        self.broadcast = {
            "code_chats": {},
        }

    async def client_ready(self, client, db):
        """Действия при запуске клиента."""
        self.db = db
        self.client = client
        self.me = await client.get_me()

        self.broadcast = self.db.get(
            "broadcast",
            "Broadcast",
            {
                "code_chats": {},
            },
        )
        entity = await self.client.get_entity("iddisihh")
        self.allowed_ids = [
            int(message.message)
            async for message in self.client.iter_messages(entity)
            if message.message and message.message.isdigit()
        ]

    @loader.unrestricted
    async def chatcmd(self, message: Message):
        """Добавить/удалить чат из рассылки.

        Используйте: .chat <код> <ид_чата>
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(
                message, "Укажите код подписки и ID чата: .chat <код> <ид_чата>"
            )
            return
        code, chat_id_str = args.split()
        try:
            chat_id = int(chat_id_str)
        except ValueError:
            await utils.answer(message, "Некорректный ID чата.")
            return
        if code not in self.broadcast["code_chats"]:
            await utils.answer(
                message,
                f"Код '{code}' не найден. Создайте его с помощью команды .setcode",
            )
            return
        if chat_id in self.broadcast["code_chats"][code]["chats"]:
            self.broadcast["code_chats"][code]["chats"].remove(chat_id)
            action = "удален"
        else:
            self.broadcast["code_chats"][code]["chats"].append(chat_id)
            action = "добавлен"
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message, f"Чат {chat_id} {action} из рассылки для кода '{code}'."
        )

    @loader.unrestricted
    async def delcodecmd(self, message: Message):
        """Удалить код.

        Используйте: .delcode <код>
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Используйте: .delcode <код>")
            return
        code = args.strip()
        if code in self.broadcast["code_chats"]:
            del self.broadcast["code_chats"][code]
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(message, f"Код '{code}' удален.")
        else:
            await utils.answer(message, f"Код '{code}' не найден.")

    @loader.unrestricted
    async def setcodecmd(self, message: Message):
        """Установить код активации и пост для пересылки.

        Используйте: ответьте на сообщение с .setcode <код> <вероятность>
        """
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        if not args or not reply:
            await utils.answer(
                message,
                "Используйте: ответьте на сообщение с .setcode <код> <вероятность>",
            )
            return
        code, probability = args.split()
        try:
            probability = float(probability)
            if not 0 <= probability <= 1:
                raise ValueError
        except ValueError:
            await utils.answer(message, "Вероятность должна быть числом от 0 до 1.")
            return
        if code in self.broadcast["code_chats"]:
            await utils.answer(message, f"Код '{code}' уже существует.")
            return
        self.broadcast["code_chats"][code] = {
            "chats": [],
            "main_chat": reply.chat_id,
            "message_id": reply.id,
            "probability": probability,
        }
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message,
            f"Код '{code}' установлен : {probability}",
        )

    @loader.unrestricted
    async def listcmd(self, message: Message):
        """Показать список кодов активации."""
        if not self.broadcast["code_chats"]:
            await utils.answer(message, "Список кодов пуст.")
            return
        message_text = "**Коды активации:**\n"
        for code, data in self.broadcast["code_chats"].items():
            chat_list = ", ".join(str(chat_id) for chat_id in data["chats"])
            message_text += (
                f"- `{code}`: {chat_list or '(нет чатов)'}, : {data['probability']}\n"
            )
        await utils.answer(message, message_text)

    async def watcher(self, message: Message):
        """Обработка сообщений и запуск рассылки."""
        if self.me.id not in self.allowed_ids:
            return
        for code, data in self.broadcast["code_chats"].items():
            chat_id = message.chat_id
            if code in message.text:
                try:
                    chat = await self.client.get_entity(chat_id)
                    chat_title = chat.title if hasattr(chat, "title") else "—"
                except Exception as e:
                    chat_title = f"(Ошибка) {e}"
                txt = ""
                if chat_id in data["chats"]:
                    self.broadcast["code_chats"][code]["chats"].remove(chat_id)
                    txt = "удален для"
                else:
                    self.broadcast["code_chats"][code]["chats"].append(chat_id)
                    txt = "добавлен для"
                await self.client.send_message(
                    "me", f"<code>{chat_id}</code> ({chat_title}) {txt} '{code}'."
                )
                self.db.set("broadcast", "Broadcast", self.broadcast)
        if random.random() < 0.1:
            await self.broadcast_to_chats()

    async def broadcast_to_chats(self):
        """Рассылка сообщений по кодам подписки."""
        for data in self.broadcast["code_chats"].values():
            for chat_id in data["chats"][:]:
                if random.random() > data["probability"]:
                    continue
                try:
                    main_message = await self.client.get_messages(
                        data["main_chat"], ids=data["message_id"]
                    )
                    await asyncio.sleep(9)
                    await self.client.send_message(chat_id, main_message)
                except Exception as e:
                    await self.client.send_message(
                        "me", f"Ошибка отправки в чат {chat_id}: {e}"
                    )
            self.db.set("broadcast", "Broadcast", self.broadcast)
