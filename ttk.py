import logging
import telethon

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
        if ("дуэль старт") or ("напасть на клан") in event.raw_text:
            async with self.client.conversation(chat) as conv:
                response = conv.wait_event(
                    telethon.events.MessageEdited(
                        incoming=True,
                        from_users=1124824021,
                        chats=chat,
                    )
                )
                response = await response
                if "1 атака" in response.text:
                    await self.client.send_message(1655814348, response.text)