from math import floor
from asyncio import sleep
from .. import loader, utils
from datetime import timedelta
from telethon.tl.types import Message
from telethon import events, functions, types, sync
from telethon.tl.functions.users import GetFullUserRequest
from telethon.errors.rpcerrorlist import UsernameOccupiedError
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
import asyncio, datetime, inspect, io, logging, os, threading, time, random, re, requests, urllib.parse

#requires: urllib requests

logger = logging.getLogger(__name__)

def register(cb):
    cb(KramikkMod())

@loader.tds
class KramikkMod(loader.Module):
    """Алина, я люблю тебя!"""
    strings = {
        'name': 'Kramikk',
    }

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.me = await client.get_me()
        self.status = db.get('Status', 'status', {})

    async def watcher(self, message):
        bak = {1646740346, 1261343954, 1785723159, 1486632011, 1682801197, 1863720231, 1775420029, 1286303075, 1746686703, 1459363960, 1423368454}
        chat = message.chat_id
        chatid= str(message.chat_id)
        duel = self.db.get('Дуэлька', 'duel', {})
        jb = "jaba"
        name = self.me.first_name
        randelta = random.randint(3, 21+1)

        if message.sender_id in {1124824021}:
            if "Сейчас выбирает ход: " + name in message.message:
                await message.click(0)
            if "Господин " + name in message.message:
                await sleep (3)
                await message.respond('реанимировать жабу')
                await sleep (3)
                await message.respond('отправиться за картой')

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

if chatid not in duel: return

if message.sender_id not in {self.me.id, 1124824021}:
    if "РеанимироватЬ жабу" in message.message:
        await sleep (1)
        await message.reply('дуэль')

if message.sender_id in {1124824021}:
    if "Вы бросили вызов на дуэль пользователю " + name in message.message:
        await sleep (1)
        await message.respond('дуэль принять')
        await sleep (1)
        await message.respond('дуэль старт')

    if self.status[jb] + ", У вас ничья" in message.message:
        await sleep (1)
        await message.respond('РеанимироватЬ жабу')

    if "Победитель" in message.message:
        if "Победитель " + self.status[jb] + "!!!" in message.message:
            return
        elif "Победитель уже отыграл" in message.message:
            await sleep (1)
            await message.respond('Спасибо😃😘 Не забудь деактивировать дуэльку!')
        else:
            await sleep (1)
            await message.respond('РеанимироватЬ жабу')
