from __future__ import annotations

import asyncio
import logging
from typing import Union, Dict, Optional, List

from telethon import TelegramClient
from telethon.tl.types import (
    Chat, 
    User, 
    Message,
    ChatParticipant,
    ChatAdminRights
)

from .. import loader, utils

logger = logging.getLogger(__name__)

class ProfessionalChatAnalyzer:
    """Профессиональный класс для анализа групповых чатов"""

    def __init__(self, client: TelegramClient):
        """
        Инициализация анализатора с клиентом Telegram

        Args:
            client (TelegramClient): Клиент Telegram для взаимодействия
        """
        self._client = client
        self._logger = logging.getLogger(self.__class__.__name__)

    async def measure_network_latency(
        self, 
        attempts: int = 3, 
        timeout: float = 3.0
    ) -> float:
        """
        Измерение сетевой задержки с повышенной надёжностью

        Args:
            attempts (int): Количество попыток измерения
            timeout (float): Максимальное время ожидания

        Returns:
            float: Средняя задержка в миллисекундах
        """
        latencies = []
        for _ in range(attempts):
            try:
                start = asyncio.get_event_loop().time()
                await asyncio.wait_for(self._client.get_me(), timeout=timeout)
                latency = (asyncio.get_event_loop().time() - start) * 1000
                latencies.append(latency)
            except Exception as e:
                self._logger.error(f"Ping measurement error: {e}")
        
        return sum(latencies) / len(latencies) if latencies else -1.0

    async def analyze_group_comprehensive(
        self, 
        chat: Chat, 
        detailed: bool = False
    ) -> Dict[str, Union[str, int]]:
        """
        Комплексный анализ группового чата с расширенной диагностикой

        Args:
            chat (Chat): Объект чата для анализа
            detailed (bool): Флаг для получения детальной информации

        Returns:
            Dict[str, Union[str, int]]: Словарь с аналитикой чата
        """
        try:
            # Получение всех участников с расширенной диагностикой
            all_participants = await self._get_participants(chat)
            
            # Комплексный анализ участников
            participants = self._get_participants_comprehensive(all_participants)
            
            # Подсчет сообщений с продвинутой фильтрацией
            messages_count = await self._count_meaningful_messages(chat)

            # Подсчет администраторов с детальной обработкой
            admin_count = self._count_group_admins(all_participants)

            result = {
                'title': getattr(chat, 'title', 'Unknown'),
                'chat_id': chat.id,
                'type': 'Группа',
                'total_members': participants['total'],
                'active_members': participants['active'],
                'admins': admin_count,
                'bots': participants['bots'],
                'total_messages': messages_count
            }

            if detailed:
                result.update(self._get_detailed_group_metadata(chat))

            return result

        except Exception as e:
            self._logger.error(f"Group analysis error: {e}")
            return {}

    async def _get_participants(
        self, 
        chat: Chat
    ) -> List[User]:
        """
        Получение всех участников группы

        Returns:
            List[User]: Список участников
        """
        try:
            return await self._client.get_participants(chat)
        except Exception as e:
            self._logger.error(f"Participants retrieval error: {e}")
            return []

    def _get_participants_comprehensive(
        self, 
        all_participants: List[User]
    ) -> Dict[str, int]:
        """
        Расширенный анализ участников группы с точной диагностикой

        Returns:
            Dict[str, int]: Статистика участников
        """
        stats = {
            'total': len(all_participants),
            'active': sum(1 for p in all_participants if not hasattr(p, 'deleted') or not p.deleted),
            'bots': sum(1 for p in all_participants if hasattr(p, 'bot') and p.bot)
        }

        self._logger.info(f"Participants analysis complete", extra=stats)
        return stats

    def _count_group_admins(
        self, 
        all_participants: List[User]
    ) -> int:
        """
        Надёжный подсчёт администраторов группы с расширенной диагностикой

        Returns:
            int: Количество администраторов
        """
        try:
            admin_participants = [p for p in all_participants if isinstance(p, User) and hasattr(p, 'admin_rights') and p.admin_rights]
            admin_count = len(admin_participants)

            self._logger.info(f"Admin count retrieved: {admin_count}")
            return admin_count

        except Exception as e:
            self._logger.error(f"Admin counting failed: {e}")
            return 0

    async def _count_meaningful_messages(
        self, 
        chat: Chat, 
        limit: int = 10000
    ) -> int:
        """
        Подсчет релевантных сообщений с продвинутой фильтрацией

        Args:
            chat (Chat): Группа для анализа
            limit (int): Максимальное количество сообщений

        Returns:
            int: Количество значимых сообщений
        """
        try:
            messages = await self._client.get_messages(chat, limit=limit)
            meaningful_messages = [
                msg for msg in messages 
                if (hasattr(msg, 'text') and msg.text and len(msg.text.strip()) > 0) and
                   (not hasattr(msg, 'service') or not msg.service)
            ]
            return len(meaningful_messages)
        except Exception as e:
            self._logger.warning(f"Message counting error: {e}")
            return 0

    def _get_detailed_group_metadata(
        self, 
        chat: Chat
    ) -> Dict[str, str]:
        """
        Получение дополнительной метаинформации о группе

        Returns:
            Dict[str, str]: Расширенные метаданные
        """
        return {
            'description': getattr(chat, 'description', 'Нет описания'),
            'creation_date': str(getattr(chat, 'date', 'Неизвестно'))
        }

@loader.tds
class PrecisionGroupModule(loader.Module):
    """Профессиональный модуль аналитики групп"""

    strings = {
        "name": "GroupPrecision",
        "error": "❌ <b>Ошибка:</b> {}"
    }

    async def client_ready(self, client, db):
        """Инициализация модуля"""
        self.analyzer = ProfessionalChatAnalyzer(client)

    @loader.command()
    async def groupstat(self, message):
        """Команда получения расширенной статистики группы"""
        try:
            # Замер задержки
            ping_time = await self.analyzer.measure_network_latency()
            
            # Получение текущей группы
            chat = await message.get_chat()
            
            # Получение статистики
            stats = await self.analyzer.analyze_group_comprehensive(chat)

            response = (
                f"🌐 <b>Сетевая задержка:</b> {ping_time:.2f} мс\n\n"
                f"📊 <b>{utils.escape_html(stats.get('title', 'Неизвестно'))}:</b>\n"
                f"ID: <code>{stats.get('chat_id', 'N/A')}</code>\n"
                f"Тип: {stats.get('type', 'Неизвестно')}\n"
                f"Всего участников: {stats.get('total_members', 0)}\n"
                f"Активные участники: {stats.get('active_members', 0)}\n"
                f"Администраторы: {stats.get('admins', 0)}\n"
                f"Боты: {stats.get('bots', 0)}\n"
                f"Сообщений: {stats.get('total_messages', 0)}"
            )

            async def refresh_stats(call):
                new_ping = await self.analyzer.measure_network_latency()
                new_response = response.replace(
                    f"🌐 <b>Сетевая задержка:</b> {ping_time:.2f} мс", 
                    f"🌐 <b>Сетевая задержка:</b> {new_ping:.2f} мс"
                )
                await call.edit(new_response)

            await self.inline.form(
                response, 
                message=message,
                reply_markup=[{"text": "🔄 Обновить", "callback": refresh_stats}]
            )

        except Exception as e:
            await self.inline.form(
                self.strings["error"].format(str(e)), 
                message=message
            )
