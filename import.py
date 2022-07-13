# scope: ffmpeg
# requires: pytube python-ffmpeg
import datetime
import os
import random

from pytube import YouTube
from telethon.tl.types import Message

from .. import loader, utils


@loader.tds
class AssMod(loader.Module):
    """Модуль"""

    strings = {"name": "Ass"}

    async def client_ready(self, client, db):
        """ready"""
        self.client = client
        self.db = db
        self.su = db.get("Su", "as", {})

    async def watcher(self, m):
        """алко"""
        if not isinstance(m, Message):
            return
        if m.text.casefold() == "топ":
            top = "Топ багоюзеров:"
            a = sorted(self.su.items(), key=lambda x: x[1], reverse=True)
            for i in enumerate(i, 1):
                a = "🩲" if i[0] == 1 else i[1][1][0]
                top += f"\n{i[0]} | {i[1][1][1]} <code>{a}</code>"
            return await m.respond(top)
        if m.text.casefold() == "сменить жабу":

            def dlyt():
                yt = YouTube("https://www.youtube.com/watch?v=lLDXtjXMjVg")
                yt = (
                    yt.streams.filter(progressive=True, file_extension="mp4")
                    .order_by("resolution")
                    .desc()
                    .first()
                )
                return yt.download("/tmp")

            path = await utils.run_sync(dlyt)
            await self.client.send_file(m.peer_id, path, reply_to=m)
            os.remove(path)
        if (
            not m.text.casefold().startswith("закидать ")
            or ("модер" not in m.text.casefold() and "админ" not in m.text.casefold())
            or m.text.count(" ") == 1
        ):
            return
        ct = datetime.datetime.now()
        time = ct.day + ct.minute + ct.second
        self.su.setdefault("minute", time)
        if -1 < (time - self.su["minute"]) < 2:
            return await m.respond("надень штаны👖")
        self.su["minute"] = time
        self.db.set("Su", "as", self.su)
        self.su.setdefault(str(m.sender_id), [0, m.sender.first_name])
        num = random.randint(2, 5)
        self.su[str(m.sender_id)][0] += num
        self.db.set("Su", "as", self.su)
        top = {"дерь": "💩", "говн": "💩", "письк": "💩", "ху": "🥵", "член": "🥵"}
        for i in top:
            cmn = "🤰🏼"
            if i in m.text.casefold():
                cmn = " Смачно отсосали!💦💦💦🥵🥵🥵" if top[i] == "🥵" else top[i]
                break
        await m.respond(
            f"Спасибо! Вы накормили модерку🥞{cmn} \n{num} админа жабабота вам благодарны🎉 \n\n <b>Ваша репутация в тп: -{self.su[str(m.sender_id)][0]}🤯</b>"
        )
