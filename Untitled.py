import asyncio
from .. import loader


@loader.tds
class ealler(loader.Module):
    """post"""

    strings = {"name": "ealler"}

    THR = 1

    async def watcher(self, m):
        """channel"""
        if not m or m.chat_id != 5274754956 or "int" not in m.text:
            return
        txt = "<i>Pursue your course, let other people talk!</i>"
        while True:
            await asyncio.sleep(1)
            await self.client.send_message(1868163414, f"{self.THR} | {txt}")
            self.THR += 1
