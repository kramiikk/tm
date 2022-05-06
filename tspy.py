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
        if "одержал" in message.text:
            klan = re.search(r"н (.+) о[\s\S]*: (.+)[\s\S]* (\d+):(\d+)", message.text)
            tog = f"🏆 {klan.group(1)}\n             {klan.group(3)}:{klan.group(4)}\n🔻 {klan.group(2)}"
        elif "проиграли" in message.text:
            klan = re.search(r", (.+),[\s\S]*: (.+)[\s\S]* (\d+):(\d+)", message.text)
            tog = f"🏆 {klan.group(2)}\n             {klan.group(3)}:{klan.group(4)}\n🔻 {klan.group(1)}"
        else:
            klan = re.search(r"н (.+),.+\n.+: (.+)", message.text)
            tog = f"{klan.group(1)} 🫂 {klan.group(2)}"
            return await self.client.send_message(1767017980, tog)
        await self.client.send_message(1767017980, tog)
        p = await self.client.get_messages(
            1782816965, search=f"35 кланов {klan.group(1)}"
        )
        if p.total == 0:
            p = await self.client.get_messages(
                1782816965, search=f"35 кланов {klan.group(2)}"
            )
        for i in p:
            tog = f"Cid: {message.chat_id}\n\nКлан: {klan.group(1)}\nЛига: {re.search(r'кланов (.+) лиге', i.text).group(1)}"
        for i in re.findall(r"•.+(<.+?(\d+).+>)", message.text):
            tog += f"\n{i[0]} {i[1]}"
        return await self.client.send_message(1655814348, tog)

    async def bww(self, message: Message):
        p = None
        await self.err(message, p)
        if "Отлично!" not in RSP.text:
            return
        ms = await self.client.get_messages(
            1655814348, search=f"{message.chat_id} {message.from_id} Лига"
        )
        for i in (
            i for i in ms if "деревян" not in i.text.casefold() and "Лига" in i.text
        ):
            klan = re.search(r"Клан: (.+)", i.text).group(1)
            liga = re.search(r"Лига: (.+)", i.text).group(1)
        p = await self.client.get_messages(1782816965, search=f"35 кланов {klan}")
        if p.total == 0:
            txt = f"{klan}\nЛига: {liga}"
        else:
            for i in p:
                txt = f"{klan}\nЛига: {re.search(r'кланов (.+) лиге', i.text).group(1)}"
            if klan not in i.text:
                txt = f"{klan}\nЛига: {liga}"
        return await self.client.send_message(1767017980, f"В поиске {txt}")

    async def cww(self, message: Message):
        klan = re.search(r"клана (.+) нашелся враг (.+), пора", message.text)
        src = f"35 кланов {klan.group(1)}"
        ms = await self.client.get_messages(1782816965, search=src)
        if ms.total == 0:
            src = f"35 кланов {klan.group(2)}"
            ms = await self.client.get_messages(1782816965, search=src)
        for i in ms:
            lig = re.search(r"Топ 35 кланов (.+) лиге", i.text).group(1)
        if "деревян" in i.text.casefold() or klan.group(1) not in i.text:
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

    async def watcher(self, message: Message):
        if not isinstance(message, Message):
            return
        if (
            message.text.startswith(("Очень жаль", "Клан ", "Эй, клан"))
            and message.from_id in [1124824021]
            and "Усилитель" not in message.text
            and "путешествие" not in message.text
        ):
            await self.aww(message)
        elif message.message.casefold().startswith(
            ("начать клановую войну", "@toadbot начать клановую войну")
        ) and len(message.message) in [21, 30]:
            await self.bww(message)
        elif message.message.startswith("Алло,") and message.from_id in [1124824021]:
            await self.cww(message)
        elif message.message.casefold().startswith(("мой клан", "@toadbot мой клан")):
            await self.dww(message)
        else:
            return
        return
