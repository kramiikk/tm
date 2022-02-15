# scope: inline_content

from .. import loader, utils
from telethon.tl.types import *
from aiogram.types import *
import logging
import asyncio

logger = logging.getLogger(__name__)


@loader.tds
class InlineGgMod(loader.Module):
    """Non-spammy ghoul module"""
    strings = {
        "name": "InlineGg",
        "imghl": "🧐 <b>Azal*n g*y?</b>",
        "tired": "😾 <b>Правильно \"Azal*n g*y\"</b>"
    }

    def get(self, *args) -> dict:
        return self.db.get(self.strings['name'], *args)

    def set(self, *args) -> None:
        return self.db.set(self.strings['name'], *args)

    async def client_ready(self, client, db) -> None:
        self.db = db
        self.client = client

    async def inline_close(self, call: CallbackQuery) -> None:
        await call.close()

    async def inline__handler(self, call: CallbackQuery, correct: bool) -> None:
        if not correct:
            await call.answer('Не то!😜')
            return

        await call.edit(f"👊 🪵 👌")
        await asyncio.sleep(1)

        await call.edit(self.strings('tired'))
        await asyncio.sleep(10)
        await call.edit(self.strings('tired'), reply_markup=[[{
            'text': '💔 Не нажимай, я стесняюсь!',
            'url': 'https://t.me/Azalonn'
        }]])
        await call.unload()

    async def ggcmd(self, message: Message) -> None:
        """Sends ghoul message"""
        await self.inline.form(self.strings('imghl'), message=message, reply_markup=[[{
            'text': '🤠 G*y',
            'callback': self.inline__handler,
            'args': (True,)
        }, {
            'text': '💃 Ballerina',
            'callback': self.inline__handler,
            'args': (False,)
        }]], force_me=False)
