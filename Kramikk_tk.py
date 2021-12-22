from .. import loader, utils
from telethon.tl.types import *
from telethon import events, functions, types
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio, datetime, json, logging, time, random, re, requests

# requires: apscheduler

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
        "quest_answer": "<i>%answer%</i>",
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

        #
        # async def statacmd(m):
        #     ph = str((await client.get_messages(m, search='ваш клан Том Рэддл одержал')).total)
        #     vi = str((await client.get_messages(m, search='клана Том Рэддл нашелся враг Вадим')).total)
        #     await client.send_message(m,
        #         ("<i>Неполные сведения, часть сообщений чата скрытые</i>\n<b>🏆Том Рэддл одержал побед:</b> {}\n" +
        #          "<b>⚜️кв Рэддла с Вадимом:</b> {}\n").format(ph, vi))
        # async def feets():
        #     await statacmd(OPPY)
        # scheduler = AsyncIOScheduler()
        # scheduler.add_job(feets, CronTrigger.from_crontab('*/33 * * * *', timezone='Asia/Almaty'))
        # scheduler.start()
        # asyncio.get_event_loop().run_forever()

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
        ch = message.client.get_entity(message.to_id)
        chat = message.chat_id
        chatid = str(chat)
        chatik = 1602929748
        duel = self.db.get("Дуэлька", "duel", {})
        EK = {}
        KW = {}
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
        nr = [11, 13, 17, 24, 33]
        OPPY = -1001655814348
        rc = random.choice(nr)
        if "взять жабу" in asly:
            ac = rc * 3
        elif "топ жаб" in asly:
            ac = rc + 7
        elif "сезон кланов" in asly:
            ac = rc + 13
        elif "топ жаб" in asly:
            ac = rc + 21
        else:
            ac = rc + 33
        ai = self.me.id % 100 + ac
        if ai > 81:
            ai -= 42
        else:
            ai += 27
        ar = random.randint(1, 131)
        if ar > ai:
            randelta = random.randint(ai, ar)
        else:
            randelta = random.randint(3, ac)
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
                return await utils.answer(message, res)

            elif "[8🐝]" in message.message and message.sender_id in {830605725}:
                return await message.click(0)
            elif "[4🐝]" in message.message and message.sender_id in {830605725}:
                return await message.click(0)
            elif "[2☢️🐝, 2🔴🐝," in message.message and message.sender_id in {
                830605725
            }:
                return await message.click(0)
            elif "Бзззз! С пасеки" in message.message and message.sender_id in {
                830605725
            }:
                return await message.click(0)
            elif "Фарма" in message.message and chat in {707693258}:
                return await self.client.send_message(
                    chat,
                    "Фарма",
                    schedule=datetime.timedelta(minutes=random.randint(1, 20)),
                )
            elif "НЕЗАЧЁТ!" in message.message and chat in {707693258}:
                args = [int(x) for x in message.text.split() if x.isnumeric()]
                randelta = random.randint(20, 60)
                if len(args) == 4:
                    delta = datetime.timedelta(
                        hours=args[1], minutes=args[2], seconds=args[3] + 13
                    )
                elif len(args) == 3:
                    delta = datetime.timedelta(minutes=args[1], seconds=args[2] + 13)
                elif len(args) == 2:
                    delta = datetime.timedelta(seconds=args[1] + 13)
                else:
                    pass
                sch = (
                    await self.client(
                        functions.messages.GetScheduledHistoryRequest(
                            chat, 1488
                        )
                    )
                ).messages
                await self.client(
                    functions.messages.DeleteScheduledMessagesRequest(
                        chat, id=[x.id for x in sch]
                    )
                )
                return await self.client.send_message(
                    chat, "Фарма", schedule=delta
                )
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
            EK = {
                -1001441941681,
                -1001436786642,
                -1001380664241,
                -1001336641071,
                -1001515004936,
            }
        elif self.me.id in {1785723159}:
            name = "Крамик"
            EK = {-1001441941681}
            rc = 0.3
        elif self.me.id in {547639600}:
            name = "Нельс"
            EK = {-1001441941681}
            rc = 0.3
        elif self.me.id in {980699009}:
            name = "Лена"
            EK = {-1001441941681}
            rc = 0.3
        elif self.me.id in {1423368454}:
            name = "LEN"
        elif self.me.id in {1682801197}:
            name = "666"
        elif self.me.id in {230473666}:
            name = "Ваня"
            EK = {-1001441941681}
        elif self.me.id in {1863720231}:
            name = "dop"
        elif self.me.id in {1709411724}:
            name = "moo"
        elif self.me.id in {1646740346}:
            name = "Kuat"
        elif self.me.id in {1746686703}:
            name = "Alu"
        elif self.me.id in {1459363960}:
            name = "Альберт"
        elif self.me.id in {887255479}:
            name = "Кира"
        else:
            name = self.me.first_name
        if (
            f"Сейчас выбирает ход: {self.me.first_name}" in message.message
            and message.mentioned
            and message.sender_id in {1124824021}
        ):
            return await message.click(0)
        elif (
            f"Господин {self.me.first_name}" in message.message
            and message.mentioned
            and message.sender_id in {1124824021}
        ):
            await message.respond("реанимировать жабу")
            await asyncio.sleep(rc)
            return await message.respond("отправиться за картой")
        elif (
            message.message.startswith((name, f'@{self.me.username}'))
            or name in message.message
            and message.message.endswith("😉")
        ) and message.sender_id in bak:
            await asyncio.sleep(rc)
            if "?" in message.message:
                words = re.findall(r"\w+", f"{message.message}")
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
                return await message.reply(
                    self.strings["quest_answer"].replace(
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
                    await conv.send_message("напасть на клан")
                    response = await response
                    if "Ваша жаба на" in response.text:
                        await conv.send_message("завершить работу")
                        await conv.send_message("реанимировать жабу")
                        return await conv.send_message("напасть на клан")
                    elif "Ваша жаба сейчас" in response.text:
                        await conv.send_message("выйти из подземелья")
                        await conv.send_message("реанимировать жабу")
                        return await conv.send_message("напасть на клан")
                    else:
                        return
            elif "подземелье" in message.message:
                async with self.client.conversation(chat) as conv:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    await conv.send_message(
                        "отправиться в золотое подземелье"
                    )
                    response = await response
                    if "Пожалейте жабу," in response.text:
                        await conv.send_message("завершить работу")
                        await conv.send_message("реанимировать жабу")
                        return await conv.send_message(
                            "<b>отправиться в золотое подземелье</b>",
                        )
                    elif "Вы не можете отправиться" in response.text:
                        await conv.send_message("дуэль отклонить")
                        await conv.send_message("дуэль отозвать")
                        return conv.send_message(
                            "<b>отправиться в золотое подземелье</b>",
                        )
                    elif "Ваша жаба при" in response.text:
                        await conv.send_message("реанимировать жабу")
                        return await conv.send_message(
                            "<b>отправиться в золотое подземелье</b>",
                        )
                    else:
                        return
            elif "покажи инвентарь" in message.message:
                await message.respond("мой инвентарь")
            elif "го кв" in message.message:
                await message.respond("начать клановую войну")
            elif "реанимируй" in message.message:
                await message.respond("отправиться за картой")
            elif "снаряжение" in message.message:
                async with self.client.conversation(chat) as conv:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    await conv.send_message("мое снаряжение")
                    response = await response
                    if "Ближний бой: Отсутствует" in response.text:
                        await conv.send_message(
                            "скрафтить клюв цапли"
                        )
                    if "Дальний бой: Отсутствует" in response.text:
                        await conv.send_message(
                            "скрафтить букашкомет"
                        )
                    if "Наголовник: Отсутствует" in response.text:
                        await conv.send_message(
                            "скрафтить наголовник из клюва цапли",
                        )
                    if "Нагрудник: Отсутствует" in response.text:
                        await conv.send_message(
                            "скрафтить нагрудник из клюва цапли",
                        )
                    if "Налапники: Отсутствует" in response.text:
                        await conv.send_message(
                            "скрафтить налапники из клюва цапли",
                        )
                    if "Банда: Отсутствует" in response.text:
                        await conv.send_message("взять жабу")
                        response = await response
                        if "У тебя уже есть" in response.text:
                            await conv.send_message("собрать банду")
                        else:
                            return await conv.send_message(
                                "взять жабу",
                                schedule=datetime.timedelta(hours=2)
                            )
                    else:
                        return

            elif "дуэлька" in message.message:
                if chatid in duel:
                    duel.pop(chatid)
                    self.db.set("Дуэлька", "duel", duel)
                    return await utils.answer(
                        message, "<b>пью ромашковый чай</b>!"
                    )
                duel.setdefault(chatid, {})
                self.db.set("Дуэлька", "duel", duel)
                async with self.client.conversation(chat) as conv:
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
                        return await conv.send_message("РеанимироватЬ жабу")
                    else:
                        return
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
                        await asyncio.sleep(time)
                elif count.isnumeric():
                    count = int(args.split(" ", 3)[1])
                    mmsg = args.split(" ", 3)[3]
                    time = int(args.split(" ", 3)[2])
                    for _ in range(count):
                        await self.client.send_message(chat, mmsg)
                        await asyncio.sleep(time)
                elif "напиши в " in message.message:
                    count = args.split(" ", 4)[3]
                    if count.isnumeric():
                        count = int(args.split(" ", 4)[3])
                    mmsg = args.split(" ", 4)[4]
                    await self.client.send_message(count, mmsg)
                    return await self.client.send_message(1001714871513, f'{count} {mmsg} {chat}')
                elif "~" in message.message:
                    mmsg = args.split(" ", 2)[2]
                    await utils.answer(
                    message, "поехали"
                    )
                    for clan_name, clan_id in self.clans.items():
                        await self.client.send_message(
                        clan_id, mmsg
                        )
                else:
                    mmsg = args.split(" ", 2)[2]
                    if reply:
                        return await reply.reply(mmsg)
                    else:
                        return await utils.answer(message, mmsg)
        elif (
            message.message.startswith("Начать клановую")
            or message.message.startswith("начать клановую")
            or message.message.startswith("@tgtoadbot Начать клановую")
        ):
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
                    ch = await ch
                    return await self.client.send_message(
                        1521550234,
                        f"<i>{message.sender.first_name} в поиске</i>\nчат: {ch.title}",
                    )
                else:
                    return
        elif (
            message.message.startswith("Алло")
            and (message.sender_id in {1124824021} or message.sender_id in bak)
        ):
                if "Для клана" in message.message:
                    capt = re.search(
                        "Для клана (.+) нашелся враг (.+), пора", message.message
                    )
                    if capt:
                        mk = capt.group(1)
                        ek = capt.group(2)
                        war = f"{mk} против клана {ek}"
                        return await self.client.send_message(
                            1521550234, f"⚡️ Клан {war}"
                        )
                        ch = await ch
                        ph = await self.client.get_messages(1521550234, search="нелс🦎")
                    else:
                        return
                else:
                    return
        elif "stata kv" in message.message:
            args = message.message
            mmsg = args.split(" ", 2)[2]
            ch = await ch
            try:
                ms = await self.client.get_messages(1521550234, search=mmsg)
            except Exception as e:
                return await message.reply(f"[Searcher] {str(e.args)}")
            if ms.total == 0:
                return await message.reply("[Searcher] Данных по запросу нет")
            for i in ms:
                #await i.forward_to(message.to_id)
                await message.respond(i.message)
        elif (
            message.message.lower().startswith("мой клан")
            and chat in ninja
        ):
            async with self.client.conversation(chat) as conv:
                response = conv.wait_event(
                    events.NewMessage(
                        incoming=True,
                        from_users=1124824021,
                        chats=message.chat_id,
                    )
                )
                response = await response
                if "Опыт" in response.text:
                    ch = await ch
                    klan = re.search(
                        "Клан (.+):", response.text
                    ).group(1)
                    liga = re.search(
                        "Лига: (.+)", response.text
                    ).group(1)
                    usil = re.search(
                        "Усилитель: (.+)", response.text
                    ).group(1)
                    info = f"Чат: {ch.title}\nИмя: {message.sender.first_name}\nКлан: {klan}\nЛига: {liga}\nУсилитель: {usil}"
                    return await self.client.send_message(OPPY, info)
                else:
                    return
        elif "букашки мне😊" in message.message and message.sender_id in bak:
            await asyncio.sleep(randelta)
            async with self.client.conversation(chat) as conv:
                response = conv.wait_event(
                    events.NewMessage(
                        incoming=True,
                        from_users=1124824021,
                        chats=message.chat_id,
                    )
                )
                await conv.send_message("мой баланс")
                response = await response
                if "Баланс букашек вашей" in response.text:
                    bug = int(
                        re.search(
                            "жабы: (\d+)", response.text, re.IGNORECASE
                        ).group(1)
                    )
                    if bug < 100:
                        return await utils.answer(
                            message, "осталось для похода"
                        )
                    else:
                        while bug > 50049:
                            await utils.answer(
                                message, "отправить букашки 50000"
                            )
                            bug -= 50000
                        snt = bug - 50
                        return await utils.answer(
                            message, f"отправить букашки {snt}"
                        )
                else:
                    return
        elif "инвентарь мне😊" in message.message and message.sender_id in bak:
            await asyncio.sleep(randelta)
            async with self.client.conversation(chat) as conv:
                response = conv.wait_event(
                    events.NewMessage(
                        incoming=True,
                        from_users=1124824021,
                        chats=message.chat_id,
                    )
                )
                await conv.send_message("мой инвентарь")
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
                            await utils.answer(
                                message, "отправить леденцы 50"
                            )
                        else:
                            await utils.answer(
                                message, f"отправить леденцы {cnd}"
                            )
                    if apt > 0:
                        if apt > 9:
                            return await utils.answer(
                                message, "отправить аптечки 10"
                            )
                        else:
                            return await utils.answer(
                                message, f"отправить аптечки {apt}"
                            )
                    else:
                        return
                else:
                    return
        elif (
            message.message.startswith(asly)
            and chat in EK
            and message.sender_id in bak
        ):
            await asyncio.sleep(randelta)
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
                await conv.send_message("Отправиться в золотое подземелье")
                response = await response
                if "Ну-ка подожди," in response.text:
                    response = conv.wait_event(
                        events.NewMessage(
                            incoming=True,
                            from_users=1124824021,
                            chats=message.chat_id,
                        )
                    )
                    await conv.send_message("рейд инфо")
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
                            await asyncio.sleep(randelta)
                            return await conv.send_message("рейд старт")
                    else:
                        return
                elif "Для входа в" in response.text:
                    await conv.send_message("Моя жаба")
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
                                return await conv.send_message(
                                    f"использовать леденцы {led}"
                                )
                        else:
                            return
                    else:
                        return
                else:
                    await conv.send_message("жаба инфо")
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
                            delta = datetime.timedelta(
                                hours=hrs, minutes=min, seconds=3
                            )
                            await conv.send_message(
                                "откормить жабку", schedule=delta
                            )
                    else:
                        await conv.send_message("откормить жабку")
                        delta = datetime.timedelta(hours=4, seconds=3)
                        await conv.send_message(
                            "откормить жабку", schedule=delta
                        )
                    for number in range(4):
                        delta = delta + datetime.timedelta(hours=4)
                        await conv.send_message(
                            "откормить жабку", schedule=delta
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
                            delta = datetime.timedelta(
                                hours=hrs, minutes=min, seconds=3
                            )
                            await conv.send_message(
                                "реанимировать жабу", schedule=delta
                            )
                            await conv.send_message(
                                "Отправиться в золотое подземелье",
                                schedule=delta + datetime.timedelta(seconds=13),
                            )
                        response = conv.wait_event(
                            events.NewMessage(
                                incoming=True,
                                from_users=1124824021,
                                chats=message.chat_id,
                            )
                        )
                        await conv.send_message("Моя семья")
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
                                delta = datetime.timedelta(
                                    hours=hrs, minutes=min, seconds=3
                                )
                                await conv.send_message(
                                    "покормить жабенка",
                                    schedule=delta,
                                )
                            else:
                                await conv.send_message("покормить жабенка")
                            if "Можно забрать через" in response.text:
                                sad = re.search(
                                    "забрать через (\d+) ч. (\d+) минут",
                                    response.text,
                                    re.IGNORECASE,
                                )
                                if sad:
                                    hrs = int(sad.group(1))
                                    min = int(sad.group(2))
                                    delta = datetime.timedelta(
                                        hours=hrs, minutes=min, seconds=3
                                    )
                                    await conv.send_message(
                                        "забрать жабенка",
                                        schedule=delta,
                                    )
                            else:
                                await conv.send_message(
                                    "забрать жабенка"
                                )
                            if "Пойти на махач" in response.text:
                                sad = re.search(
                                    "махач через (\d+) ч. (\d+) минут",
                                    response.text,
                                    re.IGNORECASE,
                                )
                                if sad:
                                    hrs = int(sad.group(1))
                                    min = int(sad.group(2))
                                    delta = datetime.timedelta(
                                        hours=hrs, minutes=min, seconds=3
                                    )
                                    await conv.send_message(
                                        "отправить жабенка на махач",
                                        schedule=delta,
                                    )
                            else:
                                await conv.send_message(
                                    "отправить жабенка на махач"
                                )
                        await conv.send_message("война инфо")
                        response = await response
                        if "⚔️Состояние⚔️: Не" in response.text:
                            if message.chat_id in KW:
                                return await conv.send_message(
                                    "начать клановую войну"
                                )
                        else:
                            return
                    else:
                        dng_s = re.search(
                            "жабу можно через (\d+) часов (\d+) минут",
                            response.text,
                            re.IGNORECASE,
                        )
                        if dng_s:
                            hrs = int(dng_s.group(1))
                            min = int(dng_s.group(2))
                            delta = datetime.timedelta(
                                hours=hrs, minutes=min, seconds=3
                            )
                            await conv.send_message(
                                "завершить работу", schedule=delta
                            )
                            await conv.send_message(
                                "реанимировать жабку",
                                schedule=delta
                                + datetime.timedelta(minutes=25, seconds=3),
                            )
                            return await conv.send_message(
                                "Отправиться в золотое подземелье",
                                schedule=delta
                                + datetime.timedelta(minutes=45, seconds=13),
                            )
                        else:
                            return
        elif message.message.startswith(asly) and message.sender_id in bak:
            await asyncio.sleep(randelta)
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
                await conv.send_message("жаба инфо")
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
                        delta = datetime.timedelta(hours=hrs, minutes=min, seconds=3)
                        await conv.send_message(
                            "покормить жабку", schedule=delta
                        )
                else:
                    delta = datetime.timedelta(hours=6, seconds=3)
                    await conv.send_message("покормить жабку")
                for number in range(3):
                    delta = delta + datetime.timedelta(hours=6, seconds=3)
                    await conv.send_message(
                        "покормить жабку", schedule=delta
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
                        delta = datetime.timedelta(hours=hrs, minutes=min, seconds=3)
                        await conv.send_message(
                            "реанимировать жабу", schedule=delta
                        )
                        await conv.send_message(
                            "работа крупье",
                            schedule=delta + datetime.timedelta(seconds=13),
                        )
                    for number in range(2):
                        delta = delta + datetime.timedelta(hours=8)
                        await conv.send_message(
                            "реанимировать жабу", schedule=delta
                        )
                        await conv.send_message(
                            "работа крупье",
                            schedule=delta + datetime.timedelta(seconds=13),
                        )
                        await conv.send_message(
                            "завершить работу",
                            schedule=delta + datetime.timedelta(hours=2, seconds=13),
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
                        delta = datetime.timedelta(hours=hrs, minutes=min, seconds=3)
                        await conv.send_message(
                            "завершить работу", schedule=delta
                        )
                elif "можно отправить" in response.text:
                    await conv.send_message("реанимировать жабу")
                    await conv.send_message("работа крупье")
                    delta = datetime.timedelta(hours=2, seconds=3)
                    await conv.send_message(
                        "завершить работу", schedule=delta
                    )
                else:
                    await conv.send_message("завершить работу")
                    delta = datetime.timedelta(hours=6)
                for number in range(2):
                    delta = delta + datetime.timedelta(hours=6, seconds=3)
                    await conv.send_message(
                        "реанимировать жабу", schedule=delta
                    )
                    await conv.send_message(
                        "работа крупье",
                        schedule=delta + datetime.timedelta(seconds=3),
                    )
                    await conv.send_message(
                        "завершить работу",
                        schedule=delta + datetime.timedelta(hours=2, seconds=13),
                    )
        else:
            pass
        if chatid not in duel:
            return
        elif message.sender_id not in {self.me.id, 1124824021}:
            if "РеанимироватЬ жабу" in message.message:
                await asyncio.sleep(rc)
                return await utils.answer(message, "дуэль")
            else:
                return
        elif message.sender_id in {1124824021}:
            if (
                f"Вы бросили вызов на дуэль пользователю {self.me.first_name}"
                in message.message
            ):
                await asyncio.sleep(rc)
                await message.respond("дуэль принять")
                await asyncio.sleep(rc)
                return await message.respond("дуэль старт")
            elif "Имя Жабы" in self.status:
                if f"{self.status['Имя Жабы']}, У вас ничья" in message.message:
                    await asyncio.sleep(rc)
                    return await message.respond("РеанимироватЬ жабу")
                elif "Победитель" in message.message:
                    if (
                        self.status["Имя Жабы"] in message.message
                        and "отыграл" in message.message
                    ):
                        duel.pop(chatid)
                        self.db.set("Дуэлька", "duel", duel)
                        await utils.answer(message, "<b>пью ромашковый чай</b>!")
                    elif self.status["Имя Жабы"] not in message.message:
                        await asyncio.sleep(rc)
                        await utils.answer(message, "РеанимироватЬ жабу")
                    else:
                        return
                else:
                    return
            else:
                return
        else:
            return
