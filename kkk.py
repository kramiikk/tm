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

    async def abj(self, chat, m):
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

    async def bbj(self, idu, m):
        if m.message.startswith(("✅", "📉")) and "auto" in self.su:
            await self.client.send_message(
                idu,
                "💑👩‍❤️‍👨👨‍❤️‍👨💑",
                schedule=timedelta(
                    minutes=random.randint(33, 55), seconds=random.randint(1, 60)
                ),
            )

    async def cbj(self, m, msg):
        if m.message.casefold().startswith(self.su["name"]):
            reply = await m.get_reply_message()
            if "напиши в " in m.message:
                chat = msg.split(" ", 4)[3]
                if chat.isnumeric():
                    chat = int(chat)
                if reply:
                    msg = reply
                txt = msg.split(" ", 4)[4]
                return await self.client.send_message(chat, txt)
            if "напиши" in m.message:
                txt = msg.split(" ", 2)[2]
                if reply:
                    await reply.reply(txt)
                await utils.answer(m, txt)
            else:
                cmn = msg.split(" ", 1)[1]
                if cmn in ded:
                    await m.reply(ded[cmn])

    async def dbj(self, m):
        if m.buttons:
            txt = "реанимировать жабу"
            await utils.answer(m, txt)
            await m.click(0)

    async def bmj(self, chat):
        """алгоритм жабабота"""
        cmn = "моя жаба"
        await self.err(chat, cmn)
        for i in (i for i in ded if i in RSP.text):
            await utils.answer(RSP, ded[i])
        jab = re.search(r"У.+: (\d+)[\s\S]*Б.+: (\d+)", RSP.text)
        cmn = "жаба инфо"
        await self.err(chat, cmn)
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
            for i in (i for i in ded if i in RSP.text):
                await utils.answer(RSP, ded[i])

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.su = db.get("Su", "su", {})
        self.me = await client.get_me()
        if "name" not in self.su:
            self.su.setdefault("name", self.me.username)
            self.su.setdefault("users", [self.me.id])

    async def err(self, chat, cmn):
        """работа с ответом жабабота"""
        async with self.client.conversation(chat, exclusive=False) as conv:
            try:
                msg = await conv.send_message(cmn)
                global RSP
                RSP = await conv.get_response()
            except asyncio.exceptions.TimeoutError:
                RSP = await self.client.get_messages(chat, search=" ")
            await conv.cancel_all()
            if chat not in [1403626354]:
                await msg.delete()
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

    async def sfcmd(self, m):
        """добавить фильтры, пример 'текст / ответ'"""
        chatid = str(m.chat_id)
        msg = utils.get_args_raw(m)
        key = msg.split(" / ")[0]
        if not msg:
            txt = ""
            for i in self.su[chatid]:
                txt += f"<b>• {i}</b>\n"
            await utils.answer(m, f"<b>Фильтры: {len(self.su[chatid])}\n\n{txt}</b>")
        if chatid not in self.su:
            self.su.setdefault(chatid, {})
        if key not in self.su[chatid]:
            self.su[chatid].setdefault(key, msg.split(" / ")[1])
            msg = "<b>добавлен</b>"
        else:
            self.su[chatid].pop(key)
            msg = "<b>удален</b>"
        if self.su[chatid] == {}:
            self.su.pop(chatid)
        self.db.set("Su", "su", self.su)
        await utils.answer(m, msg)

    async def stcmd(self, m):
        """фильтр на юзера, пример 'ид / текст / ответ'"""
        chatid = str(m.chat_id)
        msg = utils.get_args_raw(m)
        idu = msg.split(" / ")[0]
        key = msg.split(" / ")[1]
        if chatid not in self.su:
            self.su.setdefault(chatid, {})
        if idu not in self.su[chatid]:
            self.su[chatid].setdefault(idu, {})
        if key not in self.su[chatid][idu]:
            self.su[chatid][idu].setdefault(key, msg.split(" / ")[2])
            msg = "<b>активирована</b>"
        else:
            self.su[chatid][idu].pop(msg.split(" / ")[0])
            msg = "<b>деактивирована</b>"
        self.db.set("Su", "su", self.su)
        await utils.answer(m, msg)

    async def sncmd(self, m):
        """ник для команд"""
        msg = utils.get_args_raw(m)
        txt = "db:\n"
        if not msg:
            for i in self.db:
                txt += f"\n•{i}"
            return await utils.answer(m, txt)
        if "db" in msg:
            key = msg.split(" ")[1]
            for i in self.db[key]:
                txt += f"\n•{i}"
            return await utils.answer(m, txt)
        self.su["name"] = msg.casefold()
        txt = "👻 <code>" + self.su["name"] + "</code> <b>успешно изменён</b>"
        await utils.answer(m, txt)
        self.db.set("Su", "su", self.su)

    async def sucmd(self, m):
        """добавляет пользователей для управление акк"""
        msg = utils.get_args_raw(m)
        if txt in self.su["users"]:
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
        msg = m.text
        chat = m.chat_id
        chatid = str(chat)
        idu = m.sender_id
        users = self.su["users"]
        fff = {
            "💑👩‍❤️‍👨👨‍❤️‍👨💑": self.abj(chat, m),
            "✅": self.bbj(idu, m),
            "📉": self.bbj(idu, m),
            self.su["name"]: self.cbj(m, msg),
            f"Сейчас выбирает ход: {self.me.first_name}": self.dbj(m),
        }
        try:
            if idu in [1124824021] or idu in users:
                for i in (i for i in fff if i in m.message.casefold()):
                    return await fff[i]
            if chatid in self.su:
                idu = str(idu)
                if idu in self.su[chatid]:
                    for i in (i for i in self.su[chatid][idu] if i in m.message):
                        await utils.answer(m, self.su[chatid][idu][i])
                for i in (i for i in self.su[chatid] if i in m.message):
                    await utils.answer(m, self.su[chatid][i])
            return
        except Exception as e:
            return await self.client.send_message("me", f"Error:\n{' '.join(e.args)}")
