from .. import loader
from telethon.tl.types import Message


@loader.tds
class ealler(loader.Module):
    """post"""

    strings = {"name": "ealler"}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.rns = self.db.get("rns", "rns", {})
        self.rns.setdefault("rns", 0)
        keys = [f"txt{i}" for i in range(13)]
        self.rns = dict.fromkeys(keys)

    async def jaccard(self, a: str, b: str) -> float:
        """Calculate the Jaccard similarity between two strings"""
        a = set(a.split())
        b = set(b.split())
        if not (a or b):
            return 0.0
        return len(a.intersection(b)) / len(a.union(b))

    async def watcher(self, m):
        """on channel"""
        CHANNEL = -1001868163414
        if not isinstance(m, Message) or m.chat_id == CHANNEL:
            return
        user = await self.client.get_entity(m.sender_id)
        if user.bot:
            return
        tex = [self.rns[f"txt{i}"] for i in range(13)]
        for x in (await self.jaccard(x, m.raw_text) for x in tex):
            if x > 1.0:
                break
        if x > 1.0:
            self.rns["rns"] += 1
            await self.client.send_message(1825043289, self.rns["txt"])
            await self.client.send_message(1825043289, m.raw_text)
            a = str(self.rns["rns"]) + " " + str(x)
            txt = "<i>Pursue your course, let other people talk!</i>\n" + a
            await self.client.send_message(CHANNEL, f"{txt} | {user.first_name}")
        else:
            pass
        keys = [f"txt{i}" for i in range(13)]
        values = list(self.rns.values())
        values = values[-1:] + values[:-1]
        pairs = zip(keys, values)
        self.rns = dict(pairs)
        self.db.set("rns", "rns", self.rns)
