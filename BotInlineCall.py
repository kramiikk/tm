from ..inline.types import BotInlineCall
from telethon.tl.types import Message
from .. import loader


@loader.tds
class AiMod(loader.Module):
    """🇺🇦"""

    strings = {"name": "aia"}

    async def client_ready(self, client, db) -> None:
        self.db = db
        self.client = client

    async def watcher(self, m) -> None:
        if not isinstance(m, Message):
            return
        if "куат" in m.message.casefold():
            await self.inline.bot.send_message(1785723159, m.text, parse_mode="HTML")
        elif "lover" in m.message.casefold():
            await self.inline.bot.send_photo(
                m.chat_id,
                photo="https://i.postimg.cc/BZK4Cwgv/mona-4.jpg",
                caption="где хуй?",
                reply_markup=self.inline._generate_markup(
                    {
                        "text": "это",
                        "url": "https://t.me/toadbothelpchat/2661777",
                    }
                ),
            )
