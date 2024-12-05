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

    async def _safe_network_call(
        self, 
        coro, 
        default_return=None, 
        log_error: Optional[str] = None
    ):
        """Универсальный обработчик сетевых вызовов"""
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
        """Измерение сетевой задержки"""
        try:
            start_times = []
            for _ in range(attempts):
                start = asyncio.get_event_loop().time()
                await asyncio.wait_for(self._client.get_me(), timeout=timeout)
                latency = (asyncio.get_event_loop().time() - start) * 1000
                start_times.append(latency)
            
            return sum(start_times) / len(start_times) if start_times else -1.0
        except Exception as e:
            self._logger.error(f"Ping measurement error: {e}")
            return -1.0

    async def analyze_group_comprehensive(
        self, 
        chat: Chat, 
        message_limit: int = 5000
    ) -> Dict[str, Union[str, int]]:
        """Комплексный анализ группового чата"""
        try:
            # Параллельное получение участников и сообщений
            participants, messages = await asyncio.gather(
                self._safe_network_call(
                    self._client.get_participants(chat), 
                    default_return=[], 
                    log_error="Participants retrieval error"
                ),
                self._safe_network_call(
                    self._client.get_messages(chat, limit=message_limit), 
                    default_return=[], 
                    log_error="Messages retrieval error"
                )
            )

            # Определение ботов
            bots = {p.id for p in participants if getattr(p, 'bot', False)}
            
            # Фильтрация meaningful сообщений
            meaningful_messages = [
                msg for msg in messages 
                if (hasattr(msg, 'text') and msg.text and len(msg.text.strip()) > 0) and
                   (not hasattr(msg, 'service') or not msg.service)
            ]

            # Определение активных пользователей
            active_users = {
                msg.sender_id for msg in meaningful_messages 
                if msg.sender_id is not None and msg.sender_id not in bots
            }

            return {
                'title': getattr(chat, 'title', 'Неизвестно'),
                'chat_id': chat.id,
                'active_members': len(active_users),
                'bots': len(bots),
                'total_messages': len(meaningful_messages)
            }
        except Exception as e:
            self._logger.error(f"Comprehensive analysis error: {e}")
            return {}

@loader.tds
class AnalDestrModule(loader.Module):
    """Анализатор Дестройер"""

    strings = {
        "name": "Analdestr",
        "error": "❌ <b>Ошибка:</b> {}",
    }

    def __init__(self):
        self.analyzer = None
        self.last_message = None

    async def client_ready(self, client, db):
        """Инициализация модуля"""
        self.analyzer = ProfessionalChatAnalyzer(client)

    def _generate_stats_text(self, ping_time: float, chat, stats: Dict) -> str:
        """Генерация текста статистики"""
        return (
            f"🌐 <b>Сетевая задержка:</b> {ping_time:.2f} мс\n\n"
            f"<b>{utils.escape_html(getattr(chat, 'title', 'Неизвестно'))}:</b>\n"
            f"ID: <code>{chat.id}</code>\n"
            f"Активные участники: {stats.get('active_members', 'Не определено')}\n"
            f"Боты: {stats.get('bots', 'Не определено')}\n"
            f"Сообщений: {stats.get('total_messages', 'Не определено')}"
        )

    async def _update_ping(self, call):
        """Обновление пинга"""
        try:
            # Извлекаем сохраненное сообщение и последнюю использованную статистику
            if not hasattr(self, 'last_message') or not self.last_message:
                await call.answer("Нет данных для обновления", show_alert=True)
                return

            ping_time = await self.analyzer.measure_network_latency()
            
            # Обновляем только пинг в существующем сообщении
            await self.last_message.edit(
                self._generate_stats_text(
                    ping_time, 
                    self.last_message.chat, 
                    self.last_message.stats
                ),
                reply_markup=[[{"text": "🔄 Обновить пинг", "callback": self._update_ping}]]
            )

        except Exception as e:
            await call.answer(f"Ошибка обновления: {str(e)}", show_alert=True)

    @loader.command()
    async def pstat(self, message):
        """Команда получения расширенной статистики группы"""
        try:
            chat = await message.get_chat()
            ping_time = await self.analyzer.measure_network_latency()

            # Первичное сообщение с заглушкой
            response_message = await self.inline.form(
                self._generate_stats_text(ping_time, chat, {
                    'active_members': 'Подсчет...',
                    'bots': 'Поиск...',
                    'total_messages': 'Анализ...'
                }),
                message=message,
                reply_markup=[[{"text": "🔄 Обновить пинг", "callback": self._update_ping}]]
            )

            # Асинхронный сбор полной статистики
            async def update_stats():
                stats = await self.analyzer.analyze_group_comprehensive(chat)
                new_ping_time = await self.analyzer.measure_network_latency()
                
                # Сохраняем сообщение с полной статистикой для последующих обновлений
                self.last_message = response_message
                self.last_message.chat = chat
                self.last_message.stats = stats

                await response_message.edit(
                    self._generate_stats_text(new_ping_time, chat, stats),
                    reply_markup=[[{"text": "🔄 Обновить пинг", "callback": self._update_ping}]]
                )

            asyncio.create_task(update_stats())

        except Exception as e:
            await self.inline.form(
                self.strings["error"].format(str(e)), 
                message=message
            )
