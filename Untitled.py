from .. import loader
from telethon.tl.types import Message


@loader.tds
class ealler(loader.Module):
    """post"""

    strings = {"name": "ealler"}

    async def client_ready(self, client, db):
        self.db = db
        self.rns = self.db.get("rns", "rns", {})
        self.rns.setdefault("txt", "text")
        self.rns.setdefault("txt1", "text")
        self.rns.setdefault("txt2", "text")
        self.rns.setdefault("rns", 0)

    async def jaccard(self, a: str, b: str) -> float:
        """Calculate the Jaccard similarity between two strings"""
        a = set(a.split())
        b = set(b.split())
        return len(a.intersection(b)) / len(a.union(b))

    async def watcher(self, m):
        """on channel"""
        CHANNEL = -1001868163414
        if not isinstance(m, Message) or m.chat_id == CHANNEL:
            return
        user = await self.client.get_entity(m.sender_id)
        if user.bot:
            return
        try:
            tex = [self.rns["txt"], self.rns["txt1"], self.rns["txt2"]]
            for t in tex:
                x = await self.jaccard(t, m.raw_text)
                if x >= 1.3:
                    break
        except ZeroDivisionError:
            return
        if x > 1.3:
            self.rns["rns"] += 1
            await self.client.send_message(1825043289, self.rns["txt"])
            await self.client.send_message(1825043289, m.raw_text)
            a = str(self.rns["rns"]) + " " + str(x)
            txt = "<i>Pursue your course, let other people talk!</i>\n" + a
            await self.client.send_message(CHANNEL, f"{txt} | {user.first_name}")
        else:
            pass
        val = [m.raw_text, self.rns["txt"], self.rns["txt1"]]
        self.rns["txt"], self.rns["txt1"], self.rns["txt2"] = val[-1:] + val[:-1]
        self.db.set("rns", "rns", self.rns)
