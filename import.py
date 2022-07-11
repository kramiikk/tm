import random

from telethon.tl.types import Message

from .. import loader


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
        if m.text.lower() == "топ":
            ass = self.db.get("Su", "as", {})
            top = "Топ багоюзеров:\n"
            for i in sorted(ass.items(), key=lambda x: x[1], reverse=True):
                top += f"\n{i[1][1]} {i[1][0]}"
            return await m.respond(top)
        if (
            not isinstance(m, Message)
            or not m.text.casefold().startswith("закидать ")
            or ("одер" not in m.text and "мин" not in m.text)
        ):
            return
        ass = self.db.get("Su", "as", {})
        send = str(m.sender_id)
        if send not in ass:
            ass.setdefault(send, [0, m.sender.first_name])
        num = random.randint(2, 5)
        ass[send][0] += num
        self.db.set("Su", "as", ass)
        cmn = m.text.split(" ", 2)[1]
        if cmn in ("дерьмом", "говнищем", "говнишками"):
            cmn = "💩"
        elif cmn in ("письками", "хуями", "членами"):
            cmn = ". Смачно отсосали!💦💦💦🥵🥵🥵"
        else:
            cmn = "👼🏾"
        await m.respond(
            f"Спасибо! Вы покормили модерку{cmn} \n{num} админа жабабота вам благодарны🌚 \n\n <b>Ваша репутация в тп: -{ass[send][0]}🤡</b>"
        )
