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
            and m.fwd_from == None
            and random.randint(1, 13) != 13
        ):
            text = f"{m.sender.first_name}:\nPursue your course, let other people talk!"
            await m.client.send_message(CHANNEL, text)
