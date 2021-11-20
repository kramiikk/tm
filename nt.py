import re
import random
from .. import loader, utils
from datetime import timedelta
from telethon import functions
from telethon.tl.types import Message
from telethon import events
from asyncio import sleep

@loader.tds
class KramikkMod(loader.Module):
    """777"""
    strings = {'name': 'Kramikk'}

    async def watcher(self, message):
        bak = {1646740346, 1261343954, 1785723159, 1486632011, 1682801197, 1863720231, 1775420029, 1286303075}
        chat = message.chat_id
        me = await message.client.get_me()
        name = me.first_name
        randelta = random.randint(142, 156)

        if message.sender_id == me.id:
            if "Моя жаба" in message.message:
                async with message.client.conversation(chat) as conv:
                    response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=message.chat_id))
                    await sleep(3)
                    await message.client.send_message(chat, 'жаба инфо')
                    response = await response

                    if "Жабу можно покормить" in response.text:
                        delta = timedelta(hours=12, seconds=randelta)
                        delta_r = timedelta(hours=12, seconds=59)
                        await sleep(3)
                        await message.respond('покормить жабу')
                        await message.client.send_message(chat, 'Покормить жабу', schedule=delta)
                        await message.client.send_message(chat, 'Моя жаба', schedule=delta_r)

                    if "Жабу можно отправить" in response.text:
                        delta = timedelta(hours=2, seconds=randelta)
                        delta_r = timedelta(hours=2, seconds=59)
                        await sleep(3)
                        await message.respond('реанимировать жабу')
                        await sleep(3)
                        await message.respond('поход в столовую')
                        await message.client.send_message(chat, 'Завершить работу', schedule=delta)
                        await message.client.send_message(chat, 'Моя жаба', schedule=delta_r)

                    if "Можно забрать" in response.text:
                        delta = timedelta(hours=6, seconds=randelta)
                        delta_r = timedelta(seconds=randelta)
                        await sleep(3)
                        await message.respond('завершить работу')
                        await message.client.send_message(chat, 'поход в столовую', schedule=delta)
                        await message.client.send_message(chat, 'Моя жаба', schedule=delta_r)

        if message.sender_id in {1124824021}:
            delta = timedelta(minutes=randelta)
            if "Сейчас выбирает ход: " + name in message.message:
                await message.click(0)
            if "Господин " + name in message.message:
                await sleep (3)
                await message.respond('реанимировать жабу')
                await sleep (3)
                await message.respond('отправиться за картой')
            if "Тебе жаба, Милая Беседа ❤" in message.message:
                await message.client.send_message(chat, 'Моя жаба', schedule=delta)

        if message.sender_id in bak:
            if "букашки мне😊" in message.message:
                await sleep(randelta)
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
                await sleep(randelta)
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
