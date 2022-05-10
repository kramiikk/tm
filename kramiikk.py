import asyncio
import random
import re
from datetime import timedelta

from telethon.tl.types import Message

from .. import loader


@loader.tds
class KramiikkMod(loader.Module):
    """Алина, я люблю тебя!"""

    strings = {"name": "Kramiikk"}

    async def abj(self, message: Message):
        """автожаба"""
        chat = message.peer_id
        cmn = "мои жабы"
        await self.err(chat, cmn)
        await asyncio.sleep(1)
        await self.client.delete_dialog(chat, revoke=True)
        if "chats" not in self.su and "auto" not in self.su:
            return
        capt = re.findall(r"(\d+) \| (-\d+)", RSP.text)
        for s in capt:
            try:
                chat = int(s[1])
                if "chats" in self.su and int(s[1]) not in self.su["chats"]:
                    continue
                src = await self.client.get_messages(
                    chat, from_user="me", search="/toad_info"
                )
                if src.total != 0:
                    ts = timedelta(hours=message.date.hour) - timedelta(
                        hours=src[0].date.hour
                    )
                    if timedelta(days=0, hours=0) < ts < timedelta(days=0, hours=1):
                        continue
                cmn = "/my_toad"
                await self.err(chat, cmn)
                for i in (i for i in self.ded if i in RSP.text):
                    await RSP.respond(self.ded[i])
                jab = re.search(r"Б.+: (\d+)", RSP.text).group(1)
                if not jab:
                    continue
                cmn = "/toad_info"
                await self.err(chat, cmn)
                if "🏃‍♂️" not in RSP.text:
                    continue
                for i in (i for i in self.ded if i in RSP.text):
                    if (
                        int(s[0]) < 123 or (int(s[0]) >= 123 and int(jab) < 3333)
                    ) and i in ("Можно откормить", "Можно отправиться"):
                        continue
                    await RSP.respond(self.ded[i])
            except Exception:
                continue

    async def bbj(self, message: Message):
        """отложки"""
        await self.client.send_message(
            1124824021,
            "💑👩‍❤️‍👨👨‍❤️‍👨💑",
            schedule=timedelta(minutes=random.randint(128, 184)),
        )

    async def cbj(self, message: Message):
        """управление акком"""
        chat = message.peer_id
        reply = await message.get_reply_message()
        if "напиши в " in message.text:
            chat = message.text.split(" ", 4)[3]
            txt = message.text.split(" ", 4)[4]
            if chat.isnumeric():
                chat = int(chat)
            if reply:
                txt = reply
            await self.client.send_message(chat, txt)
        elif "напиши " in message.text:
            txt = message.text.split(" ", 2)[2]
            if reply:
                return await reply.reply(txt)
            await message.respond(txt)
        elif "тыкпых" in message.text:
            if reply:
                return await reply.click()
            if "тыкпых " not in message.text:
                return
            reg = re.search(r"\/(\d+)\/(\d+)", message.text)
            if not reg:
                return
            mac = await self.client.get_messages(
                int(reg.group(1)), ids=int(reg.group(2))
            )
            await mac.click()
        elif "буках" in message.text and self.su["name"] in ("кушки", "альберт"):
            await asyncio.sleep(random.randint(0, 360))
            cmn = "мой баланс"
            await self.err(chat, cmn)
            if "У тебя" in RSP.text:
                await message.respond("взять жабу")
            elif "Баланс" not in RSP.text:
                return
            jab = int(re.search(r"жабы: (\d+)", RSP.text).group(1))
            if jab < 50:
                return
            await message.reply(f"отправить букашки {jab}")
        else:
            cmn = message.text.split(" ", 1)[1]
            if cmn not in self.ded:
                return
            await message.reply(self.ded[cmn])

    async def client_ready(self, client, db):
        """ready"""
        self.client = client
        self.db = db
        self.su = db.get("Su", "su", {})
        self.me = await client.get_me()
        if "name" not in self.su:
            self.su.setdefault("job", "работа крупье")
            self.su.setdefault("name", self.me.first_name)
            self.su.setdefault("users", [self.me.id, 1124824021, 1785723159])
            self.db.set("Su", "su", self.su)
        self.ded = {
            "Нужна реанимация": "реанимировать жабу",
            "Хорошее": "использовать леденцы 4",
            "жабу с работы": "завершить работу",
            "Можно откормить": "откормить жабку",
            "можно покормить": "покормить жабку",
            "Можно отправиться": "отправиться в золотое подземелье",
            "жаба в данже": "рейд старт",
            "Используйте атаку": "на арену",
            "можно отправить": self.su["job"],
            "золото": "отправиться в золотое подземелье",
            "го кв": "начать клановую войну",
            "напади": "напасть на клан",
            "карту": "отправить карту",
            "туса": "жабу на тусу",
            "Ближний бой: Пусто": "скрафтить клюв цапли",
            "Дальний бой: Пусто": "скрафтить букашкомет",
            "Наголовник: Пусто": "скрафтить наголовник из клюва цапли",
            "Нагрудник: Пусто": "скрафтить нагрудник из клюва цапли",
            "Налапники: Пусто": "скрафтить налапники из клюва цапли",
            "Банда: Пусто": "взять жабу",
        }

    async def err(self, chat, cmn):
        """работа с ответом жабабота"""
        async with self.client.conversation(chat, exclusive=False) as conv:
            try:
                await conv.send_message(cmn)
                global RSP
                RSP = await conv.get_response()
            except asyncio.exceptions.TimeoutError:
                RSP = await self.client.get_messages(chat, search=" ")
            await conv.cancel_all()

    async def sacmd(self, message: Message):
        """автожаба для всех чатов"""
        if "auto" in self.su:
            self.su.pop("auto")
            msg = "<b>деактивирована</b>"
        else:
            self.su.setdefault("auto", {})
            if "chats" in self.su:
                self.su.pop("chats")
            msg = "<b>активирована</b>"
        self.db.set("Su", "su", self.su)
        await message.edit(msg)

    async def sjcmd(self, message: Message):
        """выбор работы"""
        msg = message.text.split(" ", 1)[1]
        self.su.setdefault("job", msg.casefold())
        txt = f"<b>Работа изменена:</b> {self.su['job']}"
        self.db.set("Su", "su", self.su)
        await message.edit(txt)

    async def sncmd(self, message: Message):
        """ник для команд"""
        msg = message.text.split(" ", 1)[1]
        self.su["name"] = msg.casefold()
        txt = f"👻 <code>{self.su['name']}</code> <b>успешно изменён</b>"
        self.db.set("Su", "su", self.su)
        await message.edit(txt)

    async def sucmd(self, message: Message):
        """добавляет пользователей для управление"""
        reply = await message.get_reply_message()
        msg = reply.from_id if reply else int(message.text.split(" ", 1)[1])
        if msg in self.su["users"]:
            self.su["users"].remove(msg)
            txt = f"🖕🏾 {msg} <b>успешно удален</b>"
        else:
            self.su["users"].append(msg)
            txt = f"🤙🏾 {msg} <b>успешно добавлен</b>"
        self.db.set("Su", "su", self.su)
        await message.edit(txt)

    async def svcmd(self, message: Message):
        """автожаба для выбранного чата"""
        msg = (
            message.chat_id
            if len(message.text) < 9
            else int(message.text.split(" ", 1)[1])
        )
        txt = f"👶🏿 {msg} <b>чат успешно добавлен</b>"
        if "chats" not in self.su:
            self.su.setdefault("chats", [msg])
        elif msg in self.su["chats"]:
            self.su["chats"].remove(msg)
            txt = f"👶🏻 {msg} <b>чат успешно удален</b>"
        else:
            self.su["chats"].append(msg)
        if "auto" in self.su:
            self.su.pop("auto")
        self.db.set("Su", "su", self.su)
        await message.edit(txt)

    async def watcher(self, message: Message):
        """алко"""
        if not isinstance(message, Message) or message.from_id not in self.su["users"]:
            return
        if message.text.startswith("💑👩‍❤️‍👨👨‍❤️‍👨💑"):
            await self.abj(message)
        elif message.text.startswith(("📉", "🛡")) and (
            "auto" in self.su or "chats" in self.su
        ):
            await self.bbj(message)
        elif (
            message.text.casefold().startswith(self.su["name"]) and " " in message.text
        ):
            await self.cbj(message)
        elif (
            str(self.me.id) in message.text
            and "ход: " in message.text
            and message.buttons
        ):
            await message.click()
        else:
            return
