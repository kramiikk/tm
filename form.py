from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.web_app_info import WebAppInfo
import json

bot = Bot("6562832316:AAFoe24u8zC6GQ1_bnv4UsZyVjMDUTrg-Ys")
dp = Dispatcher(bot)


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    markup = types.ReplyKeyboardMarkup()
    markup.add(
        types.KeyboardButton(
            "Open WebApp", web_app=WebAppInfo(url="https://kramiikk.github.io/tm/")
        )
    )

    await message.answer(
        """
        Welcome to my bot!
        
        <b>How to interact with our bot:</b>

        • Click the "Open WebApp" button to test web application.
        • Send any message to this chat to send it to me.
        """,
        parse_mode="HTML",
    )


@dp.message_handler(content_types=["web_app_data"])
async def web_app(message: types.Message):
    res = json.loads(message.web_app_data.data)
    await message.answer(f'Thank you, {res["name"]} !')
    await bot.send_message(
        "5032015812", f'Name: {res["name"]}. Username: {res["username"]}.'
    )


@dp.message_handler(content_types=types.ContentTypes.ANY)
async def forward_to_admin(message: types.Message):
    user_mention = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
    await bot.send_message(
        "5032015812", f"Message from {user_mention}:", parse_mode="HTML"
    )
    await bot.forward_message("5032015812", message.chat.id, message.message_id)
    await message.answer("Thank you for your feedback!")


@dp.message_handler(user_id="5032015812", content_types=types.ContentTypes.ANY)
async def send_reply_to_user(message: types.Message):
    user_id = message.reply_to_message.forward_from.id
    await bot.send_message(user_id, f"Admin reply: {message.text}")


executor.start_polling(dp)
