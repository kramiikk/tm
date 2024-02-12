import asyncio
import random

from telethon.tl.types import Message

from .. import loader


@loader.tds
class rass1Mod(loader.Module):
    """rass1"""

    strings = {"name": "rass1"}

    async def client_ready(self, client, db):
        """ready"""
        self.db = db
        self.client = client
        self.me = await client.get_me()
        self.rass1 = db.get("Thr", "rass1", {})
        self.rass1.setdefault("min", 5)
        self.rass1.setdefault("cod", "У кого eсть C6 Аяка?")

    async def red(self, iid):
        """add or remove id"""
        if "chats" in self.rass1 and iid in self.rass1["chats"]:
            self.rass1["chats"].remove(iid)
            txt = f"<code>{iid}</code><b> удален</b>"
            if self.rass1["chats"] == []:
                self.rass1.pop("chats")
        elif "chats" in self.rass1:
            txt = f"<code>{iid}</code><b> добавлен</b>"
            self.rass1["chats"].append(iid)
        else:
            self.rass1.setdefault("chats", [iid])
            txt = f"<code>{iid}</code><b> добавлен</b>"
        self.db.set("Thr", "rass1", self.rass1)
        return txt

    async def thc3cmd(self, m):
        """кодовая фраза"""
        if len(m.text) < 6:
            return await m.edit(
                f"Фраза для добавления чата в список рассылки: <code>{self.rass1['cod']}</code>"
            )
        cmn = m.text.split(" ", 1)[1]
        self.rass1["cod"] = cmn
        self.db.set("Thr", "rass1", self.rass1)
        await m.edit(f"Установлена фраза: <code>{cmn}</code>")

    async def tht3cmd(self, m):
        """изменить частоту в минутах"""
        if len(m.text) < 6:
            return await m.edit(f"Отправляет каждые {self.rass1['min']} минут")
        cmn = m.text.split(" ", 1)[1]
        if not 0 < int(cmn) < 60:
            return await m.edit("Введите в интервале 1 - 59")
        self.rass1["min"] = int(cmn)
        self.db.set("Thr", "rass1", self.rass1)
        await m.edit(f"Будет отправлять каждые {cmn} минут")

    async def thr3cmd(self, m):
        r"""список чатов
        укажите откуда рассылка .thr main id"""
        if len(m.text) < 6:
            txt = "Главный: "
            if "main" not in self.rass1:
                txt += "не задан\n\nСписок:"
            else:
                txt += f'<code>{self.rass1["main"]}</code>\n\nСписок:'
            if "chats" not in self.rass1:
                txt += "\n Пусто"
            else:
                for i in self.rass1["chats"]:
                    txt += f"\n<code>{i}</code>"
            return await m.edit(txt)
        if "del" in m.text:
            self.rass1.clear()
            self.db.set("Thr", "rass1", self.rass1)
            return await m.edit("Список чатов очищен")
        cmn = m.text.split(" ", 2)[1]
        if cmn == "main":
            iid = int(m.text.split(" ", 2)[2])
            self.rass1.setdefault("main", iid)
            self.db.set("Thr", "rass1", self.rass1)
            txt = f"🤙🏾 Главный: <code>{iid}</code>"
            return await m.edit(txt)
        iid = int(cmn)
        txt = ""
        await m.edit(await self.red(iid))

    async def watcher(self, m: Message):
        """алко"""
        if not hasattr(m, "text") or not isinstance(m, Message):
            return
        if self.rass1["cod"] in m.text and m.sender_id == self.me.id:
            iid = m.chat_id
            await self.client.send_message("me", await self.red(iid))
        if (
            "chats" not in self.rass1
            or m.chat_id not in self.rass1["chats"]
            or m.sender_id == self.me.id
            or m.date.minute in (0, 1, 29, 30, 31, 58, 59)
            or random.randint(0, 3) != 3
        ):
            return
        await asyncio.sleep(random.randint(3, 13) + m.date.second)
        if m.chat_id not in self.rass1:
            self.rass1.setdefault(
                m.chat_id, (m.date.hour + m.date.minute) - self.rass1["min"]
            )
        if (
            -1
            < ((m.date.hour + m.date.minute) - self.rass1[m.chat_id])
            < self.rass1["min"]
        ):
            return
        self.rass1[m.chat_id] = m.date.hour + m.date.minute
        try:
            p = await self.client.get_messages(self.rass1["main"], limit=100)
        except Exception:
            return
        if self.me.id in (847865913, 6611807065) or p.total < 2:
            return
        p = p[random.randint(0, p.total - 2)]
        await asyncio.sleep(random.randint(1, 13))
        try:
            if p.media is not None:
                await self.client.send_file(m.chat_id, p, caption=p.text)
            else:
                await self.client.send_message(m.chat_id, p.text)
        except Exception:
            continue
