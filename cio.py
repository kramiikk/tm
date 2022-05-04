import asyncio
from datetime import timedelta

from telethon import events
from telethon.tl.types import Message

from .. import loader


@loader.tds
class SpyMod(loader.Module):
    """Слежка за кланами в Жабаботе.v1.2.26"""

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

    async def bww(self, message: Message):
        if len(message.message) not in [21, 30]:
            return
        p = None
        await self.err(message, p)
        if "Отлично!" not in RSP.text:
            return
        return await message.reply("Удачи!")

    async def dww(self, message: Message):
        p = "Клан"
        await self.err(message, p)
        if p not in RSP.text:
            return
        if "Пойти" in RSP.text:
            return
        txt = "Пришло время похода: Go! Go! Go!"
        ms = await self.client.get_messages(
            message.chat_id, search="отправиться за картой", from_user=message.from_id
        )
        if not ms:
            return await message.reply(txt)
        for i in ms:
            await self.tms(message, i)
        if MS < timedelta(days=0) or MS > timedelta(days=0, hours=8):
            return await i.reply(txt)
        return await message.reply(txt)

    async def eee(self, message: Message):
        fff = {
            "начать клановую войну": self.bww(message),
            "@toadbot начать клановую войну": self.bww(message),
            "мой клан": self.dww(message),
            "@toadbot мой клан": self.dww(message),
        }
        for i in (i for i in fff if message.message.casefold().startswith(i)):
            return await fff[i]
        return

    async def watcher(self, message: Message):
        if not isinstance(message, Message):
            return
        if message.chat_id == -1001767017980:
            await self.client.send_message('me', f"{message}")
            if not message.replies.comments:
                return
            await self.client.send_message(
                message.chat_id,
                file="CAADAgADfxEAAj_OkEvc1gSOXPLoTQI",
                comment_to=message.id,
            )
        return await self.eee(message)
