from __future__ import annotations

import asyncio
import logging
from typing import Union, Optional, List

from telethon import TelegramClient
from telethon.tl.types import (
    Chat, 
    Channel, 
    User, 
    Message,
    ChannelParticipantAdmin,
    ChannelParticipantCreator
)
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.errors import (
    ChatAdminRequiredError, 
    FloodWaitError, 
    RPCError
)

from .. import loader, utils

logger = logging.getLogger(__name__)

class ChatStatisticsFetcher:
    def __init__(self, client: TelegramClient):
        self._client = client

    async def get_precise_ping(self) -> float:
        """Точное измерение задержки"""
        try:
            start = asyncio.get_event_loop().time()
            await self._client.get_me()
            return (asyncio.get_event_loop().time() - start) * 1000
        except Exception as e:
            logger.error(f"Ping measurement error: {e}")
            return -1.0

    async def count_user_messages(
        self, 
        chat: Union[Chat, Channel], 
        limit: int = 10000
    ) -> int:
        """Профессиональный подсчет пользовательских сообщений"""
        try:
            messages = await self._client.get_messages(
                chat, 
                limit=limit,
                filter=lambda m: (
                    m.sender and 
                    not m.service and 
                    not m.media and 
                    not isinstance(m.sender, User) and 
                    m.text and len(m.text.strip()) > 0
                )
            )
            return len(messages)
        except Exception as e:
            logger.warning(f"Message counting error: {e}")
            return 0

    async def get_admin_count(
        self, 
        chat: Union[Chat, Channel]
    ) -> int:
        """Точный подсчет администраторов"""
        try:
            participants = await self._client.get_participants(
                chat, 
                filter=lambda p: isinstance(p, (ChannelParticipantAdmin, ChannelParticipantCreator))
            )
            return len(participants)
        except Exception as e:
            logger.error(f"Admin counting error: {e}")
            return 0

    async def analyze_chat(
        self, 
        chat: Union[Chat, Channel]
    ) -> dict:
        """Комплексный анализ чата"""
        try:
            # Определение типа чата
            chat_type = (
                "Супер-группа" if getattr(chat, 'megagroup', False) 
                else "Канал" if isinstance(chat, Channel) 
                else "Группа"
            )

            # Получение полной информации о чате
            try:
                if isinstance(chat, Channel):
                    full_chat = await self._client(GetFullChannelRequest(chat))
                    total_members = getattr(full_chat.full_chat, 'participants_count', 0)
                else:
                    total_members = len(await self._client.get_participants(chat))
            except Exception:
                total_members = 0

            # Получение участников
            try:
                all_participants = await self._client.get_participants(chat)
                active_members = sum(
                    1 for p in all_participants 
                    if not p.deleted and not p.bot
                )
                bots = sum(1 for p in all_participants if p.bot)
            except Exception:
                active_members = total_members
                bots = 0

            # Подсчет администраторов
            admins = await self.get_admin_count(chat)
            total_messages = await self.count_user_messages(chat)

            return {
                'title': getattr(chat, 'title', 'Неизвестно'),
                'chat_id': chat.id,
                'chat_type': chat_type,
                'total_members': total_members,
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
        "name": "EnhancedPing", 
        "error": "❌ <b>Ошибка:</b> {}"
    }

    async def client_ready(self, client, db):
        self.statistic_fetcher = ChatStatisticsFetcher(client)

    @loader.command()
    async def pong(self, message):
        """Команда получения статистики чата"""
        try:
            ping_time = await self.statistic_fetcher.get_precise_ping()
            chat = await message.get_chat()
            stats = await self.statistic_fetcher.analyze_chat(chat)

            # Форматирование статистики
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
