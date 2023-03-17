import asyncio
import random

from telethon.tl.types import Message

from .. import loader


ch = [
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
    -1001543978633,
    -1001891107122,
    -1001219384558,
    -1001204963918,
    -1001659641946,
    -1001161353738,
    -1001810022268,
    -1001432347420,
    -1001659133131,
    -1001661278111,
    -1001808992481,
    -1001257002272,
    -1001528652715,
    -1001834328505,
]


@loader.tds
class krmkMod(loader.Module):
    """krmk"""

    strings = {"name": "krmk"}

    async def client_ready(self, client, db):
        """ready"""
        self.me = await client.get_me()
        self.client = client
        self.db = db

    async def watcher(self, m: Message):
        """алко"""
        if (
            not isinstance(m, Message)
            or m.chat_id not in ch
            or m.sender_id == self.me.id
            or m.date.minute in (0, 1, 29, 30, 31, 58, 59)
            or random.randint(0, 21) != 3
        ):
            return
        try:
            p = (await self.client.get_messages(806443327, search=" "))[0]
        except Exception:
            return
        if random.randint(0, 33) != 13:
            cc = [m.chat_id]
        else:
            cc = ch
        for i in cc:
            await asyncio.sleep(random.randint(1, 13))
            try:
                if p.media is not None:
                    await self.client.send_file(i, p, caption=p.text)
                else:
                    await self.client.send_message(i, p.text)
            except Exception:
                pass
