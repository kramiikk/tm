import functools
import pytube
import random

from telethon.tl.types import Message

from .. import loader, utils

from telethon import events


@loader.tds
class AssMod(loader.Module):
    """Модуль"""

    strings = {"name": "Ass"}

    async def client_ready(self, client, db):
        """ready"""
        self.client = client
        self.db = db

    async def watcher(self, m):
        """алко"""
        if not isinstance(m, Message):
            return
        if m.text.casefold() == "топ":
            ass = self.db.get("Su", "as", {})
            top = "Топ багоюзеров:\n"
            for i in sorted(ass.items(), key=lambda x: x[1], reverse=True):
                top += f"\n{i[1][1]} {i[1][0]}"
            return await m.respond(top)
        if m.text.casefold() == "сменить жабу":
            yt = pytube.YouTube("https://www.youtube.com/watch?v=lLDXtjXMjVg")
            stream = yt.streams.first()
            await self.client.send_file(m.chat_id, stream.download(), reply_to=m)
        if (
            not m.text.casefold().startswith("закидать ")
            or ("модер" not in m.text.casefold() and "админ" not in m.text.casefold())
            or m.text.count(" ") == 1
        ):
            return
        ass = self.db.get("Su", "as", {})
        send = str(m.sender_id)
        if send not in ass:
            ass.setdefault(send, [0, m.sender.first_name])
        num = random.randint(2, 5)
        ass[send][0] += num
        self.db.set("Su", "as", ass)
        top = {"дерь": "💩", "говн": "💩", "письк": "💩", "ху": "🥵", "член": "🥵"}
        for i in top:
            cmn = "🤰🏼"
            if i in m.text.casefold():
                cmn = " Смачно отсосали!💦💦💦🥵🥵🥵" if top[i] == "🥵" else top[i]
                break
        await m.respond(
            f"Спасибо! Вы накормили модерку🥞{cmn} \n{num} админа жабабота вам благодарны🎉 \n\n <b>Ваша репутация в тп: -{ass[send][0]}🤯</b>"
        )
