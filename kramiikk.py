import asyncio
import logging
import re
import random
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
        self.su = self.db.get("Su", "su", {})
        self.me = await client.get_me()

    async def err(self, chat, p):
        try:
            async with self.client.conversation(chat) as conv:
                global RSP
                RSP = await conv.wait_event(
                    events.NewMessage(from_users=1124824021, chats=chat, pattern=p)
                )
        except asyncio.exceptions.TimeoutError:
            pass

    async def bmj(self, chat):
        p = "🐸"
        await self.err(chat, p)
        jab = re.search(r"Ур.+: (\d+)[\s\S]*Бу.+: (\d+)", RSP.text)
        if "Живая" not in RSP.text:
            await self.client.send_message(chat, "реанимировать жабу")
        p = "🏃‍♂️"
        await self.client.send_message(chat, "<b>жаба инфо</b>")
        await self.err(chat, p)
        cmn = "работа крупье"
        if int(jab.group(1)) > 72 and int(jab.group(2)) > 3750:
            if (
                "В подземелье можно через 2ч" in RSP.text
                and "Жабу можно отправить" in RSP.text
            ):
                await self.client.send_message(chat, cmn)
            cmn = "отправиться в золотое подземелье"
            if "Можно отправиться" in RSP.text:
                await self.client.send_message(chat, cmn)
            cmn = "откормить жабку"
            if "(Можно откормить)" in RSP.text:
                await self.client.send_message(chat, cmn)
        else:
            if "можно отправить" in RSP.text:
                await self.client.send_message(chat, cmn)
            cmn = "покормить жабку"
            if "Жабу можно покормить" in RSP.text:
                await self.client.send_message(chat, cmn)
        cmn = "завершить работу"
        if "Ваша жаба в данже" in RSP.text and int(jab.group(1)) > 100:
            cmn = "рейд старт"
            await self.client.send_message(chat, cmn)
        elif "жабу с работы" in RSP.text:
            await self.client.send_message(chat, cmn)

    async def watcher(self, m):
        args = m.text
        if self.me.id in {547639600}:
            name = "Нельс"
        elif self.me.id in {980699009}:
            name = "Лена"
        elif self.me.id in {230473666}:
            name = "Ваня"
        elif self.me.id in {887255479}:
            name = "Кира"
        else:
            name = self.me.first_name
        usrs = {1785723159, 1261343954}
        chat = m.chat_id
        if "name" in self.su:
            name = self.su["name"]
            usrs = self.su["users"]
        try:
            if (
                m.message.casefold().startswith("/my_toad")
                and m.sender_id == self.me.id
            ):
                await self.bmj(chat)
            elif (
                m.message.startswith((name, f"@{self.me.username}"))
                and "инфо" in m.message
                and m.sender_id in usrs
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
                    "мой клан",
                    schedule=timedelta(
                        minutes=random.randint(1, 30), seconds=random.randint(1, 30)
                    ),
                )
            elif "мой клан" in m.message and m.sender_id == self.me.id:
                p = "•"
                await self.client.send_message(chat, "<b>мои жабы</b>")
                await self.err(chat, p)
                capt = re.findall(r"\| -100(\d+)", RSP.text)
                for i in capt:
                    chat = int(i)
                    await self.client.send_message(chat, "<b>моя жаба</b>")
                    await self.bmj(chat)
            elif (m.message.startswith((name, f"@{self.me.username}"))) and (
                m.sender_id in usrs
            ):
                cmn = "<b>реанимировать жабу</b>"
                reply = await m.get_reply_message()
                if "напиши в " in m.message:
                    chat = args.split(" ", 4)[3]
                    if chat.isnumeric():
                        chat = int(chat)
                    s = args.split(" ", 4)[4]
                    if reply:
                        s = reply
                    await self.client.send_message(chat, s)
                elif "напиши" in m.message:
                    mmsg = args.split(" ", 2)[2]
                    if reply:
                        await reply.reply(mmsg)
                    else:
                        await m.respond(mmsg)
                elif "арена" in m.message:
                    chat = m.chat_id
                    p = "•"
                    await self.client.send_message(chat, "<b>мои жабы</b>")
                    await self.err(chat, p)
                    capt = re.findall(r"\| -100(\d+)", RSP.text)
                    for i in capt:
                        chat = int(i)
                        await self.client.send_message(chat, cmn)
                        await self.client.send_message(chat, "<b>на арену</b>")
                elif "снаряжение" in m.message:
                    p = "Ваше"
                    await m.respond("<b>мое снаряжение</b>")
                    await self.err(chat, p)
                    if "Пусто" in RSP.text:
                        await m.respond("<b>скрафтить клюв цапли</b>")
                        await m.respond("<b>скрафтить букашкомет</b>")
                        await m.respond("<b>скрафтить наголовник из клюва цапли</b>")
                        await m.respond("<b>скрафтить нагрудник из клюва цапли</b>")
                        await m.respond("<b>скрафтить налапники из клюва цапли</b>")
                else:
                    if ("напади" or "подземелье") in m.message:
                        await m.respond(cmn)
                    i = args.split(" ", 1)[1]
                    if i in ded:
                        await m.reply(ded[i])
            elif (
                f"Сейчас выбирает ход: {self.me.first_name}" in m.message and m.buttons
            ):
                await m.respond("реанимировать жабу")
                await m.click(0)
            elif m.message.startswith("su!") and m.sender_id == self.me.id:
                i = int(args.split(" ", 1)[1])
                if i == self.me.id and "name" not in self.su:
                    self.su.setdefault("name", name)
                    self.su.setdefault("users", [])
                    self.su["users"].append(i)
                    txt = f"👺 <code>{name}</code> <b>запомните</b>"
                elif i in self.su["users"]:
                    self.su["users"].remove(i)
                    txt = f"🖕🏾 {i} успешно удален"
                else:
                    self.su["users"].append(i)
                    txt = f"🤙🏾 {i} успешно добавлен"
                self.db.set("Su", "su", self.su)
                await m.respond(txt)
            elif m.message.startswith("sn!") and m.sender_id == self.me.id:
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
