import random

from .. import loader
from telethon.tl.types import Message


@loader.tds
class ealler(loader.Module):
    """post"""

    strings = {"name": "ealler"}

    async def client_ready(self, client, db):
        self.db = db
        self.rns = self.db.get("rns", "rns", 0)

    async def watcher(self, m):
        """on channel"""
        CHANNEL = -1001868163414
        if (
            not isinstance(m, Message)
            or m.chat_id == CHANNEL
            or random.random() > 3 / 13
        ):
            return
        user = await self.client.get_entity(m.sender_id)
        if user.bot:
            return
        self.rns["rns"] += 1
        self.db.set("rns", "rns", self.rns)
        await self.client.send_message(
            CHANNEL,
            "<i>Pursue your course, let other people talk!</i>\n"
            + f"{self.rns['rns']} | {user.first_name}",
        )
