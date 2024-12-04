from __future__ import annotations

import asyncio
import logging
from typing import Union, Optional, List, Any

from telethon import TelegramClient
from telethon.tl.types import (
    Chat, 
    Channel, 
    User, 
    Message,
    PeerChannel,
    PeerChat,
    ChannelParticipantAdmin,
    ChannelParticipantCreator
)
from telethon.tl.functions.channels import GetFullChannelRequest, GetParticipantsRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.types import ChannelParticipantsFilter
from telethon.errors import (
    ChatAdminRequiredError, 
    FloodWaitError, 
    RPCError,
    ChatForbiddenError
)

from .. import loader, utils

logger = logging.getLogger(__name__)

class AdvancedChatAnalyzer:
    def __init__(self, client: TelegramClient):
        self._client = client

    async def get_precise_ping(self) -> float:
        """Профессиональное измерение задержки"""
        try:
            start = asyncio.get_event_loop().time()
            await self._client.get_me()
            return (asyncio.get_event_loop().time() - start) * 1000
        except Exception as e:
            logger.error(f"Ping measurement error: {e}")
            return -1.0

    async def _get_full_chat_info(self, chat: Union[Chat, Channel]) -> dict:
        """Получение полной информации о чате с максимальной детализацией"""
        try:
            if isinstance(chat, Channel):
                full_chat = await self._client(GetFullChannelRequest(chat))
                return {
                    'total_members': getattr(full_chat.full_chat, 'participants_count', 0),
                    'description': getattr(full_chat.full_chat, 'about', '')
                }
            elif isinstance(chat, Chat):
                full_chat = await self._client(GetFullChatRequest(chat.id))
                return {
                    'total_members': getattr(full_chat.full_chat, 'participants_count', 0),
                    'description': ''
                }
            return {'total_members': 0, 'description': ''}
        except Exception as e:
            logger.warning(f"Full chat info error: {e}")
            return {'total_members': 0, 'description': ''}

    async def count_admin_participants(self, chat: Union[Chat, Channel]) -> int:
        """Профессиональный подсчет администраторов с учетом всех нюансов"""
        try:
            if isinstance(chat, Channel) and chat.megagroup:
                try:
                    # Максимально точный метод через участников с фильтром
                    request = GetParticipantsRequest(
                        channel=chat,
                        filter=ChannelParticipantsFilter(),
                        offset=0,
                        limit=100,
                        hash=0
                    )
                    result = await self._client(request)
                    
                    admins = sum(1 for p in result.participants 
                                 if isinstance(p, (ChannelParticipantAdmin, ChannelParticipantCreator)))
                    return admins
                except Exception as detailed_e:
                    logger.warning(f"Detailed admin count error: {detailed_e}")
            
            # Резервный метод через прямой подсчет
            participants = await self._client.get_participants(
                chat, 
                filter=lambda p: isinstance(p, (ChannelParticipantAdmin, ChannelParticipantCreator))
            )
            return len(participants)
        except Exception as e:
            logger.error(f"Admin counting fatal error: {e}")
            return 0

    async def count_user_messages(
        self, 
        chat: Union[Chat, Channel], 
        limit: int = 10000
    ) -> int:
        """Профессиональный подсчет relevantных сообщений"""
        try:
            # Расширенный алгоритм фильтрации сообщений
            def message_filter(message):
                # Исключаем служебные, пустые и медиа сообщения
                return (
                    not message.service and 
                    not message.media and 
                    message.text and 
                    len(message.text.strip()) > 0
                )

            messages = await self._client.get_messages(
                chat, 
                limit=limit, 
                filter=message_filter
            )
            return len(messages)
        except Exception as e:
            logger.warning(f"Message counting error: {e}")
            return 0

    async def analyze_chat(self, chat: Union[Chat, Channel]) -> dict:
        """Комплексный анализ чата с максимальной информативностью"""
        try:
            # Определение типа чата с профессиональной точностью
            chat_type = (
                "Супер-группа" if getattr(chat, 'megagroup', False) 
                else "Канал" if isinstance(chat, Channel) 
                else "Группа"
            )

            # Получение полной информации о чате
            full_chat_info = await self._get_full_chat_info(chat)

            # Расширенный анализ участников
            try:
                all_participants = await self._client.get_participants(chat)
                active_members = sum(
                    1 for p in all_participants 
                    if not p.deleted and not p.bot and not p.is_self
                )
                bots = sum(1 for p in all_participants if p.bot)
            except Exception as e:
                logger.warning(f"Participants analysis error: {e}")
                active_members = full_chat_info['total_members']
                bots = 0

            # Подсчет администраторов с профессиональной логикой
            admins = await self.count_admin_participants(chat)
            
            # Подсчет сообщений с расширенной фильтрацией
            total_messages = await self.count_user_messages(chat)

            return {
                'title': getattr(chat, 'title', 'Неизвестно'),
                'chat_id': chat.id,
                'chat_type': chat_type,
                'total_members': full_chat_info['total_members'],
                'active_members': active_members,
                'admins': admins,
                'bots': bots,
                'total_messages': total_messages
            }
        except Exception as e:
            logger.error(f"Comprehensive chat analysis failed: {e}")
            return {}

@loader.tds
class PingKongModule(loader.Module):
    """Профессиональный модуль статистики чата"""

    strings = {
        "name": "PongCponk", 
        "error": "❌ <b>Ошибка:</b> {}"
    }

    async def client_ready(self, client, db):
        self.statistic_fetcher = AdvancedChatAnalyzer(client)

    @loader.command()
    async def pong(self, message):
        """Команда получения статистики чата"""
        try:
            ping_time = await self.statistic_fetcher.get_precise_ping()
            chat = await message.get_chat()
            stats = await self.statistic_fetcher.analyze_chat(chat)

            # Профессиональное форматирование с безопасным получением
            response = (
                f"🏓 <b>Пинг:</b> {ping_time:.2f} мс\n\n"
                f"📊 <b>{utils.escape_html(stats.get('title', 'Неизвестно'))}:</b>\n"
                f"ID: <code>{stats.get('chat_id', 'N/A')}</code>\n"
                f"Тип: {stats.get('chat_type', 'Неизвестно')}\n"
                f"Участники: {stats.get('total_members', 0)}\n"
                f"Активные: {stats.get('active_members', 0)}\n"
                f"Администраторы: {stats.get('admins', 0)}\n"
                f"Боты: {stats.get('bots', 0)}\n"
                f"Сообщений: {stats.get('total_messages', 0)}"
            )

            async def refresh_callback(call):
                new_ping = await self.statistic_fetcher.get_precise_ping()
                new_response = response.replace(f"🏓 <b>Пинг:</b> {ping_time:.2f} мс", f"🏓 <b>Пинг:</b> {new_ping:.2f} мс")
                await call.edit(new_response)

            await self.inline.form(
                response, 
                message=message,
                reply_markup=[{"text": "🔄 Обновить", "callback": refresh_callback}]
            )
        except Exception as e:
            await self.inline.form(
                self.strings["error"].format(str(e)), 
                message=message
            )
