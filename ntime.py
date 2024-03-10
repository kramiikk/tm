import asyncio
from datetime import datetime, timedelta
from telethon.tl.functions.account import UpdateProfileRequest

from .. import loader, utils


@loader.tds
class AutoNameUpdater(loader.Module):
    """Automatically updates the Telegram name with the current time."""

    strings = {
        "name": "AutoName",
        "invalid_args": "<b>Invalid arguments.</b>",
        "enabled_name": "<b>Enabled name clock ✅</b>",
        "name_not_enabled": "<b>Name clock is not enabled ❎</b>",
        "disabled_name": "<b>Name clock disabled ❎</b>",
    }

    async def client_ready(self, client, db):
        self.client = client
        self.name_enabled = False

    @loader.command()
    async def autonamecmd(self, message):
        """Usage: .autoname '<message, time as {time}>'"""
        msg = utils.get_args(message)
        if len(msg) != 1 or "{time}" not in msg[0]:
            return await utils.answer(message, self.strings["invalid_args"])
        self.client.name_enabled = True
        raw_name = msg[0]
        await self.allmodules.log("start_autoname")
        await utils.answer(message, self.strings["enabled_name"])

        try:
            while self.client.name_enabled:
                current_time = datetime.now() + timedelta(hours=5)
                name = raw_name.format(time=current_time.strftime("%H:%M"))
                await self.client(UpdateProfileRequest(first_name=name))
                await asyncio.sleep(59.9)
        except Exception as e:
            self.client.name_enabled = False
            await utils.answer(message, f"<b>Stopped due to an error: {e}</b>")

    @loader.command()
    async def stopautonamecmd(self, message):
        """Stops the automatic name update."""
        if not self.client.name_enabled:
            return await utils.answer(message, self.strings["name_not_enabled"])
        self.client.name_enabled = False
        await self.allmodules.log("stop_autoname")
        await utils.answer(message, self.strings["disabled_name"])
        await self.client(UpdateProfileRequest(first_name="00:00"))
