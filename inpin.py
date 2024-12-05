from __future__ import annotations

import asyncio
import logging
from typing import Union, Dict, List

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
    ) -> Dict[str, float]:
        """
        Комплексное измерение сетевой задержки с улучшенным RTT
        """
        results = {
            'telethon': -1.0,
            'rtt': -1.0,
            'comprehensive': -1.0
        }
    
        try:
            # Метод 1: Telethon get_me()
            telethon_latencies = []
            for _ in range(attempts):
                start = asyncio.get_event_loop().time()
                try:
                    await asyncio.wait_for(self._client.get_me(), timeout=timeout/3)
                    latency = (asyncio.get_event_loop().time() - start) * 1000
                    telethon_latencies.append(latency)
                except Exception:
                    pass
            
            if telethon_latencies:
                results['telethon'] = sum(telethon_latencies) / len(telethon_latencies)
    
            # Метод 2: Улучшенный RTT с использованием сетевых замеров
            rtt_latencies = []
            try:
                # Попытка использовать прямое измерение через socket
                import socket
                import time
    
                def measure_rtt(host='8.8.8.8', port=53):
                    try:
                        start = time.time()
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.settimeout(timeout/3)
                            s.connect((host, port))
                        return (time.time() - start) * 1000
                    except Exception:
                        return -1.0
    
                # Несколько попыток измерения
                for _ in range(attempts):
                    rtt = measure_rtt()
                    if rtt > 0:
                        rtt_latencies.append(rtt)
                
                if rtt_latencies:
                    results['rtt'] = sum(rtt_latencies) / len(rtt_latencies)
            except Exception:
                # Резервный метод через Telegram DC
                try:
                    dc_options = self._client.session.dc_options
                    if dc_options:
                        dc = dc_options[0]
                        start = asyncio.get_event_loop().time()
                        await asyncio.wait_for(
                            self._client._connection.connect(
                                dc.ip_address, 
                                dc.port, 
                                dc.id
                            ), 
                            timeout=timeout/3
                        )
                        results['rtt'] = (asyncio.get_event_loop().time() - start) * 1000
                except Exception:
                    pass
    
            # Метод 3: Комплексное измерение
            comprehensive_latencies = []
            
            # Замер через получение диалогов
            try:
                start = asyncio.get_event_loop().time()
                await asyncio.wait_for(
                    self._client.get_dialogs(limit=1), 
                    timeout=timeout/3
                )
                comprehensive_latencies.append(
                    (asyncio.get_event_loop().time() - start) * 1000
                )
            except Exception:
                pass
            
            # Замер через отправку служебного сообщения самому себе
            try:
                start = asyncio.get_event_loop().time()
                me = await self._client.get_me()
                await asyncio.wait_for(
                    self._client.send_message(me.id, "ping"),
                    timeout=timeout/3
                )
                comprehensive_latencies.append(
                    (asyncio.get_event_loop().time() - start) * 1000
                )
            except Exception:
                pass
            
            if comprehensive_latencies:
                results['comprehensive'] = sum(comprehensive_latencies) / len(comprehensive_latencies)
    
        except Exception as e:
            self._logger.error(f"Ошибка измерения пинга: {e}")
    
        return results

    async def analyze_group_comprehensive(
        self, 
        chat: Chat, 
        message_limit: int = 5000
    ) -> Dict[str, Union[str, int]]:
        """Комплексный анализ группового чата"""
        try:
            participants, messages = await asyncio.gather(
                self._client.get_participants(chat),
                self._client.get_messages(chat, limit=message_limit)
            )

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
            self._logger.error(f"Ошибка анализа чата: {e}")
            return {}

@loader.tds
class AnalDestrModule(loader.Module):
    """Расширенный анализатор чата"""

    strings = {
        "name": "AnalDestroy",
        "error": "❌ <b>Ошибка:</b> {}",
        "ping_template": (
            "🌐 <b>Ping:</b>\n"
            "• Telethon: {telethon:.2f} мс\n"
            "• RTT: {rtt:.2f} мс\n"
            "• Comprehensive: {comprehensive:.2f} мс"
        ),
        "stats_template": (
            "\n\n📊 <b>Статистика чата:</b>\n\n"
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
            'ping': None
        }

    async def client_ready(self, client, db):
        """Инициализация модуля"""
        self.analyzer = ProfessionalChatAnalyzer(client)

    async def _update_ping(self, call):
        """Обновление пинга с сохранением статистики"""
        try:
            # Измеряем пинг всеми методами
            ping_results = await self.analyzer.measure_network_latency()
            
            # Формируем текст
            ping_text = self.strings["ping_template"].format(**ping_results)
            
            # Добавляем статистику, если была
            if self._last_context['stats']:
                ping_text += self.strings["stats_template"].format(
                    **self._last_context['stats']
                )

            # Обновляем сообщение
            await call.edit(
                ping_text, 
                reply_markup=[[{"text": "🔄 Обновить пинг", "callback": self._update_ping}]]
            )
        except Exception as e:
            await call.answer(f"Ошибка обновления: {str(e)}", show_alert=True)

    @loader.command()
    async def pstat(self, message):
        """Команда получения расширенной статистики"""
        try:
            # Получаем текущий чат
            chat = await message.get_chat()
            
            # Измеряем пинг
            ping_results = await self.analyzer.measure_network_latency()

            # Отправляем первичное сообщение с пингом
            response_message = await self.inline.form(
                self.strings["ping_template"].format(**ping_results),
                message=message,
                reply_markup=[[{"text": "🔄 Обновить пинг", "callback": self._update_ping}]]
            )

            # Асинхронный сбор статистики
            async def update_stats():
                try:
                    # Собираем статистику
                    stats = await self.analyzer.analyze_group_comprehensive(chat)
                    
                    # Сохраняем контекст
                    self._last_context['chat'] = chat
                    self._last_context['stats'] = stats
                    self._last_context['ping'] = ping_results

                    # Формируем полный текст
                    full_text = (
                        self.strings["ping_template"].format(**ping_results) +
                        self.strings["stats_template"].format(**stats)
                    )

                    # Обновляем сообщение
                    await response_message.edit(
                        full_text,
                        reply_markup=[[{"text": "🔄 Обновить пинг", "callback": self._update_ping}]]
                    )
                except Exception as e:
                    logging.error(f"Ошибка обновления статистики: {e}")

            # Запускаем сбор статистики в фоне
            asyncio.create_task(update_stats())

        except Exception as e:
            await self.inline.form(
                self.strings["error"].format(str(e)), 
                message=message
            )
