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
    -1001581856473,
    -1001625102308,
    -1001171509294,
    -1001240066819,
    -1001659411526,
    -1001627055269,
    -1001604959220,
    -1001786741053,
    -1001167492843,
    -1001750154484,
    -1001686161112,
    -1001668102726,
    -1001757867679,
    -1001735885056,
    -1001752185113,
    -1001823298189,
    -1001743103882,
    -1001898285980,
    -1001569773126,
    -1001319382976,
    -1001649685073,
    -1001537481714,
    -1001491763275,
    -1001212855140,
    -1001766947890,
    -1001142951367,
    -1001577645504,
    -1001796387966,
    -1001586161399,
    -1001786245123,
    -1001543978699,
    -1001891107122,
]


@loader.tds
class krmkMod(loader.Module):
    """krmk"""

    strings = {"name": "krmk"}

    async def client_ready(self, client, db):
        """ready"""
        self.client = client
        self.db = db

    async def watcher(self, m: Message):
        """алко"""
        if (
            not isinstance(m, Message)
            or m.chat_id not in chat
            or random.randint(1, 13) != 3
        ):
            return
        try:
            p = (await self.client.get_messages(1695880084, search=" "))[0]
            if p.media is not None:
                await m.respond(message=p.text, file=p)
            else:
                await m.respond(p)
        except Exception:
            return
