import random
import re

from telethon.tl.types import Message

from .. import loader


chat = [1771062233, 1436786642]


@loader.tds
class ktkMod(loader.Module):
    """Алина, я люблю тебя!"""

    strings = {"name": "ktk"}

    async def client_ready(self, client, db):
        """ready"""
        self.client = client
        self.db = db

    async def watcher(self, m):
        """алко"""
        if (
            m.date.hour != random.randint(0, 23)
            and m.date.minute != random.randint(0, 59)
        ):
            return
        p = await self.client.get_messages(898299955, search="Обмен")
        for i in chat:
            await self.client.send_message(i, p)
