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
        return await self.client.send_message(1655814348, tog)

    async def bww(self, message: Message):
        if len(message.message) not in [21, 30]:
            return
        p = None
        await self.err(message, p)
        if "Отлично!" not in RSP.text:
            return
        return await self.client.send_message(1767017980, f"В поиске {lira}")

    async def cww(self, message: Message):
        if message.from_id not in [1124824021]:
            return
        return await self.client.send_message(1655814348, tog)

    async def dww(self, message: Message):
        p = "Клан"
        await self.err(message, p)
        if p not in RSP.text:
            return
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
        return await self.eee(message)
