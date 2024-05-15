import asyncio
import random
from telethon.tl.types import Message
from .. import loader


@loader.tds
class RassMod(loader.Module):
    """Модуль для рассылки"""

    strings = {"name": "rass"}

    async def client_ready(self, client, db):
        self.db = db
        self.client = client
        self.me = await client.get_me()
        self.rass = db.get(
            "Thr",
            "rass",
            {
                "interval": 5,
                "messages": {},
                "code": "Super Sonic",
                "main": None,
                "chats": [],
                "last_send_time": 0,
            },
        )

        self.allowed_ids = [
            int(message.message)
            async for message in self.client.iter_messages(
                await self.client.get_input_entity("iddisihh")
            )
            if message.message
        ]

    @loader.unrestricted
    async def rasscmd(self, m):
        """Управление рассылкой"""
        args = m.text.split(" ", 1)
        if len(args) < 2:
            await self.help(m)
            return
        command = args[1].lower()
        if command == "add":
            await self.manage_chats(m, add=True)
        elif command == "rem":
            await self.manage_chats(m, add=False)
        elif command == "setmsg":
            await self.set_message(m)
        elif command == "delmsgchat":
            await self.delete_message_chat(m)
        elif command == "setint":
            await self.set_interval(m)
        elif command == "list":
            await self.list_chats(m)
        elif command == "setcode":
            await self.set_code(m)
        elif command == "setmain":
            await self.set_main(m)
        else:
            await self.help(m)

    async def help(self, m):
        """Вывод справки"""
        help_text = (
            "<b>Команды управления рассылкой:</b>\n"
            "<code>.rass add [id]</code> - Добавить чат в список рассылки\n"
            "<code>.rass rem [id]</code> - Удалить чат из списка рассылки\n"
            "<code>.rass setmsg</code> - Установить сообщение для рассылки (ответить на сообщение)\n"
            "<code>.rass setint</code> - Установить интервал рассылки\n"
            "<code>.rass list</code> - Показать список чатов для рассылки\n"
            "<code>.rass setcode</code> - Установить код рассылки\n"
            "<code>.rass setmain</code> - Установить главный чат для рассылки"
        )
        await m.edit(help_text)

    async def manage_chats(self, m, add=True):
        """Управление списком чатов для рассылки"""
        args = m.text.split()
        if len(args) < 3:
            await m.edit("Укажите ID чата")
            return
        chat_id = int(args[2])
        if chat_id not in self.allowed_ids:
            await m.edit("Указанный ID чата не является валидным")
            return
        if add:
            if chat_id in self.rass["chats"]:
                await m.edit("Чат уже в списке рассылки")
            else:
                self.rass["chats"].append(chat_id)
                await m.edit("Чат добавлен в список рассылки")
        elif chat_id in self.rass["chats"]:
            self.rass["chats"].remove(chat_id)
            await m.edit("Чат удален из списка рассылки")
        else:
            await m.edit("Чата нет в списке рассылки")
        self.db.set("Thr", "rass", self.rass)

    async def set_interval(self, m):
        """Установка интервала рассылки"""
        args = m.text.split(" ", 2)
        if len(args) < 3:
            await m.edit(f"Отправляет каждые {self.rass['interval']} минут")
            return
        minutes = args[2]
        if not minutes.isdigit() or not 0 < int(minutes) < 60:
            await m.edit("Введите числовое значение в интервале 1 - 59")
            return
        self.rass["interval"] = int(minutes)
        self.db.set("Thr", "rass", self.rass)
        await m.edit(f"Будет отправлять каждые {minutes} минут")

    async def set_message(self, m):
        """Добавление сообщения"""
        reply = await m.get_reply_message()
        if not reply:
            await m.edit("Ответьте на сообщение")
            return
        args = m.text.split(" ", 2)
        message_id = reply.id

        if len(args) == 2:  # Изменено условие
            self.rass["message"] = message_id
            text = "Сообщение установлено как дефолтное для рассылки"
        elif args[2].lower() == "list":
            self.rass["messages_list"].append(message_id)
            text = "Сообщение добавлено в общий список для рассылки"
        else:
            chat_id = int(args[2])
            self.rass["messages"].setdefault(chat_id, []).append(message_id)
            text = f"Сообщение добавлено в список для рассылки в чат {chat_id}"
        self.db.set("Thr", "rass", self.rass)
        await m.edit(text)

    async def delete_message_chat(self, m):
        """Удалить сообщение из списка для рассылки в указанный чат"""
        args = m.text.split(" ", 3)
        if len(args) < 4:
            await m.edit("Укажите ID чата и ID сообщения после команды")
            return
        chat_id = int(args[2])
        message_id = int(args[3])

        if (
            chat_id not in self.rass["messages"]
            or message_id not in self.rass["messages"][chat_id]
        ):
            await m.edit(
                f"Сообщение с ID {message_id} не найдено в списке для чата {chat_id}"
            )
            return
        self.rass["messages"][chat_id].remove(message_id)
        self.db.set("Thr", "rass", self.rass)
        await m.edit(
            f"Сообщение с ID {message_id} удалено из списка для чата {chat_id}"
        )

    async def list_chats(self, m):
        """Вывод списка чатов для рассылки"""
        if not self.rass["chats"]:
            await m.edit("Список чатов пуст")
            return
        chat_list = []
        for iid in self.rass["chats"]:
            try:
                chat = await self.client.get_input_entity(iid)
                chat_list.append(f"<code>{iid}</code> - {chat.title}")
            except Exception:
                chat_list.append(f"<code>{iid}</code>")
        await m.edit("\n".join(chat_list))

    async def set_code(self, m):
        """Установка кодовой фразы для добавления чата"""
        args = m.text.split(" ", 2)
        if len(args) < 3:
            await m.edit(f"Фраза для добавления чата: <code>{self.rass['code']}</code>")
            return
        self.rass["code"] = args[2]
        self.db.set("Thr", "rass", self.rass)
        await m.edit(f"Установлена фраза: <code>{args[2]}</code>")

    async def set_main(self, m):
        """Установка главного чата"""
        args = m.text.split(" ", 2)
        if len(args) < 3:
            await m.edit("Укажите ID главного чата")
            return
        iid = int(args[2])
        self.rass["main"] = iid
        self.db.set("Thr", "rass", self.rass)
        await m.edit(f"🤙🏾 Главный: <code>{iid}</code>")

    async def watcher(self, m: Message):
        """Обработчик"""
        if (
            not hasattr(m, "text")
            or not isinstance(m, Message)
            or self.me.id not in self.allowed_ids
        ):
            return
        if self.rass["code"] in m.text and m.sender_id == self.me.id:
            iid = m.chat_id
            if m.chat_id not in self.rass["chats"]:
                self.rass["chats"].append(iid)
            else:
                self.rass["chats"].remove(m.chat_id)
            self.db.set("Thr", "rass", self.rass)
            await self.client.send_message(
                "me", f"Чат <code>{iid}</code> добавлен в список рассылки"
            )
        current_time = m.date.timestamp()
        if current_time - self.rass["last_send_time"] < self.rass["interval"] * 60:
            return
        if (
            not self.rass["message"]
            or not self.rass["chats"]
            or m.chat_id not in self.rass["chats"]
        ):
            return
        if m.chat_id in self.rass["messages"]:
            message_id = self.rass["messages"][m.chat_id]
        else:
            message_id = self.rass["message"]
        message = await self.client.get_messages(self.rass["main"], ids=message_id)

        for chat_id in self.rass["chats"]:
            try:
                if chat_id in self.rass["messages"]:
                    message_id = random.choice(self.rass["messages"][chat_id])
                elif self.rass["messages_list"]:
                    message_id = random.choice(self.rass["messages_list"])
                else:
                    message_id = self.rass["message"]
                message = await self.client.get_messages(
                    self.rass["main"], ids=message_id
                )
                if message.media:
                    await self.client.send_file(
                        chat_id, message.media, caption=message.text
                    )
                else:
                    await self.client.send_message(chat_id, message.text)
            except:
                pass
            finally:
                await asyncio.sleep(13)
        self.rass["last_send_time"] = current_time
        self.db.set("Thr", "rass", self.rass)
