from telethon import TelegramClient
from telethon.tl.types import Chat
from telethon.errors import (
    ChatAdminRequiredError, 
    FloodWaitError, 
    RPCError
)

from hikka import loader, utils
from hikka.version import __version__

import logging
import asyncio
import traceback
import structlog
from typing import Dict, Any, Optional

logger = structlog.get_logger(__name__)

@loader.tds
class GroupStatsMod(loader.Module):
    """Профессиональный модуль анализа групповых чатов Telegram"""
    
    strings = {
        "name": "GroupStats",
        "no_chat": "❌ Чат не найден",
        "stats_header": "📊 Статистика группы: {title}",
        "ping_info": "🏓 Задержка: {ping:.2f} мс",
        "members_info": "👥 Участники: {total} (Активных: {active})",
        "admin_info": "👮 Администраторы: {admins}",
        "bots_info": "🤖 Боты: {bots}",
        "messages_info": "💬 Сообщения: Всего {total} (Текст: {text}, Медиа: {media}, Служебные: {service})"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "max_messages_analyze", 
            5000, 
            "Максимальное количество сообщений для анализа"
        )

    @loader.command(ru_doc="Получить статистику текущей группы")
    async def groupstatscmd(self, message):
        """Retrieve comprehensive group statistics"""
        try:
            # Проверяем, что это чат
            if not message.is_group and not message.is_channel:
                await message.edit("❌ Эта команда работает только в группах и каналах")
                return

            await message.edit(self.strings["stats_header"].format(title="Загрузка..."))
            
            # Получаем текущий чат
            chat = await message.get_chat()
            
            # Измеряем задержку
            ping = await self._measure_network_latency()
            
            # Анализируем участников
            participants = await self._get_participants(chat)
            
            # Анализируем сообщения
            messages_stats = await self._analyze_messages(chat)
            
            # Формируем отчет
            stats_text = "\n".join([
                self.strings["stats_header"].format(title=getattr(chat, 'title', 'Unknown')),
                self.strings["ping_info"].format(ping=ping),
                self.strings["members_info"].format(
                    total=participants['total'], 
                    active=participants['active']
                ),
                self.strings["admin_info"].format(admins=participants['admins']),
                self.strings["bots_info"].format(bots=participants['bots']),
                self.strings["messages_info"].format(
                    total=messages_stats['total'],
                    text=messages_stats['text_messages'],
                    media=messages_stats['media_messages'],
                    service=messages_stats['service_messages']
                )
            ])
            
            await message.edit(stats_text)
            
        except Exception as e:
            logger.error(f"Group stats error: {e}")
            await message.edit(f"❌ Ошибка: {traceback.format_exc()}")

    async def _measure_network_latency(self, attempts: int = 3) -> float:
        """Точное измерение сетевой задержки"""
        latencies = []
        for _ in range(attempts):
            try:
                start = asyncio.get_event_loop().time()
                async with asyncio.timeout(5.0):
                    await self.client.get_me()
                latency = (asyncio.get_event_loop().time() - start) * 1000
                latencies.append(latency)
            except Exception:
                pass
        
        return sum(latencies) / len(latencies) if latencies else 0.0

    async def _get_participants(self, chat: Chat) -> Dict[str, int]:
        """Расширенный анализ участников чата"""
        try:
            # Безопасное получение участников с обработкой исключений
            try:
                participants = await self.client.get_participants(chat)
            except FloodWaitError as e:
                logger.warning(f"Flood wait: {e}")
                return {'total': 0, 'active': 0, 'admins': 0, 'bots': 0}
            
            stats = {
                'total': len(participants),
                'active': sum(1 for p in participants if not hasattr(p, 'deleted') or not p.deleted),
                'admins': await self._count_admins(chat),
                'bots': sum(1 for p in participants if hasattr(p, 'bot') and p.bot)
            }
            
            return stats

        except Exception as e:
            logger.error(f"Participants analysis error: {e}")
            return {'total': 0, 'active': 0, 'admins': 0, 'bots': 0}

    async def _count_admins(self, chat: Chat) -> int:
        """Надёжный подсчёт администраторов"""
        try:
            # Используем более надежный метод получения администраторов
            admins = await self.client.get_participants(chat, filter='admin')
            return len(admins)

        except (ChatAdminRequiredError, RPCError):
            return 0

    async def _analyze_messages(self, chat: Chat) -> Dict[str, int]:
        """Продвинутый анализ сообщений"""
        try:
            # Безопасное получение сообщений с обработкой исключений
            try:
                messages = await self.client.get_messages(
                    chat, 
                    limit=self.config['max_messages_analyze']
                )
            except FloodWaitError as e:
                logger.warning(f"Flood wait: {e}")
                return {'total': 0, 'text_messages': 0, 'media_messages': 0, 'service_messages': 0}
            
            return {
                'total': len(messages),
                'text_messages': sum(1 for msg in messages if hasattr(msg, 'text') and msg.text),
                'media_messages': sum(1 for msg in messages if hasattr(msg, 'media') and msg.media),
                'service_messages': sum(1 for msg in messages if hasattr(msg, 'service') and msg.service)
            }

        except Exception as e:
            logger.warning(f"Message analysis error: {e}")
            return {'total': 0, 'text_messages': 0, 'media_messages': 0, 'service_messages': 0}
