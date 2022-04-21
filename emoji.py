import asyncio
import random
import re
from datetime import timedelta

from telethon import events

from .. import loader, utils

ded = {
    "Нужна реанимация": "реанимировать жабу",
    "Хорошее": "использовать леденцы 4",
    "жабу с работы": "завершить работу",
    "Можно откормить": "откормить жабку",
    "можно покормить": "покормить жабку",
    "Можно отправиться": "отправиться в золотое подземелье",
    "жаба в данже": "рейд старт",
    "можно отправить": "работа крупье",
    "Используйте атаку": "на арену",
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


@loader.tds
class KramiikkMod(loader.Module):
    """Алина, я люблю тебя!"""

    strings = {"name": "Kramiikk"}

    async def abj(self, m):
        chat = m.chat_id
        await m.delete()
        cmn = "мои жабы"
        await self.err(chat, cmn)
        await self.client.send_read_acknowledge(m.chat_id)
        capt = re.findall(r"\| -100(\d+)", RSP.text)
        for i in capt:
            try:
                chat = int(i)
                await self.bmj(chat)
            else:
                pass

    async def bbj(self, m):
        if not m.text.startswith("📉"):
            return
        if "auto" in self.su:
            await self.client.send_message(
                m.sender_id,
                "💑👩‍❤️‍👨👨‍❤️‍👨💑",
                schedule=timedelta(
                    minutes=random.randint(33, 55), seconds=random.randint(1, 60)
                ),
            )

    async def cbj(self, m):
        if not m.text.casefold().startswith(self.su["name"]):
            return
        reply = await m.get_reply_message()
        if "напиши в " in m.text:
            chat = m.text.split(" ", 4)[3]
            if chat.isnumeric():
                chat = int(chat)
            if reply:
                txt = reply
            txt = m.text.split(" ", 4)[4]
            return await self.client.send_message(chat, txt)
        if "напиши" in m.text:
            txt = m.text.split(" ", 2)[2]
            if reply:
                return await reply.reply(txt)
            await utils.answer(m, txt)
        elif "буках" in m.text and self.su["name"] in ["кушки", "альберт"]:
            await asyncio.sleep(random.randint(0, 360))
            chat = m.chat_id
            cmn = "мой баланс"
            await self.err(chat, cmn)
            if "У тебя" in RSP.text:
                return await utils.answer(m, "взять жабу")
            if "Баланс" not in RSP.text:
                return
            jab = int(re.search(r"жабы: (\d+)", RSP.text).group(1))
            if jab >= 50:
                await m.reply(f"отправить букашки {jab}")
        else:
            cmn = m.text.split(" ", 1)[1]
            if cmn in ded:
                await m.reply(ded[cmn])

    async def dbj(self, m):
        await utils.answer(m, "реанимировать жабу")
        return await m.click(0)

    async def ebj(self, m, r):
        for i in (i for i in r if i in m.text.casefold()):
            return await r[i]

    async def bmj(self, chat):
        """алгоритм жабабота"""
        cmn = "моя жаба"
        await self.err(chat, cmn)
        for i in (i for i in ded if i in RSP.text):
            await utils.answer(RSP, ded[i])
        jab = re.search(r"У.+: (\d+)[\s\S]*Б.+: (\d+)", RSP.text)
        if not jab:
            return
        cmn = "жаба инфо"
        await self.err(chat, cmn)
        if "🏃‍♂️" not in RSP.text:
            return
        for i in (i for i in ded if i in RSP.text):
            if (
                int(jab.group(1)) < 123
                or (int(jab.group(1)) > 123 and int(jab.group(2)) < 3333)
            ) and i in ("Можно откормить", "Можно отправиться"):
                continue
            await utils.answer(RSP, ded[i])
        if int(jab.group(1)) > 123 and "работы" in RSP.text:
            cmn = "мое снаряжение"
            await self.err(chat, cmn)
            if "🗡" not in RSP.text:
                return
            for i in (i for i in ded if i in RSP.text):
                await utils.answer(RSP, ded[i])

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.su = db.get("Su", "su", {})
        self.me = await client.get_me()
        if "name" not in self.su:
            self.su.setdefault("name", self.me.username)
            self.su.setdefault("users", [self.me.id, 1124824021, 1785723159])
            self.db.set("Su", "su", self.su)
        if 1124824021 not in self.su["users"]:
            self.su["users"].append(1124824021)
            self.db.set("Su", "su", self.su)
        if 1785723159 not in self.su["users"]:
            self.su["users"].append(1785723159)
            self.db.set("Su", "su", self.su)

    async def err(self, chat, cmn):
        """работа с ответом жабабота"""
        async with self.client.conversation(chat, exclusive=False) as conv:
            try:
                txt = await conv.send_message(cmn)
                global RSP
                RSP = await conv.get_response()
            except asyncio.exceptions.TimeoutError:
                txt = await conv.send_message(cmn)
                RSP = await self.client.get_messages(chat, search=" ")
            await conv.cancel_all()
            if chat in [1124824021]:
                await txt.delete()
                await RSP.delete()

    async def sacmd(self, m):
        """будет смотреть за вашими жабами"""
        if "auto" not in self.su:
            self.su.setdefault("auto", {})
            msg = "<b>активирована</b>"
        else:
            self.su.pop("auto")
            msg = "<b>деактивирована</b>"
        self.db.set("Su", "su", self.su)
        await utils.answer(m, msg)

    async def sncmd(self, m):
        """ник для команд"""
        msg = utils.get_args_raw(m)
        self.su["name"] = msg.casefold()
        txt = "👻 <code>" + self.su["name"] + "</code> <b>успешно изменён</b>"
        await utils.answer(m, txt)
        self.db.set("Su", "su", self.su)

    async def sucmd(self, m):
        """добавляет пользователей для управление акк"""
        msg = utils.get_args_raw(m)
        if msg in self.su["users"]:
            txt = int(msg)
            self.su["users"].remove(txt)
            msg = f"🖕🏾 {txt} <b>успешно удален</b>"
        else:
            txt = int(msg)
            self.su["users"].append(txt)
            msg = f"🤙🏾 {txt} <b>успешно добавлен</b>"
        self.db.set("Su", "su", self.su)
        await utils.answer(m, msg)

    async def watcher(self, m):
        fff = {
            "💑👩‍❤️‍👨👨‍❤️‍👨💑": self.abj(m),
            "📉": self.bbj(m),
            self.su["name"]: self.cbj(m),
        }
        dff = {
            "выбирает": self.dbj(m),
        }
        try:
            if m.sender_id in self.su["users"]:
                r = dff if m.mentioned and "выбирает" in m.text else fff
                await self.ebj(m, r)
        except Exception as e:
            return await self.client.send_message("me", f"Error:\n{' '.join(e.args)}")


# import logging
# from .. import loader
# from telethon import events
# import asyncio
# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.triggers.cron import CronTrigger
# import re
# from datetime import timedelta

# # requires: apscheduler

# logger = logging.getLogger(__name__)

# @loader.tds
# class SchedulerMod(loader.Module):
#     """Шедулер"""
#     strings = {'name': 'Scheduler'}

#     async def client_ready(self, client, db):
#         self.client = client
#         self.db = db

#         TOAD_STATION = -1001447960786
#         TOM_REDDL = -1001441941681
#         FROPPY = -1001403626354

#         FARMS = {"Жабоботсво" : -543554726,
#                 "Жабы Вероны" : -1001256439407,
#                 "." : -1001409792751,
#                 "жабы лена" : -1001419547228,
#                 "Хэлло Вин!" : -1001426018704,
#                 "Жабьи специи" : -1001499700136,
#                 "LSDtoads" : -1001493923839,
#                 "Жаботорт" : -1001436786642,
#                 "Танцы по средам" : -1001481051409,
#                 "IELTS" : -1001492669520,
#                 "Домик в болоте " : -1001520533176,
#                 "Космос нас ждет" : -1001460270560,
#                 "Жабьи монстрики" : -1001427000422,
#                 "Forbidden Frog" : -1001511984124,
#                 "AstroFrog" : -1001575042525,
#                 "Сжабки нелс(платон)" : -1001165420047,
#                 "Жабочка" : -1001666737591,
#                 "Сказочный донатер" : -1001648008859,
#                 "Листик" : -1001685708710,
#                 "Жабы аферисты Крам и бабушка" : -421815520,
#                 "Сны лягушек" : -1001767427396,
#                 "Курсы вышивания" : -1001760342148,
#                 "Цыганка" : -1001714871513,
#                 "Vitoad" : -1001771130958,
#                 "Консилиум жаб" : -1001777552705,
#                 "Дирижабль" : -1001264330106,
#                 "Золотая жаба" : -1001787904496,
#                 "Болотозавр" : -1001624280659,
#                 "Багoboty" : -1001380664241,
#                 "Осколок" : -1001289617428,
#                 "Жабье Царство" : -714494521,
#                 "Деревня жаб" : -668421956}

#         async def feed_toad(chat):
#             await client.send_message(chat, 'откормить жабу')
#             async with client.conversation(chat) as conv:
#                 response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=chat))
#                 await asyncio.sleep(3)
#                 await client.send_message(chat, 'откормить жабку')
#                 response = await response
#                 next_food_hours = 4
#                 next_food_minutes = 3
#                 if "Откармливать жабу" in response.raw_text:

#                    pattern = re.compile('через (.) ч:(.?.) мин', re.IGNORECASE) #паттерн времени
#                    matcher = pattern.search(response.raw_text)

#                    next_food_hours = int(matcher.group(1)) #получаем часы из сообщения
#                    next_food_minutes = int(matcher.group(2)) #получаем минуты из сообщения

#                 delta = timedelta(hours=next_food_hours, minutes=next_food_minutes)
#                 await client.send_message(chat, 'откормить жабку', schedule=delta)

#                 for number in range(5):
#                    delta += timedelta(hours=4, minutes=3)
#                    await client.send_message(chat, 'откормить жабку', schedule=delta)
#                    await asyncio.sleep(1)

#                 delta = timedelta(hours=1)
#                 await client.send_message(chat, 'отправиться в золотое подземелье', schedule=delta)

#                 for number in range(15):
#                    delta += timedelta(hours=1, minutes=30)
#                    await client.send_message(chat, 'отправиться в золотое подземелье', schedule=delta)
#                    await asyncio.sleep(1)


#         async def send_kid_to_kindergarten():
#             await client.send_message(TOM_REDDL, 'отправить жабенка в детский сад')
#             await client.send_message(TOAD_STATION, 'отправить жабенка в детский сад')
#             await client.send_message(FROPPY, 'отправить жабенка в детский сад')

#         async def send_kid_to_fighting():
#             await client.send_message(TOM_REDDL, 'отправить жабенка на махач')
#             await client.send_message(TOAD_STATION, 'отправить жабенка на махач')
#             await client.send_message(FROPPY, 'отправить жабенка на махач')

#         async def feed_kid():
#             await client.send_message(TOM_REDDL, 'покормить жабенка')
#             await client.send_message(TOAD_STATION, 'покормить жабенка')
#             await client.send_message(TOAD_STATION, '/dick@kraft28_bot')
#             await client.send_message(FROPPY, 'покормить жабенка')
#             await client.send_message(FROPPY, '/dick@kraft28_bot')

#         async def kid_from_kindergarten():
#             await client.send_message(TOAD_STATION, 'забрать жабенка')
# #             await client.send_message(TOM_REDDL, 'забрать жабенка')
#             await client.send_message(FROPPY, 'забрать жабенка')

#         async def feed_toads():
#             await feed_toad(TOM_REDDL)
#             await feed_toad(TOAD_STATION)
#             await feed_toad(FROPPY)

#         async def best_toad_on_farms():
#             for farm_name, farm_id in FARMS.items():
#                 await asyncio.sleep(5)
#                 await client.send_message(farm_id, 'жаба дня')

#         async def collect_money():
#             for farm_name, farm_id in FARMS.items():
#                 await asyncio.sleep(5)
#                 await client.send_message(farm_id, '!дайте буках')

#         async def arena():
#             await client.send_message(TOM_REDDL, 'на арену')
#             await client.send_message(TOAD_STATION, 'на арену')
#             await client.send_message(FROPPY, 'на арену')

#         async def recover():
#             await client.send_message(TOM_REDDL, 'реанимировать жабу')
#             await client.send_message(TOAD_STATION, 'реанимировать жабу')
#             await client.send_message(FROPPY, 'реанимировать жабу')

#         scheduler = AsyncIOScheduler()
#         scheduler.add_job(send_kid_to_kindergarten, CronTrigger.from_crontab('03 6 * * *', timezone='Europe/Moscow'))
#         scheduler.add_job(send_kid_to_fighting, CronTrigger.from_crontab('10 8 * * *', timezone='Europe/Moscow'))
#         scheduler.add_job(kid_from_kindergarten, CronTrigger.from_crontab('6 12 * * *', timezone='Europe/Moscow'))
#         scheduler.add_job(best_toad_on_farms, CronTrigger.from_crontab('15 0 * * *', timezone='Europe/Moscow'))
# #        scheduler.add_job(collect_money, CronTrigger.from_crontab('0 9 * * *', timezone='Europe/Moscow'))
# #         scheduler.add_job(arena, CronTrigger.from_crontab('5,10,15,20 8-21 * * *', timezone='Europe/Moscow'))
# #         scheduler.add_job(recover, CronTrigger.from_crontab('3 8-21 * * *', timezone='Europe/Moscow'))

#         scheduler.start()

#         asyncio.get_event_loop().run_forever()

#         elif m.text.startswith("/an") and m.from_user.id == self._me:
#             await self._bot.send_message(
#                 int(m.text.split(" ", 2)[1]), m.text.split(" ", 2)[2]
#             )
#             await m.answer(self.strings("sent"))
#         elif self.inline.gs(m.from_user.id) == "fb_send_message":
#             r = await self._bot.forward_message(self._me, m.chat.id, m.message_id)
#             await r.answer(m.from_user.id)
#             await m.answer(self.strings("sent"))


#     async def emojicmd(self, message):
#         args = utils.get_args_raw(message)
#         c = args.split(" ")
#         emoji = [
#             "😀",
#             "😃",
#             "😄",
#             "😁",
#             "😆",
#             "😅",
#             "🤣",
#             "🥰",
#             "😇",
#             "😊",
#             "😉",
#             "🙃",
#             "🙂",
#             "😂",
#             "😍",
#             "🤩",
#             "😘",
#             "😗",
#             "☺",
#             "😚",
#             "😙",
#             "🤗",
#             "🤑",
#             "😝",
#             "🤪",
#             "😜",
#             "😛",
#             "😋",
#             "🤭",
#             "🤫",
#             "🤔",
#             "🤐",
#             "🤨",
#             "😐",
#             "😑",
#             "😌",
#             "🤥",
#             "😬",
#             "🙄",
#             "😒",
#             "😏",
#             "😶",
#             "😔",
#             "😪",
#             "🤤",
#             "😴",
#             "😷",
#             "🤒",
#             "🤕",
#             "🤢",
#             "🤯",
#             "🤮",
#             "🤠",
#             "🤧",
#             "🥳",
#             "🥵",
#             "😎",
#             "🥶",
#             "🤓",
#             "🥴",
#             "🧐",
#             "😵",
#             "😕",
#             "😳",
#             "😢",
#             "😲",
#             "😥",
#             "😯",
#             "😰",
#             "😮",
#             "😨",
#             "😧",
#             "🙁",
#             "😦",
#             "😟",
#             "🥺",
#             "😭",
#             "😫",
#             "😱",
#             "🥱",
#             "😖",
#             "😤",
#             "😣",
#             "😡",
#             "😞",
#             "😠",
#             "😓",
#             "🤬",
#             "😩",
#             "😈",
#             "👿",
#         ]
#         d = []
#         e = len(c)
#         for i in range(e):
#             rand = random.choice(emoji)
#             d.append(c[i])
#             d.append(rand)
#         f = len(d) - 1
#         d.pop(f)
#         t = "".join(d)
#         await message.edit(t)

#     async def chatcmd(self, message):
#         chat = str(message.chat_id)
#         await message.respond(f"Айди чата: <code>{chat}</code>")

#     async def delmsgcmd(self, message):
#         msg = [
#             msg
#             async for msg in message.client.iter_messages(
#                 message.chat_id, from_user="me"
#             )
#         ]
#         if utils.get_args_raw(message):
#             args = int(utils.get_args_raw(message))
#         else:
#             args = len(msg)
#         for i in range(args):
#             await msg[i].delete()
#             await sleep(0.16)

#     async def shifrcmd(self, message):
#         text = utils.get_args_raw(message).lower()
#         txtnorm = dict(
#             zip(
#                 map(ord, "йцукенгшщзхъфывапролджэячсмитьбю. ?!,-:;"),
#                 "3ëjmqv9ô§üldйa¿42zэouəà>ý5eö$0¡<61¥g8tъ7",
#             )
#         )
#         txt = text.translate(txtnorm)
#         await message.edit(txt)
#         await sleep(300)
#         await message.delete()

#     async def deshifrcmd(self, message):
#         text = str(await message.get_reply_message()).split("'")
#         await message.delete()
#         txt = text[1]

#         txtnorm = dict(
#             zip(
#                 map(ord, "3ëjmqv9ô§üldйa¿42zэouəà>ý5eö$0¡<61¥g8tъ7"),
#                 "йцукенгшщзхъфывапролджэячсмитьбю. ?!,-:;7",
#             )
#         )
#         txte = txt.translate(txtnorm)
#         await message.client.send_message("me", txte)

#     @loader.owner
#     async def qgcmd(self, m):
#         jup = ""
#         for a in utils.get_args_raw(m):
#             if a.lower() in alp:
#                 arp = alp[a.lower()]
#                 if a.isupper():
#                     arp = arp.upper()
#             else:
#                 arp = a
#             jup += arp
#         await utils.answer(m, jup)


# alp = {
#     "а": "a",
#     "ә": "ä",
#     "б": "b",
#     "в": "v",
#     "г": "g",
#     "ғ": "ğ",
#     "д": "d",
#     "е": "e",
#     "ж": "j",
#     "з": "z",
#     "и": "i",
#     "й": "y",
#     "к": "k",
#     "қ": "k",
#     "л": "l",
#     "м": "m",
#     "н": "n",
#     "ң": "ń",
#     "о": "o",
#     "ө": "ö",
#     "п": "p",
#     "р": "r",
#     "с": "s",
#     "т": "t",
#     "у": "w",
#     "ұ": "u",
#     "ү": "ü",
#     "ф": "f",
#     "х": "h",
#     "һ": "h",
#     "ы": "ı",
#     "і": "i",
#     "ч": "ch",
#     "ц": "ts",
#     "ш": "c",
#     "щ": "cc",
#     "э": "e",
#     "я": "ya",
# }
