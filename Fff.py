from __future__ import annotations

import asyncio
import logging
from typing import Union, Dict, Set, Tuple, Optional

from telethon import TelegramClient
from telethon.tl.types import Chat

from .. import loader, utils

class ProfessionalChatAnalyzer:
    def __init__(self, client: TelegramClient):
        self._client = client
        self._logger = logging.getLogger(self.__class__.__name__)

    async def _safe_execute(
        self, 
        coro, 
        default_return=None, 
        log_error: Optional[str] = None
    ):
        """Универсальный обработчик исключений для асинхронных методов"""
        try:
            return await coro
        except Exception as e:
            if log_error:
                self._logger.error(f"{log_error}: {e}")
            return default_return

    async def measure_network_latency(
        self, 
        attempts: int = 3, 
        timeout: float = 3.0
    ) -> float:
        """Измерение сетевой задержки с повышенной надёжностью"""
        async def ping_once():
            start = asyncio.get_event_loop().time()
            await asyncio.wait_for(self._client.get_me(), timeout=timeout)
            return (asyncio.get_event_loop().time() - start) * 1000

        try:
            latencies = await asyncio.gather(
                *[ping_once() for _ in range(attempts)], 
                return_exceptions=True
            )
            
            valid_latencies = [lat for lat in latencies if isinstance(lat, (int, float))]
            return sum(valid_latencies) / len(valid_latencies) if valid_latencies else -1.0
        except Exception as e:
            self._logger.error(f"Ping measurement error: {e}")
            return -1.0

    async def analyze_group_comprehensive(
        self, 
        chat: Chat, 
        message_limit: int = 5000
    ) -> Dict[str, Union[str, int]]:
        """Комплексный анализ группового чата"""
        async def get_participants():
            return await self._safe_execute(
                self._client.get_participants(chat), 
                default_return=[], 
                log_error="Participants retrieval error"
            )

        async def get_messages():
            return await self._safe_execute(
                self._client.get_messages(chat, limit=message_limit), 
                default_return=[], 
                log_error="Messages retrieval error"
            )

        participants = await get_participants()
        messages = await get_messages()

        bots = {p.id for p in participants if getattr(p, 'bot', False)}
        
        meaningful_messages = [
            msg for msg in messages 
            if (hasattr(msg, 'text') and msg.text and len(msg.text.strip()) > 0) and
               (not hasattr(msg, 'service') or not msg.service)
        ]

        active_users = {
            msg.sender_id for msg in meaningful_messages 
            if msg.sender_id is not None and msg.sender_id not in bots
        }

        return {
            'title': getattr(chat, 'title', 'Unknown'),
            'chat_id': chat.id,
            'active_members': len(active_users),
            'bots': len(bots),
            'total_messages': len(meaningful_messages)
        }

@loader.tds
class AnalDestrModule(loader.Module):
    """Анализатор Дестройер"""

    strings = {
        "name": "Analdestr",
        "error": "❌ <b>Ошибка:</b> {}",
    }

    def __init__(self):
        self.analyzer = None
        self.last_stats = None

    async def client_ready(self, client, db):
        """Инициализация модуля"""
        self.analyzer = ProfessionalChatAnalyzer(client)

    def _generate_stats_text(self, ping_time: float, stats: Dict) -> str:
        """Генерация текста статистики"""
        loading_emoji = "🔄" if stats.get('active_members') == '...' else "📊"
        return (
            f"🌐 <b>Сетевая задержка:</b> {ping_time:.2f} мс\n\n"
            f"{loading_emoji} <b>{utils.escape_html(stats.get('title', 'Неизвестно'))}:</b>\n"
            f"ID: <code>{stats.get('chat_id', 'N/A')}</code>\n"
            f"Активные участники: {stats.get('active_members', 0)}\n"
            f"Боты: {stats.get('bots', 0)}\n"
            f"Сообщений: {stats.get('total_messages', 0)}"
        )

    async def _process_stats(self, chat):
        """Общий метод для сбора статистики"""
        initial_ping = await self.analyzer.measure_network_latency()
        empty_stats = {
            'title': getattr(chat, 'title', 'Неизвестно'),
            'chat_id': chat.id,
            'active_members': '...',
            'bots': '...',
            'total_messages': '...'
        }
        return initial_ping, empty_stats

    async def _refresh_ping(self, call):
        """Обновление только пинга"""
        try:
            ping_time = await self.analyzer.measure_network_latency()
            current_stats = self.last_stats.get('stats', {})
            
            stats_to_display = current_stats if current_stats.get('active_members') != '...' else {
                'title': getattr(call.message.chat, 'title', 'Неизвестно'),
                'chat_id': call.message.chat.id,
                'active_members': '🕒 Подсчет...',
                'bots': '🤖 Поиск...',
                'total_messages': '📝 Анализ...'
            }

            await call.message.edit(
                self._generate_stats_text(ping_time, stats_to_display), 
                reply_markup=[
                    [{"text": "🔄 Обновить пинг", "callback": self._refresh_ping}]
                ]
            )

        except Exception as e:
            await call.answer(f"Ошибка обновления: {str(e)}", show_alert=True)

    @loader.command()
    async def pstat(self, message):
        """Команда получения расширенной статистики группы"""
        try:
            chat = await message.get_chat()
            initial_ping, empty_stats = await self._process_stats(chat)

            response_message = await self.inline.form(
                self._generate_stats_text(initial_ping, empty_stats), 
                message=message,
                reply_markup=[
                    [{"text": "🔄 Обновить пинг", "callback": self._refresh_ping}]
                ]
            )

            # Асинхронный сбор полной статистики
            async def update_stats():
                stats = await self.analyzer.analyze_group_comprehensive(chat)
                ping_time = await self.analyzer.measure_network_latency()
                
                self.last_stats = {
                    'chat': chat,
                    'message': response_message,
                    'stats': stats
                }

                await response_message.edit(
                    self._generate_stats_text(ping_time, stats), 
                    reply_markup=[
                        [{"text": "🔄 Обновить пинг", "callback": self._refresh_ping}]
                    ]
                )

            asyncio.create_task(update_stats())

        except Exception as e:
            await self.inline.form(
                self.strings["error"].format(str(e)), 
                message=message
            )
