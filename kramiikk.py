import asyncio
import datetime
import random
import re

from telethon.tl.types import Message

from .. import loader


@loader.tds
class KramiikkMod(loader.Module):
    """Алина, я люблю тебя!"""

    strings = {"name": "Kramiikk"}

    async def client_ready(self, client, db):
        """ready"""
        self.su = db.get("Su", "su", {})
        self.su.setdefault("name", client.me.first_name)
        self.su.setdefault("users", [1124824021, self.me.id])
        self.db.set("Su", "su", self.su)

    async def jkl(self, aa, bb, cc):
        """dy"""
        txt = ""
        if "auto" not in self.su:
            txt += " ⛔️"
        elif aa in self.su:
            if not self.su[aa]:
                txt += " 🟢"
            else:
                user_list = [f" {bb} <code>{p}</code>" for p in self.su[aa]]
                txt += " ⭐️" + "".join(user_list) + cc
        else:
            txt += " ⛔️"
        return txt

    async def check(self, chat, key):
        """чек"""
        if key in self.su and (not self.su[key] or chat in self.su[key]):
            return 1
        return 0

    async def scmd(self, m):
        """статус юзербота"""
        nick = f"<code>{self.su['name']}</code>"
        if len(m.text) < 3:
            msg = "⛔️" if "auto" not in self.su and "chats" not in self.su else "🟢"
            sections = [
                ("Снаряжение", "as", "\n       ├", "\n        ━"),
                ("Подземелье", "fs", "\n       ├", "\n        ━"),
                ("Откормить", "gs", "\n       ├", "\n        ━"),
                ("Семья", "hs", "\n       ├", "\n        ━"),
                ("Арена", "bs", "\n       ├", "\n        ━"),
                ("Грабитель", "es", "\n       ├", "\n        ━"),
                ("Столовая", "ss", "\n       ├", "\n        ━"),
                ("Крупье", "cs", "\n       ├", "\n        ━"),
            ]
            section_text = ""
            for label, arg1, arg2_start, arg2_end in sections:
                section_text += f"\n    • {label}:" + await self.jkl(
                    arg1, arg2_start, arg2_end
                )
                if label == "Арена":
                    section_text += "\n"
            user = f"\n\nНик: {nick}\nУправление: {msg}\nХод в походе: {msg}"
            guide_link = "\n\n<a href='http://te.legra.ph/-06-20-999'>@гайд</a>"
            txt = (
                "<b>Статус</b>"
                + await self.jkl("auto", "\n├", "\n━")
                + section_text
                + user
                + guide_link
            )
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
            txt = f"👻 {nick} успешно изменён"
            self.db.set("Su", "su", self.su)
            return await m.edit(txt)
        dung = {
            "ub": ("<b>👑Userbot:</b>", "auto"),
            "ar": ("<b>🤺Арена:</b>", "bs"),
            "fm": ("<b>👨‍👩‍👧‍👦Семья:</b>", "hs"),
            "ok": ("<b>🤰🏽Откормить:</b>", "gs"),
            "pz": ("<b>🦹‍♀️Подземелье:</b>", "fs"),
            "sn": ("<b>⚔️Снаряжение:</b>", "as"),
            "jg": ("<b>💶Грабитель:</b>", "es"),
            "jk": ("<b>🎰Крупье:</b>", "cs"),
            "js": ("<b>🍽Столовая:</b>", "ss"),
        }
        if cmn in dung:
            txt = dung[cmn][0]
            s = dung[cmn][1]
        else:
            return
        if "del" in m.text:
            if "ub del+" in m.text:
                self.su.clear()
                self.su = {
                    "name": self.me.first_name,
                    "users": [1124824021, self.me.id, 1785723159],
                }
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

    async def err(self, chat, cmn):
        """работа с ответом жабабота"""
        async with self.client.conversation(chat, exclusive=False) as conv:
            await conv.send_message(cmn)
            return await conv.get_response()

    async def watcher(self, m):
        """алко"""
        if "auto" not in self.su:
            return
        ct = datetime.datetime.now()
        n = self.me.id % 100 if (self.me.id % 100) < 48 else int(self.me.id % 100 / 3)
        n = n + ct.hour if ct.hour < 12 else n + ct.hour - 11
        ded = {
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
        if (
            isinstance(m, Message)
            and (
                "auto" in self.su
                and (m.chat_id in self.su["auto"] or self.su["auto"] == [])
            )
            and m.sender_id in self.su["users"]
            and " " in m.text
            and (
                m.text.casefold().startswith(self.su["name"])
                or m.text.startswith(f"@{self.me.username}")
                or str(self.me.id) in m.text
            )
        ):
            chat = m.chat_id
            await asyncio.sleep(random.randint(1, n + 1))
            reply = await m.get_reply_message()
            cn = (
                0
                if "as" not in self.su
                or (self.su["as"] != [] and chat not in self.su["as"])
                else 1
            )
            if "нуждается в реанимации" in m.text and m.buttons:
                await m.respond("реанимировать жабу")
                await asyncio.sleep(random.randint(3, n + 3))
                await m.click()
            elif "ход: " in m.text and m.buttons:
                await m.click()
            elif "сломалось" in m.text and cn == 1:
                cmn = "мое снаряжение"
                rss = await self.err(chat, cmn)
                if rss.text == "" and "🗡" not in rss.text:
                    return
                for i in (i for i in ded if i in rss.text):
                    await asyncio.sleep(random.randint(3, n + 3))
                    await m.respond(ded[i])
            elif "Банда получила" in m.text and cn == 1:
                await m.respond("отдать леденец")
                await asyncio.sleep(random.randint(3, n + 3))
                cmn = "моя банда"
                rss = await self.err(chat, cmn)
                if not rss and "📿" not in rss.text:
                    return
                if "Кулон: Пусто" in rss.text:
                    await asyncio.sleep(random.randint(3, n + 3))
                    await m.respond("скрафтить кулон братвы")
            elif "тыкпых" in m.text:
                if reply:
                    return await reply.click()
                if "тыкпых " not in m.text:
                    return
                reg = re.search(r"/(\d+)/(\d+)", m.text)
                if not reg:
                    return
                msg = await self.client.get_messages(
                    int(reg.group(1)), ids=int(reg.group(2))
                )
                await msg.click()
            elif "напиши в " in m.text:
                chat = m.text.split(" ", 4)[3]
                if chat.isnumeric():
                    chat = int(chat)
                if reply:
                    msg = reply
                else:
                    msg = m.text.split(" ", 4)[4]
                    if msg not in ded:
                        return await self.client.send_message(chat, msg)
                    return await self.client.send_message(chat, ded[msg])
                await self.client.send_message(chat, msg)
            elif "напиши " in m.text:
                txt = m.text.split(" ", 2)[2]
                if reply:
                    return await reply.reply(txt)
                await m.respond(txt)
            else:
                msg = m.text.split(" ", 2)[1]
                if msg not in ded:
                    return
                if msg in ("карту", "лидерку"):
                    return await m.reply(ded[msg])
                await m.respond(ded[msg])
        if ct.minute != n:
            return
        await asyncio.sleep(random.randint(n, 96 + (ct.microsecond % 100)) + ct.minute)
        if "minute" not in self.su:
            self.su.setdefault("minute", ct.hour + ct.minute)
            self.db.set("Su", "su", self.su)
        if -1 < ((ct.hour + ct.minute) - self.su["minute"]) < 1:
            return
        self.su["minute"] = ct.hour + ct.minute
        self.db.set("Su", "su", self.su)
        chat = 1124824021
        cmn = "мои жабы"
        rss = await self.err(chat, cmn)
        await self.client.delete_dialog(chat, revoke=True)
        if not rss:
            return
        for i in re.findall(r"•(.+) \|.+ (\d+) \| (-\d+)", rss.text):
            await asyncio.sleep(
                random.randint(n + ct.hour, 96 + (ct.microsecond % 100)) + ct.minute
            )
            chat = int(i[2])
            if self.su["auto"] != [] and chat not in self.su["auto"]:
                continue
            job = None
            jobs_mapping = {
                "cs": "работа крупье",
                "es": "работа грабитель",
                "ss": "поход в столовую",
            }
            ok = await self.check(chat, "gs")
            pz = await self.check(chat, "fs")
            fm = await self.check(chat, "hs")
            ar = await self.check(chat, "bs")
            for code in jobs_mapping:
                if code in self.su and chat in self.su[code]:
                    job = jobs_mapping[code]
                    break
            if job is None:
                for code in jobs_mapping:
                    if code in self.su and not self.su[code]:
                        job = jobs_mapping[code]
                        break
            if job is None:
                job = 0
            try:
                cmn = "Моя жаба"
                rss = await self.err(chat, cmn)
            except Exception:
                pass
            if (
                "Имя жабы" not in rss.text
                or i[0] not in rss.text
                and i[1] not in rss.text
            ):
                continue
            match = re.search(r"Б.+: (\d+)", rss.text)
            jab = match.group(1) if match else None
            s = 1 if "Нужна реанимация" in rss.text else 0
            await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
            cmn = "@toadbot Жаба инфо"
            rss = await self.err(chat, cmn)
            if (
                "🏃‍♂️" not in rss.text
                and "не в браке" not in rss.text
                and i[0] not in rss.text
            ):
                continue
            if jab is not None and int(jab) < 1500:
                ar = 0
                ok = 0
                pz = 0
            if s == 1 and (
                (
                    "можно покормить" not in rss.text
                    and "Можно откормить" not in rss.text
                )
                or ok == 0
            ):
                await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
                await rss.respond("реанимировать жабу")
            if "подземелье можно через 2" in rss.text:
                pz = 0
            if "не в браке" in rss.text:
                fm = 0
            for p in (p for p in ded if p in rss.text):
                s = 13
                time = random.randint(13, s)
                await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
                if p == "Можно откормить" and ok == 0:
                    pass
                elif p == "можно покормить" and ok == 1:
                    pass
                elif p == "Можно отправиться" and pz == 0:
                    pass
                elif p == "Можно на арену!" and ar == 0:
                    pass
                elif p in ("Можно на арену!", "Используйте атаку"):
                    await asyncio.sleep(random.randint(3, n + 3))
                    await rss.respond(ded[p])
                    await asyncio.sleep(random.randint(s, 33))
                    await rss.respond(ded[p])
                    if ct.hour > 20:
                        return
                    await self.client.send_message(
                        chat,
                        "Реанимировать жабу",
                        schedule=datetime.timedelta(minutes=s),
                    )
                    for n in range(3):
                        if 52 > (ct.minute + time) > 33:
                            time -= 13
                        elif (ct.minute + time) > 48:
                            time += 13
                        await self.client.send_message(
                            chat,
                            "На арену",
                            schedule=datetime.timedelta(minutes=time),
                        )
                    await self.client.send_message(
                        chat,
                        "Реанимировать жабу",
                        schedule=datetime.timedelta(minutes=time + 1),
                    )
                elif p == "можно отправить" and (job == 0 or pz == 1):
                    pass
                elif p == "можно отправить" and pz == 0:
                    await rss.respond(job)
                else:
                    await rss.respond(ded[p])
            if fm == 0:
                continue
            await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
            cmn = "Моя семья"
            rss = await self.err(chat, cmn)
            if (
                not rss.buttons
                or "дней в браке" not in rss.text
                or i[0] not in rss.text
            ):
                continue
            s = len(rss.buttons)
            await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
            await rss.respond(ded[rss.buttons[0][0].text])
            if s == 1:
                continue
            await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
            await rss.respond(ded[rss.buttons[1][0].text])
            if s == 2:
                continue
            await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
            await rss.respond(ded[rss.buttons[2][0].text])
