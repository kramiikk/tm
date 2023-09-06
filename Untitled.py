from .. import loader


@loader.tds
class ealler(loader.Module):
    """post"""

    strings = {"name": "ealler"}

    async def watcher(self):
        """channel"""
        i = (await self.client.get_messages(1868163414, limit=1))[0].id
        txt = f"{i} | <i>Pursue your course, let other people talk!</i>"
        await self.client.send_message(1868163414, txt)
