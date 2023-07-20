import asyncio
import random

from telethon.tl.types import Message

from .. import loader


ch = [
    -1001320693801,
    -1001654950014,
    -1001614902805,
    -1001643770499,
    -1001240066819,
    -1001659411526,
    -1001932898997,
    -1001834328505,
]


@loader.tds
class krmkMod(loader.Module):
    """krmk"""

    strings = {"name": "krmk"}

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
        await asyncio.sleep(random.randint(3, 13) + m.date.second)
        if m.chat_id not in self.rs:
            self.rs.setdefault(m.chat_id, (m.date.hour + m.date.minute) - 5)
            self.db.set("Su", "rs", self.rs)
        if -1 < ((m.date.hour + m.date.minute) - self.rs[m.chat_id]) < 5:
            return
        self.rs[m.chat_id] = m.date.hour + m.date.minute
        self.db.set("Su", "rs", self.rs)
        try:
            p = await self.client.get_messages(1613921168, limit=None)
        except Exception:
            return
        if p.total < 2:
            return
        p = p[random.randint(0, p.total - 2)]
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
