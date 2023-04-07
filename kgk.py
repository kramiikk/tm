import abc
from aiogram.types import Message as AiogramMessage
from .. import loader


@loader.tds
class FeedbackMod(loader.Module):
    """Simple feedback bot for Hikka"""

    __metaclass__ = abc.ABCMeta

    strings = {
        "name": "Feedback",
        "sent": "✅ <b>Your message has been sent to owner</b>",
    }

    async def client_ready(self):
        self.__doc__ = (
            "Feedback bot\n"
            f"Your feeback link: t.me/{self.inline.bot_username}?start=feedback\n"
            "You can freely share it"
        )

    async def aiogram_watcher(self, message: AiogramMessage):
        await self.inline.bot.forward_message(
            self._tg_id,
            message.chat.id,
            message.message_id,
        )
        await message.answer(self.strings("sent"))
        self.inline.ss(message.from_user.id, False)
