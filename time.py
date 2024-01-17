import asyncio
import datetime

from telethon.tl import functions

from .. import loader, utils


@loader.tds
class AutoProfileMod(loader.Module):
    """Automatic stuff for your profile :P"""

    strings = {
        "name": "AutoProfile",
        "invalid_args": ("lol"),
        "enabled_name": "<b>Enabled name clock <emoji document_id=5212932275376759608>✅</emoji></b>",
        "name_not_enabled": (
            "<b>Name clock is not enabled <emoji"
            " document_id=5215273032553078755>❎</emoji></b>"
        ),
        "disabled_name": (
            "<b>Name clock disabled <emoji"
            " document_id=5215273032553078755>❎</emoji></b>"
        ),
        "_cfg_time": "Use timezone 1, -1, -3 etc.",
        "missing_time": "Your message is missing the time placeholder {time}.",
    }

    def __init__(self):
        self.name_enabled = False
        self.raw_name = None
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "timezone",
                "+6",
                lambda: self.strings["_cfg_time"],
            ),
        )

    async def client_ready(self, client, db):
        self.client = client
        self._me = await client.get_me()

    @loader.command()
    async def cfautoprofcmd(self, message):
        """To specify the timezone via the config"""
        name = self.strings["name"]
        await self.allmodules.commands["config"](
            await utils.answer(message, f"{self.get_prefix()}config {name}")
        )

    @loader.command()
    async def autonamecmd(self, message):
        """autoname '<message, time as {time}>'"""

        msg = utils.get_args(message)
        if len(msg) != 1:
            return await utils.answer(message, self.strings["invalid_args"])
        raw_name = msg[0]
        if "{time}" not in raw_name:
            return await utils.answer(message, self.strings["missing_time"])
        self.name_enabled = True
        self.raw_name = raw_name
        await self.allmodules.log("start_autoname")
        await utils.answer(message, self.strings["enabled_name"])

        while self.name_enabled:
            offset = datetime.timedelta(hours=self.config["timezone"])
            tz = datetime.timezone(offset)
            time1 = datetime.datetime.now(tz)
            current_time = time1.strftime("%H:%M")
            name = raw_name.format(time=current_time)
            await self.client(functions.account.UpdateProfileRequest(first_name=name))
            await asyncio.sleep(61.3)

    @loader.command()
    async def stopautonamecmd(self, message):
        """just write .stopautoname"""

        if self.name_enabled is False:
            return await utils.answer(message, self.strings["name_not_enabled"])
        self.name_enabled = False
        await self.allmodules.log("stop_autoname")
        await utils.answer(message, self.strings["disabled_name"])
        await self.client(functions.account.UpdateProfileRequest(first_name="00:00"))
