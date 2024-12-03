from __future__ import annotations

import asyncio
import time
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Callable

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

class PingError(Exception):
    """Custom exception for ping-related errors"""
    pass

def safe_async_call(max_retries: int = 3):
    """
    Decorator for handling async method calls with retry logic
    
    Args:
        max_retries (int): Maximum number of retry attempts
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (RPCError, FloodWaitError) as e:
                    if attempt == max_retries - 1:
                        logging.error(f"Async call failed: {e}")
                        raise PingError(f"Operation failed after {max_retries} attempts")
                    await asyncio.sleep(1)  # Small delay between retries
        return wrapper
    return decorator

@dataclass
class ChatStatistics:
    """Immutable dataclass for storing chat statistics"""
    title: str = "Unknown"
    chat_id: int = 0
    chat_type: str = "Unknown"
    members: int = 0
    deleted_accounts: int = 0
    admins: int = 0
    bots: int = 0
    total_messages: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChatStatistics:
        """Create ChatStatistics from dictionary"""
        return cls(**{k: data.get(k, 0) for k in cls.__annotations__})

    def to_formatted_string(self, ping: float) -> str:
        """Generate formatted statistics string"""
        return (
            f"🏓 <b>Ping:</b> {ping:.2f} ms\n\n"
            f"📊 <b>{utils.escape_html(self.title)}:</b>\n"
            f"ID: <code>{self.chat_id}</code>\n"
            f"Type: {self.chat_type}\n"
            f"Members: {self.members}\n"
            f"Deleted: {self.deleted_accounts}\n"
            f"Admins: {self.admins}\n"
            f"Bots: {self.bots}\n"
            f"Messages: {self.total_messages}\n"
        )

@loader.tds
class EnhancedInlinePingMod(loader.Module):
    """Advanced inline ping module with comprehensive chat statistics"""

    strings = {
        "name": "EnhancedInlinePing",
        "error_message": "❌ <b>Error:</b> {error}"
    }

    def __init__(self):
        self._client: Optional[TelegramClient] = None
        self._logger = logging.getLogger(self.__class__.__name__)

    async def client_ready(self, client, db):
        """Initialize client on module load"""
        self._client = client

    @safe_async_call(max_retries=2)
    async def _fetch_chat_statistics(self, chat) -> ChatStatistics:
        """
        Comprehensive method to fetch chat statistics
        
        Args:
            chat: Telegram chat object
        
        Returns:
            ChatStatistics: Calculated chat statistics
        """
        try:
            # Determine chat type
            chat_type = (
                "Supergroup" if isinstance(chat, types.Channel) and chat.megagroup
                else "Channel" if isinstance(chat, types.Channel)
                else "Group" if isinstance(chat, types.Chat)
                else "Unknown"
            )

            # Fetch full chat information
            full_chat = await (
                self._client(GetFullChannelRequest(chat)) 
                if isinstance(chat, types.Channel)
                else self._client(GetFullChatRequest(chat.id))
            )

            # Extract base statistics from full chat information
            members_count = getattr(full_chat.full_chat, 'participants_count', 0)
            total_messages = getattr(full_chat.full_chat, 'read_outbox_max_id', 0)

            # Advanced participant analysis with safety checks
            admins_count, bots_count, deleted_accounts = 0, 0, 0
            try:
                if isinstance(chat, types.Channel):
                    # Safely fetch admins and participants
                    admins = await self._client.get_participants(
                        chat, 
                        filter=ChannelParticipantsAdmins, 
                        limit=None
                    )
                    admins_count = len(admins)

                    # Sample participants to estimate bots and deleted accounts
                    participants = await self._client.get_participants(
                        chat, 
                        limit=200
                    )
                    bots_count = sum(1 for p in participants if p.bot)
                    deleted_accounts = sum(1 for p in participants if p.deleted)

            except (ChatAdminRequiredError, FloodWaitError) as e:
                self._logger.warning(f"Participant fetch error: {e}")

            return ChatStatistics(
                title=utils.escape_html(getattr(chat, "title", "Unknown")),
                chat_id=chat.id,
                chat_type=chat_type,
                members=members_count,
                deleted_accounts=deleted_accounts,
                admins=admins_count,
                bots=bots_count,
                total_messages=total_messages
            )

        except Exception as e:
            self._logger.error(f"Chat statistics fetch failed: {e}")
            return ChatStatistics()

    @loader.command()
    async def iping(self, message):
        """Inline ping command"""
        await self._process_ping(message)

    async def _process_ping(
        self, 
        message, 
        call: Optional[types.CallbackQuery] = None
    ):
        """
        Core ping processing method
        
        Args:
            message: Telegram message object
            call: Optional callback query
        """
        start_time = time.perf_counter_ns()
        await self._client.get_me()
        ping_time = (time.perf_counter_ns() - start_time) / 1_000_000

        try:
            chat = await self._client.get_entity(message.chat_id)
            stats = await self._fetch_chat_statistics(chat)
            
            # Create async refresh callback
            async def refresh_callback(call):
                try:
                    start = time.perf_counter_ns()
                    await self._client.get_me()
                    ping_time = (time.perf_counter_ns() - start) / 1_000_000
                    
                    await call.edit(
                        stats.to_formatted_string(ping_time), 
                        reply_markup=self._create_refresh_button(refresh_callback)
                    )
                except Exception as e:
                    self._logger.error(f"Refresh callback error: {e}")
                    await call.edit(f"Error refreshing: {e}")

            # Modify _create_refresh_button to directly pass the callback
            refresh_button = self._create_refresh_button(refresh_callback)

            if call:
                await call.edit(stats.to_formatted_string(ping_time), reply_markup=refresh_button)
            else:
                await self.inline.form(
                    stats.to_formatted_string(ping_time), 
                    message=message, 
                    reply_markup=refresh_button
                )

        except Exception as e:
            error_text = self.strings["error_message"].format(error=str(e))
            await self.inline.form(error_text, message=message)

    def _create_refresh_button(
        self, 
        callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Create inline refresh button
        
        Args:
            callback: Optional custom refresh callback
        
        Returns:
            List of button configurations
        """
        # Ensure callback is always a callable
        safe_callback = callback if callable(callback) else (lambda c: None)
        return [{"text": "🔄 Refresh", "callback": safe_callback}]

    async def ping_inline_handler(self, query):
        """
        Inline query handler for ping requests
        
        Args:
            query: Inline query object
        
        Returns:
            List of inline query results
        """
        start_time = time.perf_counter_ns()
        await self._client.get_me()
        ping_time = (time.perf_counter_ns() - start_time) / 1_000_000

        try:
            if query.chat_id:
                chat = await self._client.get_entity(query.chat_id)
                stats = await self._fetch_chat_statistics(chat)
                
                async def _update_ping(call):
                    start = time.perf_counter_ns()
                    await self._client.get_me()
                    ping_time = (time.perf_counter_ns() - start) / 1_000_000
                    
                    await call.edit(
                        stats.to_formatted_string(ping_time),
                        reply_markup=[[{"text": "🔄 Refresh", "callback": _update_ping}]]
                    )

                reply_markup = [[{"text": "🔄 Refresh", "callback": _update_ping}]]
                message_text = stats.to_formatted_string(ping_time)
            else:
                message_text = f"🏓 <b>Ping:</b> {ping_time:.2f} ms"
                reply_markup = None

            return [{
                "type": "article",
                "id": "ping_result",
                "title": f"Ping: {ping_time:.2f} ms",
                "description": "Ping и статистика чата" if query.chat_id else "Ping",
                "input_message_content": {
                    "message_text": message_text,
                    "parse_mode": "HTML",
                },
                "reply_markup": reply_markup,
                "thumb_url": "https://te.legra.ph/file/5d8c7f1960a3e126d916a.jpg",
            }]

        except Exception as e:
            return [{
                "type": "article",
                "id": "error_result",
                "title": "Ошибка",
                "description": "Произошла ошибка",
                "input_message_content": {
                    "message_text": self.strings["error_message"].format(error=str(e)),
                    "parse_mode": "HTML",
                },
            }]
