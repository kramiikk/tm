""" Author: @kramiikk """

import asyncio
import json
import logging
import random
import time
from collections import OrderedDict
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Union

from telethon.tl.types import Message
from telethon.errors import (
    ChatWriteForbiddenError,
    UserBannedInChannelError,
    FloodWaitError,
)

from .. import loader

logger = logging.getLogger(__name__)


class RateLimiter:
    """Глобальный ограничитель частоты отправки сообщений"""

    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Проверяет возможность отправки и при необходимости ждет"""
        async with self._lock:
            now = time.time()

            self.requests = [t for t in self.requests if now - t < self.time_window]

            if len(self.requests) >= self.max_requests:
                wait_time = self.time_window - (now - self.requests[0])
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            self.requests.append(now)

    async def get_stats(self) -> dict:
        """Возвращает текущую статистику использования"""
        async with self._lock:
            now = time.time()
            active_requests = [t for t in self.requests if now - t < self.time_window]
            return {
                "current_requests": len(active_requests),
                "max_requests": self.max_requests,
                "time_window": self.time_window,
                "usage_percent": round(
                    len(active_requests) / self.max_requests * 100, 1
                ),
            }


class SimpleCache:
    """Улучшенный кэш с автоочисткой"""

    def __init__(self, ttl: int = 3600, max_size: int = 50):
        self.cache = OrderedDict()
        self.ttl = ttl
        self.max_size = max_size
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 3000
        self._cleaning = False

    async def get(self, key):
        """Получает значение из кэша с проверкой на очистку"""
        async with self._lock:
            await self._maybe_cleanup()
            if key not in self.cache:
                return None
            timestamp, value = self.cache[key]
            if time.time() - timestamp > self.ttl:
                del self.cache[key]
                return None
            self.cache.move_to_end(key)
            return value

    async def set(self, key, value):
        """Устанавливает значение в кэш с оптимизированной очисткой"""
        async with self._lock:
            await self._maybe_cleanup()
            if len(self.cache) >= self.max_size:
                to_remove = max(1, len(self.cache) // 4)
                for _ in range(to_remove):
                    self.cache.popitem(last=False)
            self.cache[key] = (time.time(), value)

    async def _maybe_cleanup(self):
        """Проверяет необходимость очистки устаревших записей"""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            await self.clean_expired()
            self._last_cleanup = current_time

    async def clean_expired(self):
        """Оптимизированная очистка устаревших записей"""
        if self._cleaning:
            return
        try:
            self._cleaning = True
            async with self._lock:
                current_time = time.time()
                self.cache = OrderedDict(
                    (k, v)
                    for k, v in self.cache.items()
                    if current_time - v[0] <= self.ttl
                )
        finally:
            self._cleaning = False

    async def get_stats(self) -> dict:
        """Получение статистики кэша"""
        async with self._lock:
            try:
                current_time = time.time()
                active_entries = {
                    k: (t, v)
                    for k, (t, v) in self.cache.items()
                    if current_time - t <= self.ttl
                }
                expired_entries = len(self.cache) - len(active_entries)

                stats = {
                    "total_entries": len(self.cache),
                    "active_entries": len(active_entries),
                    "expired_entries": expired_entries,
                    "max_size": self.max_size,
                    "ttl_seconds": self.ttl,
                    "usage_percent": round(len(self.cache) / self.max_size * 100, 1),
                }

                if active_entries:
                    timestamps = [t for t, _ in active_entries.values()]
                    stats.update(
                        {
                            "oldest_entry_age": round(
                                (current_time - min(timestamps)) / 60, 1
                            ),
                            "newest_entry_age": round(
                                (current_time - max(timestamps)) / 60, 1
                            ),
                        }
                    )
                return stats
            except Exception as e:
                logger.error(f"Error getting cache stats: {e}")
                return {
                    "total_entries": 0,
                    "active_entries": 0,
                    "expired_entries": 0,
                    "max_size": self.max_size,
                    "ttl_seconds": self.ttl,
                    "usage_percent": 0,
                }


def register(cb):
    """Регистрация модуля"""
    cb(BroadcastMod())
    return []


@loader.tds
class BroadcastMod(loader.Module):
    """Модуль для управления рассылками

    Используйте <code>.br</code> для управления рассылками.

    <strong>Команды:</strong>

    <ul>
        <li><code>.br add <код></code> - <strong>Создать или добавить сообщение в рассылку.</strong> Ответьте этой командой на сообщение, которое хотите добавить. Если рассылка с указанным <код> не существует, она будет создана.
            <ul>
                <li>Пример: <code>.br my_broadcast</code> (в ответ на сообщение)</li>
            </ul></li>
        <li><code>.br delete <код></code> - <strong>Удалить рассылку.</strong>  Удаляет рассылку с указанным <код> вместе со всеми ее сообщениями и настройками.
            <ul>
                <li>Пример: <code>.br delete my_broadcast</code></li>
            </ul></li>
        <li><code>.br remove <код></code> - <strong>Удалить сообщение из рассылки.</strong> Ответьте этой командой на сообщение, которое хотите удалить из указанной рассылки.
            <ul>
                <li>Пример: <code>.br remove my_broadcast</code> (в ответ на сообщение)</li>
            </ul></li>
        <li><code>.br addchat <код> [ссылка/юзернейм/ID]</code> - <strong>Добавить чат в рассылку.</strong> Добавляет текущий чат или указанный чат (по ссылке, юзернейму или ID) в список получателей рассылки.
            <ul>
                <li>Пример (добавить текущий чат): <code>.br addchat my_broadcast</code></li>
                <li>Пример (добавить по ссылке): <code>.br addchat my_broadcast t.me/my_channel</code></li>
                <li>Пример (добавить по ID): <code>.br addchat my_broadcast 123456789</code></li>
            </ul></li>
        <li><code>.br rmchat <код> [ссылка/юзернейм/ID]</code> - <strong>Удалить чат из рассылки.</strong> Удаляет текущий чат или указанный чат из списка получателей рассылки.
            <ul>
                <li>Пример (удалить текущий чат): <code>.br rmchat my_broadcast</code></li>
                <li>Пример (удалить по юзернейму): <code>.br rmchat my_broadcast my_channel</code></li>
            </ul></li>
        <li><code>.br int <код> <мин> <макс></code> - <strong>Установить интервал отправки.</strong> Задает случайный интервал в минутах между отправкой сообщений в рассылке (минимальное и максимальное значения).
            <ul>
                <li>Пример: <code>.br int my_broadcast 5 10</code> (интервал от 5 до 10 минут)</li>
            </ul></li>
        <li><code>.br mode <код> <режим></code> - <strong>Установить режим отправки.</strong> Определяет способ отправки сообщений в рассылке.
            <ul>
                <li><code>auto</code>: Автоматически выбирает режим (пересылка для медиа, отправка текста для текста).</li>
                <li><code>normal</code>: Отправляет сообщения как обычный текст (может не работать для медиа).</li>
                <li><code>forward</code>: Пересылает сообщения (работает для медиа и текста).</li>
                <li>Пример: <code>.br mode my_broadcast forward</code></li>
            </ul></li>
        <li><code>.br allmsgs <код> <on/off></code> - <strong>Управлять отправкой всех сообщений.</strong>
            <ul>
                <li><code>on</code>: Отправлять все сообщения из рассылки по очереди в каждый чат.</li>
                <li><code>off</code>: Отправлять только одно, случайно выбранное сообщение из рассылки в каждый чат.</li>
                <li>Пример: <code>.br allmsgs my_broadcast on</code></li>
            </ul></li>
        <li><code>.br start <код></code> - <strong>Запустить рассылку.</strong> Начинает отправку сообщений в соответствии с настройками рассылки.
            <ul>
                <li>Пример: <code>.br start my_broadcast</code></li>
            </ul></li>
        <li><code>.br stop <код></code> - <strong>Остановить рассылку.</strong> Прекращает активную отправку сообщений.
            <ul>
                <li>Пример: <code>.br stop my_broadcast</code></li>
            </ul></li>
        <li><code>.br watcher</code> <on/off> - <strong>Включить/выключить автоматическое добавление чатов.</strong> Когда включено, чаты, в которых вы отправляете сообщение, начинающееся с !код_рассылки, будут автоматически добавлены в эту рассылку.</li>
            <ul>
                <li>Пример использования (в чате, который нужно добавить в рассылку с кодом <code>road</code>): <code>!road</code></li>
            </ul></ins>
        <li><code>.br list</code> - <strong>Показать список рассылок.</strong></li>
    </ul>        
    """

    strings = {"name": "Broadcast"}

    async def client_ready(self):
        """Инициализация при загрузке модуля"""
        self.manager = BroadcastManager(self._client, self.db)
        await self.manager._load_config()
        self.me_id = (await self._client.get_me()).id
    
    async def watcher(self, message: Message):
        """Автоматически добавляет чаты в рассылку."""
        try:
            if not self.manager.watcher_enabled:
                return
            if not (message and message.text and message.text.startswith("!")):
                return
            if message.sender_id != self.me_id:
                return
            parts = message.text.split()
            if len(parts) != 2:
                logger.info(
                    f"Parts length check failed. Got {len(parts)} parts: {parts}"
                )
                return
            code_name = parts[0][1:]
            if not code_name:
                logger.info("Empty code name")
                return
            chat_id = message.chat_id
            logger.info(f"Processing code: {code_name}, chat_id: {chat_id}")

            code = self.codes.get(code_name)
            if not code:
                logger.info(f"Code {code_name} not found in self.codes")
                return
            if len(code.chats) >= 500:
                logger.info(f"Max chats limit reached for code {code_name}")
                return
            if chat_id not in code.chats:
                logger.info(f"Adding chat {chat_id} to code {code_name}")
                code.chats.add(chat_id)
                await self.save_config()
                logger.info(f"Successfully added chat {chat_id} to code {code_name}")
            else:
                logger.info(f"Chat {chat_id} already in code {code_name}")
        except Exception as e:
            logger.error(f"Error in watcher: {e}", exc_info=True)

    async def on_unload(self):
        """Cleanup on module unload."""
        self._active = False

        for task_name in ["_cleanup_task", "_periodic_task"]:
            task = getattr(self, task_name, None)
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
        for task in [t for t in self.manager.broadcast_tasks.values() if t and not t.done()]:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    async def brcmd(self, message):
        """Команда для управления рассылкой. Используйте .help Broadcast для справки."""
        if not message.sender_id in self.manager._authorized_users:
            await message.edit("❌ У вас нет доступа к этой команде")
            return
        await self.manager.handle_command(message)
    
    async def debug_broadcast(self, code_name: str):
        """Debug function to check broadcast issues"""
        code = self.manager.codes.get(code_name)
        if not code:
            return f"❌ Code {code_name} not found"
        debug_info = []

        debug_info.append("📊 Basic Configuration:")
        debug_info.append(f"- Active status: {code._active}")
        debug_info.append(f"- Number of chats: {len(code.chats)}")
        debug_info.append(f"- Number of messages: {len(code.messages)}")
        debug_info.append(f"- Interval: {code.interval}")
        debug_info.append(f"- Send mode: {code.send_mode}")
        debug_info.append(f"- Batch mode: {code.batch_mode}")

        # Check message data

        debug_info.append("\n📝 Message Check:")
        for idx, msg in enumerate(code.messages):
            try:
                message = await self._fetch_messages(msg)
                status = "✅" if message else "❌"
                debug_info.append(
                    f"- Message {idx + 1}: {status} (ID: {msg['message_id']})"
                )
            except Exception as e:
                debug_info.append(f"- Message {idx + 1}: ❌ Error: {str(e)}")
        # Check chat permissions

        debug_info.append("\n👥 Chat Permissions:")
        for chat_id in code.chats:
            try:
                permissions = await self._client.get_permissions(chat_id, self.me_id)
                can_send = "✅" if permissions.send_messages else "❌"
                debug_info.append(f"- Chat {chat_id}: {can_send}")
            except Exception as e:
                debug_info.append(f"- Chat {chat_id}: ❌ Error: {str(e)}")
        # Check rate limits

        debug_info.append("\n⏱️ Rate Limits:")
        minute_stats = await self.manager.minute_limiter.get_stats()
        hour_stats = await self.manager.hour_limiter.get_stats()
        debug_info.append(f"- Minute usage: {minute_stats['usage_percent']}%")
        debug_info.append(f"- Hour usage: {hour_stats['usage_percent']}%")

        return "\n".join(debug_info)

    async def debugcmd(self, message):
        """Debug command for broadcast issues"""
        args = message.text.split()
        if len(args) < 2:
            await message.edit("❌ Please specify the broadcast code to debug")
            return
        code_name = args[1]
        debug_result = await self.manager.debug_broadcast(code_name)
        await message.edit(debug_result)



@dataclass
class Broadcast:
    """Основной класс для управления рассылкой"""

    chats: Set[int] = field(default_factory=set)
    messages: List[dict] = field(default_factory=list)
    interval: Tuple[int, int] = (10, 13)
    send_mode: str = "auto"
    batch_mode: bool = False
    _last_message_index: int = field(default=0, init=False)
    _active: bool = field(default=False, init=False)

    def add_message(
        self, chat_id: int, message_id: int, grouped_ids: List[int] = None
    ) -> bool:
        """Добавляет сообщение с проверкой дубликатов"""
        message_data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "grouped_ids": grouped_ids or [],
        }

        for existing in self.messages:
            if existing["chat_id"] == chat_id and existing["message_id"] == message_id:
                return False
        self.messages.append(message_data)
        return True

    def remove_message(self, message_id: int, chat_id: int) -> bool:
        """Удаляет сообщение из списка"""
        initial_length = len(self.messages)
        self.messages = [
            m
            for m in self.messages
            if not (m["message_id"] == message_id and m["chat_id"] == chat_id)
        ]
        return len(self.messages) < initial_length

    def get_next_message_index(self) -> int:
        """Возвращает индекс следующего сообщения для отправки"""
        if not self.messages:
            return 0
        self._last_message_index = (self._last_message_index + 1) % len(self.messages)
        return self._last_message_index

    def is_valid_interval(self) -> bool:
        """Проверяет корректность интервала"""
        min_val, max_val = self.interval
        return (
            isinstance(min_val, int)
            and isinstance(max_val, int)
            and 0 < min_val < max_val <= 1440
        )

    def to_dict(self) -> dict:
        """Сериализует объект в словарь"""
        return {
            "chats": list(self.chats),
            "messages": self.messages,
            "interval": list(self.interval),
            "send_mode": self.send_mode,
            "batch_mode": self.batch_mode,
            "active": self._active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Broadcast":
        """Создает объект из словаря"""
        instance = cls(
            chats=set(data.get("chats", [])),
            messages=data.get("messages", []),
            interval=tuple(data.get("interval", (10, 13))),
            send_mode=data.get("send_mode", "auto"),
            batch_mode=data.get("batch_mode", False),
        )
        instance._active = data.get("active", False)
        return instance


class BroadcastManager:
    """Manages broadcast operations and state."""

    BATCH_SIZE_SMALL = 5
    BATCH_SIZE_MEDIUM = 8
    BATCH_SIZE_LARGE = 10
    BATCH_SIZE_XLARGE = 15

    MAX_MESSAGES_PER_CODE = 100
    MAX_MESSAGES_PER_MINUTE = 20
    MAX_MESSAGES_PER_HOUR = 300
    MAX_CODES = 50
    MAX_RETRY_COUNT = 3
    MAX_FLOOD_WAIT_COUNT = 3
    MAX_CONSECUTIVE_ERRORS = 5
    MAX_MEDIA_SIZE = 10 * 1024 * 1024

    BATCH_THRESHOLD_SMALL = 20
    BATCH_THRESHOLD_MEDIUM = 50
    BATCH_THRESHOLD_LARGE = 100

    RETRY_DELAY_LONG = 300
    RETRY_DELAY_SHORT = 60
    RETRY_DELAY_MINI = 3
    EXPONENTIAL_DELAY_BASE = 10
    NOTIFY_DELAY = 1

    NOTIFY_GROUP_SIZE = 30
    OFFSET_MULTIPLIER = 2
    INTERVAL_PADDING = 1

    def __init__(self, client, db):
        self.client = client
        self.db = db
        self.codes: Dict[str, Broadcast] = {}
        self.broadcast_tasks: Dict[str, asyncio.Task] = {}
        self.last_broadcast_time: Dict[str, float] = {}
        self._message_cache = SimpleCache(ttl=7200, max_size=50)
        self._active = True
        self._lock = asyncio.Lock()
        self._cleanup_task = None
        self._periodic_task = None
        self._authorized_users = self._load_authorized_users()
        self.watcher_enabled = False

        self.minute_limiter = RateLimiter(self.MAX_MESSAGES_PER_MINUTE, 60)
        self.hour_limiter = RateLimiter(self.MAX_MESSAGES_PER_HOUR, 3600)

        self.error_counts = {}
        self.last_error_time = {}

    @staticmethod
    def _get_message_content(msg: Message) -> Union[str, Message]:
        """Получает контент сообщения для отправки."""
        return msg.text if msg.text else msg

    def _load_authorized_users(self) -> Set[int]:
        """Загружает список авторизованных пользователей из JSON файла"""
        try:
            with open("/root/Heroku/loll.json", "r") as f:
                data = json.load(f)
                return set(int(uid) for uid in data.get("authorized_users", []))
        except Exception as e:
            logger.error(f"Ошибка загрузки авторизованных пользователей: {e}")
            return {7175372340}

    async def _save_authorized_users(self):
        """Сохраняет список авторизованных пользователей в JSON файл"""
        try:
            with open("/root/Heroku/loll.json", "r") as f:
                data = json.load(f)
            data["authorized_users"] = list(self._authorized_users)
            with open("/root/Heroku/loll.json", "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Ошибка сохранения авторизованных пользователей: {e}")

    async def _load_config(self):
        """Loads configuration from database with improved state handling"""
        try:
            config = self.db.get("broadcast", "config", {})
            if not config:
                return
            for code_name, code_data in config.get("codes", {}).items():
                self.codes[code_name] = Broadcast.from_dict(code_data)
                # Restore active broadcasts

                if self.codes[code_name]._active:
                    self.broadcast_tasks[code_name] = asyncio.create_task(
                        self._broadcast_loop(code_name)
                    )
                    logger.info(f"Restored active broadcast: {code_name}")
            saved_times = self.db.get("broadcast", "last_broadcast_times", {})
            self.last_broadcast_time.update(
                {code: float(time_) for code, time_ in saved_times.items()}
            )

            # Verify loaded states

            for code_name, code in self.codes.items():
                if code._active and code_name not in self.broadcast_tasks:
                    logger.warning(
                        f"Inconsistent state detected for {code_name}, restarting broadcast"
                    )
                    self.broadcast_tasks[code_name] = asyncio.create_task(
                        self._broadcast_loop(code_name)
                    )
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")

    async def save_config(self):
        """Saves configuration to database with improved state handling"""
        async with self._lock:
            try:
                for code_name, code in self.codes.items():
                    task = self.broadcast_tasks.get(code_name)
                    if task:
                        code._active = not task.done()
                config = {
                    "version": 1,
                    "last_save": int(time.time()),
                    "codes": {
                        name: code.to_dict() for name, code in self.codes.items()
                    },
                }

                self.db.set("broadcast", "config", config)
                self.db.set(
                    "broadcast",
                    "last_broadcast_times",
                    self.last_broadcast_time,
                )

                logger.info("Configuration saved successfully")
            except Exception as e:
                logger.error(f"Error saving configuration: {e}")

    async def handle_command(self, message: Message):
        """Обработчик команд для управления рассылкой"""
        try:
            args = message.text.split()[1:]
            if not args:
                await message.edit("❌ Укажите действие и код рассылки")
                return
            action = args[0].lower()
            code_name = args[1] if len(args) > 1 else None

            if action == "list":
                await self._handle_list_command(message)
                return
            elif action == "watcher":
                await self._handle_watcher_command(message, args)
                return
            if not code_name:
                await message.edit("❌ Укажите код рассылки")
                return
            code = self.codes.get(code_name)
            if action != "add" and not code:
                await message.edit(f"❌ Код рассылки {code_name} не найден")
                return
            command_handlers = {
                "add": self._handle_add_command,
                "delete": self._handle_delete_command,
                "remove": self._handle_remove_command,
                "addchat": self._handle_addchat_command,
                "rmchat": self._handle_rmchat_command,
                "int": self._handle_interval_command,
                "mode": self._handle_mode_command,
                "allmsgs": self._handle_allmsgs_command,
                "start": self._handle_start_command,
                "stop": self._handle_stop_command,
            }

            handler = command_handlers.get(action)
            if handler:
                await handler(message, code, code_name, args)
            else:
                await message.edit("❌ Неизвестное действие")
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            await message.edit(f"❌ Произошла ошибка: {str(e)}")

    async def _handle_list_command(self, message: Message):
        """Обработчик команды list"""
        if not self.codes:
            await message.edit("❌ Нет активных рассылок")
            return
        response = "📝 Список рассылок:\n\n"
        current_time = time.time()

        for name, code in self.codes.items():
            is_running = (
                name in self.broadcast_tasks and not self.broadcast_tasks[name].done()
            )
            status = "✅ Активна" if code._active and is_running else "❌ Не запущена"
            last_time = self.last_broadcast_time.get(name, 0)

            last_active = ""
            if last_time and current_time > last_time:
                minutes_ago = int((current_time - last_time) / 60)
                last_active = f"(последняя активность: {'менее минуты' if minutes_ago == 0 else f'{minutes_ago} мин'} назад)"
            response += (
                f"• {name}: {status} {last_active}\n"
                f"  ├ Чатов: {len(code.chats)} (активных)\n"
                f"  ├ Сообщений: {len(code.messages)}\n"
                f"  ├ Интервал: {code.interval[0]}-{code.interval[1]} мин\n"
                f"  ├ Режим: {code.send_mode}\n"
                f"  └ Все сообщения: {'да' if code.batch_mode else 'нет'}\n\n"
            )
        await message.edit(response)

    async def _handle_watcher_command(self, message: Message, args: list):
        """Обработчик команды watcher"""
        if len(args) < 2:
            status = "включен" if self.watcher_enabled else "выключен"
            await message.edit(
                "ℹ️ Автодобавление чатов\n"
                f"Текущий статус: {status}\n\n"
                "Использование: .br watcher <on/off>"
            )
            return
        mode = args[1].lower()
        if mode not in ["on", "off"]:
            await message.edit("❌ Укажите on или off")
            return
        self.watcher_enabled = mode == "on"
        await message.edit(
            f"✅ Автодобавление чатов {'включено' if self.watcher_enabled else 'выключено'}"
        )

    async def _handle_add_command(
        self, message: Message, code: Optional[Broadcast], code_name: str, args: list
    ):
        """Обработчик команды add"""
        reply = await message.get_reply_message()
        if not reply:
            await message.edit(
                "❌ Ответьте на сообщение, которое нужно добавить в рассылку"
            )
            return
        is_new = code is None
        if is_new:
            code = Broadcast()
            self.codes[code_name] = code
        if len(code.messages) >= self.MAX_MESSAGES_PER_CODE:
            await message.edit(
                f"❌ Достигнут лимит сообщений ({self.MAX_MESSAGES_PER_CODE})"
            )
            return
        grouped_id = getattr(reply, "grouped_id", None)
        grouped_ids = []

        if grouped_id:
            album_messages = []
            async for album_msg in message.client.iter_messages(
                reply.chat_id,
                min_id=max(0, reply.id - 10),
                max_id=reply.id + 10,
                limit=30,
            ):
                if getattr(album_msg, "grouped_id", None) == grouped_id:
                    album_messages.append(album_msg)
            album_messages.sort(key=lambda m: m.id)
            grouped_ids = list(dict.fromkeys(msg.id for msg in album_messages))
        if code.add_message(reply.chat_id, reply.id, grouped_ids):
            await self.save_config()
            await message.edit(
                f"✅ {'Рассылка создана и с' if is_new else 'С'}ообщение добавлено"
            )
        else:
            await message.edit("❌ Это сообщение уже есть в рассылке")

    async def _handle_delete_command(
        self, message: Message, code: Broadcast, code_name: str, args: list
    ):
        """Обработчик команды delete"""
        if (
            code_name in self.broadcast_tasks
            and not self.broadcast_tasks[code_name].done()
        ):
            self.broadcast_tasks[code_name].cancel()
        del self.codes[code_name]
        await self.save_config()
        await message.edit(f"✅ Рассылка {code_name} удалена")

    async def _handle_remove_command(
        self, message: Message, code: Broadcast, code_name: str, args: list
    ):
        """Обработчик команды remove"""
        reply = await message.get_reply_message()
        if not reply:
            await message.edit(
                "❌ Ответьте на сообщение, которое нужно удалить из рассылки"
            )
            return
        if code.remove_message(reply.id, reply.chat_id):
            await self.save_config()
            await message.edit("✅ Сообщение удалено из рассылки")
        else:
            await message.edit("❌ Это сообщение не найдено в рассылке")

    async def _handle_addchat_command(
        self, message: Message, code: Broadcast, code_name: str, args: list
    ):
        """Обработчик команды addchat"""
        if len(args) > 2:
            chat_id = await self._get_chat_id(args[2])
            if not chat_id:
                await message.edit(
                    "❌ Не удалось получить ID чата. Проверьте ссылку/юзернейм"
                )
                return
        else:
            chat_id = message.chat_id
        if len(code.chats) >= 500:
            await message.edit(f"❌ Достигнут лимит чатов 500")
            return
        if chat_id in code.chats:
            await message.edit("❌ Этот чат уже добавлен в рассылку")
            return
        code.chats.add(chat_id)
        await self.save_config()
        await message.edit("✅ Чат добавлен в рассылку")

    async def _handle_rmchat_command(
        self, message: Message, code: Broadcast, code_name: str, args: list
    ):
        """Обработчик команды rmchat"""
        if len(args) > 2:
            chat_id = await self._get_chat_id(args[2])
            if not chat_id:
                await message.edit(
                    "❌ Не удалось получить ID чата. Проверьте ссылку/юзернейм"
                )
                return
        else:
            chat_id = message.chat_id
        if chat_id not in code.chats:
            await message.edit("❌ Этот чат не найден в рассылке")
            return
        code.chats.remove(chat_id)
        await self.save_config()
        await message.edit("✅ Чат удален из рассылки")

    async def _handle_interval_command(
        self, message: Message, code: Broadcast, code_name: str, args: list
    ):
        """Обработчик команды int"""
        if len(args) < 4:
            await message.edit(
                "❌ Укажите минимальный и максимальный интервал в минутах"
            )
            return
        try:
            min_val = int(args[2])
            max_val = int(args[3])
        except ValueError:
            await message.edit("❌ Интервалы должны быть числами")
            return
        code.interval = (min_val, max_val)
        if not code.is_valid_interval():
            await message.edit("❌ Некорректный интервал (0 < min < max <= 1440)")
            return
        await self.save_config()
        await message.edit(f"✅ Установлен интервал {min_val}-{max_val} минут")

    async def _handle_mode_command(
        self, message: Message, code: Broadcast, code_name: str, args: list
    ):
        """Обработчик команды mode"""
        if len(args) < 3:
            await message.edit("❌ Укажите режим отправки (auto/normal/forward)")
            return
        mode = args[2].lower()
        if mode not in ["auto", "normal", "forward"]:
            await message.edit(
                "❌ Неверный режим. Доступные режимы: auto, normal, forward"
            )
            return
        code.send_mode = mode
        await self.save_config()
        await message.edit(f"✅ Установлен режим отправки: {mode}")

    async def _handle_allmsgs_command(
        self, message: Message, code: Broadcast, code_name: str, args: list
    ):
        """Обработчик команды allmsgs"""
        if len(args) < 3:
            await message.edit("❌ Укажите on или off")
            return
        mode = args[2].lower()
        if mode not in ["on", "off"]:
            await message.edit("❌ Укажите on или off")
            return
        code.batch_mode = mode == "on"
        await self.save_config()
        await message.edit(
            f"✅ Отправка всех сообщений {'включена' if code.batch_mode else 'выключена'}"
        )

    async def _handle_start_command(
        self, message: Message, code: Broadcast, code_name: str, args: list
    ):
        """Обработчик команды start"""
        if not code.messages:
            await message.edit("❌ Добавьте хотя бы одно сообщение в рассылку")
            return
        if not code.chats:
            await message.edit("❌ Добавьте хотя бы один чат в рассылку")
            return
        if (
            code_name in self.broadcast_tasks
            and self.broadcast_tasks[code_name]
            and not self.broadcast_tasks[code_name].done()
        ):
            self.broadcast_tasks[code_name].cancel()
            try:
                await self.broadcast_tasks[code_name]
            except asyncio.CancelledError:
                pass
        code._active = True
        self.broadcast_tasks[code_name] = asyncio.create_task(
            self._broadcast_loop(code_name)
        )
        await message.edit(f"✅ Рассылка {code_name} запущена")

    async def _handle_stop_command(
        self, message: Message, code: Broadcast, code_name: str, args: list
    ):
        """Обработчик команды stop"""
        code._active = False
        if (
            code_name in self.broadcast_tasks
            and not self.broadcast_tasks[code_name].done()
        ):
            self.broadcast_tasks[code_name].cancel()
            try:
                await self.broadcast_tasks[code_name]
            except asyncio.CancelledError:
                pass
        await message.edit(f"✅ Рассылка {code_name} остановлена")

    async def _send_messages_to_chats(
        self,
        code: Optional[Broadcast],
        code_name: str,
        messages_to_send: List[Union[Message, List[Message]]],
    ) -> Set[int]:
        """Обновленный метод отправки сообщений в чаты"""
        if not code:
            return set()
        failed_chats: Set[int] = set()
        success_count: int = 0
        flood_wait_count: int = 0

        async def get_optimal_batch_size(total_chats: int) -> int:
            minute_stats = await self.minute_limiter.get_stats()
            hour_stats = await self.hour_limiter.get_stats()

            if minute_stats["usage_percent"] > 80 or hour_stats["usage_percent"] > 80:
                return max(self.BATCH_SIZE_SMALL // 2, 1)
            if total_chats <= self.BATCH_THRESHOLD_SMALL:
                return self.BATCH_SIZE_SMALL
            elif total_chats <= self.BATCH_THRESHOLD_MEDIUM:
                return self.BATCH_SIZE_MEDIUM
            return self.BATCH_SIZE_LARGE

        async def send_to_chat(
            chat_id: int,
            base_time: datetime,
            position_in_batch: int,
            current_batch_size: int,
        ):
            nonlocal success_count, flood_wait_count

            try:
                error_key = f"{chat_id}_general"
                if self.error_counts.get(error_key, 0) >= self.MAX_CONSECUTIVE_ERRORS:
                    last_error = self.last_error_time.get(error_key, 0)
                    if time.time() - last_error < self.RETRY_DELAY_LONG:
                        failed_chats.add(chat_id)
                        return
                offset_minutes = (
                    position_in_batch * self.OFFSET_MULTIPLIER
                ) // current_batch_size
                schedule_time = base_time + timedelta(minutes=offset_minutes)

                for message in messages_to_send:
                    success = await self._send_message(
                        code_name,
                        chat_id,
                        message,
                        code.send_mode,
                        schedule_time,
                    )
                    if not success:
                        raise Exception("Ошибка отправки сообщения")
                success_count += 1
            except FloodWaitError as e:
                flood_wait_count += 1
                if flood_wait_count >= self.MAX_FLOOD_WAIT_COUNT:
                    logger.error("Слишком много FloodWaitError, останавливаем рассылку")
                    code._active = False
                failed_chats.add(chat_id)
            except Exception as e:
                failed_chats.add(chat_id)
                logger.error(f"Ошибка отправки в чат {chat_id}: {str(e)}")

        chats = list(code.chats)
        random.shuffle(chats)
        total_chats = len(chats)

        batch_size = await get_optimal_batch_size(total_chats)

        for i in range(0, total_chats, batch_size):
            if not self._active or not code._active:
                break
            current_batch = chats[i : i + batch_size]
            current_time = datetime.now()

            tasks = []
            for idx, chat_id in enumerate(current_batch):
                task = send_to_chat(chat_id, current_time, idx, len(current_batch))
                tasks.append(task)
            await asyncio.gather(*tasks)

            min_interval, max_interval = code.interval
            sleep_time = random.uniform(min_interval * 60, max_interval * 60)
            await asyncio.sleep(max(3.0, sleep_time))
        return failed_chats

    async def _send_message(
        self,
        code_name: str,
        chat_id: int,
        messages_to_send: Union[Message, List[Message]],
        send_mode: str = "auto",
        schedule_time: Optional[datetime] = None,
    ) -> bool:
        try:

            async def forward_messages(messages: Union[Message, List[Message]]) -> None:
                if isinstance(messages, list):
                    await self.client.forward_messages(
                        entity=chat_id,
                        messages=messages,
                        from_peer=messages[0].chat_id,
                        schedule=schedule_time,
                    )
                else:
                    await self.client.forward_messages(
                        entity=chat_id,
                        messages=[messages],
                        from_peer=messages.chat_id,
                        schedule=schedule_time,
                    )

            await self.minute_limiter.acquire()
            await self.hour_limiter.acquire()

            await asyncio.sleep(1)

            if send_mode == "forward":
                await forward_messages(messages_to_send)
            elif send_mode == "normal":
                if isinstance(messages_to_send, list):
                    for msg in messages_to_send:
                        await self.client.send_message(
                            entity=chat_id,
                            message=self._get_message_content(msg),
                            schedule=schedule_time,
                        )
                else:
                    await self.client.send_message(
                        entity=chat_id,
                        message=self._get_message_content(messages_to_send),
                        schedule=schedule_time,
                    )
            elif send_mode == "auto":

                if isinstance(messages_to_send, list):
                    await forward_messages(messages_to_send)
                elif hasattr(messages_to_send, "media") and messages_to_send.media:
                    await forward_messages(messages_to_send)
                else:
                    await self.client.send_message(
                        entity=chat_id,
                        message=self._get_message_content(messages_to_send),
                        schedule=schedule_time,
                    )
            self.error_counts[chat_id] = 0
            return True
        except FloodWaitError as e:
            error_key = f"{chat_id}_flood"
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
            self.last_error_time[error_key] = time.time()

            wait_time = e.seconds * (2 ** self.error_counts[error_key])
            logger.warning(
                f"FloodWaitError {code_name} для чата {chat_id}: ждем {wait_time} секунд"
            )
            await asyncio.sleep(wait_time)
            raise
        except (ChatWriteForbiddenError, UserBannedInChannelError):
            raise
        except Exception as e:
            error_key = f"{chat_id}_general"
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
            self.last_error_time[error_key] = time.time()

            if self.error_counts[error_key] >= self.MAX_CONSECUTIVE_ERRORS:
                wait_time = self.RETRY_DELAY_SHORT * (
                    2 ** (self.error_counts[error_key] - self.MAX_CONSECUTIVE_ERRORS)
                )
                logger.warning(
                    f"Превышен лимит ошибок для {code_name}  чата {chat_id}, ждем {wait_time} секунд"
                )
                await asyncio.sleep(wait_time)
            raise

    async def _handle_failed_chats(
        self, code_name: str, failed_chats: Set[int]
    ) -> None:
        """Обрабатывает чаты, в которые не удалось отправить сообщения."""
        if not failed_chats:
            return
        try:
            async with self._lock:
                code = self.codes.get(code_name)
                if not code:
                    logger.error(
                        f"Код рассылки {code_name} не найден при обработке ошибок"
                    )
                    return
                code.chats -= failed_chats
                await self.save_config()

                chat_groups = [
                    ", ".join(
                        str(chat_id)
                        for chat_id in tuple(failed_chats)[
                            i : i + self.NOTIFY_GROUP_SIZE
                        ]
                    )
                    for i in range(0, len(failed_chats), self.NOTIFY_GROUP_SIZE)
                ]

                me = await self.client.get_me()
                base_message = (
                    f"⚠️ Рассылка '{code_name}':\n"
                    f"Не удалось отправить сообщения в {len(failed_chats)} чат(ов).\n"
                    f"Чаты удалены из рассылки.\n\n"
                    f"ID чатов:\n"
                )

                for group in chat_groups:
                    try:
                        await self.client.send_message(
                            me.id,
                            base_message + group,
                            schedule=datetime.now()
                            + timedelta(seconds=self.RETRY_DELAY_SHORT),
                        )
                        await asyncio.sleep(self.NOTIFY_DELAY)
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления: {e}")
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
            logger.error(f"FloodWaitError: {e}")
        except Exception as e:
            logger.error(f"Ошибка обработки неудачных чатов для {code_name}: {e}")

    @staticmethod
    def _chunk_messages(
        messages: List[Union[Message, List[Message]]], batch_size: int = 8
    ) -> List[List[Union[Message, List[Message]]]]:
        """Разбивает список сообщений на части оптимального размера."""
        if not messages:
            return []
        return [
            messages[i : i + batch_size] for i in range(0, len(messages), batch_size)
        ]

    async def _process_message_batch(
        self, code: Optional[Broadcast], messages: List[dict]
    ) -> Tuple[List[Union[Message, List[Message]]], List[dict]]:
        """Обрабатывает пакет сообщений с оптимизированной загрузкой."""
        if not code:
            logger.error("Получен пустой объект рассылки при обработке сообщений")
            return [], messages
        messages_to_send = []
        deleted_messages = []

        results = await asyncio.gather(
            *[self._fetch_messages(msg) for msg in messages],
            return_exceptions=True,
        )

        for msg_data, result in zip(messages, results):
            if isinstance(result, Exception):
                logger.error(
                    f"Ошибка загрузки сообщения {msg_data['message_id']}: {result}"
                )
                deleted_messages.append(msg_data)
            elif result:
                if isinstance(result, list):
                    valid = all(self._check_media_size(msg) for msg in result)
                else:
                    valid = self._check_media_size(result)
                if valid:
                    messages_to_send.append(result)
                else:
                    deleted_messages.append(msg_data)
            else:
                deleted_messages.append(msg_data)
        return messages_to_send, deleted_messages

    @staticmethod
    def _check_media_size(message: Optional[Message]) -> bool:
        """Проверяет размер медиафайла."""
        if not message:
            return False
        if hasattr(message, "media") and message.media:
            if hasattr(message.media, "document") and hasattr(
                message.media.document, "size"
            ):
                return message.media.document.size <= 10 * 1024 * 1024
        return True

    def _should_continue(self, code: Optional[Broadcast], code_name: str) -> bool:
        """Проверяет, нужно ли продолжать рассылку."""
        if not self._active or not code or not code._active:
            return False
        if not code.chats or not code.messages:
            return False
        return True

    async def _broadcast_loop(self, code_name: str):
        """Main broadcast loop."""
        while self._active:
            retry_count = 0
            deleted_messages = []
            messages_to_send = []

            try:
                code = self.codes.get(code_name)
                if not self._should_continue(code, code_name):
                    await asyncio.sleep(self.RETRY_DELAY_SHORT)
                    continue
                current_messages = code.messages.copy()

                batches = self._chunk_messages(
                    current_messages, batch_size=self.BATCH_SIZE_LARGE
                )

                for batch in batches:
                    if not self._should_continue(code, code_name):
                        break
                    batch_messages, deleted = await self._process_message_batch(
                        code, batch
                    )
                    messages_to_send.extend(batch_messages)
                    deleted_messages.extend(deleted)
                if deleted_messages:
                    async with self._lock:
                        code.messages = [
                            m for m in code.messages if m not in deleted_messages
                        ]
                        await self.save_config()
                if not self._should_continue(code, code_name) or not messages_to_send:
                    retry_count += 1
                    if retry_count >= self.MAX_RETRY_COUNT:
                        logger.error(
                            f"Достигнут лимит попыток получения сообщений для {code_name}"
                        )
                        await asyncio.sleep(self.RETRY_DELAY_LONG)
                        retry_count = 0
                    else:
                        await asyncio.sleep(self.RETRY_DELAY_SHORT)
                    continue
                retry_count = 0

                if not code.batch_mode:
                    async with self._lock:
                        next_index = code.get_next_message_index()

                        messages_to_send = [
                            messages_to_send[next_index % len(messages_to_send)]
                        ]
                failed_chats = await self._send_messages_to_chats(
                    code, code_name, messages_to_send
                )

                if failed_chats:
                    await self._handle_failed_chats(code_name, failed_chats)
                current_time = time.time()
                self.last_broadcast_time[code_name] = current_time

                try:
                    async with self._lock:
                        saved_times = self.db.get(
                            "broadcast", "last_broadcast_times", {}
                        )
                        saved_times[code_name] = current_time
                        self.db.set("broadcast", "last_broadcast_times", saved_times)
                except Exception as e:
                    logger.error(f"Ошибка сохранения времени рассылки: {e}")
            except asyncio.CancelledError:
                logger.info(f"Рассылка {code_name} остановлена")
                break
            except Exception as e:
                logger.error(f"Критическая ошибка в цикле рассылки {code_name}: {e}")
                retry_count += 1
                if retry_count >= self.MAX_RETRY_COUNT:
                    logger.error(
                        f"Достигнут лимит попыток выполнения рассылки {code_name}"
                    )
                    await asyncio.sleep(self.RETRY_DELAY_LONG)
                    retry_count = 0
                else:
                    await asyncio.sleep(self.RETRY_DELAY_SHORT)

    async def _fetch_messages(
        self, msg_data: dict
    ) -> Optional[Union[Message, List[Message]]]:
        """Получает сообщения с улучшенной обработкой ошибок"""
        key = (msg_data["chat_id"], msg_data["message_id"])

        try:
            cached = await self._message_cache.get(key)
            if cached:
                return cached
            # Попытка получить сообщение напрямую

            message = await self.client.get_messages(
                msg_data["chat_id"], ids=msg_data["message_id"]
            )

            if message:
                # Проверяем, есть ли grouped_ids

                if msg_data.get("grouped_ids"):
                    messages = []
                    for msg_id in msg_data["grouped_ids"]:
                        grouped_msg = await self.client.get_messages(
                            msg_data["chat_id"], ids=msg_id
                        )
                        if grouped_msg:
                            messages.append(grouped_msg)
                    if messages:
                        await self._message_cache.set(key, messages)
                        return messages[0] if len(messages) == 1 else messages
                else:
                    await self._message_cache.set(key, message)
                    return message
            logger.warning(
                f"Сообщение {msg_data['message_id']} существует, но не удалось получить из чата {msg_data['chat_id']}"
            )
            return None
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Сетевая ошибка при получении сообщений: {e}")
            return None
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при получении сообщений: {e}")
            return None

    async def _get_chat_id(self, chat_identifier: str) -> Optional[int]:
        """Получает ID чата из разных форматов (ссылка, юзернейм, ID)"""
        try:
            if chat_identifier.lstrip("-").isdigit():
                return int(chat_identifier)
            clean_username = chat_identifier.lower()
            for prefix in ["https://", "http://", "t.me/", "@", "telegram.me/"]:
                clean_username = clean_username.replace(prefix, "")
            entity = await self.client.get_entity(clean_username)
            return entity.id
        except Exception as e:
            logger.error(f"Ошибка получения chat_id: {e}")
            return None
