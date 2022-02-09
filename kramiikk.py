import asyncio
import datetime
import logging
import random
import re

from telethon import events, functions

from .. import loader

logger = logging.getLogger(__name__)

RESPONSE = None

bak = [
    1785723159,
    1261343954,
    1377037394,
    635396952,
    547639600,
    553299699,
    412897338,
    449434040,
    388412512,
]


@loader.tds
class KramiikkMod(loader.Module):
    """Алина, я люблю тебя."""

    answers = {
        0: ("Ответ тебе известен", "Ты знаешь лучше меня!", "Ответ убил!.."),
        1: ("Да, но есть помехи", "Может быть", "Вероятно", "Возможно", "Наверняка"),
        2: ("Есть помехи...", "Вряд ли", "Что-то помешает", "Маловероятно"),
        3: ("Нет, но пока", "Скоро!", "Жди!", "Пока нет"),
    }
    strings = {"name": "kramiikk", "quest_answer": "<i>%answer%</i>"}

    def __init__(self):
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        """.

        ----------

        """
        self.client = client
        self.db = db
        self.me = await client.get_me()

    async def err(self, m, p, s):
        """.

        ----------

        """
        try:
            async with self.client.conversation(m.chat_id) as conv:
                await s
                global RESPONSE
                RESPONSE = await conv.wait_event(
                    events.NewMessage(from_users=1124824021, chats=m.chat_id, pattern=p)
                )
                await conv.cancel_all()
        except asyncio.exceptions.TimeoutError:
            pass

    async def watcher(self, m):
        """.

        ----------

        """
        if self.me.id in {1486632011}:
            name = "оботи"
        elif self.me.id in {1286303075}:
            name = "лавин"
        elif self.me.id in {1785723159}:
            name = "крамик"
        elif self.me.id in {547639600}:
            name = "нельс"
        elif self.me.id in {980699009}:
            name = "лена"
        elif self.me.id in {1423368454}:
            name = "len"
        elif self.me.id in {230473666}:
            name = "ваня"
        elif self.me.id in {887255479}:
            name = "кира"
        else:
            name = self.me.first_name
        if (
            m.message.lower().startswith((name, f"@{self.me.username}"))
            or (name in m.message and m.message.endswith("😉"))
        ) and m.sender_id in bak:
            args = m.text
            reply = await m.get_reply_message()
            count = args.split(" ", 2)[1]
            if m.raw_text.endswith("?"):
                words = re.findall(r"\w+", f"{m.text}")
                words_len = [words.__len__()] + [x.__len__() for x in words]
                i = words_len.__len__()
                while i > 1:
                    i -= 1
                    for s in range(i):
                        words_len[s] = (
                            words_len[s] + words_len[s + 1] - 3
                            if words_len[s] + words_len[s + 1] > 3
                            else words_len[s] + words_len[s + 1]
                        )
                await m.reply(
                    self.strings["quest_answer"].replace(
                        "%answer%", random.choice(self.answers[words_len[0]])
                    )
                )
            elif "напиши в" in m.message:
                i = args.split(" ", 4)[3]
                if i.isnumeric():
                    i = int(i)
                s = args.split(" ", 4)[4]
                if reply:
                    s = reply
                await self.client.send_message(i, s)
            elif "реплай" in m.message:
                i = args.split(" ", 4)[2]
                if i.isnumeric():
                    i = int(i)
                p = args.split(" ", 4)[3]
                if p.isnumeric():
                    p = int(p)
                i = await self.client.get_messages(i, ids=p)
                s = args.split(" ", 4)[4]
                if reply:
                    s = reply
                await i.reply(s)
            elif "reply" in m.message:
                await m.respond(reply)
            elif "арена" in m.message:
                p = "•"
                s = self.client.send_message(m.chat_id, "<b>мои жабы</b>")
                await self.err(m, p, s)
                capt = re.findall(r"\| -100(\d+)", RESPONSE.text)
                for i in capt:
                    await self.client.send_message(int(i), "<b>реанимировать жабу</b>")
                    await self.client.send_message(int(i), "<b>на арену</b>")
            elif "напади" in m.message:
                p = None
                s = self.client.send_message(m.chat_id, "<b>напасть на клан</b>")
                await self.err(m, p, s)
                if "Ваша жаба на" in RESPONSE.text:
                    await m.respond("завершить работу")
                    await m.respond("реанимировать жабу")
                    await m.respond("напасть на клан")
                elif "Ваша жаба сейчас" in RESPONSE.text:
                    await m.respond("выйти из подземелья")
                    await m.respond("реанимировать жабу")
                    await m.respond("напасть на клан")
            elif "подземелье" in m.message:
                p = None
                s = self.client.send_message(
                    m.chat_id, "<b>отправиться в золотое подземелье</b>"
                )
                await self.err(m, p, s)
                if "Пожалейте жабу," in RESPONSE.text:
                    await m.respond("завершить работу")
                    await m.respond("реанимировать жабу")
                    await m.respond("<b>отправиться в золотое подземелье</b>")
                elif "Ваша жаба при" in RESPONSE.text:
                    await m.respond("реанимировать жабу")
                    await m.respond("<b>отправиться в золотое подземелье</b>")
                else:
                    await m.respond("<b>рейд инфо</b>")
            elif "снаряжение" in m.message:
                p = "Ваше"
                s = self.client.send_message(m.chat_id, "<b>мое снаряжение</b>")
                await self.err(m, p, s)
                if "Ближний бой: Пусто" in RESPONSE.text:
                    await m.respond("скрафтить клюв цапли")
                if "Дальний бой: Пусто" in RESPONSE.text:
                    await m.respond("скрафтить букашкомет")
                if "Наголовник: Пусто" in RESPONSE.text:
                    await m.respond("скрафтить наголовник из клюва цапли")
                if "Нагрудник: Пусто" in RESPONSE.text:
                    await m.respond("скрафтить нагрудник из клюва цапли")
                if "Налапники: Пусто" in RESPONSE.text:
                    await m.respond("скрафтить налапники из клюва цапли")
                else:
                    await m.respond("мой инвентарь")
            elif "лвл чек" in m.message:
                s = (
                    (int(m.text.split(" ", 4)[3]) + int(m.text.split(" ", 4)[4])) - 160
                ) * 2
                if s > -1:
                    await m.reply(f"<b>~ {s} лвл</b>")
            elif "туса" in m.message:
                await m.respond("жабу на тусу")
            elif "го кв" in m.message:
                await m.respond("начать клановую войну")
            elif count.isnumeric() and reply:
                count = int(args.split(" ", 3)[1])
                mmsg = args.split(" ", 3)[3]
                time = int(args.split(" ", 3)[2])
                for i in range(count):
                    await reply.reply(mmsg)
                    await asyncio.sleep(time)
            elif count.isnumeric():
                count = int(args.split(" ", 3)[1])
                mmsg = args.split(" ", 3)[3]
                time = int(args.split(" ", 3)[2])
                for i in range(count):
                    await m.reply(mmsg)
                    await asyncio.sleep(time)
            else:
                mmsg = args.split(" ", 2)[2]
                if reply:
                    await reply.reply(mmsg)
                else:
                    await m.respond(mmsg)
        elif m.message.lower().startswith("букашки мне😊") and m.sender_id in bak:
            await asyncio.sleep(random.randint(1, 13))
            p = "Баланс"
            s = self.client.send_message(m.chat_id, "<b>мой баланс</b>")
            await self.err(m, p, s)
            bug = int(re.search(r"жабы: (\d+)", RESPONSE.text, re.IGNORECASE).group(1))
            if bug < 100:
                await m.reply("осталось для похода")
            else:
                while bug > 50049:
                    await m.reply("отправить букашки 50000")
                    bug -= 50000
                snt = bug - 50
                await m.reply(f"отправить букашки {snt}")
        elif m.message.lower().startswith("инвентарь мне😊") and m.sender_id in bak:
            await asyncio.sleep(random.randint(1, 13))
            p = "Ваш"
            s = self.client.send_message(m.chat_id, "<b>мой инвентарь</b>")
            await self.err(m, p, s)
            cnd = int(
                re.search(r"Леденцы: (\d+)", RESPONSE.text, re.IGNORECASE).group(1)
            )
            apt = int(
                re.search(r"Аптечки: (\d+)", RESPONSE.text, re.IGNORECASE).group(1)
            )
            if cnd > 0:
                if cnd > 49:
                    await m.reply("отправить леденцы 50")
                else:
                    await m.reply(f"отправить леденцы {cnd}")
                if apt > 9:
                    await m.reply("отправить аптечки 10")
                else:
                    await m.reply(f"отправить аптечки {apt}")
        elif f"Сейчас выбирает ход: {self.me.first_name}" in m.message and m.buttons:
            await m.respond("реанимировать жабу")
            await m.click(0)
        elif m.message.lower().startswith(
            ("жаба инфо", "@toadbot жаба")
        ) and m.sender_id in {1785723159, 1261343954}:
            sch = (
                await self.client(
                    functions.messages.GetScheduledHistoryRequest(m.chat_id, 0)
                )
            ).messages
            await self.client(
                functions.messages.DeleteScheduledMessagesRequest(
                    m.chat_id, id=[x.id for x in sch]
                )
            )
            delta = datetime.timedelta(seconds=7)
            p = None
            s = self.client.send_message(
                    m.chat_id, "моя банда", schedule=delta
                )
            await self.err(m, p, s)
            if "(Откормить через" in RESPONSE.text:
                time_f = re.search(
                    r"Откормить через (\d+)ч:(\d+)м",
                    RESPONSE.text,
                    re.IGNORECASE,
                )
                delta = datetime.timedelta(
                    hours=int(time_f.group(1)),
                    minutes=int(time_f.group(2)),
                    seconds=3,
                )
                await self.client.send_message(
                    m.chat_id, "откормить жабку", schedule=delta
                )
            else:
                await self.client.send_message(m.chat_id, "откормить жабку")
                delta = datetime.timedelta(hours=4, seconds=3)
                await self.client.send_message(
                    m.chat_id, "откормить жабку", schedule=delta
                )
            for i in range(4):
                delta = delta + datetime.timedelta(hours=4)
                await self.client.send_message(
                    m.chat_id, "откормить жабку", schedule=delta
                )
            if "В подземелье можно" in RESPONSE.text:
                dng_s = re.search(
                    r"подземелье можно через (\d+)ч. (\d+)м.",
                    RESPONSE.text,
                    re.IGNORECASE,
                )
                delta = datetime.timedelta(
                    hours=int(dng_s.group(1)),
                    minutes=int(dng_s.group(2)),
                    seconds=3,
                )
                await self.client.send_message(
                    m.chat_id, "реанимировать жабу", schedule=delta
                )
                await self.client.send_message(
                    m.chat_id,
                    "Отправиться в золотое подземелье",
                    schedule=delta + datetime.timedelta(seconds=13),
                )
                if int(dng_s.group(1)) > 1:
                    await m.respond("реанимировать жабу")
                    await m.respond("работа крупье")
                    delta = datetime.timedelta(hours=2, seconds=3)
                    await self.client.send_message(
                        m.chat_id, "завершить работу", schedule=delta
                    )
                for i in range(2):
                    delta = delta + datetime.timedelta(hours=6, seconds=3)
                    await self.client.send_message(
                        m.chat_id, "реанимировать жабу", schedule=delta
                    )
                    await self.client.send_message(
                        m.chat_id,
                        "работа крупье",
                        schedule=delta + datetime.timedelta(seconds=3),
                    )
                    await self.client.send_message(
                        m.chat_id,
                        "завершить работу",
                        schedule=delta + datetime.timedelta(hours=2, seconds=13),
                    )
            elif "Забрать жабу можно" in RESPONSE.text:
                dng_s = re.search(
                    r"жабу можно через (\d+) часов (\d+) минут",
                    RESPONSE.text,
                    re.IGNORECASE,
                )
                delta = datetime.timedelta(
                    hours=int(dng_s.group(1)),
                    minutes=int(dng_s.group(2)),
                    seconds=3,
                )
                await self.client.send_message(
                    m.chat_id, "завершить работу", schedule=delta
                )
                await self.client.send_message(
                    m.chat_id,
                    "реанимировать жабку",
                    schedule=delta + datetime.timedelta(minutes=25, seconds=3),
                )
                await self.client.send_message(
                    m.chat_id,
                    "Отправиться в золотое подземелье",
                    schedule=delta + datetime.timedelta(minutes=45, seconds=13),
                )
