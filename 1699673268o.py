import asyncio
import random

from telethon.tl.types import Message

from .. import loader


ch = [-1001646057581]


@loader.tds
class krmk0Mod(loader.Module):
    """krmk0"""

    strings = {"name": "krmk0"}

    async def client_ready(self, client, db):
        """ready"""
        self.db = db
        self.client = client
        self.me = await client.get_me()
        self.rs = db.get("Su", "rs", {})

    async def watcher(self, m: Message):
        """алко"""
        if (
            not isinstance(m, Message)
            or m.chat_id not in ch
            or m.sender_id == self.me.id
            or random.randint(0, 21) != 3
        ):
            return
        await asyncio.sleep(random.randint(3, 13) + m.date.second)
        if m.chat_id not in self.rs:
            self.rs.setdefault(m.chat_id, (m.date.hour + m.date.minute) - 5)
            self.db.set("Su", "rs", self.rs)
        if -1 < ((m.date.hour + m.date.minute) - self.rs[m.chat_id]) < 5:
            return
        self.rs[m.chat_id] = m.date.hour + m.date.minute
        self.db.set("Su", "rs", self.rs)
        try:
            p = (await self.client.get_messages(862023922, search=" "))[0]
        except Exception:
            return
        for i in ch:
            await asyncio.sleep(random.randint(1, 13))
            try:
                if p.media is not None:
                    await self.client.send_file(i, p, caption=p.text)
                else:
                    await self.client.send_message(i, p.text)
            except Exception:
                pass
