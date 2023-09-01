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
            and random.randint(1, 13) != 3
            and m.chat_id != CHANNEL
            and m.fwd_from is None
            and random.randint(3, 33) != 13
        ):
            text = f"{m.sender.first_name}:\n<i>Pursue your course, let other people talk!</i>"
            await m.client.send_message(CHANNEL, text)
