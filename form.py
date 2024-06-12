from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.web_app_info import WebAppInfo
import json

bot = Bot("TOKEN")
dp = Dispatcher(bot)

# --- UX/UI Improvements ---

# 1. Informative Welcome Message with Emojis


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton(
            "Open WebApp 🌐", web_app=WebAppInfo(url="https://kramiikk.github.io/tm/")
        )
    )
    await message.answer(
        f"Hi {message.from_user.first_name}! 👋\n\n"
        f"To get started, please fill out the form by clicking the button below 👇",
        reply_markup=markup,
    )
    await bot.send_message(
        5032015812,
        f"Bot started by {message.from_user.first_name} *User ID:* {message.from_user.id}",
    )


# 2. User-Friendly Data Confirmation with Formatting


@dp.message_handler(content_types=["web_app_data"])
async def web_app(message: types.Message):
    res = json.loads(message.web_app_data.data)
    await message.answer(
        f"Thank you, {res['name']}! ✅ Your data has been successfully submitted.",
        parse_mode="Markdown",
    )

    user_info = f"**New submission:**\n\n*Name:* {res['name']}\n*Username:* {res['username']}\n*User ID:* {message.from_user.id}"
    await bot.send_message("5032015812", user_info, parse_mode="Markdown")


# Helper function for forwarding messages


async def forward_message(chat_id, message):
    await bot.copy_message(chat_id, message.chat.id, message.message_id)
    await bot.send_message(
        "5032015812", f"Message forwarded to {chat_id}", parse_mode="Markdown"
    )


# 3. Forward admin replies to the correct user


@dp.message_handler(
    lambda message: message.chat.id == 5032015812, content_types=types.ContentType.ANY
)
async def reply_to_user(message: types.Message):
    if message.reply_to_message and "User ID:" in message.reply_to_message.text:
        user_id = int(message.reply_to_message.text.split()[-1])
        await forward_message(user_id, message)


# 4. Forward all user messages to the admin


@dp.message_handler(content_types=types.ContentType.ANY)
async def forward_to_admin(message: types.Message):
    if message.from_user.id != 5032015812:
        user_mention = message.from_user.mention
        user_id = message.from_user.id
        await bot.send_message(
            5032015812, f"Message from: {user_mention} User ID: {user_id}"
        )
        await forward_message(5032015812, message)
        await message.reply(
            "Your message has been sent to the admin. Please wait for a response. ☺️"
        )


# Start polling


executor.start_polling(dp)
