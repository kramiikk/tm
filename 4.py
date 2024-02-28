import asyncio
import random

from telethon.tl.types import Message

from .. import loader


@loader.tds
class rass4Mod(loader.Module):
    """rass4"""

    strings = {"name": "rass4"}

    async def client_ready(self, client, db):
        """ready"""
        self.db = db
        self.client = client
        self.me = await client.get_me()
        self.rass4 = db.get("Thr", "rass4", {})
        self.rass4.setdefault("min", 5)
        self.rass4.setdefault("cod", "У кого eсть C6 Аяка?")

    async def red(self, iid):
        """add or remove id"""
        if "chats" in self.rass4 and iid in self.rass4["chats"]:
            self.rass4["chats"].remove(iid)
            txt = f"<code>{iid}</code><b> удален</b>"
            if self.rass4["chats"] == []:
                self.rass4.pop("chats")
        elif "chats" in self.rass4:
            txt = f"<code>{iid}</code><b> добавлен</b>"
            self.rass4["chats"].append(iid)
        else:
            self.rass4.setdefault("chats", [iid])
            txt = f"<code>{iid}</code><b> добавлен</b>"
        self.db.set("Thr", "rass4", self.rass4)
        return txt

    async def thc4cmd(self, m):
        """кодовая фраза"""
        if len(m.text) < 6:
            return await m.edit(
                f"Фраза для добавления чата в список рассылки: <code>{self.rass4['cod']}</code>"
            )
        cmn = m.text.split(" ", 1)[1]
        self.rass4["cod"] = cmn
        self.db.set("Thr", "rass4", self.rass4)
        await m.edit(f"Установлена фраза: <code>{cmn}</code>")

    async def tht4cmd(self, m):
        """изменить частоту в минутах"""
        if len(m.text) < 6:
            return await m.edit(f"Отправляет каждые {self.rass4['min']} минут")
        cmn = m.text.split(" ", 1)[1]
        if not 0 < int(cmn) < 60:
            return await m.edit("Введите в интервале 1 - 59")
        self.rass4["min"] = int(cmn)
        self.db.set("Thr", "rass4", self.rass4)
        await m.edit(f"Будет отправлять каждые {cmn} минут")

    async def thr4cmd(self, m):
        r"""список чатов
        укажите откуда рассылка .thr main id"""
        if len(m.text) < 6:
            txt = "Главный: "
            if "main" not in self.rass4:
                txt += "не задан\n\nСписок:"
            else:
                txt += f'<code>{self.rass4["main"]}</code>\n\nСписок:'
            if "chats" not in self.rass4:
                txt += "\n Пусто"
            else:
                for i in self.rass4["chats"]:
                    txt += f"\n<code>{i}</code>"
            return await m.edit(txt)
        if "del" in m.text:
            self.rass4.clear()
            self.db.set("Thr", "rass4", self.rass4)
            return await m.edit("Список чатов очищен")
        cmn = m.text.split(" ", 2)[1]
        if cmn == "main":
            iid = int(m.text.split(" ", 2)[2])
            self.rass4.setdefault("main", iid)
            self.db.set("Thr", "rass4", self.rass4)
            txt = f"🤙🏾 Главный: <code>{iid}</code>"
            return await m.edit(txt)
        iid = int(cmn)
        txt = ""
        await m.edit(await self.red(iid))

    async def watcher(self, m: Message):
        """алко"""
        if not hasattr(m, "text") or not isinstance(m, Message):
            return
        if self.rass4["cod"] in m.text and m.sender_id == self.me.id:
            iid = m.chat_id
            await self.client.send_message("me", await self.red(iid))
        if (
            "chats" not in self.rass4
            or m.chat_id not in self.rass4["chats"]
            or m.sender_id == self.me.id
            or m.date.minute in (0, 1, 29, 30, 31, 58, 59)
            or random.randint(0, 13) != 3
        ):
            return
        await asyncio.sleep(random.randint(3, 13) + m.date.second)
        if m.chat_id not in self.rass4:
            self.rass4.setdefault(
                m.chat_id, (m.date.hour + m.date.minute) - self.rass4["min"]
            )
        if (
            -1
            < ((m.date.hour + m.date.minute) - self.rass4[m.chat_id])
            < self.rass4["min"]
        ):
            return
        self.rass4[m.chat_id] = m.date.hour + m.date.minute
        try:
            p = await self.client.get_messages(self.rass4["main"], limit=100)
        except Exception:
            return
        if p.total < 2:
            return
        p = p[random.randint(0, p.total - 2)]
        for i in self.rass4["chats"]:
            await asyncio.sleep(random.randint(3, 13))
            try:
                if p.media is not None:
                    await self.client.send_file(i, p, caption=p.text)
                else:
                    await self.client.send_message(i, p.text)
            except Exception:
                continue
