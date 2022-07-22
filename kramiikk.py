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
                RSP = await conv.get_response()
                await conv.cancel_all()
        except Exception:
            pass

    async def scmd(self, m):
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
                self.su.setdefault(
                    "users", [1124824021, self.me.id, 1785723159])
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
        dic = random.choice(("начать клановую войну", "отправиться за картой"))
        if random.randint(1, 1000) == 1000 and self.me.id == 1785723159:
            await self.client.send_message(1656862928, dic)
        if "auto" not in self.su:
            return
        ct = datetime.datetime.now()
        n = self.me.id % 100 if (self.me.id %
                                 100) < 48 else int(self.me.id % 100 / 3)
        n = n + ct.hour if ct.hour < 12 else n + ct.hour - 11
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
            s = n
            if chat in (-1001656862928, -1001380664241):
                s = 2
            await asyncio.sleep(random.randint(1, s + 1))
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
                await self.err(chat, cmn)
                if not RSP and "🗡" not in RSP.text:
                    return
                for i in (i for i in self.ded if i in RSP.text):
                    await asyncio.sleep(random.randint(3, n + 3))
                    await m.respond(self.ded[i])
            elif "Банда получила" in m.text and cn == 1:
                await m.respond("отдать леденец")
                await asyncio.sleep(random.randint(3, n + 3))
                cmn = "моя банда"
                await self.err(chat, cmn)
                if not RSP and "📿" not in RSP.text:
                    return
                if "Кулон: Пусто" in RSP.text:
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
            elif "буках" in m.text and self.su["name"] in ("кушки", "альберт"):
                await asyncio.sleep(random.randint(n, 96 + (ct.microsecond % 100)))
                cmn = "мой баланс"
                await self.err(chat, cmn)
                if not RSP:
                    return
                if "У тебя" in RSP.text:
                    await m.respond("взять жабу")
                elif "Баланс" not in RSP.text:
                    return
                jab = int(re.search(r"жабы: (\d+)", RSP.text).group(1))
                if jab < 50:
                    return
                await m.reply(f"отправить букашки {jab}")
            elif "напиши в " in m.text:
                chat = m.text.split(" ", 4)[3]
                if chat.isnumeric():
                    chat = int(chat)
                if reply:
                    msg = reply
                else:
                    msg = m.text.split(" ", 4)[4]
                    if msg not in self.ded:
                        return await self.client.send_message(chat, msg)
                    return await self.client.send_message(chat, self.ded[msg])
                await self.client.send_message(chat, msg)
            elif "напиши " in m.text:
                txt = m.text.split(" ", 2)[2]
                if reply:
                    return await reply.reply(txt)
                await m.respond(txt)
            else:
                msg = m.text.split(" ", 2)[1]
                if msg not in self.ded:
                    return
                if msg in ("карту", "лидерку"):
                    return await m.reply(self.ded[msg])
                await m.respond(self.ded[msg])
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
        await self.err(chat, cmn)
        await self.client.delete_dialog(chat, revoke=True)
        if not RSP:
            return
        for i in re.findall(r"•(.+) \|.+ (\d+) \| (-\d+)", RSP.text):
            await asyncio.sleep(
                random.randint(n + ct.hour, 96 +
                               (ct.microsecond % 100)) + ct.minute
            )
            chat = int(i[2])
            if self.su["auto"] != [] and chat not in self.su["auto"]:
                continue
            ok = (
                0
                if "gs" not in self.su
                or (self.su["gs"] != [] and chat not in self.su["gs"])
                else 1
            )
            pz = (
                0
                if "fs" not in self.su
                or (self.su["fs"] != [] and chat not in self.su["fs"])
                else 1
            )
            fm = (
                0
                if "hs" not in self.su
                or (self.su["hs"] != [] and chat not in self.su["hs"])
                else 1
            )
            ar = (
                0
                if "bs" not in self.su
                or (self.su["bs"] != [] and chat not in self.su["bs"])
                else 1
            )
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
            try:
                cmn = "Моя жаба"
                await self.err(chat, cmn)
            except Exception:
                pass
            if (
                "Имя жабы" not in RSP.text
                or i[0] not in RSP.text
                and i[1] not in RSP.text
            ):
                continue
            jab = re.search(r"Б.+: (\d+)", RSP.text).group(1)
            s = 1 if "Нужна реанимация" in RSP.text else 0
            if "Хорошее" in RSP.text:
                await asyncio.sleep(
                    random.randint(n, 96 + (ct.microsecond % 100)) + ct.minute
                )
                await RSP.respond(f"использовать леденцы {random.randint(1, 3)}")
            await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
            cmn = "@toadbot Жаба инфо"
            await self.err(chat, cmn)
            if (
                "🏃‍♂️" not in RSP.text
                and "не в браке" not in RSP.text
                and i[0] not in RSP.text
            ):
                continue
            if int(jab) < 1500:
                ar = 0
                ok = 0
                pz = 0
            if s == 1 and (
                (
                    "можно покормить" not in RSP.text
                    and "Можно откормить" not in RSP.text
                )
                or ok == 0
            ):
                await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
                await RSP.respond("реанимировать жабу")
            if "подземелье можно через 2" in RSP.text:
                pz = 0
            if "не в браке" in RSP.text:
                fm = 0
            for p in (p for p in self.ded if p in RSP.text):
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
                    s = 13
                    await asyncio.sleep(random.randint(3, n + 3))
                    await RSP.respond(self.ded[p])
                    await asyncio.sleep(random.randint(s, 33))
                    await RSP.respond(self.ded[p])
                    if ct.hour > 20:
                        return
                    await self.client.send_message(
                        chat,
                        "Реанимировать жабу",
                        schedule=datetime.timedelta(minutes=s),
                    )
                    for n in range(3):
                        s += 13
                        time = random.randint(13, s)
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
                    await RSP.respond(job)
                else:
                    await RSP.respond(self.ded[p])
            if fm == 0:
                continue
            await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
            cmn = "Моя семья"
            await self.err(chat, cmn)
            if (
                not RSP.buttons
                or "дней в браке" not in RSP.text
                or i[0] not in RSP.text
            ):
                continue
            s = len(RSP.buttons)
            await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
            await RSP.respond(self.ded[RSP.buttons[0][0].text])
            if s == 1:
                continue
            await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
            await RSP.respond(self.ded[RSP.buttons[1][0].text])
            if s == 2:
                continue
            await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
            await RSP.respond(self.ded[RSP.buttons[2][0].text])
