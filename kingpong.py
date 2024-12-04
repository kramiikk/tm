from __future__ import annotations

import asyncio
import logging
from typing import Union, Optional, List, Dict, Any, Callable

from telethon import TelegramClient
from telethon.tl.types import (
    Chat, 
    Channel, 
    User, 
    ChannelParticipantAdmin,
    ChannelParticipantCreator
)
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.errors import (
    ChatAdminRequiredError, 
    FloodWaitError, 
    RPCError, 
    ChatForbiddenError
)

from .. import loader, utils


class PerformanceProfiler:
    """Профессиональный замер производительности"""
    
    @staticmethod
    def measure_time(func: Callable) -> Callable:
        """Декоратор точного измерения времени выполнения"""
        async def wrapper(*args, **kwargs):
            start = asyncio.get_event_loop().time()
            try:
                return await func(*args, **kwargs)
            finally:
                execution_time = (asyncio.get_event_loop().time() - start) * 1000
                if execution_time > 0.5:
                    logging.warning(
                        f"Slow operation: {func.__name__} "
                        f"took {execution_time:.4f} ms"
                    )
        return wrapper


class ChatStatistics:
    """Оптимизированный контейнер статистики чата"""
    __slots__ = (
        'title', 'chat_id', 'chat_type', 'total_members', 
        'active_members', 'admins', 'bots', 'total_messages'
    )

    def __init__(
        self, 
        title: str = 'Неизвестно',
        chat_id: int = 0,
        chat_type: str = 'Неизвестно',
        total_members: int = 0,
        active_members: int = 0,
        admins: int = 0,
        bots: int = 0,
        total_messages: int = 0
    ):
        self.title = title
        self.chat_id = chat_id
        self.chat_type = chat_type
        self.total_members = total_members
        self.active_members = active_members
        self.admins = admins
        self.bots = bots
        self.total_messages = total_messages

    def format(self, ping: float) -> str:
        """Безопасное форматирование статистики"""
        return (
            f"🏓 <b>Пинг:</b> {ping:.2f} мс\n\n"
            f"📊 <b>{utils.escape_html(self.title)}:</b>\n"
            f"ID: <code>{self.chat_id}</code>\n"
            f"Тип: {self.chat_type}\n"
            f"Участники: {self.total_members}\n"
            f"Активные: {self.active_members}\n"
            f"Администраторы: {self.admins}\n"
            f"Боты: {self.bots}\n"
            f"Сообщений: {self.total_messages}"
        )


@loader.tds
class EnhancedPingModule(loader.Module):
    """Профессиональный модуль статистики чата"""

    strings = {
        "name": "EnhancedPing", 
        "error": "❌ <b>Ошибка:</b> {}"
    }

    def __init__(self):
        self._client: Optional[TelegramClient] = None
        self._logger = logging.getLogger(self.__class__.__name__)

    async def client_ready(self, client, db):
        """Безопасная инициализация клиента"""
        self._client = client
        self._logger.info("EnhancedPing module initialized")

    @PerformanceProfiler.measure_time
    async def _get_precise_ping(self) -> float:
        """Точное измерение задержки"""
        start = asyncio.get_event_loop().time()
        try:
            await self._client.get_me()
            return (asyncio.get_event_loop().time() - start) * 1000
        except Exception as e:
            self._logger.error(f"Ping error: {e}")
            return -1.0

    @PerformanceProfiler.measure_time
    async def _count_user_messages(
        self, 
        chat: Union[Chat, Channel], 
        limit: int = 5000
    ) -> int:
        """Точный подсчет сообщений от пользователей"""
        try:
            messages = await self._client.get_messages(
                chat, 
                limit=limit,
                filter=lambda m: (
                    not m.service and 
                    not m.empty and 
                    isinstance(m.sender, User)
                )
            )
            return len(messages)
        except Exception as e:
            self._logger.warning(f"Message counting error: {e}")
            return 0

    @PerformanceProfiler.measure_time
    async def _analyze_chat_comprehensive(
        self, 
        chat: Union[Chat, Channel]
    ) -> ChatStatistics:
        """Комплексный анализ чата с расширенной диагностикой"""
        try:
            # Определение типа чата
            chat_type = (
                "Супер-группа" if getattr(chat, 'megagroup', False) 
                else "Канал" if isinstance(chat, Channel) 
                else "Группа" if isinstance(chat, Chat) 
                else "Неизвестный тип"
            )

            chat_id = getattr(chat, 'id', 0)
            title = utils.escape_html(getattr(chat, 'title', 'Неизвестно'))

            # Получение полной информации о чате
            try:
                full_chat = (
                    await self._client(GetFullChannelRequest(chat)) 
                    if isinstance(chat, Channel) 
                    else await self._client(GetFullChatRequest(chat.id))
                )
                total_members = getattr(full_chat.full_chat, 'participants_count', 0)
            except Exception as e:
                self._logger.warning(f"Full chat info error: {e}")
                total_members = 0

            # Расширенный подсчет участников
            try:
                all_participants = await self._client.get_participants(
                    chat_id, 
                    aggressive=True
                )

                total_participants = len(all_participants)
                active_members = sum(
                    1 for p in all_participants 
                    if not p.deleted and 
                       not p.bot and 
                       not p.is_self and 
                       p.access_hash is not None
                )
                bots = sum(1 for p in all_participants if p.bot)
            except Exception as e:
                self._logger.warning(f"Participants count error: {e}")
                total_participants = total_members
                active_members = 0
                bots = 0

            # Подсчет сообщений
            total_messages = await self._count_user_messages(chat)

            # Подсчет администраторов
            try:
                full_chat_info = await self._client(GetFullChannelRequest(chat))
                admins = getattr(full_chat_info.full_chat, 'admins_count', 0)
            except Exception as e:
                self._logger.warning(f"Admin count error: {e}")
                admins = 0

            return ChatStatistics(
                title=title,
                chat_id=chat_id,
                chat_type=chat_type,
                total_members=total_members,
                active_members=active_members,
                admins=admins,
                bots=bots,
                total_messages=total_messages
            )

        except Exception as e:
            self._logger.error(f"Comprehensive chat analysis failed: {e}")
            return ChatStatistics(chat_id=chat_id)

    @loader.command()
    async def pong(self, message):
        """Команда получения статистики чата"""
        try:
            ping_time = await self._get_precise_ping()
            chat = await self._client.get_entity(message.chat_id)
            chat_stats = await self._analyze_chat_comprehensive(chat)

            async def refresh_callback(call):
                new_ping = await self._get_precise_ping()
                await call.edit(
                    chat_stats.format(new_ping),
                    reply_markup=self._create_refresh_markup(refresh_callback)
                )

            await self.inline.form(
                chat_stats.format(ping_time),
                message=message,
                reply_markup=self._create_refresh_markup(refresh_callback)
            )
        except Exception as e:
            await self.inline.form(
                self.strings["error"].format(str(e)), 
                message=message
            )

    def _create_refresh_markup(self, callback: Optional[Callable] = None):
        """Создание унифицированной разметки обновления"""
        return [{"text": "🔄 Обновить", "callback": callback or (lambda _: None)}]
