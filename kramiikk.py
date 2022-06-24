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
            "жабу с работы": "@toadbot Завершить работу",
            "Можно откормить": "@toadbot Откормить жабу",
            "можно покормить": "@toadbot Покормить жабу",
            "Можно отправиться": "Отправиться в золотое подземелье",
            "жаба в данже": "Рейд старт",
            "Можно на арену!": "@toadbot На арену",
            "Используйте атаку": "@toadbot На арену",
            "можно отправить": "Работа крупье",
            "золото": "Отправиться в золотое подземелье",
            "кв": "Начать клановую войну",
            "напади": "Напасть на клан",
            "арена": "На арену",
            "реанимируй": "Реанимировать жабу",
            "карту": "Отправить карту",
            "снаряга": "Мое снаряжение",
            "инвентарь": "Мой инвентарь",
            "туса": "Жабу на тусу",
            "туси": "Начать тусу",
            "рейд": "Рейд старт",
            "работа": "Завершить работу",
            "минималист": "Выбрать усилитель минималист",
            "предел": "Выбрать усилитель на пределе",
            "родитель": "Выбрать усилитель Родитель года",
            "леденец": "Отдать леденец",
            "кулон": "Скрафтить кулон братвы",
            "лидерку": "Передать клан",
            "букахи": "Букашки",
            "аптеки": "Аптечки",
            "ледики": "Леденцы",
            "Ближний бой: Пусто": "скрафтить клюв цапли",
            "Дальний бой: Пусто": "скрафтить букашкомет",
            "Наголовник: Пусто": "скрафтить наголовник из клюва цапли",
            "Нагрудник: Пусто": "скрафтить нагрудник из клюва цапли",
            "Налапники: Пусто": "скрафтить налапники из клюва цапли",
            "Банда: Пусто": "взять жабу",
            "Покормить жабенка": "@toadbot Покормить жабенка",
            "Брак вознаграждение": "@toadbot Брак вознаграждение",
            "Забрать жабенка": "@toadbot Забрать жабенка",
            "В детский сад!": "@toadbot Отправить жабенка в детсад",
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

    async def npn(self, chat, msg):
        cmn = self.ded[msg]
        await self.err(chat, cmn)
        if not RSP:
            return
        if "Вы не участвуете" in RSP.text or "Ваша жаба на тусе" in RSP.text:
            return
        await asyncio.sleep(random.randint(9, 13))
        if "Ваша жаба в предсмертном" in RSP.text or "Для участия" in RSP.text:
            await RSP.respond("реанимировать жабу")
        elif "Ваша жаба на" in RSP.text:
            await RSP.respond("завершить работу")
        await asyncio.sleep(random.randint(9, 13))
        await self.client.send_message(chat, cmn)

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
        sn = (
            "\n\n    • Снаряжение:",
            "as",
            " 🟢",
            " ⭐️",
            "\n       ├",
            "\n        ━",
            " ⛔️",
            "<b>⚔️Снаряжение:</b>",
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
        ar = (
            "\n    • Арена:",
            "bs",
            " 🟢",
            " ⭐️",
            "\n       ├",
            "\n        ━",
            " ⛔️",
            "<b>🤺Арена:</b>",
        )
        js = (
            "\n\n    🍽Столовая:",
            "ss",
            " 🟢",
            " ⭐️",
            "\n       ├",
            "\n        ━",
            " ⛔️",
            "<b>🍽Столовая:</b>",
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
            "\n    💶Грабитель:",
            "es",
            " 🟢",
            " ⭐️",
            "\n       ├",
            "\n        ━",
            " ⛔️",
            "<b>💶Грабитель:</b>",
        )
        if len(m.text) < 3:
            ede = (ub, sn, pz, ok, fm, ar, js, jk, jg)
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
            txt += f"\n\nДоступ: {msg} <code>.s su</code>"
            txt += f"\nХод в походе: {msg}"
            txt += f"\nНик для команд: <code>{self.su['name']}</code>"
            txt += "\n\n<a href='te.legra.ph/-06-20-999'>@гайд</a>\n@jabuser"
            return await m.edit(txt)
        cmn = m.text.split(" ", 2)[1]
        if cmn == "su":
            reply = await m.get_reply_message()
            if len(m.text) < 13 and not reply:
                txt = "Доступ к управлению модулем:\n"
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
            if len(m.text) < 4:
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
        elif cmn == "sn":
            p = sn
        elif cmn == "pz":
            p = pz
        elif cmn == "ok":
            p = ok
        elif cmn == "fm":
            p = fm
        elif cmn == "ar":
            p = ar
        elif cmn == "js":
            p = js
        elif cmn == "jk":
            p = jk
        elif cmn == "jg":
            p = jg
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
        try:
            if "auto" not in self.su:
                return
            ct = datetime.datetime.now()
            n = (
                self.me.id % 100
                if (self.me.id % 100) < 48
                else int(self.me.id % 100 / 3)
            )
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
                    await asyncio.sleep(random.randint(3, n))
                    await m.click()
                elif "ход: " in m.text and m.buttons:
                    await m.click()
                elif "сломалось" in m.text and cn == 1:
                    cmn = "мое снаряжение"
                    await self.err(chat, cmn)
                    if not RSP and "🗡" not in RSP.text:
                        return
                    for i in (i for i in self.ded if i in RSP.text):
                        await asyncio.sleep(random.randint(3, n))
                        await m.respond(self.ded[i])
                elif "Банда получила" in m.text and cn == 1:
                    await m.respond("отдать леденец")
                    await asyncio.sleep(random.randint(3, n))
                    cmn = "моя банда"
                    await self.err(chat, cmn)
                    if not RSP and "📿" not in RSP.text:
                        return
                    if "Кулон: Пусто" in RSP.text:
                        await asyncio.sleep(random.randint(3, n))
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
                        if msg in ("напади", "арена"):
                            return await self.npn(chat, msg)
                        return await self.client.send_message(chat, self.ded[msg])
                    await self.client.send_message(chat, msg)
                elif "напиши " in m.text:
                    txt = m.text.split(" ", 2)[2]
                    if reply:
                        return await reply.reply(txt)
                    await m.respond(txt)
                else:
                    cmn = m.text.split(" ", 2)[1]
                    if reply and cmn in ("ледики", "аптеки", "букахи"):
                        return await reply.reply(
                            f"отправить {self.ded[cmn]} {m.text.split(' ', 2)[2]}"
                        )
                    msg = m.text.split(" ", 2)[1]
                    if msg not in self.ded:
                        return
                    if msg in ("напади", "арена"):
                        return await self.npn(chat, msg)
                    if msg in ("карту", "лидерку"):
                        return await m.reply(self.ded[msg])
                    await asyncio.sleep(random.randint(3, n) + ct.minute)
                    await m.respond(self.ded[msg])
            if ct.minute != n:
                return
            await asyncio.sleep(
                random.randint(n, 96 + (ct.microsecond % 100)) + ct.minute
            )
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
                    random.randint(n + ct.hour, 96 + (ct.microsecond % 100)) + ct.minute
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
                elif "ss" in self.su and chat in self.su["ss"]:
                    job = "поход в столовую"
                elif "es" in self.su and chat in self.su["es"]:
                    job = "работа грабитель"
                elif "cs" in self.su and self.su["cs"] == []:
                    job = "работа крупье"
                elif "ss" in self.su and self.su["ss"] == []:
                    job = "поход в столовую"
                elif "es" in self.su and self.su["es"] == []:
                    job = "работа грабитель"
                else:
                    job = 0
                try:
                    cmn = "Моя жаба"
                    await self.err(chat, cmn)
                except Exception:
                    pass
                if (
                    "Имя жабы" not in RSP.text
                    and i[0] not in RSP.text
                    and i[1] not in RSP.text
                ):
                    continue
                s = 0
                if "Нужна реанимация" in RSP.text:
                    s = 1
                if "Хорошее" in RSP.text:
                    await asyncio.sleep(
                        random.randint(n, 96 + (ct.microsecond % 100)) + ct.minute
                    )
                    await RSP.respond(f"использовать леденцы {random.randint(1, 3)}")
                jab = re.search(r"Б.+: (\d+)", RSP.text).group(1)
                if not jab:
                    continue
                await asyncio.sleep(random.randint(3, n) + ct.minute)
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
                    await asyncio.sleep(random.randint(3, n) + ct.minute)
                    await RSP.respond("реанимировать жабу")
                if "подземелье можно через 2" in RSP.text:
                    pz = 0
                if "не в браке" in RSP.text:
                    fm = 0
                for p in (p for p in self.ded if p in RSP.text):
                    await asyncio.sleep(random.randint(3, n) + ct.minute)
                    if p == "Можно откормить" and ok == 0:
                        pass
                    elif p == "можно покормить" and ok == 1:
                        pass
                    elif p == "Можно отправиться" and pz == 0:
                        pass
                    elif p == "Можно на арену!" and ar == 0:
                        pass
                    elif p in ("Можно на арену!", "Используйте атаку"):
                        if ct.minute < 48:
                            await asyncio.sleep(random.randint(3, n) + ct.minute)
                            await RSP.respond(self.ded[p])
                        for n in range(3):
                            s += 13
                            i = random.randint(9, s)
                            await self.client.send_message(
                                chat,
                                "Реанимировать жабу",
                                schedule=datetime.timedelta(minutes=i),
                            )
                            await self.client.send_message(
                                chat,
                                self.ded[p],
                                schedule=datetime.timedelta(minutes=i + 1),
                            )
                    elif p == "можно отправить" and (job == 0 or pz == 1):
                        pass
                    elif p == "можно отправить" and pz == 0:
                        await RSP.respond(job)
                    else:
                        await RSP.respond(self.ded[p])
                if fm == 0:
                    continue
                await asyncio.sleep(random.randint(3, n) + ct.minute)
                cmn = "Моя семья"
                await self.err(chat, cmn)
                if (
                    "дней в браке" not in RSP.text
                    and i[0] not in RSP.text
                    and not RSP.buttons
                ):
                    continue
                s = len(RSP.buttons)
                await asyncio.sleep(random.randint(3, n) + ct.minute)
                await RSP.respond(self.ded[RSP.buttons[0][0].text])
                if s == 1:
                    continue
                await asyncio.sleep(random.randint(3, n) + ct.minute)
                await RSP.respond(self.ded[RSP.buttons[1][0].text])
                if s == 2:
                    continue
                await asyncio.sleep(random.randint(3, n) + ct.minute)
                await RSP.respond(self.ded[RSP.buttons[2][0].text])
        except Exception:
            return
