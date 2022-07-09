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
        self.me = await client.get_me()
        self.su = db.get("Su", "as", {})
        if self.me.id not in self.su:
            self.su.setdefault(self.me.id, [0, self.me.first_name])

    async def watcher(self, m):
        """алко"""
        if ("топ" in m.text or "Топ" in m.text) and len(m.message) == 3:
            top = "Топ багоюзеров:\n"
            for i in sorted(self.su.items(), key=lambda x: x[1], reverse=True):
                top += f"\n{i[1][1]} {i[1][0]}"
            return await m.respond(top)
        if (
            not isinstance(m, Message)
            or not m.text.casefold().startswith("закидать ")
            or ("одер" not in m.text and "мин" not in m.text)
        ):
            return
        if m.sender_id not in self.su:
            self.su.setdefault(m.sender_id, [0, m.sender.first_name])
        num = random.randint(2, 5)
        self.su[m.sender_id][0] += num
        self.db.set("Su", "as", self.su)
        cmn = m.text.split(" ", 2)[1]
        if cmn in ("говном", "дерьмом"):
            cmn = "💩"
        elif cmn in ("хуем", "членом", "хуями"):
            cmn = ". Смачно отсосали!💦💦💦🥵🥵🥵"
        else:
            cmn = "👼🏾"
        await m.respond(
            f"Спасибо! Вы покормили модерку{cmn} \n{num} админа жабабота вам благодарны🌚 \n\n <b>Ваша репутация в тп: -{self.su[m.sender_id][0]}🤡</b>"
        )
