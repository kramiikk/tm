import asyncio
import datetime
import logging
import random
import re

from telethon import events, functions

from .. import loader

logger = logging.getLogger(__name__)

MS = None
RESPONSE = datetime.timedelta(hours=4, minutes=30)
bak = [
    1785723159,
    1261343954,
    1377037394,
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
        """.

        ----------

        """
        self.client = client
        self.db = db
        self.me = await client.get_me()

    async def err(self, m, p, s):
        """.

        ----------

        """
        async with self.client.conversation(m.chat_id) as conv:
            await s
            global RESPONSE
            RESPONSE = await conv.wait_event(
                events.NewMessage(from_users=1124824021, chats=m.chat_id, pattern=p)
            )
            await conv.cancel_all()

    async def ter(self, m, p):
        """.

        ----------

        """
        s = await self.client.get_messages(1767017980, search=p)
        global MS
        for MS in s:
            global RESPONSE
            RESPONSE = datetime.timedelta(
                hours=m.date.hour, minutes=m.date.minute, seconds=m.date.second
            ) - datetime.timedelta(
                hours=MS.date.hour, minutes=MS.date.minute, seconds=MS.date.second
            )

    async def watcher(self, m):
        """.

        ----------

        """
        name = "монарх"
        if ("Итоги" or "Эй, клан") in m.message and m.sender_id in {
            1124824021,
            1261343954,
        }:
            if "одержал" in m.message:
                klan = re.search(r"клан (.+) одержал[\s\S]* (\d+):(\d+)!", m.message)
            elif "слабее" in m.message:
                klan = re.search(r", (.+) в этот[\s\S]* (\d+):(\d+)", m.message)
            else:
                klan = re.search(r"клан (.+),", m.message)
            p = f"VS {klan.group(1)}"
            await self.ter(m, p)
            if (
                datetime.timedelta(days=0, hours=4)
                < RESPONSE
                < datetime.timedelta(days=0, hours=4, minutes=30)
            ):
                capt = re.search(r"⚡️(.+) VS (.+)", MS.message)
                chet = f"{klan.group(2)}:{klan.group(3)}"
                itog = f"{capt.group(1)} 🥳 {capt.group(2)} 😢"
                if (klan.group(1) == capt.group(1) and "одержал" in m.message) or (
                    klan.group(1) != capt.group(1) and "слабее" in m.message
                ):
                    if int(klan.group(2)) < int(klan.group(3)):
                        chet = "".join(reversed(chet))
                elif (klan.group(1) == capt.group(1) and "слабее" in m.message) or (
                    klan.group(1) != capt.group(1) and "одержал" in m.message
                ):
                    if int(klan.group(2)) > int(klan.group(3)):
                        chet = "".join(reversed(chet))
                    itog = f"{capt.group(1)} 😢 {capt.group(2)} 🥳"
                else:
                    itog = "победила любовь🏳️‍🌈"
                    chet = "🫂"
                itog += f"\n<i>{chet}</i>"
                await MS.reply(itog)
                capt = re.findall(r"•(<.+?(\d+).+>)", m.text)
                itog = f"Chat id: {m.chat_id}\n\nСостав {klan.group(1)}:"
                for i in capt:
                    itog += f"\n{i[0]} {i[1]}"
                await self.client.send_message(1655814348, itog)
        elif m.message.lower().startswith(
            ("начать клановую", "@tgtoadbot начать клановую")
        ):
            p = None
            s = self.client.send_message(1655814348, m.message)
            await self.err(m, p, s)
            if not RESPONSE.text.startswith(
                ("Алло", "Ваш клан", "Для старта", "Чувак")
            ):
                src = f"Chat id: {m.chat_id} {m.sender_id} Клан:"
                ms = await self.client.get_messages(1655814348, search=src)
                for i in ms:
                    liga = None
                    klan = re.search(r"Клан: (.+)", i.message).group(1)
                p = f"VS {klan}"
                await self.ter(m, p)
                if RESPONSE != datetime.timedelta(days=0, hours=0):
                    if "Усилитель:" in i.message:
                        p = re.search(r"Лига: (.+)\nУсилитель: (.+)", i.message)
                        liga = f"{p.group(1)}\nУсилитель: {p.group(2)}"
                    else:
                        src = f"Топ 35 кланов {klan}"
                        p = await self.client.get_messages(1782816965, search=src)
                        if p.total != 0:
                            return
                        for s in p:
                            liga = re.search(
                                r"Топ 35 кланов (.+) лиге", s.message
                            ).group(1)
                    if ("в деревянной" or "Деревянная") not in liga:
                        txt = f"В поиске {klan}\nЛига: {liga}"
                        await self.client.send_message(1767017980, txt)
        elif m.message.startswith("Алло") and m.sender_id in {1124824021}:
            klan = re.search(r"клана (.+) нашелся враг (.+), пора", m.text)
            p = f"VS {klan.group(1)}"
            await self.ter(m, p)
            if RESPONSE != datetime.timedelta(days=0, hours=0):
                src = f"Топ 35 кланов {klan.group(1)}"
                ms = await self.client.get_messages(1782816965, search=src)
                if ms.total == 0:
                    src = f"{m.chat_id} {klan.group(1)} Лига:"
                    ms = await self.client.get_messages(1655814348, search=src)
                    if ms.total != 0:
                        return
                    for i in ms:
                        ms = re.search(r"Лига: (.+)", i.message).group(1)
                else:
                    for i in ms:
                        ms = re.search(r"Топ 35 кланов (.+) лиге", i.message).group(1)
                        
                if ("в деревянной" or "Деревянная") not in ms:
                    txt = f"⚡️{klan.group(1)} <b>VS</b> {klan.group(2)}\nЛига: {ms}"
                    await self.client.send_message(1767017980, txt)
                    capt = re.findall(r"<.+?id=(\d+)\">", m.text)
                    itog = f"Chat id: {m.chat_id}\nКлан: {klan.group(1)}\n\nСостав:"
                    for i in capt:
                        itog += f"\n{i}"
                    await self.client.send_message(1655814348, itog)
        elif m.message.lower().startswith(("мой клан", "@tgtoadbot мой клан")):
            async with self.client.conversation(m.chat_id) as conv:
                response = conv.wait_event(
                    events.NewMessage(
                        incoming=True,
                        from_users=1124824021,
                        chats=m.chat_id,
                    )
                )
                response = await response
                if "Опыт" in response.text:
                    klan = re.search("Клан (.+):", response.text).group(1)
                    liga = re.search("Лига: (.+)", response.text).group(1)
                    usil = re.search("Усилитель: (.+)", response.text).group(1)
                    info = response.text
                    clj = re.search(
                        r"\n\W+ (.+)\n\W+ (.+)\n\W+ (.+)\n\W+ (.+)\n\W+ (.+)\n\n",
                        response.text,
                    )
                    if clj:
                        lid = clj.group(1)
                        ja1 = clj.group(2)
                        ja2 = clj.group(3)
                        ja3 = clj.group(4)
                        ja4 = clj.group(5)
                        info = f"Chat id: {m.chat_id}\nUser id: {m.sender_id}\nИмя: {m.sender.first_name}\nЛига: {liga}\nУсилитель: {usil}\n\nКлан: {klan}\n(лид): {lid}\n{ja1}\n{ja2}\n{ja3}:\n{ja4}"
                    return await self.client.send_message(1655814348, info)
        elif "захват топа" in m.message and m.sender_id in bak:
            args = m.message
            p = "⚔️"
            s = self.client.send_message(
                m.chat_id, "сезон кланов " + args.split(" ", 2)[2]
            )
            await self.err(m, p, s)
            result = re.findall(r"(\d+)\. 🛡(\d+) \| (.*)", RESPONSE.text)
            rep = "🧛🏿Захваченные в этом сезоне🧛🏿\n(Победы | Название | Наказание):"
            for i in result:
                src = f"{i[2]} Усилитель:"
                ms = await self.client.get_messages(1655814348, search=src)
                if ms.total != 0:
                    s = "<i>😈Захвачен</i>"
                else:
                    s = "<i>🌚Кто это...</i>"
                rep += f"\n{i[0]}.🛡{i[1]} | {i[2]} | {s}"
            await RESPONSE.reply(rep)
        elif (
            m.message.lower().startswith((name, f"@{self.me.username}"))
            or (name in m.message and m.message.endswith("😉"))
        ) and m.sender_id in bak:
            await asyncio.sleep(random.randint(1, 13))
            args = m.message
            reply = await m.get_reply_message()
            count = args.split(" ", 2)[1]
            if m.message.endswith("?"):
                words = re.findall(r"\w+", f"{m.message}")
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
            elif "реплай" in m.message:
                i = args.split(" ", 4)[2]
                if i.isnumeric():
                    i = int(i)
                p = args.split(" ", 4)[3]
                if p.isnumeric():
                    p = int(p)
                i = await self.client.get_messages(i, ids=p)
                s = args.split(" ", 4)[4]
                if reply:
                    s = reply
                await i.reply(s)
            elif "reply" in m.message:
                await m.respond(reply)
            elif "напади" in m.message:
                p = None
                s = self.client.send_message(m.chat_id, "<b>напасть на клан</b>")
                await self.err(m, p, s)
                if "Ваша жаба на" in RESPONSE.text:
                    await m.respond("завершить работу")
                    await m.respond("реанимировать жабу")
                    await m.respond("напасть на клан")
                elif "Ваша жаба сейчас" in RESPONSE.text:
                    await m.respond("выйти из подземелья")
                    await m.respond("реанимировать жабу")
                    await m.respond("напасть на клан")
            elif "подземелье" in m.message:
                p = None
                s = self.client.send_message(
                    m.chat_id, "<b>отправиться в золотое подземелье</b>"
                )
                await self.err(m, p, s)
                if "Пожалейте жабу," in RESPONSE.text:
                    await m.respond("завершить работу")
                    await m.respond("реанимировать жабу")
                    await m.respond("<b>отправиться в золотое подземелье</b>")
                elif "Ваша жаба при" in RESPONSE.text:
                    await m.respond("реанимировать жабу")
                    await m.respond("<b>отправиться в золотое подземелье</b>")
                else:
                    await m.respond("<b>рейд инфо</b>")
            elif "снаряжение" in m.message:
                p = "Ваше"
                s = self.client.send_message(m.chat_id, "<b>мое снаряжение</b>")
                await self.err(m, p, s)
                if "Ближний бой: Пусто" in RESPONSE.text:
                    await m.respond("скрафтить клюв цапли")
                if "Дальний бой: Пусто" in RESPONSE.text:
                    await m.respond("скрафтить букашкомет")
                if "Наголовник: Пусто" in RESPONSE.text:
                    await m.respond("скрафтить наголовник из клюва цапли")
                if "Нагрудник: Пусто" in RESPONSE.text:
                    await m.respond("скрафтить нагрудник из клюва цапли")
                if "Налапники: Пусто" in RESPONSE.text:
                    await m.respond("скрафтить налапники из клюва цапли")
                else:
                    await m.respond("мой инвентарь")
            elif m.message.lower().startswith("лвл чек"):
                s = (
                    (int(m.message.split(" ", 3)[2]) + int(m.message.split(" ", 3)[3]))
                    - 160
                ) * 2
                if s > -1:
                    await m.reply(f"<b>~ {s} лвл</b>")
            elif "туса" in m.message:
                await m.respond("жабу на тусу")
            elif "го кв" in m.message:
                await m.respond("начать клановую войну")
            elif count.isnumeric() and reply:
                count = int(args.split(" ", 3)[1])
                mmsg = args.split(" ", 3)[3]
                time = int(args.split(" ", 3)[2])
                for i in range(count):
                    await reply.reply(mmsg)
                    await asyncio.sleep(time)
            elif count.isnumeric():
                count = int(args.split(" ", 3)[1])
                mmsg = args.split(" ", 3)[3]
                time = int(args.split(" ", 3)[2])
                for i in range(count):
                    await m.reply(mmsg)
                    await asyncio.sleep(time)
            else:
                mmsg = args.split(" ", 2)[2]
                if reply:
                    await reply.reply(mmsg)
                else:
                    await m.respond(mmsg)
        elif m.message.lower().startswith("букашки мне😊") and m.sender_id in bak:
            await asyncio.sleep(random.randint(1, 13))
            p = "Баланс"
            s = self.client.send_message(m.chat_id, "<b>мой баланс</b>")
            await self.err(m, p, s)
            bug = int(re.search(r"жабы: (\d+)", RESPONSE.text, re.IGNORECASE).group(1))
            if bug < 100:
                await m.reply("осталось для похода")
            else:
                while bug > 50049:
                    await m.reply("отправить букашки 50000")
                    bug -= 50000
                snt = bug - 50
                await m.reply(f"отправить букашки {snt}")
        elif m.message.lower().startswith("инвентарь мне😊") and m.sender_id in bak:
            await asyncio.sleep(random.randint(1, 13))
            p = "Ваш"
            s = self.client.send_message(m.chat_id, "<b>мой инвентарь</b>")
            await self.err(m, p, s)
            cnd = int(
                re.search(r"Леденцы: (\d+)", RESPONSE.text, re.IGNORECASE).group(1)
            )
            apt = int(
                re.search(r"Аптечки: (\d+)", RESPONSE.text, re.IGNORECASE).group(1)
            )
            if cnd > 0:
                if cnd > 49:
                    await m.reply("отправить леденцы 50")
                else:
                    await m.reply(f"отправить леденцы {cnd}")
                if apt > 9:
                    await m.reply("отправить аптечки 10")
                else:
                    await m.reply(f"отправить аптечки {apt}")
        elif "сейчас в кв" in m.message:
            ms = await self.client.get_messages(1767017980, limit=42)
            s = "<b>Сейчас в кв:\n</b>"
            for i in ms:
                delta = datetime.timedelta(
                    hours=m.date.hour, minutes=m.date.minute, seconds=m.date.second
                ) - datetime.timedelta(
                    hours=i.date.hour, minutes=i.date.minute, seconds=i.date.second
                )
                if "VS" in i.message and datetime.timedelta(
                    days=0
                ) <= delta < datetime.timedelta(hours=4, minutes=3):
                    s += f"\n{i.message}\n<i>Время кв: {delta}</i>\n"
            await m.edit(s)
        elif f"Сейчас выбирает ход: {self.me.first_name}" in m.message and m.buttons:
            await m.respond("реанимировать жабу")
            await m.click(0)
        elif (
            "[8🐝]" or "[4🐝]" or "[2☢️🐝, 2🔴🐝," or "Бзззз! С пасеки"
        ) in m.message and m.buttons:
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
            m.message.lower().startswith(("доброе утро", "спокойной ночи"))
            and m.sender_id in bak
        ):
            sch = (
                await self.client(
                    functions.messages.GetScheduledHistoryRequest(m.chat_id, 0)
                )
            ).messages
            await self.client(
                functions.messages.DeleteScheduledMessagesRequest(
                    m.chat_id, id=[x.id for x in sch]
                )
            )
            p = "🐸"
            s = self.client.send_message(m.chat_id, "<b>моя жаба</b>")
            await self.err(m, p, s)
            jaba = re.search(r"Уровень.+: (\d+)[\s\S]*Букашки: (\d+)", RESPONSE.text)
            if int(jaba.group(1)) > 50 and int(jaba.group(2)) > 2700:
                p = "🍭"
                s = self.client.send_message(m.chat_id, "<b>жаба инфо</b>")
                await self.err(m, p, s)
                if "(Откормить через" in RESPONSE.text:
                    time_f = re.search(
                        r"Откормить через (\d+)ч:(\d+)м",
                        RESPONSE.text,
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
                if "В подземелье можно" in RESPONSE.text:
                    dng_s = re.search(
                        r"подземелье можно через (\d+)ч. (\d+)м.",
                        RESPONSE.text,
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
                            schedule=delta + datetime.timedelta(hours=2, seconds=13),
                        )
                elif "Забрать жабу можно" in RESPONSE.text:
                    dng_s = re.search(
                        r"жабу можно через (\d+) часов (\d+) минут",
                        RESPONSE.text,
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
                s = self.client.send_message(m.chat_id, "<b>жаба инфо</b>")
                await self.err(m, p, s)
                if "покормить через" in RESPONSE.text:
                    time_n = re.search(
                        r"покормить через (\d+)ч:(\d+)м",
                        RESPONSE.text,
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
                if "работу можно" in RESPONSE.text:
                    time = re.search(
                        r"будет через (\d+)ч:(\d+)м",
                        RESPONSE.text,
                        re.IGNORECASE,
                    )
                    delta = datetime.timedelta(
                        hours=int(time.group(1)), minutes=int(time.group(2)), seconds=3
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
                            schedule=delta + datetime.timedelta(hours=2, seconds=13),
                        )
                if "жабу можно через" in RESPONSE.text:
                    time = re.search(
                        r"через (\d+) часов (\d+) минут",
                        RESPONSE.text,
                        re.IGNORECASE,
                    )
                    delta = datetime.timedelta(
                        hours=int(time.group(1)), minutes=int(time.group(2)), seconds=3
                    )
                    await self.client.send_message(
                        m.chat_id, "завершить работу", schedule=delta
                    )
                elif "можно отправить" in RESPONSE.text:
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

                # if message.message.lower().startswith(
                #     ("моя жаба", "@tgtoadbot моя жаба")
                # ):
                #     async with self.client.conversation(chat) as conv:
                #         response = conv.wait_event(
                #             events.NewMessage(
                #                 incoming=True,
                #                 from_users=1124824021,
                #                 chats=message.chat_id,
                #             )
                #         )
                #         response = await response
                #         if "Имя жабы:" in response.text:
                #             imy = re.search("Имя жабы: (.+)",
                #                             response.text).group(1)
                #             urv = re.search("вашей жабы: (.+)",
                #                             response.text).group(1)
                #             cll = re.search(
                #                 "Класс: (.+)", response.text).group(1)
                #             info = f"Chat id: {chat}\nUser id: {message.sender_id}\nЖаба: {imy}\nУровень: {urv}\nКласс: {cll}\n{message.sender.first_name}"
                #             return await self.client.send_message(OPPY, info)
                # if message.message.lower().startswith(
                #     ("мое снаряжение", "@tgtoadbot мое снаряжение")
                # ):
                #     async with self.client.conversation(chat) as conv:
                #         response = conv.wait_event(
                #             events.NewMessage(
                #                 incoming=True,
                #                 from_users=1124824021,
                #                 chats=message.chat_id,
                #             )
                #         )
                #         response = await response
                #         if "Ваше снаряжение:" in response.text:
                #             snr = re.search(
                #                 "(.+)\n(.+)\n(.+)\n(.+)\n(.+)\n(.+)\n(.+)\n\n.+\n.+\n.+\n.+\n\n(.+)\n(.+)\n(.+)",
                #                 response.text,
                #             )
                #             if snr:
                #                 aa = snr.group(1)
                #                 a1 = snr.group(2)
                #                 a2 = snr.group(3)
                #                 a3 = snr.group(4)
                #                 a4 = snr.group(5)
                #                 a5 = snr.group(6)
                #                 a6 = snr.group(7)
                #                 a7 = snr.group(8)
                #                 a8 = snr.group(9)
                #                 a9 = snr.group(10)
                #             info = f"Chat id: {chat}\nUser id: {message.sender_id}\nИмя: {message.sender.first_name}\\n\nСнаряжение:\n{aa}\n{a1}\n{a2}\n{a3}\n{a4}\n\n{a5}\n{a6}\n{a7}\n{a8}\n{a9}"
                #             return await self.client.send_message(OPPY, info)
                # if message.message.lower().startswith(
                #     ("напасть на клан", "@tgtoadbot напасть на клан")
                # ):
                #     async with self.client.conversation(chat) as conv:
                #         response = conv.wait_event(
                #             events.MessageEdited(
                #                 incoming=True,
                #                 from_users=1124824021,
                #                 chats=chat,
                #             )
                #         )
                #         response = await response
                #         if "1 атака" in response.text:
                #             jbb = re.search(
                #                 "а (.+):\n.+: (.+) \n.+\n.+: (\d+)\n\n.+а (.+):\n.+: (.+) \n.+\n.+: (\d+)$",
                #                 response.text,
                #             )
                #             if jbb:
                #                 jn = jbb.group(1)
                #                 ur = jbb.group(2)
                #                 zd = jbb.group(3)
                #                 jn1 = jbb.group(4)
                #                 ur1 = jbb.group(5)
                #                 zd1 = jbb.group(6)
                #                 x = int(ur)
                #                 u = int(zd)
                #                 y = ((x + u) - 160) * 2
                #                 x1 = int(ur1)
                #                 u1 = int(zd1)
                #                 y1 = ((x1 + u1) - 160) * 2
                #             info = f"Chat id: {chat}\nUser id: {message.sender_id}\nЖаба: {jn}\nУровень: ~{y+1}\n\nЖаба противника: {jn1}\nУровень: ~{y1+1}"
                #             mf = await self.client.send_message(OPPY, info)
                #             response1 = await conv.wait_event(
                #                 events.NewMessage(
                #                     incoming=True,
                #                     from_users=1124824021,
                #                     chats=message.chat_id,
                #                 )
                #             )
                #             if f"Победитель {jn}!!!" in response1.text:
                #                 info += f"\n\n<b>Победитель {jn}!!!</b>"
                #             elif f"Победитель {jn1}!!!" in response1.text:
                #                 info += f"\n\n<b>Победитель {jn1}!!!</b>"
                #             await mf.edit(info)
