import datetime
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

    async def watcher(self, m):
        """channel"""
        if m and m.chat_id != -1001868163414 and not m.photo:
            ct = datetime.datetime.now()
            txt = " | <i>Pursue your course, let other people talk!</i>"
            if ct.second != self.thr["sec"]:
                self.thr["sec"] = ct.second
                self.thr["count"] += 1
                self.db.set("Thr", "thr", self.thr)
                await self.client.send_message(1868163414, f"{self.thr['count']}{txt}")
