import random

from telethon.tl.types import Message

from .. import loader


chat = [
    -1001614902805,
    -1001534956287,
    -1001845303401,
    -1001701044657,
    -1001654950014,
    -1001226236676,
    -1001349335204,
    -1001298501933,
    -1001666744611,
    -1001320693801,
    -1001547929649,
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
            or m.chat_id not in chat
            or random.randint(3, 33) != 33
        ):
            return
        p = await self.client.get_messages(1695880084, search="Обмен")
        try:
            await self.client.send_message(m.chat_id, p[0])
        except Exception:
            return
