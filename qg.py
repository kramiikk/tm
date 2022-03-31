# scope: inline

import abc
import asyncio
import logging
import time
from random import choice, randint

from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, InlineQueryResultArticle,
                           InputTextMessageContent)
from aiogram.types import Message as AiogramMessage
from telethon.utils import get_display_name

from .. import loader, utils
from ..inline import InlineQuery

logger = logging.getLogger(__name__)


@loader.tds
class FbackMod(loader.Module):
    """yoooh"""

    __metaclass__ = abc.ABCMeta

    strings = {
        "name": "Fback",
        "/start": "🤵‍♀️ <b>Привет. Это бот обратной связи с {}. Прочитайте /note, прежде чем продолжить.</b>\n<b>Вы можете отправлять только одно сообщение в минуту.</b>",
        "/note": (
            "👨‍🎓 <b><u>Правила общения в Интернете:</u></b>\n\n"
            "🚫 <b>Не <u>пишите</u> просто 'Привет'</b>\n"
            "🚫 <b>Не <u>отправляйте</u> рекламу</b>\n"
            "🚫 <b>Не <u>адресуйте</u> оскорбления</b>\n"
            "✅ <b>Отправьте послание одним сообщением</b>"
        ),
        "enter": "✍️ <b>Отлично, можете отправить сообщение</b>",
        "sent": "✅ <b>Ваше сообщение отправлено</b>",
    }

    async def inline__close(self, call: CallbackQuery) -> None:
        await call.delete()

    def get(self, *args) -> dict:
        return self._db.get(self.strings["name"], *args)

    def set(self, *args) -> None:
        return self._db.set(self.strings["name"], *args)

    async def coin_inline_handler(self, query: InlineQuery) -> None:
        """
        Heads or tails?
        @allow: all
        """

        r = "🦅 Heads" if randint(0, 1) else "🪙 Tails"
        await query.answer(
            [
                InlineQueryResultArticle(
                    id=utils.rand(20),
                    title="Toss a coin",
                    description="Trust in the God of luck, and he will be by your side!",
                    input_message_content=InputTextMessageContent(
                        f"<i>The God of luck tells us...</i> <b>{r}</b>",
                        "HTML",
                        disable_web_page_preview=True,
                    ),
                    thumb_url="https://img.icons8.com/external-justicon-flat-justicon/64/000000/external-coin-pirates-justicon-flat-justicon-1.png",
                    thumb_width=128,
                    thumb_height=128,
                )
            ],
            cache_time=0,
        )

    async def random_inline_handler(self, query: InlineQuery) -> None:
        """
        [number] - Send random number less than specified
        @allow: all
        """

        if not query.args:
            return

        a = query.args

        if not str(a).isdigit():
            return

        await query.answer(
            [
                InlineQueryResultArticle(
                    id=utils.rand(20),
                    title=f"Toss random number less or equal to {a}",
                    description="Trust in the God of luck, and he will be by your side!",
                    input_message_content=InputTextMessageContent(
                        f"<i>The God of luck screams...</i> <b>{randint(1, int(a))}</b>",
                        "HTML",
                        disable_web_page_preview=True,
                    ),
                    thumb_url="https://img.icons8.com/external-flaticons-flat-flat-icons/64/000000/external-numbers-auction-house-flaticons-flat-flat-icons.png",
                    thumb_width=128,
                    thumb_height=128,
                )
            ],
            cache_time=0,
        )

    async def choice_inline_handler(self, query: InlineQuery) -> None:
        """
        Make a choice
        @allow: all
        """

        if not query.args or not query.args.count("|"):
            return

        args = query.args
        text = args.split("|")
        words = text[1]
        text1 = text[0].split(" ")
        time = int(text1[0]) * 60
        words1 = " ".join(text1[1:])

        await query.answer(
            [
                InlineQueryResultArticle(
                    id=utils.rand(20),
                    title="Choose one item from list",
                    description="Trust in the God of luck, and he will be by your side!",
                    input_message_content=InputTextMessageContent(
                        f"<i>The God of luck whispers...</i> <b>{words1}</b>",
                        "HTML",
                        disable_web_page_preview=True,
                    ),
                    thumb_url="https://img.icons8.com/external-filled-outline-geotatah/64/000000/external-choice-customer-satisfaction-filled-outline-filled-outline-geotatah.png",
                    thumb_width=128,
                    thumb_height=128,
                )
            ],
            cache_time=0,
        )
        await asyncio.sleep(time)
        await query.edit(words)

    async def client_ready(self, client, db) -> None:
        self._db = db
        self._client = client
        self._me = (await client.get_me()).id
        self._name = utils.escape_html(get_display_name(await client.get_me()))

        self._bot = self.inline._bot
        self._ratelimit = {}
        self._markup = InlineKeyboardMarkup()
        self._markup.add(
            InlineKeyboardButton("✍️ Нажмите чтобы написать", callback_data="leave")
        )

        self._cancel = InlineKeyboardMarkup()
        self._cancel.add(InlineKeyboardButton("🚫 Отмена", callback_data="cancel"))

        self.__doc__ = f"Your feeback link: t.me/{self.inline._bot_username}?start\n"

    async def aiogram_watcher(self, message: AiogramMessage) -> None:
        if message.text == "/start":
            await message.answer(
                self.strings("/start").format(self._name), reply_markup=self._markup
            )
        elif message.text == "/note":
            await message.answer(self.strings("/note"), reply_markup=self._markup)
        elif self.inline.gs(message.from_user.id) == "send":
            await self._bot.forward_message(
                self._me, message.chat.id, message.message_id
            )
            await message.answer(self.strings("sent"))
            self._ratelimit[message.from_user.id] = time.time() + 60
            self.inline.ss(message.from_user.id, False)

    async def feedback_callback_handler(self, call: CallbackQuery) -> None:
        """
        Handles button clicks
        @allow: all
        """
        if call.data == "cancel":
            self.inline.ss(call.from_user.id, False)
            await self._bot.delete_message(
                call.message.chat.id, call.message.message_id
            )
            return

        if call.data != "leave":
            return

        if (
                call.from_user.id in self._ratelimit
                and self._ratelimit[call.from_user.id] > time.time()
        ):
            await call.answer(
                f"Сообщение можно отправить через {self._ratelimit[call.from_user.id] - time.time():.0f} секунд",
                show_alert=True,
            )
            return

        self.inline.ss(call.from_user.id, "send")
        await self._bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=self.strings("enter"),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=self._cancel,
        )
