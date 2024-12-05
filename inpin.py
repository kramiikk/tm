from __future__ import annotations

import asyncio
import logging
from typing import Dict, Optional, Any

from telethon import TelegramClient
from telethon.tl.types import Chat
from telethon.errors import (
    ChatAdminRequiredError, 
    FloodWaitError, 
    RPCError,
    UserNotParticipantError
)

import structlog
import traceback

class TelegramGroupAnalyzer:
    """Профессиональный анализатор групповых чатов с расширенной диагностикой"""

    def __init__(
        self, 
        telethon_client: TelegramClient
    ):
        """
        Инициализация анализатора с Telethon клиентом

        Args:
            telethon_client (TelegramClient): Основной Telethon клиент
        """
        self._telethon_client = telethon_client
        
        # Использование структурированного логирования
        self._logger = structlog.get_logger(self.__class__.__name__)
        
        # Настройка уровня логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    async def measure_network_latency(
        self, 
        attempts: int = 3, 
        timeout: float = 5.0
    ) -> float:
        """
        Точное измерение сетевой задержки с повышенной надёжностью

        Args:
            attempts (int): Количество попыток измерения
            timeout (float): Максимальное время ожидания

        Returns:
            float: Средняя задержка в миллисекундах
        """
        latencies = []
        for attempt in range(attempts):
            try:
                start = asyncio.get_event_loop().time()
                async with asyncio.timeout(timeout):
                    await self._telethon_client.get_me()
                latency = (asyncio.get_event_loop().time() - start) * 1000
                latencies.append(latency)
            except asyncio.TimeoutError:
                self._logger.warning(f"Timeout in latency measurement, attempt {attempt + 1}")
            except Exception as e:
                self._logger.error(f"Ping measurement error: {e}")
        
        return sum(latencies) / len(latencies) if latencies else -1.0

    async def analyze_group_comprehensive(
        self, 
        chat: Chat,
        detailed: bool = False
    ) -> Dict[str, Any]:
        """
        Расширенный комплексный анализ группового чата

        Args:
            chat (Chat): Объект чата для анализа
            detailed (bool): Флаг для получения детальной информации

        Returns:
            Dict[str, Any]: Словарь с расширенной аналитикой чата
        """
        try:
            # Получение участников с расширенной диагностикой
            participants = await self._get_participants_comprehensive(chat)
            
            # Подсчет сообщений с продвинутой фильтрацией
            messages_stats = await self._analyze_messages(chat)

            result = {
                'title': getattr(chat, 'title', 'Unknown'),
                'chat_id': chat.id,
                'total_members': participants['total'],
                'active_members': participants['active'],
                'verified_admins': participants['admins'],
                'bots': participants['bots'],
                'messages_stats': messages_stats
            }

            return result

        except Exception as e:
            self._logger.error(
                "Comprehensive group analysis failed",
                chat_id=getattr(chat, 'id', 'unknown'),
                error=str(e),
                trace=traceback.format_exc()
            )
            return {}

    async def _get_participants_comprehensive(
        self, 
        chat: Chat
    ) -> Dict[str, int]:
        """
        Расширенный анализ участников чата

        Returns:
            Dict[str, int]: Статистика участников
        """
        try:
            # Попытка получения через Telethon
            participants = await self._telethon_client.get_participants(chat)
            
            stats = {
                'total': len(participants),
                'active': sum(1 for p in participants if not hasattr(p, 'deleted') or not p.deleted),
                'admins': await self._count_admins(chat),
                'bots': sum(1 for p in participants if hasattr(p, 'bot') and p.bot)
            }

            self._logger.info(
                "Participants analysis complete", 
                total_members=stats['total'], 
                active_members=stats['active']
            )
            return stats

        except Exception as e:
            self._logger.error(
                "Participants analysis error",
                error=str(e),
                trace=traceback.format_exc()
            )
            return {'total': 0, 'active': 0, 'admins': 0, 'bots': 0}

    async def _count_admins(
        self, 
        chat: Chat
    ) -> int:
        """
        Надёжный подсчёт администраторов с расширенной диагностикой

        Returns:
            int: Количество администраторов
        """
        try:
            # Попытка получения администраторов через Telethon
            participants = await self._telethon_client.get_participants(
                chat, 
                filter=lambda p: hasattr(p, 'admin') and p.admin
            )
            
            admin_count = len(participants)
            
            self._logger.info(
                "Admin count retrieved", 
                chat_id=chat.id, 
                admin_count=admin_count
            )
            
            return admin_count

        except ChatAdminRequiredError:
            self._logger.warning(
                "No admin permissions to retrieve admin list", 
                chat_id=chat.id
            )
            return 0
        except Exception as e:
            self._logger.error(
                "Admin counting failed",
                error=str(e),
                trace=traceback.format_exc()
            )
            return 0

    async def _analyze_messages(
        self, 
        chat: Chat, 
        limit: int = 10000
    ) -> Dict[str, int]:
        """
        Продвинутый анализ сообщений с многоуровневой фильтрацией

        Returns:
            Dict[str, int]: Статистика сообщений
        """
        try:
            messages = await self._telethon_client.get_messages(chat, limit=limit)
            
            message_types = {
                'total': len(messages),
                'text_messages': sum(1 for msg in messages if msg.text),
                'media_messages': sum(1 for msg in messages if msg.media),
                'service_messages': sum(1 for msg in messages if msg.service)
            }

            return message_types

        except Exception as e:
            self._logger.warning(f"Message analysis error: {e}")
            return {'total': 0, 'text_messages': 0, 'media_messages': 0, 'service_messages': 0}

class PrecisionGroupModule:
    """Модуль прецизионного анализа групп"""

    def __init__(self, client: TelegramClient):
        """
        Инициализация модуля с расширенным анализатором
        
        Args:
            client (TelegramClient): Клиент Telegram
        """
        self.analyzer = TelegramGroupAnalyzer(client)
        self.logger = structlog.get_logger(self.__class__.__name__)

    async def get_group_stats(
        self, 
        message: Any
    ) -> Dict[str, Any]:
        """
        Получение расширенной статистики группы с диагностикой

        Args:
            message (Any): Объект сообщения

        Returns:
            Dict[str, Any]: Статистика группы
        """
        try:
            # Замер задержки с повышенной точностью
            ping_time = await self.analyzer.measure_network_latency()
            
            # Получение текущей группы
            chat = await message.get_chat()
            
            # Получение статистики
            stats = await self.analyzer.analyze_group_comprehensive(chat)

            self.logger.info(
                "Group stats retrieved successfully", 
                chat_id=chat.id, 
                ping_time=ping_time
            )

            return {**stats, 'ping_time': ping_time}

        except Exception as e:
            self.logger.error(
                "Group stats retrieval failed",
                error=str(e),
                trace=traceback.format_exc()
            )
            return {}
