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

bot = Bot("")
dp = Dispatcher(bot, storage=MemoryStorage())


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


@dp.message_handler(content_types=["web_app_data"])
async def process_web_app_data(message: types.Message):
    data = json.loads(message.web_app_data.data)
    await message.answer(
        f"Thanks, {data['name']}! I received your data from the WebApp:\n"
    )
    await bot.send_message("", f"N: {data['name']} U: {data['username']}")


@dp.message_handler(text="Leave Feedback")
async def ask_for_feedback(message: types.Message):
    await message.answer("Please write your feedback:")
    await UserData.waiting_for_feedback.set()


@dp.message_handler(state=UserData.waiting_for_feedback)
async def process_feedback(message: types.Message, state: FSMContext):
    feedback = message.text
    user_mention = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
    await bot.send_message("", f"Feedback from {user_mention}:\n{feedback}")
    await message.answer("Thank you for your feedback!")
    await state.finish()


@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def forward_to_admin(message: types.Message):
    user_mention = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
    await bot.send_message("", f"Message from {user_mention}:")
    await bot.forward_message("", message.chat.id, message.message_id)


if __name__ == "__main__":
    executor.start_polling(dp)
