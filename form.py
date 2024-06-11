from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.web_app_info import WebAppInfo
import json

bot = Bot("")
dp = Dispatcher(bot)

# --- UX/UI Improvements ---

# 1. Informative Welcome Message with Emojis:


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


# 2. User-Friendly Data Confirmation with Formatting:


@dp.message_handler(content_types=["web_app_data"])
async def web_app(message: types.Message):
    res = json.loads(message.web_app_data.data)
    await message.answer(
        f"Thank you, {res['name']}! ✅ Your data has been successfully submitted.",
        parse_mode="Markdown",
    )

    # Format admin message for better readability

    user_info = (
        f"**New submission:**\n\n*Name:* {res['name']}\n*Username:* {res['username']}"
    )
    await bot.send_message("5032015812", user_info, parse_mode="Markdown")


# Helper function for forwarding messages (unchanged, but good practice)


async def forward_message(chat_id, message):
    if message.text:
        await message.forward(chat_id)
    elif message.sticker:
        await bot.send_sticker(chat_id, message.sticker.file_id)
    elif message.photo:
        await bot.send_photo(chat_id, message.photo[-1].file_id)
    elif message.document:
        await bot.send_document(chat_id, message.document.file_id)
    elif message.animation:
        await bot.send_animation(chat_id, message.animation.file_id)
    elif message.video:
        await bot.send_video(chat_id, message.video.file_id)
    elif message.voice:
        await bot.send_voice(chat_id, message.voice.file_id)
    elif message.audio:
        await bot.send_audio(chat_id, message.audio.file_id)


# 3. Loading Indicator for Admin Replies (using typing indicator):


@dp.message_handler(chat_id=5032015812)
async def reply_to_user(message: types.Message):
    if message.reply_to_message and "User ID:" in message.reply_to_message.text:
        user_id = int(message.reply_to_message.text.split()[-1])
        await bot.send_chat_action(user_id, "typing")
        await forward_message(user_id, message)


# 4. Clearer Message Forwarding to Admin:


@dp.message_handler()
async def forward_to_admin(message: types.Message):
    if message.from_user.id != 5032015812:
        user_mention = message.from_user.mention
        user_id = message.from_user.id
        await bot.send_message(
            5032015812, f"Message from: {user_mention} (User ID: {user_id})"
        )
        await forward_message(5032015812, message)
        await message.reply(
            "Your message has been sent to the admin. Please wait for a response."
        )


executor.start_polling(dp)
