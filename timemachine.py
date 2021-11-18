import time
import asyncio
import logging
import datetime
import threading
from asyncio import sleep
from .. import loader, utils
from apscheduler.triggers.cron import CronTrigger
from telethon.tl.functions.users import GetFullUserRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon.errors.rpcerrorlist import UsernameOccupiedError
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest

# requires: apscheduler

logger = logging.getLogger(__name__)

@loader.tds
class SchedMod(loader.Module):
    """Timemachine"""
    strings = {'name': 'Timemachine'}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

        map = 707693258

        async def zaraz():
            for number in range (7):
                await client.send_message(map, 'заразить р')
                await sleep (13)

        async def off():
            now = datetime.now(timezone.utc)
            firstname = f"ʍօղɑɾϲհ 🔴(афк) {now.hour+6}:{now.minute}"
            await client(UpdateProfileRequest(first_name=firstname))

        scheduler = AsyncIOScheduler()
        scheduler.add_job(zaraz, CronTrigger.from_crontab('*/30 * * * *', timezone='Asia/Almaty'))
        scheduler.add_job(off, CronTrigger.from_crontab('*/3 * * * *', timezone='Asia/Almaty'))
        scheduler.start()
