import asyncio
import datetime
import logging
import random
import re

from telethon import events, functions

from .. import loader, utils

logger = logging.getLogger(__name__)
asl = [
    "жаба дня",
    "топ жаб",
    "сезон кланов",
    "кланы",
    "взять жабу",
]
bak = [
    1709411724,
    1261343954,
    1785723159,
    1486632011,
    1863720231,
    547639600,
    449434040,
    388412512,
    553299699,
    412897338,
]
elj = [
    -1001441941681,
    -1001436786642,
    -1001380664241,
    -1001289617428,
    -1001485617300,
    -1001465870466,
    -1001169549362,
    -1001543064221,
]
klw = [-419726290, -1001543064221, -577735616, -1001493923839]
ninja = [
    -1001380664241,
    -1001441941681,
    -1001289617428,
    -1001436786642,
    -1001447960786,
    -1001290958283,
    -1001485617300,
]
nr = [1, 3, 5, 7, 9]


def register(cb):
    """.

    ----------

    """
    cb(kramiikkMod())


@loader.tds
class kramiikkMod(loader.Module):
    """Алина, я люблю тебя."""

    answers = {
        0: ("Ответ тебе известен", "Ты знаешь лучше меня!", "Ответ убил!.."),
        1: ("Да, но есть помехи", "Может быть", "Вероятно", "Возможно", "Наверняка"),
        2: ("Есть помехи...", "Вряд ли", "Что-то помешает", "Маловероятно"),
        3: ("Нет, но пока", "Скоро!", "Жди!", "Пока нет"),
    }
    strings = {
        "name": "kramiikk",
        "quest_answer": "<i>%answer%</i>",
    }

    def __init__(self):
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        """.

        ----------

        """
        self.client = client
        self.db = db
        self.me = await client.get_me()
        self.status = db.get("Status", "status", {})
        self.duel = db.get("Дуэлька", "duel", {})

    async def watcher(self, message):
        """.

        ----------

        """
        asly = random.choice(asl)
        chat = message.chat_id
        name = "монарх"
        rh = random.choice(nr)
        rd = random.randint(rh, 13)
        if "Сейчас выбирает ход" in message.message and message.mentioned:
            await message.respond("реанимировать жабу")
            await message.click(0)
        elif "[8🐝]" in message.message:
            await message.click(0)
        elif "[4🐝]" in message.message:
            await message.click(0)
        elif "[2☢️🐝, 2🔴🐝," in message.message:
            await message.click(0)
        elif "Бзззз! С пасеки" in message.message:
            await message.click(0)
        elif "НЕЗАЧЁТ!" in message.message and chat in {707693258}:
            args = [int(x) for x in message.text.split() if x.isnumeric()]
            rd = random.randint(20, 60)
            if len(args) == 4:
                delta = datetime.timedelta(
                    hours=args[1], minutes=args[2], seconds=args[3] + 13
                )
            elif len(args) == 3:
                delta = datetime.timedelta(
                    minutes=args[1], seconds=args[2] + 13)
            elif len(args) == 2:
                delta = datetime.timedelta(seconds=args[1] + 13)
            for i in range(3):
                delta = delta + datetime.timedelta(seconds=13)
                await self.client.send_message(chat, "Фарма", schedule=delta)
        elif (
            "РеанимироватЬ жабу" in message.message
            and message.sender_id not in {self.me.id, 1124824021}
            and chat in self.duel
        ):
            await asyncio.sleep(rd)
            await utils.answer(message, "дуэль")
        elif (
            f"Вы бросили вызов на дуэль пользователю {self.me.first_name}"
            in message.message
            and message.sender_id in {1124824021}
            and chat in self.duel
        ):
            await asyncio.sleep(rd)
            await message.respond("дуэль принять")
            await asyncio.sleep(rd)
            await message.respond("дуэль старт")
        elif (
            f"{self.status['Имя Жабы']}, У вас ничья" in message.message
            and chat in self.duel
        ):
            await asyncio.sleep(rd)
            await message.respond("РеанимироватЬ жабу")
        elif (
            self.status["Имя Жабы"] in message.message
            and "отыграл" in message.message
            and chat in self.duel
        ):
            self.duel.pop(chat)
            self.db.set("Дуэлька", "duel", self.duel)
            await utils.answer(message, "<b>пью ромашковый чай</b>!")
        elif (
            "Победитель" in message.message
            and self.status["Имя Жабы"] not in message.message
            and chat in self.duel
        ):
            await asyncio.sleep(rd)
            await utils.answer(message, "РеанимироватЬ жабу")
        elif (
            message.message.startswith("Алло")
            and message.sender_id in {1124824021}
            and chat in ninja
        ):
            capt = re.search(
                "клана (.+) нашелся враг (.+), пора", message.text)
            if capt:
                mk = capt.group(1)
                ek = capt.group(2)
                txt = f"⚡️{mk} <b>VS</b> {ek}"
                nm = await self.client.send_message(1767017980, txt)
                src = f"Топ 35 кланов {mk}"
                ms = await self.client.get_messages(1782816965, search=src)
                if ms.total == 0:
                    src = f"{chat} {mk} Лига:"
                    ms1 = await self.client.get_messages(1655814348, search=src)
                    for i in ms1:
                        liga = re.search("Лига: (.+)", i.message).group(1)
                else:
                    for i in ms:
                        liga = re.search(
                            "Топ 35 кланов (.+) лиге", i.message
                        ).group(1)
                txt += f"\nЛига: {liga}"
                await utils.answer(nm, txt)
        else:
            return