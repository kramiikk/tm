from .. import loader


@loader.tds
class ealler(loader.Module):
    """post"""

    strings = {"name": "ealler"}

    async def client_ready(self, client, db):
        """ready"""
        self.db = db
        self.client = client
        self.thr = db.get("Thr", "thr", {})
        self.thr.setdefault("count", 1002)

    async def watcher(self, m):
        """channel"""
        if m and not m.photo:
            i = self.thr["count"] + 1
            self.thr["count"] = i
            txt = f"{i} | <i>Pursue your course, let other people talk!</i>"
            await self.client.send_message(1868163414, txt)
            self.db.set("Thr", "thr", self.thr)
