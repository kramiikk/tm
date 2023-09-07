import time
from .. import loader


@loader.tds
class ealler(loader.Module):
    """post"""

    strings = {"name": "ealler"}

    async def client_ready(self, client, db):
        """ready"""
        self.db = db
        self.client = client
        self.thr = {"count": 0, "sec": 1}

    @loader.ratelimit(1)
    async def watcher(self, m):
        """channel"""
        if m and m.chat_id != -1001868163414 and not m.photo:
            txt = "<i>Pursue your course, let other people talk!</i>"
            sec = int(time.time()) % 60
            if sec != self.thr["sec"]:
                self.thr["sec"] = sec
                self.thr["count"] += 1
                self.db.set("Thr", "thr", self.thr)
                await self.client.send_message(
                    1868163414, f"{self.thr['count']} | {txt}"
                )
