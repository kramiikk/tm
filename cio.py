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

    async def tms(self, message: Message, i):
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
                        from_users=1124824021, chats=message.peer_id, pattern=p
                    )
                )
            except asyncio.exceptions.TimeoutError:
                RSP = await self.client.get_messages(message.chat_id, search=" ")
            return await conv.cancel_all()

    async def aww(self, message: Message):
        if message.from_id not in [1124824021]:
            return
        return await message.respond("Ого, вот это эпичная битва!")

    async def bww(self, message: Message):
        if len(message.message) not in [21, 30]:
            return
        p = None
        await self.err(message, p)
        if "Отлично!" not in RSP.text:
            return
        return await message.respond('Удачной охоты')

    async def cww(self, message: Message):
        if message.from_id not in [1124824021]:
            return
        return await message.respond('Алллоооо! Вас не слышшшшнноооо!')

    async def dww(self, message: Message):
        txt = "Крутой клан — крутой лид!"
        p = "Клан"
        await self.err(message, p)
        if p not in RSP.text:
            return
        if "Пойти" not in RSP.text:
            ms = await self.client.get_messages(message.chat_id, search="отправиться за картой", from_user=message.from_id)
            for i in ms:
                await self.tms(message, i)
                if MS > timedelta(days=-1) or MS > timedelta(days=0, hours=8):
                    txt = "Пришло время похода: Go! Go! Go!"
        return await i.reply(txt)

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
