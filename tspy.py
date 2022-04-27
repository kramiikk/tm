import asyncio
import re
from datetime import timedelta

from telethon import events

from .. import loader


@loader.tds
class SpyMod(loader.Module):
    """Слежка за кланами в Жабаботе."""

    strings = {"name": "spy"}

    async def client_ready(self, client, db):
        self.db = db
        self.client = client

    @staticmethod
    async def tms(m, i):
        global MS
        MS = timedelta(
            hours=m.date.hour, minutes=m.date.minute, seconds=m.date.second
        ) - timedelta(hours=i.date.hour, minutes=i.date.minute, seconds=i.date.second)

    async def err(self, m, p):
        async with self.client.conversation(m.chat_id, exclusive=False) as conv:
            try:
                global RSP
                RSP = await conv.wait_event(
                    events.NewMessage(from_users=1124824021, chats=m.chat_id, pattern=p)
                )
            except asyncio.exceptions.TimeoutError:
                RSP = await self.client.get_messages(m.chat_id, search=" ")
            await conv.cancel_all()

    async def rrr(self, m):
        async with self.client.conversation(m.chat_id, exclusive=False) as conv:
            try:
                global RSP
                RSP = await conv.get_response()
            except asyncio.exceptions.TimeoutError:
                RSP = await self.client.get_messages(m.chat_id, search=" ")
            await conv.cancel_all()

    async def aww(self, m):
        if m.from_id not in [1124824021]:
            return
        if "одержал" in m.text:
            klan = re.search(r"н (.+) о[\s\S]*: (.+)[\s\S]* (\d+):(\d+)", m.text)
            tog = f"🏆 {klan.group(1)}\n             {klan.group(3)}:{klan.group(4)}\n🔻 {klan.group(2)}"
        elif "проиграли" in m.text:
            klan = re.search(r", (.+),[\s\S]*: (.+)[\s\S]* (\d+):(\d+)", m.text)
            tog = f"🏆 {klan.group(2)}\n             {klan.group(3)}:{klan.group(4)}\n🔻 {klan.group(1)}"
        else:
            klan = re.search(r"н (.+),.+\n.+: (.+)", m.text)
            tog = f"{klan.group(1)} 🫂 {klan.group(2)}\n<i>                                    ничья</i>"
            return await self.client.send_message(1767017980, tog)
        await self.client.send_message(1767017980, tog)
        tog = f"Chat id: {m.chat_id}\n\nКлан: {klan.group(1)}"
        for i in re.findall(r"•.+(<.+?(\d+).+>)", m.text):
            tog += f"\n{i[0]} {i[1]}"
        return await self.client.send_message(1655814348, tog)

    async def bww(self, m):
        if len(m.message) not in [21, 30]:
            return
        p = None
        await self.err(m, p)
        if "Отлично!" not in RSP.text:
            return
        src = f"{m.chat_id} {m.from_id}"
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

    async def cww(self, m):
        if m.from_id not in [1124824021]:
            return
        klan = re.search(r"клана (.+) нашелся враг (.+), пора", m.text)
        src = f"35 кланов {klan.group(1)}"
        ms = await self.client.get_messages(1782816965, search=src)
        if ms.total == 0:
            src = f"35 кланов {klan.group(2)}"
            ms = await self.client.get_messages(1782816965, search=src)
        for i in ms:
            ms = re.search(r"Топ 35 кланов (.+) лиге", i.text).group(1)
        if "деревян" in ms.casefold():
            return
        txt = f"⚡️{klan.group(1)} <b>VS</b> {klan.group(2)}\nЛига: {ms}"
        await self.client.send_message(1767017980, txt)
        capt = re.findall(r"<.+?id=(\d+)\">", m.text)
        tog = f"Chat id: {m.chat_id}\nКлан: {klan.group(1)}\nЛига: {ms}"
        for i in capt:
            tog += f"\n{i}"
        return await self.client.send_message(1655814348, tog)

    async def dww(self, m):
        await self.rrr(m)
        if "Опыт" not in RSP.text:
            return
        klan = re.search(r"н (.+):[\s\S]*а: (.+)[\s\S]*ь: (.+)", RSP.text)
        info = f"Cid: {m.chat_id}\nUid: {m.from_id}\nЛига: {klan.group(2)}\nУсилитель: {klan.group(3)}\n\nКлан: {klan.group(1)}"
        return await self.client.send_message(1655814348, info)

    async def eee(self, m):
        fff = {
            "очень": self.aww(m),
            "клан": self.aww(m),
            "эй, клан": self.aww(m),
            "начать клановую войну": self.bww(m),
            "@toadbot начать клановую войну": self.bww(m),
            "алло": self.cww(m),
            "мой клан": self.dww(m),
            "@toadbot мой клан": self.dww(m),
        }
        for i in (i for i in fff if m.message.casefold().startswith(i)):
            return await fff[i]
        return

    async def watcher(self, m):
        return await self.eee(m)
