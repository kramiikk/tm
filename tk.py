import logging
import random
import re

from telethon import events, functions, types

from .. import loader, utils

logger = logging.getLogger(__name__)


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
                            ja1 = clj.group(2)
                            ja2 = clj.group(3)
                            ja3 = clj.group(4)
                            ja4 = clj.group(5)
                            info = f"Chat id: {chat}\nUser id: {message.sender_id}\nИмя: {message.sender.first_name}\nЛига: {liga}\nУсилитель: {usil}\n\nКлан: {klan}\n(лид): {lid}\n{ja1}\n{ja2}\n{ja3}:\n{ja4}"
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
                        imy = re.search("Имя жабы: (.+)",
                                        response.text).group(1)
                        urv = re.search("вашей жабы: (.+)",
                                        response.text).group(1)
                        cll = re.search("Класс: (.+)", response.text).group(1)
                        info = f"Chat id: {chat}\nUser id: {message.sender_id}\nЖаба: {imy}\nУровень: {urv}\nКласс: {cll}\n{message.sender.first_name}"
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
                        info = f"Chat id: {chat}\nUser id: {message.sender_id}\nИмя: {message.sender.first_name}\\n\nСнаряжение:\n{aa}\n{a1}\n{a2}\n{a3}\n{a4}\n\n{a5}\n{a6}\n{a7}\n{a8}\n{a9}"
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
                            info = f"Chat id: {chat}\nUser id: {message.sender_id}\nИмя: {message.sender.first_name}\n\n<b>Клан {cln}</b> в войне с {cln1}\n{ja0}\n{ja1}\n{ja2}\n{ja3}\n{ja4}"
                        return await self.client.send_message(OPPY, info)
                    else:
                        return
        except:
            return
