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
    -1001256967385,
    -1001826675898,
    -1001647517456,
    -1001446910788,
    -1001666744611,
    -1001581856473,
    -1001647517456,
    -1001625102308,
    -1001171509294,
    -1001240066819,
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
            or random.randint(1, 33) not in (3, 13)
        ):
            return
        p = await self.client.get_messages(736039911, search=" ")
        try:
            await self.client.send_message(m.chat_id, p[0])
        except Exception:
            return
