import asyncio
import random

from telethon.tl.types import Message

from .. import loader


ch = [
    -1001645335158,
    -1001646057581,
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
            or random.randint(0, 72) != 3
        ):
            return
        try:
            p = (await self.client.get_messages(741683201, search=" "))[0]
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
