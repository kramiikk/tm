import random

from .. import loader
from telethon.tl.types import Message


@loader.tds
class ealler(loader.Module):
    """post"""

    strings = {"name": "ealler"}

    async def client_ready(self, client, db):
        self.db = db
        self.rns = self.db.get("rns", "rns", {})
        self.rns.setdefault("txt", "text")
        self.rns.setdefault("rns", 0)

    async def jaccard(self, a: str, b: str) -> float:
        """Calculate the Jaccard similarity between two strings"""
        a = set(a.split())
        b = set(b.split())
        return len(a.intersection(b)) / len(a.union(b))

    async def watcher(self, m):
        """on channel"""
        CHANNEL = -1001868163414
        if not isinstance(m, Message) or m.chat_id == CHANNEL:
            return
        user = await self.client.get_entity(m.sender_id)
        if user.bot:
            return
        self.rns["rns"] += 1
        try:
            x = await self.jaccard(self.rns["txt"], m.raw_text)
        except ZeroDivisionError:
            return
        if x > 0.08:
            await self.client.send_message(1825043289, self.rns["txt"])
            await self.client.send_message(1825043289, m.raw_text)
        else:
            return
        a = str(self.rns["rns"]) + " " + str(x)
        txt = "<i>Pursue your course, let other people talk!</i>\n" + a
        await self.client.send_message(CHANNEL, f"{txt} | {user.first_name}")
        self.rns["txt"] = m.raw_text
        self.db.set("rns", "rns", self.rns)
