import os
import re
import time
import random
import asyncio
import logging
import datetime
import requests
import threading
import io, inspect
import urllib.parse
from math import floor
from asyncio import sleep
from .. import loader, utils
from datetime import timedelta
from telethon.tl.types import Message
from telethon import events, functions, types
from telethon.tl.functions.users import GetFullUserRequest
from telethon.errors.rpcerrorlist import UsernameOccupiedError
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest

#requires: urllib requests

logger = logging.getLogger(__name__)

def register(cb):
    cb(KramikkMod())

@loader.tds
class KramikkMod(loader.Module):
    """Алина, я люблю тебя!"""
    strings = {
        'farmon': '<i>Запущен</i>',
        'farmon_already': '<i>Уже запущено</i>',
        'farmoff': '<i>❌Остановлен.\n☢️Надюпано:</i> <b>%coins% i¢</b>',
        'iriska': 'farmiris',
        'name': 'Kramikk',
        'no_args': 'нету аргументов!',
    }

    def __init__(self):
        self.iriska = self.strings['iriska']

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.myid = (await client.get_me()).id

    
    async def irisoncmd(self, message):
        status = self.db.get(self.iriska, "status", False)
        if status: return await message.edit(self.strings['farmon_already'])
        self.db.set(self.iriska, "status", True)
        await self.client.send_message(chat, "Фарма", schedule=timedelta(seconds=20))
        await message.edit(self.strings['farmon'])

    async def irisoffcmd(self, message):
       self.db.set(self.iriska, 'status', False)
       coins = self.db.get(self.iriska, 'coins', 0)
       if coins: self.db.set(self.iriska, 'coins', 0)
       await message.edit(self.strings['farmoff'].replace("%coins%", str(coins)))

    async def watcher(self, message):
        bak = {1646740346, 1261343954, 1785723159, 1486632011, 1682801197, 1863720231, 1775420029, 1286303075}
        chat = message.chat_id
        chatid = str(message.chat_id)
        duel = self.db.get("Дуэлька", "duel", {})
        lvl = False
        me = await message.client.get_me()
        n = 13
        name = me.first_name
        randelta = random.randint(n, n+13)
        u = 0
        x = 0
        EK = {
            -1001441941681,
            -1001436786642,
            -1001380664241,
            -1001289617428,
            -1001485617300,
            -1001465870466,
            -1001447960786}
        KW = {-419726290, -1001543064221, -577735616, -1001493923839}

        if message.sender_id in {1124824021}:
            if "Сейчас выбирает ход: " + name in message.message:
                await message.click(0)
            if "Господин " + name in message.message:
                await sleep (3)
                await message.respond('реанимировать жабу')
                await sleep (3)
                await message.respond('отправиться за картой')
            if "позвать на тусу" in message.message:
                await sleep(3)
                await message.respond('реанимировать жабу')
                await sleep(3)
                await message.respond('жабу на тусу')
            if "Тебе жаба," in message.message:
                if chat in KW:
                    async with self.client.conversation(message.chat_id) as conv:
                        await sleep (3)
                        response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=message.chat_id))
                        await message.respond('мой клан')
                        response = await response
                        if "Клан" in response.text:
                            if "Пойти за картой" not in response.text:
                                await sleep (3)
                                await message.respond('отправиться за картой')
                                await sleep (13)
                                await message.respond('отправиться за картой')
                                delta = timedelta(hours=8, seconds=n)
                                await message.client.send_message(chat, 'отправиться за картой', schedule=delta)
                                await message.client.send_message(chat, 'отправиться за картой', schedule=delta + timedelta(hours=8, seconds=13))

        if message.sender_id in {830605725}:
            if "[8🐝]" in message.message:
                await message.click(0)
            if "[4🐝]" in message.message:
                await message.click(0)
            if "[2☢️🐝, 2🔴🐝," in message.message:
                await message.click(0)
            if "Бзззз! С пасеки" in message.message:
                await message.click(0)

        if "лвл чек" in message.message:
            async with self.client.conversation(message.chat_id) as conv:
                await message.respond(f'Отправь урон и здоровье противника в первой атаке, в виде:\n\n.. 😏 ..\n\n(вместо точек вводить цифры)')
                response = await conv.wait_event(events.NewMessage(incoming=True, outgoing=True, from_users=message.sender_id, chats=message.chat_id))
                if "😏" in response.text:
                    lvl = re.search('(\d+)\s😏\s(\d+)', response.text)
                    if lvl:
                        x = int(lvl.group(1))
                        u = int(lvl.group(2))
                        y = u + x
                        res = ( y - 160 )*2
                        if res > -1:
                            if "😏" in response.text:
                                args = f'~ {res} лвл'
                        else:
                            args = f'лвл не может быть отрицательным!!!\nпробуй заново, напиши:\n\nлвл чек'
                        url = 'https://carbonnowsh.herokuapp.com/?code=' + urllib.parse.quote_plus(args).replace('%0A', '%250A').replace('%23', '%2523').replace('%2F', '%252f')
                        logger.info('[Carbon]: Fetching url ' + url)
                        await self.client.send_message(chat, file=requests.get(url).content, reply_to=response)
                else:
                    await message.reply(f'пробуй заново, напиши:\n\n<code>лвл чек</code>')

        if message.sender_id in {me.id}:
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
                    url = 'https://carbonnowsh.herokuapp.com/?code=' + urllib.parse.quote_plus(args).replace('%0A', '%250A').replace('%23', '%2523').replace('%2F', '%252f')
                    logger.info('[Carbon]: Fetching url ' + url)
                    await self.client.send_message(chat, file=requests.get(url).content, reply_to=reply)

            if "тусач" in message.message:
                reply = await message.get_reply_message()
                if reply:
                    count = len(re.findall('^\d', reply.text, re.MULTILINE))
                    if count > 1:
                        ui = count * 150
                        args = f' ▄▀ ▄▀\n  ▀  ▀\n█▀▀▀▀▀█▄\n█░░░░░█ █\n▀▄▄▄▄▄▀▀\n\nдля этой тусы потратят {ui} букашек'
                    else:
                        args = f' ▄▀ ▄▀\n  ▀  ▀\n█▀▀▀▀▀█▄\n█░░░░░█ █\n▀▄▄▄▄▄▀▀\n\nвсего 1 тусит'
                else:
                    args = f' ▄▀ ▄▀\n  ▀  ▀\n█▀▀▀▀▀█▄\n█░░░░░█ █\n▀▄▄▄▄▄▀▀\n\nкапец никто не тусит'
                url = 'https://carbonnowsh.herokuapp.com/?code=' + urllib.parse.quote_plus(args).replace('%0A', '%250A').replace('%23', '%2523').replace('%2F', '%252f')
                logger.info('[Carbon]: Fetching url ' + url)
                await self.client.send_message(chat, file=requests.get(url).content, reply_to=reply)

            if "гонщик" in message.message:
                reply = await message.get_reply_message()
                if reply:
                    count = int(len(re.findall('^🏆', reply.text, re.MULTILINE)))
                    if count > 1:
                        money = int(re.search('сумма ставки: (\d+) букашек', reply.text, re.IGNORECASE). group (1))
                        gm = round((money * count) * 0.85)
                        args = f'< в забеге участвуют {count} чувачка\nпобедитель получит {gm} букашек >\n\n     \   ^__^\n	      \  (oo)\_______\n         (__)\       )\/\n             ||----w||\n	             ||     ||'
                    else:
                        args = '🌕🌕🌕🌕🌕🌕🌕🌕🌕\n🌕🌗🌑🌑🌑🌑🌑🌓🌕\n🌕🌗🌑🌑🌑🌑🌑🌕🌕\n🌕🌗🌑🌓🌕🌕🌕🌕🌕\n🌕🌗🌑🌓🌕🌕🌕🌕🌕\n🌕🌗🌑🌑🌑🌑🌓🌕🌕\n🌕🌗🌑🌑🌑🌑🌕🌕🌕\n🌕🌗🌑🌓🌕🌕🌕🌕🌕\n🌕🌗🌑🌓🌕🌕🌕🌕🌕\n🌕🌗🌑🌓🌕🌕🌕🌕🌕\n🌕🌕🌕🌕🌕🌕🌕🌕🌕'
                    url = 'https://carbonnowsh.herokuapp.com/?code=' + urllib.parse.quote_plus(args).replace('%0A', '%250A').replace('%23', '%2523').replace('%2F', '%252f')
                    logger.info('[Carbon]: Fetching url ' + url)
                    await self.client.send_message(chat, file=requests.get(url).content, reply_to=reply)

        if chat in EK:
            if message.sender_id in bak:
                if "топ жаб" in message.message:
                    async with self.client.conversation(message.chat_id) as conv:
                        response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=message.chat_id))
                        await message.respond('Отправиться в золотое подземелье')
                        response = await response
                        if "Ну-ка подожди," in response.text:
                            await sleep(3)
                            response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=message.chat_id))
                            await message.respond('рейд инфо')
                            response = await response
                            if "Ребята в золотом" in response.text:
                                count = len(re.findall("• ", response.text.split(sep="Ребята в золотом подземелье:")[1]))
                                if count > 2:
                                    await sleep(3)
                                    response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=message.chat_id))
                                    await message.respond(chat, 'мое снаряжение')
                                    response = await response
                                    if "Ближний бой: Отсутствует" in response.text:
                                        await sleep(3)
                                        await message.respond('скрафтить клюв цапли')
                                    if "Дальний бой: Отсутствует" in response.text:
                                        await sleep(3)
                                        await message.respond('скрафтить букашкомет')
                                    if "Наголовник: Отсутствует" in response.text:
                                        await sleep(3)
                                        await message.respond('скрафтить наголовник из клюва цапли')
                                    if "Нагрудник: Отсутствует" in response.text:
                                        await sleep(3)
                                        await message.respond('скрафтить нагрудник из клюва цапли')
                                    if "Налапники: Отсутствует" in response.text:
                                        await sleep(3)
                                        await message.respond('скрафтить налапники из клюва цапли')
                                    if "Банда: Отсутствует" in response.text:
                                        await sleep(3)
                                        await message.respond('собрать банду')
                                    await sleep(3)
                                    await message.respond('рейд старт')
                        elif "Для входа в" in response.text:
                            response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=message.chat_id))
                            await message.respond('Моя жаба')
                            response = await response
                            if "Имя жабы:" in response.text:
                                bug = int(re.search('Букашки: (\d+)', response.text, re.IGNORECASE).group(1))
                                nas = int(re.search('Настроение.?:.+\((\d+)\)', response.text, re.IGNORECASE).group(1))
                                if nas < 500:
                                    led = int((500 - nas)/25)
                                    if led > 0:
                                        await sleep(3)
                                        await message.respond(f"использовать леденцы {led}")
                        else:
                            await sleep(3)
                            response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=message.chat_id))
                            await message.respond('жаба инфо')
                            response = await response

                            if "(Откормить через" in response.text:
                                time_f = re.search('Откормить через (\d+)ч:(\d+)м', response.text, re.IGNORECASE)
                                if time_f:
                                    hrs = int(time_f.group(1))
                                    min = int(time_f.group(2))
                                    delta = timedelta(hours=hrs, minutes=min, seconds=n)
                                await message.client.send_message(chat, 'откормить жабку', schedule=delta)
                            else:
                                await sleep(3)
                                await message.respond('откормить жабку')
                                delta = timedelta(hours=4, seconds=n)
                                await message.client.send_message(chat, 'откормить жабку', schedule=delta)
                            for number in range(4):
                                delta = delta + timedelta(hours=4)
                                await message.client.send_message(chat, 'откормить жабку', schedule=delta)
                                await sleep(3)
                            if "В подземелье можно" in response.text:
                                dng_s = re.search('подземелье можно через (\d+)ч. (\d+)м.', response.text, re.IGNORECASE)
                                if dng_s:
                                    hrs = int(dng_s.group(1))
                                    min = int(dng_s.group(2))
                                    delta = timedelta(hours=hrs, minutes=min, seconds=n)
                                await message.client.send_message(chat, 'реанимировать жабу', schedule=delta)
                                await message.client.send_message(chat, 'Отправиться в золотое подземелье', schedule=delta + timedelta(seconds=13))
                                await sleep(3)
                                response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=message.chat_id))
                                await message.respond('Моя семья')
                                response = await response
                                if "Ваш жабёныш:" in response.text:
                                    if "Можно покормить через" in response.text:
                                        sem = re.search('покормить через (\d+) ч. (\d+) минут', response.text, re.IGNORECASE)
                                        if sem:
                                            hrs = int(sem.group(1))
                                            min = int(sem.group(2))
                                        delta = timedelta(hours=hrs, minutes=min, seconds=n)
                                        await message.client.send_message(chat, 'покормить жабенка', schedule=delta)
                                    else:
                                        await sleep(3)
                                        await message.respond('покормить жабенка')

                                    if "Можно забрать через" in response.text:
                                        sad = re.search('забрать через (\d+) ч. (\d+) минут', response.text, re.IGNORECASE)
                                        if sad:
                                            hrs = int(sad.group(1))
                                            min = int(sad.group(2))
                                            delta = timedelta(hours=hrs, minutes=min, seconds=n)
                                            await message.client.send_message(chat, 'забрать жабенка', schedule=delta)
                                    else:
                                        await sleep(3)
                                        await message.respond('забрать жабенка')
                                    if "Пойти на махач" in response.text:
                                        sad = re.search('махач через (\d+) ч. (\d+) минут', response.text, re.IGNORECASE)
                                        if sad:
                                            hrs = int(sad.group(1))
                                            min = int(sad.group(2))
                                            delta = timedelta(hours=hrs, minutes=min, seconds=n)
                                            await message.client.send_message(chat, 'отправить жабенка на махач', schedule=delta)
                                    else:
                                        await sleep(3)
                                        await message.respond('отправить жабенка на махач')
                                    await sleep (3)
                                    response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=message.chat_id))
                                    await message.client.send_message(chat, 'война инфо')
                                    response = await response
                                    if "⚔️Состояние⚔️: Не" in response.text:
                                        if message.chat_id in KW:
                                            await sleep(3)
                                            await message.respond('начать клановую войну')
                                    else:
                                        if name + " | Не атаковал" in response.text:
                                            await sleep(3)
                                            await message.respond('реанимировать жабу')
                                            await sleep(3)
                                            await message.respond('напасть на клан')
                            else:
                                dng_s = re.search('жабу можно через (\d+) часов (\d+) минут', response.text, re.IGNORECASE)
                                if dng_s:
                                    hrs = int(dng_s.group(1))
                                    min = int(dng_s.group(2))
                                    delta = timedelta(hours=hrs, minutes=min, seconds=n)
                                    await message.client.send_message(chat, 'завершить работу', schedule=delta)
                                    await message.client.send_message(chat, 'реанимировать жабку', schedule=delta + timedelta(minutes=25, seconds=n))
                                    await message.client.send_message(chat, 'Отправиться в золотое подземелье', schedule=delta + timedelta(minutes=45, seconds=n+13))
        else:
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
                                delta = timedelta(hours=hrs, minutes=min, seconds=n)
                            await message.client.send_message(chat, 'реанимировать жабу', schedule=delta)
                            await message.client.send_message(chat, 'работа грабитель', schedule=delta + timedelta(seconds=13))
                            for number in range(2):
                                delta = delta + timedelta(hours=8)
                                await message.client.send_message(chat, 'реанимировать жабу', schedule=delta)
                                await message.client.send_message(chat, 'работа грабитель', schedule=delta + timedelta(seconds=n))
                                await message.client.send_message(chat, 'завершить работу', schedule=delta + timedelta(hours=2, seconds=n+3))
                                await sleep(1)
                        else:
                            if "жабу можно через" in response.text:
                                time_r = re.search('через (\d+) часов (\d+) минут', response.text, re.IGNORECASE)
                                if time_r:
                                    hrs = int(time_r.group(1))
                                    min = int(time_r.group(2))
                                    delta = timedelta(hours=hrs, minutes=min, seconds=n)
                                await message.client.send_message(chat, 'завершить работу', schedule=delta)
                            elif "можно отправить" in response.text:
                                await sleep(3)
                                await message.respond('реанимировать жабу')
                                await sleep(3)
                                await message.respond('работа грабитель')
                                delta = timedelta(hours=2, seconds=n)
                                await message.client.send_message(chat, 'завершить работу', schedule=delta)
                            else:
                                await sleep(3)
                                await message.respond('завершить работу')
                            for number in range(2):
                                delta = delta + timedelta(hours=6, seconds=3)
                                await message.client.send_message(chat, 'реанимировать жабу', schedule=delta)
                                await message.client.send_message(chat, 'работа грабитель', schedule=delta + timedelta(seconds=n))
                                await message.client.send_message(chat, 'завершить работу', schedule=delta + timedelta(hours=2, seconds=n+3))
                                await sleep(3)
                        if "покормить через" in response.text:
                            time_n = re.search('покормить через (\d+)ч:(\d+)м', response.text, re.IGNORECASE)
                            if time_n:
                                hrs = int(time_n.group(1))
                                min = int(time_n.group(2))
                                delta = timedelta(hours=hrs, minutes=min, seconds=n)
                            await message.client.send_message(chat, 'покормить жабку', schedule=delta)
                        else:
                            delta = timedelta(seconds=n)
                            await message.client.send_message(chat, 'покормить жабку', schedule=delta)
                        for number in range(1):
                            delta = delta + timedelta(hours=12, seconds=3)
                            await message.client.send_message(chat, 'покормить жабку', schedule=delta)
                            await sleep(3)

        if message.sender_id in bak:
            if "Монарх дуэлька" in message.message:
                duel = self.db.get("Дуэлька", "duel", {})
                chatid = str(message.chat_id)
                if chatid in duel:
                    duel.pop(chatid)
                    self.db.set("Дуэлька", "duel", duel)
                    return await message.respond("<b>пью ромашковый чай</b>!")
                duel.setdefault(chatid, {})
                self.db.set("Дуэлька", "duel", duel)
                await message.respond("<b>го дуэли</b>")
            if "Монарх напади" in message.message:
                await message.respond("<b>реанимировать жабу</b>")
                await sleep (3)
                await message.respond("<b>напасть на клан</b>")
            if "Монарх подземелье" in message.message:
                await message.respond("<b>реанимировать жабу</b>")
                await sleep (3)
                await message.respond("<b>отправиться в золотое подземелье</b>")
            if "Монарх с работы" in message.message:
                await message.respond("<b>завершить работу</b>")
            if "Монарх карта" in message.message:
                await message.respond("<b>отправиться за картой</b>")
            if "Монарх на тусу" in message.message:
                await message.respond("<b>реанимировать жабу</b>")
                await sleep (3)
                await message.respond("<b>жабу на тусу</b>")
            if "букашки мне😊" in message.message:
                async with message.client.conversation(chat) as conv:
                    response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=message.chat_id))
                    await message.respond('мой баланс')
                    response = await response
                    if 'Баланс букашек вашей' in response.text:
                        bug = int(re.search('жабы: (\d+)', response.text, re.IGNORECASE).group(1))
                        if bug <100:
                            await message.reply('осталось для похода')
                        else:
                            while bug > 50049:
                                await message.reply('отправить букашки 50000')
                                bug -= 50000
                                await sleep(1)
                            snt = bug-50
                            await message.reply(f'отправить букашки {snt}')
            if "инвентарь мне😊" in message.message:
                async with message.client.conversation(chat) as conv:
                    response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=message.chat_id))
                    await message.respond('мой инвентарь')
                    response = await response
                    if 'Ваш инвентарь:' in response.text:
                        cnd = int(re.search('Леденцы: (\d+)', response.text, re.IGNORECASE).group(1))
                        apt = int(re.search('Аптечки: (\d+)', response.text, re.IGNORECASE).group(1))
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

        if message.chat_id in {707693258}:
            status = self.db.get(self.iriska, 'status', False)
            if not status: return
            if "Фарма" in message.message:
                return await self.client.send_message(chat, "Фарма", schedule=timedelta(minutes=random.randint(1, 20)))
            if "НЕЗАЧЁТ!" in message.message:
                args = [int(x) for x in message.text.split() if x.isnumeric()]
                randelta = random.randint(20, 60)
                if len(args) == 4: delta = timedelta(hours=args[1], minutes=args[2], seconds=args[3]+randelta)
                elif len(args) == 3: delta = timedelta(minutes=args[1], seconds=args[2]+randelta)
                elif len(args) == 2: delta = timedelta(seconds=args[1]+randelta)
                else: return
                sch = (await self.client(functions.messages.GetScheduledHistoryRequest(chat, 1488))).messages
                await self.client(functions.messages.DeleteScheduledMessagesRequest(chat, id=[x.id for x in sch]))
                return await self.client.send_message(chat, 'Фарма', schedule=delta)
            if "ЗАЧЁТ" in message.message or 'УДАЧА' in message.message:
                args = message.text.split()
                for x in args:
                    if x[0] == '+':
                        return self.db.set(self.iriska, 'coins', self.db.get(self.iriska, 'coins', 0) + int(x[1:]))

        if chatid not in duel: return
        if message.sender_id in {1124824021}:
            jaba = "❏ kramikk◬"
            if "Вы бросили вызов на дуэль пользователю " + name in message.message:
                await sleep (3)
                await message.respond('дуэль принять')
                await sleep (3)
                await message.respond('дуэль старт')
            if jaba + ", У вас ничья" in message.message:
                await sleep (3)
                await message.respond('РеанимироватЬ жабу')
            elif "Победитель " + jaba in message.message:
                return
            elif "Победитель уже отыграл" in message.message:
                await sleep (3)
                await message.respond('Спасибо👊')
            else:
                if "Победитель" in message.message:
                    await sleep (3)
                    await message.respond('РеанимироватЬ жабу')
        else:
            if message.sender_id not in {me.id, 1124824021}:
                if "РеанимироватЬ жабу" in message.message:
                    await sleep (3)
                    await message.reply('дуэль')