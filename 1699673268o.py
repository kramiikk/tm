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
        if not hasattr(m, "text") or not isinstance(m, Message):
            return
        if "У кого есть Кэйя с6?" in m.text:
            await asyncio.sleep(random.randint(3, 33))
            await (await self.client.get_messages("d3668", ids=2)).react("❤️")
        if (
            m.chat_id not in ch
            or m.sender_id == self.me.id
            or m.date.minute in (0, 1, 29, 30, 31, 58, 59)
            or random.randint(0, 21) != 3
        ):
            return
        await asyncio.sleep(random.randint(3, 13) + m.date.second)
        if m.chat_id not in self.rs:
            self.rs.setdefault(m.chat_id, (m.date.hour + m.date.minute) - 15)
            self.db.set("Su", "rs", self.rs)
        if -1 < ((m.date.hour + m.date.minute) - self.rs[m.chat_id]) < 15:
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
