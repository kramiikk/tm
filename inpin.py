from telethon import TelegramClient, events, utils, functions, types
import time
import asyncio
from telethon.tl.types import Channel, Chat, Message
from telethon.errors import ChatAdminRequiredError
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest

from .. import loader, utils


@loader.tds
class InlinePingMod(loader.Module):
    """Compact inline pinger with chat stats"""

    strings = {
        "name": "InlinePing",
        "ping_text": "🏓 <b>Ping:</b> {ping:.2f} ms",
        "stats_text": "📊 <b>{title}:</b>\nID: <code>{chat_id}</code>\nType: {chat_type}\nCreated: {created_at}\nMembers: {members}\nOnline: ~{online_count}\nBots: {bots}\nAdmins: {admins}\nMessages: {total_messages}\n",
        "error_text": "❌ <b>Error:</b> {error}",
    }

    async def client_ready(self, client, db):
        self._client = client

    @loader.command()
    async def iping(self, message):
        """Get ping and chat statistics"""
        await self._ping(message)

    async def _get_chat_stats(self, chat):
        if isinstance(chat, Channel):
            full_chat = await self._client(GetFullChannelRequest(chat))
            participants = full_chat.users
            chat_type = "Supergroup" if chat.megagroup else "Channel"
            admins = full_chat.full_chat.admins_count or 0
            messages = full_chat.full_chat.read_outbox_max_id
        elif isinstance(chat, Chat):
            full_chat = await self._client(GetFullChatRequest(chat.id))
            participants = full_chat.users
            chat_type = "Group"
            admins = sum(
                1
                for p in participants
                if p.participant
                and isinstance(
                    p.participant,
                    (types.ChatParticipantAdmin, types.ChatParticipantCreator),
                )
            )
            messages = getattr(full_chat.full_chat, "read_outbox_max_id", 0)
        else:
            raise TypeError("Unsupported chat type")
        online = sum(
            1
            for p in participants
            if p.status and isinstance(p.status, types.UserStatusOnline)
        )
        bots = sum(1 for p in participants if p.bot)

        return {
            "title": utils.escape_html(getattr(chat, "title", "Unknown")),
            "chat_id": chat.id,
            "chat_type": chat_type,
            "created_at": chat.date.strftime("%Y-%m-%d") if chat.date else "Unknown",
            "members": len(participants),
            "online_count": online,
            "bots": bots,
            "admins": admins,
            "total_messages": messages,
        }

    async def _ping(self, message, call=None):
        start = time.perf_counter()
        await self._client.get_me()
        ping = (time.perf_counter() - start) * 1000

        try:
            chat = await self._client.get_entity(message.chat_id)
            stats = await self._get_chat_stats(chat)
            text = f"{self.strings['ping_text'].format(ping=ping)}\n\n{self.strings['stats_text'].format(**stats)}"
        except (ChatAdminRequiredError, TypeError, ValueError) as e:
            text = self.strings["error_text"].format(error=str(e))
        except Exception as e:
            text = self.strings["error_text"].format(
                error=f"An unexpected error occurred: {e}"
            )
        refresh_button = [
            {"text": "🔄 Refresh", "callback": lambda c: self._ping(message, c)}
        ]
        if call:
            await call.edit(text, reply_markup=[refresh_button])
        else:
            await self.inline.form(text, message=message, reply_markup=[refresh_button])

    async def ping_inline_handler(self, query):
        async def _update_ping(call):
            start = time.perf_counter()
            await self._client.get_me()
            ping = (time.perf_counter() - start) * 1000
            await call.edit(
                self.strings["ping_text"].format(ping=ping),
                reply_markup=[[{"text": "🔄 Refresh", "callback": _update_ping}]],
            )

        start = time.perf_counter()
        await self._client.get_me()
        ping = (time.perf_counter() - start) * 1000

        try:
            if query.chat_id:
                message = Message(peer_id=query.chat_id, out=query.out)
                stats_text = await self._ping(message)
                message_text = (
                    f"{self.strings['ping_text'].format(ping=ping)}\n\n{stats_text}"
                )
                reply_markup = [[{"text": "🔄 Refresh", "callback": _update_ping}]]
            else:
                message_text = self.strings["ping_text"].format(ping=ping)
                reply_markup = None
            return [
                {
                    "type": "article",
                    "id": "ping_result",
                    "title": f"Ping: {ping:.2f} ms",
                    "description": "Ping and Chat Stats" if query.chat_id else "Ping",
                    "input_message_content": {
                        "message_text": message_text,
                        "parse_mode": "HTML",
                    },
                    "reply_markup": reply_markup,
                    "thumb_url": "https://te.legra.ph/file/5d8c7f1960a3e126d916a.jpg",
                }
            ]
        except Exception as e:
            return [
                {
                    "type": "article",
                    "id": "error_result",
                    "title": "Error",
                    "description": "An error occurred",
                    "input_message_content": {
                        "message_text": self.strings["error_text"].format(error=str(e)),
                        "parse_mode": "HTML",
                    },
                }
            ]
