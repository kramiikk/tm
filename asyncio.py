import asyncio
import random
from .. import loader, utils
from telethon.tl.types import Message


@loader.tds
class IsMod(loader.Module):
    """go"""

    strings = {"name": "Is"}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    async def watcher(self, m: Message):
        if not isinstance(m, Message) or m.from_id != -1001398750595:
            return
        await asyncio.sleep(random.randint(1, 33))
        await m.reply(
            random.choice(
                (
                    "пон",
                    "непон",
                    "кто Кэйя мейнер?",
                    "секси",
                    "кто в данж?",
                    "го раскрывать новые пространства!",
                    "го в среншин?",
                )
            )
        )
