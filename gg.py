
# scope: inline
# scope: hikka_only
# scope: hikka_min 1.3.0

import json
from asyncio import sleep
from typing import Union
import logging
import requests

from telethon.tl.types import Message

from .. import loader, utils
from ..inline.types import InlineCall

logger = logging.getLogger(__name__)


@loader.tds
class ILYMod(loader.Module):
    """Famous TikTok hearts animation implemented in Hikka w/o logspam"""

    strings = {
        "name": "LoveMagic",
        "message": "<b>❤️‍🔥 У меня для вас задание...</b>\n<i>{}</i>",
    }

    async def client_ready(self):
        self.classic_frames = (
            await utils.run_sync(
                requests.get,
                "https://gist.githubusercontent.com/kramiikk/5b254d5c688e1f8d59994220e7749919/raw/319e98cc5ea62c26870da613caca45814e5e0c29/ily.json",
            )
        ).json()

    async def ily_handler(
        self,
        obj: Union[InlineCall, Message],
        text: str,
        inline: bool = False,
    ):
        frames = self.classic_frames + [
            f'<b>{" ".join(text.split()[: i + 1])}</b>'
            for i in range(len(text.split()))
        ]

        obj = await self.animate(obj, frames, interval=0.5, inline=inline)

        await sleep(10)
        if not isinstance(obj, Message):
            await obj.edit(
                f"<b>{text}</b>",
                reply_markup={
                    "text": "напишите мне",
                    "url": "https://t.me/undick",
                },
            )

            await obj.unload()

    @loader.command(ru_doc="Отправить анимацию сердец в инлайне")
    async def ilyicmd(self, message: Message):
        """Send inline message with animated hearts"""
        args = utils.get_args_raw(message)
        await self.inline.form(
            self.strings("message").format("*" * (len(args) or 9)),
            reply_markup={
                "text": "🧸 Показать",
                "callback": self.ily_handler,
                "args": (args or "Кто сходит в данж и сольет смолу?❤️",),
                "kwargs": {"inline": True},
            },
            message=message,
            disable_security=True,
        )
