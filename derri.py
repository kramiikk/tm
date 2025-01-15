import asyncio
import json
import logging
import random
import time
from collections import OrderedDict
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


@loader.tds
class BroadcastMod(loader.Module):
    """Модуль для массовой рассылки."""

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
            code_name = parts[0][1:]
            if not code_name:
                return
            chat_id = message.chat_id
            code = self.manager.codes.get(code_name)
            if not code:
                return
            if len(code.chats) >= 500:
                logger.info(f"Max chats limit reached for code {code_name}")
                return
            if chat_id not in code.chats:
                code.chats.add(chat_id)
                await self.manager.save_config()
            else:
                logger.info(f"Chat {chat_id} already in code {code_name}")
        except Exception as e:
            logger.error(f"Error in watcher: {e}", exc_info=True)

    async def on_unload(self):
        """Cleanup on module unload."""
        self._active = False

        async def cancel_task(task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        tasks = [t for t in self.manager.broadcast_tasks.values() if t]
        await asyncio.gather(*map(cancel_task, tasks), return_exceptions=True)

    async def brcmd(self, message):
        """Команда для управления рассылкой."""
        if not message.sender_id in self.manager._authorized_users:
            await message.edit("❌ У вас нет доступа к этой команде")
            return
        await self.manager.handle_command(message)


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
    MAX_MESSAGES_PER_HOUR = 250
    MAX_CODES = 50

    MAX_FLOOD_WAIT_COUNT = 3
    MAX_CONSECUTIVE_ERRORS = 7

    BATCH_THRESHOLD_SMALL = 20
    BATCH_THRESHOLD_MEDIUM = 50
    BATCH_THRESHOLD_LARGE = 100

    EXPONENTIAL_DELAY_BASE = 10
    NOTIFY_DELAY = 1

    NOTIFY_GROUP_SIZE = 30

    def __init__(self, client, db):
        self.client = client
        self.db = db
        self.codes: Dict[str, Broadcast] = {}
        self.broadcast_tasks: Dict[str, asyncio.Task] = {}
        self.last_broadcast_time: Dict[str, float] = {}
        self._message_cache = SimpleCache(ttl=7200, max_size=50)
        self._active = True
        self._lock = asyncio.Lock()
        self._authorized_users = self._load_authorized_users()
        self.watcher_enabled = False
        self._semaphore = asyncio.Semaphore(10)

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

    async def _load_config(self):
        """Loads configuration from database with improved state handling"""
        try:
            config = self.db.get("broadcast", "config", {})
            if not config:
                return
            for code_name, code_data in config.get("codes", {}).items():
                try:
                    broadcast = Broadcast.from_dict(code_data)
                    self.codes[code_name] = broadcast
                    broadcast._active = False
                except Exception as e:
                    logger.error(f"Error loading broadcast {code_name}: {e}")
                    continue
            active_broadcasts = config.get("active_broadcasts", [])
            for code_name in active_broadcasts:
                try:
                    if code_name not in self.codes:
                        continue
                    code = self.codes[code_name]

                    if not code.messages or not code.chats:
                        continue
                    code._active = True
                    self.broadcast_tasks[code_name] = asyncio.create_task(
                        self._broadcast_loop(code_name)
                    )
                except Exception as e:
                    logger.error(f"Error restoring broadcast {code_name}: {e}")
                    continue
            saved_times = self.db.get("broadcast", "last_broadcast_times", {})
            self.last_broadcast_time.update(
                {code: float(time_) for code, time_ in saved_times.items()}
            )
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")

    async def save_config(self):
        """Saves configuration to database with improved state handling"""
        async with self._lock:
            try:
                for code_name, code in self.codes.items():
                    task = self.broadcast_tasks.get(code_name)
                    code._active = bool(task and not task.done())
                config = {
                    "version": 1,
                    "last_save": int(time.time()),
                    "codes": {
                        name: code.to_dict() for name, code in self.codes.items()
                    },
                    "active_broadcasts": [
                        name for name, code in self.codes.items() if code._active
                    ],
                }

                self.db.set("broadcast", "config", config)
                self.db.set(
                    "broadcast",
                    "last_broadcast_times",
                    self.last_broadcast_time,
                )
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
                "add": lambda: self._handle_add_command(message, code, code_name),
                "delete": lambda: self._handle_delete_command(message, code_name),
                "remove": lambda: self._handle_remove_command(message, code),
                "addchat": lambda: self._handle_addchat_command(message, code, args),
                "rmchat": lambda: self._handle_rmchat_command(message, code, args),
                "int": lambda: self._handle_interval_command(message, code, args),
                "mode": lambda: self._handle_mode_command(message, code, args),
                "allmsgs": lambda: self._handle_allmsgs_command(message, code, args),
                "start": lambda: self._handle_start_command(message, code, code_name),
                "stop": lambda: self._handle_stop_command(message, code, code_name),
            }

            handler = command_handlers.get(action)
            if handler:
                await handler()
            else:
                await message.edit("❌ Неизвестное действие")
        except Exception as e:
            logger.error(f"Error handling command: {e}")

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
        self, message: Message, code: Optional[Broadcast], code_name: str
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

    async def _handle_delete_command(self, message: Message, code_name: str):
        """Обработчик команды delete"""
        task = self.broadcast_tasks.get(code_name)
        if task and not task.done():
            self.broadcast_tasks[code_name].cancel()
        del self.codes[code_name]
        await self.save_config()
        await message.edit(f"✅ Рассылка {code_name} удалена")

    async def _handle_remove_command(self, message: Message, code: Broadcast):
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
        self, message: Message, code: Broadcast, args: list
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
        self, message: Message, code: Broadcast, args: list
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
        self, message: Message, code: Broadcast, args: list
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

    async def _handle_mode_command(self, message: Message, code: Broadcast, args: list):
        """Обработчик команды mode"""
        if len(args) < 3:
            await message.edit("❌ Укажите режим отправки (auto/forward)")
            return
        mode = args[2].lower()
        if mode not in ["auto", "forward"]:
            await message.edit("❌ Неверный режим.")
            return
        code.send_mode = mode
        await self.save_config()
        await message.edit(f"✅ Установлен режим отправки: {mode}")

    async def _handle_allmsgs_command(
        self, message: Message, code: Broadcast, args: list
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
        self, message: Message, code: Broadcast, code_name: str
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
        await self.save_config()
        await message.edit(f"✅ Рассылка {code_name} запущена")

    async def _handle_stop_command(
        self, message: Message, code: Broadcast, code_name: str
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
        await self.save_config()
        await message.edit(f"✅ Рассылка {code_name} остановлена")

    async def _get_chat_permissions(self, chat_id: int) -> bool:
        """Проверяет, может ли бот отправлять сообщения в чат"""
        try:
            me = await self.client.get_me()
            permissions = await self.client.get_permissions(chat_id, me.id)

            if hasattr(permissions, "post_messages"):
                return bool(permissions.post_messages)
            if hasattr(permissions, "chat") and hasattr(
                permissions.chat, "send_messages"
            ):
                return bool(permissions.chat.send_messages)
            if hasattr(permissions, "permissions") and hasattr(
                permissions.permissions, "send_messages"
            ):
                return bool(permissions.permissions.send_messages)
            if hasattr(permissions, "send_messages"):
                return bool(permissions.send_messages)
            return True
        except Exception as e:
            logger.error(f"Ошибка при проверке разрешений для чата {chat_id}: {str(e)}")
            return False

    async def _send_messages_to_chats(
        self,
        code: Optional[Broadcast],
        code_name: str,
        messages_to_send: List[Union[Message, List[Message]]],
    ) -> Set[int]:
        """Обновленный метод отправки сообщений в чаты"""
        async with self._semaphore:
            """Обновленный метод отправки сообщений в чаты с расширенным логгированием"""
            async with self._semaphore:
                logger.info(
                    f"[{code_name}][send_messages] Starting message distribution"
                )
                if not code:
                    logger.error(
                        f"[{code_name}][send_messages] No broadcast code provided"
                    )
                    return set()
            failed_chats: Set[int] = set()
            success_count: int = 0
            flood_wait_count: int = 0

            async def get_optimal_batch_size(total_chats: int) -> int:
                minute_stats = await self.minute_limiter.get_stats()
                hour_stats = await self.hour_limiter.get_stats()

                if (
                    minute_stats["usage_percent"] > 80
                    or hour_stats["usage_percent"] > 80
                ):
                    return max(self.BATCH_SIZE_SMALL // 2, 1)
                if total_chats <= self.BATCH_THRESHOLD_SMALL:
                    return self.BATCH_SIZE_SMALL
                elif total_chats <= self.BATCH_THRESHOLD_MEDIUM:
                    return self.BATCH_SIZE_MEDIUM
                return self.BATCH_SIZE_LARGE

            async def send_to_chat(chat_id: int):
                nonlocal success_count, flood_wait_count

                try:
                    logger.info(
                        f"[{code_name}][send_messages] Attempting send to chat {chat_id}"
                    )
                    error_key = f"{chat_id}_general"

                    if (
                        self.error_counts.get(error_key, 0)
                        >= self.MAX_CONSECUTIVE_ERRORS
                    ):
                        last_error = self.last_error_time.get(error_key, 0)
                        if time.time() - last_error < 300:
                            logger.warning(
                                f"[{code_name}][send_messages] Chat {chat_id} in error cooldown"
                            )
                            failed_chats.add(chat_id)
                            return
                    if not await self._get_chat_permissions(chat_id):
                        logger.warning(
                            f"[{code_name}][send_messages] No permissions for chat {chat_id}"
                        )
                        failed_chats.add(chat_id)
                        return
                    for message in messages_to_send:
                        success = await self._send_message(
                            code_name, chat_id, message, code.send_mode
                        )
                        if not success:
                            raise Exception(
                                f"[{code_name}][send_messages] Failed to send message to {chat_id}"
                            )
                    success_count += 1
                    logger.info(
                        f"[{code_name}][send_messages] Successfully sent to chat {chat_id}"
                    )
                except FloodWaitError as e:
                    flood_wait_count += 1
                    logger.warning(
                        f"[{code_name}][send_messages] FloodWaitError in chat {chat_id}: {e}"
                    )
                    if flood_wait_count >= self.MAX_FLOOD_WAIT_COUNT:
                        logger.error(
                            f"[{code_name}][send_messages] Max flood wait exceeded"
                        )
                        code._active = False
                    failed_chats.add(chat_id)
                except Exception as e:
                    failed_chats.add(chat_id)
                    logger.error(
                        f"[{code_name}][send_messages] Error in chat {chat_id}: {str(e)}"
                    )

            chats = list(code.chats)
            random.shuffle(chats)
            total_chats = len(chats)

            batch_size = await get_optimal_batch_size(total_chats)

            for i in range(0, total_chats, batch_size):
                if not self._active or not code._active:
                    break
                current_batch = chats[i : i + batch_size]

                tasks = []
                for chat_id in current_batch:
                    task = send_to_chat(chat_id)
                    tasks.append(task)
                await asyncio.gather(*tasks)

                min_interval, max_interval = code.interval
                sleep_time = random.uniform(min_interval * 60, max_interval * 60)
                await asyncio.sleep(max(60, sleep_time))
            return failed_chats

    async def _send_message(
        self,
        code_name: str,
        chat_id: int,
        messages_to_send: Union[Message, List[Message]],
        send_mode: str = "auto",
    ) -> bool:
        try:
            logger.info(f"[{code_name}][send_message] Starting send to {chat_id}")

            async def forward_messages(messages: Union[Message, List[Message]]) -> None:
                logger.info(f"[{code_name}][forward] Forwarding to {chat_id}")
                if isinstance(messages, list):
                    await self.client.forward_messages(
                        entity=chat_id,
                        messages=messages,
                        from_peer=messages[0].chat_id,
                    )
                else:
                    await self.client.forward_messages(
                        entity=chat_id,
                        messages=[messages],
                        from_peer=messages.chat_id,
                    )
                logger.info(
                    f"[{code_name}][forward] Successfully forwarded to {chat_id}"
                )

            await self.minute_limiter.acquire()
            await self.hour_limiter.acquire()

            await asyncio.sleep(1)

            is_auto_mode = send_mode == "auto"
            is_forwardable = isinstance(messages_to_send, list) or (
                hasattr(messages_to_send, "media") and messages_to_send.media
            )
            logger.info(
                f"[{code_name}][send_message] Mode: {'forward' if not is_auto_mode or is_forwardable else 'auto'}"
            )
            if not is_auto_mode or is_forwardable:
                await forward_messages(messages_to_send)
            else:
                await self.client.send_message(
                    entity=chat_id,
                    message=self._get_message_content(messages_to_send),
                )
            logger.info(f"[{code_name}][send_message] Successfully sent to {chat_id}")
            self.error_counts[chat_id] = 0
            self.error_counts[f"{chat_id}_general"] = 0
            self.last_error_time[f"{chat_id}_general"] = 0
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
            logger.error(
                f"[{code_name}][send_message] Error sending to {chat_id}: {str(e)}"
            )
            error_key = f"{chat_id}_general"
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
            self.last_error_time[error_key] = time.time()

            if self.error_counts[error_key] >= self.MAX_CONSECUTIVE_ERRORS:
                wait_time = 60 * (
                    2 ** (self.error_counts[error_key] - self.MAX_CONSECUTIVE_ERRORS)
                )
                logger.warning(
                    f"Превышен лимит ошибок для {code_name}  чата {chat_id}, ждем {wait_time} секунд"
                )
                await asyncio.sleep(wait_time)
            logger.error(
                f"""
            Ошибка при отправке в чат {chat_id}:
            - Тип ошибки: {type(e).__name__}
            - Текст ошибки: {str(e)}
            - Текущие счетчики ошибок: {self.error_counts}
            """
            )
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
                    await self.client.send_message(
                        me.id,
                        base_message + group,
                        schedule=datetime.now() + timedelta(seconds=60),
                    )
                    await asyncio.sleep(self.NOTIFY_DELAY)
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
        logger.info(
            f"[batch] Processed batch: {len(messages_to_send)} valid, {len(deleted_messages)} deleted"
        )
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

    async def _broadcast_loop(self, code_name: str):
        """Main broadcast loop with enhanced debug logging"""
        while self._active:
            logger.info(f"[{code_name}] Starting broadcast cycle")
            deleted_messages = []
            messages_to_send = []

            try:
                code = self.codes.get(code_name)
                if not code or not code._active:
                    logger.warning(f"[{code_name}] Code inactive or not found")
                    break
                current_messages = code.messages.copy()
                if not current_messages:
                    logger.warning(f"[{code_name}] No messages to send")
                    await asyncio.sleep(300)
                    continue
                logger.info(
                    f"[{code_name}] Processing {len(current_messages)} messages"
                )

                try:
                    batches = self._chunk_messages(
                        current_messages, batch_size=self.BATCH_SIZE_LARGE
                    )

                    for batch_idx, batch in enumerate(batches):
                        if not self._active or not code._active:
                            logger.info(
                                f"[{code_name}] Stopped during batch processing"
                            )
                            return
                        logger.info(
                            f"[{code_name}] Processing batch {batch_idx + 1}/{len(batches)}"
                        )
                        batch_messages, deleted = await self._process_message_batch(
                            code, batch
                        )

                        if batch_messages:
                            logger.info(
                                f"[{code_name}] Batch {batch_idx + 1} processed: {len(batch_messages)} valid messages"
                            )
                        else:
                            logger.warning(
                                f"[{code_name}] Batch {batch_idx + 1} processing failed"
                            )
                        messages_to_send.extend(batch_messages)
                        deleted_messages.extend(deleted)
                    if not messages_to_send:
                        logger.error(
                            f"[{code_name}] Failed to retrieve any valid messages"
                        )
                        await asyncio.sleep(300)
                        continue
                except Exception as batch_error:
                    logger.error(
                        f"[{code_name}] Batch processing error: {batch_error}",
                        exc_info=True,
                    )
                    await asyncio.sleep(300)
                    continue
                # Remove deleted messages

                if deleted_messages:
                    async with self._lock:
                        original_count = len(code.messages)
                        code.messages = [
                            m for m in code.messages if m not in deleted_messages
                        ]
                        logger.info(
                            f"[{code_name}] Removed {original_count - len(code.messages)} deleted messages"
                        )
                        await self.save_config()
                # Handle batch mode

                if not code.batch_mode:
                    async with self._lock:
                        next_index = code.get_next_message_index()
                        messages_to_send = [
                            messages_to_send[next_index % len(messages_to_send)]
                        ]
                        logger.info(
                            f"[{code_name}] Single message mode: selected message {next_index}"
                        )
                # Send messages

                logger.info(
                    f"[{code_name}] Starting message broadcast to {len(code.chats)} chats"
                )
                failed_chats = await self._send_messages_to_chats(
                    code, code_name, messages_to_send
                )

                if failed_chats:
                    logger.info(
                        f"[{code_name}] Handling {len(failed_chats)} failed chats"
                    )
                    await self._handle_failed_chats(code_name, failed_chats)
                # Update timestamp

                current_time = time.time()
                self.last_broadcast_time[code_name] = current_time

                async with self._lock:
                    saved_times = self.db.get("broadcast", "last_broadcast_times", {})
                    saved_times[code_name] = current_time
                    self.db.set("broadcast", "last_broadcast_times", saved_times)
                    logger.info(f"[{code_name}] Updated broadcast timestamp")
                logger.info(f"[{code_name}] Cycle completed successfully")
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                logger.info(f"[{code_name}] Broadcast cancelled")
                break
            except Exception as e:
                logger.error(
                    f"[{code_name}] Critical error in broadcast loop: {e}",
                    exc_info=True,
                )
                # Add stack trace

                logger.exception("Full traceback:")
                await asyncio.sleep(300)
            logger.info(f"[{code_name}] Cycle iteration complete")

    async def _fetch_messages(
        self, msg_data: dict
    ) -> Optional[Union[Message, List[Message]]]:
        """Получает сообщения с улучшенной обработкой ошибок"""
        key = (msg_data["chat_id"], msg_data["message_id"])

        try:
            logger.info(
                f"[fetch] Attempting to fetch message {msg_data['message_id']} from {msg_data['chat_id']}"
            )
            cached = await self._message_cache.get(key)
            if cached:
                logger.info(
                    f"[fetch] Retrieved message {msg_data['message_id']} from cache"
                )
                return cached
            message = await self.client.get_messages(
                msg_data["chat_id"], ids=msg_data["message_id"]
            )

            if message:
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
                        logger.info(
                            f"[fetch] Successfully cached album with {len(messages)} messages"
                        )
                        return messages[0] if len(messages) == 1 else messages
                else:
                    await self._message_cache.set(key, message)
                    logger.info(
                        f"[fetch] Successfully cached single message {msg_data['message_id']}"
                    )
                    return message
            logger.warning(
                f"Сообщение {msg_data['message_id']} существует, но не удалось получить из чата {msg_data['chat_id']}"
            )
            return None
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при получении сообщения: {e}")
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
