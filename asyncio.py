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
            or not m.text.startswith("Здравствуйте")
            or m.sender_id != self.me.id
        ):
            return
        if "Здравствуйте!" in m.text:
            return await self.client.send_message('me', f"{m.chat_id}")
        reply = await m.get_reply_message()
        ids = m.chat_id if not reply else reply.sender_id
        txt = f"<code>{ids}</code>\n\n"
        p = await self.client.get_messages(1660119676, search=str(ids))
        if p.total == 0:
            txt += ""
        else:
            txt += "<b>sgb:</b> ban\n\n"
        p = await self.client.get_messages(1539778138, search=str(ids))
        if p.total == 0:
            txt += ""
        else:
            txt += "<b>ss:</b> ban\n\n"
        p = await self.client.get_messages(1584117978, search=str(ids))
        if p.total == 0:
            txt += ""
        else:
            txt += "<b>bk:</b> ban\n"
        if "ban" not in txt:
            txt += "нет в слитых"
        await self.client.send_message('me', txt)
