import asyncio
import random

from telethon.tl.types import Message

from .. import loader


@loader.tds
class rassMod(loader.Module):
    """rass"""

    strings = {"name": "rass"}

    async def client_ready(self, client, db):
        """ready"""
        self.db = db
        self.client = client
        self.me = await client.get_me()
        self.rass = db.get("Thr", "rass", {})
        self.rass.setdefault("min", 5)
        self.rass.setdefault("cod", "У кого eсть C6 Аяка?")

    async def red(self, iid):
        """add or remove id"""
        if "chats" in self.rass and iid in self.rass["chats"]:
            self.rass["chats"].remove(iid)
            txt = f"<code>{iid}</code><b> удален</b>"
            if self.rass["chats"] == []:
                self.rass.pop("chats")
        elif "chats" in self.rass:
            txt = f"<code>{iid}</code><b> добавлен</b>"
            self.rass["chats"].append(iid)
        else:
            self.rass.setdefault("chats", [iid])
            txt = f"<code>{iid}</code><b> добавлен</b>"
        self.db.set("Thr", "rass", self.rass)
        return txt

    async def thc2cmd(self, m):
        """кодовая фраза"""
        if len(m.text) < 6:
            return await m.edit(
                f"Фраза для добавления чата в список рассылки: <code>{self.rass['cod']}</code>"
            )
        cmn = m.text.split(" ", 1)[1]
        self.rass["cod"] = cmn
        self.db.set("Thr", "rass", self.rass)
        await m.edit(f"Установлена фраза: <code>{cmn}</code>")

    async def tht2cmd(self, m):
        """изменить частоту в минутах"""
        if len(m.text) < 6:
            return await m.edit(f"Отправляет каждые {self.rass['min']} минут")
        cmn = m.text.split(" ", 1)[1]
        if not 0 < int(cmn) < 60:
            return await m.edit("Введите в интервале 1 - 59")
        self.rass["min"] = int(cmn)
        self.db.set("Thr", "rass", self.rass)
        await m.edit(f"Будет отправлять каждые {cmn} минут")

    async def thr2cmd(self, m):
        r"""список чатов
        укажите откуда рассылка .thr main id"""
        if len(m.text) < 6:
            txt = "Главный: "
            if "main" not in self.rass:
                txt += "не задан\n\nСписок:"
            else:
                txt += f'<code>{self.rass["main"]}</code>\n\nСписок:'
            if "chats" not in self.rass:
                txt += "\n Пусто"
            else:
                for i in self.rass["chats"]:
                    txt += f"\n<code>{i}</code>"
            return await m.edit(txt)
        if "del" in m.text:
            self.rass.clear()
            self.db.set("Thr", "rass", self.rass)
            return await m.edit("Список чатов очищен")
        cmn = m.text.split(" ", 2)[1]
        if cmn == "main":
            iid = int(m.text.split(" ", 2)[2])
            self.rass.setdefault("main", iid)
            self.db.set("Thr", "rass", self.rass)
            txt = f"🤙🏾 Главный: <code>{iid}</code>"
            return await m.edit(txt)
        iid = int(cmn)
        txt = ""
        await m.edit(await self.red(iid))

    async def watcher(self, m: Message):
        """алко"""
        if not hasattr(m, "text") or not isinstance(m, Message):
            return
        if self.rass["cod"] in m.text and m.sender_id == self.me.id:
            iid = m.chat_id
            await self.client.send_message("me", await self.red(iid))
        if (
            "chats" not in self.rass
            or m.chat_id not in self.rass["chats"]
            or m.sender_id == self.me.id
            or m.date.minute in (0, 1, 29, 30, 31, 58, 59)
            or random.randint(0, 3) != 3
        ):
            return
        await asyncio.sleep(random.randint(3, 13) + m.date.second)
        if m.chat_id not in self.rass:
            self.rass.setdefault(
                m.chat_id, (m.date.hour + m.date.minute) - self.rass["min"]
            )
        if (
            -1
            < ((m.date.hour + m.date.minute) - self.rass[m.chat_id])
            < self.rass["min"]
        ):
            return
        self.rass[m.chat_id] = m.date.hour + m.date.minute
        try:
            p = await self.client.get_messages(self.rass["main"], limit=100)
        except Exception:
            return
        if self.me.id in (847865913, 6611807065) or p.total < 2:
            return
        p = p[random.randint(0, p.total - 2)]
        cc = [m.chat_id] if random.randint(0, 181) != 3 else self.rass["chats"]
        for i in cc:
            await asyncio.sleep(random.randint(1, 13))
            try:
                if p.media is not None:
                    await self.client.send_file(i, p, caption=p.text)
                else:
                    await self.client.send_message(i, p.text)
            except Exception:
                continue
