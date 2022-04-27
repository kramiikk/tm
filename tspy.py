import asyncio
import re
from datetime import timedelta

from telethon import events

from .. import loader


@loader.tds
class SpyMod(loader.Module):
    """Слежка за кланами в Жабаботе."""

    strings = {"name": "spy"}

    async def client_ready(self, client, db):
        self.db = db
        self.client = client

    @staticmethod
    async def tms(m, i):
        global MS
        MS = timedelta(
            hours=m.date.hour, minutes=m.date.minute, seconds=m.date.second
        ) - timedelta(hours=i.date.hour, minutes=i.date.minute, seconds=i.date.second)

    async def err(self, m, p):
        async with self.client.conversation(m.chat_id, exclusive=False) as conv:
            try:
                global RSP
                RSP = await conv.wait_event(
                    events.NewMessage(from_users=1124824021, chats=m.chat_id, pattern=p)
                )
            except asyncio.exceptions.TimeoutError:
                RSP = await self.client.get_messages(m.chat_id, search=" ")
            await conv.cancel_all()

    async def aww(self, m):
        if m.from_id not in {1124824021}:
            return
        if "одержал" in m.text:
            klan = re.search(r"Клан (.+) одержал[\s\S]* (\d+):(\d+)", m.text)
        elif "проиграли" in m.text:
            klan = re.search(r", (.+), вы[\s\S]* (\d+):(\d+)", m.text)
        else:
            return
        s = await self.client.get_messages(1767017980, search=f"VS {klan.group(1)}")
        for i in s:
            await self.tms(m, i)
            if timedelta(days=0, hours=4) > MS:
                return
            p = re.search(r"..(.+) <.+> (.+)", i.text)
            chet = f"{klan.group(2)}:{klan.group(3)}"
            if int(klan.group(2)) < int(klan.group(3)):
                chet = "".join(reversed(chet))
            tog = f"🏆 {p.group(1)}\n             {chet}\n🔻 {p.group(2)}"
            if (klan.group(1) == p.group(1) and "проиграли" in m.text) or (
                klan.group(1) != p.group(1) and "одержал" in m.text
            ):
                tog = f"🏆 {p.group(2)}\n             {chet}\n🔻 {p.group(1)}"
            await i.reply(tog)
        ms = re.findall(r"•.+(<.+?(\d+).+>)", m.text)
        tog = f"Chat id: {m.chat_id}\n\nСостав {klan.group(1)}:"
        for i in ms:
            tog += f"\n{i[0]} {i[1]}"
        return await self.client.send_message(1655814348, tog)

    async def bww(self, m):
        if (RSP.text.startswith(("Алло", "Ваш клан", "Для старта", "Чувак"))) or (
            len(m.message) not in {21, 30}
        ):
            return
        p = None
        await self.err(m, p)
        src = f"{m.chat_id} {m.sender_id} Клан:"
        ms = await self.client.get_messages(1655814348, search=src)
        for i in (i for i in ms if "деревян" not in i.text.casefold()):
            if "Усилитель:" in i.message:
                klan = re.search(r"Лига: (.+)\nУсилитель: (.+)\n\nКлан: (.+)", i.text)
                lira = f"{klan.group(3)}\nЛига: {klan.group(1)}\nУсилитель: {klan.group(2)}"
            else:
                klan = re.search(r"Клан: (.+)", i.text)
                src = f"Топ 35 кланов {klan.group(1)}"
                p = await self.client.get_messages(1782816965, search=src)
                if p.total == 0:
                    return
                for i in p:
                    lira = re.search(r"Топ 35 кланов (.+) лиге", i.message)
                    lira = f"{klan.group(1)}\nЛига: {lira.group(1)}"
            return await self.client.send_message(1767017980, f"В поиске {lira}")
        return

    async def cww(self, m):
        if m.from_id not in {1124824021}:
            return
        klan = re.search(r"клана (.+) нашелся враг (.+), пора", m.text)
        src = f"Топ 35 кланов {klan.group(1)}"
        ms = await self.client.get_messages(1782816965, search=src)
        if ms.total == 0:
            src = f"{m.chat_id} {klan.group(1)} Лига:"
            p = await self.client.get_messages(1655814348, search=src)
            if p.total == 0:
                return
            for i in p:
                ms = re.search(r"Лига: (.+)", i.text).group(1)
        else:
            for i in ms:
                ms = re.search(r"Топ 35 кланов (.+) лиге", i.text).group(1)
        if "деревян" in ms.casefold():
            return
        txt = f"⚡️{klan.group(1)} <b>VS</b> {klan.group(2)}\nЛига: {ms}"
        await self.client.send_message(1767017980, txt)
        capt = re.findall(r"<.+?id=(\d+)\">", m.text)
        tog = f"Chat id: {m.chat_id}\nКлан: {klan.group(1)}\n\nСостав:"
        for i in capt:
            tog += f"\n{i}"
        return await self.client.send_message(1655814348, tog)

    async def dww(self, m):
        p = "Клан"
        await self.err(m, p)
        klan = re.search(r"н (.+):[\s\S]*а: (.+)[\s\S]*ь: (.+)", RSP.text)
        info = f"Chat id: {m.chat_id}\nUser id: {m.sender_id}\nЛига: {klan.group(2)}\nУсилитель: {klan.group(3)}\n\nКлан: {klan.group(1)}"
        return await self.client.send_message(1655814348, info)

    async def eww(self, m):
        if len(m.message) not in {17, 8}:
            return
        p = "🐸"
        await self.err(m, p)
        reg = re.search(
            r": (.+)[\s\S]*У.+: (.+)[\s\S]*сс.+: (.+)",
            RSP.text,
        )
        info = f"Chat id: {m.chat_id}\nUser id: {m.sender_id}\nЖаба: {reg.group(1)}\nУровень: {reg.group(2)}\nКласс: {reg.group(3)}"
        return await self.client.send_message(1655814348, info)

    async def eee(self, m):
        fff = {
            "Очень": self.aww(m),
            "Клан": self.aww(m),
            "начать клановую войну": self.bww(m),
            "@toadbot начать клановую войну": self.bww(m),
            "Алло": self.cww(m),
            "мой клан": self.dww(m),
            "@toadbot мой клан": self.dww(m),
            "моя жаба": self.eww(m),
            "@toadbot моя жаба": self.eww(m),
            "/my_toad": self.eww(m),
        }
        for i in (i for i in fff if m.message.casefold().startswith(i)):
            return await fff[i]
        return

    async def watcher(self, m):
        return await self.eee(m)
