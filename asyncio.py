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

    async def watcher(self, event):
        if not isinstance(event, Message) or utils.get_chat_id(event) != 1605756650:
            return
        await self.client.send_message(1605756650, "pon")