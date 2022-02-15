import asyncio
import datetime
import logging
import random
import re

from telethon import events, functions

from .. import loader

logger = logging.getLogger(__name__)

bak = [
    1785723159,
    1261343954,
    1377037394,
    635396952,
    547639600,
    553299699,
    412897338,
    449434040,
    388412512,
]


@loader.tds
class KramiikkMod(loader.Module):
    """Алина, я люблю тебя."""

    answers = {
        0: ("Ответ тебе известен", "Ты знаешь лучше меня!", "Ответ убил!.."),
        1: ("Да, но есть помехи", "Может быть", "Вероятно", "Возможно", "Наверняка"),
        2: ("Есть помехи...", "Вряд ли", "Что-то помешает", "Маловероятно"),
        3: ("Нет, но пока", "Скоро!", "Жди!", "Пока нет"),
    }
    strings = {"name": "kramiikk", "quest_answer": "<i>%answer%</i>"}

    def __init__(self):
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.me = await client.get_me()

    async def tms(self, m, i):
        global MS
        MS = datetime.timedelta(
            hours=m.date.hour, minutes=m.date.minute, seconds=m.date.second
        ) - datetime.timedelta(
            hours=i.date.hour, minutes=i.date.minute, seconds=i.date.second
        )

    async def err(self, m, p):
        try:
            async with self.client.conversation(m.chat_id) as conv:
                global RSP
                RSP = await conv.wait_event(
                    events.NewMessage(from_users=1124824021, chats=m.chat_id, pattern=p)
                )
        except asyncio.exceptions.TimeoutError:
            pass

    async def watcher(self, m):
        name = "монарх"
        try:
            if m.message.startswith("Йоу,") and m.sender_id in {1124824021}:
                if "одержал" in m.text:
                    klan = re.search(r"клан (.+) одержал[\s\S]* (\d+):(\d+)!", m.text)
                else:
                    klan = re.search(r", (.+) в этот[\s\S]* (\d+):(\d+)", m.text)
                s = await self.client.get_messages(
                    1767017980, search=f"VS {klan.group(1)}"
                )
                for i in s:
                    await self.tms(m, i)
                    if (
                        datetime.timedelta(days=0, hours=4)
                        <= MS
                        < datetime.timedelta(days=0, hours=4, minutes=30)
                    ):
                        p = re.search(r"..(.+) <.+> (.+)", i.text)
                        chet = f"{klan.group(2)}:{klan.group(3)}"
                        tog = f"{p.group(1)} 🥳 {p.group(2)} 😢"
                        if (klan.group(1) == p.group(1) and "одержал" in m.text) or (
                            klan.group(1) != p.group(1) and "слабее" in m.text
                        ):
                            if int(klan.group(2)) < int(klan.group(3)):
                                chet = "".join(reversed(chet))
                        else:
                            if int(klan.group(2)) > int(klan.group(3)):
                                chet = "".join(reversed(chet))
                            tog = f"{p.group(1)} 😢 {p.group(2)} 🥳"
                        tog += f"\n<i>{chet}</i>"
                        await i.reply(tog)
                ms = re.findall(r"•(<.+?(\d+).+>)", m.text)
                tog = f"Chat id: {m.chat_id}\n\nСостав {klan.group(1)}:"
                for i in ms:
                    tog += f"\n{i[0]} {i[1]}"
                await self.client.send_message(1655814348, tog)
            elif m.message.casefold().startswith(
                ("моя жаба", "@toadbot моя жаба")
            ) and len(m.message) in {17, 8}:
                p = "🐸"
                await self.err(m, p)
                if "Имя жабы" in RSP.text:
                    reg = re.search(
                        r"жабы: (.+)[\s\S]*й жабы: (.+)[\s\S]*Класс: (.+)",
                        RSP.raw_text,
                    )
                    info = f"Chat id: {m.chat_id}\nUser id: {m.sender_id}\nЖаба: {reg.group(1)}\nУровень: {reg.group(2)}\nКласс: {reg.group(3)}"
                    await self.client.send_message(1655814348, info)
            elif m.message.casefold().startswith(
                ("начать клановую войну", "@toadbot начать клановую войну")
            ) and len(m.message) in {21, 30}:
                p = None
                await self.err(m, p)
                if not RSP.text.startswith(("Алло", "Ваш клан", "Для старта", "Чувак")):
                    src = f"{m.chat_id} {m.sender_id} Клан:"
                    lira = None
                    ms = await self.client.get_messages(1655814348, search=src)
                    for i in ms:
                        if "Усилитель:" in i.message:
                            klan = re.search(
                                r"Лига: (.+)\nУсилитель: (.+)\n\nКлан: (.+)", i.text
                            )
                            lira = f"{klan.group(3)}\nЛига: {klan.group(1)}\nУсилитель: {klan.group(2)}"
                        else:
                            klan = re.search(r"Клан: (.+)", i.text)
                            src = f"Топ 35 кланов {klan.group(1)}"
                            p = await self.client.get_messages(1782816965, search=src)
                            if p.total == 0:
                                return
                            for s in p:
                                lira = re.search(r"Топ 35 кланов (.+) лиге", s.message)
                                lira = f"{klan.group(1)}\nЛига: {lira.group(1)}"
                    if "деревян" not in lira.casefold():
                        await self.client.send_message(1767017980, f"В поиске {lira}")
            elif m.message.startswith("Алло") and m.sender_id in {1124824021}:
                klan = re.search(r"клана (.+) нашелся враг (.+), пора", m.text)
                src = f"Топ 35 кланов {klan.group(1)}"
                ms = await self.client.get_messages(1782816965, search=src)
                if ms.total == 0:
                    src = f"{m.chat_id} {klan.group(1)} Лига:"
                    p = await self.client.get_messages(1655814348, search=src)
                    if p.total == 0:
                        return
                    for i in p:
                        ms = re.search(r"Лига: (.+)", i.text).group(1)
                else:
                    for i in ms:
                        ms = re.search(r"Топ 35 кланов (.+) лиге", i.text).group(1)
                if "деревян" not in ms.casefold():
                    txt = f"⚡️{klan.group(1)} <b>VS</b> {klan.group(2)}\nЛига: {ms}"
                    await self.client.send_message(1767017980, txt)
                    capt = re.findall(r"<.+?id=(\d+)\">", m.text)
                    tog = f"Chat id: {m.chat_id}\nКлан: {klan.group(1)}\n\nСостав:"
                    for i in capt:
                        tog += f"\n{i}"
                    await self.client.send_message(1655814348, tog)
            elif m.message.casefold().startswith(("мой клан", "@toadbot мой клан")):
                p = "Клан"
                await self.err(m, p)
                klan = re.search(r"н (.+):[\s\S]*а: (.+)[\s\S]*ь: (.+)", RSP.text)
                info = f"Chat id: {m.chat_id}\nUser id: {m.sender_id}\nЛига: {klan.group(2)}\nУсилитель: {klan.group(3)}\n\nКлан: {klan.group(1)}"
                return await self.client.send_message(1655814348, info)
            elif (
                m.message.casefold().startswith((name, f"@{self.me.username}"))
            ) and m.sender_id in bak:
                args = m.text
                reply = await m.get_reply_message()
                count = args.split(" ", 2)[1]
                if m.raw_text.endswith("?"):
                    words = re.findall(r"\w+", f"{m.text}")
                    words_len = [words.__len__()] + [x.__len__() for x in words]
                    i = words_len.__len__()
                    while i > 1:
                        i -= 1
                        for s in range(i):
                            words_len[s] = (
                                words_len[s] + words_len[s + 1] - 3
                                if words_len[s] + words_len[s + 1] > 3
                                else words_len[s] + words_len[s + 1]
                            )
                    await m.reply(
                        self.strings["quest_answer"].replace(
                            "%answer%", random.choice(self.answers[words_len[0]])
                        )
                    )
                elif "напиши в" in m.message:
                    i = args.split(" ", 4)[3]
                    if i.isnumeric():
                        i = int(i)
                    s = args.split(" ", 4)[4]
                    if reply:
                        s = reply
                    await self.client.send_message(i, s)
                elif "арена" in m.message:
                    p = "•"
                    await self.client.send_message(m.chat_id, "<b>мои жабы</b>")
                    await self.err(m, p)
                    capt = re.findall(r"\| -100(\d+)", RSP.text)
                    for i in capt:
                        await self.client.send_message(
                            int(i), "<b>реанимировать жабу</b>"
                        )
                        await self.client.send_message(int(i), "<b>на арену</b>")
                elif "напади" in m.message:
                    await m.respond("напасть на клан")
                elif "подземелье" in m.message:
                    await m.respond("<b>отправиться в золотое подземелье</b>")
                elif "снаряжение" in m.message:
                    p = "Ваше"
                    await self.client.send_message(m.chat_id, "<b>мое снаряжение</b>")
                    await self.err(m, p)
                    if "Ближний бой: Пусто" in RSP.text:
                        await m.respond("скрафтить клюв цапли")
                    if "Дальний бой: Пусто" in RSP.text:
                        await m.respond("скрафтить букашкомет")
                    if "Наголовник: Пусто" in RSP.text:
                        await m.respond("скрафтить наголовник из клюва цапли")
                    if "Нагрудник: Пусто" in RSP.text:
                        await m.respond("скрафтить нагрудник из клюва цапли")
                    if "Налапники: Пусто" in RSP.text:
                        await m.respond("скрафтить налапники из клюва цапли")
                else:
                    mmsg = args.split(" ", 2)[2]
                    if reply:
                        await reply.reply(mmsg)
                    else:
                        await m.respond(mmsg)
            elif (
                f"Сейчас выбирает ход: {self.me.first_name}" in m.message and m.buttons
            ):
                await m.respond("реанимировать жабу")
                await m.click(0)
            elif m.sender_id in {830605725} and m.buttons and "Ваше уважение" not in m.message:
                await m.click(0)
            elif "НЕЗАЧЁТ!" in m.message and m.chat_id in {707693258}:
                args = [int(x) for x in m.text.split() if x.isnumeric()]
                delta = datetime.timedelta(hours=4)
                if len(args) == 4:
                    delta = datetime.timedelta(
                        hours=args[1], minutes=args[2], seconds=args[3] + 13
                    )
                elif len(args) == 3:
                    delta = datetime.timedelta(minutes=args[1], seconds=args[2] + 13)
                elif len(args) == 2:
                    delta = datetime.timedelta(seconds=args[1] + 13)
                for i in range(3):
                    delta = delta + datetime.timedelta(seconds=13)
                    await self.client.send_message(m.chat_id, "Фарма", schedule=delta)
            elif (
                m.message.casefold().startswith(("доброе утро", "спокойной ночи"))
                and m.sender_id in bak
            ):
                p = "🐸"
                await self.client.send_message(m.chat_id, "<b>моя жаба</b>")
                await self.err(m, p)
                jab = re.search(r"Уровень.+: (\d+)[\s\S]*Букашки: (\d+)", RSP.raw_text)
                if int(jab.group(1)) > 50 and int(jab.group(2)) > 2700:
                    p = "🏃‍♂️"
                    await self.client.send_message(m.chat_id, "<b>жаба инфо</b>")
                    await self.err(m, p)
                    if "(Откормить через" in RSP.text:
                        time_f = re.search(
                            r"Откормить через (\d+)ч:(\d+)м",
                            RSP.text,
                            re.IGNORECASE,
                        )
                        delta = datetime.timedelta(
                            hours=int(time_f.group(1)),
                            minutes=int(time_f.group(2)),
                            seconds=3,
                        )
                        await self.client.send_message(
                            m.chat_id, "откормить жабку", schedule=delta
                        )
                    else:
                        await self.client.send_message(m.chat_id, "откормить жабку")
                        delta = datetime.timedelta(hours=4, seconds=3)
                        await self.client.send_message(
                            m.chat_id, "откормить жабку", schedule=delta
                        )
                    for i in range(4):
                        delta = delta + datetime.timedelta(hours=4)
                        await self.client.send_message(
                            m.chat_id, "откормить жабку", schedule=delta
                        )
                    if "В подземелье можно" in RSP.text:
                        dng_s = re.search(
                            r"подземелье можно через (\d+)ч. (\d+)м.",
                            RSP.text,
                            re.IGNORECASE,
                        )
                        delta = datetime.timedelta(
                            hours=int(dng_s.group(1)),
                            minutes=int(dng_s.group(2)),
                            seconds=3,
                        )
                        await self.client.send_message(
                            m.chat_id, "реанимировать жабу", schedule=delta
                        )
                        await self.client.send_message(
                            m.chat_id,
                            "Отправиться в золотое подземелье",
                            schedule=delta + datetime.timedelta(seconds=13),
                        )
                        if int(dng_s.group(1)) > 1:
                            await m.respond("реанимировать жабу")
                            await m.respond("работа крупье")
                            delta = datetime.timedelta(hours=2, seconds=3)
                            await self.client.send_message(
                                m.chat_id, "завершить работу", schedule=delta
                            )
                        for i in range(2):
                            delta = delta + datetime.timedelta(hours=6, seconds=3)
                            await self.client.send_message(
                                m.chat_id, "реанимировать жабу", schedule=delta
                            )
                            await self.client.send_message(
                                m.chat_id,
                                "работа крупье",
                                schedule=delta + datetime.timedelta(seconds=3),
                            )
                            await self.client.send_message(
                                m.chat_id,
                                "завершить работу",
                                schedule=delta
                                + datetime.timedelta(hours=2, seconds=13),
                            )
                    elif "Забрать жабу можно" in RSP.text:
                        dng_s = re.search(
                            r"жабу можно через (\d+) часов (\d+) минут",
                            RSP.text,
                            re.IGNORECASE,
                        )
                        delta = datetime.timedelta(
                            hours=int(dng_s.group(1)),
                            minutes=int(dng_s.group(2)),
                            seconds=3,
                        )
                        await self.client.send_message(
                            m.chat_id, "завершить работу", schedule=delta
                        )
                        await self.client.send_message(
                            m.chat_id,
                            "реанимировать жабку",
                            schedule=delta + datetime.timedelta(minutes=25, seconds=3),
                        )
                        await self.client.send_message(
                            m.chat_id,
                            "Отправиться в золотое подземелье",
                            schedule=delta + datetime.timedelta(minutes=45, seconds=13),
                        )
                else:
                    p = "🍭"
                    await self.client.send_message(m.chat_id, "<b>жаба инфо</b>")
                    await self.err(m, p)
                    if "покормить через" in RSP.text:
                        time_n = re.search(
                            r"покормить через (\d+)ч:(\d+)м",
                            RSP.text,
                            re.IGNORECASE,
                        )
                        delta = datetime.timedelta(
                            hours=int(time_n.group(1)),
                            minutes=int(time_n.group(2)),
                            seconds=3,
                        )
                        await self.client.send_message(
                            m.chat_id, "покормить жабку", schedule=delta
                        )
                    else:
                        delta = datetime.timedelta(hours=6, seconds=3)
                        await m.respond("покормить жабку")
                    for i in range(3):
                        delta = delta + datetime.timedelta(hours=6, seconds=3)
                        await self.client.send_message(
                            m.chat_id, "покормить жабку", schedule=delta
                        )
                    if "работу можно" in RSP.text:
                        time = re.search(
                            r"будет через (\d+)ч:(\d+)м",
                            RSP.text,
                            re.IGNORECASE,
                        )
                        delta = datetime.timedelta(
                            hours=int(time.group(1)),
                            minutes=int(time.group(2)),
                            seconds=3,
                        )
                        await self.client.send_message(
                            m.chat_id, "реанимировать жабу", schedule=delta
                        )
                        await self.client.send_message(
                            m.chat_id,
                            "работа крупье",
                            schedule=delta + datetime.timedelta(seconds=13),
                        )
                        for i in range(2):
                            delta = delta + datetime.timedelta(hours=8)
                            await self.client.send_message(
                                m.chat_id, "реанимировать жабу", schedule=delta
                            )
                            await self.client.send_message(
                                m.chat_id,
                                "работа крупье",
                                schedule=delta + datetime.timedelta(seconds=13),
                            )
                            await self.client.send_message(
                                m.chat_id,
                                "завершить работу",
                                schedule=delta
                                + datetime.timedelta(hours=2, seconds=13),
                            )
                    if "жабу можно через" in RSP.text:
                        time = re.search(
                            r"через (\d+) часов (\d+) минут",
                            RSP.text,
                            re.IGNORECASE,
                        )
                        delta = datetime.timedelta(
                            hours=int(time.group(1)),
                            minutes=int(time.group(2)),
                            seconds=3,
                        )
                        await self.client.send_message(
                            m.chat_id, "завершить работу", schedule=delta
                        )
                    elif "можно отправить" in RSP.text:
                        await m.respond("реанимировать жабу")
                        await m.respond("работа крупье")
                        delta = datetime.timedelta(hours=2, seconds=3)
                        await self.client.send_message(
                            m.chat_id, "завершить работу", schedule=delta
                        )
                    else:
                        await m.respond("завершить работу")
                        delta = datetime.timedelta(hours=6)
                    for i in range(2):
                        delta = delta + datetime.timedelta(hours=6, seconds=3)
                        await self.client.send_message(
                            m.chat_id, "реанимировать жабу", schedule=delta
                        )
                        await self.client.send_message(
                            m.chat_id,
                            "работа крупье",
                            schedule=delta + datetime.timedelta(seconds=3),
                        )
                        await self.client.send_message(
                            m.chat_id,
                            "завершить работу",
                            schedule=delta + datetime.timedelta(hours=2, seconds=13),
                        )
        finally:
            return
