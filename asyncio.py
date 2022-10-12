from .. import loader, utils
from telethon.tl.types import Message


@loader.tds
class IsMod(loader.Module):
    """go"""

    strings = {
        "name": "Is"
    }

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    async def watcher(self, m: Message):
        if not isinstance(m, Message) or m.from_id != -1001605756650:
            return
        await m.reply("pon")