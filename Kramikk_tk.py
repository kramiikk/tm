from math import floor
from html import escape
from random import choice
from asyncio import sleep
from .. import loader, utils
from datetime import timedelta
from urllib.parse import quote_plus
from telethon.tl.types import Message
from telethon import events, functions, types, sync
import asyncio, datetime, inspect, io, json, logging, os, time, random, re, requests

logger = logging.getLogger(__name__)
asl = [
    "жаба дня",
    "топ жаб",
    "сезон кланов",
    "кланы",
    "взять жабу",
]
def register(cb):
    cb(KramikkMod())

@loader.tds
class KramikkMod(loader.Module):
    """Алина, я люблю тебя!"""

    answers = {
        0: ("Невнятен вопрос, хз, что отвечать",),
        1: ("Ответ тебе известен", "Ты знаешь лучше меня!", "Ответ убил!.."),
        2: ("Да", "Утвердительный ответ", "Ага"),
        3: ("Да, но есть помехи", "Может быть", "Вероятно", "Возможно", "Наверняка"),
        4: (
            "Знаю ответ, но не скажу",
            "Думай!",
            "Угадай-ка...",
            "Это загадка от Жака Фреско...",
        ),
        5: ("Нет", "Отрицательный ответ"),
        6: ("Обязательно", "Конечно", "Сто пудов", "Абсолютно", "Разумеется", "100%"),
        7: ("Есть помехи...", "Вряд ли", "Что-то помешает", "Маловероятно"),
        8: ("Да, но нескоро", "Да, но не сейчас!"),
        9: ("Нет, но пока", "Скоро!", "Жди!", "Пока нет"),
    }
    strings = {
        "name": "Kramikk",
        "update": "<b>обновление списка..</b>",
        "quest_answer": "\n\n<u>%answer%</u>",
        "mention": "<a href='tg://user?id=%id%'>%uname%</a>",
    }

    def __init__(self):
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        clans = {
            "Багoboty": -1001380664241,
            "Том Рэддл": -1001441941681,
            "Манулы и Зайчатки": -1001289617428,
            "Жаботорт": -1001436786642,
            ".": -1001409792751,
            "жабки нэлс(платон)": -1001165420047,
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
        }
        self.clans = clans
        self.client = client
        self.db = db
        self.me = await client.get_me()
        self.status = db.get("Status", "status", {})

    async def watcher(self, message):
        asly = random.choice(asl)
        bak = {
            1709411724,
            1261343954,
            1785723159,
            1486632011,
            547639600,
            449434040,
            388412512,
            553299699,
            412897338,
        }
        chat = message.chat_id
        chatid = str(chat)
        chatik = 1602929748
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
                -1001169549362,
                -1001543064221,
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

            if "лвл чек" in message.message and message.sender_id in bak:
                x = int(message.message.split(" ", 3)[2])
                u = int(message.message.split(" ", 3)[3])
                y = ((x + u) - 160) * 2
                if y > -1:
                    res = f"<b>~ {y} лвл</b>"
                else:
                    res = f"<b>лвл не может быть отрицательным!!!\nпробуй заново, напиши:\n\n<code>лвл чек 160 90</code></b>"
                await utils.answer(message, res)

            elif message.message.startswith("Алло") and chat in ninja and message.sender_id in {1124824021}:
                capt = re.search(
                    "Для клана (.+) нашелся враг (.+), пора", message.text
                )
                if capt:
                    mk = capt.group(1)
                    ek = capt.group(2)
                    war = f"{mk} против клана {ek}"
                    await self.client.send_message(1767017980, f"⚡️ Клан {war}")

            elif (message.message.startswith("Начать клановую") or message.message.startswith("начать клановую") or message.message.startswith("@tgtoadbot Начать клановую")) and chat in ninja:
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
                        ch = await message.client.get_entity(message.to_id)
                        await self.client.send_message(
                            1767017980,
                            f"<i>{message.sender.first_name} в поиске</i>\nчат: {ch.title}",
                        )

            elif "[8🐝]" in message.message and message.sender_id in {830605725}:
                await message.click(0)
            elif "[4🐝]" in message.message and message.sender_id in {830605725}:
                await message.click(0)
            elif "[2☢️🐝, 2🔴🐝," in message.message and message.sender_id in {830605725}:
                await message.click(0)
            elif "Бзззз! С пасеки" in message.message and message.sender_id in {830605725}:
                await message.click(0)

            elif "Фарма" in message.message and chat in {707693258}:
                await self.client.send_message(
                    chat, "Фарма", schedule=timedelta(minutes=random.randint(1, 20))
                )
            elif "НЕЗАЧЁТ!" in message.message and chat in {707693258}:
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
                    pass
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
            else:
                pass

        elif self.me.id in {1486632011}:
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
        elif self.me.id in {980699009}:
            chatik = -1001441941681
            name = "Лена"
        elif self.me.id in {1863720231}:
            name = "dop"
        elif self.me.id in {1709411724}:
            name = "moo"
        elif self.me.id in {1423368454}:
            name = "LEN"
        elif self.me.id in {1646740346}:
            name = "Kuat"
        elif self.me.id in {1682801197}:
            name = "666"
        elif self.me.id in {1746686703}:
            name = "Alu"
        elif self.me.id in {1459363960}:
            name = "Альберт"
        elif self.me.id in {547639600}:
            name = "Нельс"
        elif self.me.id in {887255479}:
            name = "Кира"
        else:
            name = self.me.first_name
        if (
            "Сейчас выбирает ход: " + self.me.first_name in message.message
            and message.mentioned and message.sender_id in {1124824021}
        ):
            await message.click(0)
        elif (
            "Господин " + self.me.first_name in message.message
            and message.mentioned and message.sender_id in {1124824021}
        ):
            await sleep(randelta)
            await utils.answer(message, "реанимировать жабу")
            await utils.answer(message, "отправиться за картой")

        elif (message.message.startswith(name) or message.message.endswith('😉')) and message.sender_id in bak:
            if "?" in message.message:
                uname = message.sender.first_name
                words = re.findall(r"\w+", f"{uname} {message.message}")
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
                await utils.answer(message,
                    self.strings["mention"]
                    .replace("%id%", str(message.sender_id))
                    .replace("%uname%", uname)
                    + ":\n"
                    + message.message
                    + f'\n\n{" |"*words_len[0]}'
                    + self.strings["quest_answer"].replace(
                        "%answer%", choice(self.answers[words_len[0]])
                    )
                )
            elif "напади" in message.message:
                async with self.client.conversation(chat) as conv:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    await utils.answer(message, "<b>напасть на клан</b>")
                    response = await response
                    if "Ваша жаба на" in response.text:
                        await utils.answer(message, 'завершить работу')
                        await utils.answer(message, 'реанимировать жабу')
                        await utils.answer(message, 'напасть на клан')
                    elif "Ваша жаба сейчас" in response.text:
                        await utils.answer(message, "выйти из подземелья")
                        await utils.answer(message, "реанимировать жабу")
                        await utils.answer(message, "напасть на клан")
                    else:
                        await utils.answer(message, "использовать леденец")
            elif "подземелье" in message.message:
                async with self.client.conversation(chat) as conv:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    await utils.answer(message,
                        "<b>отправиться в золотое подземелье</b>"
                    )
                    response = await response
                    if "Пожалейте жабу," in response.text:
                        await utils.answer(message, "завершить работу")
                        await utils.answer(message, "реанимировать жабу")
                        await utils.answer(message,
                            "<b>отправиться в золотое подземелье</b>"
                        )
                    elif "Вы не можете отправиться" in response.text:
                        await utils.answer(message, "дуэль отклонить")
                        await utils.answer(message, "дуэль отозвать")
                        await utils.answer(message,
                            "<b>отправиться в золотое подземелье</b>"
                        )
                    elif "Ваша жаба при" in response.text:
                        await utils.answer(message, "реанимировать жабу")
                        await utils.answer(message,
                            "<b>отправиться в золотое подземелье</b>"
                        )
                    else:
                        await utils.answer(message, "рейд инфо")
            elif "дуэлька" in message.message:
                if chatid in duel:
                    duel.pop(chatid)
                    self.db.set("Дуэлька", "duel", duel)
                    return await utils.answer(message, "<b>пью ромашковый чай</b>!")
                duel.setdefault(chatid, {})
                self.db.set("Дуэлька", "duel", duel)
                async with self.client.conversation(
                    message.chat_id
                ) as conv:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    await conv.send_message("моя жаба")
                    response = await response
                    if "Имя жабы:" in response.text:
                        jaba = re.search(
                            "Имя жабы: (.+)", response.text
                        ).group(1)
                        self.status["Имя Жабы"] = jaba
                        self.db.set("Status", "status", self.status)
                await utils.answer(message, f"Имя жабы установлен: {jaba}")
                await utils.answer(message, "РеанимироватЬ жабу")
            elif "общий инвентарь" in message.message:
                inv = await utils.answer(message, "<b>Обновление списка...</b>")
                uid = message.from_id
                prit = "<b>Мой общий инвентарь:</b>"
                for clan_name, clan_id in self.clans.items():
                    async with self.client.conversation(clan_id) as conv:
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=clan_id,
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
                            await sleep(0.69)
                prit += f"\n{uid}\n{message.id}"
                await utils.answer(inv, prit)
            else:
                args = message.message
                reply = await message.get_reply_message()
                count = args.split(" ", 2)[1]

                if count.isnumeric() and reply:
                    count = int(args.split(" ", 3)[1])
                    mmsg = args.split(" ", 3)[3]
                    time = int(args.split(" ", 3)[2])
                    for _ in range(count):
                        await reply.reply(mmsg)
                        await sleep(time)
                elif count.isnumeric():
                    count = int(args.split(" ", 3)[1])
                    mmsg = args.split(" ", 3)[3]
                    time = int(args.split(" ", 3)[2])
                    for _ in range(count):
                        await self.client.send_message(chat, mmsg)
                        await sleep(time)
                else:
                    mmsg = args.split(" ", 1)[1]
                    if reply:
                        await reply.reply(mmsg)
                    else:
                        await utils.answer(message, mmsg)
        elif "букашки мне😊" in message.message and message.sender_id in bak:
            await sleep(randelta)
            async with self.client.conversation(chat) as conv:
                response = conv.wait_event(
                    events.NewMessage(
                        incoming=True,
                        from_users=1124824021,
                        chats=message.chat_id,
                    )
                )
                await utils.answer(message, "мой баланс")
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
        elif "инвентарь мне😊" in message.message and message.sender_id in bak:
            await sleep(randelta)
            async with self.client.conversation(chat) as conv:
                response = conv.wait_event(
                    events.NewMessage(
                        incoming=True,
                        from_users=1124824021,
                        chats=message.chat_id,
                    )
                )
                await utils.answer(message, "мой инвентарь")
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
        elif message.message.startswith(asly) and chat in EK and message.sender_id in bak:
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
                await utils.answer(message, "Отправиться в золотое подземелье")
                response = await response
                if "Ну-ка подожди," in response.text:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    await utils.answer(message, "рейд инфо")
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
                            await utils.answer(message, "мое снаряжение")
                            response = await response
                            if "Ближний бой: Отсутствует" in response.text:
                                await utils.answer(message,
                                    "скрафтить клюв цапли"
                                )
                            if "Дальний бой: Отсутствует" in response.text:
                                await utils.answer(message,
                                    "скрафтить букашкомет"
                                )
                            if "Наголовник: Отсутствует" in response.text:
                                await utils.answer(message,
                                    "скрафтить наголовник из клюва цапли"
                                )
                            if "Нагрудник: Отсутствует" in response.text:
                                await utils.answer(message,
                                    "скрафтить нагрудник из клюва цапли"
                                )
                            if "Налапники: Отсутствует" in response.text:
                                await utils.answer(message,
                                    "скрафтить налапники из клюва цапли"
                                )
                            if "Банда: Отсутствует" in response.text:
                                await utils.answer(message, "собрать банду")
                            await sleep(randelta)
                            await utils.answer(message, "рейд старт")
                elif "Для входа в" in response.text:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    await utils.answer(message, "Моя жаба")
                    response = await response
                    if "Имя жабы:" in response.text:
                        bug = int(
                            re.search(
                                "Букашки: (\d+)",
                                response.text,
                                re.IGNORECASE,
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
                                await utils.answer(message,
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
                    await utils.answer(message, "жаба инфо")
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
                        await utils.answer(message, "откормить жабку")
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
                        await utils.answer(message, "Моя семья")
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
                                    chat,
                                    "покормить жабенка",
                                    schedule=delta,
                                )
                            else:
                                await utils.answer(message, "покормить жабенка")
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
                                        chat,
                                        "забрать жабенка",
                                        schedule=delta,
                                    )
                            else:
                                await utils.answer(message, "забрать жабенка")
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
                                await utils.answer(message,
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
                                    await utils.answer(message,
                                        "начать клановую войну"
                                    )
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
                                + timedelta(minutes=45, seconds=13),
                            )
        elif message.message.startswith(asly) and message.sender_id in bak:
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
                await utils.answer(message, "жаба инфо")
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
                        delta = timedelta(hours=hrs, minutes=min, seconds=3)
                    await self.client.send_message(
                        chat, "покормить жабку", schedule=delta
                    )
                else:
                    delta = timedelta(hours=6, seconds=3)
                    await utils.answer(message, "покормить жабку")
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
                        delta = timedelta(hours=hrs, minutes=min, seconds=3)
                    await self.client.send_message(
                        chat, "реанимировать жабу", schedule=delta
                    )
                    await self.client.send_message(
                        chat,
                        "работа крупье",
                        schedule=delta + timedelta(seconds=13),
                    )
                    for number in range(2):
                        delta = delta + timedelta(hours=8)
                        await self.client.send_message(
                            chat, "реанимировать жабу", schedule=delta
                        )
                        await self.client.send_message(
                            chat,
                            "работа крупье",
                            schedule=delta + timedelta(seconds=13),
                        )
                        await self.client.send_message(
                            chat,
                            "завершить работу",
                            schedule=delta + timedelta(hours=2, seconds=13),
                        )
                if "жабу можно через" in response.text:
                    time_r = re.search(
                        "через (\d+) часов (\d+) минут",
                        response.text,
                        re.IGNORECASE,
                    )
                    if time_r:
                        hrs = int(time_r.group(1))
                        min = int(time_r.group(2))
                        delta = timedelta(hours=hrs, minutes=min, seconds=3)
                    await self.client.send_message(
                        chat, "завершить работу", schedule=delta
                    )
                elif "можно отправить" in response.text:
                    await utils.answer(message, "реанимировать жабу")
                    await utils.answer(message, "работа крупье")
                    delta = timedelta(hours=2, seconds=3)
                    await self.client.send_message(
                        chat, "завершить работу", schedule=delta
                    )
                else:
                    await utils.answer(message, "завершить работу")
                    delta = timedelta(hours=6)
                for number in range(2):
                    delta = delta + timedelta(hours=6, seconds=3)
                    await self.client.send_message(
                        chat, "реанимировать жабу", schedule=delta
                    )
                    await self.client.send_message(
                        chat,
                        "работа крупье",
                        schedule=delta + timedelta(seconds=3),
                    )
                    await self.client.send_message(
                        chat,
                        "завершить работу",
                        schedule=delta + timedelta(hours=2, seconds=13),
                    )
        else:
            pass
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
                await utils.answer(message, "дуэль принять")
                await sleep(randelta)
                await utils.answer(message, "дуэль старт")
            if "Имя Жабы" in self.status:
                if self.status["Имя Жабы"] + ", У вас ничья" in message.message:
                    await sleep(randelta)
                    await utils.answer(message, "РеанимироватЬ жабу")

                if "Победитель" in message.message:
                    if self.status["Имя Жабы"] + "!!!" in message.message:
                        if "отыграл" in message.message:
                            duel.pop(chatid)
                            self.db.set("Дуэлька", "duel", duel)
                            await utils.answer(message,
                                "<b>пью ромашковый чай</b>!"
                            )
                        else:
                            pass
                    else:
                        await sleep(randelta)
                        await utils.answer(message, "РеанимироватЬ жабу")
