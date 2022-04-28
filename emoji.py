from datetime import timedelta

from telethon.tl.types import Message

from .. import loader


@loader.tds
class KkkMod(loader.Module):
    """Я люблю тебя!"""

    strings = {"name": "Kkk"}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    async def edj(self, message: Message):
        if message.chat_id != 707693258:
            return
        msg = [int(x) for x in message.text.split() if x.isnumeric()]
        delta = timedelta(hours=msg[1], minutes=msg[2], seconds=33)
        for i in range(3):
            delta += timedelta(minutes=msg[2])
            await self.client.send_message(707693258, "<b>Фарма</b>", schedule=delta)
        return

    async def fdj(self, message: Message):
        return await message.react("❤️")

    async def ebj(self, message: Message):
        fff = {
            "❌ незачет": self.edj(message),
            "куат": self.fdj(message),
        }
        for i in (i for i in fff if (i in message.text.casefold())):
            return await fff[i]
        return

    async def watcher(self, message: Message):
        return await self.ebj(message)
