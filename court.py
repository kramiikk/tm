from __future__ import annotations

import asyncio
import time
import logging
import sys
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable, Union

from telethon import TelegramClient, types
from telethon.errors import (
    ChatAdminRequiredError, 
    FloodWaitError, 
    RPCError,
    NetworkError
)
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.types import ChannelParticipantsAdmins

from .. import loader, utils


class PerfMetrics:
    """Performance and error tracking"""
    __slots__ = ('_calls', '_errors', '_total_time')

    def __init__(self):
        self._calls: int = 0
        self._errors: int = 0
        self._total_time: float = 0.0

    def record(self, success: bool, exec_time: float):
        """Record method performance"""
        self._calls += 1
        self._total_time += exec_time
        if not success:
            self._errors += 1

    @property
    def metrics(self) -> Dict[str, Union[int, float]]:
        """Generate performance report"""
        return {
            'total_calls': self._calls,
            'total_errors': self._errors,
            'avg_exec_time': self._total_time / max(self._calls, 1),
            'error_rate': self._errors / max(self._calls, 1)
        }


@dataclass
class ChatStatistics:
    """Immutable, efficient chat statistics container"""
    __slots__ = (
        'title', 'chat_id', 'chat_type', 'members', 
        'deleted_accounts', 'admins', 'bots', 'total_messages'
    )

    title: str = "Unknown"
    chat_id: int = 0
    chat_type: str = "Unknown"
    members: int = 0
    deleted_accounts: int = 0
    admins: int = 0
    bots: int = 0
    total_messages: int = 0
    metrics: PerfMetrics = field(default_factory=PerfMetrics)

    def format(self, ping: float) -> str:
        """Ultra-fast, memory-efficient formatting"""
        return (
            f"🏓 <b>Ping:</b> {ping:.2f} ms\n"
            f"📊 <b>{utils.escape_html(self.title)}:</b>\n"
            f"ID: <code>{self.chat_id}</code>\n"
            f"Type: {self.chat_type}\n"
            f"Members: {self.members}\n"
            f"Deleted: {self.deleted_accounts}\n"
            f"Admins: {self.admins}\n"
            f"Bots: {self.bots}\n"
            f"Messages: {self.total_messages}"
        )


class ResilienceManager:
    """Advanced error handling and retry mechanism"""
    @staticmethod
    async def execute_with_retry(
        func: Callable,
        *args,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        **kwargs
    ):
        """
        Intelligent retry mechanism with exponential backoff
        Handles various error scenarios
        """
        last_exception = None
        for attempt in range(max_retries):
            try:
                start_time = time.perf_counter()
                result = await func(*args, **kwargs)
                exec_time = time.perf_counter() - start_time
                return result, exec_time
            except (NetworkError, RPCError) as e:
                last_exception = e
                wait_time = backoff_factor * (2 ** attempt)
                logging.warning(
                    f"Attempt {attempt + 1} failed. "
                    f"Retrying in {wait_time:.2f} seconds. Error: {e}"
                )
                await asyncio.sleep(wait_time)
        
        logging.error(f"Operation failed after {max_retries} attempts: {last_exception}")
        raise last_exception


@loader.tds
class UltraPerformancePingModule(loader.Module):
    """
    Hyper-optimized Telegram ping module
    Designed for maximum performance and reliability
    """
    strings = {
        "name": "UltraPerformancePing",
        "error": "❌ <b>Critical Module Error:</b> {}"
    }

    def __init__(self):
        self._client: Optional[TelegramClient] = None
        self._logger = logging.getLogger(self.__class__.__name__)
        self._global_metrics = PerfMetrics()

    async def client_ready(self, client, db):
        """Advanced module initialization"""
        self._client = client
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('telegram_ping.log', mode='a')
            ]
        )

    async def _high_precision_ping(self) -> float:
        """
        Hyper-precise network latency measurement
        Uses performance counters for maximum accuracy
        """
        try:
            start = time.perf_counter_ns()
            await self._client.get_me()
            ping_time = (time.perf_counter_ns() - start) / 1_000_000
            
            self._global_metrics.record(success=True, exec_time=ping_time)
            return ping_time
        except Exception as e:
            self._global_metrics.record(success=False, exec_time=0)
            self._logger.error(f"Ping measurement failed: {e}")
            return 0.0

    async def _gather_chat_metrics(self, chat) -> ChatStatistics:
        """
        Comprehensive, parallel chat metrics collection
        Minimizes API calls and processing overhead
        """
        start_time = time.perf_counter()
        try:
            chat_type = (
                "Supergroup" if isinstance(chat, types.Channel) and chat.megagroup
                else "Channel" if isinstance(chat, types.Channel)
                else "Group" if isinstance(chat, types.Chat)
                else "Unknown"
            )

            # Parallel metrics gathering
            full_chat, total_messages = await asyncio.gather(
                ResilienceManager.execute_with_retry(
                    self._client(
                        GetFullChannelRequest(chat) 
                        if isinstance(chat, types.Channel) 
                        else GetFullChatRequest(chat.id)
                    )
                )[0],
                ResilienceManager.execute_with_retry(
                    self._client.get_messages, chat, limit=0
                )[0]
            )

            if isinstance(chat, types.Channel):
                participants, admins = await asyncio.gather(
                    ResilienceManager.execute_with_retry(
                        self._client.get_participants, chat, limit=200
                    )[0],
                    ResilienceManager.execute_with_retry(
                        self._client.get_participants, 
                        chat, 
                        filter=ChannelParticipantsAdmins, 
                        limit=None
                    )[0]
                )

                stats = ChatStatistics(
                    title=utils.escape_html(getattr(chat, 'title', 'Unknown')),
                    chat_id=chat.id,
                    chat_type=chat_type,
                    members=getattr(full_chat.full_chat, 'participants_count', 0),
                    deleted_accounts=sum(1 for p in participants if p.deleted),
                    admins=len(admins),
                    bots=sum(1 for p in participants if p.bot),
                    total_messages=total_messages.total
                )
            else:
                stats = ChatStatistics(
                    title=utils.escape_html(getattr(chat, 'title', 'Unknown')),
                    chat_id=chat.id,
                    chat_type=chat_type,
                    total_messages=total_messages.total
                )

            exec_time = time.perf_counter() - start_time
            stats.metrics.record(success=True, exec_time=exec_time)
            return stats

        except Exception as e:
            self._logger.error(f"Chat metrics collection failed: {e}")
            exec_time = time.perf_counter() - start_time
            stats = ChatStatistics()
            stats.metrics.record(success=False, exec_time=exec_time)
            return stats

    @loader.command()
    async def pong(self, message):
        """
        Intelligent ping command with comprehensive error handling
        """
        try:
            ping, chat = await asyncio.gather(
                self._high_precision_ping(),
                self._client.get_entity(message.chat_id)
            )
            stats = await self._gather_chat_metrics(chat)

            async def refresh_callback(call):
                new_ping = await self._high_precision_ping()
                await call.edit(
                    stats.format(new_ping),
                    reply_markup=[{"text": "🔄 Refresh", "callback": refresh_callback}]
                )

            await self.inline.form(
                stats.format(ping),
                message=message,
                reply_markup=[{"text": "🔄 Refresh", "callback": refresh_callback}]
            )

        except Exception as e:
            self._logger.critical(f"Ping module critical error: {e}", exc_info=True)
            await self.inline.form(
                self.strings["error"].format(e), 
                message=message
            )

    @loader.command()
    async def ping_stats(self, message):
        """
        Expose module performance metrics
        """
        global_metrics = self._global_metrics.metrics
        stats_message = (
            "📊 <b>Module Performance Metrics:</b>\n"
            f"Total Calls: {global_metrics['total_calls']}\n"
            f"Total Errors: {global_metrics['total_errors']}\n"
            f"Average Execution Time: {global_metrics['avg_exec_time']:.4f} ms\n"
            f"Error Rate: {global_metrics['error_rate']:.2%}"
        )
        await message.reply(stats_message)
