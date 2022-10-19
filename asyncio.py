from .. import loader
from telethon.tl.types import Message


@loader.tds
class IsMod(loader.Module):
    """go"""

    strings = {"name": "Is"}

    async def watcher(self, m: Message):
        if not isinstance(m, Message) or m.from_id != -1001398750595 or m.text == "":
            return
        await m.reply("Пофиг")
