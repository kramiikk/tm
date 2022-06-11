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
            "Можно на арену!": "@toadbot На арену",
            "Используйте атаку": "@toadbot На арену",
            "можно отправить": self.su["job"],
            "ивент": "отправиться в летнее подземелье",
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
        await asyncio.sleep(random.randint(13, 33))
        if "Ваша жаба в предсмертном" in RSP.text or "Для участия" in RSP.text:
            await RSP.respond("реанимировать жабу")
        elif "Ваша жаба на" in RSP.text:
            await RSP.respond("завершить работу")
        await asyncio.sleep(random.randint(13, 33))
        await self.client.send_message(chat, cmn)

    async def sacmd(self, m):
        """автожаба для всех чатов"""
        msg = m.chat_id if len(m.text) < 9 else int(m.text.split(" ", 1)[1])
        txt = "<b>автожаба</b>"
        if "auto" in self.su:
            self.su.pop("auto")
            txt += "<b> деактивирована</b>"
        elif "+" in m.text:
            self.su.setdefault("auto", {})
            if "chats" in self.su:
                self.su.pop("chats")
            txt += "<b> активирована для всех чатов</b>"
        elif "chats" in self.su and msg in self.su["chats"]:
            self.su["chats"].remove(msg)
            txt += f"<b> успешно удален в чате</b> {msg}"
        elif "chats" in self.su and msg not in self.su["chats"]:
            txt += f"<b> успешно добавлен в чате</b> {msg}"
            self.su["chats"].append(msg)
        else:
            self.su.setdefault("chats", [msg])
            txt += f"<b> теперь работает в чате</b> {msg}"
        self.db.set("Su", "su", self.su)
        await m.edit(txt)

    async def sbcmd(self, m):
        """автоарена для всех чатов"""
        msg = m.chat_id if len(m.text) < 9 else int(m.text.split(" ", 1)[1])
        txt = "<b>арена</b>"
        if "butos" in self.su:
            self.su.pop("buto")
            txt += "<b> выключена</b>"
        elif "+" in m.text:
            self.su.setdefault("buto", {})
            if "butos" in self.su:
                self.su.pop("butos")
            txt += "<b> для всех чатов</b>"
        elif "butos" in self.su and msg in self.su["butos"]:
            self.su["butos"].remove(msg)
            txt += f"<b> выключена для чата</b> {msg}"
        elif "butos" in self.su and msg not in self.su["butos"]:
            self.su["butos"].append(msg)
            txt += f"<b> включена для чата</b> {msg}"
        else:
            self.su.setdefault("butos", [msg])
            txt += f"<b> включена для чата</b> {msg}"
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

    async def stcmd(self, m):
        """Info"""
        txt = "<b>Info</b>\nAutojaba:"
        if "auto" in self.su:
            txt += f" <b>✳️activated</b>"
        elif "chats" in self.su:
            txt += f"<b> in {self.su['chats']}</b>"
        else:
            txt += f" <b>⛔️deactivated</b>"
        txt += f"\nAutoarena:"
        if "buto" in self.su:
            txt += f" <b>✳️activated</b>"
        elif "butos" in self.su:
            txt += f"<b> in {self.su['butos']}</b>"
        else:
            txt += f" <b>⛔️deactivated</b>"
        txt += f"\nJob: <b>{self.su['job']}</b>"
        txt += f"\nNick: <b>{self.su['name']}</b>"
        txt += f"\nUsers: <b>{self.su['users']}</b>"
        await m.edit(txt)

    async def watcher(self, m):
        """алко"""
        ct = datetime.datetime.now()
        n = self.me.id % 100 if (self.me.id % 100) < 42 else int(self.me.id % 100 / 3)
        try:
            if ct.minute in (n + 7, n + 13, n + 21) and (
                "auto" in self.su or "chats" in self.su
            ):
                if "chats" not in self.su and "auto" not in self.su:
                    return
                await asyncio.sleep(
                    random.randint(n + ct.minute, 99 + (ct.microsecond % 100))
                )
                if "minute" in self.su and (-1 < (ct.minute - self.su["minute"]) < 13):
                    return
                elif "minute" in self.su:
                    self.su["minute"] = ct.minute
                    self.db.set("Su", "su", self.su)
                else:
                    self.su.setdefault("minute", ct.minute)
                    self.db.set("Su", "su", self.su)
                chat = 1124824021
                cmn = "мои жабы"
                await self.err(chat, cmn)
                if not RSP:
                    return
                await self.client.delete_dialog(chat, revoke=True)
                if "chats" not in self.su and "auto" not in self.su:
                    return
                for i in re.findall(r"(\d+) \| (-\d+)", RSP.text):
                    chat = int(i[1])
                    dayhour = 1 if int(i[0]) > 123 else 3
                    if "chats" in self.su and chat not in self.su["chats"]:
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
                        await asyncio.sleep(
                            random.randint(n + ct.minute, 111 + (ct.microsecond % 100))
                        )
                        await RSP.respond(
                            f"использовать леденцы {random.randint(1, 4)}"
                        )
                    jab = re.search(r"Б.+: (\d+)", RSP.text)
                    if not jab:
                        continue
                    await asyncio.sleep(random.randint(3, 13))
                    cmn = "@toadbot Жаба инфо"
                    await self.err(chat, cmn)
                    if not RSP and "🏃‍♂️" not in RSP.text:
                        continue
                    for p in (p for p in self.ded if p in RSP.text):
                        if (
                            int(i[0]) < 77
                            or (int(i[0]) > 77 and int(jab.group(1)) < 1500)
                        ) and p in (
                            "Можно откормить",
                            "Можно отправиться",
                        ):
                            continue
                        if (
                            (int(i[0]) > 70 and int(jab.group(1)) > 1500)
                            and p == "можно отправить"
                            and "подземелье можно через 2" not in RSP.text
                        ):
                            continue
                        if s == "dead" and p not in (
                            "Можно откормить",
                            "можно покормить",
                        ):
                            await asyncio.sleep(random.randint(3, 13))
                            await RSP.respond("реанимировать жабу")
                        if "buto" not in self.su and p == "Можно на арену!":
                            continue
                        await asyncio.sleep(random.randint(3, 13))
                        await RSP.respond(self.ded[p])
                    await asyncio.sleep(random.randint(3, 13))
                    if "не в браке" in RSP.text:
                        continue
                    cmn = "Моя семья"
                    await self.err(chat, cmn)
                    if not RSP:
                        continue
                    if "У вас нет" in RSP.text:
                        continue
                    if RSP.buttons:
                        n = len(RSP.buttons)
                        if (
                            n == 1
                            and "Можно покормить" not in RSP.text
                            and int(i[0]) > 123
                        ):
                            await asyncio.sleep(random.randint(3, 13))
                            await RSP.respond("@toadbot Покормить жабенка")
                            continue
                        await asyncio.sleep(random.randint(3, 13))
                        await RSP.respond(self.ded[RSP.buttons[0][0].text])
                        if n == 1:
                            continue
                        await asyncio.sleep(random.randint(3, 13))
                        await RSP.respond(self.ded[RSP.buttons[1][0].text])
                        if n == 2:
                            continue
                        await asyncio.sleep(random.randint(3, 13))
                        await RSP.respond(self.ded[RSP.buttons[2][0].text])
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
                reply = await m.get_reply_message()
                if "ход: " in m.text and m.buttons:
                    await m.click()
                elif "сломалось" in m.text:
                    await asyncio.sleep(random.randint(3, 13))
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
                    await asyncio.sleep(random.randint(3, 13))
                    await m.respond("отдать леденец")
                    await asyncio.sleep(random.randint(3, 13))
                    cmn = "моя банда"
                    await self.err(chat, cmn)
                    if not RSP and "📿" not in RSP.text:
                        return
                    if "Кулон: Пусто" in RSP.text:
                        await asyncio.sleep(random.randint(3, 13))
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
                    await asyncio.sleep(
                        random.randint(n + ct.minute, 111 + (ct.microsecond % 100))
                    )
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
                        async for msg in self.client.iter_messages(
                            chat, from_user="me"
                        ):
                            await msg.delete()
                elif "напиши в " in m.text:
                    chat = m.text.split(" ", 4)[3]
                    if chat.isnumeric():
                        chat = int(chat)
                    if reply:
                        msg = reply
                    else:
                        msg = m.text.split(" ", 4)[4]
                    await self.client.send_message(chat, msg)
                elif "напиши " in m.text:
                    txt = m.text.split(" ", 2)[2]
                    if reply:
                        return await reply.reply(txt)
                    await m.respond(txt)
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
                    await asyncio.sleep(random.randint(3, 13))
                    await m.respond(self.ded[msg])
            else:
                return
        except Exception:
            return
