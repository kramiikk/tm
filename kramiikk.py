import asyncio
import random
import re
from datetime import timedelta

from .. import loader


@loader.tds
class KramiikkMod(loader.Module):
    """Алина, я люблю тебя!"""

    strings = {"name": "Kramiikk"}

    async def abj(self, m):
        if m.from_id not in self.su["users"]:
            return
        chat = m.peer_id
        await m.delete()
        cmn = "мои жабы"
        await self.err(chat, cmn)
        await self.client.delete_dialog(chat)
        if "chats" not in self.su and "auto" not in self.su:
            return
        capt = re.findall(r"(\d+) \| (-\d+)", RSP.text)
        for s in capt:
            try:
                chat = int(s[1])
                if "chats" in self.su and int(s[1]) not in self.su["chats"]:
                    continue
                cmn = "моя жаба"
                await self.err(chat, cmn)
                for i in (i for i in self.ded if i in RSP.text):
                    await RSP.respond(self.ded[i])
                jab = re.search(r"Б.+: (\d+)", RSP.text).group(1)
                if not jab:
                    return
                cmn = "жаба инфо"
                await self.err(chat, cmn)
                if "🏃‍♂️" not in RSP.text:
                    return
                for i in (i for i in self.ded if i in RSP.text):
                    if (int(s[0]) < 123 or int(jab) < 3333) and i in (
                        "Можно откормить",
                        "Можно отправиться",
                    ):
                        continue
                    await RSP.respond(self.ded[i])
            except Exception:
                return
        return

    async def bbj(self, m):
        if not m.text.startswith("📉") and m.from_id not in self.su["users"]:
            return
        if "auto" not in self.su or "chats" not in self.su:
            return
        return await self.client.send_message(
            1124824021,
            "💑👩‍❤️‍👨👨‍❤️‍👨💑",
            schedule=timedelta(minutes=random.randint(128, 2)),
        )

    async def cbj(self, m):
        if m.from_id not in self.su["users"]:
            return
        if not m.text.casefold().startswith(self.su["name"]):
            return
        if " " not in m.text:
            return
        chat = m.peer_id
        reply = await m.get_reply_message()
        if "напиши в " in m.text:
            chat = m.text.split(" ", 4)[3]
            txt = m.text.split(" ", 4)[4]
            if chat.isnumeric():
                chat = int(chat)
            if reply:
                txt = reply
            return await self.client.send_message(chat, txt)
        if "напиши " in m.text:
            txt = m.text.split(" ", 2)[2]
            if reply:
                return await reply.reply(txt)
            return await m.respond(txt)
        if "тыкпых " in m.text:
            if reply:
                return await reply.click(0)
            reg = re.search(r"\/(\d+)\/(\d+)", m.text)
            if not reg:
              return
            mac = await self.client.get_messages(int(reg.group(1)), ids=int(reg.group(2)))
            await mac.click(0)
        if "буках" in m.text and self.su["name"] in ["кушки", "альберт"]:
            await asyncio.sleep(random.randint(0, 360))
            cmn = "мой баланс"
            await self.err(chat, cmn)
            if "У тебя" in RSP.text:
                return await m.respond("взять жабу")
            if "Баланс" not in RSP.text:
                return
            jab = int(re.search(r"жабы: (\d+)", RSP.text).group(1))
            if jab < 50:
                return
            return await m.reply(f"отправить букашки {jab}")
        cmn = m.text.split(" ", 1)[1]
        if cmn not in self.ded:
            return
        return await m.reply(self.ded[cmn])

    async def client_ready(self, client, db):
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

    async def dbj(self, m):
        if f"ход: {self.me.first_name}" not in m.text:
            return
        if not m.buttons:
            return
        await m.respond("реанимировать жабу")
        return await m.click(0)

    async def ebj(self, m):
        fff = {
            "💑👩‍❤️‍👨👨‍❤️‍👨💑": self.abj(m),
            "📉": self.bbj(m),
            self.su["name"]: self.cbj(m),
            self.me.first_name: self.dbj(m),
        }
        for i in (i for i in fff if i in m.text.casefold()):
            return await fff[i]
        return

    async def err(self, chat, cmn):
        """работа с ответом жабабота"""
        async with self.client.conversation(chat, exclusive=False) as conv:
            try:
                await conv.send_message(cmn)
                global RSP
                RSP = await conv.get_response()
            except asyncio.exceptions.TimeoutError:
                await conv.send_message(cmn)
                RSP = await self.client.get_messages(chat, search=" ")
            await conv.cancel_all()

    async def sacmd(self, m):
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
        return await m.edit(msg)

    async def sjcmd(self, m):
        """выбор работы"""
        msg = m.text.split(" ", 1)[1]
        self.su.setdefault("job", msg.casefold())
        txt = f"<b>Работа изменена:</b> {self.su['job']}"
        self.db.set("Su", "su", self.su)
        return await m.edit(txt)

    async def sncmd(self, m):
        """ник для команд"""
        msg = m.text.split(" ", 1)[1]
        self.su["name"] = msg.casefold()
        txt = f"👻 <code>{self.su['name']}</code> <b>успешно изменён</b>"
        self.db.set("Su", "su", self.su)
        return await m.edit(txt)

    async def sucmd(self, m):
        """добавляет пользователей для управление"""
        reply = await m.get_reply_message()
        msg = reply.from_id if reply else int(m.text.split(" ", 1)[1])
        if msg in self.su["users"]:
            self.su["users"].remove(msg)
            txt = f"🖕🏾 {msg} <b>успешно удален</b>"
        else:
            self.su["users"].append(msg)
            txt = f"🤙🏾 {msg} <b>успешно добавлен</b>"
        self.db.set("Su", "su", self.su)
        return await m.edit(txt)

    async def svcmd(self, m):
        """автожаба для выбранного чата"""
        msg = m.chat_id if len(m.text) < 9 else int(m.text.split(" ", 1)[1])
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
        return await m.edit(txt)

    async def watcher(self, m):
        return await self.ebj(m)
