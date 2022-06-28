import asyncio
import datetime
import random
import re

from telethon.tl.types import Message

from .. import loader


@loader.tds
class ZhabaMod(loader.Module):
    """Модуль для @toadbot"""

    strings = {"name": "Zhaba"}

    async def client_ready(self, client, db):
        """ready"""
        self.client = client
        self.db = db
        self.su = db.get("Su", "su", {})
        self.me = await client.get_me()
        if "name" not in self.su:
            self.su.setdefault("name", self.me.first_name)
            self.su.setdefault("users", [1124824021, self.me.id, 1785723159])
            self.db.set("Su", "su", self.su)
        self.ded = {
            "туса": "Жабу на тусу",
            "карту": "Отправить карту",
            "напади": "Напасть на клан",
            "снаряга": "Мое снаряжение",
            "Банда: Пусто": "взять жабу",
            "жаба в данже": "Рейд старт",
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

    async def vcc(self, chat):
        try:
            cmn = "Моя жаба"
            await self.err(chat, cmn)
        except Exception:
            pass
        if (
            "Имя жабы" not in RSP.text
            or i[0] not in RSP.text
            and i[1] not in RSP.text
        ):
            return

    async def err(self, chat, cmn):
        """работа с ответом жабабота"""
        try:
            async with self.client.conversation(chat, exclusive=False) as conv:
                await conv.send_message(cmn)
                global RSP
                RSP = await conv.get_response()
                await conv.cancel_all()
        except Exception:
            pass

    async def watcher(self, m):
        """алко"""
        if "auto" not in self.su:
            return
        ct = datetime.datetime.now()
        n = self.me.id % 100 if (self.me.id %
                                 100) < 48 else int(self.me.id % 100 / 3)
        n = n + ct.hour if ct.hour < 12 else n + ct.hour - 11
        if ct.minute != n:
            return
        await asyncio.sleep(random.randint(n, 96 + (ct.microsecond % 100)) + ct.minute)
        if "minute" not in self.su:
            self.su.setdefault("minute", ct.hour + ct.minute)
            self.db.set("Su", "su", self.su)
        if -1 < ((ct.hour + ct.minute) - self.su["minute"]) < 1:
            return
        self.su["minute"] = ct.hour + ct.minute
        self.db.set("Su", "su", self.su)
        chat = 1124824021
        cmn = "мои жабы"
        await self.err(chat, cmn)
        await self.client.delete_dialog(chat, revoke=True)
        if not RSP:
            return
        for i in re.findall(r"•(.+) \|.+ (\d+) \| (-\d+)", RSP.text):
            await asyncio.sleep(
                random.randint(n + ct.hour, 96 +
                               (ct.microsecond % 100)) + ct.minute
            )
            chat = int(i[2])
            if self.su["auto"] != [] and chat not in self.su["auto"]:
                continue
            if "msg" in self.su and chat in self.su["msg"]:
                msg = await self.client.get_messages(self.su["msg"][chat][0], ids=self.su["msg"][chat][1])
            if "msg" not in self.su:
                self.su.setdefault("msg", {})
            if chat not in self.su["msg"] or not msg or msg.date.day != ct.day or msg.date.hour > 19:
                cmn = "@toadbot Жаба инфо"
                await self.err(chat, cmn)
                if (
                    "🏃‍♂️" not in RSP.text
                    or "не в браке" not in RSP.text
                    and i[0] not in RSP.text
                ):
                    continue
                self.su["msg"].setdefault(chat, [chat, RSP.id])
                msg = RSP
