from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.types.web_app_info import WebAppInfo
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import json

bot = Bot("6562832316:AAFoe24u8zC6GQ1_bnv4UsZyVjMDUTrg-Ys")
dp = Dispatcher(bot, storage=MemoryStorage())

# === States Group ===


class UserData(StatesGroup):
    waiting_for_feedback = State()


# === Keyboard Creation (Simplified) ===


def create_keyboard(buttons):
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        *[KeyboardButton(button) for button in buttons]
    )


# === Message Handlers ===


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    try:
        markup = create_keyboard(["Open WebApp", "Leave Feedback"])
        await message.answer(
            "Hi! 👋\n\nI'm a bot that can:\n- Open the WebApp\n- Take your feedback\n",
            reply_markup=markup,
        )
    except Exception as e:
        await message.answer(f"Oops, something went wrong. Please try again later. {e}")


@dp.message_handler(text="Open WebApp")
async def web_app_button(message: types.Message):
    try:
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton(
                "Go to WebApp", web_app=WebAppInfo(url="https://kramiikk.github.io/tm/")
            )
        )
        await message.answer("Great! Open the WebApp:", reply_markup=markup)
    except Exception as e:
        await message.answer("Oops, something went wrong. Please try again later. {e}")


@dp.message_handler(content_types=["web_app_data"])
async def process_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        name = data.get("name")
        username = data.get("username")

        if name and username:
            await message.answer(
                f"Thanks, {name}! I received your data from the WebApp:\n"
            )
            await bot.send_message("5032015812", f"N: {name} U: {username}")
        else:
            await message.answer("Something went wrong. Please try again.")
    except Exception as e:
        await message.answer(
            f"Oops, something went wrong processing your data. Please try again. {e}"
        )


@dp.message_handler(text="Leave Feedback")
async def ask_for_feedback(message: types.Message):
    try:
        await message.answer("Please write your feedback:")
        await UserData.waiting_for_feedback.set()
    except Exception as e:
        await message.answer(f"Oops, something went wrong. Please try again later.{e}")


@dp.message_handler(state=UserData.waiting_for_feedback)
async def process_feedback(message: types.Message, state: FSMContext):
    try:
        feedback = message.text
        user_mention = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
        await bot.send_message(
            "5032015812", f"Feedback from {user_mention}:\n{feedback}"
        )
        await message.answer("Thank you for your feedback!")
        await state.finish()
    except Exception as e:
        await message.answer(
            f"Oops, something went wrong sending your feedback. Please try again later. {e}"
        )


@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def forward_to_admin(message: types.Message):
    try:
        user_mention = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
        await bot.send_message("5032015812", f"Message from {user_mention}:")
        await bot.forward_message("5032015812", message.chat.id, message.message_id)
    except Exception as e:
        await message.answer(f"Error forwarding message to admin: {e}")


# === Start the Bot ===

if __name__ == "__main__":
    executor.start_polling(dp)
