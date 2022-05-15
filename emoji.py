import asyncio
import random
import re
from datetime import timedelta

from telethon.tl.types import Message

from .. import loader


@loader.tds
class KramiikkMod(loader.Module):
    """Алина, я люблю тебя!😘"""

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
            "Нужна реанимация": "реанимировать жабу",
            "Хорошее": "использовать леденцы 4",
            "жабу с работы": "завершить работу",
            "Можно откормить": "откормить жабку",
            "можно покормить": "покормить жабку",
            "Можно отправиться": "отправиться в золотое подземелье",
            "жаба в данже": "рейд старт",
            "Используйте атаку": "на арену",
            "можно отправить": self.su["job"],
            "золото": "отправиться в золотое подземелье",
            "го кв": "начать клановую войну",
            "напади": "напасть на клан",
            "карту": "отправить карту",
            "туса": "жабу на тусу",
            "Ближний бой: Пусто": "скрафтить клюв цапли",
            "Дальний бой: Пусто": "скрафтить букашкомет",
            "Наголовник: Пусто": "скрафтить наголовник из клюва цапли",
            "Нагрудник: Пусто": "скрафтить нагрудник из клюва цапли",
            "Налапники: Пусто": "скрафтить налапники из клюва цапли",
            "Банда: Пусто": "взять жабу",
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
        self.su.setdefault("job", msg.casefold())
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
        if message.text.startswith("💑👩‍❤️‍👨👨‍❤️‍👨💑"):
            chat = message.peer_id
            cmn = "мои жабы"
            dayhour = "dayhour"
            await self.err(chat, cmn)
            if not RSP:
                return
            await self.client.delete_dialog(chat, revoke=True)
            if "chats" not in self.su and "auto" not in self.su:
                return
            for s in re.findall(r"(\d+) \| (-\d+)", RSP.text):
                chat = int(s[1])
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
                        ts = timedelta(
                            days=message.date.day, hours=message.date.hour
                        ) - timedelta(days=int(day), hours=int(hur))
                        if timedelta(days=0, hours=0) <= ts < timedelta(days=0, hours=2):
                            dayhour += f"\n{chat} {day} {hour}"
                            continue
                cmn = "/my_toad"
                await self.err(chat, cmn)
                if not RSP:
                    continue
                for i in (i for i in self.ded if i in RSP.text):
                    await RSP.respond(self.ded[i])
                jab = re.search(r"Б.+: (\d+)", RSP.text)
                if not jab:
                    continue
                cmn = "/toad_info"
                await self.err(chat, cmn)
                if not RSP:
                    continue
                if "🏃‍♂️" not in RSP.text:
                    continue
                for p in (p for p in self.ded if p in RSP.text):
                    if (
                        int(s[0]) < 123
                        or (int(s[0]) >= 123 and int(jab.group(1)) < 3333)
                    ) and p in ("Можно откормить", "Можно отправиться"):
                        continue
                    await RSP.respond(self.ded[p])
                dayhour += f"\n{chat} {RSP.date.day} {RSP.date.hour}"
            if "dayhour" not in self.su:
                dh = await self.client.send_message("me", dayhour)
                self.su.setdefault("dayhour", dh.id)
            elif not msg:
                msg = await self.client.send_message("me", dayhour)
                self.su["dayhour"] = msg.id
            else:
                await msg.edit(dayhour)
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
            chat = message.peer_id
            reply = await message.get_reply_message()
            if "напиши в " in message.text:
                chat = message.text.split(" ", 4)[3]
                txt = message.text.split(" ", 4)[4]
                if chat.isnumeric():
                    chat = int(chat)
                if reply:
                    txt = reply
                await self.client.send_message(chat, txt)
            elif "напиши " in message.text:
                txt = message.text.split(" ", 2)[2]
                if reply:
                    return await reply.reply(txt)
                await message.respond(txt)
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
            else:
                cmn = message.text.split(" ", 1)[1]
                if cmn not in self.ded:
                    return
                await message.reply(self.ded[cmn])
        elif (
            str(self.me.id) in message.text
            and "ход: " in message.text
            and message.buttons
        ):
            await message.click()
        else:
            return
