from .. import loader
from telethon.tl.types import Message


@loader.tds
class ealler(loader.Module):
    """post"""

    strings = {"name": "ealler"}

    async def watcher(self, m):
        """channel"""
        CHANNEL = -1001868163414
        if not isinstance(m, Message) or m.chat_id != CHANNEL:
            return
        txt = "{} | <i>Pursue your course, let other people talk!</i>"
        await self.client.send_message(CHANNEL, txt.format(m.id))
