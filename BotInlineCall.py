import abc
from aiogram.types import Message as AiogramMessage
from .. import loader
from ..inline.types import BotInlineCall


@loader.tds
class AiMod(loader.Module):
    """🇺🇦"""

    __metaclass__ = abc.ABCMeta

    strings = {"name": "aia"}

    async def client_ready(self, client, db):
        self.db = db
        self.client = client

    async def aiogram_watcher(self, m: AiogramMessage):
        if "куат" in m.text.casefold():
            await self.inline.bot.send_message(
                1785723159, m.text, parse_mode="HTML"
            )
        elif "lover" in m.text.casefold():
            await self.inline.bot.send_file(
                1785723159,
                photo="https://i.postimg.cc/BZK4Cwgv/mona-4.jpg",
                caption="где хуй?",
                reply_markup=self.inline._generate_markup(
                    {
                        "text": "это",
                        "url": "https://t.me/toadbothelpchat/2661777",
                    }
                ),
            )
