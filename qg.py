# scope: inline

import abc
import logging
import time

from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup)
from aiogram.types import Message as AiogramMessage
from telethon.utils import get_display_name

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class FbackMod(loader.Module):
    """yoooh"""

    __metaclass__ = abc.ABCMeta

    strings = {
        "name": "Feedback",
        "/start": "🤵‍♀️ <b>Привет. Это бот обратной связи с {}. Прочитайте /nometa, прежде чем продолжить.</b>\n<b>Вы можете отправлять только одно сообщение в минуту.</b>",
        "/nometa": (
            "👨‍🎓 <b><u>Правила общения в Интернете:</u></b>\n\n"
            "🚫 <b>Не <u>пишите</u> просто 'Привет'</b>\n"
            "🚫 <b>Не <u>отправляйте</u> рекламу</b>\n"
            "🚫 <b>Не <u>адресуйте</u> оскорбления</b>\n"
            "✅ <b>Отправьте послание одним сообщением</b>"
        ),
        "enter": "✍️ <b>Отлично, можете отправить сообщение</b>",
        "sent": "✅ <b>Ваше сообщение отправлено</b>",
    }

    def get(self, *args) -> dict:
        return self._db.get(self.strings["name"], *args)

    def set(self, *args) -> None:
        return self._db.set(self.strings["name"], *args)

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
        elif message.text == "/nometa":
            await message.answer(self.strings("/nometa"), reply_markup=self._markup)
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

    @loader.owner
    async def qgcmd(self, m):
        jup = ""
        for a in utils.get_args_raw(m):
            if a.lower() in alp:
                arp = alp[a.lower()]
                if a.isupper():
                    arp = arp.upper()
            else:
                arp = a
            jup += arp
        await utils.answer(m, jup)


alp = {
    "а": "a",
    "ә": "ä",
    "б": "b",
    "в": "v",
    "г": "g",
    "ғ": "ğ",
    "д": "d",
    "е": "e",
    "ж": "j",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "қ": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "ң": "ń",
    "о": "o",
    "ө": "ö",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "w",
    "ұ": "u",
    "ү": "ü",
    "ф": "f",
    "х": "h",
    "һ": "h",
    "ы": "ı",
    "і": "i",
    "ч": "ch",
    "ц": "ts",
    "ш": "c",
    "щ": "cc",
    "э": "e",
    "я": "ya",
}
