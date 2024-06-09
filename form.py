import json

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

bot = Bot("6562832316:AAFoe24u8zC6GQ1_bnv4UsZyVjMDUTrg-Ys")
dp = Dispatcher(bot)


class UserData(StatesGroup):
    waiting_for_feedback = State()


def create_keyboard(buttons):
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        *[KeyboardButton(button) for button in buttons]
    )


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    markup = create_keyboard(["Open WebApp", "Leave Feedback"])
    await message.answer("×͜~", reply_markup=markup)


@dp.message_handler(text="Open WebApp")
async def web_app_button(message: types.Message):
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton(
            "Go to WebApp", web_app=WebAppInfo(url="https://kramiikk.github.io/tm/")
        )
    )
    await message.answer("Great! Open the WebApp:", reply_markup=markup)


@dp.message_handler(content_types=types.ContentTypes.WEB_APP_DATA)
async def handle_web_app(message: types.Message):
    data = json.loads(message.web_app_data.data)
    name = data.get("name")
    username = data.get("username")

    await message.answer(f"Hello, {name}! Your username is: @{username}")
    await bot.send_message(
        "5032015812", text=f"New data:\nName: {name}\nUsername: {username}"
    )


@dp.message_handler(text="Leave Feedback")
async def ask_for_feedback(message: types.Message):
    await message.answer("Please write your feedback:")
    await UserData.waiting_for_feedback.set()


@dp.message_handler(state=UserData.waiting_for_feedback)
async def process_feedback(message: types.Message, state: FSMContext):
    feedback = message.text
    user_mention = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
    await bot.send_message("5032015812", f"Feedback from {user_mention}:\n{feedback}")
    await message.answer("Thank you for your feedback!")
    await state.finish()


@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def forward_to_admin(message: types.Message):
    user_mention = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
    await bot.send_message("5032015812", f"Message from {user_mention}:")
    await bot.forward_message("5032015812", message.chat.id, message.message_id)


if __name__ == "__main__":
    executor.start_polling(dp)
