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
        self.db = db
        self.client = client
        self.me = await client.get_me()
        self.su = db.get("Su", "su", {})
        if "name" not in self.su:
            self.su.setdefault("name", self.me.first_name)
            self.su.setdefault("users", [1124824021, self.me.id])
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
            rsp = ""
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
                rsp += (await self.err(chat, cmn)).text
                if rsp == "" and "🗡" not in rsp:
                    return
                for i in (i for i in self.ded if i in rsp):
                    await asyncio.sleep(random.randint(3, n + 3))
                    await m.respond(self.ded[i])
            elif "Банда получила" in m.text and cn == 1:
                await m.respond("отдать леденец")
                await asyncio.sleep(random.randint(3, n + 3))
                cmn = "моя банда"
                rsp += (await self.err(chat, cmn)).text
                if rsp == "" and "📿" not in rsp:
                    return
                if "Кулон: Пусто" in rsp:
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
        rsp = ""
        rss = await self.err(chat, cmn)
        rsp += rss.text
        await self.client.delete_dialog(chat, revoke=True)
        if rsp == "":
            return
        for i in re.findall(r"•(.+) \|.+ (\d+) \| (-\d+)", rsp):
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
                rsp = ""
                rss = await self.err(chat, cmn)
                rsp += rss.text
            except Exception:
                pass
            if "Имя жабы" not in rsp or i[0] not in rsp and i[1] not in rsp:
                continue
            jab = re.search(r"Б.+: (\d+)", rsp).group(1)
            s = 1 if "Нужна реанимация" in rsp else 0
            if "Хорошее" in rsp:
                await asyncio.sleep(
                    random.randint(n, 96 + (ct.microsecond % 100)) + ct.minute
                )
                await rss.respond(f"использовать леденцы {random.randint(1, 3)}")
            await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
            cmn = "@toadbot Жаба инфо"
            rsp = ""
            rss = await self.err(chat, cmn)
            rsp += rss.text
            if "🏃‍♂️" not in rsp and "не в браке" not in rsp and i[0] not in rsp:
                continue
            if int(jab) < 1500:
                ar = 0
                ok = 0
                pz = 0
            if s == 1 and (
                ("можно покормить" not in rsp and "Можно откормить" not in rsp)
                or ok == 0
            ):
                await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
                await rss.respond("реанимировать жабу")
            if "подземелье можно через 2" in rsp:
                pz = 0
            if "не в браке" in rsp:
                fm = 0
            for p in (p for p in self.ded if p in rsp):
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
                    await rss.respond(self.ded[p])
                    await asyncio.sleep(random.randint(s, 33))
                    await rss.respond(self.ded[p])
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
                    await rss.respond(job)
                else:
                    await rss.respond(self.ded[p])
            if fm == 0:
                continue
            await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
            cmn = "Моя семья"
            rss = await self.err(chat, cmn)
            if not rss.buttons or "дней в браке" not in rsp or i[0] not in rsp:
                continue
            s = len(rss.buttons)
            await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
            await rss.respond(self.ded[rss.buttons[0][0].text])
            if s == 1:
                continue
            await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
            await rss.respond(self.ded[rss.buttons[1][0].text])
            if s == 2:
                continue
            await asyncio.sleep(random.randint(3, n + 3) + ct.minute)
            await rss.respond(self.ded[rss.buttons[2][0].text])
