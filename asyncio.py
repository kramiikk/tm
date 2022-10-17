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
        if not isinstance(m, Message) or m.from_id != -1001398750595 or m.text == "":
            return
        await m.reply(
            random.choice(
                (
                    "у кого есть Кэйя с6?",
                    "кто со мной собирать геокулусы? У меня не хватает для крафта ресурсов!\n\nUID: <code>746264860</code>",
                )
            )
        )
