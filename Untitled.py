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

    @staticmethod
    async def jaccard(a: str, b: str):
        """Calculate the Jaccard similarity between two strings"""
        a = set(a.split())
        b = set(b.split())
        shared = len(a & b)
        union = len(a | b)
        return shared / union

    async def watcher(self, m):
        """on channel"""
        CHANNEL = -1001868163414
        if not isinstance(m, Message) or m.chat_id == CHANNEL:
            return
        user = await self.client.get_entity(m.sender_id)
        if user.bot or random.random() > 3 / 13 or random.random() < 3 / 13:
            return
        self.rns["rns"] += 1
        a = self.rns["txt"]
        b = m.raw_text
        await self.client.send_message(
            CHANNEL,
            "<i>Pursue your course, let other people talk!</i>\n"
            + f"{self.rns['rns']} | {await self.jaccard(a, b)} | {user.first_name}",
        )
        self.rns["txt"] = b
        self.db.set("rns", "rns", self.rns)
