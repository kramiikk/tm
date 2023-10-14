from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo
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
    await message.answer(f'Thank you, {res["name"]} !')
    await bot.send_message("", f'Name: {res["name"]}. Username: {res["username"]}.')


start_polling(dp)
