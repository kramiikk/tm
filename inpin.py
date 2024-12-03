from telethon import TelegramClient, types
from telethon.errors import ChatAdminRequiredError
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest

import time
from typing import Union, Dict, Any

from .. import loader, utils

@loader.tds
class InlinePingMod(loader.Module):
    """Compact inline pinger with detailed chat stats"""

    strings = {
        "name": "InlinePing",
        "ping_text": "🏓 <b>Ping:</b> {ping:.2f} ms",
        "stats_text": "📊 <b>{title}:</b>\n"
        "ID: <code>{chat_id}</code>\n"
        "Type: {chat_type}\n"
        "Members: {members}\n"
        "Deleted: {deleted_accounts}\n"
        "Admins: {admins}\n"
        "Bots: {bots}\n"
        "Messages: {total_messages}\n",
        "error_text": "❌ <b>Error:</b> {error}",
    }

    async def client_ready(self, client, db):
        self._client = client

    async def _get_chat_stats(self, chat):
        try:
            # Common data extraction
            chat_title = utils.escape_html(getattr(chat, "title", "Unknown"))
            chat_id = chat.id
            chat_type = (
                "Supergroup" if isinstance(chat, types.Channel) and chat.megagroup
                else "Channel" if isinstance(chat, types.Channel)
                else "Group" if isinstance(chat, types.Chat)
                else "Unknown"
            )

            # Fetch full chat details
            try:
                full_chat = (
                    await self._client(GetFullChannelRequest(chat)) 
                    if isinstance(chat, types.Channel)
                    else await self._client(GetFullChatRequest(chat.id))
                )
            except Exception:
                full_chat = None

            # Participant details
            try:
                participants = await self._client.get_participants(chat)
                
                # Optimized admin counting
                admins_count = sum(
                    1 for p in participants 
                    if p.admin or getattr(p, 'is_creator', False)
                )
                
                bots_count = sum(1 for p in participants if p.bot)
                deleted_accounts = sum(1 for p in participants if p.deleted)
                members_count = len(participants)
            except Exception:
                admins_count = bots_count = deleted_accounts = members_count = 0

            # Total messages fallback
            total_messages = (
                getattr(full_chat.full_chat, 'read_outbox_max_id', 0) 
                if full_chat else 0
            )

            return {
                "title": chat_title,
                "chat_id": chat_id,
                "chat_type": chat_type,
                "members": members_count,
                "deleted_accounts": deleted_accounts,
                "admins": admins_count,
                "bots": bots_count,
                "total_messages": total_messages,
            }
        except Exception:
            # Graceful fallback with minimal error info
            return {
                "title": "Error",
                "chat_id": getattr(chat, "id", 0),
                "chat_type": "Unknown",
                "members": 0,
                "deleted_accounts": 0,
                "admins": 0,
                "bots": 0,
                "total_messages": 0,
            }

    @loader.command()
    async def iping(self, message):
        """Get ping and chat statistics"""
        await self._ping(message)

    async def _ping(self, message, call=None):
        start = time.perf_counter_ns()
        await self._client.get_me()
        ping = (time.perf_counter_ns() - start) / 1_000_000

        try:
            chat = await self._client.get_entity(message.chat_id)
            stats = await self._get_chat_stats(chat)

            text = (
                f"{self.strings['ping_text'].format(ping=ping)}\n\n"
                f"{self.strings['stats_text'].format(**stats)}"
            )
            
            # Create refresh button with closure
            async def refresh_callback(call):
                start = time.perf_counter_ns()
                await self._client.get_me()
                ping = (time.perf_counter_ns() - start) / 1_000_000

                await call.edit(
                    f"{self.strings['ping_text'].format(ping=ping)}\n\n"
                    f"{self.strings['stats_text'].format(**stats)}",
                    reply_markup=[refresh_button]
                )

            refresh_button = [{"text": "🔄 Refresh", "callback": refresh_callback}]

            if call:
                await call.edit(text, reply_markup=[refresh_button])
            else:
                await self.inline.form(text, message=message, reply_markup=[refresh_button])

        except Exception as e:
            text = self.strings["error_text"].format(error=str(e))
            await self.inline.form(text, message=message)

    # Inline handler remains mostly the same, with minor optimizations
    async def ping_inline_handler(self, query):
        start = time.perf_counter_ns()
        await self._client.get_me()
        ping = (time.perf_counter_ns() - start) / 1_000_000

        try:
            if query.chat_id:
                chat = await self._client.get_entity(query.chat_id)
                stats = await self._get_chat_stats(chat)
                message_text = (
                    f"{self.strings['ping_text'].format(ping=ping)}\n\n"
                    f"{self.strings['stats_text'].format(**stats)}"
                )

                async def _update_ping(call):
                    start = time.perf_counter_ns()
                    await self._client.get_me()
                    ping = (time.perf_counter_ns() - start) / 1_000_000
                    await call.edit(
                        f"{self.strings['ping_text'].format(ping=ping)}\n\n"
                        f"{self.strings['stats_text'].format(**stats)}",
                        reply_markup=[
                            [{"text": "🔄 Refresh", "callback": _update_ping}]
                        ],
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
                    "description": ("Ping и статистика чата" if query.chat_id else "Ping"),
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
                    "title": "Ошибка",
                    "description": "Произошла ошибка",
                    "input_message_content": {
                        "message_text": self.strings["error_text"].format(error=str(e)),
                        "parse_mode": "HTML",
                    },
                }
            ]
