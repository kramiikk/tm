import asyncio
from .. import loader


@loader.tds
class ealler(loader.Module):
    """post"""

    strings = {"name": "ealler"}

    THR = 1

    async def watcher(self, m):
        """channel"""
        if not (m or m.chat_id == 5274754956):
            return
        txt = "<i>Pursue your course, let other people talk!</i>"
        for _ in asyncio.while_true():
            await self.client.send_message(1868163414, gtext())

            def gtext():
                return f"{self.THR} | {txt}"

            self.THR += 1
            await asyncio.sleep(1)
