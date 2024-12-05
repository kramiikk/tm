from __future__ import annotations

import asyncio
import logging
from typing import Union, Dict, Set, Tuple, Optional

from telethon import TelegramClient
from telethon.tl.types import Chat
from telethon.events import CallbackQuery

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
    """Расширенный анализатор чата"""

    strings = {
        "name": "ChatAnalyzer",
        "error": "❌ <b>Ошибка:</b> {}",
        "stats_template": (
            "📊 <b>Статистика чата:</b>\n\n"
            "🌐 <b>Сетевая задержка:</b> {ping_time:.2f} мс\n\n"
            "🏷️ <b>Название:</b> {title}\n"
            "🆔 ID: <code>{chat_id}</code>\n"
            "👥 Активные участники: {active_members}\n"
            "🤖 Боты: {bots}\n"
            "💬 Сообщений: {total_messages}"
        )
    }

    def __init__(self):
        self.analyzer = None
        self.current_chat = None
        self.last_stats = {}
        self.last_message = None

    async def client_ready(self, client, db):
        """Инициализация модуля"""
        self.analyzer = ProfessionalChatAnalyzer(client)

    async def _update_stats(self, message=None, call=None):
        """Общий метод обновления статистики"""
        try:
            # Определяем chat из сообщения или каллбэка
            chat = self.current_chat or (await message.get_chat() if message else None)
            
            if not chat:
                if call:
                    await call.answer("❌ Чат не выбран", show_alert=True)
                return

            # Измерение пинга
            ping_time = await self.analyzer.measure_network_latency()

            # Сбор статистики
            stats = await self.analyzer.analyze_group_comprehensive(chat)
            
            # Форматирование текста
            stats_text = self.strings["stats_template"].format(
                ping_time=ping_time,
                title=utils.escape_html(stats.get('title', 'Неизвестно')),
                chat_id=stats.get('chat_id', 'N/A'),
                active_members=stats.get('active_members', '🔄'),
                bots=stats.get('bots', '🔄'),
                total_messages=stats.get('total_messages', '🔄')
            )

            # Кнопки
            buttons = [
                [{"text": "🔄 Обновить статистику", "callback": self._update_stats}]
            ]

            # Выбор метода ответа
            if call:
                await call.edit(stats_text, reply_markup=buttons)
            elif message:
                self.last_message = await self.inline.form(
                    stats_text, 
                    message=message, 
                    reply_markup=buttons
                )

            # Сохраняем контекст
            self.current_chat = chat
            self.last_stats = stats

        except Exception as e:
            error_text = f"❌ Ошибка обновления: {str(e)}"
            if call:
                await call.answer(error_text, show_alert=True)
            elif message:
                await self.inline.form(error_text, message=message)

    @loader.command()
    async def pstat(self, message):
        """Команда получения расширенной статистики группы"""
        await self._update_stats(message=message)
