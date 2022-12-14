from telethon.tl.types import Message

from .. import loader


chat = [1857641810, 1545199233]


@loader.tds
class kgkMod(loader.Module):
    """Алина, я люблю тебя!"""

    strings = {"name": "kgk"}

    async def client_ready(self, client, db):
        """ready"""
        self.client = client
        self.db = db

    async def watcher(self, m):
        """алко"""
        if (
            not isinstance(m, Message)
            or m.sender_id != -1001886209557
            or not m.text.startswith("Пользователь")
        ):
            return
        id = re.search(r"\n.+ди\D+(\d+)", m.text).group(1)
        for i in chat:
            await self.client.send_message(i, f"!ban {id} можете увидеть в @KGBBANS")
