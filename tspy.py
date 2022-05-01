import asyncio
import re
from datetime import timedelta

from telethon import events
from telethon.tl.types import Message

from .. import loader


@loader.tds
class SpyMod(loader.Module):
    """Слежка за кланами в Жабаботе."""

    strings = {"name": "spy"}

    async def client_ready(self, client, db):
        self.db = db
        self.client = client

    @staticmethod
    async def tms(message: Message, i):
        global MS
        MS = timedelta(
            hours=message.date.hour,
            minutes=message.date.minute,
            seconds=message.date.second,
        ) - timedelta(hours=i.date.hour, minutes=i.date.minute, seconds=i.date.second)

    async def err(self, message: Message, p):
        async with self.client.conversation(message.chat_id, exclusive=False) as conv:
            try:
                global RSP
                RSP = await conv.wait_event(
                    events.NewMessage(
                        from_users=1124824021, chats=message.chat_id, pattern=p
                    )
                )
            except asyncio.exceptions.TimeoutError:
                RSP = await self.client.get_messages(message.chat_id, search=" ")
            return await conv.cancel_all()

    async def aww(self, message: Message):
        if message.from_id not in [1124824021]:
            return
        if "одержал" in message.text:
            klan = re.search(r"н (.+) о[\s\S]*: (.+)[\s\S]* (\d+):(\d+)", message.text)
            tog = f"🏆 {klan.group(1)}\n             {klan.group(3)}:{klan.group(4)}\n🔻 {klan.group(2)}"
        elif "проиграли" in message.text:
            klan = re.search(r", (.+),[\s\S]*: (.+)[\s\S]* (\d+):(\d+)", message.text)
            tog = f"🏆 {klan.group(2)}\n             {klan.group(3)}:{klan.group(4)}\n🔻 {klan.group(1)}"
        else:
            klan = re.search(r"н (.+),.+\n.+: (.+)", message.text)
            tog = f"{klan.group(1)} 🫂 {klan.group(2)}\n<i>                                    ничья</i>"
            return await self.client.send_message(1767017980, tog)
        await self.client.send_message(1767017980, tog)
        tog = f"Cid: {message.chat_id}\n\nКлан: {klan.group(1)}"
        for i in re.findall(r"•.+(<.+?(\d+).+>)", message.text):
            tog += f"\n{i[0]} {i[1]}"
        return await self.client.send_message(1655814348, tog)

    async def bww(self, message: Message):
        if len(message.message) not in [21, 30]:
            return
        p = None
        await self.err(message, p)
        if "Отлично!" not in RSP.text:
            return
        src = f"{message.chat_id} {message.from_id}"
        ms = await self.client.get_messages(1655814348, search=src)
        for i in (i for i in ms if "деревян" not in i.text.casefold()):
            if "Усилитель:" in i.text:
                klan = re.search(r"Лига: (.+)\nУсилитель: (.+)\n\nКлан: (.+)", i.text)
                lira = f"{klan.group(3)}\nЛига: {klan.group(1)}\nУсилитель: {klan.group(2)}"
            else:
                klan = re.search(r"Клан: (.+)", i.text).group(1)
                src = f"35 кланов {klan}"
                p = await self.client.get_messages(1782816965, search=src)
                if p.total == 0:
                    return
                for i in p:
                    lira = re.search(r"кланов (.+) лиге", i.message).group(1)
                    lira = f"{klan}\nЛига: {lira}"
            return await self.client.send_message(1767017980, f"В поиске {lira}")
        return

    async def cww(self, message: Message):
        if message.from_id not in [1124824021]:
            return
        klan = re.search(r"клана (.+) нашелся враг (.+), пора", message.text)
        src = f"35 кланов {klan.group(1)}"
        ms = await self.client.get_messages(1782816965, search=src)
        if ms.total == 0:
            src = f"35 кланов {klan.group(2)}"
            ms = await self.client.get_messages(1782816965, search=src)
        for i in ms:
            lig = re.search(r"Топ 35 кланов (.+) лиге", i.text).group(1)
        (if not lig) or ("деревян" in lig.casefold()) or ({klan.group(1)} not in i.text):
            return
        txt = f"⚡️{klan.group(1)} <b>VS</b> {klan.group(2)}\nЛига: {lig}"
        await self.client.send_message(1767017980, txt)
        tog = f"Cid: {message.chat_id}\nКлан: {klan.group(1)}\nЛига: {lig}"
        for i in re.findall(r"<.+?id=(\d+)\">", message.text):
            tog += f"\n{i}"
        return await self.client.send_message(1655814348, tog)

    async def dww(self, message: Message):
        p = "Клан"
        await self.err(message, p)
        if p not in RSP.text:
            return
        klan = re.search(r"н (.+):[\s\S]*а: (.+)[\s\S]*ь: (.+)", RSP.text)
        info = f"Cid: {message.chat_id}\nUid: {message.from_id}\nЛига: {klan.group(2)}\nУсилитель: {klan.group(3)}\n\nКлан: {klan.group(1)}"
        return await self.client.send_message(1655814348, info)

    async def eee(self, message: Message):
        fff = {
            "очень жаль": self.aww(message),
            "одержал победу!": self.aww(message),
            "эй, клан": self.aww(message),
            "начать клановую войну": self.bww(message),
            "@toadbot начать клановую войну": self.bww(message),
            "алло,": self.cww(message),
            "мой клан": self.dww(message),
            "@toadbot мой клан": self.dww(message),
        }
        for i in (i for i in fff if message.message.casefold().startswith(i)):
            return await fff[i]
        return

    async def watcher(self, message: Message):
        if not isinstance(message, Message):
            return
        return await self.eee(message)
