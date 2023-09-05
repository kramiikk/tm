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
    async def jaccard(x: str, y: str):
        """AAAAAAAAAAA"""
        x = set(x.split())
        y = set(y.split())
        shared = x.intersection(y)
        union = x.union(y)
        return len(shared) / len(union)

    async def watcher(self, m):
        """on channel"""
        CHANNEL = -1001868163414
        if (
            not isinstance(m, Message)
            or m.chat_id == CHANNEL
            or random.random() < 3 / 13
        ):
            return
        user = await self.client.get_entity(m.sender_id)
        if user.bot:
            return
        self.rns["rns"] += 1
        a = self.rns["txt"]
        b = m.text
        await self.client.send_message(
            CHANNEL,
            "<i>Pursue your course, let other people talk!</i>\n"
            + f"{self.rns['rns']} {str(self.jaccard(a, b))} | {user.first_name}",
        )
        a = b
        self.db.set("rns", "rns", self.rns)
