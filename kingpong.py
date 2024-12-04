from __future__ import annotations

import asyncio
import logging
from typing import Union, Dict, Optional

from telethon import TelegramClient
from telethon.tl.types import (
    Chat, 
    Channel, 
    User
)
from telethon.errors import (
    ChatAdminRequiredError, 
    FloodWaitError, 
    RPCError
)

from .. import loader, utils

logger = logging.getLogger(__name__)

class AdvancedTelegramAnalyzer:
    """Профессиональный класс для глубокого анализа Telegram-чатов"""

    def __init__(self, client: TelegramClient):
        """
        Инициализация анализатора с клиентом Telegram

        Args:
            client (TelegramClient): Клиент Telegram для взаимодействия
        """
        self._client = client
        self._logger = logging.getLogger(self.__class__.__name__)

    async def measure_network_latency(self, attempts: int = 3) -> float:
        """
        Измерение сетевой задержки с усреднением

        Args:
            attempts (int): Количество попыток измерения

        Returns:
            float: Средняя задержка в миллисекундах
        """
        latencies = []
        for _ in range(attempts):
            try:
                start = asyncio.get_event_loop().time()
                await self._client.get_me()
                latency = (asyncio.get_event_loop().time() - start) * 1000
                latencies.append(latency)
            except Exception as e:
                self._logger.error(f"Ping measurement error: {e}")
        
        return sum(latencies) / len(latencies) if latencies else -1.0

    async def analyze_chat_comprehensive(
        self, 
        chat: Union[Chat, Channel], 
        detailed: bool = False
    ) -> Dict[str, Union[str, int]]:
        """
        Комплексный анализ чата с расширенными возможностями

        Args:
            chat (Union[Chat, Channel]): Объект чата для анализа
            detailed (bool): Флаг для получения детальной информации

        Returns:
            Dict[str, Union[str, int]]: Словарь с аналитикой чата
        """
        try:
            chat_type = self._determine_chat_type(chat)
            
            participants = await self._get_participants_info(chat)
            messages_count = await self._count_meaningful_messages(chat)

            result = {
                'title': getattr(chat, 'title', 'Unknown'),
                'chat_id': chat.id,
                'type': chat_type,
                'total_members': participants['total'],
                'active_members': participants['active'],
                'admins': participants['admins'],
                'bots': participants['bots'],
                'total_messages': messages_count
            }

            if detailed:
                result.update(self._get_detailed_chat_metadata(chat))

            return result

        except Exception as e:
            self._logger.error(f"Chat analysis error: {e}")
            return {}

    def _determine_chat_type(self, chat: Union[Chat, Channel]) -> str:
        """Определение типа чата с высокой точностью"""
        if isinstance(chat, Channel):
            return "Супер-группа" if chat.megagroup else "Канал"
        return "Группа"

    async def _get_participants_info(self, chat: Union[Chat, Channel]) -> Dict[str, int]:
        """
        Получение детальной информации об участниках чата

        Returns:
            Dict[str, int]: Статистика участников
        """
        try:
            participants = await self._client.get_participants(chat)
            return {
                'total': len(participants),
                'active': sum(1 for p in participants if not p.deleted and not p.bot and not p.is_self),
                'admins': sum(1 for p in participants if p.is_admin or p.is_creator),
                'bots': sum(1 for p in participants if p.bot)
            }
        except Exception as e:
            self._logger.warning(f"Participants analysis error: {e}")
            return {'total': 0, 'active': 0, 'admins': 0, 'bots': 0}

    async def _count_meaningful_messages(
        self, 
        chat: Union[Chat, Channel], 
        limit: int = 10000
    ) -> int:
        """
        Подсчет релевантных сообщений с продвинутой фильтрацией

        Args:
            chat (Union[Chat, Channel]): Чат для анализа
            limit (int): Максимальное количество сообщений для анализа

        Returns:
            int: Количество значимых сообщений
        """
        try:
            messages = await self._client.get_messages(
                chat, 
                limit=limit, 
                filter=lambda msg: (
                    not msg.service and 
                    not msg.media and 
                    msg.text and 
                    len(msg.text.strip()) > 0
                )
            )
            return len(messages)
        except Exception as e:
            self._logger.warning(f"Message counting error: {e}")
            return 0

    def _get_detailed_chat_metadata(self, chat: Union[Chat, Channel]) -> Dict[str, str]:
        """
        Получение дополнительной метаинформации о чате

        Returns:
            Dict[str, str]: Расширенные метаданные
        """
        return {
            'description': getattr(chat, 'about', 'Нет описания'),
            'username': getattr(chat, 'username', 'Отсутствует'),
            'creation_date': str(getattr(chat, 'date', 'Неизвестно'))
        }

@loader.tds
class PrecisionChatModule(loader.Module):
    """Профессиональный модуль аналитики Telegram-чатов"""

    strings = {
        "name": "ChatPrecision",
        "error": "❌ <b>Ошибка:</b> {}"
    }

    async def client_ready(self, client, db):
        """Инициализация модуля при подключении клиента"""
        self.analyzer = AdvancedTelegramAnalyzer(client)

    @loader.command()
    async def chatstat(self, message):
        """Команда для получения расширенной статистики чата"""
        try:
            # Замер задержки
            ping_time = await self.analyzer.measure_network_latency()
            
            # Получение текущего чата
            chat = await message.get_chat()
            
            # Получение статистики
            stats = await self.analyzer.analyze_chat_comprehensive(chat)

            # Форматирование ответа с HTML-разметкой
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

            # Интерактивное обновление статистики
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
