from __future__ import annotations

import asyncio
import logging
import re
from typing import Dict, List, Optional, Union

import socket
import time

from telethon import TelegramClient
from telethon.tl.types import Chat, Message

from .. import loader, utils

class NetworkAnalyzer:
    @staticmethod
    async def measure_latency(client: TelegramClient, attempts: int = 3) -> Dict[str, float]:
        """Измерение сетевой задержки различными методами"""
        results = {"telethon": -1.0, "rtt": -1.0, "comprehensive": -1.0}
        
        try:
            # Telethon latency
            telethon_times = []
            for _ in range(attempts):
                start = time.time()
                try:
                    await asyncio.wait_for(client.get_me(), timeout=2)
                    telethon_times.append((time.time() - start) * 1000)
                except Exception:
                    pass
            
            if telethon_times:
                results["telethon"] = sum(telethon_times) / len(telethon_times)
            
            # RTT latency
            try:
                start = time.time()
                with socket.create_connection(('8.8.8.8', 53), timeout=2) as sock:
                    results["rtt"] = (time.time() - start) * 1000
            except Exception:
                pass
            
            # Comprehensive latency
            try:
                start = time.time()
                await asyncio.wait_for(client.get_dialogs(limit=1), timeout=2)
                results["comprehensive"] = (time.time() - start) * 1000
            except Exception:
                pass
        
        except Exception as e:
            logging.error(f"Ошибка измерения пинга: {e}")
        
        return results

class ChatAnalyzer:
    @staticmethod
    async def analyze_chat(
        client: TelegramClient, 
        chat: Union[Chat, int], 
        message_limit: int = 100000, 
        pattern: Optional[str] = None
    ) -> Dict[str, Union[str, int, List[Dict]]]:
        """Комплексный анализ чата"""
        try:
            # Параллельная загрузка участников и сообщений
            participants, messages = await asyncio.gather(
                client.get_participants(chat, limit=message_limit),
                client.get_messages(chat, limit=message_limit)
            )
            
            # Фильтрация сообщений
            def is_meaningful_message(msg: Message) -> bool:
                return (
                    hasattr(msg, 'text') and 
                    msg.text and 
                    msg.text.strip() and 
                    not getattr(msg, 'service', False)
                )
            
            meaningful_messages = list(filter(is_meaningful_message, messages))
            
            # Фильтрация по регулярному выражению
            if pattern:
                meaningful_messages = [
                    msg for msg in meaningful_messages 
                    if re.search(pattern, msg.text or '', re.IGNORECASE)
                ]
            
            # Подсчет сообщений пользователей
            user_message_count = {}
            for msg in meaningful_messages:
                if msg.sender_id:
                    user_message_count[msg.sender_id] = user_message_count.get(msg.sender_id, 0) + 1
            
            # Определение топ-пользователей
            async def get_user_info(user_id: int) -> Optional[Dict]:
                try:
                    user = await client.get_entity(user_id)
                    return {
                        'name': f"<a href='tg://user?id={user_id}'>{user.username or user.first_name or 'Unknown'}</a>",
                        'messages': user_message_count.get(user_id, 0)
                    }
                except Exception:
                    return None
            
            top_users = await asyncio.gather(*[
                get_user_info(user_id) 
                for user_id in sorted(user_message_count, key=user_message_count.get, reverse=True)[:3]
            ])
            top_users = [user for user in top_users if user is not None]
            
            # Идентификация ботов и активных пользователей
            bot_ids = {p.id for p in participants if getattr(p, 'bot', False)}
            active_user_ids = {
                msg.sender_id for msg in meaningful_messages 
                if msg.sender_id and msg.sender_id not in bot_ids
            }
            
            return {
                'title': getattr(chat, 'title', 'Неизвестно'),
                'chat_id': chat.id if hasattr(chat, 'id') else chat,
                'total_messages': len(meaningful_messages),
                'active_members': len(active_user_ids),
                'bots': len(bot_ids),
                'top_users': top_users,
                'pattern_count': len(meaningful_messages) if pattern else 0,
            }
        
        except Exception as e:
            logging.error(f"Ошибка анализа чата: {e}")
            return {}

@loader.tds
class AnalyzerModule(loader.Module):
    """Расширенный анализатор чата"""
    
    strings = {
        "name": "ChatAnalyzer",
        "error": "❌ <b>Ошибка:</b> {}",
        "ping_template": (
            "🌐 <b>Ping: {comprehensive:.2f} мс</b>\n"
            "• Telethon: {telethon:.2f} мс\n"
            "• RTT: {rtt:.2f} мс\n"
        ),
        "stats_template": (
            "\n<b>Статистика чата:</b>\n"
            "🏷️ Название: {title}\n"
            "🆔 ID: <code>{chat_id}</code>\n"
            "💬 Сообщений: {total_messages}\n"
            "👥 Активные участники: {active_members}\n"
            "🤖 Боты: {bots}\n"
            "{pattern_section}"
            "\n<b>Топ-3 активных пользователей:</b>\n"
            "{top_users_section}"
        ),
        "pattern_section": "🔍 Сообщений с '{pattern}': {pattern_count}\n",
        "top_users_template": "• {name}: {messages} сообщений\n",
    }

    def __init__(self):
        self.network_analyzer = NetworkAnalyzer()
        self.chat_analyzer = ChatAnalyzer()
        self._last_context = {"chat": None, "stats": None, "ping": None}

    async def client_ready(self, client, db):
        """Инициализация модуля"""
        self._client = client

    @loader.command()
    async def pstat(self, message):
        """Команда получения расширенной статистики чата"""
        try:
            # Разбор аргументов
            args = utils.get_args(message)
            chat_id_arg = args[0] if args else None
            pattern = None

            # Поиск регулярного выражения
            for arg in args:
                if arg.startswith("r'") and arg.endswith("'"):
                    pattern = arg[2:-1]
                    args.remove(arg)
                    chat_id_arg = args[0] if args else None
                    break

            # Определение чата
            chat = await (
                self._client.get_entity(int(chat_id_arg)) if chat_id_arg 
                else message.get_chat()
            )

            # Измерение пинга
            ping_results = await self.network_analyzer.measure_latency(self._client)

            await message.edit(
                self.strings["ping_template"].format(**ping_results)
            )

            # Сбор статистики
            stats = await self.chat_analyzer.analyze_chat(
                self._client, chat, pattern=pattern
            )

            # Подготовка секций
            top_users_section = "• Нет данных"
            if stats.get("top_users"):
                top_users_section = "".join(
                    self.strings["top_users_template"].format(**user)
                    for user in stats["top_users"]
                )

            pattern_section = (
                self.strings["pattern_section"].format(
                    pattern=pattern, 
                    pattern_count=stats.get("pattern_count", 0)
                ) if pattern else ""
            )

            # Обновление сообщения полной статистикой
            await message.edit(
                self.strings["ping_template"].format(**ping_results) +
                self.strings["stats_template"].format(
                    **stats,
                    pattern_section=pattern_section,
                    top_users_section=top_users_section
                )
            )

        except Exception as e:
            await message.edit(self.strings["error"].format(str(e)))
