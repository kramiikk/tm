import asyncio
import logging
import time
from datetime import datetime
from typing import Tuple

import numpy as np
from dateutil.relativedelta import relativedelta

from .. import loader, utils

logger = logging.getLogger(__name__)

data = {
    "5396587273": 1648014800,
    "5336336790": 1646368100,
    "4317845111": 1620028800,
    "3318845111": 1618028800,
    "2018845111": 1608028800,
    "1919230638": 1598028800,
    "755000000": 1548028800,
    "782000000": 1546300800,
    "727572658": 1543708800,
    "616816630": 1529625600,
    "391882013": 1509926400,
    "400169472": 1499904000,
    "369669043": 1492214400,
    "234480941": 1464825600,
    "200000000": 1451606400,
    "150000000": 1434326400,
    "10000000": 1413331200,
    "7679610": 1389744000,
    "2768409": 1383264000,
    "1000000": 1380326400,
}


class Function:
    def __init__(self, order: int = 3):
        self.order = order
        self.x, self.y = self._unpack_data()
        self._func = self._fit_data()

    def _unpack_data(self) -> Tuple[list, list]:
        x_data = np.array(list(map(int, data.keys())))
        y_data = np.array(list(data.values()))
        return x_data, y_data

    def _fit_data(self) -> object:
        fitted = np.polyfit(self.x, self.y, self.order)
        return np.poly1d(fitted)

    def add_datapoint(self, pair: tuple):
        if not isinstance(pair[0], str) or not pair[0].isdigit():
            raise ValueError("Invalid Telegram ID")
        if not isinstance(pair[1], (int, float)):
            raise ValueError("Invalid timestamp")
        data[pair[0]] = pair[1]  # Directly update the data dictionary
        self._func = self._fit_data()

    def func(self, tg_id: int) -> int:
        value = self._func(tg_id)
        current = time.time()
        return min(value, current)


@loader.tds
class AcTimeMod(loader.Module):
    strings = {
        "name": "Account Time",
        "info": "Get the account registration date and time!",
        "error": "Error!",
        "cfg_answer_text": "⏳ This account: {0}\n🕰 A registered: {1}\nP.S. The module script is trained with the number of requests from different ids, so the data can be refined",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "answer_text",
            self.strings("cfg_answer_text"),
            lambda m: self.strings("cfg_answer_text", m),
        )
        self.name = self.strings["name"]
        self.interpolation = Function()

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    def time_format(self, unix_time: int, fmt="%Y-%m-%d") -> str:
        result = [str(datetime.utcfromtimestamp(unix_time).strftime(fmt))]
        d = relativedelta(datetime.now(), datetime.utcfromtimestamp(unix_time))
        result.append(f"{d.years} years, {d.months} months, {d.days} days")
        return result

    @loader.unrestricted
    @loader.ratelimit
    async def actimecmd(self, message):
        try:
            reply = await message.get_reply_message()
            tg_id = int(reply.sender.id) if reply else int(message.from_id)
            registration_time = self.interpolation.func(tg_id)
            date_str = self.time_format(int(registration_time))
            await utils.answer(
                message, self.config["answer_text"].format(date_str[0], date_str[1])
            )
        except ValueError as e:
            await utils.answer(message, f"Invalid Telegram ID: {e}")
        except Exception as e:
            await utils.answer(message, f"An error occurred: {e}")
            if message.out:
                await asyncio.sleep(5)
                await message.delete()
