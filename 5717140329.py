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
        if not hasattr(m, "text") or not isinstance(m, Message):
            return
        if "У кого Кэйя с6" in m.text:
            await asyncio.sleep(random.randint(3, 33))
            await (await self.client.get_messages("tginfochat", ids=1419481)).react("❤️")
        if (
            m.chat_id not in ch
            or m.sender_id == self.me.id
            or m.date.minute in (0, 1, 29, 30, 31, 58, 59)
            or random.randint(0, 21) != 3
        ):
            return
        cs = 869534519
        if random.randint(0, 3) == 1:
            cs = 741683201
        try:
            p = (await self.client.get_messages(cs, search=" "))[0]
        except Exception:
            return
        if random.randint(0, 13) != 3:
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
