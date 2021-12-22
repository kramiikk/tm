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
        name = self.me.first_name
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
        if (
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
                        "Клан: (.+)", response.text
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
