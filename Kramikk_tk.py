from math import floor
from html import escape
from random import choice
from asyncio import sleep
from .. import loader, utils
from datetime import timedelta
from urllib.parse import quote_plus
from telethon.tl.types import Message
from asyncio.exceptions import TimeoutError
from apscheduler.triggers.cron import CronTrigger
from telethon import events, functions, types, sync
from telethon.tl.functions.users import GetFullUserRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon.errors.rpcerrorlist import UsernameOccupiedError
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
import asyncio, datetime, inspect, io, json, logging, os, time, random, re, requests

#requires: apscheduler

logger = logging.getLogger(__name__)
asl = [
    "жаба дня",
    "топ жаб",
    "сезон кланов",
    "кланы",
    "взять жабу",
]
types_of = [
    "femdom",
    "tickle",
    "classic",
    "ngif",
    "erofeet",
    "meow",
    "erok",
    "poke",
    "les",
    "hololewd",
    "lewdk",
    "keta",
    "feetg",
    "nsfw_neko_gif",
    "eroyuri",
    "kiss",
    "_8ball",
    "kuni",
    "tits",
    "pussy_jpg",
    "cum_jpg",
    "pussy",
    "lewdkemo",
    "lizard",
    "slap",
    "lewd",
    "cum",
    "cuddle",
    "spank",
    "smallboobs",
    "goose",
    "Random_hentai_gif",
    "avatar",
    "fox_girl",
    "nsfw_avatar",
    "hug",
    "gecg",
    "boobs",
    "pat",
    "feet",
    "smug",
    "kemonomimi",
    "solog",
    "holo",
    "wallpaper",
    "bj",
    "woof",
    "yuri",
    "trap",
    "anal",
    "baka",
    "blowjob",
    "holoero",
    "feed",
    "neko",
    "gasm",
    "hentai",
    "futanari",
    "ero",
    "solo",
    "waifu",
    "pwankg",
    "eron",
    "erokemo",
]


def chunks(lst, n):
    return [lst[i : i + n] for i in range(0, len(lst), n)]


def register(cb):
    cb(KramikkMod())


@loader.tds
class KramikkMod(loader.Module):
    """Алина, я люблю тебя!"""

    answers = {
        0: ("Невнятен вопрос, хз, что отвечать",),
        1: ("Ответ тебе известен", "Ты знаешь лучше меня!", "Ответ убил!.."),
        2: ("Да", "Утвердительный ответ", "Ага"),
        3: (
            "Да, но есть помехи", "Может быть", "Вероятно", "Возможно", "Наверняка"
        ),
        4: (
            "Знаю ответ, но не скажу",
            "Думай!",
            "Угадай-ка...",
            "Это загадка от Жака Фреско...",
        ),
        5: ("Нет", "Отрицательный ответ"),
        6: (
            "Обязательно", "Конечно", "Сто пудов", "Абсолютно", "Разумеется", "100%"
        ),
        7: ("Есть помехи...", "Вряд ли", "Что-то помешает", "Маловероятно"),
        8: ("Да, но нескоро", "Да, но не сейчас!"),
        9: ("Нет, но пока", "Скоро!", "Жди!", "Пока нет"),
    }
    strings = {
        "name": "Kramikk",
        "update": "<b>обновление списка кланов</b>",
        "name_not_found": "<u>Не указано имя:</u>\n <code>.kblname %name%</code>",
        "name_set": "<u>Имя успешно установлено</u>",
        "quest_not_found": "<u>Агде вопрос?</u>",
        "quest_answer": "\n\n<u>%answer%</u>",
        "mention": "<a href='tg://user?id=%id%'>%name%</a>",
    }

    def __init__(self):
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        ans = (
            await utils.run_sync(
                requests.get, "https://nekos.life/api/v2/endpoints"
            )
        ).json()
        clans = {
            "Багoboty": -1001380664241,
            "Том Рэддл": -1001441941681,
            "Манулы и Зайчатки": -1001289617428,
            "Жаботорт": -1001436786642,
            "Своя атмосфера": -1001485617300,
            "Бар": -1001465870466,
            ".": -1001409792751,
            "жабки нэлс(платон)": -1001165420047,
            "Станция": -1001447960786,
            "Дирижабль": -1001264330106,
            "Сказочный донатер": -1001648008859,
            "Листик": -1001685708710,
            "Жабы аферисты Крам и бабушка": -421815520,
            "Хэлло Вин!": -1001426018704,
            "Танцы по средам": -1001481051409,
            "IELTS": -1001492669520,
            "Домик в болоте": -1001520533176,
            "Космос нас ждет": -1001460270560,
            "Forbidden Frog": -1001511984124,
            "Vitoad": -1001771130958,
            "Курсы вышивания": -1001760342148,
            "Золотая жаба": -1001787904496,
            "LSDtoads": -1001493923839,
            "Цыганка": -1001714871513,
            "жабы лена": -1001419547228,
            "Жабочка": -1001666737591,
            "AstroFrog": -1001575042525,
            "Консилиум жаб": -1001777552705,
            "Жабьи монстрики": -1001427000422,
            "Жабы Вероны": -1001256439407,
            "Жабьи специи": -1001499700136,
            "Болотозавр": -1001624280659,
            "Ж4блЯ": -1001290958283,
        }
        self.categories = json.loads(
            "["
            + [_ for _ in ans if "/api" in _ and "/img/" in _][0]
            .split("<")[1]
            .split(">")[0]
            .replace("'", '"')
            + "]"
        )
        self.clans = clans
        self.client = client
        self.endpoints = {
            "img": "https://nekos.life/api/v2/img/",
            "owoify": "https://nekos.life/api/v2/owoify?text=",
            "why": "https://nekos.life/api/v2/why",
            "cat": "https://nekos.life/api/v2/cat",
            "fact": "https://nekos.life/api/v2/fact",
        }
        self.db = db
        self.me = await client.get_me()
        self.status = db.get("Status", "status", {})
    TOAD_STATION = -1001447960786
    TOM_REDDL = -1001441941681

    @loader.sudo
    async def delmecmd(self, message):
        """Удаляет все свои сообщения в групповых чатах"""
        chat = message.chat
        args = utils.get_args_raw(message)
        mag = await utils.answer(message, "<b>Ищу сообщения...</b>")
        all = (await self.client.get_messages(chat, from_user="me")).total
        await utils.answer(mag, f"<b>Удаляются {all} сообщений..</b>")
        messages = [
            msg async for msg in self.client.iter_messages(chat, from_user="me")
        ]
        _ = ""
        async for msg in self.client.iter_messages(chat, from_user="me"):
            if _:
                await msg.delete()
            else:
                _ = "_"
        await message.delete()

    async def idcmd(self, message):
        """ID юзера, и прочая фигня"""
        reply = await message.get_reply_message()
        user = await self.client.get_entity(reply.sender_id)
        adjectives_start = [
            "хороший(-ая)",
            "интересный(-ая)",
            "прекрасный(-ая)",
            "для меня няшный(-ая)",
            "пышный(-ая)",
            "ангельский(-ая)",
            "аппетитный(-ая)",
        ]
        emojies = ["🐶", "🐱", "🐹", "🐣", "🥪", "🍓", "♥️", "🤍", "🪄", "✨", "🦹🏻", "🌊"]
        nouns = ["человек", "участник(-ца) данного чата"]
        starts = [
            "Не хочу делать поспешных выводов, но",
            "Я, конечно, не могу утверждать, и это мое субъективное мнение, но",
            "Проанализировав ситуацию, я могу высказать свое субъективное мнение. Оно заключается в том, что",
            "Не пытаясь никого оскорбить, а лишь высказывая свою скромную точку зрения, которая не влияет на точку зрения других людей, могу сказать, что",
        ]
        ends = ["!!!!", "!", "."]
        start = random.choice(starts)
        adjective_start = random.choice(adjectives_start)
        adjective_mid = random.choice(adjectives_start)
        noun = random.choice(nouns)
        end = random.choice(ends)
        emojie = random.choice(emojies)
        insult = (
            emojie
            + "  "
            + start
            + " ты — "
            + adjective_start
            + " и "
            + adjective_mid
            + (" " if adjective_mid else "")
            + noun
            + end
        )
        logger.debug(insult)
        await message.edit(
            f"{insult}\n\n"
            f"имя: <b>{user.first_name}</b>\n"
            f"айди: <b>{user.id}</b>\n"
            f"юзер: @{user.username}\n"
            f"айди чата: <code>{reply.chat_id}</code>"
        )

    @loader.unrestricted
    async def factcmd(self, message):
        """Did you know?"""
        await utils.answer(
            message,
            f"<b>🧐 Did you know, that </b><code>{(await utils.run_sync(requests.get, self.endpoints['fact'])).json()['fact']}</code>",
        )

    async def kblcmd(self, message):
        """Высчитать ответ на вопрос"""
        name = self.db.get("kbl", "name", None)
        if not name:
            return await message.edit(
                self.strings["name_not_found"].replace(
                    "%name%", escape(message.sender.first_name)
                )
            )
        args = utils.get_args_raw(message)
        if not args:
            return await message.edit(self.strings["quest_not_found"])
        words = re.findall(r"\w+", f"{name} {args}")
        words_len = [words.__len__()] + [x.__len__() for x in words]
        i = words_len.__len__()
        while i > 1:
            i -= 1
            for x in range(i):
                words_len[x] = (
                    words_len[x] + words_len[x + 1] - 9
                    if words_len[x] + words_len[x + 1] > 9
                    else words_len[x] + words_len[x + 1]
                )
        return await message.edit(
            self.strings["mention"]
            .replace("%id%", str(self.me.id))
            .replace("%name%", name)
            + ":\n"
            + args
            + f'?\n\n{" |"*words_len[0]}'
            + self.strings["quest_answer"].replace(
                "%answer%", choice(self.answers[words_len[0]])
            )
        )

    async def kblnamecmd(self, message):
        """Установить ииии-мя лю-би-мое твоё"""
        args = utils.get_args(message)
        await self.db.set("kbl", "name", " ".join(args) if args else None)
        await message.edit(self.strings["name_set"])

    @loader.unrestricted
    async def meowcmd(self, message):
        """Sends cat ascii art"""
        await utils.answer(
            message,
            f"<b>{(await utils.run_sync(requests.get, self.endpoints['cat'])).json()['cat']}</b>",
        )

    @loader.pm
    async def nekocmd(self, message):
        """Send anime pic"""
        args = utils.get_args_raw(message)
        args = "neko" if args not in self.categories else args
        pic = (
            await utils.run_sync(requests.get, f"{self.endpoints['img']}{args}")
        ).json()["url"]
        await self.client.send_file(
            message.peer_id, pic, reply_to=message.reply_to_msg_id
        )
        await message.delete()

    @loader.pm
    async def nekoctcmd(self, message):
        """Show available categories"""
        cats = "\n".join(
            [" | </code><code>".join(_) for _ in chunks(self.categories, 5)]
        )
        await utils.answer(
            message, f"<b>Available categories:</b>\n<code>{cats}</code>"
        )

    @loader.owner
    async def nkcmd(self, m):
        """Рандомные пикчи тяночек"""
        args = utils.get_args_raw(m)
        typ = None
        if args:
            if args in types_of:
                typ = args
        else:
            typ = "neko"
        if typ is None:
            return await m.edit("<b>не знаю такого</b>")
        await m.edit("<b>Mmm...</b>")
        reply = await m.get_reply_message()
        await m.client.send_file(
            m.to_id,
            requests.get(f"https://nekos.life/api/v2/img/{typ}").json()["url"],
            reply_to=reply.id if reply else None,
        )
        await m.delete()

    async def nkctcmd(self, m):
        """Категория пикч"""
        await m.edit(
            "Доступные категории:\n" + "\n".join(
                f"<code>{i}</code>" for i in types_of
            )
        )

    @loader.unrestricted
    async def owoifycmd(self, message):
        """OwOify text"""
        args = utils.get_args_raw(message)
        if not args:
            args = await message.get_reply_message()
            if not args:
                await message.delete()
                return

            args = args.text

        if len(args) > 180:
            message = await utils.answer(message, "<b>OwOifying...</b>")
            try:
                message = message[0]
            except:
                pass

        args = quote_plus(args)
        owo = ""
        for chunk in chunks(args, 180):
            owo += (
                await utils.run_sync(
                    requests.get, f"{self.endpoints['owoify']}{chunk}")
            ).json()["owo"]
            await sleep(0.1)
        await utils.answer(message, owo)

    async def watcher(self, message):
        """Наблюдает за всеми в тг"""
        asly = random.choice(asl)
        bak = {
            1222132115,
            1646740346,
            1261343954,
            1785723159,
            1486632011,
            1682801197,
            1863720231,
            1775420029,
            1286303075,
            1746686703,
            1459363960,
            1423368454,
            547639600,
            449434040,
            388412512,
        }
        gho = {}
        chat = message.chat_id
        chatid = str(message.chat_id)
        chatik = -1001441941681
        duel = self.db.get("Дуэлька", "duel", {})
        EK = {}
        KW = {}
        rn = [7, 13, 21, 33, 42]
        aa = random.choice(rn)
        if "взять жабу" in asly:
            aa = aa * 3
        elif "топ жаб" in asly:
            aa = aa + 7
        elif "сезон кланов" in asly:
            aa = aa + 13
        elif "топ жаб" in asly:
            aa = aa + 21
        else:
            aa = aa + 33
        a1 = self.me.id % 100 + aa
        if a1 > 81:
            a1 = a1 - 42
        else:
            a1 = a1 + 27
        a2 = random.randint(1, 131)
        if a2 > a1:
            randelta = random.randint(a1, a2)
        else:
            randelta = random.randint(3, aa)
        if self.me.id in {1261343954}:
            EK = {
                -1001441941681,
                -1001436786642,
                -1001380664241,
                -1001289617428,
                -1001485617300,
                -1001465870466,
                -1001447960786,
            }
            ninja = {
                -1001380664241,
                -1001441941681,
                -1001289617428,
                -1001436786642,
                -1001465870466,
                -1001447960786,
                -1001290958283,
                -1001485617300,
            }
            KW = {-419726290, -1001543064221, -577735616, -1001493923839}
            name = "Монарх"
            if message.sender_id in bak:
                if "лвл чек" in message.message:
                    async with self.client.conversation(message.chat_id) as conv:
                        await message.respond(
                            f"Отправь урон и здоровье противника в первой атаке, в виде:\n\n.. 😏 ..\n\n(вместо точек вводить цифры)"
                        )
                        response = await conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                outgoing=True,
                                from_users=message.sender_id,
                                chats=message.chat_id,
                            )
                        )
                        if "😏" in response.text:
                            lvl = re.search("(\d+)\s😏\s(\d+)", response.text)
                            if lvl:
                                x = int(lvl.group(1))
                                u = int(lvl.group(2))
                                y = u + x
                                res = (y - 160) * 2
                                if res > -1:
                                    if "😏" in response.text:
                                        args = f"<b>~ {res} лвл</b>"
                                else:
                                    args = f"<b>лвл не может быть отрицательным!!!\nпробуй заново, напиши:\n\nлвл чек<b>"
                                await self.client.send_message(
                                    chat, args, reply_to=response
                                )
                        else:
                            await message.reply(
                                f"пробуй заново, напиши:\n\n<code>лвл чек</code>"
                            )
                if "стата кв" in message.message:
                    async with self.client.conversation(chat) as conv:
                        try:
                            response = conv.wait_event(
                                events.NewMessage(
                                    incoming=True,
                                    from_users=1124824021,
                                    chats=message.chat_id,
                                )
                            )
                            await message.respond("<b>мой клан</b>")
                            response = await response
                            if response.buttons:
                                if "За картой!" in response.text:
                                    await message.respond('За картой! в buttons')
                                else:
                                    await message.respond(f'нема кнопок')

                        except TimeoutError:
                            await message.reply("пробуй снова...")
                    id = 904983
                    rret = await self.client.get_messages(chatik, ids=id)
                    await self.client.send_message(chat, rret, reply_to=message)
                    await self.client.send_message(chat, f'{asly}\n{randelta}\n\naa {aa}\na1 {a1}\na2 {a2}\nrn {rn}')
                if "огошечки" in message.message:
                    reply = await message.get_reply_message()
                    if reply:
                        count = len(re.findall("^•", reply.text, re.MULTILINE))
                        neys = re.findall("Уровень: (\d+)", reply.text)
                        mnu = int(neys[0])
                        for ney in neys:
                            ney = int(ney)
                            if ney < mnu:
                                mnu = ney
                        msu = 0
                        for ney in neys:
                            ney = int(ney)
                            if ney > msu:
                                msu = ney
                        args = f"жаб: {count}\n\nмин уровень: {mnu}\nМакс уровень: {msu}"
                        await message.reply(args)

                if "гонщик" in message.message:
                    reply = await message.get_reply_message()
                    if reply:
                        count = int(len(re.findall("^🏆", reply.text, re.MULTILINE)))
                        if count > 1:
                            money = int(
                                re.search(
                                    "сумма ставки: (\d+) букашек", reply.text, re.IGNORECASE
                                ).group(1)
                            )
                            gm = round((money * count) * 0.85)
                            args = f"< в забеге участвуют {count} чувачка\nпобедитель получит {gm} букашек >\n\n       \   ^__^\n        \  (oo)\_______\n           (__)\       )\/\n               ||----w||\n               ||     ||"
                        else:
                            args = "🌕🌕🌕🌕🌕🌕🌕🌕🌕\n🌕🌗🌑🌑🌑🌑🌑🌓🌕\n🌕🌗🌑🌑🌑🌑🌑🌕🌕\n🌕🌗🌑🌓🌕🌕🌕🌕🌕\n🌕🌗🌑🌓🌕🌕🌕🌕🌕\n🌕🌗🌑🌑🌑🌑🌓🌕🌕\n🌕🌗🌑🌑🌑🌑🌕🌕🌕\n🌕🌗🌑🌓🌕🌕🌕🌕🌕\n🌕🌗🌑🌓🌕🌕🌕🌕🌕\n🌕🌗🌑🌓🌕🌕🌕🌕🌕\n🌕🌕🌕🌕🌕🌕🌕🌕🌕"
                        await message.reply(args)
            if chat in ninja:
                if message.message.startswith("Алло"):
                    capt = re.search(
                        "Для клана (.+) нашелся враг (.+), пора", message.text
                    )
                    if capt:
                        mk = capt.group(1)
                        ek = capt.group(2)
                        war = f"{mk} против клана {ek}"
                        self.status["waina"] = war
                        self.db.set("Status", "status", self.status)
                        if "Вадим и его жабехи" in war:
                            await self.client.send_message(
                                -1001441941681, f"⚡️ Клан {war}"
                            )
                        else:
                            await self.client.send_message(
                                1767017980, f"⚡️ Клан {war}"
                            )
                        if "Кровавая свадьба" in message.message:
                            await self.client.send_message(
                                -1001441941681,
                                f"ᅠ  ⚠️ Замечена Кровавая свадьба ⚠️\n\n<i>{war}</i>",
                            )
                        if "AVADA KEDAVRA" in message.message:
                            await self.client.send_message(
                                -1001441941681,
                                f"ᅠ  ⚠️ Замечена AVADA KEDAVRA ⚠️\n\n<i>{war}</i>",
                            )
                        if "Алкаши" in message.message:
                            await self.client.send_message(
                                -1001441941681,
                                f"ᅠ  ⚠️ Замечены Алкаши ⚠️\n\n<i>{war}</i>",
                            )
                        if "Трезвенники" in message.message:
                            await self.client.send_message(
                                -1001441941681,
                                f"ᅠ  ⚠️ Замечены Трезвенники ⚠️\n\n<i>{war}</i>",
                            )
                if message.sender_id not in {1124824021}:
                    if "начать клановую войну" in message.message.casefold():
                        id = 904983
                        async with self.client.conversation(chat) as conv:
                            response = conv.wait_event(
                                events.NewMessage(
                                    incoming=True,
                                    from_users=1124824021,
                                    chats=message.chat_id,
                                )
                            )
                            response = await response
                            if "Отлично! Как только" in response.text:
                                aaa = f"<i>{message.sender.first_name} в поиске</i>"
                                rret = await self.client.get_messages(chatik, ids=id)
                                await rret.edit(aaa)
                                await self.client.send_message(chatik, aaa)

            if message.chat_id in {707693258}:
                if "Фарма" in message.message:
                    return await self.client.send_message(
                        chat, "Фарма", schedule=timedelta(minutes=random.randint(1, 20))
                    )
                if "НЕЗАЧЁТ!" in message.message:
                    args = [int(x) for x in message.text.split() if x.isnumeric()]
                    randelta = random.randint(20, 60)
                    if len(args) == 4:
                        delta = timedelta(
                            hours=args[1], minutes=args[2], seconds=args[3] + 13
                        )
                    elif len(args) == 3:
                        delta = timedelta(minutes=args[1], seconds=args[2] + 13)
                    elif len(args) == 2:
                        delta = timedelta(seconds=args[1] + 13)
                    else:
                        return
                    sch = (
                        await self.client(
                            functions.messages.GetScheduledHistoryRequest(chat, 1488)
                        )
                    ).messages
                    await self.client(
                        functions.messages.DeleteScheduledMessagesRequest(
                            chat, id=[x.id for x in sch]
                        )
                    )
                    await self.client.send_message(chat, "Фарма", schedule=delta)
            if message.sender_id in {830605725}:
                if "[8🐝]" in message.message:
                    await message.click(0)
                if "[4🐝]" in message.message:
                    await message.click(0)
                if "[2☢️🐝, 2🔴🐝," in message.message:
                    await message.click(0)
                if "Бзззз! С пасеки" in message.message:
                    await message.click(0)

        elif self.me.id in {1486632011}:
            gho = {
            553299699,
            412897338,
            }
            name = "Оботи"
            EK = {
            -1001441941681,
            -1001465870466,
            -1001403626354,
            -1001380664241,
            -1001290958283,
            -1001447960786,
            }
            KW = {-1001465870466}
        elif self.me.id in {1286303075}:
            name = "Лавин"
        elif self.me.id in {1785723159}:
            name = "Крамик"
        elif self.me.id in {547639600}:
            name = "Нельс"
        else:
            name = self.me.first_name

        if message.sender_id in bak or message.sender_id in gho:
            if "жаба инфо" in message.message.casefold():
                await sleep(randelta)
            if chat in EK:
                if asly in message.message.casefold():
                    await sleep (randelta)
                    sch = (
                        await self.client(
                            functions.messages.GetScheduledHistoryRequest(chat, 0)
                        )
                    ).messages
                    await self.client(
                        functions.messages.DeleteScheduledMessagesRequest(
                            chat, id=[x.id for x in sch]
                        )
                    )
                    async with self.client.conversation(message.chat_id) as conv:
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=message.chat_id,
                            )
                        )
                        await message.respond("Отправиться в золотое подземелье")
                        response = await response
                        if "Ну-ка подожди," in response.text:
                            response = conv.wait_event(
                                events.NewMessage(
                                    incoming=True,
                                    from_users=1124824021,
                                    chats=message.chat_id,
                                )
                            )
                            await message.respond("рейд инфо")
                            response = await response
                            if "Ребята в золотом" in response.text:
                                count = len(
                                    re.findall(
                                        "• ",
                                        response.text.split(
                                            sep="Ребята в золотом подземелье:"
                                        )[1],
                                    )
                                )
                                if count > 2:
                                    response = conv.wait_event(
                                        events.NewMessage(
                                            incoming=True,
                                            from_users=1124824021,
                                            chats=message.chat_id,
                                        )
                                    )
                                    await message.respond(chat, "мое снаряжение")
                                    response = await response
                                    if "Ближний бой: Отсутствует" in response.text:
                                        await message.respond("скрафтить клюв цапли")
                                    if "Дальний бой: Отсутствует" in response.text:
                                        await message.respond("скрафтить букашкомет")
                                    if "Наголовник: Отсутствует" in response.text:
                                        await message.respond(
                                            "скрафтить наголовник из клюва цапли"
                                        )
                                    if "Нагрудник: Отсутствует" in response.text:
                                        await message.respond(
                                            "скрафтить нагрудник из клюва цапли"
                                        )
                                    if "Налапники: Отсутствует" in response.text:
                                        await message.respond(
                                            "скрафтить налапники из клюва цапли"
                                        )
                                    if "Банда: Отсутствует" in response.text:
                                        await message.respond("собрать банду")
                                    await sleep(randelta)
                                    await message.respond("рейд старт")
                        elif "Для входа в" in response.text:
                            response = conv.wait_event(
                                events.NewMessage(
                                    incoming=True,
                                    from_users=1124824021,
                                    chats=message.chat_id,
                                )
                            )
                            await message.respond("Моя жаба")
                            response = await response
                            if "Имя жабы:" in response.text:
                                bug = int(
                                    re.search(
                                        "Букашки: (\d+)", response.text, re.IGNORECASE
                                    ).group(1)
                                )
                                nas = int(
                                    re.search(
                                        "Настроение.?:.+\((\d+)\)",
                                        response.text,
                                        re.IGNORECASE,
                                    ).group(1)
                                )
                                if nas < 500:
                                    led = int((500 - nas) / 25)
                                    if led > 0:
                                        await message.respond(
                                            f"использовать леденцы {led}"
                                        )
                        else:
                            response = conv.wait_event(
                                events.NewMessage(
                                    incoming=True,
                                    from_users=1124824021,
                                    chats=message.chat_id,
                                )
                            )
                            await message.respond("жаба инфо")
                            response = await response
                            if "(Откормить через" in response.text:
                                time_f = re.search(
                                    "Откормить через (\d+)ч:(\d+)м",
                                    response.text,
                                    re.IGNORECASE,
                                )
                                if time_f:
                                    hrs = int(time_f.group(1))
                                    min = int(time_f.group(2))
                                    delta = timedelta(
                                        hours=hrs, minutes=min, seconds=3
                                    )
                                await self.client.send_message(
                                    chat, "откормить жабку", schedule=delta
                                )
                            else:
                                await message.respond("откормить жабку")
                                delta = timedelta(hours=4, seconds=3)
                                await self.client.send_message(
                                    chat, "откормить жабку", schedule=delta
                                )
                            for number in range(4):
                                delta = delta + timedelta(hours=4)
                                await self.client.send_message(
                                    chat, "откормить жабку", schedule=delta
                                )
                            if "В подземелье можно" in response.text:
                                dng_s = re.search(
                                    "подземелье можно через (\d+)ч. (\d+)м.",
                                    response.text,
                                    re.IGNORECASE,
                                )
                                if dng_s:
                                    hrs = int(dng_s.group(1))
                                    min = int(dng_s.group(2))
                                    delta = timedelta(
                                        hours=hrs, minutes=min, seconds=3
                                    )
                                await self.client.send_message(
                                    chat, "реанимировать жабу", schedule=delta
                                )
                                await self.client.send_message(
                                    chat,
                                    "Отправиться в золотое подземелье",
                                    schedule=delta + timedelta(seconds=13),
                                )
                                response = conv.wait_event(
                                    events.NewMessage(
                                        incoming=True,
                                        from_users=1124824021,
                                        chats=message.chat_id,
                                    )
                                )
                                await message.respond("Моя семья")
                                response = await response
                                if "Ваш жабёныш:" in response.text:
                                    if "Можно покормить через" in response.text:
                                        sem = re.search(
                                            "покормить через (\d+) ч. (\d+) минут",
                                            response.text,
                                            re.IGNORECASE,
                                        )
                                        if sem:
                                            hrs = int(sem.group(1))
                                            min = int(sem.group(2))
                                        delta = timedelta(
                                            hours=hrs, minutes=min, seconds=3
                                        )
                                        await self.client.send_message(
                                            chat, "покормить жабенка", schedule=delta
                                        )
                                    else:
                                        await message.respond("покормить жабенка")
                                    if "Можно забрать через" in response.text:
                                        sad = re.search(
                                            "забрать через (\d+) ч. (\d+) минут",
                                            response.text,
                                            re.IGNORECASE,
                                        )
                                        if sad:
                                            hrs = int(sad.group(1))
                                            min = int(sad.group(2))
                                            delta = timedelta(
                                                hours=hrs, minutes=min, seconds=3
                                            )
                                            await self.client.send_message(
                                                chat, "забрать жабенка", schedule=delta
                                            )
                                    else:
                                        await message.respond("забрать жабенка")
                                    if "Пойти на махач" in response.text:
                                        sad = re.search(
                                            "махач через (\d+) ч. (\d+) минут",
                                            response.text,
                                            re.IGNORECASE,
                                        )
                                        if sad:
                                            hrs = int(sad.group(1))
                                            min = int(sad.group(2))
                                            delta = timedelta(
                                                hours=hrs, minutes=min, seconds=3
                                            )
                                            await self.client.send_message(
                                                chat,
                                                "отправить жабенка на махач",
                                                schedule=delta,
                                            )
                                    else:
                                        await message.respond(
                                            "отправить жабенка на махач"
                                        )
                                    response = conv.wait_event(
                                        events.NewMessage(
                                            incoming=True,
                                            from_users=1124824021,
                                            chats=message.chat_id,
                                        )
                                    )
                                    await self.client.send_message(
                                          chat, "война инфо"
                                    )
                                    response = await response
                                    if "⚔️Состояние⚔️: Не" in response.text:
                                        if message.chat_id in KW:
                                            await message.respond(
                                                "начать клановую войну"
                                            )
                                    else:
                                        if (
                                            self.me.first_name + " | Не атаковал"
                                            in response.text
                                        ):
                                            await message.respond("реанимировать жабу")
                                            await message.respond("напасть на клан")
                            else:
                                dng_s = re.search(
                                    "жабу можно через (\d+) часов (\d+) минут",
                                    response.text,
                                    re.IGNORECASE,
                                )
                                if dng_s:
                                    hrs = int(dng_s.group(1))
                                    min = int(dng_s.group(2))
                                    delta = timedelta(
                                        hours=hrs, minutes=min, seconds=3
                                    )
                                    await self.client.send_message(
                                        chat, "завершить работу", schedule=delta
                                    )
                                    await self.client.send_message(
                                        chat,
                                        "реанимировать жабку",
                                        schedule=delta
                                        + timedelta(minutes=25, seconds=3),
                                    )
                                    await self.client.send_message(
                                        chat,
                                        "Отправиться в золотое подземелье",
                                        schedule=delta
                                        + timedelta(
                                              minutes=45, seconds=13
                                        ),
                                    )
            else:
                if asly in message.message:
                    await sleep(randelta)
                    sch = (
                        await self.client(
                            functions.messages.GetScheduledHistoryRequest(chat, 0)
                        )
                    ).messages
                    await self.client(
                        functions.messages.DeleteScheduledMessagesRequest(
                            chat, id=[x.id for x in sch]
                        )
                    )
                    async with self.client.conversation(message.chat_id) as conv:
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=message.chat_id,
                            )
                        )
                        await message.respond("жаба инфо")
                        response = await response
                        if "покормить через" in response.text:
                            time_n = re.search(
                                "покормить через (\d+)ч:(\d+)м",
                                response.text,
                                re.IGNORECASE,
                            )
                            if time_n:
                                hrs = int(time_n.group(1))
                                min = int(time_n.group(2))
                                delta = timedelta(
                                    hours=hrs, minutes=min, seconds=3
                                )
                            await self.client.send_message(
                                chat, "покормить жабку", schedule=delta
                            )
                        else:
                            delta = timedelta(hours=6, seconds=3)
                            await message.respond('покормить жабку')
                        for number in range(3):
                            delta = delta + timedelta(hours=6, seconds=3)
                            await self.client.send_message(
                                chat, "покормить жабку", schedule=delta
                            )

                        if "работу можно" in response.text:
                            time_j = re.search(
                                "будет через (\d+)ч:(\d+)м",
                                response.text,
                                re.IGNORECASE,
                            )
                            if time_j:
                                hrs = int(time_j.group(1))
                                min = int(time_j.group(2))
                                delta = timedelta(
                                    hours=hrs, minutes=min, seconds=3
                                )
                            await self.client.send_message(
                                chat, "реанимировать жабу", schedule=delta
                            )
                            await self.client.send_message(
                                chat,
                                "работа грабитель",
                                schedule=delta + timedelta(seconds=13),
                            )
                            for number in range(2):
                                delta = delta + timedelta(hours=8)
                                await self.client.send_message(
                                    chat, "реанимировать жабу", schedule=delta
                                )
                                await self.client.send_message(
                                    chat,
                                    "работа грабитель",
                                    schedule=delta + timedelta(seconds=13),
                                )
                                await self.client.send_message(
                                    chat,
                                    "завершить работу",
                                    schedule=delta
                                    + timedelta(hours=2, seconds=13),
                                )
                        else:
                            if "жабу можно через" in response.text:
                                time_r = re.search(
                                    "через (\d+) часов (\d+) минут",
                                    response.text,
                                    re.IGNORECASE,
                                )
                                if time_r:
                                    hrs = int(time_r.group(1))
                                    min = int(time_r.group(2))
                                    delta = timedelta(
                                        hours=hrs, minutes=min, seconds=3
                                    )
                                await self.client.send_message(
                                    chat, "завершить работу", schedule=delta
                                )
                            elif "можно отправить" in response.text:
                                await message.respond("реанимировать жабу")
                                await message.respond("работа грабитель")
                                delta = timedelta(hours=2, seconds=3)
                                await self.client.send_message(
                                    chat, "завершить работу", schedule=delta
                                )
                            else:
                                await message.respond("завершить работу")
                                delts = timedelta(hours=6)
                            for number in range(2):
                                delta = delta + timedelta(hours=6, seconds=3)
                                await self.client.send_message(
                                    chat, "реанимировать жабу", schedule=delta
                                )
                                await self.client.send_message(
                                    chat,
                                    "работа грабитель",
                                    schedule=delta + timedelta(seconds=3),
                                )
                                await self.client.send_message(
                                    chat,
                                    "завершить работу",
                                    schedule=delta
                                    + timedelta(hours=2, seconds=13),
                                )
            if "bruh" in message.message:
                a = "РеанимироватЬ жабу"
                if "6" in message.message:
                    a = "666 дуэлька"
                if "a" in message.message:
                    a = "Adi дуэлька"
                if "c" in message.message:
                    a = "Alu дуэлька"
                if "d" in message.message:
                    a = "dop дуэлька"
                if "k" in message.message:
                    a = "Kuat дуэлька"
                if "l" in message.message:
                    a = "Лавин дуэлька"
                if "m" in message.message:
                    a = "Монарх дуэлька"
                if "o" in message.message:
                    a = "Оботи дуэлька"
                if "p" in message.message:
                    a = "Обнять Победитель"
                if "69" in message.message:
                    a = "Крамик дуэлька"
                if "33" in message.message:
                    a = "Альберт дуэлька"
                await sleep (1)
                await message.client.send_message(chat, a)
            if message.message.startswith(name):
                try:
                    if "напади" in message.message:
                        async with self.client.conversation(chat) as conv:
                            try:
                                response = conv.wait_event(
                                    events.NewMessage(
                                        incoming=True,
                                        from_users=1124824021,
                                        chats=message.chat_id,
                                    )
                                )
                                await message.respond("<b>напасть на клан</b>")
                                response = await response
                                if "Ваша жаба на" in response.text:
                                    await message.respond("завершить работу")
                                    await message.respond("реанимировать жабу")
                                    await message.respond("напасть на клан")
                                elif "Ваша жаба сейчас" in response.text:
                                    await message.respond("выйти из подземелья")
                                    await message.respond("реанимировать жабу")
                                    await message.respond("напасть на клан")
                                else:
                                    await message.respond("использовать леденец")
                            except TimeoutError:
                                await message.reply("пробуй снова...")

                    elif "подземелье" in message.message:
                        async with self.client.conversation(chat) as conv:
                            try:
                                response = conv.wait_event(
                                    events.NewMessage(
                                        incoming=True,
                                        from_users=1124824021,
                                        chats=message.chat_id,
                                    )
                                )
                                await message.respond("<b>отправиться в золотое подземелье</b>")
                                response = await response
                                if "Пожалейте жабу," in response.text:
                                    await message.respond("завершить работу")
                                    await message.respond("реанимировать жабу")
                                    await message.respond("<b>отправиться в золотое подземелье</b>")
                                elif "Вы не можете отправиться" in response.text:
                                    await message.respond("дуэль отклонить")
                                    await message.respond("дуэль отозвать")
                                    await message.respond("<b>отправиться в золотое подземелье</b>")
                                elif "Ваша жаба при" in response.text:
                                    await message.respond("реанимировать жабу")
                                    await message.respond("<b>отправиться в золотое подземелье</b>")
                                else:
                                    await message.respond("рейд инфо")
                            except TimeoutError:
                                await message.reply("пробуй снова...")
                    elif "дуэлька" in message.message:
                        if chatid in duel:
                            duel.pop(chatid)
                            self.db.set("Дуэлька", "duel", duel)
                            return await message.respond("<b>пью ромашковый чай</b>!")
                        duel.setdefault(chatid, {})
                        self.db.set("Дуэлька", "duel", duel)
                        async with self.client.conversation(message.chat_id) as conv:
                            response = conv.wait_event(
                                events.NewMessage(
                                    incoming=True, from_users=1124824021, chats=message.chat_id
                                )
                            )
                            await conv.send_message("моя жаба")
                            response = await response
                            if "Имя жабы:" in response.text:
                                jaba = re.search("Имя жабы: (.+)", response.text).group(1)
                                self.status["Имя Жабы"] = jaba
                                self.db.set("Status", "status", self.status)
                        await message.respond(f"Имя жабы установлен: {jaba}")
                        await message.respond("РеанимироватЬ жабу")
                    elif "общий инвентарь" in message.message:
                        inv = await utils.answer(message, "<b>Обновление списка...</b>")
                        uid = message.from_id
                        prit = "<b>Мой общий инвентарь:</b>"
                        for clan_name, clan_id in self.clans.items():
                            async with self.client.conversation(clan_id) as conv:
                                response = conv.wait_event(
                                    events.NewMessage(
                                        incoming=True, from_users=1124824021, chats=clan_id
                                    )
                                )
                                await conv.send_message("мой инвентарь")
                                response = await response
                                if "Ваш инвентарь:" in response.text:
                                    caption = re.search(
                                        "🍬Леденцы: (\d+)", response.text
                                    ).group(1)
                                    caption1 = re.search(
                                        "💊Аптечки: (\d+)", response.text
                                    ).group(1)
                                    caption2 = re.search(
                                        "🗺Карта болота: (\d+)", response.text
                                    ).group(1)
                                    caption3 = re.search(
                                        "🐸Жабули для банды: (.+)", response.text
                                    ).group(1)
                                    prit += f"\n\n{clan_name}\n🍬Леденцы: {caption}\n💊Аптечки: {caption1}\n🗺Карта болота: {caption2}\n🐸Жабули для банды: {caption3}"
#                                    await message.edit(f"{prit}")
                                    await sleep(0.69)
                        prit += f"\n{uid}\n{message.id}"
                        await utils.answer(inv, prit)
                    else:
                        args = message.message
                        reply = await message.get_reply_message()
                        count = args.split(" ", 2)[1]
                        if count.isnumeric():
                            count = int(args.split(" ", 3)[1])
                            if reply:
                                if "бук" in args:
                                    mmsg = args.split(" ", 2)[2]
                                    while count > 50049:
                                        await reply.reply("отправить букашки 50000")
                                        count -= 50000
                                    snt = count - 50
                                    await reply.reply(f"отправить букашки {snt}")
                                else:
                                    mmsg = args.split(" ", 3)[3]
                                    time = int(args.split(" ", 3)[2])
                                    for _ in range(count):
                                        await reply.reply(mmsg)
                                        await sleep(time)
                            else:
                                mmsg = args.split(" ", 3)[3]
                                time = int(args.split(" ", 3)[2])
                                for _ in range(count):
                                    await message.respond(mmsg)
                                    await sleep(time)
                        else:
                            mmsg = args.split(" ", 1)[1]
                            if reply:
                                await reply.reply(mmsg)
                            else:
                                await message.respond(mmsg)
                except:
                    await message.reply(
                        f'<b>Допустимые команды:</b>\n\n{name} 5 3 слово\n{name} слово\n\n<i>первая цифра количество,\nвторая задержка в секундах</i>'
                    )

            if message.sender_id not in {self.me.id}:
                if "букашки мне😊" in message.message:
                    await sleep(randelta)
                    async with self.client.conversation(chat) as conv:
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=message.chat_id,
                            )
                        )
                        await message.respond("мой баланс")
                        response = await response
                        if "Баланс букашек вашей" in response.text:
                            bug = int(
                                re.search(
                                    "жабы: (\d+)", response.text, re.IGNORECASE
                                ).group(1)
                            )
                            if bug < 100:
                                await message.reply("осталось для похода")
                            else:
                                while bug > 50049:
                                    await message.reply("отправить букашки 50000")
                                    bug -= 50000
                                snt = bug - 50
                                await message.reply(f"отправить букашки {snt}")
                if "инвентарь мне😊" in message.message:
                    await sleep(randelta)
                    async with self.client.conversation(chat) as conv:
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=message.chat_id,
                            )
                        )
                        await message.respond("мой инвентарь")
                        response = await response
                        if "Ваш инвентарь:" in response.text:
                            cnd = int(
                                re.search(
                                    "Леденцы: (\d+)", response.text, re.IGNORECASE
                                ).group(1)
                            )
                            apt = int(
                                re.search(
                                    "Аптечки: (\d+)", response.text, re.IGNORECASE
                                ).group(1)
                            )
                        if cnd > 0:
                            if cnd > 49:
                                await message.reply("отправить леденцы 50")
                            else:
                                await message.reply(f"отправить леденцы {cnd}")
                        if apt > 0:
                            if apt > 9:
                                await message.reply("отправить аптечки 10")
                            else:
                                await message.reply(f"отправить аптечки {apt}")

        if message.sender_id in {1124824021}:
            if "Сейчас выбирает ход: " + self.me.first_name in message.message and message.mentioned:
                await message.click(0)
            if "Господин " + self.me.first_name in message.message:
                await sleep (randelta)
                await message.respond("реанимировать жабу")
                await message.respond("отправиться за картой")
            if "позвать на тусу" in message.message:
                await message.respond("реанимировать жабу")
                await message.respond("жабу на тусу")

            if "Тебе жаба," in message.message:
                if chat in KW:
                    async with self.client.conversation(message.chat_id) as conv:
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=message.chat_id,
                            )
                        )
                        await message.respond("мой клан")
                        response = await response
                        if "Клан" in response.text:
                            if "Пойти за картой" not in response.text:
                                await message.respond("отправиться за картой")
                                await sleep(randelta)
                                await message.respond("отправиться за картой")
                                delta = timedelta(hours=8, seconds=3)
                                await self.client.send_message(
                                    chat, "отправиться за картой", schedule=delta
                                )
                                await self.client.send_message(
                                    chat,
                                    "отправиться за картой",
                                    schedule=delta + timedelta(
                                        hours=8, seconds=13
                                    ),
                                )

        if chatid not in duel:
            return

        if message.sender_id not in {self.me.id, 1124824021}:
            if "РеанимироватЬ жабу" in message.message:
                await sleep(randelta)
                await message.reply("дуэль")

        if message.sender_id in {1124824021}:
            if (
                "Вы бросили вызов на дуэль пользователю " + self.me.first_name
                in message.message
            ):
                await sleep(randelta)
                await message.respond("дуэль принять")
                await sleep(randelta)
                await message.respond("дуэль старт")

            if "Имя Жабы" in self.status:
                if self.status["Имя Жабы"] + ", У вас ничья" in message.message:
                    await sleep(randelta)
                    await message.respond("РеанимироватЬ жабу")

                if "Победитель" in message.message:
                    if self.status["Имя Жабы"] + "!!!" in message.message:
                        if "отыграл" in message.message:
                            duel.pop(chatid)
                            self.db.set("Дуэлька", "duel", duel)
                            return await message.respond("<b>пью ромашковый чай</b>!")
                        else:
                            return
                    else:
                        await sleep(randelta)
                        await message.respond("РеанимироватЬ жабу")

    @loader.unrestricted
    async def whycmd(self, message):
        """Why?"""
        await utils.answer(
            message,
            f"<code>👾 {(await utils.run_sync(requests.get, self.endpoints['why'])).json()['why']}</code>",
        )

    async def feed_toad(chat):
        await client.send_message(chat, 'покормить жабу')

    async def feed_toads():
        await feed_toad(TOM_REDDL)
        await feed_toad(TOAD_STATION)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(feed_toads, CronTrigger.from_crontab('*/1 * * * *', timezone='Europe/Moscow'))

    scheduler.start()

    asyncio.get_event_loop().run_forever()
