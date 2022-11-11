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
        if (
            not isinstance(m, Message)
            or not m.text.startswith("$ ")
            or m.sender_id != 1261343954
        ):
            return
        reply = await m.get_reply_message()
        i = m.text.split(" ", 2)[1]
        ids = (
            ((await self.client.get_entity(i)).id if not (i).isdigit() else i)
            if not reply
            else reply.sender_id
        )
        chat = 5136727087
        cmn = f"/чек {ids}"
        txt = f"<b><a href='tg://user?id={ids}'>link</a>\n{i}\n<code>{ids}</code>\n\n<a href='t.me/system_global_bot'>SGB:</a></b>"
        await self.err(chat, cmn)
        await self.client.delete_dialog(chat, revoke=True)
        if not RSP:
            txt += "\n---"
        txt += f"\n{RSP.text}"
        await asyncio.sleep(1)
        chat = 5390607371
        cmn = f"/check {ids}"
        txt += "\n\n\n<a href='t.me/SSelestia_bot'><b>Stop Scam:</b></a>"
        await self.err(chat, cmn)
        await self.client.delete_dialog(chat, revoke=True)
        if not RSP:
            txt += "\n---"
        txt += f"\n{RSP.text}"
        await asyncio.sleep(1)
        txt += "\n\n\n<a href='t.me/Biblootekabk'><b>Библиотека бк:</b></a>\n"
        p = await self.client.get_messages(1584117978, search=str(ids))
        if p.total == 0:
            txt += "---"
        else:
            for i in p:
                txt += i.text
        await m.edit(txt)
