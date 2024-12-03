import asyncio
import time
from datetime import datetime

from telethon import types
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest

from .. import loader, utils
from ..inline.types import InlineCall, InlineQuery


@loader.tds
class InlinePingMod(loader.Module):
    """Accurate inline pinger with extended chat stats"""

    strings = {
        "name": "InlinePing",
        "ping_text": "🏓 <b>Ping:</b> {overall_ping:.2f} ms",
        "stats_text": (
            "📊 <b>Chat Stats:</b>\n"
            "├ <b>Title:</b> {title}\n"
            "├ <b>ID:</b> <code>{chat_id}</code>\n"
            "├ <b>Type:</b> {chat_type}\n"
            "├ <b>Created:</b> {created_at}\n"
            "├ 👥 <b>Members:</b> {members}\n"
            "├ 👤 <b>Online:</b> ~{online_count}\n"
            "├ 🤖 <b>Bots:</b> {bots}\n"
            "├ 👻 <b>No Avatar:</b> {no_avatar}\n"
            "├ 🛡️ <b>Admins:</b> {admins}\n"
            "├ 🖼️ <b>Media:</b> {media_messages}\n"
            "└ 💬 <b>Messages:</b> {total_messages}\n"
        ),
        "error_text": "❌ <b>Error:</b> {error}",
    }

    async def client_ready(self, client, db):
        self._client = client

    async def _measure_ping(self):
        """Measures overall ping"""
        start = time.perf_counter()
        await self._client.get_me()
        return (time.perf_counter() - start) * 1000

    async def _get_chat_stats(self, chat):
        """Gets extended chat statistics"""
        try:
            if isinstance(chat, types.Channel):
                full_chat = await self._client(GetFullChannelRequest(chat))
                admins = full_chat.full_chat.admins_count or 0
                total_messages = full_chat.full_chat.read_inbox_max_id
                chat_type = "Channel"
            else:
                full_chat = await self._client(GetFullChatRequest(chat.id))
                admins = len(
                    [
                        p.participant
                        for p in await self._client.get_participants(chat)
                        if isinstance(
                            p.participant,
                            (types.ChatParticipantAdmin, types.ChatParticipantCreator),
                        )
                    ]
                )
                total_messages = (
                    full_chat.full_chat.read_inbox_max_id
                    if hasattr(full_chat.full_chat, "read_inbox_max_id")
                    else 0
                )
                chat_type = "Group" if isinstance(chat, types.Chat) else "Private"
            participants = await self._client.get_participants(chat)
            members = len(participants)
            online_count = sum(
                1
                for p in participants
                if p.status and isinstance(p.status, types.UserStatusOnline)
            )
            bots = sum(1 for p in participants if p.bot)
            no_avatar = sum(1 for p in participants if not p.photo)

            media_messages = (
                await self._client(
                    telethon.tl.functions.messages.SearchRequest(
                        peer=chat,
                        q="",
                        filter=telethon.tl.types.InputMessagesFilterPhotoVideo(),
                        limit=0,
                    )
                )
            ).count

            created_at = (
                datetime.fromtimestamp(chat.date).strftime("%Y-%m-%d")
                if chat.date
                else "Unknown"
            )

            return {
                "title": getattr(chat, "title", "Unknown"),
                "chat_id": chat.id,
                "chat_type": chat_type,
                "created_at": created_at,
                "members": members,
                "online_count": online_count,
                "bots": bots,
                "no_avatar": no_avatar,
                "admins": admins,
                "media_messages": media_messages,
                "total_messages": total_messages,
            }
        except Exception as e:
            return {"error": str(e)}

    @loader.command()
    async def iping(self, message):
        """Get ping and chat statistics"""
        await self._do_iping(message)

    async def _do_iping(self, message, call=None):
        ping = await self._measure_ping()
        chat = await message.get_chat()
        stats = await self._get_chat_stats(chat)

        if "error" in stats:
            text = self.strings["error_text"].format(**stats)
        else:
            text = f"{self.strings['ping_text'].format(overall_ping=ping)}\n\n{self.strings['stats_text'].format(**stats)}"
        if call:
            await call.edit(
                text,
                reply_markup=[
                    [{"text": "🔄 Refresh Ping", "callback": self._refresh_ping}]
                ],
            )
        else:
            await self.inline.form(
                text,
                message=message,
                reply_markup=[
                    [{"text": "🔄 Refresh Ping", "callback": self._refresh_ping}]
                ],
            )

    async def _refresh_ping(self, call: InlineCall):
        """Refreshes the ping"""
        await self._do_iping(call.original_message, call)

    async def ping_inline_handler(self, query: InlineQuery):
        """Inline handler for ping"""
        ping = await self._measure_ping()
        return {
            "title": f"Ping: {ping:.2f} ms",
            "description": "Ping",
            "message": self.strings["ping_text"].format(overall_ping=ping),
            "thumb": "https://te.legra.ph/file/5d8c7f1960a3e126d916a.jpg",
        }
