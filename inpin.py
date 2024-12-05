from __future__ import annotations

import asyncio
import logging
from typing import Union, Dict, Optional

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
        """Измерение сетевой задержки"""
        try:
            latencies = [
                (asyncio.get_event_loop().time() - 
                 (start := asyncio.get_event_loop().time())) * 1000 
                for _ in range(attempts) 
                if await asyncio.wait_for(self._client.get_me(), timeout=timeout)
            ]
            
            return sum(latencies) / len(latencies) if latencies else -1.0
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
            # Параллельное получение данных
            participants, messages = await asyncio.gather(
                self._client.get_participants(chat),
                self._client.get_messages(chat, limit=message_limit)
            )

            # Определение ботов и активных пользователей
            bots = {p.id for p in participants if getattr(p, 'bot', False)}
            meaningful_messages = [
                msg for msg in messages 
                if hasattr(msg, 'text') and msg.text.strip() and 
                   (not hasattr(msg, 'service') or not msg.service)
            ]
            active_users = {
                msg.sender_id for msg in meaningful_messages 
                if msg.sender_id and msg.sender_id not in bots
            }

            return {
                'title': getattr(chat, 'title', 'Неизвестно'),
                'chat_id': chat.id,
                'total_messages': len(meaningful_messages),
                'active_members': len(active_users),
                'bots': len(bots)
            }
        except Exception as e:
            self._logger.error(f"Comprehensive analysis error: {e}")
            return {}

@loader.tds
class AnalDestrModule(loader.Module):
    """Расширенный анализатор чата"""

    strings = {
        "name": "AnalDestroy",
        "error": "❌ <b>Ошибка:</b> {}",
        "ping_template": "🌐 <b>Ping:</b> {ping_time:.2f} мс",
        "stats_template": (
            "\n\n📊 <b>Статистика чата:</b>\n"
            "🏷️ <b>Название:</b> {title}\n"
            "🆔 ID: <code>{chat_id}</code>\n"
            "💬 Сообщений: {total_messages}\n"
            "👥 Активные участники: {active_members}\n"
            "🤖 Боты: {bots}\n"
        )
    }

    def __init__(self):
        self.analyzer = None
        self._last_context = {
            'chat': None,
            'stats': None,
            'message': None
        }

    async def client_ready(self, client, db):
        """Инициализация модуля"""
        self.analyzer = ProfessionalChatAnalyzer(client)

    def _format_stats_message(self, ping_time: float, stats: Dict) -> str:
        """Форматирование сообщения со статистикой"""
        full_text = self.strings["ping_template"].format(ping_time=ping_time)
        if stats:
            full_text += self.strings["stats_template"].format(
                title=utils.escape_html(stats.get('title', 'Неизвестно')),
                chat_id=stats.get('chat_id', 'N/A'),
                total_messages=stats.get('total_messages', '🔄'),
                active_members=stats.get('active_members', '🔄'),
                bots=stats.get('bots', '🔄')
            )
        return full_text

    async def _update_ping(self, call):
        """Обновление пинга с сохранением статистики"""
        try:
            # Измеряем новый пинг
            ping_time = await self.analyzer.measure_network_latency()
            
            # Формируем полный текст с пингом и статистикой
            full_text = self._format_stats_message(ping_time, self._last_context['stats'])

            # Обновляем сообщение
            await call.edit(
                full_text, 
                reply_markup=[[{"text": "🔄 Обновить пинг", "callback": self._update_ping}]]
            )
        except Exception as e:
            await call.answer(f"Ошибка обновления: {str(e)}", show_alert=True)

    @loader.command()
    async def pstat(self, message):
        """Команда получения расширенной статистики группы"""
        try:
            # Получаем текущий чат
            chat = await message.get_chat()
            
            # Измеряем первоначальный пинг
            ping_time = await self.analyzer.measure_network_latency()

            # Отправляем первичное сообщение только с пингом
            response_message = await self.inline.form(
                self.strings["ping_template"].format(ping_time=ping_time),
                message=message,
                reply_markup=[[{"text": "🔄 Обновить пинг", "callback": self._update_ping}]]
            )

            # Асинхронный сбор полной статистики
            async def update_stats():
                try:
                    # Собираем статистику
                    stats = await self.analyzer.analyze_group_comprehensive(chat)
                    
                    # Сохраняем контекст
                    self._last_context['chat'] = chat
                    self._last_context['stats'] = stats

                    # Формируем полный текст
                    full_text = self._format_stats_message(ping_time, stats)

                    # Обновляем сообщение с пингом и статистикой
                    await response_message.edit(
                        full_text,
                        reply_markup=[[{"text": "🔄 Обновить пинг", "callback": self._update_ping}]]
                    )
                except Exception as e:
                    logging.error(f"Stats update error: {e}")

            # Запускаем сбор статистики в фоне
            asyncio.create_task(update_stats())

        except Exception as e:
            await self.inline.form(
                self.strings["error"].format(str(e)), 
                message=message
            )
