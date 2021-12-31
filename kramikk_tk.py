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


def register(cb):
    cb(KramikkMod())


@loader.tds
class KramikkMod(loader.Module):
    """Алина, я люблю тебя!"""

    strings = {
        "name": "Kramikk",
    }

    def __init__(self):
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.me = await client.get_me()
        self.status = db.get("Status", "status", {})

        #
        # async def statacmd(m):
        #     ph = str((await client.get_messages(m, search='ваш клан Том Рэддл одержал')).total)
        #     vi = str((await client.get_messages(m, search='клана Том Рэддл нашелся враг Вадим')).total)
        #     await client.send_message(m,
        #         ("<i>Неполные сведения, часть сообщений чата скрытые</i>\n<b>🏆Том Рэддл одержал побед:</b> {}\n" +
        #          "<b>⚜️кв Рэддла с Вадимом:</b> {}\n").format(ph, vi))
        # async def feets():
        #     await statacmd(OPPY)
        # scheduler = AsyncIOScheduler()
        # scheduler.add_job(feets, CronTrigger.from_crontab('*/33 * * * *', timezone='Asia/Almaty'))
        # scheduler.start()
        # asyncio.get_event_loop().run_forever()

    async def watcher(self, message):
        try:
            asly = random.choice(asl)
            bak = {
                1709411724,
                1261343954,
                1785723159,
                1486632011,
                547639600,
                449434040,
                388412512,
                553299699,
                412897338,
            }
            ch = message.client.get_entity(message.to_id)
            chat = message.chat_id
            chatid = str(chat)
            duel = self.db.get("Дуэлька", "duel", {})
            ninja = {
                -1001380664241,
                -1001441941681,
                -1001289617428,
                -1001436786642,
                -1001465870466,
                -1001447960786,
                -1001290958283,
                -1001485617300,
                -1001484924016,
            }
            nr = [11, 13, 17, 24, 33]
            OPPY = -1001655814348
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
            if ai > 81:
                ai -= 42
            else:
                ai += 27
            ar = random.randint(1, 131)
            if ar > ai:
                randelta = random.randint(ai, ar)
            else:
                randelta = random.randint(3, ac)
            
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
                        txt = f"<i>{message.sender.first_name} в поиске</i>"
                        nm = await self.client.send_message(1655814348, txt)
                        ch = await ch
                        src = (
                            f"Chat id: {chat}\nUser id: {message.sender_id}\nУсилитель:"
                        )
                        ms = await self.client.get_messages(1655814348, search=src)
                        if ms.total == 0:
                            src = f"Chat id: {chat}\nUser id: {message.sender_id}\nИмя жабы:"
                            ms2 = await self.client.get_messages(1655814348, search=src)
                            for i in ms2:
                                jbn = re.search(
                                    "Имя жабы: (.+)", i.message).group(1)
                            src = f"Chat id: {chat}\nКлан: {jbn}"
                            ms3 = await self.client.get_messages(1655814348, search=src)
                            for i in ms3:
                                klan = re.search(
                                    "Клан: (.+)", i.message).group(1)
                        for i in ms:
                            klan = re.search("Клан: (.+)", i.message).group(1)
                            if "Усилитель:" in i.message:
                                liga = re.search(
                                    "Лига: (.+)", i.message).group(1)
                                usil = re.search(
                                    "Усилитель: (.+)", i.message).group(1)
                                txt += f"\nЧат: {ch.title}\nКлан: {klan}\nЛига: {liga}\nУсилитель: {usil}"
                            else:
                                src = f"Топ 35 кланов {klan}"
                                ms1 = await self.client.get_messages(
                                    1441941681, search=src
                                )
                                for i in ms1:
                                    liga = re.search(
                                        "Топ 35 кланов (.+) сезона", i.message
                                    ).group(1)
                                    txt += (
                                        f"\nЧат: {ch.title}\nКлан: {klan}\nЛига: {liga}"
                                    )
                        return await utils.answer(nm, txt)
                    else:
                        return
            elif (
                message.message.startswith("Алло")
                and chat in ninja
                and message.sender_id in {1124824021}
            ):
                capt = re.search(
                    "клана (.+) нашелся враг (.+), пора .+\n(<.+?(\d+).+>), (<.+=(\d+).+>), (<.+=(\d+).+>), (<.+=(\d+).+>), (<.+=(\d+).+>)",
                    message.text,
                )
                if capt:
                    id0 = capt.group(12)
                    ja0 = capt.group(11)
                    id1 = capt.group(10)
                    ja1 = capt.group(9)
                    id2 = capt.group(8)
                    ja2 = capt.group(7)
                    id3 = capt.group(6)
                    ja3 = capt.group(5)
                    id4 = capt.group(4)
                    ja4 = capt.group(3)
                    ek = capt.group(2)
                    mk = capt.group(1)
                    war = f"{mk} против клана {ek}"
                    m = await self.client.send_message(1655814348, f"⚡️ Клан {war}")
                    war += f"\nChat id: {chat}\n<b>Клан: {mk}</b>\n{ja0} {id0}\n{ja1} {id1}\n{ja2} {id2}\n{ja3} {id3}\n{ja4} {id4}"
                    return await utils.answer(m, war)
                else:
                    return
            elif (
                message.message.lower().startswith(("мой клан", "@tgtoadbot мой клан"))
                and chat in ninja
            ):
                async with self.client.conversation(chat) as conv:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    response = await response
                    if "Опыт" in response.text:
                        ch = await ch
                        klan = re.search("Клан (.+):", response.text).group(1)
                        liga = re.search("Лига: (.+)", response.text).group(1)
                        usil = re.search("Усилитель: (.+)",
                                         response.text).group(1)
                        info = response.text
                        clj = re.search(
                            "\n\W+ (.+)\n\W+ (.+)\n\W+ (.+)\n\W+ (.+)\n\W+ (.+)\n\n",
                            response.text,
                        )
                        if clj:
                            lid = clj.group(1)
##                            src = f"Chat id: {chat}\nИмя жабы: {lid}"
##                            ms = await self.client.get_messages(1655814348, search=src)
##                            if ms.total == 0:
##                                urv0 = "~"
##                                cll0 = "~"
##                            else:
##                                for i in ms:
##                                    lid = re.search(
##                                        "Имя: (.+)", i.message).group(1)
##                                    urv0 = re.search("Уровень: (.+)", i.message).group(
##                                        1
##                                    )
##                                    cll0 = re.search(
##                                        "Класс: (.+)", i.message).group(1)
                            ja1 = clj.group(2)
                            ja2 = clj.group(3)
                            ja3 = clj.group(4)
                            ja4 = clj.group(5)
                            info = f"Chat id: {chat}\nUser id: {message.sender_id}\nЧат: {ch.title}\nИмя: {message.sender.first_name}\nЛига: {liga}\nУсилитель: {usil}\n\nКлан: {klan}\n(лид): {lid}\n{ja1}\n{ja2}\n{ja3}:\n{ja4}"
                        return await self.client.send_message(OPPY, info)
                    else:
                        return
            elif (
                message.message.lower().startswith(("моя жаба", "@tgtoadbot моя жаба"))
                and chat in ninja
            ):
                async with self.client.conversation(chat) as conv:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    response = await response
                    if "Имя жабы:" in response.text:
                        ch = await ch
                        imy = re.search("Имя жабы: (.+)",
                                        response.text).group(1)
                        urv = re.search("вашей жабы: (.+)",
                                        response.text).group(1)
                        cll = re.search("Класс: (.+)", response.text).group(1)
                        syt = re.search("Сытость: (.+)",
                                        response.text).group(1)
                        byk = re.search("Букашки: (.+)",
                                        response.text).group(1)
                        info = f"Chat id: {chat}\nUser id: {message.sender_id}\nИмя жабы: {imy}\nУровень: {urv}\nСытость: {syt}\nКласс: {cll}\nБукашки: {byk}\nИмя: {message.sender.first_name}\nЧат: {ch.title}"
                        return await self.client.send_message(OPPY, info)
                    else:
                        return
            elif (
                message.message.lower().startswith(
                    ("мое снаряжение", "@tgtoadbot мое снаряжение")
                )
                and chat in ninja
            ):
                async with self.client.conversation(chat) as conv:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    response = await response
                    if "Ваше снаряжение:" in response.text:
                        ch = await ch
                        snr = re.search(
                            "(.+)\n(.+)\n(.+)\n(.+)\n(.+)\n(.+)\n(.+)\n\n.+\n.+\n.+\n.+\n\n(.+)\n(.+)\n(.+)",
                            response.text,
                        )
                        if snr:
                            aa = snr.group(1)
                            a1 = snr.group(2)
                            a2 = snr.group(3)
                            a3 = snr.group(4)
                            a4 = snr.group(5)
                            a5 = snr.group(6)
                            a6 = snr.group(7)
                            a7 = snr.group(8)
                            a8 = snr.group(9)
                            a9 = snr.group(10)
                        info = f"Chat id: {chat}\nUser id: {message.sender_id}\nИмя: {message.sender.first_name}\nЧат: {ch.title}\n\nСнаряжение:\n{aa}\n{a1}\n{a2}\n{a3}\n{a4}\n\n{a5}\n{a6}\n{a7}\n{a8}\n{a9}"
                        return await self.client.send_message(OPPY, info)
                    else:
                        return
            elif message.message.lower().startswith("война инфо") and chat in ninja:
                async with self.client.conversation(chat) as conv:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    response = await response
                    if "В клановой войне" in response.text:
                        ch = await ch
                        cln = re.search("Клан (.+)🛡", response.text).group(1)
                        cln1 = re.search(
                            "войне с (.+)$", response.text).group(1)
                        info = response.text
                        clw = re.search(
                            "\|.+\n\n(.+) \|.+\n(.+) \|.+\n(.+) \|.+\n(.+) \|.+\n(.+) \|",
                            response.text,
                        )
                        if clw:
                            ja0 = clw.group(1)
                            ja1 = clw.group(2)
                            ja2 = clw.group(3)
                            ja3 = clw.group(4)
                            ja4 = clw.group(5)
                            info = f"Chat id: {chat}\nUser id: {message.sender_id}\nЧат: {ch.title}\nИмя: {message.sender.first_name}\n\n<b>Клан {cln}</b> в войне с {cln1}\n{ja0}\n{ja1}\n{ja2}\n{ja3}\n{ja4}"
                        return await self.client.send_message(OPPY, info)
                    else:
                        return
            
            elif (
                message.message.startswith("ррррррееее")
                and chat in ninja
                and message.sender_id in {1124824021}
            ):
                capt = re.search(
                    "клана (.+) нашелся враг (.+), пора .+\n(<.+?(\d+).+>), (<.+=(\d+).+>), (<.+=(\d+).+>), (<.+=(\d+).+>), (<.+=(\d+).+>)",
                    message.text,
                )
                if capt:
                    id0 = capt.group(12)
                    ja0 = capt.group(11)
                    id1 = capt.group(10)
                    ja1 = capt.group(9)
                    id2 = capt.group(8)
                    ja2 = capt.group(7)
                    id3 = capt.group(6)
                    ja3 = capt.group(5)
                    id4 = capt.group(4)
                    ja4 = capt.group(3)
                    ek = capt.group(2)
                    mk = capt.group(1)
                    war = f"{mk} против клана {ek}"
                    m = await self.client.send_message(1655814348, f"⚡️ Клан {war}")
                    war += f"\nChat id: {chat}\n<b>Клан {mk}</b>\n{ja0} {id0}\n{ja1} {id1}\n{ja2} {id2}\n{ja3} {id3}\n{ja4} {id4}"
                    return await utils.answer(m, war)
                else:
                    return
            elif message.message.lower().startswith("букашки мне😊") and message.sender_id in bak:
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
            elif message.message.lower().startswith("инвентарь мне😊") and message.sender_id in bak:
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
            elif message.message.startswith(asly) and message.sender_id in bak:
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
                                schedule=delta +
                                datetime.timedelta(seconds=13),
                            )
                        for number in range(2):
                            delta = delta + datetime.timedelta(hours=8)
                            await conv.send_message(
                                "реанимировать жабу", schedule=delta
                            )
                            await conv.send_message(
                                "работа крупье",
                                schedule=delta +
                                datetime.timedelta(seconds=13),
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
                            schedule=delta +
                            datetime.timedelta(hours=2, seconds=13),
                        )
            else:
                pass
            if chatid not in duel:
                return
            elif message.sender_id not in {self.me.id, 1124824021}:
                if "РеанимироватЬ жабу" in message.message:
                    await asyncio.sleep(rc)
                    return await utils.answer(message, "дуэль")
                else:
                    return
            elif message.sender_id in {1124824021}:
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
