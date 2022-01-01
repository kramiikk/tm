import asyncio
import datetime
import logging
import random
import re

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
    -1001465870466,
    -1001447960786,
    -1001290958283,
    -1001485617300,
]
nr = [11, 13, 17, 24, 33]


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
            chat = message.chat_id
            chatid = str(chat)
            duel = self.db.get("Дуэлька", "duel", {})
            name = "монарх"
            rc = random.choice(nr)
            if "взять жабу" in asly:
                ac = 3
            elif "топ жаб" in asly:
                ac = 7
            elif "клан сезон" in asly:
                ac = 13
            elif "кланы" in asly:
                ac = 21
            else:
                ac = 33
            if 21 > rc:
                randelta = random.randint(rc + ac, 42)
            else:
                randelta = random.randint(3, rc)
            if chat in elj:
                rc = 0.3
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
                        src = f"Chat id: {chat} {message.sender_id} Клан:"
                        ms = await self.client.get_messages(1655814348, search=src)
                        if ms.total == 0:
                            return await self.client.send_message(
                                1767017980,
                                f"<i>В поиске {message.sender.first_name}</i>",
                            )
                        for i in ms:
                            klan = re.search("Клан: (.+)", i.message).group(1)
                            if "Усилитель:" in i.message:
                                liga = re.search("Лига: (.+)", i.message).group(1)
                                usil = re.search("Усилитель: (.+)", i.message).group(1)
                                lif = f"\nЛига: {liga}\nУсилитель: {usil}"
                            else:
                                src = f"Топ 35 кланов {klan}"
                                ms = await self.client.get_messages(
                                    1782816965, search=src
                                )
                                for i in ms:
                                    liga = re.search(
                                        "Топ 35 кланов (.+) сезона", i.message
                                    ).group(1)
                                    lif = f"\nЛига: {liga}"
                        txt = f"В поиске {klan}{lif}"
                        nm = await self.client.send_message(1767017980, txt)
                    else:
                        return
            elif (
                message.message.startswith("Алло")
                and chat in ninja
                and message.sender_id in {1124824021}
            ):
                capt = re.search("клана (.+) нашелся враг (.+), пора", message.text)
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
                                "Топ 35 кланов (.+) сезона", i.message
                            ).group(1)
                    txt += f"\nЛига: {liga}"
                    return await utils.answer(nm, txt)
                else:
                    return
            elif (
                f"Сейчас выбирает ход: {self.me.first_name}" in message.message
                and message.mentioned
                and message.sender_id in {1124824021}
            ):
                await message.respond("реанимировать жабу")
                return await message.click(1)
            elif (
                message.message.lower().startswith(asly)
                and chat in elj
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
                        for i in range(4):
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
                                if message.chat_id in klw:
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
                    for i in range(3):
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
                        for i in range(2):
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
                    for i in range(2):
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
            elif (
                message.message.lower().startswith("лвл чек")
                and message.sender_id in bak
            ):
                x = int(message.message.split(" ", 3)[2])
                u = int(message.message.split(" ", 3)[3])
                y = ((x + u) - 160) * 2
                if y > -1:
                    res = f"<b>~ {y} лвл</b>"
                else:
                    return
                return await utils.answer(message, res)
            elif (
                message.message.lower().startswith((name, f"@{self.me.username}"))
                or (name in message.message and message.message.endswith("😉"))
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
            elif (
                message.message.lower().startswith("букашки мне😊")
                and message.sender_id in bak
            ):
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
            elif (
                message.message.lower().startswith("инвентарь мне😊")
                and message.sender_id in bak
            ):
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
            elif "[8🐝]" in message.message and message.sender_id in {830605725}:
                return await message.click(0)
            elif "[4🐝]" in message.message and message.sender_id in {830605725}:
                return await message.click(0)
            elif "[2☢️🐝, 2🔴🐝," in message.message and message.sender_id in {830605725}:
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
                    delta = datetime.timedelta(minutes=args[1], seconds=args[2] + 13)
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
            else:
                return
        except:
            return
