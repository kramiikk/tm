import asyncio
import random

from telethon.tl.types import Message

from .. import loader


@loader.tds
class thrMod(loader.Module):
    """thr"""

    strings = {"name": "thr"}

    async def client_ready(self, client, db):
        """ready"""
        self.db = db
        self.client = client
        self.me = await client.get_me()
        self.thr = db.get("Thr", "thr", {})
        self.thr.setdefault("min", 5)
        self.thr.setdefault("cod", "Ayaka c6?")

    async def red(self, iid):
        """add or remove id"""
        if "chats" in self.thr and iid in self.thr["chats"]:
            self.thr["chats"].remove(iid)
            txt = f"<code>{iid}</code><b> added</b>"
            if self.thr["chats"] == []:
                self.thr.pop("chats")
        elif "chats" in self.thr:
            txt = f"<code>{iid}</code><b> removed</b>"
            self.thr["chats"].append(iid)
        else:
            self.thr.setdefault("chats", [iid])
            txt = f"<code>{iid}</code><b> removed</b>"
        self.db.set("Thr", "thr", self.thr)
        return txt

    async def thccmd(self, m):
        """phrase"""
        if len(m.text) < 5:
            return await m.edit(
                f"Phrase: <code>{self.thr['cod']}</code>"
            )
        cmn = m.text.split(" ", 1)[1]
        self.thr["cod"] = cmn
        self.db.set("Thr", "thr", self.thr)
        await m.edit(f"Phrase: <code>{cmn}</code>")

    async def thtcmd(self, m):
        """timer"""
        if len(m.text) < 5:
            return await m.edit(f"{self.thr['min']} minute")
        cmn = m.text.split(" ", 1)[1]
        if not 0 < int(cmn) < 60:
            return await m.edit("input 1 - 59")
        self.thr["min"] = int(cmn)
        self.db.set("Thr", "thr", self.thr)
        await m.edit(f"{cmn} minute")

    async def thrcmd(self, m):
        r"""main group .thr main id"""
        if len(m.text) < 5:
            txt = "Main: "
            if "main" not in self.thr:
                txt += "-\n\nList:"
            else:
                txt += f'<code>{self.thr["main"]}</code>\n\nList:'
            if "chats" not in self.thr:
                txt += "\n Empty"
            else:
                for i in self.thr["chats"]:
                    txt += f"\n<code>{i}</code>"
            return await m.edit(txt)
        if "del" in m.text:
            self.thr.clear()
            self.db.set("Thr", "thr", self.thr)
            return await m.edit("Cleared")
        cmn = m.text.split(" ", 2)[1]
        if cmn == "main":
            iid = int(m.text.split(" ", 2)[2])
            self.thr.setdefault("main", iid)
            self.db.set("Thr", "thr", self.thr)
            txt = f"🤙🏾 Main: <code>{iid}</code>"
            return await m.edit(txt)
        await m.edit(await self.red(int(cmn)))

    async def watcher(self, m: Message):
        """alko"""
        if not hasattr(m, "text") or not isinstance(m, Message):
            return
        if self.thr["cod"] in m.text and m.sender_id == self.me.id:
            iid = m.chat_id
            await self.client.send_message("me", await self.red(iid))
        if (
            "chats" not in self.thr
            or m.chat_id not in self.thr["chats"]
            or m.sender_id == self.me.id
            or m.date.minute in (0, 1, 29, 30, 31, 58, 59)
            or random.randint(0, 3) != 3
        ):
            return
        await asyncio.sleep(random.randint(3, 13) + m.date.second)
        if m.chat_id not in self.thr:
            self.thr.setdefault(
                m.chat_id, (m.date.hour + m.date.minute) - self.thr["min"]
            )
        if -1 < ((m.date.hour + m.date.minute) - self.thr[m.chat_id]) < self.thr["min"]:
            return
        self.thr[m.chat_id] = m.date.hour + m.date.minute
        try:
            p = await self.client.get_messages(self.thr["main"], limit=100)
        except Exception:
            return
        if p.total < 2:
            return
        p = p[random.randint(0, p.total - 2)]
        cc = [m.chat_id] if random.randint(0, 181) != 3 else self.thr["chats"]
        for i in cc:
            await asyncio.sleep(random.randint(1, 13))
            try:
                if p.media is not None:
                    await self.client.send_file(i, p, caption=p.text)
                else:
                    await self.client.send_message(i, p.text)
            except Exception:
                continue
