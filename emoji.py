import asyncio
import random
import re
from datetime import timedelta

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
            "минималист": "выбрать усилитель мминималист",
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
        except:
            return

    async def npn(self, chat, msg):
        await self.snr(chat)
        await asyncio.sleep(3)
        cmn = self.ded[msg]
        await self.err(chat, cmn)
        if not RSP:
            return
        if "Вы не участвуете" in RSP.text or "Ваша жаба на тусе" in RSP.text:
            return
        await asyncio.sleep(random.randint(3, 13))
        if "Ваша жаба в предсмертном" in RSP.text or "Для участия" in RSP.text:
            await RSP.respond("реанимировать жабу")
        elif "Ваша жаба на" in RSP.text:
            await RSP.respond("завершить работу")
        for i in range(3):
            await asyncio.sleep(random.randint(13, 33))
            await self.client.send_message(chat, cmn)

    async def snr(self, chat):
        cmn = "@toadbot Мое снаряжение"
        await self.err(chat, cmn)
        if not RSP and "🗡" not in RSP.text:
            return
        await asyncio.sleep(random.randint(3, 13))
        for p in (p for p in self.ded if p in RSP.text):
            await RSP.respond(self.ded[p])

    async def sacmd(self, message: Message):
        """автожаба для всех чатов"""
        if "auto" in self.su:
            self.su.pop("auto")
            msg = "<b>деактивирована</b>"
        else:
            self.su.setdefault("auto", {})
            if "chats" in self.su:
                self.su.pop("chats")
            msg = "<b>активирована</b>"
        self.db.set("Su", "su", self.su)
        await message.edit(msg)

    async def sjcmd(self, message: Message):
        """выбор работы"""
        msg = message.text.split(" ", 1)[1]
        self.su["job"] = msg.casefold()
        txt = f"<b>Работа изменена:</b> {self.su['job']}"
        self.db.set("Su", "su", self.su)
        await message.edit(txt)

    async def sncmd(self, message: Message):
        """ник для команд"""
        msg = message.text.split(" ", 1)[1]
        self.su["name"] = msg.casefold()
        txt = f"👻 <code>{self.su['name']}</code> <b>успешно изменён</b>"
        self.db.set("Su", "su", self.su)
        await message.edit(txt)

    async def sucmd(self, message: Message):
        """добавляет пользователей для управление"""
        reply = await message.get_reply_message()
        msg = reply.from_id if reply else int(message.text.split(" ", 1)[1])
        if msg in self.su["users"]:
            self.su["users"].remove(msg)
            txt = f"🖕🏾 {msg} <b>успешно удален</b>"
        else:
            self.su["users"].append(msg)
            txt = f"🤙🏾 {msg} <b>успешно добавлен</b>"
        self.db.set("Su", "su", self.su)
        await message.edit(txt)

    async def svcmd(self, message: Message):
        """автожаба для выбранного чата"""
        msg = (
            message.chat_id
            if len(message.text) < 9
            else int(message.text.split(" ", 1)[1])
        )
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
        await message.edit(txt)

    async def watcher(self, message: Message):
        """алко"""
        if not isinstance(message, Message) or message.from_id not in self.su["users"]:
            return
        chat = message.peer_id
        if message.text.startswith("💑👩‍❤️‍👨👨‍❤️‍👨💑"):
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
                if "chats" in self.su and chat not in self.su["chats"]:
                    continue
                if "dayhour" in self.su:
                    msg = await self.client.get_messages(
                        "me", ids=int(self.su["dayhour"])
                    )
                    if msg:
                        reg = re.search(rf"{chat} (\d+) (\d+)", msg.text)
                        if reg:
                            day = reg.group(1)
                            hur = reg.group(2)
                            dayhour = 2
                            if int(i[0]) < 123:
                                dayhour = 4
                            ts = timedelta(
                                days=message.date.day, hours=message.date.hour
                            ) - timedelta(days=int(day), hours=int(hur))
                            if (
                                timedelta(days=0, hours=0)
                                <= ts
                                < timedelta(days=0, hours=dayhour)
                            ):
                                txt += f"\n{chat} {day} {hur}"
                                continue
                try:
                    cmn = "@toadbot Моя жаба"
                    await self.err(chat, cmn)
                except Exception:
                    continue
                if not RSP:
                    continue
                s = "alive"
                if "Нужна реанимация" in RSP.text:
                    s = "dead"
                if "Хорошее" in RSP.text:
                    await RSP.respond(f"использовать леденцы {random.randint(1, 4)}")
                    await asyncio.sleep(random.randint(3, 13))
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
                        int(i[0]) < 123
                        or (int(i[0]) > 123 and int(jab.group(1)) < 3333)
                    ) and p in ("Можно откормить", "Можно отправиться"):
                        continue
                    if s == "dead" and p not in ("Можно откормить", "можно покормить"):
                        await RSP.respond("реанимировать жабу")
                    await asyncio.sleep(random.randint(3, 13))
                    await RSP.respond(self.ded[p])
                await asyncio.sleep(random.randint(3, 13))
                cmn = "@toadbot Моя семья"
                await self.err(chat, cmn)
                if not RSP:
                    continue
                txt += f"\n{chat} {RSP.date.day} {RSP.date.hour}"
                s = 0
                if "У вас нет" in RSP.text:
                    continue
                if "Ваш жабёныш" in RSP.text and "Можно покормить" not in RSP.text:
                    s = 1
                    if int(i[0]) > 123:
                        await RSP.respond("@toadbot Покормить жабенка")
                if RSP.buttons:
                    if len(RSP.buttons[0]) == 2:
                        await RSP.respond("@toadbot Брак вознаграждение")
                    n = len(RSP.buttons)
                    if n == 1 and s == 1:
                        continue
                    await RSP.respond(self.ded[RSP.buttons[0][0].text])
                    if n == 1:
                        continue
                    await RSP.respond(self.ded[RSP.buttons[1][0].text])
                    if n == 2:
                        continue
                    await RSP.respond(self.ded[RSP.buttons[2][0].text])
            txt += f"\nlcheck: {message.date}"
            if "dayhour" not in self.su:
                msg = await self.client.send_message("me", txt)
                self.su.setdefault("dayhour", msg.id)
            elif not msg:
                msg = await self.client.send_message("me", txt)
                self.su["dayhour"] = msg.id
            else:
                await msg.edit(txt)
            self.db.set("Su", "su", self.su)
        elif message.text.startswith(("📉", "🛡")) and (
            "auto" in self.su or "chats" in self.su
        ):
            await self.client.send_message(
                1124824021,
                "💑👩‍❤️‍👨👨‍❤️‍👨💑",
                schedule=timedelta(minutes=random.randint(128, 184)),
            )
        elif (
            message.text.casefold().startswith(self.su["name"]) and " " in message.text
        ):
            await asyncio.sleep(random.randint(3, 13))
            reply = await message.get_reply_message()
            if " в " in message.text:
                if "жабл" in message.text:
                    chat = 1290958283
                elif "атмо" in message.text:
                    chat = 1563178957
                elif "пруд" in message.text:
                    chat = 1403626354
                elif "бот" in message.text:
                    chat = 1124824021
                else:
                    chat = message.peer_id
                if reply:
                    msg = reply
                else:
                    msg = message.text.split(" ", 3)[1]
                    if msg not in self.ded:
                        return
                    if msg in ("напади", "арена"):
                        await self.npn(chat, msg)
                    msg = self.ded[msg]
                await asyncio.sleep(random.randint(13, 33))
                await self.client.send_message(chat, msg)
            elif "тыкпых" in message.text:
                if reply:
                    return await reply.click()
                if "тыкпых " not in message.text:
                    return
                reg = re.search(r"/(\d+)/(\d+)", message.text)
                if not reg:
                    return
                mac = await self.client.get_messages(
                    int(reg.group(1)), ids=int(reg.group(2))
                )
                await mac.click()
            elif "буках" in message.text and self.su["name"] in ("кушки", "альберт"):
                await asyncio.sleep(random.randint(0, 360))
                cmn = "мой баланс"
                await self.err(chat, cmn)
                if not RSP:
                    return
                if "У тебя" in RSP.text:
                    await message.respond("взять жабу")
                elif "Баланс" not in RSP.text:
                    return
                jab = int(re.search(r"жабы: (\d+)", RSP.text).group(1))
                if jab < 50:
                    return
                await message.reply(f"отправить букашки {jab}")
            elif "del" in message.text:
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
                if reply and message.text.split(" ", 2)[1] in (
                    "ледик",
                    "аптек",
                    "буках",
                ):
                    return await reply.reply(
                        f"отправить {self.ded[msg]} {message.text.split(' ', 2)[2]}"
                    )
                msg = message.text.split(" ", 1)[1]
                if msg not in self.ded:
                    return
                if msg in ("карту", "лидерку"):
                    return await message.reply(self.ded[msg])
                if msg in ("напади", "арена"):
                    await self.npn(chat, msg)
                await asyncio.sleep(random.randint(13, 33))
                await message.respond(self.ded[msg])
        elif str(self.me.id) in message.text or message.mentioned:
            if "ход: " in message.text and message.buttons:
                await message.click()
            elif "сломалось" in message.text:
                await asyncio.sleep(random.randint(13, 33))
                txt = (
                    "клюв цапли",
                    "букашкомет",
                    "наголовник из клюва цапли",
                    "нагрудник из клюва цапли",
                    "налапники из клюва цапли",
                )
                for i in txt:
                    await message.respond(f"скрафтить {i}")
            elif "Банда получила" in message.text:
                await asyncio.sleep(random.randint(3, 13))
                await message.respond("отдать леденец")
                await asyncio.sleep(random.randint(3, 13))
                cmn = "@toadbot Моя банда"
                await self.err(chat, cmn)
                if not RSP and "📿" not in RSP.text:
                    return
                if "Кулон: Пусто" in RSP.text:
                    await message.respond("скрафтить кулон братвы")
            else:
                return
        else:
            return
