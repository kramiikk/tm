import asyncio
import random
import re
from datetime import timedelta

from telethon import events

from .. import loader


@loader.tds
class KramiikkMod(loader.Module):
    """Алина, я люблю тебя!"""

    strings = {"name": "Kramiikk"}

    async def abj(self, m):
        chat = m.peer_id
        await m.delete()
        cmn = "мои жабы"
        await self.err(chat, cmn)
        await self.client.delete_dialog(chat)
        capt = re.findall(r"(\d+) \| (-\d+)", RSP.text)
        for s in capt:
            try:
                chat = int(s[1])
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
                pass

    async def bbj(self, m):
        if "auto" in self.su:
            await self.client.send_message(
                1124824021,
                "💑👩‍❤️‍👨👨‍❤️‍👨💑",
                schedule=timedelta(minutes=random.randint(42, 181)),
            )

    async def cbj(self, m):
        if not m.text.casefold().startswith(self.su["name"]):
            return
        reply = await m.get_reply_message()
        if "напиши в " in m.text:
            chat = m.text.split(" ", 4)[3]
            if chat.isnumeric():
                chat = int(chat)
            if reply:
                txt = reply
            txt = m.text.split(" ", 4)[4]
            return await self.client.send_message(chat, txt)
        if "напиши" in m.text:
            txt = m.text.split(" ", 2)[2]
            if reply:
                return await reply.reply(txt)
            await m.respond(txt)
        elif "буках" in m.text and self.su["name"] in ["кушки", "альберт"]:
            await asyncio.sleep(random.randint(0, 360))
            chat = m.peer_id
            cmn = "мой баланс"
            await self.err(chat, cmn)
            if "У тебя" in RSP.text:
                return await m.respond("взять жабу")
            if "Баланс" not in RSP.text:
                return
            jab = int(re.search(r"жабы: (\d+)", RSP.text).group(1))
            if jab >= 50:
                await m.reply(f"отправить букашки {jab}")
        else:
            cmn = m.text.split(" ", 1)[1]
            if cmn in self.ded:
                await m.reply(self.ded[cmn])

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
        await m.respond("реанимировать жабу")
        return await m.click(0)

    async def ebj(self, m):
        fff = {
            "💑👩‍❤️‍👨👨‍❤️‍👨💑": self.abj(m),
            "📉": self.bbj(m),
            self.su["name"]: self.cbj(m),
        }
        dff = {
            "выбирает": self.dbj(m),
        }
        r = dff if m.mentioned and "выбирает" in m.text else fff
        for i in (i for i in r if i in m.text.casefold()):
            return await r[i]

    async def err(self, chat, cmn):
        """работа с ответом жабабота"""
        async with self.client.conversation(chat, exclusive=False) as conv:
            try:
                txt = await conv.send_message(cmn)
                global RSP
                RSP = await conv.get_response()
            except asyncio.exceptions.TimeoutError:
                txt = await conv.send_message(cmn)
                RSP = await self.client.get_messages(chat, search=" ")
            await conv.cancel_all()

    async def fdj(self, chat):
        cmn = "мое снаряжение"
        await self.err(chat, cmn)
        if "🗡" not in RSP.text:
            return
        for i in (i for i in self.ded if i in RSP.text):
            await RSP.respond(self.ded[i])

    async def sacmd(self, m):
        """будет смотреть за вашими жабами"""
        if "auto" not in self.su:
            self.su.setdefault("auto", {})
            msg = "<b>активирована</b>"
        else:
            self.su.pop("auto")
            msg = "<b>деактивирована</b>"
        self.db.set("Su", "su", self.su)
        await m.edit(msg)

    async def sjcmd(self, m):
        """выбор работы"""
        msg = m.text.split(" ", 1)[1]
        if "job" not in self.su:
            self.su.setdefault("job", msg.casefold())
        else:
            self.su["job"] = msg.casefold()
        txt = f"<b>Работа успешно изменена на</b> {self.su['job']}"
        await m.edit(txt)
        self.db.set("Su", "su", self.su)

    async def sncmd(self, m):
        """ник для команд"""
        msg = m.text.split(" ", 1)[1]
        self.su["name"] = msg.casefold()
        txt = f"👻 <code>{self.su['name']}</code> <b>успешно изменён</b>"
        await m.edit(txt)
        self.db.set("Su", "su", self.su)

    async def sucmd(self, m):
        """добавляет пользователей для управление акк"""
        reply = await m.get_reply_message()
        msg = reply.from_id if reply else int(m.text.split(" ", 1)[1])
        if msg in self.su["users"]:
            self.su["users"].remove(msg)
            txt = f"🖕🏾 {msg} <b>успешно удален</b>"
        else:
            self.su["users"].append(msg)
            txt = f"🤙🏾 {msg} <b>успешно добавлен</b>"
        self.db.set("Su", "su", self.su)
        await m.edit(txt)

    async def watcher(self, m):
        try:
            if m.from_id in self.su["users"]:
                await self.ebj(m)
        finally:
            return
