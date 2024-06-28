import asyncio
import logging
import time
from datetime import datetime
from typing import Callable, Tuple

import numpy as np
from dateutil.relativedelta import relativedelta

from .. import loader, utils

# Данные для обучения модели предсказания времени создания аккаунта
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


# Класс для предсказания времени создания аккаунта на основе ID Telegram
class Function:
    def __init__(self, order: int = 3):
        # Устанавливаем порядок полиномиальной функции, используемой для аппроксимации
        self.order = 3

        # Распаковываем данные в отдельные списки для ID Telegram (x) и меток времени (y)
        self.x, self.y = self._unpack_data()
        # Аппроксимируем полиномиальной функцией данные
        self._func = self._fit_data()

    # Распаковываем данные из словаря в массивы numpy
    def _unpack_data(self) -> Tuple[list, list]:
        x_data = np.array(list(map(int, data.keys())))
        y_data = np.array(list(data.values()))

        return (x_data, y_data)

    # Аппроксимируем данные полиномиальной функцией с помощью numpy.polyfit
    def _fit_data(self) -> Callable[[int], int]:
        fitted = np.polyfit(self.x, self.y, self.order)
        return np.poly1d(fitted)

    # Добавляем новую точку данных в обучающие данные
    def add_datapoint(self, pair: tuple):
        pair[0] = str(pair[0])

        data.update([pair])

        self._func = self._fit_data()

    # Предсказываем время создания аккаунта для заданного ID Telegram
    def func(self, tg_id: int) -> int:
        value = self._func(tg_id)
        current = time.time()

        # Убеждаемся, что предсказанное время не в будущем
        value = min(value, current)
        return value


logger = logging.getLogger(__name__)


# Модуль бота Telegram для получения времени создания аккаунта
@loader.tds
class AcTimeMod(loader.Module):
    """Модуль для получения времени создания аккаунта"""

    strings = {
        "name": "Время аккаунта",
        "info": "Получить дату и время регистрации аккаунта!",
        "error": "Ошибка!",
    }

    def __init__(self):
        # Настраиваем шаблон сообщения ответа
        self.config = loader.ModuleConfig(
            "answer_text",
            (
                "⏳ Этот аккаунт: {0}\n🕰 Зарегистрирован: {1}\n\nP.S. Скрипт модуля"
                " обучен на количестве запросов от разных ID, поэтому данные"
                " могут быть уточнены"
            ),
            lambda m: self.strings("cfg_answer_text", m),
        )
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    # Форматируем метку времени Unix в удобочитаемую строку даты
    def time_format(self, unix_time: int, fmt="%Y-%m-%d") -> str:
        result = [str(datetime.utcfromtimestamp(unix_time).strftime(fmt))]

        # Вычисляем разницу во времени между текущим моментом и заданной меткой времени
        d = relativedelta(datetime.now(), datetime.utcfromtimestamp(unix_time))
        result.append(f"{d.years} лет, {d.months} месяцев, {d.days} дней")

        return result

    # Обработчик команды для получения времени создания аккаунта
    @loader.unrestricted
    @loader.ratelimit
    async def actimecmd(self, message):
        """
         - получить дату и время регистрации аккаунта [beta]
        P.S. Вы также можете отправить команду в ответ на сообщение
        """
        try:
            # Создаем экземпляр класса Function для предсказания
            interpolation = Function()
            # Получаем сообщение в ответ, если оно существует
            reply = await message.get_reply_message()

            # Предсказываем время создания аккаунта на основе ID Telegram
            if reply:
                date = self.time_format(
                    unix_time=round(interpolation.func(int(reply.sender.id)))
                )
            else:
                date = self.time_format(
                    unix_time=round(interpolation.func(int(message.from_id)))
                )
            # Отправляем сообщение ответа с предсказанным временем создания аккаунта
            await utils.answer(
                message, self.config["answer_text"].format(date[0], date[1])
            )
        except Exception as e:
            # Обрабатываем любые исключения и отправляем сообщение об ошибке
            await utils.answer(message, f'{self.strings["error"]}\n\n{e}')
            if message.out:
                await asyncio.sleep(5)
                await message.delete()