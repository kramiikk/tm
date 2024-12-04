from __future__ import annotations

import asyncio
import logging
from typing import Optional, Union, List, Dict, Any

from telethon import TelegramClient
from telethon.tl.types import (
    Chat,
    Channel,
    Message,
    ChannelParticipantAdmin,
    ChannelParticipantCreator,
)
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.errors import ChatAdminRequiredError, FloodWaitError, RPCError

from .. import loader, utils


class PerformanceProfiler:
    """Профессиональный профайлер производительности"""

    @staticmethod
    def measure_time(func):
        """Декоратор для измерения времени выполнения"""

        async def wrapper(*args, **kwargs):
            import time

            start_time = time.perf_counter()
            result = await func(*args, **kwargs)
            execution_time = time.perf_counter() - start_time

            if execution_time > 0.5:  # Логируем медленные операции
                logging.warning(
                    f"Slow operation: {func.__name__} took {execution_time:.4f} seconds"
                )
            return result

        return wrapper


class ChatStatistics:
    """
    Расширенный контейнер статистики чата
    с оптимизированной логикой сбора данных
    """

    __slots__ = (
        "title",
        "chat_id",
        "chat_type",
        "total_members",
        "active_members",
        "admins",
        "bots",
        "total_messages",
    )

    def __init__(
        self,
        title: str = "Неизвестно",
        chat_id: int = 0,
        chat_type: str = "Неизвестно",
        total_members: int = 0,
        active_members: int = 0,
        admins: int = 0,
        bots: int = 0,
        total_messages: int = 0,
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
        """Форматированный вывод статистики с улучшенным escaped html"""
        return (
            f"🏓 <b>Пинг:</b> {ping:.2f} мс\n\n"
            f"📊 <b>{utils.escape_html(self.title or 'Неизвестно')}:</b>\n"
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
    """Профессиональный модуль пинга с точной статистикой"""

    strings = {"name": "EnhancedPing", "error": "❌ <b>Ошибка:</b> {}"}

    def __init__(self):
        self._client: Optional[TelegramClient] = None
        self._logger = logging.getLogger(self.__class__.__name__)
        self._cache: Dict[int, Dict[str, Any]] = {}

    async def client_ready(self, client, db):
        """Инициализация клиента с расширенной диагностикой"""
        self._client = client
        self._logger.info("EnhancedPing module initialized")

    @PerformanceProfiler.measure_time
    async def _get_precise_ping(self) -> float:
        """
        Точное измерение задержки с использованием
        высокоточного таймера
        """
        start = asyncio.get_event_loop().time()
        await self._client.get_me()
        return (asyncio.get_event_loop().time() - start) * 1000

    @PerformanceProfiler.measure_time
    async def _count_messages(self, chat: Union[Chat, Channel]) -> int:
        """
        Оптимизированный подсчет сообщений
        с ограничением для предотвращения перегрузки
        """
        try:
            # Получаем последние 5000 сообщений для анализа

            messages = await self._client.get_messages(chat, limit=5000)
            return len(messages)
        except Exception as e:
            self._logger.warning(f"Ошибка подсчета сообщений: {e}")
            return 0

    @PerformanceProfiler.measure_time
    async def _get_admin_count(self, chat: Union[Chat, Channel]) -> int:
        """
        Точный и безопасный подсчет администраторов
        """
        try:
            participants = await self._client.get_participants(
                chat,
                filter=lambda p: isinstance(
                    p, (ChannelParticipantAdmin, ChannelParticipantCreator)
                ),
            )
            return len(participants)
        except (ChatAdminRequiredError, FloodWaitError) as e:
            self._logger.warning(f"Ошибка получения администраторов: {e}")
            return 0

    @PerformanceProfiler.measure_time
    async def _analyze_chat_comprehensive(
        self, chat: Union[Chat, Channel]
    ) -> ChatStatistics:
        """
        Комплексный анализ статистики чата с расширенной диагностикой типов
        """
        try:
            # Расширенная логика определения типа чата

            if hasattr(chat, "megagroup") and chat.megagroup:
                chat_type = "Супер-группа"
            elif isinstance(chat, Channel):
                chat_type = "Канал" if not chat.megagroup else "Приватный канал"
            elif isinstance(chat, Chat):
                chat_type = "Группа"
            elif hasattr(chat, "access_hash"):  # Служебные чаты
                chat_type = "Служебный чат"
            else:
                chat_type = "Неизвестный тип"
            # Безопасное получение идентификатора

            chat_id = getattr(chat, "id", 0)

            # Получение полной информации о чате с расширенной обработкой

            try:
                if isinstance(chat, Channel):
                    full_chat = await self._client(GetFullChannelRequest(chat))
                elif isinstance(chat, Chat):
                    full_chat = await self._client(GetFullChatRequest(chat.id))
                else:
                    # Fallback для нестандартных типов

                    full_chat = await self._client.get_full_chat(chat_id)
                total_members = getattr(full_chat.full_chat, "participants_count", 0)
            except Exception as e:
                self._logger.warning(
                    f"Не удалось получить полную информацию о чате: {e}"
                )
                total_members = 0
            # Безопасный подсчет участников и сообщений

            try:
                # Используем более надежный метод с параметром aggressive=True

                participants = await self._client.get_participants(
                    chat_id, aggressive=True, limit=None
                )

                # Расширенная фильтрация участников

                total_participants = len(participants)
                active_members = sum(
                    1
                    for p in participants
                    if not p.deleted and not p.bot and not p.is_self
                )
                bots = sum(1 for p in participants if p.bot)
            except Exception as e:
                self._logger.warning(f"Ошибка получения участников: {e}")
                total_participants = total_members
                active_members = 0
                bots = 0
            # Подсчет сообщений с расширенной обработкой

            try:
                # Используем more_events=True для полного охвата

                messages = await self._client.get_messages(
                    chat_id, limit=0, offset_date=None, reverse=False
                )
                total_messages = messages.total if hasattr(messages, "total") else 0
            except Exception as e:
                self._logger.warning(f"Ошибка подсчета сообщений: {e}")
                total_messages = 0
            # Точный подсчет администраторов

            try:
                admins = await self._get_admin_count(chat)
            except Exception as e:
                self._logger.warning(f"Ошибка подсчета администраторов: {e}")
                admins = 0
            return ChatStatistics(
                title=utils.escape_html(getattr(chat, "title", "Неизвестно")),
                chat_id=chat_id,
                chat_type=chat_type,
                total_members=total_members,
                active_members=active_members,
                admins=admins,
                bots=bots,
                total_messages=total_messages,
            )
        except Exception as e:
            self._logger.error(f"Критическая ошибка анализа чата: {e}")
            return ChatStatistics(chat_id=getattr(chat, "id", 0))

    @loader.command()
    async def pong(self, message):
        """Команда для получения статистики чата"""
        try:
            ping_time = await self._get_precise_ping()
            chat = await self._client.get_entity(message.chat_id)
            chat_stats = await self._analyze_chat_comprehensive(chat)

            async def refresh_callback(call):
                new_ping = await self._get_precise_ping()
                await call.edit(
                    chat_stats.format(new_ping),
                    reply_markup=self._create_refresh_markup(refresh_callback),
                )

            await self.inline.form(
                chat_stats.format(ping_time),
                message=message,
                reply_markup=self._create_refresh_markup(refresh_callback),
            )
        except Exception as e:
            await self.inline.form(
                self.strings["error"].format(str(e)), message=message
            )

    def _create_refresh_markup(self, callback=None):
        """Создание разметки обновления с унифицированным интерфейсом"""
        return [{"text": "🔄 Обновить", "callback": callback or (lambda _: None)}]
