# scope: inline_content
# scope: hikka_only

import abc
import logging
import time

from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import Message as AiogramMessage
from telethon.utils import get_display_name

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class FeedbackMod(loader.Module):
    """Simple feedback bot for Hikka"""

    __metaclass__ = abc.ABCMeta

    strings = {
        "name": "Feedback",
        "/start": "🤵‍♀️ <b>Hello. I'm feedback bot of {}. Read /nometa before continuing</b>\n<b>You can send only one message per minute</b>",
        "/nometa": (
            "👨‍🎓 <b><u>Internet-talk rules:</u></b>\n\n"
            "<b>🚫 Do <u>not</u> send just 'Hello'</b>\n"
            "<b>🚫 Do <u>not</u> advertise</b>\n"
            "<b>🚫 Do <u>not</u> insult</b>\n"
            "<b>🚫 Do <u>not</u> split message</b>\n"
            "<b>✅ Write your question in one message</b>"
        ),
        "enter_message": "✍️ <b>Enter your message here</b>",
        "sent": "✅ <b>Your message has been sent to owner</b>",
    }

    async def client_ready(self, client, db) -> None:
        self._me = (await client.get_me()).id
        self._name = utils.escape_html(get_display_name(await client.get_me()))

        if not hasattr(self, "inline"):
            raise Exception("Hikka Only")

        self._bot = self.inline.bot
        self._ratelimit = {}
        self._markup = InlineKeyboardMarkup()
        self._markup.add(
            InlineKeyboardButton(
                "✍️ Leave a message [1 per minute]", callback_data="fb_leave_message"
            )
        )

        self._cancel = InlineKeyboardMarkup()
        self._cancel.add(InlineKeyboardButton("🚫 Cancel", callback_data="fb_cancel"))

        self.__doc__ = (
            "Feedback bot\n"
            f"Your feeback link: t.me/{self.inline.bot_username}?start=feedback\n"
            "You can freely share it"
        )

    async def aiogram_watcher(self, m: AiogramMessage) -> None:
        if m.text == "/start":
            await m.answer(
                self.strings("/start").format(self._name), reply_markup=self._markup
            )
        elif m.text == "/nometa":
            await m.answer(self.strings("/nometa"), reply_markup=self._markup)
        elif self.inline.gs(m.from_user.id) == "fb_send_message":
            await self._bot.forward_message(self._me, m.chat.id, m.message_id)
            await self._bot.send_message(self._me, m.from_user.id, parse_mode="HTML")
            await m.answer(self.strings("sent"))
            self._ratelimit[m.from_user.id] = time.time() + 60
            self.inline.ss(m.from_user.id, False)

    async def feedback_callback_handler(self, call: CallbackQuery) -> None:
        """
        Handles button clicks
        @allow: all
        """
        if call.data == "fb_cancel":
            self.inline.ss(call.from_user.id, False)
            await self._bot.delete_message(
                call.message.chat.id, call.message.message_id
            )
            return

        if call.data != "fb_leave_message":
            return

        if (
            call.from_user.id in self._ratelimit
            and self._ratelimit[call.from_user.id] > time.time()
        ):
            await call.answer(
                f"You can send next message in {self._ratelimit[call.from_user.id] - time.time():.0f} second(-s)",
                show_alert=True,
            )
            return

        self.inline.ss(call.from_user.id, "fb_send_message")
        await self._bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=self.strings("enter_message"),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=self._cancel,
        )


#     async def emojicmd(self, message):
#         args = utils.get_args_raw(message)
#         c = args.split(" ")
#         emoji = [
#             "😀",
#             "😃",
#             "😄",
#             "😁",
#             "😆",
#             "😅",
#             "🤣",
#             "🥰",
#             "😇",
#             "😊",
#             "😉",
#             "🙃",
#             "🙂",
#             "😂",
#             "😍",
#             "🤩",
#             "😘",
#             "😗",
#             "☺",
#             "😚",
#             "😙",
#             "🤗",
#             "🤑",
#             "😝",
#             "🤪",
#             "😜",
#             "😛",
#             "😋",
#             "🤭",
#             "🤫",
#             "🤔",
#             "🤐",
#             "🤨",
#             "😐",
#             "😑",
#             "😌",
#             "🤥",
#             "😬",
#             "🙄",
#             "😒",
#             "😏",
#             "😶",
#             "😔",
#             "😪",
#             "🤤",
#             "😴",
#             "😷",
#             "🤒",
#             "🤕",
#             "🤢",
#             "🤯",
#             "🤮",
#             "🤠",
#             "🤧",
#             "🥳",
#             "🥵",
#             "😎",
#             "🥶",
#             "🤓",
#             "🥴",
#             "🧐",
#             "😵",
#             "😕",
#             "😳",
#             "😢",
#             "😲",
#             "😥",
#             "😯",
#             "😰",
#             "😮",
#             "😨",
#             "😧",
#             "🙁",
#             "😦",
#             "😟",
#             "🥺",
#             "😭",
#             "😫",
#             "😱",
#             "🥱",
#             "😖",
#             "😤",
#             "😣",
#             "😡",
#             "😞",
#             "😠",
#             "😓",
#             "🤬",
#             "😩",
#             "😈",
#             "👿",
#         ]
#         d = []
#         e = len(c)
#         for i in range(e):
#             rand = random.choice(emoji)
#             d.append(c[i])
#             d.append(rand)
#         f = len(d) - 1
#         d.pop(f)
#         t = "".join(d)
#         await message.edit(t)

#     async def chatcmd(self, message):
#         chat = str(message.chat_id)
#         await message.respond(f"Айди чата: <code>{chat}</code>")

#     async def delmsgcmd(self, message):
#         msg = [
#             msg
#             async for msg in message.client.iter_messages(
#                 message.chat_id, from_user="me"
#             )
#         ]
#         if utils.get_args_raw(message):
#             args = int(utils.get_args_raw(message))
#         else:
#             args = len(msg)
#         for i in range(args):
#             await msg[i].delete()
#             await sleep(0.16)

#     async def shifrcmd(self, message):
#         text = utils.get_args_raw(message).lower()
#         txtnorm = dict(
#             zip(
#                 map(ord, "йцукенгшщзхъфывапролджэячсмитьбю. ?!,-:;"),
#                 "3ëjmqv9ô§üldйa¿42zэouəà>ý5eö$0¡<61¥g8tъ7",
#             )
#         )
#         txt = text.translate(txtnorm)
#         await message.edit(txt)
#         await sleep(300)
#         await message.delete()

#     async def deshifrcmd(self, message):
#         text = str(await message.get_reply_message()).split("'")
#         await message.delete()
#         txt = text[1]

#         txtnorm = dict(
#             zip(
#                 map(ord, "3ëjmqv9ô§üldйa¿42zэouəà>ý5eö$0¡<61¥g8tъ7"),
#                 "йцукенгшщзхъфывапролджэячсмитьбю. ?!,-:;7",
#             )
#         )
#         txte = txt.translate(txtnorm)
#         await message.client.send_message("me", txte)

#     @loader.owner
#     async def qgcmd(self, m):
#         jup = ""
#         for a in utils.get_args_raw(m):
#             if a.lower() in alp:
#                 arp = alp[a.lower()]
#                 if a.isupper():
#                     arp = arp.upper()
#             else:
#                 arp = a
#             jup += arp
#         await utils.answer(m, jup)


# alp = {
#     "а": "a",
#     "ә": "ä",
#     "б": "b",
#     "в": "v",
#     "г": "g",
#     "ғ": "ğ",
#     "д": "d",
#     "е": "e",
#     "ж": "j",
#     "з": "z",
#     "и": "i",
#     "й": "y",
#     "к": "k",
#     "қ": "k",
#     "л": "l",
#     "м": "m",
#     "н": "n",
#     "ң": "ń",
#     "о": "o",
#     "ө": "ö",
#     "п": "p",
#     "р": "r",
#     "с": "s",
#     "т": "t",
#     "у": "w",
#     "ұ": "u",
#     "ү": "ü",
#     "ф": "f",
#     "х": "h",
#     "һ": "h",
#     "ы": "ı",
#     "і": "i",
#     "ч": "ch",
#     "ц": "ts",
#     "ш": "c",
#     "щ": "cc",
#     "э": "e",
#     "я": "ya",
# }
