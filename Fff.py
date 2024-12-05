from __future__ import annotations

import asyncio
import logging
from typing import Union, Dict, Set, Tuple

from telethon import TelegramClient
from telethon.tl.types import Chat

from .. import loader, utils

class ProfessionalChatAnalyzer:
    def __init__(self, client: TelegramClient):
        self._client = client
        self._logger = logging.getLogger(self.__class__.__name__)

    async def measure_network_latency(
        self, 
        attempts: int = 3, 
        timeout: float = 3.0
    ) -> float:
        """Измерение сетевой задержки с повышенной надёжностью"""
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
        message_limit: int = 5000
    ) -> Dict[str, Union[str, int]]:
        """Комплексный анализ группового чата"""
        try:
            active_users, total_messages = await self._analyze_message_activity(chat, message_limit)
            bots_count = await self._count_bots(chat)

            return {
                'title': getattr(chat, 'title', 'Unknown'),
                'chat_id': chat.id,
                'active_members': len(active_users),
                'bots': bots_count,
                'total_messages': total_messages
            }
        except Exception as e:
            self._logger.error(f"Group analysis error: {e}")
            return {}

    async def _analyze_message_activity(
        self, 
        chat: Chat, 
        message_limit: int = 5000
    ) -> Tuple[Set[int], int]:
        """Анализ активности пользователей по сообщениям"""
        try:
            bots = await self._get_bot_ids(chat)
            messages = await self._client.get_messages(chat, limit=message_limit)
            
            meaningful_messages = [
                msg for msg in messages 
                if (hasattr(msg, 'text') and msg.text and len(msg.text.strip()) > 0) and
                   (not hasattr(msg, 'service') or not msg.service)
            ]

            active_users = {
                msg.sender_id for msg in meaningful_messages 
                if msg.sender_id is not None and msg.sender_id not in bots
            }

            return active_users, len(meaningful_messages)

        except Exception as e:
            self._logger.warning(f"Message activity analysis error: {e}")
            return set(), 0

    async def _get_bot_ids(self, chat: Chat) -> Set[int]:
        """Получение ID ботов в группе"""
        try:
            participants = await self._client.get_participants(chat)
            return {p.id for p in participants if hasattr(p, 'bot') and p.bot}
        except Exception as e:
            self._logger.error(f"Bot ID retrieval error: {e}")
            return set()

    async def _count_bots(self, chat: Chat) -> int:
        """Подсчет количества ботов в группе"""
        try:
            participants = await self._client.get_participants(chat)
            return sum(1 for p in participants if hasattr(p, 'bot') and p.bot)
        except Exception as e:
            self._logger.error(f"Bot counting error: {e}")
            return 0

@loader.tds
class AnalDestrModule(loader.Module):
    """Анализатор Дестройер"""

    strings = {
        "name": "Analdestr",
        "error": "❌ <b>Ошибка:</b> {}",
    }

    async def client_ready(self, client, db):
        """Инициализация модуля"""
        self.analyzer = ProfessionalChatAnalyzer(client)

    def _generate_stats_text(self, ping_time: float, stats: Dict) -> str:
        """Генерация текста статистики"""
        return (
            f"🌐 <b>Сетевая задержка:</b> {ping_time:.2f} мс\n\n"
            f"📊 <b>{utils.escape_html(stats.get('title', 'Неизвестно'))}:</b>\n"
            f"ID: <code>{stats.get('chat_id', 'N/A')}</code>\n"
            f"Активные участники: {stats.get('active_members', 0)}\n"
            f"Боты: {stats.get('bots', 0)}\n"
            f"Сообщений: {stats.get('total_messages', 0)}"
        )

    @loader.command()
    async def groupstat(self, message):
        """Команда получения расширенной статистики группы"""
        try:
            # Моментальный ответ с текущим пингом
            initial_ping_time = await self.analyzer.measure_network_latency()
            chat = await message.get_chat()

            # Отправка первоначального сообщения
            initial_stats = {
                'title': getattr(chat, 'title', 'Неизвестно'),
                'chat_id': chat.id,
                'active_members': '...',
                'bots': '...',
                'total_messages': '...'
            }

            response_message = await self.inline.form(
                self._generate_stats_text(initial_ping_time, initial_stats), 
                message=message,
                reply_markup=[
                    [{"text": "🔄 Обновить статистику", "callback": self._refresh_stats}]
                ]
            )

            # Асинхронный сбор полной статистики
            asyncio.create_task(self._update_stats_async(response_message, chat))

        except Exception as e:
            await self.inline.form(
                self.strings["error"].format(str(e)), 
                message=message
            )

    async def _update_stats_async(self, response_message, chat):
        """Асинхронное обновление статистики"""
        try:
            # Одновременный сбор пинга и статистики
            ping_task = asyncio.create_task(self.analyzer.measure_network_latency())
            stats_task = asyncio.create_task(self.analyzer.analyze_group_comprehensive(chat))
            
            ping_time, stats = await asyncio.gather(ping_task, stats_task)

            # Редактирование сообщения с полной статистикой
            await response_message.edit(
                self._generate_stats_text(ping_time, stats), 
                reply_markup=[
                    [{"text": "🔄 Обновить статистику", "callback": self._refresh_stats}]
                ]
            )
        except Exception as e:
            self._logger.error(f"Async stats update error: {e}")

    async def _refresh_stats(self, call):
        """Обновление статистики по кнопке"""
        try:
            # Быстрый пинг
            ping_time = await self.analyzer.measure_network_latency()
            chat = await call.message.get_chat()

            # Моментальный ответ с текущим пингом
            initial_stats = {
                'title': getattr(chat, 'title', 'Неизвестно'),
                'chat_id': chat.id,
                'active_members': '...',
                'bots': '...',
                'total_messages': '...'
            }

            await call.message.edit(
                self._generate_stats_text(ping_time, initial_stats), 
                reply_markup=[
                    [{"text": "🔄 Обновить статистику", "callback": self._refresh_stats}]
                ]
            )

            # Асинхронный сбор полной статистики
            asyncio.create_task(self._update_stats_async(call.message, chat))

        except Exception as e:
            await call.answer(f"Ошибка обновления: {str(e)}", show_alert=True)
