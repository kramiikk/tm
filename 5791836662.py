import asyncio
import random

from telethon.tl.types import Message

from .. import loader


ch = [
    -1001536915379,
    -1001583439030,
    -1001640898837,
    -1001699627148,
    -1001779263910,
    -1001210331108,
    -1001464083684,
    -1001276005577,
    -1001612518469,
]


@loader.tds
class krmkMod(loader.Module):
    """krmk"""

    strings = {"name": "krmk"}

    async def client_ready(self, client, db):
        """ready"""
        self.me = await client.get_me()
        self.client = client
        self.db = db

    async def watcher(self, m: Message):
        """алко"""
        if (
            not isinstance(m, Message)
            or m.chat_id not in ch
            or m.sender_id == self.me.id
            or m.date.minute in (0, 1, 29, 30, 31, 58, 59)
            or random.randint(0, 13) != 3
        ):
            return
        try:
            p = (await self.client.get_messages(868659378, search=" "))[0]
        except Exception:
            return
        if random.randint(0, 33) != 13:
            cc = [m.chat_id]
        else:
            cc = ch
        for i in cc:
            await asyncio.sleep(random.randint(1, 13))
            try:
                if p.media is not None:
                    await self.client.send_file(i, p, caption=p.text)
                else:
                    await self.client.send_message(i, p.text)
            except Exception:
                pass
