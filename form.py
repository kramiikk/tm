from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.web_app_info import WebAppInfo
import json

bot = Bot("")
dp = Dispatcher(bot)


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    markup = types.ReplyKeyboardMarkup()
    markup.add(types.KeyboardButton("Open WebApp", web_app=WebAppInfo(url="https://kramiikk.github.io/tm/")))
    await message.answer(f"{message.from_user.first_name}👋 Click the button!", reply_markup=markup)


@dp.message_handler(content_types=["web_app_data"])
async def web_app(message: types.Message):
    res = json.loads(message.web_app_data.data)
    await message.answer(f'Thank you, {res["name"]} !')
    await bot.send_message("5032015812", f'Name: {res["name"]}. Username: {res["username"]}.')

@dp.message_handler()
async def forward_to_admin(message: types.Message):
    await message.forward(5032015812)
    user_mention = message.from_user.mention
    user_id = message.from_user.id
    await bot.send_message(5032015812, f"Message from: {user_mention} (ID: {user_id})")

@dp.message_handler(chat_id=5032015812)
async def reply_to_user(message: types.Message):
    if message.reply_to_message:
        reply_text = message.reply_to_message.text
        user_id = int(reply_text.split("ID: ")[-1])
        await message.forward(user_id)

executor.start_polling(dp)