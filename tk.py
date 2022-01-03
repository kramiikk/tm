import logging
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
            chat = message.chat_id
            ninja = {
                -1001484924016,
                -1001465870466,
                -1001403626354,
            }
            OPPY = -1001655814348
            if chat in ninja:
                if message.message.startswith("Алло") and message.sender_id in {
                    1124824021
                }:
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
                                    "Топ 35 кланов (.+) лиге", i.message
                                ).group(1)
                        txt += f"\nЛига: {liga}"
                        await utils.answer(nm, txt)
                    apt = re.search(
                        "клана (.+) нашелся враг (.+), пора .+\n(<.+?(\d+).+>), (<.+=(\d+).+>), (<.+=(\d+).+>), (<.+=(\d+).+>), (<.+=(\d+).+>)",
                        message.text,
                    )
                    if apt:
                        id0 = apt.group(12)
                        ja0 = apt.group(11)
                        id1 = apt.group(10)
                        ja1 = apt.group(9)
                        id2 = apt.group(8)
                        ja2 = apt.group(7)
                        id3 = apt.group(6)
                        ja3 = apt.group(5)
                        id4 = apt.group(4)
                        ja4 = apt.group(3)
                        ek = apt.group(2)
                        mk = apt.group(1)
                        war = f"{mk} против клана {ek}"
                        m = await self.client.send_message(1655814348, f"⚡️ Клан {war}")
                        war += f"\nChat id: {chat}\n<b>Клан: {mk}</b>\n{ja0} {id0}\n{ja1} {id1}\n{ja2} {id2}\n{ja3} {id3}\n{ja4} {id4}"
                        return await utils.answer(m, war)
                elif message.message.lower().startswith(
                    ("начать клановую", "@tgtoadbot начать клановую")
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
                                    usil = re.search(
                                        "Усилитель: (.+)", i.message
                                    ).group(1)
                                    lif = f"\nЛига: {liga}\nУсилитель: {usil}"
                                else:
                                    src = f"Топ 35 кланов {klan}"
                                    ms = await self.client.get_messages(
                                        1782816965, search=src
                                    )
                                    for i in ms:
                                        liga = re.search(
                                            "Топ 35 кланов (.+) лиге", i.message
                                        ).group(1)
                                        lif = f"\nЛига: {liga}"
                            txt = f"В поиске {klan}{lif}"
                            nm = await self.client.send_message(1767017980, txt)
                elif message.message.lower().startswith(
                    ("мой клан", "@tgtoadbot мой клан")
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
                            usil = re.search("Усилитель: (.+)", response.text).group(1)
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
                elif message.message.lower().startswith(
                    ("моя жаба", "@tgtoadbot моя жаба")
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
                            imy = re.search("Имя жабы: (.+)", response.text).group(1)
                            urv = re.search("вашей жабы: (.+)", response.text).group(1)
                            cll = re.search("Класс: (.+)", response.text).group(1)
                            info = f"Chat id: {chat}\nUser id: {message.sender_id}\nЖаба: {imy}\nУровень: {urv}\nКласс: {cll}\n{message.sender.first_name}"
                            return await self.client.send_message(OPPY, info)
                elif message.message.lower().startswith(
                    ("мое снаряжение", "@tgtoadbot мое снаряжение")
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
            elif message.message.lower().startswith(
                ("дуэль старт", "@tgtoadbot дуэль старт")
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
                    response1 = await response
                    if "У вас ничья" in response1.text:
                        await self.client.send_message(
                            OPPY,
                            f"{response1.text}",
                        )
                    elif "Победитель" in response1.text:
                        await self.client.send_message(
                            OPPY,
                            f"{response1.text}",
                        )
            if "1 атака" in message.message and message.sender_id in {1124824021}:
                await self.client.send_message(OPPY, message.text)
        except:
            return
