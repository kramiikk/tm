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
        self.thr.setdefault("count", 0)

    async def watcher(self, m):
        """channel"""
        if m and m.chat_id != -1001868163414 and not m.photo:
            txt = f" | <i>Pursue your course, let other people talk!</i>"
            await self.client.send_message(1868163414, str(self.thr["count"]) + txt)
            self.thr["count"] += 1
            self.db.set("Thr", "thr", self.thr)
