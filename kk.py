import asyncio
import datetime
import json
import logging
import random
import re
import time

import requests
from telethon import events, functions, types

from .. import loader, utils

logger = logging.getLogger(__name__)
asl = [
    "жаба дня",
    "топ жаб",
    "сезон кланов",
    "кланы",
    "взять жабу",
]


def register(cb):
    cb(kramiikkMod())


@loader.tds
class kramiikkMod(loader.Module):
    """Алина, я люблю тебя!"""

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
    bak = {
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
    }
    farms = {
        "Багoboty": -1001380664241,
        "Том Рэддл": -1001441941681,
        "Манулы и Зайчатки": -1001289617428,
        "Жаботорт": -1001436786642,
        ".": -1001409792751,
        "жабки нэлс(платон)": -1001165420047,
        "Дирижабль": -1001264330106,
        "Сказочный донатер": -1001648008859,
        "Листик": -1001685708710,
        "Жабы аферисты Крам и бабушка": -421815520,
        "Хэлло Вин!": -1001426018704,
        "Танцы по средам": -1001481051409,
        "IELTS": -1001492669520,
        "Домик в болоте": -1001520533176,
        "Космос нас ждет": -1001460270560,
        "Forbidden Frog": -1001511984124,
        "Vitoad": -1001771130958,
        "Курсы вышивания": -1001760342148,
        "Золотая жаба": -1001787904496,
        "LSDtoads": -1001493923839,
        "Цыганка": -1001714871513,
        "жабы лена": -1001419547228,
        "Жабочка": -1001666737591,
        "AstroFrog": -1001575042525,
        "Консилиум жаб": -1001777552705,
        "Жабьи монстрики": -1001427000422,
        "Жабы Вероны": -1001256439407,
        "Жабьи специи": -1001499700136,
        "Болотозавр": -1001624280659,
    }
    EK = {
        -1001441941681,
        -1001436786642,
        -1001380664241,
        -1001289617428,
        -1001485617300,
        -1001465870466,
        -1001169549362,
        -1001543064221,
    }
    KW = {-419726290, -1001543064221, -577735616, -1001493923839}
    ninja = {
        -1001380664241,
        -1001441941681,
        -1001289617428,
        -1001436786642,
        -1001465870466,
        -1001447960786,
        -1001290958283,
        -1001485617300,
    }

    def __init__(self):
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.me = await client.get_me()
        self.status = db.get("Status", "status", {})

    async def watcher(self, message):
        try:
            asly = random.choice(asl)
            nr = [11, 13, 17, 24, 33]
            rc = random.choice(nr)
            if "взять жабу" in asly:
                ac = rc * 3
            elif "топ жаб" in asly:
                ac = rc + 7
            elif "сезон кланов" in asly:
                ac = rc + 13
            elif "топ жаб" in asly:
                ac = rc + 21
            else:
                ac = rc + 33
            ai = self.me.id % 100 + ac
            if ai > 56:
                ai -= 42
            else:
                ai += 9
            ar = random.randint(rc, ac)
            if ar > ai:
                randelta = random.randint(ai, ar)
            else:
                randelta = random.randint(1, ac)
            if chat in EK:
                rc = 0.3
            ch = self.client.get_entity(message.to_id)
            chat = message.chat_id
            chatid = str(chat)
            duel = self.db.get("Дуэлька", "duel", {})
            name = "монарх"
            if (
                message.message.lower().startswith(
                    ("начать клановую", "@tgtoadbot начать клановую")
                )
            ) and chat in ninja:
                async with self.client.conversation(chat) as conv:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    response = await response
                    if "Отлично! Как только" in response.text:
                        txt = f"<i>{message.sender.first_name} в поиске"
                        nm = await self.client.send_message(1767017980, txt)
                        ch = await ch
                        txt += (
                            f"\nЧат: <i>{ch.title}</i>"
                        )
                        await utils.answer(nm, txt)
                        src = f"Chat id: {chat}\nUser id: {message.sender_id}\nУсилитель:"
                        ms = await self.client.get_messages(1655814348, search=src)
                        if ms.total == 0:
                            return
                        for i in ms:
                            klan = re.search("Клан: (.+)", i.message).group(1)
                            liga = re.search("Лига: (.+)", i.message).group(1)
                            usil = re.search(
                                "Усилитель: (.+)", i.message
                            ).group(1)
                        src = f"Топ 35 кланов {klan}"
                        ms = await self.client.get_messages(1441941681, search=src)
                        if ms.total == 0:
                            tdd = ""
                        else:
                            for i in ms:
                                ligz = re.search(
                                    "Топ 35 кланов (.+) сезона", i.message
                                ).group(1)
                                mest = re.search(f"(.+). 🛡(.+) \| {klan}", i.message)
                                if mest:
                                    mest1 = mest.group(1)
                                    mest2 = mest.group(2)
                            tdd = f"\nСезон: {ligz}\nМесто: {mest1}\nПобед: {mest2}"
                        txt += f"\nКлан: {klan}\nЛига: {liga}\nУсилитель: {usil}\n\n{tdd}"
                        return await utils.answer(nm, txt)
                    else:
                        return
            elif (
                message.message.startswith("Алло")
                and chat in ninja
                and message.sender_id in {1124824021}
            ):
                capt = re.search(
                    "клана (.+) нашелся враг (.+), пора", message.text
                )
                if capt:
                    mk = capt.group(1)
                    ek = capt.group(2)
                    war = f"{mk} против клана {ek}"
                    return await self.client.send_message(
                        1767017980, f"⚡️ Клан {war}"
                    )
                else:
                    return
            elif (
                f"Сейчас выбирает ход: {self.me.first_name}" in message.message
                and message.mentioned
                and message.sender_id in {1124824021}
            ):
                await message.click(1)
                await message.respond("реанимировать жабу")
                await asyncio.sleep(rc)
                return await message.respond("отправиться за картой")
            elif (
                message.message.lower().startswith(asly)
                and chat in EK
                and message.sender_id in bak
            ):
                await asyncio.sleep(randelta)
                sch = (
                    await self.client(
                        functions.messages.GetScheduledHistoryRequest(chat, 0)
                    )
                ).messages
                await self.client(
                    functions.messages.DeleteScheduledMessagesRequest(
                        chat, id=[x.id for x in sch]
                    )
                )
                async with self.client.conversation(message.chat_id) as conv:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    await conv.send_message("Отправиться в золотое подземелье")
                    response = await response
                    if "Ну-ка подожди," in response.text:
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=message.chat_id,
                            )
                        )
                        await conv.send_message("рейд инфо")
                        response = await response
                        if "Ребята в золотом" in response.text:
                            count = len(
                                re.findall(
                                    "• ",
                                    response.text.split(
                                        sep="Ребята в золотом подземелье:"
                                    )[1],
                                )
                            )
                            if count > 2:
                                await asyncio.sleep(randelta)
                                return await conv.send_message("рейд старт")
                        else:
                            return
                    elif "Для входа в" in response.text:
                        await conv.send_message("Моя жаба")
                        response = await response
                        if "Имя жабы:" in response.text:
                            bug = int(
                                re.search(
                                    "Букашки: (\d+)",
                                    response.text,
                                    re.IGNORECASE,
                                ).group(1)
                            )
                            nas = int(
                                re.search(
                                    "Настроение.?:.+\((\d+)\)",
                                    response.text,
                                    re.IGNORECASE,
                                ).group(1)
                            )
                            if nas < 500:
                                led = int((500 - nas) / 25)
                                if led > 0:
                                    return await conv.send_message(
                                        f"использовать леденцы {led}"
                                    )
                            else:
                                return
                        else:
                            return
                    else:
                        await conv.send_message("жаба инфо")
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=message.chat_id,
                            )
                        )
                        response = await response
                        if "(Откормить через" in response.text:
                            time_f = re.search(
                                "Откормить через (\d+)ч:(\d+)м",
                                response.text,
                                re.IGNORECASE,
                            )
                            if time_f:
                                hrs = int(time_f.group(1))
                                min = int(time_f.group(2))
                                delta = datetime.timedelta(
                                    hours=hrs, minutes=min, seconds=3
                                )
                                await conv.send_message(
                                    "откормить жабку", schedule=delta
                                )
                        else:
                            await conv.send_message("откормить жабку")
                            delta = datetime.timedelta(hours=4, seconds=3)
                            await conv.send_message("откормить жабку", schedule=delta)
                        for number in range(4):
                            delta = delta + datetime.timedelta(hours=4)
                            await conv.send_message("откормить жабку", schedule=delta)
                        if "В подземелье можно" in response.text:
                            dng_s = re.search(
                                "подземелье можно через (\d+)ч. (\d+)м.",
                                response.text,
                                re.IGNORECASE,
                            )
                            if dng_s:
                                hrs = int(dng_s.group(1))
                                min = int(dng_s.group(2))
                                delta = datetime.timedelta(
                                    hours=hrs, minutes=min, seconds=3
                                )
                                await conv.send_message(
                                    "реанимировать жабу", schedule=delta
                                )
                                await conv.send_message(
                                    "Отправиться в золотое подземелье",
                                    schedule=delta + datetime.timedelta(seconds=13),
                                )
                            await conv.send_message("Моя семья")
                            response = await response
                            if "Ваш жабёныш:" in response.text:
                                if "Можно покормить через" in response.text:
                                    sem = re.search(
                                        "покормить через (\d+) ч. (\d+) минут",
                                        response.text,
                                        re.IGNORECASE,
                                    )
                                    if sem:
                                        hrs = int(sem.group(1))
                                        min = int(sem.group(2))
                                    delta = datetime.timedelta(
                                        hours=hrs, minutes=min, seconds=3
                                    )
                                    await conv.send_message(
                                        "покормить жабенка",
                                        schedule=delta,
                                    )
                                else:
                                    await conv.send_message("покормить жабенка")
                                if "Можно забрать через" in response.text:
                                    sad = re.search(
                                        "забрать через (\d+) ч. (\d+) минут",
                                        response.text,
                                        re.IGNORECASE,
                                    )
                                    if sad:
                                        hrs = int(sad.group(1))
                                        min = int(sad.group(2))
                                        delta = datetime.timedelta(
                                            hours=hrs, minutes=min, seconds=3
                                        )
                                        await conv.send_message(
                                            "забрать жабенка",
                                            schedule=delta,
                                        )
                                else:
                                    await conv.send_message("забрать жабенка")
                                if "Пойти на махач" in response.text:
                                    sad = re.search(
                                        "махач через (\d+) ч. (\d+) минут",
                                        response.text,
                                        re.IGNORECASE,
                                    )
                                    if sad:
                                        hrs = int(sad.group(1))
                                        min = int(sad.group(2))
                                        delta = datetime.timedelta(
                                            hours=hrs, minutes=min, seconds=3
                                        )
                                        await conv.send_message(
                                            "отправить жабенка на махач",
                                            schedule=delta,
                                        )
                                else:
                                    await conv.send_message(
                                        "отправить жабенка на махач"
                                    )
                            await conv.send_message("война инфо")
                            response = await response
                            if "⚔️Состояние⚔️: Не" in response.text:
                                if message.chat_id in KW:
                                    return await conv.send_message(
                                        "начать клановую войну"
                                    )
                            else:
                                return
                        else:
                            dng_s = re.search(
                                "жабу можно через (\d+) часов (\d+) минут",
                                response.text,
                                re.IGNORECASE,
                            )
                            if dng_s:
                                hrs = int(dng_s.group(1))
                                min = int(dng_s.group(2))
                                delta = datetime.timedelta(
                                    hours=hrs, minutes=min, seconds=3
                                )
                                await conv.send_message(
                                    "завершить работу", schedule=delta
                                )
                                await conv.send_message(
                                    "реанимировать жабку",
                                    schedule=delta
                                    + datetime.timedelta(minutes=25, seconds=3),
                                )
                                return await conv.send_message(
                                    "Отправиться в золотое подземелье",
                                    schedule=delta
                                    + datetime.timedelta(minutes=45, seconds=13),
                                )
                            else:
                                return
            elif message.message.lower().startswith(asly) and message.sender_id in bak:
                await asyncio.sleep(randelta)
                sch = (
                    await self.client(
                        functions.messages.GetScheduledHistoryRequest(chat, 0)
                    )
                ).messages
                await self.client(
                    functions.messages.DeleteScheduledMessagesRequest(
                        chat, id=[x.id for x in sch]
                    )
                )
                async with self.client.conversation(message.chat_id) as conv:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    await conv.send_message("жаба инфо")
                    response = await response
                    if "покормить через" in response.text:
                        time_n = re.search(
                            "покормить через (\d+)ч:(\d+)м",
                            response.text,
                            re.IGNORECASE,
                        )
                        if time_n:
                            hrs = int(time_n.group(1))
                            min = int(time_n.group(2))
                            delta = datetime.timedelta(
                                hours=hrs, minutes=min, seconds=3
                            )
                            await conv.send_message("покормить жабку", schedule=delta)
                    else:
                        delta = datetime.timedelta(hours=6, seconds=3)
                        await conv.send_message("покормить жабку")
                    for number in range(3):
                        delta = delta + datetime.timedelta(hours=6, seconds=3)
                        await conv.send_message("покормить жабку", schedule=delta)
                    if "работу можно" in response.text:
                        time_j = re.search(
                            "будет через (\d+)ч:(\d+)м",
                            response.text,
                            re.IGNORECASE,
                        )
                        if time_j:
                            hrs = int(time_j.group(1))
                            min = int(time_j.group(2))
                            delta = datetime.timedelta(
                                hours=hrs, minutes=min, seconds=3
                            )
                            await conv.send_message(
                                "реанимировать жабу", schedule=delta
                            )
                            await conv.send_message(
                                "работа крупье",
                                schedule=delta + datetime.timedelta(seconds=13),
                            )
                        for number in range(2):
                            delta = delta + datetime.timedelta(hours=8)
                            await conv.send_message(
                                "реанимировать жабу", schedule=delta
                            )
                            await conv.send_message(
                                "работа крупье",
                                schedule=delta + datetime.timedelta(seconds=13),
                            )
                            await conv.send_message(
                                "завершить работу",
                                schedule=delta
                                + datetime.timedelta(hours=2, seconds=13),
                            )
                    if "жабу можно через" in response.text:
                        time_r = re.search(
                            "через (\d+) часов (\d+) минут",
                            response.text,
                            re.IGNORECASE,
                        )
                        if time_r:
                            hrs = int(time_r.group(1))
                            min = int(time_r.group(2))
                            delta = datetime.timedelta(
                                hours=hrs, minutes=min, seconds=3
                            )
                            await conv.send_message("завершить работу", schedule=delta)
                    elif "можно отправить" in response.text:
                        await conv.send_message("реанимировать жабу")
                        await conv.send_message("работа крупье")
                        delta = datetime.timedelta(hours=2, seconds=3)
                        await conv.send_message("завершить работу", schedule=delta)
                    else:
                        await conv.send_message("завершить работу")
                        delta = datetime.timedelta(hours=6)
                    for number in range(2):
                        delta = delta + datetime.timedelta(hours=6, seconds=3)
                        await conv.send_message("реанимировать жабу", schedule=delta)
                        await conv.send_message(
                            "работа крупье",
                            schedule=delta + datetime.timedelta(seconds=3),
                        )
                        await conv.send_message(
                            "завершить работу",
                            schedule=delta + datetime.timedelta(hours=2, seconds=13),
                        )
            elif "лвл чек" in message.message and message.sender_id in bak:
                x = int(message.message.split(" ", 3)[2])
                u = int(message.message.split(" ", 3)[3])
                y = ((x + u) - 160) * 2
                if y > -1:
                    res = f"<b>~ {y} лвл</b>"
                else:
                    res = f"<b>лвл не может быть отрицательным!!!\nпробуй заново, напиши:\n\n<code>лвл чек 160 90</code></b>"
                return await utils.answer(message, res)
            elif (
                message.message.lower().startswith((name, f"@{self.me.username}"))
                or name in message.message
                and message.message.endswith("😉")
            ) and message.sender_id in bak:
                await asyncio.sleep(rc)
                args = message.message
                reply = await message.get_reply_message()
                count = args.split(" ", 2)[1]
                if message.message.endswith("?"):
                    words = re.findall(r"\w+", f"{message.message}")
                    words_len = [words.__len__()] + [x.__len__() for x in words]
                    i = words_len.__len__()
                    while i > 1:
                        i -= 1
                        for x in range(i):
                            words_len[x] = (
                                words_len[x] + words_len[x + 1] - 3
                                if words_len[x] + words_len[x + 1] > 3
                                else words_len[x] + words_len[x + 1]
                            )
                    return await message.reply(
                        self.strings["quest_answer"].replace(
                            "%answer%", random.choice(self.answers[words_len[0]])
                        )
                    )
                elif "~" in message.message:
                    mmsg = args.split(" ", 2)[2]
                    await utils.answer(message, "поехали")
                    for farm_name, farm_id in self.farms.items():
                        await self.client.send_message(farm_id, mmsg)
                elif "напиши в " in message.message:
                    count = args.split(" ", 4)[3]
                    if count.isnumeric():
                        count = int(args.split(" ", 4)[3])
                    mmsg = args.split(" ", 4)[4]
                    await self.client.send_message(
                        1001714871513, f"{count} {mmsg} {chat}"
                    )
                    async with self.client.conversation(count) as conv:
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=count,
                            )
                        )
                        await conv.send_message(mmsg)
                        response = await response
                        await message.reply(response.message)
                elif "напади" in message.message:
                    async with self.client.conversation(chat) as conv:
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=message.chat_id,
                            )
                        )
                        await conv.send_message("напасть на клан")
                        response = await response
                        if "Ваша жаба на" in response.text:
                            await conv.send_message("завершить работу")
                            await conv.send_message("реанимировать жабу")
                            return await conv.send_message("напасть на клан")
                        elif "Ваша жаба сейчас" in response.text:
                            await conv.send_message("выйти из подземелья")
                            await conv.send_message("реанимировать жабу")
                            return await conv.send_message("напасть на клан")
                        else:
                            return
                elif "подземелье" in message.message:
                    async with self.client.conversation(chat) as conv:
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=message.chat_id,
                            )
                        )
                        await conv.send_message("отправиться в золотое подземелье")
                        response = await response
                        if "Пожалейте жабу," in response.text:
                            await conv.send_message("завершить работу")
                            await conv.send_message("реанимировать жабу")
                            return await conv.send_message(
                                "<b>отправиться в золотое подземелье</b>",
                            )
                        elif "Вы не можете отправиться" in response.text:
                            await conv.send_message("дуэль отклонить")
                            await conv.send_message("дуэль отозвать")
                            return conv.send_message(
                                "<b>отправиться в золотое подземелье</b>",
                            )
                        elif "Ваша жаба при" in response.text:
                            await conv.send_message("реанимировать жабу")
                            return await conv.send_message(
                                "<b>отправиться в золотое подземелье</b>",
                            )
                        else:
                            return
                elif "туса" in message.message:
                    await message.respond("жабу на тусу")
                elif "го кв" in message.message:
                    await message.respond("начать клановую войну")
                elif "снаряжение" in message.message:
                    async with self.client.conversation(chat) as conv:
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=message.chat_id,
                            )
                        )
                        await conv.send_message("мое снаряжение")
                        response = await response
                        if "Ближний бой: Отсутствует" in response.text:
                            await conv.send_message("скрафтить клюв цапли")
                        if "Дальний бой: Отсутствует" in response.text:
                            await conv.send_message("скрафтить букашкомет")
                        if "Наголовник: Отсутствует" in response.text:
                            await conv.send_message(
                                "скрафтить наголовник из клюва цапли",
                            )
                        if "Нагрудник: Отсутствует" in response.text:
                            await conv.send_message(
                                "скрафтить нагрудник из клюва цапли",
                            )
                        if "Налапники: Отсутствует" in response.text:
                            await conv.send_message(
                                "скрафтить налапники из клюва цапли",
                            )
                        if "Банда: Отсутствует" in response.text:
                            await conv.send_message("взять жабу")
                            response = await response
                            if "У тебя уже есть" in response.text:
                                await conv.send_message("собрать банду")
                            else:
                                return await conv.send_message(
                                    "взять жабу", schedule=datetime.timedelta(hours=2)
                                )
                        else:
                            return
                elif "дуэлька" in message.message:
                    if chatid in duel:
                        duel.pop(chatid)
                        self.db.set("Дуэлька", "duel", duel)
                        return await utils.answer(message, "<b>пью ромашковый чай</b>!")
                    duel.setdefault(chatid, {})
                    self.db.set("Дуэлька", "duel", duel)
                    async with self.client.conversation(message.chat_id) as conv:
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=message.chat_id,
                            )
                        )
                        await conv.send_message("моя жаба")
                        response = await response
                        if "Имя жабы:" in response.text:
                            jaba = re.search("Имя жабы: (.+)", response.text).group(1)
                            self.status["Имя Жабы"] = jaba
                            self.db.set("Status", "status", self.status)
                            return await conv.send_message("РеанимироватЬ жабу")
                        else:
                            return
                elif count.isnumeric() and reply:
                    count = int(args.split(" ", 3)[1])
                    mmsg = args.split(" ", 3)[3]
                    time = int(args.split(" ", 3)[2])
                    for _ in range(count):
                        await reply.reply(mmsg)
                        await asyncio.sleep(time)
                elif count.isnumeric():
                    count = int(args.split(" ", 3)[1])
                    mmsg = args.split(" ", 3)[3]
                    time = int(args.split(" ", 3)[2])
                    for _ in range(count):
                        await self.client.send_message(chat, mmsg)
                        await asyncio.sleep(time)
                else:
                    mmsg = args.split(" ", 2)[2]
                    if reply:
                        return await reply.reply(mmsg)
                    else:
                        return await utils.answer(message, mmsg)
            elif "букашки мне😊" in message.message and message.sender_id in bak:
                await asyncio.sleep(randelta)
                async with self.client.conversation(chat) as conv:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    await conv.send_message("мой баланс")
                    response = await response
                    if "Баланс букашек вашей" in response.text:
                        bug = int(
                            re.search(
                                "жабы: (\d+)", response.text, re.IGNORECASE
                            ).group(1)
                        )
                        if bug < 100:
                            return await utils.answer(message, "осталось для похода")
                        else:
                            while bug > 50049:
                                await utils.answer(message, "отправить букашки 50000")
                                bug -= 50000
                            snt = bug - 50
                            return await utils.answer(
                                message, f"отправить букашки {snt}"
                            )
                    else:
                        return
            elif "инвентарь мне😊" in message.message and message.sender_id in bak:
                await asyncio.sleep(randelta)
                async with self.client.conversation(chat) as conv:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    await conv.send_message("мой инвентарь")
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
                        if cnd > 0:
                            if cnd > 49:
                                await utils.answer(message, "отправить леденцы 50")
                            else:
                                await utils.answer(message, f"отправить леденцы {cnd}")
                        if apt > 0:
                            if apt > 9:
                                return await utils.answer(
                                    message, "отправить аптечки 10"
                                )
                            else:
                                return await utils.answer(
                                    message, f"отправить аптечки {apt}"
                                )
                        else:
                            return
                    else:
                        return
            elif "[8🐝]" in message.message and message.sender_id in {830605725}:
                return await message.click(0)
            elif "[4🐝]" in message.message and message.sender_id in {830605725}:
                return await message.click(0)
            elif "[2☢️🐝, 2🔴🐝," in message.message and message.sender_id in {
                830605725
            }:
                return await message.click(0)
            elif "Бзззз! С пасеки" in message.message and message.sender_id in {
                830605725
            }:
                return await message.click(0)
            elif "Фарма" in message.message and chat in {707693258}:
                return await self.client.send_message(
                    chat,
                    "Фарма",
                    schedule=datetime.timedelta(minutes=random.randint(1, 20)),
                )
            elif "НЕЗАЧЁТ!" in message.message and chat in {707693258}:
                args = [int(x) for x in message.text.split() if x.isnumeric()]
                randelta = random.randint(20, 60)
                if len(args) == 4:
                    delta = datetime.timedelta(
                        hours=args[1], minutes=args[2], seconds=args[3] + 13
                    )
                elif len(args) == 3:
                    delta = datetime.timedelta(
                        minutes=args[1], seconds=args[2] + 13
                    )
                elif len(args) == 2:
                    delta = datetime.timedelta(seconds=args[1] + 13)
                else:
                    pass
                sch = (
                    await self.client(
                        functions.messages.GetScheduledHistoryRequest(chat, 1488)
                    )
                ).messages
                await self.client(
                    functions.messages.DeleteScheduledMessagesRequest(
                        chat, id=[x.id for x in sch]
                    )
                )
                return await self.client.send_message(chat, "Фарма", schedule=delta)
            elif chatid in duel and message.sender_id not in {self.me.id, 1124824021}:
                if "РеанимироватЬ жабу" in message.message:
                    await asyncio.sleep(rc)
                    return await utils.answer(message, "дуэль")
                else:
                    return
            elif chatid in duel and message.sender_id in {1124824021}:
                if (
                    f"Вы бросили вызов на дуэль пользователю {self.me.first_name}"
                    in message.message
                ):
                    await asyncio.sleep(rc)
                    await message.respond("дуэль принять")
                    await asyncio.sleep(rc)
                    return await message.respond("дуэль старт")
                elif "Имя Жабы" in self.status:
                    if f"{self.status['Имя Жабы']}, У вас ничья" in message.message:
                        await asyncio.sleep(rc)
                        return await message.respond("РеанимироватЬ жабу")
                    elif "Победитель" in message.message:
                        if (
                            self.status["Имя Жабы"] in message.message
                            and "отыграл" in message.message
                        ):
                            duel.pop(chatid)
                            self.db.set("Дуэлька", "duel", duel)
                            await utils.answer(message, "<b>пью ромашковый чай</b>!")
                        elif self.status["Имя Жабы"] not in message.message:
                            await asyncio.sleep(rc)
                            await utils.answer(message, "РеанимироватЬ жабу")
                        else:
                            return
                    else:
                        return
                else:
                    return
            else:
                return
        except:
            return