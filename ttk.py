import logging

from .. import loader, utils

logger = logging.getLogger(__name__)


def register(cb):
    cb(kkMod())


@loader.tds
class kkMod(loader.Module):
    """Алина, я люблю тебя!"""

    strings = {
        "name": "kk",
    }

    async def client_ready(self, client, db):
        self.client = client

    async def watcher(self, event):
        chat = utils.get_chat_id(event)
        if "1 атака" in event.raw_text:
            await self.client.send_message(1655814348, event.raw_text)
