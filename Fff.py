from __future__ import annotations

import asyncio
import logging
from typing import Union, Dict, Optional, List, Set, Tuple

from telethon import TelegramClient
from telethon.tl.types import (
    Chat, 
    User, 
    Message
)

from .. import loader, utils

logger = logging.getLogger(__name__)

class ProfessionalChatAnalyzer:
    """Профессиональный класс для анализа групповых чатов по активности сообщений"""

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
        detailed: bool = False,
        message_limit: int = 5000
    ) -> Dict[str, Union[str, int]]:
        """
        Комплексный анализ группового чата с определением активности по сообщениям

        Args:
            chat (Chat): Объект чата для анализа
            detailed (bool): Флаг для получения детальной информации
            message_limit (int): Лимит сообщений для анализа

        Returns:
            Dict[str, Union[str, int]]: Словарь с аналитикой чата
        """
        try:
            # Получение сообщений и анализ активности
            active_users, total_messages = await self._analyze_message_activity(chat, message_limit)
            
            # Получение статистики ботов
            bots_count = await self._count_bots(chat)

            result = {
                'title': getattr(chat, 'title', 'Unknown'),
                'chat_id': chat.id,
                'type': 'Группа',
                'active_members': len(active_users),
                'bots': bots_count,
                'total_messages': total_messages
            }

            if detailed:
                result.update(self._get_detailed_group_metadata(chat))

            return result

        except Exception as e:
            self._logger.error(f"Group analysis error: {e}")
            return {}

    async def _analyze_message_activity(
        self, 
        chat: Chat, 
        message_limit: int = 5000
    ) -> Tuple[Set[int], int]:
        """
        Анализ активности пользователей по сообщениям

        Args:
            chat (Chat): Группа для анализа
            message_limit (int): Максимальное количество сообщений

        Returns:
            Tuple[Set[int], int]: Множество активных пользователей и общее число сообщений
        """
        try:
            # Получаем список всех ботов в группе
            bots = await self._get_bot_ids(chat)

            messages = await self._client.get_messages(chat, limit=message_limit)
            
            # Фильтрация значимых сообщений
            meaningful_messages = [
                msg for msg in messages 
                if (hasattr(msg, 'text') and msg.text and len(msg.text.strip()) > 0) and
                   (not hasattr(msg, 'service') or not msg.service)
            ]

            # Определение уникальных активных пользователей (исключая ботов)
            active_users = {
                msg.sender_id for msg in meaningful_messages 
                if msg.sender_id is not None and msg.sender_id not in bots
            }

            return active_users, len(meaningful_messages)

        except Exception as e:
            self._logger.warning(f"Message activity analysis error: {e}")
            return set(), 0

    async def _get_bot_ids(self, chat: Chat) -> Set[int]:
        """
        Получение ID ботов в группе

        Args:
            chat (Chat): Группа для анализа

        Returns:
            Set[int]: Множество ID ботов
        """
        try:
            participants = await self._client.get_participants(chat)
            return {p.id for p in participants if hasattr(p, 'bot') and p.bot}
        except Exception as e:
            self._logger.error(f"Bot ID retrieval error: {e}")
            return set()

    async def _count_bots(self, chat: Chat) -> int:
        """
        Подсчет количества ботов в группе

        Args:
            chat (Chat): Группа для анализа

        Returns:
            int: Количество ботов
        """
        try:
            participants = await self._client.get_participants(chat)
            return sum(1 for p in participants if hasattr(p, 'bot') and p.bot)
        except Exception as e:
            self._logger.error(f"Bot counting error: {e}")
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
            # Асинхронный замер задержки
            ping_time_task = asyncio.create_task(self.analyzer.measure_network_latency())
            
            # Получение текущей группы
            chat = await message.get_chat()
            
            # Инициальный ответ с пингом
            ping_time = await ping_time_task
            initial_response = (
                f"🌐 <b>Сетевая задержка:</b> {ping_time:.2f} мс\n\n"
                f"⏳ Сбор статистики..."
            )

            # Отправка первоначального сообщения
            bot_message = await self.inline.form(
                initial_response, 
                message=message,
                reply_markup=[{"text": "🔄 Обновить", "callback": self._refresh_ping}]
            )

            # Асинхронный сбор статистики
            stats_task = asyncio.create_task(self.analyzer.analyze_group_comprehensive(chat))
            
            # Ожидание статистики
            stats = await stats_task

            # Формирование полного ответа
            full_response = (
                f"🌐 <b>Сетевая задержка:</b> {ping_time:.2f} мс\n\n"
                f"📊 <b>{utils.escape_html(stats.get('title', 'Неизвестно'))}:</b>\n"
                f"ID: <code>{stats.get('chat_id', 'N/A')}</code>\n"
                f"Тип: {stats.get('type', 'Неизвестно')}\n"
                f"Активные участники: {stats.get('active_members', 0)}\n"
                f"Боты: {stats.get('bots', 0)}\n"
                f"Сообщений: {stats.get('total_messages', 0)}"
            )

            # Редактирование сообщения с полной статистикой
            await bot_message.edit(full_response)

        except Exception as e:
            await self.inline.form(
                self.strings["error"].format(str(e)), 
                message=message
            )

    async def _refresh_ping(self, call):
        """Обновление только пинга без полной перезагрузки статистики"""
        try:
            ping_time = await self.analyzer.measure_network_latency()
            current_text = call.message.text
            
            # Регулярное обновление пинга в существующем сообщении
            updated_text = current_text.split('\n\n', 1)
            updated_text = (
                f"🌐 <b>Сетевая задержка:</b> {ping_time:.2f} мс\n\n" + 
                updated_text[1]
            )
            
            await call.edit(updated_text)
        except Exception as e:
            await call.answer(str(e), show_alert=True)
