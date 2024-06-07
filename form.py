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
    await message.answer(f'Thank you, {res["name"]} !')

    user_mention = f'<a href="tg://user?id={message.from_user.id}">{res["name"]}</a>'
    message_text = f'Name: {user_mention}. Username: {res["username"]}.'

    await bot.send_message("", message_text)


@dp.message_handler()
async def forward_to_you(message: types.Message):
    user_mention = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
    await bot.send_message("", f"Message from {user_mention}:")
    await bot.forward_message("", message.chat.id, message.message_id)


executor.start_polling(dp)
