from math import floor
from html import escape
from random import choice
from asyncio import sleep
from .. import loader, utils
from datetime import timedelta
from urllib.parse import quote_plus
from telethon.tl.types import Message
from asyncio.exceptions import TimeoutError
from telethon import events, functions, types, sync
from telethon.tl.functions.users import GetFullUserRequest
from telethon.errors.rpcerrorlist import UsernameOccupiedError
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
import asyncio, datetime, inspect, io, json, logging, os, time, random, re, requests

logger = logging.getLogger(__name__)

def register(cb):
    cb(KramikkMod())

@loader.tds
class KramikkMod(loader.Module):
    """Алина, я люблю тебя!"""

    strings = {
        "name": "Kramikk",
        "name_set": "<u>Имя успешно установлено</u>",
    }

    def __init__(self):
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.me = await client.get_me()
        self.status = db.get("Status", "status", {})

    async def watcher(self, message):
        bak = {
            1222132115,
            1646740346,
            1261343954,
            1785723159,
            1486632011,
            1682801197,
            1863720231,
            1775420029,
            1286303075,
            1746686703,
            1459363960,
            1423368454,
            547639600,
            553299699,
            412897338,
            388412512,
        }
        chat = message.chat_id
        chatid = str(message.chat_id)
        chatik = -1001441941681
        duel = self.db.get("Дуэлька", "duel", {})
        jb = "Ваша Жаба"
        name = self.me.first_name
        if self.me.id in {1261343954}:
            name = "Монарх"
        if self.me.id in {1486632011}:
            name = "Оботи"
        if self.me.id in {1286303075}:
            name = "Лавин"
        if self.me.id in {1775420029}:
            name = "Адият"
        if self.me.id in {1682801197}:
            name = "666"
        if self.me.id in {1646740346}:
            name = "Куат"
        if self.me.id in {1863720231}:
            name = "Допинг"
        if self.me.id in {1785723159}:
            name = "Крамик"
        if self.me.id in {547639600}:
            name = "Нельс"

        rn = [5, 9, 13]
        rn1 = [63, 81, 99]
        aa = random.choice(rn)
        bb = random.choice(rn1)
        a1 = int(((aa + 3) / 2) - 1)
        b1 = int(((bb - 13) / 2) + 1)
        c1 = int(b1 - a1)
        a2 = random.randint(a1, c1)
        b2 = random.randint(c1, b1)
        c2 = random.choice(range(a2, b2+a2))
        cc = int(c2 - a2)
        randelta = random.randint(cc, c2)
        snt = 0

        if "buji" in message.message:
            try:
                await message.delete()
                args = message.text
                reply = await message.get_reply_message()
                count = int(args.split(" ", 3)[1])
                time = int(args.split(" ", 3)[2])
                if reply:
                    spammsg = args.split(" ", 3)[3]
                    for _ in range(count):
                        await reply.reply(spammsg)
                        await sleep(time)
                    if "бук" in spammsg:
                        while count > 50049:
                           await message.reply("отправить букашки 50000")
                           count -= 50000
                           await sleep(time)
                       snt = count - 50
                       await message.reply(f"отправить букашки {snt}")
                else:
                    spammsg = args.split(" ", 3)[3]
                    for _ in range(count):
                        await message.respond(spammsg)
                        await sleep(time)
            except:
                await self.client.send_message(
                    chat, "buji <count:int> <time(sec):int> <args>"
                )

        if message.sender_id in {1124824021}:
            if "Сейчас выбирает ход: " + self.me.first_name in message.message:
                await message.click(0)
            if "Господин " + self.me.first_name in message.message:
                await sleep(3)
                await message.respond("реанимировать жабу")
                await sleep(3)
                await message.respond("отправиться за картой")

            if message.sender_id in bak:
                if "жаба дня" in message.message:
                    async with self.client.conversation(message.chat_id) as conv:
                        await sleep(3)
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=message.chat_id,
                            )
                        )
                        await message.respond("жаба инфо")
                        response = await response
                        if "работу можно" in response.text:
                            time_j = re.search(
                                "будет через (\d+)ч:(\d+)м",
                                response.text,
                                re.IGNORECASE,
                            )
                            if time_j:
                                hrs = int(time_j.group(1))
                                min = int(time_j.group(2))
                                delta = timedelta(
                                    hours=hrs, minutes=min, seconds=randelta
                                )
                            await self.client.send_message(
                                chat, "реанимировать жабу", schedule=delta
                            )
                            await self.client.send_message(
                                chat,
                                "работа грабитель",
                                schedule=delta + timedelta(seconds=13),
                            )
                            for number in range(2):
                                delta = delta + timedelta(hours=8)
                                await self.client.send_message(
                                    chat, "реанимировать жабу", schedule=delta
                                )
                                await self.client.send_message(
                                    chat,
                                    "работа грабитель",
                                    schedule=delta + timedelta(seconds=randelta),
                                )
                                await self.client.send_message(
                                    chat,
                                    "завершить работу",
                                    schedule=delta
                                    + timedelta(hours=2, seconds=randelta + 3),
                                )
                                await sleep(1)
                        else:
                            if "жабу можно через" in response.text:
                                time_r = re.search(
                                    "через (\d+) часов (\d+) минут",
                                    response.text,
                                    re.IGNORECASE,
                                )
                                if time_r:
                                    hrs = int(time_r.group(1))
                                    min = int(time_r.group(2))
                                    delta = timedelta(
                                        hours=hrs, minutes=min, seconds=randelta
                                    )
                                await self.client.send_message(
                                    chat, "завершить работу", schedule=delta
                                )
                            elif "можно отправить" in response.text:
                                await sleep(3)
                                await message.respond("реанимировать жабу")
                                await sleep(3)
                                await message.respond("работа грабитель")
                                delta = timedelta(hours=2, seconds=randelta)
                                await self.client.send_message(
                                    chat, "завершить работу", schedule=delta
                                )
                            else:
                                await sleep(3)
                                await message.respond("завершить работу")
                            for number in range(2):
                                delta = delta + timedelta(hours=6, seconds=3)
                                await self.client.send_message(
                                    chat, "реанимировать жабу", schedule=delta
                                )
                                await self.client.send_message(
                                    chat,
                                    "работа грабитель",
                                    schedule=delta + timedelta(seconds=randelta),
                                )
                                await self.client.send_message(
                                    chat,
                                    "завершить работу",
                                    schedule=delta
                                    + timedelta(hours=2, seconds=randelta + 3),
                                )
                                await sleep(3)
                        if "покормить через" in response.text:
                            time_n = re.search(
                                "покормить через (\d+)ч:(\d+)м",
                                response.text,
                                re.IGNORECASE,
                            )
                            if time_n:
                                hrs = int(time_n.group(1))
                                min = int(time_n.group(2))
                                delta = timedelta(
                                    hours=hrs, minutes=min, seconds=randelta
                                )
                            await self.client.send_message(
                                chat, "покормить жабку", schedule=delta
                            )
                        else:
                            delta = timedelta(seconds=randelta)
                            await self.client.send_message(
                                chat, "покормить жабку", schedule=delta
                            )
                        for number in range(1):
                            delta = delta + timedelta(hours=12, seconds=3)
                            await self.client.send_message(
                                chat, "покормить жабку", schedule=delta
                            )
                            await sleep(3)

            if name + " дуэлька" in message.message:
                if chatid in duel:
                    duel.pop(chatid)
                    self.db.set("Дуэлька", "duel", duel)
                    return await message.respond("<b>пью ромашковый чай</b>!")
                duel.setdefault(chatid, {})
                self.db.set("Дуэлька", "duel", duel)
                async with self.client.conversation(message.chat_id) as conv:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True, from_users=1124824021, chats=message.chat_id
                        )
                    )
                    await sleep(1)
                    await conv.send_message("моя жаба")
                    response = await response
                    if "Имя жабы:" in response.text:
                        jaba = re.search("Имя жабы: (.+)", response.text).group(1)
                self.status[jb] = jaba
                self.db.set("Status", "status", self.status)
                await message.respond(f"Имя жабы установлен: {jaba}\n го дуэли")
                await message.respond("РеанимироватЬ жабу")
            if name + " напади" in message.message:
                await message.respond("<b>реанимировать жабу</b>")
                await sleep(3)
                await message.respond("<b>напасть на клан</b>")
            if name + " подземелье" in message.message:
                await message.respond("<b>реанимировать жабу</b>")
                await sleep(3)
                await message.respond("<b>отправиться в золотое подземелье</b>")
            if name + " с работы" in message.message:
                await message.respond("<b>завершить работу</b>")
            if name + " карту" in message.message:
                await message.respond("<b>отправить карту</b>")
            if name + " за картой" in message.message:
                await message.respond("<b>отправиться за картой</b>")
            if name + " на тусу" in message.message:
                await message.respond("<b>реанимировать жабу</b>")
                await sleep(3)
                await message.respond("<b>жабу на тусу</b>")
            if message.sender_id not in {self.me.id}:
                if "букашки мне😊" in message.message:
                    await sleep(randelta)
                    async with self.client.conversation(chat) as conv:
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=message.chat_id,
                            )
                        )
                        await message.respond("мой баланс")
                        response = await response
                        if "Баланс букашек вашей" in response.text:
                            bug = int(
                                re.search(
                                    "жабы: (\d+)", response.text, re.IGNORECASE
                                ).group(1)
                            )
                            if bug < 100:
                                await message.reply("осталось для похода")
                            else:
                                while bug > 50049:
                                    await message.reply("отправить букашки 50000")
                                    bug -= 50000
                                    await sleep(1)
                                snt = bug - 50
                                await sleep(randelta)
                                await message.reply(f"отправить букашки {snt}")
                if "инвентарь мне😊" in message.message:
                    await sleep(randelta)
                    async with self.client.conversation(chat) as conv:
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=message.chat_id,
                            )
                        )
                        await message.respond("мой инвентарь")
                        response = await response
                        if "Ваш инвентарь:" in response.text:
                            cnd = int(
                                re.search(
                                    "Леденцы: (\d+)", response.text, re.IGNORECASE
                                ).group(1)
                            )
                            apt = int(
                                re.search(
                                    "Аптечки: (\d+)", response.text, re.IGNORECASE
                                ).group(1)
                            )
                            await sleep(randelta)
                        if cnd > 0:
                            while cnd > 49:
                                await message.reply("отправить леденцы 50")
                                cnd -= 50
                                await sleep(1)
                            await message.reply(f"отправить леденцы {cnd}")
                            await sleep(1)
                        if apt > 0:
                            if apt > 9:
                                await message.reply("отправить аптечки 10")
                            else:
                                await message.reply(f"отправить аптечки {apt}")

        if chatid not in duel:
            return

        if message.sender_id not in {self.me.id, 1124824021}:
            if "РеанимироватЬ жабу" in message.message:
                await sleep(1)
                await message.reply("дуэль")

        if message.sender_id in {1124824021}:
            if (
                "Вы бросили вызов на дуэль пользователю " + self.me.first_name
                in message.message
            ):
                await sleep(1)
                await message.respond("дуэль принять")
                await sleep(1)
                await message.respond("дуэль старт")

            if self.status[jb] + ", У вас ничья" in message.message:
                await sleep(1)
                await message.respond("РеанимироватЬ жабу")

            if "Победитель" in message.message:
                if self.status[jb] + "!!!" in message.message:
                    if "отыграл" in message.message:
                        duel.pop(chatid)
                        self.db.set("Дуэлька", "duel", duel)
                        return await message.respond("<b>пью ромашковый чай</b>!")
                    else:
                        return
                else:
                    await sleep(1)
                    await message.respond("РеанимироватЬ жабу")
