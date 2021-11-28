from math import floor
from html import escape
from random import choice
from asyncio import sleep
from .. import loader, utils
from datetime import timedelta
from urllib.parse import quote_plus
from telethon.tl.types import Message
from telethon import events, functions, types, sync
from telethon.tl.functions.users import GetFullUserRequest
from telethon.errors.rpcerrorlist import UsernameOccupiedError
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
import asyncio, datetime, inspect, io, json, logging, os, threading, time, random, re, requests, urllib.parse

#requires: urllib requests

logger = logging.getLogger(__name__)
types_of = ['femdom', 'tickle', 'classic', 'ngif', 'erofeet', 'meow', 'erok', 'poke', 'les', 'hololewd', 'lewdk', 'keta', 'feetg', 'nsfw_neko_gif', 'eroyuri', 'kiss', '_8ball', 'kuni', 'tits', 'pussy_jpg', 'cum_jpg', 'pussy', 'lewdkemo', 'lizard', 'slap', 'lewd', 'cum', 'cuddle', 'spank', 'smallboobs', 'goose',
'Random_hentai_gif', 'avatar', 'fox_girl', 'nsfw_avatar', 'hug', 'gecg', 'boobs', 'pat', 'feet', 'smug', 'kemonomimi', 'solog', 'holo', 'wallpaper', 'bj', 'woof', 'yuri', 'trap', 'anal', 'baka', 'blowjob', 'holoero', 'feed', 'neko', 'gasm', 'hentai', 'futanari', 'ero', 'solo', 'waifu', 'pwankg', 'eron', 'erokemo']

def chunks(lst, n):
    return [lst[i:i + n] for i in range(0, len(lst), n)]

def register(cb):
    cb(KramikkMod())

@loader.tds
class KramikkMod(loader.Module):
    """Алина, я люблю тебя!"""
    answers = { 0:("Невнятен вопрос, хз, что отвечать",),
        1:("Ответ тебе известен", "Ты знаешь лучше меня!", "Ответ убил!.."),
        2:("Да", "Утвердительный ответ", "Ага"),
        3:("Да, но есть помехи", "Может быть", "Вероятно", "Возможно", "Наверняка"),
        4:("Знаю ответ, но не скажу", "Думай!", "Угадай-ка...", "Это загадка от Жака Фреско..."),
        5:("Нет", "Отрицательный ответ"),
        6:("Обязательно", "Конечно", "Сто пудов", "Абсолютно", "Разумеется", "100%"),
        7:("Есть помехи...", "Вряд ли", "Что-то помешает", "Маловероятно"),
        8:("Да, но нескоро", "Да, но не сейчас!"),
        9:("Нет, но пока", "Скоро!", "Жди!", "Пока нет")}
    strings = {
        'name': 'Kramikk',
        'loading': '<b>Loading...</b>',
        'update': '<b>обновление списка кланов</b>',
        "name_not_found": "<u>Не указано имя, исправь это:</u>\n <code>.kblname %name%</code>",
        "name_set": "<u>Имя успешно установлено</u>",
        "quest_not_found": "<u>Агде вопрос?</u>",
        "quest_answer": "\n\n<u>%answer%</u>",
        "mention": "<a href='tg://user?id=%id%'>%name%</a>",
    }

    def __init__(self):
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        ans = (await utils.run_sync(requests.get, 'https://nekos.life/api/v2/endpoints')).json()
        clans = {
            'Багoboty' : -1001380664241,
            'Том Рэддл' : -1001441941681,
            'Манулы и Зайчатки' : -1001289617428,
            'Жаботорт' : -1001436786642,
            'Своя атмосфера' : -1001485617300,
            'Бар' : -1001465870466,
            '.' : -1001409792751,
            'жабки нэлс(платон)' : -1001165420047,
            'Станция' : -1001447960786,
            'Дирижабль' : -1001264330106,
            'Сказочный донатер' : -1001648008859,
            'Листик' : -1001685708710,
            'Жабы аферисты Крам и бабушка' : -421815520,
            'Хэлло Вин!' : -1001426018704,
            'Танцы по средам' : -1001481051409,
            'IELTS' : -1001492669520,
            'Домик в болоте' : -1001520533176,
            'Космос нас ждет' : -1001460270560,
            'Forbidden Frog' : -1001511984124,
            'Vitoad' : -1001771130958,
            'Курсы вышивания' : -1001760342148,
            'Золотая жаба' : -1001787904496,
            'LSDtoads' : -1001493923839,
            'Цыганка' : -1001714871513,
            'жабы лена' : -1001419547228,
            'Жабочка' : -1001666737591,
            'AstroFrog' : -1001575042525,
            'Консилиум жаб' : -1001777552705,
            'Жабьи монстрики' : -1001427000422,
            'Жабы Вероны' : -1001256439407,
            'Жабьи специи' : -1001499700136,
            'Болотозавр' : -1001624280659,
            'Жабоботство' : -543554726,
        }
        self.categories = json.loads('[' + [_ for _ in ans if '/api' in _ and '/img/' in _][0].split('<')[1].split('>')[0].replace("'", '"') + ']')
        self.clans = clans
        self.client = client
        self.endpoints = {
            'img': 'https://nekos.life/api/v2/img/',
            'owoify': 'https://nekos.life/api/v2/owoify?text=',
            'why': 'https://nekos.life/api/v2/why',
            'cat': 'https://nekos.life/api/v2/cat',
            'fact': 'https://nekos.life/api/v2/fact'
        }
        self.db = db
        self.me = await client.get_me()
        self.status = db.get('Status', 'status', {})

    @loader.sudo
    async def delmecmd(self, message):
        chat = message.chat
        if chat:
            args = utils.get_args_raw(message)
            mag = await utils.answer(message, "<b>Ищу сообщения...</b>")
            all = (await self.client.get_messages(chat, from_user='me')).total
            await utils.answer(msg, f'<b>{all} сообщений будет удалено!</b>')
            messages = [msg async for msg in self.client.iter_messages(chat, from_user='me')]
            _ = ""
            async for msg in self.client.iter_messages(chat, from_user='me'):
                if _:
                    await msg.delete()
                else:
                    _ = "_"
            await message.delete()

    async def idcmd(self, message):
        reply = await message.get_reply_message()
        user = await message.client.get_entity(reply.sender_id)
        adjectives_start = ["хороший(-ая)", "интересный(-ая)", "прекрасный(-ая)", "для меня няшный(-ая)",
                            "пышный(-ая)", "ангельский(-ая)", "аппетитный(-ая)", "гарный(-ая)"]
        emojies = ["🐶", "🐱", "🐹", "🐣", "🥪", "🍓", "♥️", "🤍", "🪄", "✨", "🦹🏻", "🌊"]
        nouns = ["человек", "участник(-ца) данного чата"]
        starts = ["Не хочу делать поспешных выводов, но", "Я, конечно, не могу утверждать, и это мое субъективное мнение, но", "Проанализировав ситуацию, я могу высказать свое субъективное мнение. Оно заключается в том, что",
                  "Не пытаясь никого оскорбить, а лишь высказывая свою скромную точку зрения, которая не влияет на точку зрения других людей, могу сказать, что"]
        ends = ["!!!!", "!", "."]
        start = random.choice(starts)
        adjective_start = random.choice(adjectives_start)
        adjective_mid = random.choice(adjectives_start)
        noun = random.choice(nouns)
        end = random.choice(ends)
        emojie = random.choice(emojies)
        insult = emojie + "  " + start + " ты — " + adjective_start + " и " + \
            adjective_mid + (" " if adjective_mid else "") + noun + end
        logger.debug(insult)
        await message.edit(f'{insult}\n\n'
                           f'имя: <b>{user.first_name}</b>\n'
                           f'айди: <b>{user.id}</b>\n'
                           f'юзер: @{user.username}\n'
                           f'айди чата: <code>{reply.chat_id}</code>')

    @loader.unrestricted
    async def factcmd(self, message):
        """Did you know?"""
        await utils.answer(message, f"<b>🧐 Did you know, that </b><code>{(await utils.run_sync(requests.get, self.endpoints['fact'])).json()['fact']}</code>")

    async def kblcmd(self, message):
        """Высчитать ответ на вопрос"""
        name = self.db.get("kbl", "name", None)
        if not name: return await message.edit(self.strings["name_not_found"].replace("%name%", escape(message.sender.first_name)))
        args = utils.get_args_raw(message)
        if not args: return await message.edit(self.strings["quest_not_found"])
        words = re.findall(r"\w+", f"{name} {args}")
        words_len = [words.__len__()] + [x.__len__() for x in words]
        i = words_len.__len__()
        while i > 1:
            i -= 1
            for x in range(i): words_len[x] = words_len[x] + words_len[x+1] - 9 if words_len[x] + words_len[x+1] > 9 else words_len[x] + words_len[x+1]
        return await message.edit(self.strings["mention"].replace('%id%', str(self.me.id)).replace('%name%', name)+':\n'
                                  +args+f'?\n\n{" |"*words_len[0]}'+self.strings["quest_answer"].replace("%answer%", choice(self.answers[words_len[0]])))

    async def kblnamecmd(self, message):
        """Установить ииии-мя лю-би-мое твоё"""
        args = utils.get_args(message)
        await self.db.set("kbl", "name", ' '.join(args) if args else None)
        await message.edit(self.strings["name_set"])

    @loader.unrestricted
    async def meowcmd(self, message):
        """Sends cat ascii art"""
        await utils.answer(message, f"<b>{(await utils.run_sync(requests.get, self.endpoints['cat'])).json()['cat']}</b>")

    @loader.pm
    async def nekocmd(self, message):
        """Send anime pic"""
        args = utils.get_args_raw(message)
        args = 'neko' if args not in self.categories else args
        pic = (await utils.run_sync(requests.get, f"{self.endpoints['img']}{args}")).json()["url"]
        await self.client.send_file(message.peer_id, pic, reply_to=message.reply_to_msg_id)
        await message.delete()

    @loader.pm
    async def nekoctcmd(self, message):
        """Show available categories"""
        cats = '\n'.join([' | </code><code>'.join(_) for _ in chunks(self.categories, 5)])
        await utils.answer(message, f'<b>Available categories:</b>\n<code>{cats}</code>')

    @loader.owner
    async def nkcmd(self, m):
        "Отправить фото/гиф\nПо умолчанию отправляется neko\nМожно указать другую категорию(.nkct)"
        args = utils.get_args_raw(m)
        typ = None
        if args:
            if args in types_of:
                typ = args
        else:
            typ = "neko"
        if typ is None:
            return await m.edit('<b>не знаю такого</b>')
        await m.edit('<b>Mmm...</b>')
        reply = await m.get_reply_message()
        await m.client.send_file(m.to_id, requests.get(f'https://nekos.life/api/v2/img/{typ}').json()['url'], reply_to=reply.id if reply else None)
        await m.delete()
    async def nkctcmd(self, m):
        await m.edit('Доступные категории:\n' + '\n'.join(f'<code>{i}</code>' for i in types_of))

    async def carboncmd(self, message):
        args = utils.get_args_raw(message)
        message = await utils.answer(message, self.strings('loading', message))
        try:
            message = message[0]
        except:
            pass
        url = 'https://carbonnowsh.herokuapp.com/?code=' + urllib.parse.quote_plus(args).replace('%0A', '%250A').replace('%23', '%2523').replace('%2F', '%252f')
        logger.info('[Carbon]: Fetching url ' + url)
        await self.client.send_message(utils.get_chat_id(message), file=requests.get(url).content)
        await message.delete()


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
            message = await utils.answer(message, '<b>OwOifying...</b>')
            try:
                message = message[0]
            except: pass

        args = quote_plus(args)
        owo = ""
        for chunk in chunks(args, 180):
            owo += (await utils.run_sync(requests.get, f"{self.endpoints['owoify']}{chunk}")).json()['owo']
            await asyncio.sleep(0.1)
        await utils.answer(message, owo)

    async def watcher(self, message):
        bak = {1222132115, 1646740346, 1261343954, 1785723159, 1486632011, 1682801197, 1863720231, 1775420029, 1286303075, 1746686703, 1459363960, 1423368454, 547639600, 388412512}
        chat = message.chat_id
        chatid= str(message.chat_id)
        chatik = -1001441941681
        duel = self.db.get('Дуэлька', 'duel', {})
        jb = "jaba"
        name = "жабич"
        if self.me.id in {1261343954}:
            name = "Монарх"
        if self.me.id in {1486632011}:
            name = "Оботи"
        if self.me.id in {1286303075}:
            name = "Лавин"
        if self.me.id in {1775420029}:
            name = "Адият"
        if self.me.id in {1682801197}:
            name = "666"
        if self.me.id in {1646740346}:
            name = "Куат"
        if self.me.id in {1863720231}:
            name = "Допинг"
        if self.me.id in {1785723159}:
            name = "Крамик"
        if self.me.id in {547639600}:
            name = "Нельс"
        randelta = random.randint(7, 21+1)

        if message.sender_id in {1124824021}:
            if "Сейчас выбирает ход: " + self.me.first_name in message.message:
                await message.click(0)
            if "Господин " + self.me.first_name in message.message:
                await sleep (3)
                await message.respond('реанимировать жабу')
                await sleep (3)
                await message.respond('отправиться за картой')
            if "позвать на тусу" in message.message:
                await sleep(3)
                await message.respond('реанимировать жабу')
                await sleep(3)
                await message.respond('жабу на тусу')

        if message.sender_id in {self.me.id}:
            if "общий инвентарь" in message.message:
                cid = "clan"
                if cid not in self.status:
                    await utils.answer(message, self.strings('update', message))
                else:
                    await message.edit(self.status[cid])
                prit = "<b>Мой общий инвентарь:</b>"
                for clan_name, clan_id in self.clans.items():
                    async with message.client.conversation(clan_id) as conv:
                        response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=clan_id))
                        await sleep(1)
                        await conv.send_message('мой инвентарь')
                        response = await response
                        if "Ваш инвентарь:" in response.text:
                            caption = re.search('🍬Леденцы: (\d+)', response.text).group(1)
                            caption1 = re.search('💊Аптечки: (\d+)', response.text).group(1)
                            caption2 = re.search('🗺Карта болота: (\d+)', response.text).group(1)
                            caption3 = re.search('🐸Жабули для банды: (.+)', response.text).group(1)
                            prit += f"\n\n{clan_name}\n🍬Леденцы: {caption}\n💊Аптечки: {caption1}\n🗺Карта болота: {caption2}\n🐸Жабули для банды: {caption3}"
                args = prit
                self.status[cid] = args
                self.db.set('Status', 'status', self.status)
                await message.edit(f'{args}')

        if message.sender_id in bak:
            if "жаба дня" in message.message:
                async with self.client.conversation(message.chat_id) as conv:
                    await sleep(3)
                    response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=message.chat_id))
                    await message.respond('жаба инфо')
                    response = await response
                    if "работу можно" in response.text:
                        time_j = re.search('будет через (\d+)ч:(\d+)м', response.text, re.IGNORECASE)
                        if time_j:
                            hrs = int(time_j.group(1))
                            min = int(time_j.group(2))
                            delta = timedelta(hours=hrs, minutes=min, seconds=randelta)
                        await message.client.send_message(chat, 'реанимировать жабу', schedule=delta)
                        await message.client.send_message(chat, 'работа грабитель', schedule=delta + timedelta(seconds=13))
                        for number in range(2):
                            delta = delta + timedelta(hours=8)
                            await message.client.send_message(chat, 'реанимировать жабу', schedule=delta)
                            await message.client.send_message(chat, 'работа грабитель', schedule=delta + timedelta(seconds=randelta))
                            await message.client.send_message(chat, 'завершить работу', schedule=delta + timedelta(hours=2, seconds=randelta+3))
                            await sleep(1)
                    else:
                        if "жабу можно через" in response.text:
                            time_r = re.search('через (\d+) часов (\d+) минут', response.text, re.IGNORECASE)
                            if time_r:
                                hrs = int(time_r.group(1))
                                min = int(time_r.group(2))
                                delta = timedelta(hours=hrs, minutes=min, seconds=randelta)
                            await message.client.send_message(chat, 'завершить работу', schedule=delta)
                        elif "можно отправить" in response.text:
                            await sleep(3)
                            await message.respond('реанимировать жабу')
                            await sleep(3)
                            await message.respond('работа грабитель')
                            delta = timedelta(hours=2, seconds=randelta)
                            await message.client.send_message(chat, 'завершить работу', schedule=delta)
                        else:
                            await sleep(3)
                            await message.respond('завершить работу')
                        for number in range(2):
                            delta = delta + timedelta(hours=6, seconds=3)
                            await message.client.send_message(chat, 'реанимировать жабу', schedule=delta)
                            await message.client.send_message(chat, 'работа грабитель', schedule=delta + timedelta(seconds=randelta))
                            await message.client.send_message(chat, 'завершить работу', schedule=delta + timedelta(hours=2, seconds=randelta+3))
                            await sleep(3)
                    if "покормить через" in response.text:
                        time_n = re.search('покормить через (\d+)ч:(\d+)м', response.text, re.IGNORECASE)
                        if time_n:
                            hrs = int(time_n.group(1))
                            min = int(time_n.group(2))
                            delta = timedelta(hours=hrs, minutes=min, seconds=randelta)
                        await message.client.send_message(chat, 'покормить жабку', schedule=delta)
                    else:
                        delta = timedelta(seconds=randelta)
                        await message.client.send_message(chat, 'покормить жабку', schedule=delta)
                    for number in range(1):
                        delta = delta + timedelta(hours=12, seconds=3)
                        await message.client.send_message(chat, 'покормить жабку', schedule=delta)
                        await sleep(3)

            if name + " дуэлька" in message.message:
                if chatid in duel:
                    duel.pop(chatid)
                    self.db.set('Дуэлька', 'duel', duel)
                    return await message.respond('<b>пью ромашковый чай</b>!')
                duel.setdefault(chatid, {})
                self.db.set('Дуэлька', 'duel', duel)
                async with message.client.conversation(message.chat_id) as conv:
                    response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=message.chat_id))
                    await sleep(1)
                    await conv.send_message('моя жаба')
                    response = await response
                    if "Имя жабы:" in response.text:
                        jaba = re.search('Имя жабы: (.+)', response.text).group(1)
                self.status[jb] = jaba
                self.db.set('Status', 'status', self.status)
                await message.respond(f'Имя жабы установлен: {jaba}\n го дуэли')
                await message.respond('РеанимироватЬ жабу')
            if name + " напади" in message.message:
                await message.respond("<b>реанимировать жабу</b>")
                await sleep (3)
                await message.respond('<b>напасть на клан</b>')
            if name + " подземелье" in message.message:
                await message.respond('<b>реанимировать жабу</b>')
                await sleep (3)
                await message.respond('<b>отправиться в золотое подземелье</b>')
            if name + " с работы" in message.message:
                await message.respond('<b>завершить работу</b>')
            if name + " карту" in message.message:
                await message.respond('<b>отправить карту</b>')
            if name + " за картой" in message.message:
                await message.respond('<b>отправиться за картой</b>')
            if name + " на тусу" in message.message:
                await message.respond('<b>реанимировать жабу</b>')
                await sleep (3)
                await message.respond('<b>жабу на тусу</b>')
            if "букашки мне😊" in message.message:
                await sleep (randelta)
                async with message.client.conversation(chat) as conv:
                    response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=message.chat_id))
                    await message.respond('мой баланс')
                    response = await response
                    if 'Баланс букашек вашей' in response.text:
                        bug = int(re.search('жабы: (\d+)', response.text, re.IGNORECASE).group(1))
                        if bug <50:
                            await message.reply('осталось для похода')
                        else:
                            while bug > 50049:
                                await message.reply('отправить букашки 50000')
                                bug -= 50000
                                await sleep(1)
                            snt = bug-50
                            await sleep (randelta)
                            await message.reply(f'отправить букашки {snt}')
            if "инвентарь мне😊" in message.message:
                await sleep (randelta)
                async with message.client.conversation(chat) as conv:
                    response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=message.chat_id))
                    await message.respond('мой инвентарь')
                    response = await response
                    if 'Ваш инвентарь:' in response.text:
                        cnd = int(re.search('Леденцы: (\d+)', response.text, re.IGNORECASE).group(1))
                        apt = int(re.search('Аптечки: (\d+)', response.text, re.IGNORECASE).group(1))
                        await sleep (randelta)
                    if cnd > 0:
                        while cnd > 49:
                            await message.reply('отправить леденцы 50')
                            cnd -= 50
                            await sleep(1)
                        await message.reply(f'отправить леденцы {cnd}')
                        await sleep(1)
                    if apt > 0:
                        if apt > 9:
                            await message.reply('отправить аптечки 10')
                        else:
                            await message.reply(f'отправить аптечки {apt}')

            if "огошечки" in message.message:
                reply = await message.get_reply_message()
                if reply:
                    count = len(re.findall('^•', reply.text, re.MULTILINE))
                    neys = re.findall('Уровень: (\d+)', reply.text)
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
                    args = f'жаб: {count}\n\nмин уровень: {mnu}\nМакс уровень: {msu}'
                    await message.reply(args)

            if "гонщик" in message.message:
                reply = await message.get_reply_message()
                if reply:
                    count = int(len(re.findall('^🏆', reply.text, re.MULTILINE)))
                    if count > 1:
                        money = int(re.search('сумма ставки: (\d+) букашек', reply.text, re.IGNORECASE). group (1))
                        gm = round((money * count) * 0.85)
                        args = f'< в забеге участвуют {count} чувачка\nпобедитель получит {gm} букашек >\n\n       \   ^__^\n        \  (oo)\_______\n           (__)\       )\/\n               ||----w||\n               ||     ||'
                    else:
                        args = '🌕🌕🌕🌕🌕🌕🌕🌕🌕\n🌕🌗🌑🌑🌑🌑🌑🌓🌕\n🌕🌗🌑🌑🌑🌑🌑🌕🌕\n🌕🌗🌑🌓🌕🌕🌕🌕🌕\n🌕🌗🌑🌓🌕🌕🌕🌕🌕\n🌕🌗🌑🌑🌑🌑🌓🌕🌕\n🌕🌗🌑🌑🌑🌑🌕🌕🌕\n🌕🌗🌑🌓🌕🌕🌕🌕🌕\n🌕🌗🌑🌓🌕🌕🌕🌕🌕\n🌕🌗🌑🌓🌕🌕🌕🌕🌕\n🌕🌕🌕🌕🌕🌕🌕🌕🌕'
                    await message.reply(args)

        if chatid not in duel: return

        if message.sender_id not in {self.me.id, 1124824021}:
            if "РеанимироватЬ жабу" in message.message:
                await sleep (1)
                await message.reply('дуэль')

        if message.sender_id in {1124824021}:
            if "Вы бросили вызов на дуэль пользователю " + self.me.first_name in message.message:
                await sleep (1)
                await message.respond('дуэль принять')
                await sleep (1)
                await message.respond('дуэль старт')

            if self.status[jb] + ", У вас ничья" in message.message:
                await sleep (1)
                await message.respond('РеанимироватЬ жабу')

            if "Победитель" in message.message:
                if self.status[jb] + "!!!" in message.message:
                    if "отыграл" in message.message:
                        duel.pop(chatid)
                        self.db.set('Дуэлька', 'duel', duel)
                        return await message.respond('<b>пью ромашковый чай</b>!')
                    else:
                        return
                else:
                    await sleep (1)
                    await message.respond('РеанимироватЬ жабу')

    @loader.unrestricted
    async def whycmd(self, message):
        """Why?"""
        await utils.answer(message, f"<code>👾 {(await utils.run_sync(requests.get, self.endpoints['why'])).json()['why']}</code>")
