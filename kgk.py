from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class kgkMod(loader.Module):
    """Алина, я люблю тебя!"""

    strings = {"name": "kgk"}

    async def client_ready(self, client, db):
        """ready"""
        self.client = client
        self.db = db

    async def watcher(self, m):
        """алко"""
        if (
            not isinstance(m, Message)
            or m.sender_id != -1001920586126
        ):
            return
        await m.reply("!ban")
