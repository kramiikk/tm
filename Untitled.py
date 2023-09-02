from .. import loader, utils
import random

from telethon.tl.types import Message


@loader.tds
class ealler(loader.Module):
    """post"""

    strings = {"name": "ealler"}

    async def client_ready(self, client, db):
        self.db = db

    async def watcher(self, m):
        """on channel"""
        CHANNEL = -1001868163414
        user = await utils.get_user(m)
        if (
            isinstance(m, Message)
            and m.chat_id != CHANNEL
            and random.randint(3, 33) == 13
            and not user.bot
        ):
            rns = self.db.get("rns", "rns", {})
            rns.setdefault("rns", 0)
            count = rns["rns"] + 1
            text = f"{count} | {user.first_name}:\n"
            text += "<i>Pursue your course, let other people talk!</i>"
            await m.client.send_message(CHANNEL, text)
            self.db.set("rns", "rns", rns)
