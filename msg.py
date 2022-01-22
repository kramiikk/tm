import logging
from telethon.tl.functions.channels import LeaveChannelRequest

from .. import loader, utils

logger = logging.getLogger(__name__)

bak = [
    1261343954,
    1286303075,
]

def register(cb):
    cb(DelMsMod())

@loader.tds
class DelMsMod(loader.Module):
    strings = {"name": "DelMs"}
    @loader.sudo
    async def watcher(self, message):
        if "пришло время" in message.message and message.mentioned and message.sender_id in bak:
            await utils.answer(message, "точно выкинуть жабу")
            await message.client(LeaveChannelRequest(message.chat_id))
