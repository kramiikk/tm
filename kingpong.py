from __future__ import annotations

import asyncio
import logging
from typing import Optional, List, Dict, Any, Union

from telethon import TelegramClient, events
from telethon.tl.types import (
    User, Chat, Channel, 
    ChannelParticipantAdmin, ChannelParticipantCreator
)
from telethon.errors import (
    ChatAdminRequiredError, 
    FloodWaitError, 
    RPCError
)

from .. import loader, utils


class EnhancedPingError(Exception):
    """Специализированное исключение для модуля"""
    pass


def retry_decorator(max_retries: int = 3, delay: float = 1.0):
    """
    Декоратор для асинхронных повторных попыток с экспоненциальной задержкой
    
    :param max_retries: Максимальное число попыток
    :param delay: Начальная задержка между попытками
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt == max_retries:
                        logging.error(f"Ошибка после {max_retries} попыток: {e}")
                        raise
                    await asyncio.sleep(delay * (2 ** attempt))
        return wrapper
    return decorator


class ChatStatistics:
    """Легковесный контейнер статистики чата"""
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
    """Расширенный модуль пинга с детальной статистикой"""

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

    @retry_decorator(max_retries=2)
    async def _get_precise_ping(self) -> float:
        """Точное измерение задержки"""
        start = asyncio.get_event_loop().time()
        await self._client.get_me()
        return (asyncio.get_event_loop().time() - start) * 1000

    @retry_decorator(max_retries=2)
    async def _analyze_chat(self, chat: Union[Chat, Channel]) -> ChatStatistics:
        """
        Комплексный анализ статистики чата
        
        :param chat: Объект чата Telegram
        :return: Объект со статистикой
        """
        try:
            # Определение типа чата
            if isinstance(chat, Channel):
                chat_type = "Супер-группа" if chat.megagroup else "Канал"
            elif isinstance(chat, Chat):
                chat_type = "Группа"
            else:
                chat_type = "Неизвестно"

            # Получение участников
            try:
                participants = await self._client.get_participants(chat, limit=None)
            except (ChatAdminRequiredError, FloodWaitError):
                participants = await self._client.get_participants(chat, limit=200)

            # Подсчет статистики
            total_members = len(participants)
            active_members = sum(1 for p in participants if not p.deleted and not p.bot)
            admins = sum(1 for p in participants if isinstance(p, (ChannelParticipantAdmin, ChannelParticipantCreator)))
            bots = sum(1 for p in participants if p.bot)

            # Подсчет сообщений
            messages = await self._client.get_messages(
                chat, 
                limit=None, 
                filter=lambda m: not (m.service or getattr(m, 'action', None))
            )
            total_messages = len(messages)

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
            self._logger.error(f"Ошибка анализа чата: {e}")
            return ChatStatistics()

    @loader.command()
    async def ping(self, message):
        """Команда для получения статистики чата"""
        try:
            ping_time = await self._get_precise_ping()
            chat = await self._client.get_entity(message.chat_id)
            chat_stats = await self._analyze_chat(chat)

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
