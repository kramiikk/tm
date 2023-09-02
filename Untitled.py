from .. import loader, utils
import random

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
            or random.random() > 1 / 13
        ):
            return
        user = await utils.get_user(m)
        if user.bot or random.random() < 1 / 3:
            return
        self.rns["rns"] += 1
        self.db.set("rns", "rns", self.rns)
        text = "<i>Pursue your course, let other people talk!</i>\n"
        text += str(self.rns["rns"]) + " | " + user.first_name
        await m.client.send_message(CHANNEL, text)
