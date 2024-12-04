from __future__ import annotations

import asyncio
import logging
from typing import Optional, Union, List

from telethon import TelegramClient
from telethon.tl.types import (
    Chat, Channel, 
    ChannelParticipantAdmin, 
    ChannelParticipantCreator
)
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.errors import (
    ChatAdminRequiredError, 
    FloodWaitError, 
    RPCError
)

from .. import loader, utils


class ChatStatistics:
    """Контейнер статистики чата с fallback механизмом"""
    __slots__ = (
        'title', 'chat_id', 'chat_type', 
        'total_members', 'active_members', 
        'admins', 'bots', 'total_messages'
    )

    def __init__(
        self, 
        title: str = "Неизвестно", 
        chat_id: int = 0, 
        chat_type: str = "Неизвестно", 
        total_members: int = 0,
        active_members: int = 0,
        admins: int = 0, 
        bots: int = 0, 
        total_messages: int = 0
    ):
        self.title = title
        self.chat_id = chat_id
        self.chat_type = chat_type
        self.total_members = total_members
        self.active_members = active_members
        self.admins = admins
        self.bots = bots
        self.total_messages = total_messages

    def format(self, ping: float) -> str:
        """Форматированный вывод статистики"""
        return (
            f"🏓 <b>Пинг:</b> {ping:.2f} мс\n\n"
            f"📊 <b>{utils.escape_html(self.title)}:</b>\n"
            f"ID: <code>{self.chat_id}</code>\n"
            f"Тип: {self.chat_type}\n"
            f"Участники: {self.total_members}\n"
            f"Активные: {self.active_members}\n"
            f"Администраторы: {self.admins}\n"
            f"Боты: {self.bots}\n"
            f"Сообщений: {self.total_messages}"
        )


@loader.tds
class EnhancedPingModule(loader.Module):
    """Расширенный модуль пинга с адаптивной статистикой"""

    strings = {
        "name": "EnhancedPing",
        "error": "❌ <b>Ошибка:</b> {}"
    }

    def __init__(self):
        self._client: Optional[TelegramClient] = None
        self._logger = logging.getLogger(self.__class__.__name__)

    async def client_ready(self, client, db):
        """Инициализация клиента"""
        self._client = client

    async def _get_precise_ping(self) -> float:
        """Точное измерение задержки"""
        start = asyncio.get_event_loop().time()
        await self._client.get_me()
        return (asyncio.get_event_loop().time() - start) * 1000

    async def _get_chat_full_info(self, chat: Union[Chat, Channel]):
        """Получение полной информации о чате с обработкой ошибок"""
        try:
            if isinstance(chat, Channel):
                return await self._client(GetFullChannelRequest(chat))
            return await self._client(GetFullChatRequest(chat.id))
        except Exception:
            return None

    async def _count_messages(self, chat: Union[Chat, Channel]) -> int:
        """
        Безопасный подсчет сообщений с fallback механизмом
        """
        try:
            # Получаем последние сообщения с фильтрацией системных
            messages = await self._client.get_messages(
                chat, 
                limit=None,
                filter=lambda m: not (
                    getattr(m, 'service', False) or 
                    getattr(m, 'action', None)
                )
            )
            return len(messages)
        except Exception:
            # Fallback: пытаемся получить хотя бы базовую информацию
            try:
                full_chat = await self._get_chat_full_info(chat)
                return getattr(full_chat, 'messages', 0)
            except Exception:
                return 0

    async def _analyze_chat_flexible(self, chat: Union[Chat, Channel]) -> ChatStatistics:
        """
        Гибкий анализ статистики чата с множественными fallback механизмами
        """
        try:
            # Определение типа чата
            if isinstance(chat, Channel):
                chat_type = "Супер-группа" if chat.megagroup else "Канал"
            elif isinstance(chat, Chat):
                chat_type = "Группа"
            else:
                chat_type = "Неизвестно"

            # Получение полной информации о чате
            full_chat_info = await self._get_chat_full_info(chat)
            total_members = getattr(full_chat_info.full_chat, 'participants_count', 0)

            # Безопасный подсчет сообщений
            total_messages = await self._count_messages(chat)

            # Попытка получения участников
            try:
                participants = await self._client.get_participants(
                    chat, 
                    limit=200,  # Ограничиваем для больших чатов
                    aggressive=False  # Более мягкий режим
                )
                
                active_members = sum(1 for p in participants if not p.deleted and not p.bot)
                admins = sum(1 for p in participants if isinstance(p, (ChannelParticipantAdmin, ChannelParticipantCreator)))
                bots = sum(1 for p in participants if p.bot)
            except (ChatAdminRequiredError, FloodWaitError):
                # Fallback если не удалось получить участников
                active_members = admins = bots = 0

            return ChatStatistics(
                title=utils.escape_html(getattr(chat, 'title', 'Неизвестно')),
                chat_id=chat.id,
                chat_type=chat_type,
                total_members=total_members,
                active_members=active_members,
                admins=admins,
                bots=bots,
                total_messages=total_messages
            )

        except Exception as e:
            self._logger.error(f"Критическая ошибка анализа: {e}")
            return ChatStatistics(chat_id=getattr(chat, 'id', 0))

    @loader.command()
    async def pong(self, message):
        """Команда для получения статистики чата"""
        try:
            ping_time = await self._get_precise_ping()
            chat = await self._client.get_entity(message.chat_id)
            chat_stats = await self._analyze_chat_flexible(chat)

            async def refresh_callback(call):
                new_ping = await self._get_precise_ping()
                await call.edit(
                    chat_stats.format(new_ping),
                    reply_markup=self._create_refresh_markup(refresh_callback)
                )

            await self.inline.form(
                chat_stats.format(ping_time),
                message=message,
                reply_markup=self._create_refresh_markup(refresh_callback)
            )

        except Exception as e:
            await self.inline.form(
                self.strings["error"].format(str(e)), 
                message=message
            )

    def _create_refresh_markup(self, callback=None):
        """Создание разметки обновления"""
        return [{"text": "🔄 Обновить", "callback": callback or (lambda _: None)}]
