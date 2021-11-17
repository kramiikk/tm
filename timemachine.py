import time
import asyncio
import logging
import datetime
import threading
from .. import loader, utils
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# requires: apscheduler

logger = logging.getLogger(__name__)

@loader.tds
class SchedMod(loader.Module):
    """sched"""
    strings = {'name': 'Sched'}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

        map = 707693258

        async def zaraz():
            for number in range(7):
                await client.send_message(map, 'заразить р')
                await sleep(3)

        scheduler = AsyncIOScheduler()
        scheduler.add_job(zaraz, CronTrigger.from_crontab('*/20 * * * *', timezone='Europe/Moscow'))
        scheduler.start()

        asyncio.get_event_loop().run_forever()
