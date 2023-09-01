from .. import loader
import random

from telethon.tl.types import Message


@loader.tds
class ealler(loader.Module):
    """post"""

    strings = {"name": "ealler"}

    async def watcher(self, m):
        """on channel"""
        CHANNEL = -1001868163414
        if (
            isinstance(m, Message)
            and m.chat_id != CHANNEL
            and m.fwd_from is None
            and random.randint(0, 3) != 3
            and random.randint(1, 33) != 13
            and random.randint(13, 99) != 33
        ):
            text = f"{m.sender.first_name}:\n"
            text += "<i>Pursue your course, let other people talk!</i>"
            await m.client.send_message(CHANNEL, text)
