from telethon.tl.types import Message

from .. import loader


@loader.tds
class ikkMod(loader.Module):
    """Алина, я люблю тебя!"""

    strings = {"name": "ikk"}

    async def client_ready(self, client, db):
        """ready"""
        self.client = client
        self.db = db
        self.me = await client.get_me()

    async def watcher(self, m):
        """алко"""
        if (
            not isinstance(m, Message)
            or not m.text.startswith("ID")
            or m.sender_id != self.me.id
        ):
            return
        r = (1660119676, 1539778138, 1584117978)
        t = int(m.text.split(" ", 1)[1])
        txt = f"<code>{t}</code>"
        for i in r:
            if i == 1660119676:
                n = "sgb"
            elif i == 1539778138:
                n = "ss"
            else:
                n = "bk"
            p = await self.client.get_messages(i, search=t)
            if p.total == 0:
                txt += ""
            else:
                txt += f" <b>{n}:</b> ban"
        await self.client.send_message("me", txt)
