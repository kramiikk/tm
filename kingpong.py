from __future__ import annotations

import asyncio
import time
import logging
from typing import Optional, List, Dict, Any, Callable

from telethon import TelegramClient, types
from telethon.errors import (
    ChatAdminRequiredError, 
    FloodWaitError, 
    RPCError
)
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.types import ChannelParticipantsAdmins

from .. import loader, utils


class PingModuleError(Exception):
    """Custom exception for ping module errors"""
    pass


def retry_async(max_retries: int = 3):
    """Advanced async retry decorator with exponential backoff"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
            logging.error(f"Operation failed after {max_retries} attempts: {last_exception}")
            raise PingModuleError(f"Operation failed: {last_exception}")
        return wrapper
    return decorator


class ChatStatistics:
    """Lightweight immutable chat statistics container"""
    __slots__ = (
        'title', 'chat_id', 'chat_type', 'members', 
        'deleted_accounts', 'admins', 'bots', 'total_messages'
    )

    def __init__(
        self, 
        title: str = "Unknown", 
        chat_id: int = 0, 
        chat_type: str = "Unknown", 
        members: int = 0, 
        deleted_accounts: int = 0, 
        admins: int = 0, 
        bots: int = 0, 
        total_messages: int = 0
    ):
        self.title = title
        self.chat_id = chat_id
        self.chat_type = chat_type
        self.members = members
        self.deleted_accounts = deleted_accounts
        self.admins = admins
        self.bots = bots
        self.total_messages = total_messages

    def format(self, ping: float) -> str:
        """Generate compact formatted statistics"""
        return (
            f"🏓 <b>Ping:</b> {ping:.2f} ms\n\n"
            f"📊 <b>{utils.escape_html(self.title)}:</b>\n"
            f"ID: <code>{self.chat_id}</code>\n"
            f"Type: {self.chat_type}\n"
            f"Members: {self.members}\n"
            f"Deleted: {self.deleted_accounts}\n"
            f"Admins: {self.admins}\n"
            f"Bots: {self.bots}\n"
            f"Messages: {self.total_messages}"
        )


@loader.tds
class EnhancedPingModule(loader.Module):
    """Advanced, efficient Telegram ping module"""

    strings = {
        "name": "EnhancedPing",
        "error": "❌ <b>Error:</b> {}"
    }

    def __init__(self):
        self._client: Optional[TelegramClient] = None
        self._logger = logging.getLogger(self.__class__.__name__)

    async def client_ready(self, client, db):
        self._client = client

    @retry_async(max_retries=2)
    async def _calculate_ping(self) -> float:
        """Precise ping measurement"""
        start = time.perf_counter()
        await self._client.get_me()
        return (time.perf_counter() - start) * 1000

    @retry_async(max_retries=2)
    async def _fetch_chat_stats(self, chat) -> ChatStatistics:
        """Comprehensive, efficient chat statistics gathering"""
        try:
            chat_type = (
                "Supergroup" if isinstance(chat, types.Channel) and chat.megagroup
                else "Channel" if isinstance(chat, types.Channel)
                else "Group" if isinstance(chat, types.Chat)
                else "Unknown"
            )

            full_chat = await (
                self._client(GetFullChannelRequest(chat)) 
                if isinstance(chat, types.Channel) 
                else self._client(GetFullChatRequest(chat.id))
            )

            # Precise message count
            total_messages = (await self._client.get_messages(chat, limit=0)).total

            try:
                if isinstance(chat, types.Channel):
                    admins = await self._client.get_participants(
                        chat, filter=ChannelParticipantsAdmins, limit=None
                    )
                    participants = await self._client.get_participants(chat, limit=200)
                    
                    stats = ChatStatistics(
                        title=utils.escape_html(getattr(chat, 'title', 'Unknown')),
                        chat_id=chat.id,
                        chat_type=chat_type,
                        members=getattr(full_chat.full_chat, 'participants_count', 0),
                        deleted_accounts=sum(1 for p in participants if p.deleted),
                        admins=len(admins),
                        bots=sum(1 for p in participants if p.bot),
                        total_messages=total_messages
                    )
                    return stats
            except (ChatAdminRequiredError, FloodWaitError) as e:
                self._logger.warning(f"Participant fetch limited: {e}")

            return ChatStatistics(
                title=utils.escape_html(getattr(chat, 'title', 'Unknown')),
                chat_id=chat.id,
                chat_type=chat_type,
                total_messages=total_messages
            )

        except Exception as e:
            self._logger.error(f"Chat stats retrieval failed: {e}")
            return ChatStatistics()

    def _create_refresh_markup(self, callback: Optional[Callable] = None):
        """Simplified markup creation"""
        return [{"text": "🔄 Refresh", "callback": callback or (lambda _: None)}]

    @loader.command()
    async def pong(self, message):
        """Primary ping command handler"""
        try:
            ping = await self._calculate_ping()
            chat = await self._client.get_entity(message.chat_id)
            stats = await self._fetch_chat_stats(chat)

            async def refresh_callback(call):
                new_ping = await self._calculate_ping()
                await call.edit(
                    stats.format(new_ping), 
                    reply_markup=self._create_refresh_markup(refresh_callback)
                )

            await self.inline.form(
                stats.format(ping),
                message=message,
                reply_markup=self._create_refresh_markup(refresh_callback)
            )
        except Exception as e:
            await self.inline.form(
                self.strings["error"].format(e), 
                message=message
            )

    async def ping_inline_handler(self, query):
        """Inline query handler"""
        try:
            ping = await self._calculate_ping()
            
            if query.chat_id:
                chat = await self._client.get_entity(query.chat_id)
                stats = await self._fetch_chat_stats(chat)
                
                async def update_ping(call):
                    new_ping = await self._calculate_ping()
                    await call.edit(
                        stats.format(new_ping),
                        reply_markup=[self._create_refresh_markup(update_ping)]
                    )
                
                markup = [self._create_refresh_markup(update_ping)]
                text = stats.format(ping)
            else:
                text = f"🏓 <b>Ping:</b> {ping:.2f} ms"
                markup = None

            return [{
                "type": "article",
                "id": "ping_result",
                "title": f"Ping: {ping:.2f} ms",
                "description": "Chat ping and statistics",
                "input_message_content": {
                    "message_text": text,
                    "parse_mode": "HTML"
                },
                "reply_markup": markup,
                "thumb_url": "https://te.legra.ph/file/5d8c7f1960a3e126d916a.jpg"
            }]

        except Exception as e:
            return [{
                "type": "article",
                "id": "error_result",
                "title": "Error",
                "description": "Ping request failed",
                "input_message_content": {
                    "message_text": self.strings["error"].format(e),
                    "parse_mode": "HTML"
                }
            }]
