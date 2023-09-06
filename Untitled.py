from .. import loader
from telethon.tl.types import Message


@loader.tds
class ealler(loader.Module):
    """post"""

    strings = {"name": "ealler"}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.rns = self.db.get("Rns", "rns", {})
        self.thr = self.db.get("Thr", "thr", {})
        self.thr.setdefault("tmm", 0)
        self.rns = ["text"] * 13

    async def jaccard(self, a: str, b: str) -> float:
        """Calculate the Jaccard similarity between two strings"""
        a = set(a.split())
        b = set(b.split())
        if not (a or b):
            return 0.0
        return len(a & b) / len(a | b)

    async def watcher(self, m):
        """on channel"""
        CHANNEL = -1001868163414
        if not isinstance(m, Message) or m.chat_id == CHANNEL:
            return
        user = await self.client.get_entity(m.sender_id)
        if user.bot:
            return
        pairs = [(t, await self.jaccard(t, m.raw_text)) for t in self.rns]
        max_pair = max(pairs, key=lambda p: p[1])
        t = max_pair[0]
        x = max_pair[1]
        if x > 1.0:
            self.thr["tmm"] += 1
            self.db.set("Thr", "thr", self.thr)
            await self.client.send_message(1825043289, t)
            await self.client.send_message(1825043289, m.raw_text)
            a = str(self.thr["tmm"]) + " " + str(x)
            txt = "<i>Pursue your course, let other people talk!</i>\n" + a
            await self.client.send_message(CHANNEL, f"{txt} | {user.first_name}")
        else:
            pass
        self.rns = self.rns[1:] + [m.text]
        self.db.set("Rns", "rns", self.rns)
