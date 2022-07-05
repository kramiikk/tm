import asyncio
import datetime
import random
import re

from telethon import events
from telethon.tl.types import Message

from .. import loader


@loader.tds
class ZhabaMod(loader.Module):
    """Модуль для @toadbot"""

    strings = {"name": "Zhaba"}

    async def client_ready(self, client, db):
        """ready"""
        self.client = client
        self.db = db
        self.su = db.get("Su", "su", {})
        self.me = await client.get_me()
        if "name" not in self.su:
            self.su.setdefault("name", self.me.first_name)
            self.su.setdefault("users", [1124824021, self.me.id, 1785723159])
            self.db.set("Su", "su", self.su)
        self.ded = {
            "туса": "Жабу на тусу",
            "карту": "Отправить карту",
            "напади": "Напасть на клан",
            "снаряга": "Мое снаряжение",
            "Банда: Пусто": "взять жабу",
            "инвентарь": "Мой инвентарь",
            "можно отправить": "Работа крупье",
            "реанимируй": "Реанимировать жабу",
            "Можно на арену!": "@toadbot На арену",
            "Используйте атаку": "@toadbot На арену",
            "Дальний бой: Пусто": "скрафтить букашкомет",
            "жабу с работы": "@toadbot Завершить работу",
            "Забрать жабенка": "@toadbot Забрать жабенка",
            "Ближний бой: Пусто": "скрафтить клюв цапли",
            "можно покормить": "@toadbot Покормить жабу",
            "Можно откормить": "@toadbot Откормить жабу",
            "Покормить жабенка": "@toadbot Покормить жабенка",
            "Брак вознаграждение": "@toadbot Брак вознаграждение",
            "Можно отправиться": "Отправиться в золотое подземелье",
            "В детский сад!": "@toadbot Отправить жабенка в детсад",
            "Нагрудник: Пусто": "скрафтить нагрудник из клюва цапли",
            "Налапники: Пусто": "скрафтить налапники из клюва цапли",
            "Наголовник: Пусто": "скрафтить наголовник из клюва цапли",
            "Отправить жабенка на махач": "@toadbot Отправить жабенка на махач",
        }

    async def err(self, chat, cmn):
        """работа с ответом жабабота"""
        try:
            async with self.client.conversation(chat, exclusive=False) as conv:
                await conv.send_message(cmn)
                global RSP
                RSP = await conv.wait_event(
                    events.NewMessage(incoming=True, from_users=1124824021, chats=chat)
                )
                await conv.cancel_all()
        except Exception:
            pass

    async def stcmd(self, m):
        """статус юзербота"""
        ub = (
            "<b>Статус",
            "auto",
            " 🟢",
            " ⭐️",
            "\n├",
            "\n━",
            " ⛔️",
            "<b>👑Userbot:</b>",
        )
        ar = (
            "\n\n    • Арена:",
            "bs",
            " 🟢",
            " ⭐️",
            "\n       ├",
            "\n        ━",
            " ⛔️",
            "<b>🤺Арена:</b>",
        )
        fm = (
            "\n    • Семья:",
            "hs",
            " 🟢",
            " ⭐️",
            "\n       ├",
            "\n        ━",
            " ⛔️",
            "<b>👨‍👩‍👧‍👦Семья:</b>",
        )
        ok = (
            "\n    • Откормить:",
            "gs",
            " 🟢",
            " ⭐️",
            "\n       ├",
            "\n        ━",
            " ⛔️",
            "<b>🤰🏽Откормить:</b>",
        )
        pz = (
            "\n    • Подземелье:",
            "fs",
            " 🟢",
            " ⭐️",
            "\n       ├",
            "\n        ━",
            " ⛔️",
            "<b>🦹‍♀️Подземелье:</b>",
        )
        sn = (
            "\n    • Снаряжение:",
            "as",
            " 🟢",
            " ⭐️",
            "\n       ├",
            "\n        ━",
            " ⛔️",
            "<b>⚔️Снаряжение:</b>",
        )
        jk = (
            "\n    🎰Крупье:",
            "cs",
            " 🟢",
            " ⭐️",
            "\n       ├",
            "\n        ━",
            " ⛔️",
            "<b>🎰Крупье:</b>",
        )
        jg = (
            "\n\n    💶Грабитель:",
            "es",
            " 🟢",
            " ⭐️",
            "\n       ├",
            "\n        ━",
            " ⛔️",
            "<b>💶Грабитель:</b>",
        )
        js = (
            "\n    🍽Столовая:",
            "ss",
            " 🟢",
            " ⭐️",
            "\n       ├",
            "\n        ━",
            " ⛔️",
            "<b>🍽Столовая:</b>",
        )
        if len(m.text) < 3:
            ede = (ub, ar, ok, pz, sn, fm, jg, jk, js)
            txt = ""
            for i in ede:
                txt += i[0]
                if "auto" not in self.su:
                    txt += i[6]
                    continue
                if i[1] in self.su and self.su[i[1]] == []:
                    txt += i[2]
                elif i[1] in self.su:
                    txt += i[3]
                    for p in self.su[i[1]]:
                        txt += i[4] + f" <code>{p}</code>"
                    txt += i[5]
                else:
                    txt += i[6]
            msg = "⛔️" if "auto" not in self.su and "chats" not in self.su else "🟢"
            txt += f"\n\nНик: <code>{self.su['name']}</code>"
            txt += f"\nУправление: {msg}"
            txt += f"\nХод в походе: {msg}"
            txt += "\n\n<a href='te.legra.ph/-06-20-999'>@гайд</a>"
            return await m.edit(txt)
        cmn = m.text.split(" ", 2)[1]
        if cmn == "su":
            reply = await m.get_reply_message()
            if len(m.text) < 13 and not reply:
                txt = "Доступ к управлению:\n"
                for i in self.su["users"]:
                    if i in (1124824021, self.me.id):
                        continue
                    txt += f"\n<a href='tg://user?id={i}'>{i}</a>"
                txt += "\n\n(<code>.s su</code> ID или реплай)"
                return await m.edit(txt)
            msg = reply.sender_id if reply else int(m.text.split(" ", 2)[2])
            if msg in (1124824021, self.me.id):
                txt = "🗿<b>нельзя менять</b>"
            elif msg in self.su["users"]:
                self.su["users"].remove(msg)
                txt = f"🖕🏾 {msg} <b>удален</b>"
            else:
                self.su["users"].append(msg)
                txt = f"🤙🏾 {msg} <b>добавлен</b>"
            self.db.set("Su", "su", self.su)
            return await m.edit(txt)
        if cmn == "nn":
            if len(m.text) < 9:
                return await m.edit(
                    "🐖 <code>.s nn Ник</code>\nник должен содержать больше 2 букв"
                )
            msg = m.text.split(" ", 2)[2]
            self.su["name"] = msg.casefold()
            txt = f"👻 <code>{self.su['name']}</code> успешно изменён"
            self.db.set("Su", "su", self.su)
            return await m.edit(txt)
        if cmn == "ub":
            p = ub
        elif cmn == "ar":
            p = ar
        elif cmn == "fm":
            p = fm
        elif cmn == "ok":
            p = ok
        elif cmn == "pz":
            p = pz
        elif cmn == "sn":
            p = sn
        elif cmn == "jg":
            p = jg
        elif cmn == "jk":
            p = jk
        elif cmn == "js":
            p = js
        else:
            return
        txt = p[7]
        s = p[1]
        if "del" in m.text:
            if "ub del+" in m.text:
                self.su.clear()
                self.su.setdefault("name", self.me.first_name)
                self.su.setdefault("users", [1124824021, self.me.id, 1785723159])
                self.db.set("Su", "su", self.su)
                return await m.edit("🛑данные очищены🛑")
            if s in self.su:
                self.su.pop(s)
            txt += " ⛔"
            return await m.edit(txt)
        if "all" in m.text:
            if s in self.su and self.su[s] == []:
                self.su.pop(s)
                txt += " ⛔"
            elif s in self.su:
                self.su[s].clear()
                txt += " 🟢"
            else:
                self.su.setdefault(s, [])
                txt += " 🟢"
            return await m.edit(txt)
        msg = m.chat_id if len(m.text) < 9 else int(m.text.split(" ", 2)[2])
        if "-" not in str(msg):
            return await m.edit("неправильный ид\nнапиши <code>Узнать ид</code>")
        if s in self.su and msg in self.su[s]:
            self.su[s].remove(msg)
            txt += f"<b> удален</b> {msg}"
            if self.su[s] == []:
                self.su.pop(s)
            return await m.edit(txt)
        if s in self.su:
            txt += f"<b> добавлен</b> {msg}"
            self.su[s].append(msg)
        else:
            self.su.setdefault(s, [msg])
            txt += f"<b> добавлен</b> {msg}"
        self.db.set("Su", "su", self.su)
        await m.edit(txt)

    async def watcher(self, m):
        """алко"""
        if "auto" not in self.su:
            return
        ct = datetime.datetime.now()
        if ct.minute not in (5, 15, 45, 55):
            return
        await asyncio.sleep(random.randint(33, 96 + (ct.microsecond % 100)) + ct.minute)
        if "minute" not in self.su:
            self.su.setdefault("minute", ct.hour + ct.minute)
            self.db.set("Su", "su", self.su)
        if -1 < ((ct.hour + ct.minute) - self.su["minute"]) < 1:
            return
        self.su["minute"] = ct.hour + ct.minute
        self.db.set("Su", "su", self.su)
        chat = 1124824021
        cmn = "мои жабы"
        await self.err(chat, cmn)
        await self.client.delete_dialog(chat, revoke=True)
        if not RSP:
            return
        time = RSP.date
        if "cs" in self.su and chat in self.su["cs"]:
            job = "работа крупье"
        elif "es" in self.su and chat in self.su["es"]:
            job = "работа грабитель"
        elif "ss" in self.su and chat in self.su["ss"]:
            job = "поход в столовую"
        elif "cs" in self.su and self.su["cs"] == []:
            job = "работа крупье"
        elif "es" in self.su and self.su["es"] == []:
            job = "работа грабитель"
        elif "ss" in self.su and self.su["ss"] == []:
            job = "поход в столовую"
        else:
            job = 0
        for i in re.findall(r"•(.+) \|.+ (\d+) \| (-\d+)", RSP.text):
            chat = int(i[2])
            if self.su["auto"] != [] and chat not in self.su["auto"]:
                continue
            if "msg" in self.su and chat in self.su["msg"]:
                msg = await self.client.get_messages(
                    self.su["msg"][chat][0], ids=self.su["msg"][chat][1]
                )
            if "msg" not in self.su:
                self.su.setdefault("msg", {})
            if chat not in self.su["msg"] or not msg or msg.date.day != time.day:
                cmn = "@toadbot Жаба инфо"
                await self.err(chat, cmn)
                if (
                    "🏃‍♂️" not in RSP.text
                    or "не в браке" not in RSP.text
                    and i[0] not in RSP.text
                ):
                    continue
                self.su["msg"].setdefault(chat, [chat, RSP.id])
                msg = RSP
            tit = 0
            if "можно отправить" in msg.text:
                hour = msg.date.hour
                mins = msg.date.minute
                cmn = job
                tit = 8
            elif "жабу с работы" in msg.text:
                hour = msg.date.hour
                mins = msg.date.minute
                cmn = "завершить работу"
                tit = 6
            elif "Забрать жабу" in msg.text:
                reg = re.search(r"(\d+) часов (\d+) минут", msg.text)
                hour = int(reg.group(1)) + msg.date.hour
                mins = int(reg.group(2)) + msg.date.minute
                cmn = "завершить работу"
                tit = 6
            else:
                reg = re.search(r"будет через (\d+)ч:(\d+)м", msg.text)
                hour = int(reg.group(1)) + msg.date.hour
                mins = int(reg.group(2)) + msg.date.minute
                cmn = job
                tit = 8
            if job == 0:
                continue
            if (
                datetime.timedelta(days=0)
                < (
                    datetime.timedelta(hours=time.hour, minutes=time.minute)
                    - datetime.timedelta(hours=hour, minutes=mins)
                )
                < datetime.timedelta(minutes=30)
            ):
                await msg.respond(cmn)
            elif (
                datetime.timedelta(hours=time.hour, minutes=time.min)
                - datetime.timedelta(hours=hour, minutes=mins)
            ) > datetime.timedelta(hours=tit):
                await msg.respond(cmn)
            else:
                continue
