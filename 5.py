import asyncio
import random

from telethon.tl.types import Message

from .. import loader


@loader.tds
class rass5Mod(loader.Module):
    """rass5"""

    strings = {"name": "rass5"}

    async def client_ready(self, client, db):
        """ready"""
        self.db = db
        self.client = client
        self.me = await client.get_me()
        self.rass5 = db.get("Thr", "rass5", {})
        self.rass5.setdefault("min", 5)
        self.rass5.setdefault("cod", "У кого eсть C6 Аяка?")

    async def red(self, iid):
        """add or remove id"""
        if "chats" in self.rass5 and iid in self.rass5["chats"]:
            self.rass5["chats"].remove(iid)
            txt = f"<code>{iid}</code><b> удален</b>"
            if self.rass5["chats"] == []:
                self.rass5.pop("chats")
        elif "chats" in self.rass5:
            txt = f"<code>{iid}</code><b> добавлен</b>"
            self.rass5["chats"].append(iid)
        else:
            self.rass5.setdefault("chats", [iid])
            txt = f"<code>{iid}</code><b> добавлен</b>"
        self.db.set("Thr", "rass5", self.rass5)
        return txt

    async def thc5cmd(self, m):
        """кодовая фраза"""
        if len(m.text) < 6:
            return await m.edit(
                f"Фраза для добавления чата в список рассылки: <code>{self.rass5['cod']}</code>"
            )
        cmn = m.text.split(" ", 1)[1]
        self.rass5["cod"] = cmn
        self.db.set("Thr", "rass5", self.rass5)
        await m.edit(f"Установлена фраза: <code>{cmn}</code>")

    async def tht5cmd(self, m):
        """изменить частоту в минутах"""
        if len(m.text) < 6:
            return await m.edit(f"Отправляет каждые {self.rass5['min']} минут")
        cmn = m.text.split(" ", 1)[1]
        if not 0 < int(cmn) < 60:
            return await m.edit("Введите в интервале 1 - 59")
        self.rass5["min"] = int(cmn)
        self.db.set("Thr", "rass5", self.rass5)
        await m.edit(f"Будет отправлять каждые {cmn} минут")

    async def thr5cmd(self, m):
        r"""список чатов
        укажите откуда рассылка .thr main id"""
        if len(m.text) < 6:
            txt = "Главный: "
            if "main" not in self.rass5:
                txt += "не задан\n\nСписок:"
            else:
                txt += f'<code>{self.rass5["main"]}</code>\n\nСписок:'
            if "chats" not in self.rass5:
                txt += "\n Пусто"
            else:
                for i in self.rass5["chats"]:
                    txt += f"\n<code>{i}</code>"
            return await m.edit(txt)
        if "del" in m.text:
            self.rass5.clear()
            self.db.set("Thr", "rass5", self.rass5)
            return await m.edit("Список чатов очищен")
        cmn = m.text.split(" ", 2)[1]
        if cmn == "main":
            iid = int(m.text.split(" ", 2)[2])
            self.rass5.setdefault("main", iid)
            self.db.set("Thr", "rass5", self.rass5)
            txt = f"🤙🏾 Главный: <code>{iid}</code>"
            return await m.edit(txt)
        iid = int(cmn)
        txt = ""
        await m.edit(await self.red(iid))

    async def watcher(self, m: Message):
        """алко"""
        if not hasattr(m, "text") or not isinstance(m, Message):
            return
        if self.rass5["cod"] in m.text and m.sender_id == self.me.id:
            iid = m.chat_id
            await self.client.send_message("me", await self.red(iid))
        if (
            "chats" not in self.rass5
            or m.chat_id not in self.rass5["chats"]
            or m.sender_id == self.me.id
            or m.date.minute in (0, 1, 29, 30, 31, 58, 59)
            or random.randint(0, 13) != 3
        ):
            return
        await asyncio.sleep(random.randint(3, 13) + m.date.second)
        if m.chat_id not in self.rass5:
            self.rass5.setdefault(
                m.chat_id, (m.date.hour + m.date.minute) - self.rass5["min"]
            )
        if (
            -1
            < ((m.date.hour + m.date.minute) - self.rass5[m.chat_id])
            < self.rass5["min"]
        ):
            return
        self.rass5[m.chat_id] = m.date.hour + m.date.minute
        try:
            p = await self.client.get_messages(self.rass5["main"], limit=100)
        except Exception:
            return
        if p.total < 2:
            return
        p = p[random.randint(0, p.total - 2)]
        for i in self.rass5["chats"]:
            await asyncio.sleep(random.randint(3, 13))
            try:
                if p.media is not None:
                    await self.client.send_file(i, p, caption=p.text)
                else:
                    await self.client.send_message(i, p.text)
            except Exception:
                continue
