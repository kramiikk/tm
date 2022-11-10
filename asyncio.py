import asyncio

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

    async def err(self, chat, cmn):
        """работа с ответом жабабота"""
        try:
            async with self.client.conversation(chat, exclusive=False) as conv:
                await conv.send_message(cmn)
                global RSP
                RSP = await conv.get_response()
                await conv.cancel_all()
        except Exception:
            pass

    async def watcher(self, m):
        """алко"""
        if not isinstance(m, Message) or m.chat_id != 1709411724:
            return
        ids = (
            (await self.client.get_entity(m.raw_text)).id
            if not (m.raw_text).isdigit()
            else m.raw_text
        )
        chat = 5136727087
        cmn = f"/чек {ids}"
        txt = f"<b><a href='tg://user?id={ids}'>link</a>\n<a href='t.me/system_global_bot'>SGB:</b></a>"
        await self.err(chat, cmn)
        if not RSP:
            txt += "\n---"
        txt += f"\n{RSP}"
        await asyncio.sleep(1)
        chat = 5390607371
        cmn = f"/check {ids}"
        txt += "\n\n\n<a href='t.me/SSelestia_bot'><b>Stop Scam:</b></a>"
        await self.err(chat, cmn)
        if not RSP:
            txt += "\n---"
        txt += f"\n{RSP}"
        await m.respond(txt)