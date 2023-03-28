import asyncio
import datetime
import random
from telethon.tl.types import Message

from .. import loader


@loader.tds
class KramiikkMod(loader.Module):
    """Алина, я люблю тебя!"""

    strings = {"name": "Kramiikk"}

    async def client_ready(self, client, db):
        """ready"""
        self.db = db
        self.client = client
        self.me = await client.get_me()
        self.su = db.get("Su", "su", {})
        if "name" not in self.su:
            self.su.setdefault("name", self.me.first_name)
            self.su.setdefault("users", [self.me.id])
            self.db.set("Su", "su", self.su)
        self.ded = {
            "туса": "Жабу на тусу",
            "карту": "Отправить карту",
            "напади": "Напасть на клан",
            "снаряга": "Мое снаряжение",
            "Банда: Пусто": "взять жабу",
            "инвентарь": "Мой инвентарь",
            "можно отправить": "Работа крупье",
            "реанимируй": "Реанимировать жабу",
            "Можно на арену!": "@toadbot На арену",
            "Используйте атаку": "@toadbot На арену",
            "Дальний бой: Пусто": "скрафтить букашкомет",
            "жабу с работы": "@toadbot Завершить работу",
            "Забрать жабенка": "@toadbot Забрать жабенка",
            "Ближний бой: Пусто": "скрафтить клюв цапли",
            "можно покормить": "@toadbot Покормить жабу",
            "Можно откормить": "@toadbot Откормить жабу",
            "Покормить жабенка": "@toadbot Покормить жабенка",
            "Брак вознаграждение": "@toadbot Брак вознаграждение",
            "Можно отправиться": "Отправиться в золотое подземелье",
            "В детский сад!": "@toadbot Отправить жабенка в детсад",
            "Нагрудник: Пусто": "скрафтить нагрудник из клюва цапли",
            "Налапники: Пусто": "скрафтить налапники из клюва цапли",
            "Наголовник: Пусто": "скрафтить наголовник из клюва цапли",
            "Отправить жабенка на махач": "@toadbot Отправить жабенка на махач",
        }

    async def err(self, chat, cmn, rsp):
        """работа с ответом жабабота"""
        async with self.client.conversation(chat, exclusive=False) as conv:
            await conv.send_message(cmn)
            rsp = await conv.get_response()
            return rsp

    async def watcher(self, m):
        """алко"""
        if "auto" not in self.su:
            return
        ct = datetime.datetime.now()
        n = self.me.id % 100 if (self.me.id % 100) < 48 else int(self.me.id % 100 / 3)
        n = n + ct.hour if ct.hour < 12 else n + ct.hour - 11
        rsp = None
        if (
            isinstance(m, Message)
            and (
                "auto" in self.su
                and (m.chat_id in self.su["auto"] or self.su["auto"] == [])
            )
            and m.sender_id in self.su["users"]
            and " " in m.text
        ):
            chat = m.chat_id
            await asyncio.sleep(random.randint(1, n + 1))
            reply = await m.get_reply_message()
            if "напиши " in m.text:
                txt = m.text.split(" ", 2)[2]
                if reply:
                    return await reply.reply(txt)
                await m.respond(txt)
            else:
                msg = m.text.split(" ", 2)[1]
                if msg not in self.ded:
                    return
                if msg in ("карту", "лидерку"):
                    return await m.reply(self.ded[msg])
                await m.respond(self.ded[msg])
        if "Eliot" not in m.text:
            return
        chat = 1124824021
        cmn = "мои жабы"
        await self.err(chat, cmn, rsp)
        if rsp is None:
            return
        await m.reply(rsp.text)
