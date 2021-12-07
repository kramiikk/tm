import random
import logging
from .. import loader, utils
import datetime
from telethon import functions
from telethon.tl.types import Message
from telethon import events
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import re
from datetime import timedelta

# requires: apscheduler

logger = logging.getLogger(__name__)

@loader.tds
class SchedulerMod(loader.Module):
    """Шедулер"""
    strings = {'name': 'Scheduler'}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

        TOAD_STATION = -1001447960786
        TOM_REDDL = -1001441941681

        async def feed_toad(chat):
            await client.send_message(chat, 'откормить жабу')
            async with client.conversation(chat) as conv:
                response = conv.wait_event(events.NewMessage(incoming=True, from_users=1124824021, chats=chat))
                await asyncio.sleep(3)
                await client.send_message(chat, 'откормить жабку')
                response = await response
                next_food_hours = 4
                next_food_minutes = 3
                if "Откармливать жабу" in response.raw_text:

                   pattern = re.compile('через (.) ч:(.?.) мин', re.IGNORECASE) #паттерн времени
                   matcher = pattern.search(response.raw_text)

                   next_food_hours = int(matcher.group(1)) #получаем часы из сообщения
                   next_food_minutes = int(matcher.group(2)) #получаем минуты из сообщения

                delta = timedelta(hours=next_food_hours, minutes=next_food_minutes)
                await client.send_message(chat, 'откормить жабку', schedule=delta)

                for number in range(5):
                   delta += timedelta(hours=4, minutes=3)
                   await client.send_message(chat, 'откормить жабку', schedule=delta)
                   await asyncio.sleep(1)

                delta = timedelta(hours=1)
                await client.send_message(chat, 'отправиться в золотое подземелье', schedule=delta)

                for number in range(15):
                   delta += timedelta(hours=1, minutes=30)
                   await client.send_message(chat, 'отправиться в золотое подземелье', schedule=delta)
                   await asyncio.sleep(1)


        async def send_kid_to_kindergarten():
            await client.send_message(TOM_REDDL, 'отправить жабенка в детский сад')
            await client.send_message(TOAD_STATION, 'отправить жабенка в детский сад')

        async def send_kid_to_fighting():
            await client.send_message(TOM_REDDL, 'отправить жабенка на махач')
            await client.send_message(TOAD_STATION, 'отправить жабенка на махач')

        async def feed_kid():
            await client.send_message(TOM_REDDL, 'покормить жабенка')
            await client.send_message(TOAD_STATION, 'покормить жабенка')
            await client.send_message(TOAD_STATION, '/dick@kraft28_bot')

        async def kid_from_kindergarten():
            await client.send_message(TOAD_STATION, 'забрать жабенка')

        async def feed_toads():
            await feed_toad(TOM_REDDL)
            await feed_toad(TOAD_STATION)

        scheduler = AsyncIOScheduler()
        scheduler.add_job(send_kid_to_kindergarten, CronTrigger.from_crontab('03 6 * * *', timezone='Europe/Moscow'))
        scheduler.add_job(send_kid_to_fighting, CronTrigger.from_crontab('10 8 * * *', timezone='Europe/Moscow'))
        scheduler.add_job(feed_kid, CronTrigger.from_crontab('10 22,10 * * *', timezone='Europe/Moscow'))
        scheduler.add_job(kid_from_kindergarten, CronTrigger.from_crontab('6 12 * * *', timezone='Europe/Moscow'))
        scheduler.add_job(feed_toads, CronTrigger.from_crontab('5 0 * * *', timezone='Europe/Moscow'))

        scheduler.start()

        asyncio.get_event_loop().run_forever()
