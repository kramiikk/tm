import time
from .. import loader


@loader.tds
class ealler(loader.Module):
    """post"""

    strings = {"name": "ealler"}

    THR = {"count": 0, "sec": 1}

    async def cher(self, m):
        """channel"""
        while True:
            txt = "<i>Pursue your course, let other people talk!</i>"
            if time.time() % 60 != self.THR["sec"]:
                self.THR["sec"] = time.time() % 60
                self.THR["count"] += 1
                await self.client.send_message(
                    1868163414, f"{self.THR['count']} | {txt}"
                )
