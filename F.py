# scope: inline_content

import asyncio
import logging
import re

from aiogram.types import *
from telethon.tl.types import *

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class InlineGgMod(loader.Module):
    """Non-spam"""
    strings = {
        "name": "InlineGg",
        "imghl": "🧐 <b>Azal*n g*y?</b>",
        "tired": "👉"
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
            await call.answer("лох")
            return
        src = f"Клан Вадим и его жабехи Состав:"
        msg = f"Клан Вадим и его жабехи:\n"
        get = await self.client.get_messages(1655814348, search=src)
        for i in get:
            ids = re.search(r"id: (.+)", i.text).group(1)
            reg = re.findall(r"\n(\d+)", i.text)
            for s in reg:
                src = f"{ids} {s} Уровень:"
                get = await self.client.get_messages(1655814348, search=src)
                for p in get:
                    ger = re.search(r"ь: (\d+)", p.text)
                    msg += f"\nУровень: {ger.group(1)}"
                    if "Жаба:" in p.text:
                        ger = re.search(r"а: (.+)", p.text).group(1)
                        msg += f" Жаба: {ger}"
        await call.edit(msg)
        await asyncio.sleep(13)
        await call.edit(self.strings('tired'), reply_markup=[[{
            'text': '💔 Не нажимай!',
            'url': 'https://t.me/+PGb_kTUvwYcyN2Qy'
        }]])
        await call.unload()

    async def ggcmd(self, message: Message) -> None:
        """Sends gg message"""
        await self.inline.form(self.strings('imghl'), message=message, reply_markup=[[{
            'text': '🤠 G*y',
            'callback': self.inline__handler,
            'args': (True,)
        }, {
            'text': '💃 Ballerina',
            'callback': self.inline__handler,
            'args': (False,)
        }]], force_me=False)
