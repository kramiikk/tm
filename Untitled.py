from .. import loader


@loader.tds
class ealler(loader.Module):
    """post"""

    strings = {"name": "ealler"}

    async def watcher(self, m):
        """on channel"""
        CHANNEL = -1001868163414
        if m.chat_id != CHANNEL:
            text = f"{m.sender.first_name}: Pursue your course, let other people talk!"
            await m.client.send_message(CHANNEL, text)
