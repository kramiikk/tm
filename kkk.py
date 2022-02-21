import asyncio
import logging
import re
from datetime import timedelta

from telethon import events

from .. import loader

logger = logging.getLogger(__name__)

@loader.tds
class KramiikkMod(loader.Module):
    """Алина, я люблю тебя."""

    strings = {"name": "kramiikk"}

    def __init__(self):
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.su = self.db.get("su", "users", [])
        self.mu = self.db.get("su", "names", {})
        self.me = await client.get_me()

    async def tms(self, m, i):
        global MS
        MS = timedelta(
            hours=m.date.hour, minutes=m.date.minute, seconds=m.date.second
        ) - timedelta(hours=i.date.hour, minutes=i.date.minute, seconds=i.date.second)

    async def err(self, m, p):
        try:
            async with self.client.conversation(m.chat_id) as conv:
                global RSP
                RSP = await conv.wait_event(
                    events.NewMessage(from_users=1124824021, chats=m.chat_id, pattern=p)
                )
        except asyncio.exceptions.TimeoutError:
            pass

    async def uku(self, m, cmn, txt):
        time = re.search(
            txt,
            RSP.text,
            re.IGNORECASE,
        )
        await self.client.send_message(
            m.chat_id,
            cmn,
            schedule=timedelta(hours=int(time.group(1)), minutes=int(time.group(2))),
        )

    async def bmj(self, m):
        p = "🐸"
        await self.err(m, p)
        jab = re.search(r"Ур.+: (\d+)[\s\S]*Бу.+: (\d+)", RSP.text)
        if "Живая" not in RSP.text:
            await m.respond("реанимировать жабу")
        p = "🏃‍♂️"
        await m.respond("<b>жаба инфо</b>")
        await self.err(m, p)
        if int(jab.group(1)) > 72 and int(jab.group(2)) > 3750:
            cmn = "откормить жабку"
            if "(Откормить через" in RSP.text:
                txt = r"Откормить через (\d+)ч:(\d+)м"
                await self.uku(m, cmn, txt)
            else:
                await m.respond(cmn)
            if "Можно отправиться" in RSP.text:
                cmn = "отправиться в золотое подземелье"
                await m.respond(cmn)
            elif (
                "В подземелье можно через 2ч" in RSP.text
                and "Жабу можно отправить" in RSP.text
            ):
                cmn = "работа крупье"
                await m.respond(cmn)
            elif "В подземелье можно" in RSP.text:
                cmn = "отправиться в золотое подземелье"
                txt = r"подземелье можно через (\d+)ч. (\d+)м."
                await self.uku(m, cmn, txt)
        else:
            cmn = "покормить жабку"
            if "покормить через" in RSP.text:
                txt = r"покормить через (\d+)ч:(\d+)м"
                await self.uku(m, cmn, txt)
            else:
                await m.respond(cmn)
            if "работу можно" in RSP.text:
                cmn = "работа крупье"
                txt = r"будет через (\d+)ч:(\d+)м"
                await self.uku(m, cmn, txt)
            elif "можно отправить" in RSP.text:
                await m.respond("работа крупье")
        if "жабу с работы" in RSP.text:
            cmn = "завершить работу"
            await m.respond(cmn)
        elif "жабу можно через" in RSP.text:
            cmn = "завершить работу"
            txt = r"через (\d+) часов (\d+) минут"
            await self.uku(m, cmn, txt)

    async def watcher(self, m):
        args = m.text
        name = "Монарх"
        try:
            if m.message.startswith("Йоу,") and m.sender_id in {1124824021}:
                if "одержал" in m.text:
                    klan = re.search(r"клан (.+) одержал[\s\S]* (\d+):(\d+)!", m.text)
                else:
                    klan = re.search(r", (.+) в этот[\s\S]* (\d+):(\d+)", m.text)
                s = await self.client.get_messages(1767017980, search=f"VS {klan.group(1)}")
                for i in s:
                    await self.tms(m, i)
                    if (
                        timedelta(days=0, hours=4)
                        <= MS
                        < timedelta(days=0, hours=4, minutes=30)
                    ):
                        p = re.search(r"..(.+) <.+> (.+)", i.text)
                        chet = f"{klan.group(2)}:{klan.group(3)}"
                        if int(klan.group(2)) < int(klan.group(3)):
                            chet = "".join(reversed(chet))
                        tog = f"🏆 {p.group(1)}\n             {chet}\n🔻 {p.group(2)}"
                        if (klan.group(1) == p.group(1) and "слабее" in m.text) or (
                            klan.group(1) != p.group(1) and "одержал" in m.text
                        ):
                            tog = f"🏆 {p.group(2)}\n             {chet}\n🔻 {p.group(1)}"
                        await i.reply(tog)
                ms = re.findall(r"•(<.+?(\d+).+>)", m.text)
                tog = f"Chat id: {m.chat_id}\n\nСостав {klan.group(1)}:"
                for i in ms:
                    tog += f"\n{i[0]} {i[1]}"
                await self.client.send_message(1655814348, tog)
            elif m.message.casefold().startswith(
                ("начать клановую войну", "@toadbot начать клановую войну")
            ) and len(m.message) in {21, 30}:
                p = None
                await self.err(m, p)
                if not RSP.text.startswith(("Алло", "Ваш клан", "Для старта", "Чувак")):
                    src = f"{m.chat_id} {m.sender_id} Клан:"
                    lira = None
                    ms = await self.client.get_messages(1655814348, search=src)
                    for i in ms:
                        if "Усилитель:" in i.message:
                            klan = re.search(
                                r"Лига: (.+)\nУсилитель: (.+)\n\nКлан: (.+)", i.text
                            )
                            lira = f"{klan.group(3)}\nЛига: {klan.group(1)}\nУсилитель: {klan.group(2)}"
                        else:
                            klan = re.search(r"Клан: (.+)", i.text)
                            src = f"Топ 35 кланов {klan.group(1)}"
                            p = await self.client.get_messages(1782816965, search=src)
                            if p.total == 0:
                                return
                            for s in p:
                                lira = re.search(r"Топ 35 кланов (.+) лиге", s.message)
                                lira = f"{klan.group(1)}\nЛига: {lira.group(1)}"
                    if "деревян" not in lira.casefold():
                        await self.client.send_message(1767017980, f"В поиске {lira}")
            elif m.message.startswith("Алло") and m.sender_id in {1124824021}:
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
                if "деревян" not in ms.casefold():
                    txt = f"⚡️{klan.group(1)} <b>VS</b> {klan.group(2)}\nЛига: {ms}"
                    await self.client.send_message(1767017980, txt)
                    capt = re.findall(r"<.+?id=(\d+)\">", m.text)
                    tog = f"Chat id: {m.chat_id}\nКлан: {klan.group(1)}\n\nСостав:"
                    for i in capt:
                        tog += f"\n{i}"
                    await self.client.send_message(1655814348, tog)
            elif m.message.casefold().startswith(("мой клан", "@toadbot мой клан")):
                p = "Клан"
                await self.err(m, p)
                klan = re.search(r"н (.+):[\s\S]*а: (.+)[\s\S]*ь: (.+)", RSP.text)
                info = f"Chat id: {m.chat_id}\nUser id: {m.sender_id}\nЛига: {klan.group(2)}\nУсилитель: {klan.group(3)}\n\nКлан: {klan.group(1)}"
                return await self.client.send_message(1655814348, info)
            elif m.message.casefold().startswith("/my_toad") and m.sender_id == self.me.id:
                await self.bmj(m)
            elif (
                m.message.startswith((name, f"@{self.me.username}"))
                and "инфо" in m.message
                and m.sender_id in {1785723159}
            ):
                await m.respond("<b>моя жаба</b>")
                await self.bmj(m)
            elif (m.message.startswith((name, f"@{self.me.username}"))) and (
                m.sender_id in {1785723159, 1261343954} or m.sender_id in self.su
            ):
                cmn = "<b>реанимировать жабу</b>"
                await m.respond(cmn)
                reply = await m.get_reply_message()
                if "напиши в" in m.message:
                    i = args.split(" ", 4)[3]
                    if i.isnumeric():
                        i = int(i)
                    s = args.split(" ", 4)[4]
                    if reply:
                        s = reply
                    await self.client.send_message(i, cmn)
                    await self.client.send_message(i, s)
                elif "арена" in m.message:
                    p = "•"
                    await self.client.send_message(m.chat_id, "<b>мои жабы</b>")
                    await self.err(m, p)
                    capt = re.findall(r"\| -100(\d+)", RSP.text)
                    for i in capt:
                        await self.client.send_message(int(i), cmn)
                        await self.client.send_message(int(i), "<b>на арену</b>")
                elif "напади" in m.message:
                    await m.respond("напасть на клан")
                elif "подземелье" in m.message:
                    await m.respond("<b>отправиться в золотое подземелье</b>")
                elif "снаряжение" in m.message:
                    p = "Ваше"
                    await self.client.send_message(m.chat_id, "<b>мое снаряжение</b>")
                    await self.err(m, p)
                    if "Ближний бой: Пусто" in RSP.text:
                        await m.respond("скрафтить клюв цапли")
                    if "Дальний бой: Пусто" in RSP.text:
                        await m.respond("скрафтить букашкомет")
                    if "Наголовник: Пусто" in RSP.text:
                        await m.respond("скрафтить наголовник из клюва цапли")
                    if "Нагрудник: Пусто" in RSP.text:
                        await m.respond("скрафтить нагрудник из клюва цапли")
                    if "Налапники: Пусто" in RSP.text:
                        await m.respond("скрафтить налапники из клюва цапли")
                else:
                    mmsg = args.split(" ", 2)[2]
                    if reply:
                        await reply.reply(mmsg)
                    else:
                        await m.respond(mmsg)
            elif f"Сейчас выбирает ход: {self.me.first_name}" in m.message and m.buttons:
                await m.respond("реанимировать жабу")
                await m.click(0)
            elif (
                m.sender_id in {830605725}
                and m.buttons
                and "Ваше уважение" not in m.message
                and "[12🔵" not in m.message
            ):
                await m.click(0)
            elif "НЕЗАЧЁТ!" in m.message and m.chat_id in {707693258}:
                args = [int(x) for x in m.text.split() if x.isnumeric()]
                delta = timedelta(hours=args[1], minutes=args[2], seconds=args[3])
                for i in range(3):
                    delta = delta + timedelta(seconds=30)
                    await self.client.send_message(m.chat_id, "Фарма", schedule=delta)
            elif m.message.casefold().startswith(
                ("моя жаба", "@toadbot моя жаба", "/my_toad")
            ) and len(m.message) in {17, 8}:
                p = "🐸"
                await self.err(m, p)
                if "Имя жабы" in RSP.text:
                    reg = re.search(
                        r"жабы: (.+)[\s\S]*й жабы: (.+)[\s\S]*Класс: (.+)",
                        RSP.raw_text,
                    )
                    info = f"Chat id: {m.chat_id}\nUser id: {m.sender_id}\nЖаба: {reg.group(1)}\nУровень: {reg.group(2)}\nКласс: {reg.group(3)}"
                    await self.client.send_message(1655814348, info)
            elif m.message.startswith("su!") and m.sender_id == self.me.id:
                i = int(args.split(" ", 1)[1])
                if i == self.me.id and i not in self.su:
                    self.su.append(i)
                    self.mu.setdefault("name", name)
                    await m.respond(f"{name} запомните")
                    self.db.set("su", "users", self.su)
                    self.db.set("su", "names", self.mu)
                    return
                if i in self.su:
                    self.su.remove(i)
                    await m.respond(f"🖕🏾 {i} успешно удален")
                else:
                    self.su.append(i)
                    await m.respond(f"🤙🏾 {i} успешно добавлен")
                self.db.set("su", "users", self.su)
            elif m.message.startswith("sn!") and m.sender_id == self.me.id:
                self.mu["name"] = args.split(" ", 1)[1]
                i = self.mu["name"]
                await m.respond(f"👻 {i} успешно добавлен")
                self.db.set("su", "names", self.mu)
        finally:
            return
