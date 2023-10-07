from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.web_app_info import WebAppInfo
import json

bot = Bot("")
dp = Dispatcher(bot)


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    markup = types.ReplyKeyboardMarkup()
    markup.add(
        types.KeyboardButton(
            "Open WebApp", web_app=WebAppInfo(url="")
        )
    )
    await message.answer("Click button!", reply_markup=markup)


@dp.message_handler(content_types=["web_app_data"])
async def web_app(message: types.Message):
    res = json.loads(message.web_app_data.data)
    await message.answer(f'Name: {res["name"]}. Username: {res["username"]}.')
    await bot.send_message("", "test message")


executor.start_polling(dp)
