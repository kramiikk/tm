from .. import loader, utils
from ..inline.types import InlineQuery  # type: ignore

import logging

from telethon.tl.types import Message  # type: ignore
from telethon.utils import get_display_name  # type: ignore

logger = logging.getLogger(__name__)


@loader.tds
class MyVizitkaMod(loader.Module):
    strings = {"name": "MyVizitka"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "custom_message",
                "<b>Тест</b>",
                lambda: "Custom message in .myvizit\nMay contain {me}, {prefix}, {platform} keywords",
            ),
            loader.ConfigValue(
                "button_1",
                ["My bot", "https://t.me/jiberrbot"],
                lambda: "You 1 button",
                validator=loader.validators.Series(min_len=0, max_len=2),
            ),
            loader.ConfigValue(
                "button_2",
                ["My channel", "https://t.me/kzuaaa"],
                lambda: "You 2 button",
                validator=loader.validators.Series(min_len=0, max_len=2),
            ),
            loader.ConfigValue(
                "button_3",
                ["My account", "https://t.me/kzuaa"],
                lambda: "You 3 button",
                validator=loader.validators.Series(min_len=0, max_len=2),
            ),
            loader.ConfigValue(
                "file_url",
                "https://i.pinimg.com/564x/b9/30/e6/b930e6476d705d7e92f7b961e61d5141.jpg",
                lambda: "Direct link to photo/video/gif/music",
            ),
            loader.ConfigValue(
                "type_file",
                "photo",
                lambda: "Type of file specified in file_url",
                validator=loader.validators.Choice(["photo", "video", "audio", "gif"]),
            ),
        )

    def _get_mark(self, btn_count: int) -> dict:
        return (
            {
                "text": self.config[f"button_{str(btn_count)}"][0],
                "url": self.config[f"button_{str(btn_count)}"][1],
            }
            if self.config[f"button_{str(btn_count)}"]
            else {}
        )

    async def client_ready(self):
        self.me = await self._client.get_me()

    @loader.unrestricted
    async def myvizitcmd(self, message: Message):
        """Command for displaying a business card"""
        m = {x: self._get_mark(x) for x in range(7)}
        me = (
            "<b><a"
            f' href="tg://user?id={self.me.id}">{get_display_name(self.me)}</a></b>'
        )
        prefix = self.get_prefix()
        platform = utils.get_named_platform()
        await self.inline.form(
            disable_security=True,
            message=message,
            text=self.config["custom_message"].format(
                me=me, prefix=prefix, platform=platform
            ),
            reply_markup=[
                [
                    *([m[1]] if m[1] else []),
                    *([m[2]] if m[2] else []),
                    *([m[3]] if m[3] else []),
                ],
            ],
            **{self.config["type_file"]: self.config["file_url"]},
        )

    @loader.inline_handler(ru_doc="Моя визитка")
    async def myvizit(self, _: InlineQuery) -> dict:
        """My inline card"""
        m = {x: self._get_mark(x) for x in range(7)}
        me = (
            "<b><a"
            f' href="tg://user?id={self.me.id}">{get_display_name(self.me)}</a></b>'
        )
        prefix = self.get_prefix()
        platform = utils.get_named_platform()

        return {
            "title": "MyVizitka",
            "description": "My business card",
            "message": self.config["custom_message"].format(
                me=me,
                prefix=prefix,
                platform=platform,
            ),
            "thumb": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Info_Simple_bw.svg/1200px-Info_Simple_bw.svg.png",
            "reply_markup": [
                [
                    *([m[1]] if m[1] else []),
                    *([m[2]] if m[2] else []),
                    *([m[3]] if m[3] else []),
                ],
            ],
        }
