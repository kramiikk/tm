import asyncio
import logging
import random
import re
from datetime import timedelta

from telethon import events, functions

from .. import loader

logger = logging.getLogger(__name__)


@loader.tds
class KramiikkMod(loader.Module):
    """Алина, я люблю тебя!"""

    strings = {"name": "Kramiikk"}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.su = db.get("Su", "su", {})
        self.me = await client.get_me()

    async def err(self, chat, pattern):
        try:
            async with self.client.conversation(chat) as conv:
                global RSP
                RSP = await conv.wait_event(
                    events.NewMessage(
                        from_users=1124824021, chats=chat, pattern=pattern
                    )
                )
        except asyncio.exceptions.TimeoutError:
            pass

    async def bmj(self, chat):
        pattern = "🐸"
        await self.err(chat, pattern)
        jab = re.search(r"Ур.+: (\d+)[\s\S]*Бу.+: (\d+)", RSP.text)
        if "Живая" not in RSP.text:
            await self.client.send_message(chat, "<b>реанимировать жабу</b>")
        pattern = "🏃‍♂️"
        await self.client.send_message(chat, "<b>жаба инфо</b>")
        await self.err(chat, pattern)
        cmn = "<b>работа крупье</b>"
        if int(jab.group(1)) > 72 and int(jab.group(2)) > 3750:
            if (
                "В подземелье можно через 2ч" in RSP.text
                and "Жабу можно отправить" in RSP.text
            ):
                await self.client.send_message(chat, cmn)
            cmn = "<b>откормить жабку</b>"
            if "Можно откормить" in RSP.text:
                await self.client.send_message(chat, cmn)
            cmn = "<b>отправиться в золотое подземелье</b>"
            if "Можно отправиться" in RSP.text:
                await self.client.send_message(chat, cmn)
        else:
            if "можно отправить" in RSP.text:
                await self.client.send_message(chat, cmn)
            cmn = "<b>покормить жабку</b>"
            if "Жабу можно покормить" in RSP.text:
                await self.client.send_message(chat, cmn)
        cmn = "<b>завершить работу</b>"
        if "Ваша жаба в данже" in RSP.text and int(jab.group(1)) > 100:
            cmn = "<b>рейд старт</b>"
            pattern = "Ваше"
            await self.client.send_message(chat, "<b>мое снаряжение</b>")
            await self.err(chat, pattern)
            if "Пусто" in RSP.text and "Усилитель: Пусто" not in RSP.text:
                await self.client.send_message(chat, "<b>скрафтить клюв цапли</b>")
                await self.client.send_message(chat, "<b>скрафтить букашкомет</b>")
                await self.client.send_message(
                    chat, "<b>скрафтить наголовник из клюва цапли</b>"
                )
                await self.client.send_message(
                    chat, "<b>скрафтить нагрудник из клюва цапли</b>"
                )
                await self.client.send_message(
                    chat, "<b>скрафтить налапники из клюва цапли</b>"
                )
            await self.client.send_message(chat, cmn)
        elif "жабу с работы" in RSP.text:
            await self.client.send_message(chat, cmn)

    async def watcher(self, m):
        args = m.text
        chat = m.chat_id
        me = self.me.id
        name = self.me.username
        users = me
        if "name" in self.su:
            name = self.su["name"]
            users = self.su["users"]
        try:
            if m.message.casefold().startswith("/my_toad") and m.sender_id == me:
                await self.bmj(chat)
            elif (
                m.message.casefold().startswith((name, f"@{self.me.username}"))
                and "инфо" in m.message
                and m.sender_id in users
            ):
                await m.respond("<b>моя жаба</b>")
                await self.bmj(chat)
            elif (
                "Банда получила" in m.message
                or "Йоу, ваш клан" in m.message
                and m.sender_id in {1124824021}
            ):
                await self.client.send_message(
                    chat,
                    "<b>мой клан</b>",
                    schedule=timedelta(
                        minutes=random.randint(1, 30), seconds=random.randint(1, 30)
                    ),
                )
            elif m.message.startswith("мой клан") and m.sender_id == me:
                pattern = "•"
                await self.client.send_message(chat, "<b>мои жабы</b>")
                await self.err(chat, pattern)
                capt = re.findall(r"\| -100(\d+)", RSP.text)
                for i in capt:
                    try:
                        chat = int(i)
                        msg = await self.client.send_message(chat, "<b>моя жаба</b>")
                        await self.bmj(chat)
                    except:
                        pass
            elif (m.message.startswith((name, f"@{self.me.username}"))) and (
                m.sender_id in users
            ):
                cmn = "<b>реанимировать жабу</b>"
                reply = await m.get_reply_message()
                if "напиши в " in m.message:
                    chat = args.split(" ", 4)[3]
                    if chat.isnumeric():
                        chat = int(chat)
                    msg = args.split(" ", 4)[4]
                    if reply:
                        msg = reply
                    await self.client.send_message(chat, msg)
                elif "напиши" in m.message:
                    msg = args.split(" ", 2)[2]
                    if reply:
                        await reply.reply(msg)
                    else:
                        await m.respond(msg)
                elif "арена" in m.message:
                    chat = m.chat_id
                    pattern = "•"
                    await self.client.send_message(chat, "<b>мои жабы</b>")
                    await self.err(chat, pattern)
                    capt = re.findall(r"\| -100(\d+)", RSP.text)
                    for i in capt:
                        chat = int(i)
                        await self.client.send_message(chat, cmn)
                        await self.client.send_message(chat, "<b>на арену</b>")
                else:
                    if ("напади" or "подземелье") in m.message:
                        await m.respond(cmn)
                    cmn = args.split(" ", 1)[1]
                    if cmn in ded:
                        await m.reply(ded[cmn])
            elif (
                f"Сейчас выбирает ход: {self.me.first_name}" in m.message and m.buttons
            ):
                await m.respond("<b>реанимировать жабу</b>")
                await m.click(0)
            elif (
                m.sender_id in {830605725}
                and m.buttons
                and "Ваше уважение" not in m.message
                and "[12🔵" not in m.message
            ):
                await m.click(0)
            elif "НЕЗАЧЁТ!" in m.message:
                args = [int(x) for x in m.text.split() if x.isnumeric()]
                delta = timedelta(hours=args[1], minutes=args[2], seconds=33)
                delta = delta + timedelta(seconds=33)
                await self.client.send_message(
                    707693258, "<b>Фарма</b>", schedule=delta
                )
            elif m.message.startswith("su!") and m.sender_id == me:
                txt = int(args.split(" ", 1)[1])
                if txt == me and "name" not in self.su:
                    self.su.setdefault("name", name)
                    self.su.setdefault("users", [])
                    self.su["users"].append(txt)
                    msg = f"👺 <code>{name}</code> <b>запомните</b>"
                elif txt in self.su["users"]:
                    self.su["users"].remove(txt)
                    msg = f"🖕🏾 {txt} <b>успешно удален</b>"
                else:
                    self.su["users"].append(txt)
                    msg = f"🤙🏾 {txt} <b>успешно добавлен</b>"
                self.db.set("Su", "su", self.su)
                await m.respond(msg)
            elif m.message.startswith("sn!") and m.sender_id == me:
                self.su["name"] = args.split(" ", 1)[1]
                await m.respond(
                    "👻 <code>" + self.su["name"] + "</code> <b>успешно изменён</b>"
                )
                self.db.set("Su", "su", self.su)
            else:
                return
        finally:
            return


ded = {
    "го кв": "<b>начать клановую войну</b>",
    "напади": "<b>напасть на клан</b>",
    "подземелье": "<b>отправиться в золотое подземелье</b>",
    "карту": "<b>отправить карту</b>",
    "туса": "<b>жабу на тусу</b>",
}
