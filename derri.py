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
    ChannelPrivateError,
    ChatAdminRequiredError,
    FloodWaitError,
)

from .. import loader

logger = logging.getLogger(__name__)


class SimpleCache:
    """Простой кэш с TTL и ограничением размера"""

    def __init__(self, ttl: int = 3600, max_size: int = 50):
        self.cache = OrderedDict()
        self.ttl = ttl
        self.max_size = max_size
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 3000

    async def get(self, key):
        """Получает значение из кэша"""
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
        """Устанавливает значение в кэш"""
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
        """Очищает устаревшие записи"""
        async with self._lock:
            current_time = time.time()
            self.cache = OrderedDict(
                (k, v)
                for k, v in self.cache.items()
                if current_time - v[0] <= self.ttl
            )


def register(cb):
    """Регистрация модуля"""
    cb(BroadcastMod())
    return []


@loader.tds
class BroadcastMod(loader.Module):
    """Модуль для управления рассылками

    Команды:
    • .br add <код> - создать рассылку и добавить сообщение (ответом)
    • .br delete <код> - удалить рассылку
    • .br remove <код> - удалить сообщение (ответом)
    • .br addchat <код> - добавить текущий чат
    • .br rmchat <код> - удалить текущий чат
    • .br int <код> <мин> <макс> - установить интервал
    • .br mode <код> <режим> - установить режим (auto/normal/schedule)
    • .br allmsgs <код> <on/off> - отправлять все сообщения/одно
    • .br start <код> - запустить рассылку
    • .br stop <код> - остановить рассылку
    • .br list - список рассылок
    """

    strings = {"name": "Broadcast"}

    async def client_ready(self):
        """Инициализация при загрузке модуля"""
        self.manager = BroadcastManager(self._client, self.db)
        await self.manager._load_config()
        self.me_id = (await self._client.get_me()).id

    async def brcmd(self, message):
        """Команда для управления рассылкой. Используйте .help Broadcast для справки."""
        if not self.manager.is_authorized(message.sender_id):
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
            if (
                existing["chat_id"] == chat_id
                and existing["message_id"] == message_id
            ):
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
        self._last_message_index = (self._last_message_index + 1) % len(
            self.messages
        )
        return self._last_message_index

    def is_valid_interval(self) -> bool:
        """Проверяет корректность интервала"""
        min_val, max_val = self.interval
        return (
            isinstance(min_val, int)
            and isinstance(max_val, int)
            and 0 < min_val < max_val <= 1440
        )

    def normalize_interval(self) -> Tuple[int, int]:
        """Нормализует интервал рассылки"""
        if self.is_valid_interval():
            return self.interval
        return (10, 13)

    def get_random_delay(self) -> int:
        """Возвращает случайную задержку в пределах интервала"""
        min_val, max_val = self.normalize_interval()
        return random.randint(min_val * 60, max_val * 60)

    def to_dict(self) -> dict:
        """Сериализует объект в словарь"""
        return {
            "chats": list(self.chats),
            "messages": self.messages,
            "interval": list(self.interval),
            "send_mode": self.send_mode,
            "batch_mode": self.batch_mode,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Broadcast":
        """Создает объект из словаря"""
        return cls(
            chats=set(data.get("chats", [])),
            messages=data.get("messages", []),
            interval=tuple(data.get("interval", (10, 13))),
            send_mode=data.get("send_mode", "auto"),
            batch_mode=data.get("batch_mode", False),
        )


class BroadcastManager:
    """Manages broadcast operations and state."""

    # Размеры батчей
    BATCH_SIZE_SMALL = 5
    BATCH_SIZE_MEDIUM = 8
    BATCH_SIZE_LARGE = 10
    BATCH_SIZE_XLARGE = 15

    MAX_MESSAGES_PER_CODE = 100
    MAX_CHATS_PER_CODE = 1000
    MAX_CODES = 50
    MAX_RETRY_COUNT = 3
    MAX_FLOOD_WAIT_COUNT = 3
    MAX_CONSECUTIVE_ERRORS = 5
    MAX_MEDIA_SIZE = 10 * 1024 * 1024  # 10MB

    # Пороги для батчей
    BATCH_THRESHOLD_SMALL = 20
    BATCH_THRESHOLD_MEDIUM = 50
    BATCH_THRESHOLD_LARGE = 100

    # Задержки
    RETRY_DELAY_LONG = 300   # 5 минут
    RETRY_DELAY_SHORT = 60   # 1 минута
    RETRY_DELAY_MINI = 3     # 3 секунды
    EXPONENTIAL_DELAY_BASE = 10  # База для экспоненциальной задержки
    NOTIFY_DELAY = 1  # Задержка между уведомлениями

    # Прочие константы
    NOTIFY_GROUP_SIZE = 50  # Размер группы для уведомлений
    OFFSET_MULTIPLIER = 2  # Множитель для смещения времени в группе
    COMMAND_PARTS_COUNT = 2  # Количество частей команды в watcher
    INTERVAL_PADDING = 1  # Дополнительная минута к интервалу

    def __init__(self, client, db):
        self.client = client
        self.db = db
        self.codes: Dict[str, Broadcast] = {}
        self.broadcast_tasks: Dict[str, asyncio.Task] = {}
        self.last_broadcast_time: Dict[str, float] = {}
        self._message_cache = SimpleCache(ttl=7200, max_size=50)
        self._active = True
        self._lock = asyncio.Lock()
        self.me_id = None
        self._cleanup_task = None
        self._periodic_task = None
        self._authorized_users = self._load_authorized_users()
        self.watcher_enabled = False

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

    def is_authorized(self, user_id: int) -> bool:
        """Проверяет, авторизован ли пользователь"""
        return user_id in self._authorized_users or user_id == self.me_id

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
        """Загружает конфигурацию из базы данных"""
        try:
            config = self.db.get("broadcast", "config", {})
            if not config:
                return

            for code_name, code_data in config.get("codes", {}).items():
                self.codes[code_name] = Broadcast.from_dict(code_data)

            saved_times = self.db.get("broadcast", "last_broadcast_times", {})
            self.last_broadcast_time.update(
                {code: float(time_) for code, time_ in saved_times.items()}
            )

        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")

    async def save_config(self):
        """Сохраняет конфигурацию в базу данных"""
        async with self._lock:
            try:
                config = {
                    "version": 1,
                    "last_save": int(time.time()),
                    "codes": {
                        name: code.to_dict()
                        for name, code in self.codes.items()
                    },
                }
                self.db.set("broadcast", "config", config)
                self.db.set(
                    "broadcast",
                    "last_broadcast_times",
                    self.last_broadcast_time,
                )
            except Exception as e:
                logger.error(f"Ошибка сохранения конфигурации: {e}")

    async def handle_command(self, message: Message):
        """Обработчик команд для управления рассылкой"""
        try:
            args = message.text.split()[1:]
            if not args:
                await message.edit("❌ Укажите действие и код рассылки")
                return

            action = args[0].lower()

            code_name = args[1] if len(args) > 1 else None

            if action == "add":
                if not code_name:
                    await message.edit("❌ Укажите код рассылки")
                    return

                reply = await message.get_reply_message()
                if not reply:
                    await message.edit(
                        "❌ Ответьте на сообщение, которое нужно добавить в рассылку"
                    )
                    return

                code = self.codes.get(code_name)
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
                    async for msg in message.client.iter_messages(
                        reply.chat_id,
                        min_id=max(0, reply.id - 10),
                        max_id=reply.id + 10,
                    ):
                        if getattr(msg, "grouped_id", None) == grouped_id:
                            grouped_ids.append(msg.id)

                if code.add_message(reply.chat_id, reply.id, grouped_ids):
                    await self.save_config()
                    await message.edit(
                        f"✅ {'Рассылка создана и с' if is_new else 'С'}ообщение добавлено"
                    )
                else:
                    await message.edit("❌ Это сообщение уже есть в рассылке")

            elif action == "delete":
                if not code_name:
                    await message.edit("❌ Укажите код рассылки")
                    return
                
                code = self.codes.get(code_name)
                if not code:
                    await message.edit(f"❌ Код рассылки {code_name} не найден")
                    return
                
                if (
                    code_name in self.broadcast_tasks
                    and not self.broadcast_tasks[code_name].done()
                ):
                    self.broadcast_tasks[code_name].cancel()
                del self.codes[code_name]
                await self.save_config()
                await message.edit(f"✅ Рассылка {code_name} удалена")

            elif action == "remove":
                if not code_name:
                    await message.edit("❌ Укажите код рассылки")
                    return
                
                code = self.codes.get(code_name)
                if not code:
                    await message.edit(f"❌ Код рассылки {code_name} не найден")
                    return

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
                    await message.edit(
                        "❌ Это сообщение не найдено в рассылке"
                    )

            elif action == "addchat":
                if not code_name:
                    await message.edit("❌ Укажите код рассылки")
                    return
                
                code = self.codes.get(code_name)
                if not code:
                    await message.edit(f"❌ Код рассылки {code_name} не найден")
                    return

                if len(args) > 2:
                    chat_id = await self._get_chat_id(args[2])
                    if not chat_id:
                        await message.edit(
                            "❌ Не удалось получить ID чата. Проверьте ссылку/юзернейм"
                        )
                        return
                else:
                    chat_id = message.chat_id

                if len(code.chats) >= self.MAX_CHATS_PER_CODE:
                    await message.edit(
                        f"❌ Достигнут лимит чатов ({self.MAX_CHATS_PER_CODE})"
                    )
                    return

                if chat_id in code.chats:
                    await message.edit("❌ Этот чат уже добавлен в рассылку")
                    return

                code.chats.add(chat_id)
                await self.save_config()
                await message.edit("✅ Чат добавлен в рассылку")

            elif action == "rmchat":
                if not code_name:
                    await message.edit("❌ Укажите код рассылки")
                    return
                
                code = self.codes.get(code_name)
                if not code:
                    await message.edit(f"❌ Код рассылки {code_name} не найден")
                    return

                chat_id = None
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

            elif action == "int":
                if not code_name:
                    await message.edit("❌ Укажите код рассылки")
                    return
                
                code = self.codes.get(code_name)
                if not code:
                    await message.edit(f"❌ Код рассылки {code_name} не найден")
                    return

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
                    await message.edit(
                        "❌ Некорректный интервал (0 < min < max <= 1440)"
                    )
                    return

                await self.save_config()
                await message.edit(
                    f"✅ Установлен интервал {min_val}-{max_val} минут"
                )

            elif action == "mode":
                if not code_name:
                    await message.edit("❌ Укажите код рассылки")
                    return
                
                code = self.codes.get(code_name)
                if not code:
                    await message.edit(f"❌ Код рассылки {code_name} не найден")
                    return

                if len(args) < 3:
                    await message.edit(
                        "❌ Укажите режим отправки (auto/normal/schedule)"
                    )
                    return

                mode = args[2].lower()
                if mode not in ["auto", "normal", "schedule"]:
                    await message.edit(
                        "❌ Неверный режим. Доступные режимы: auto, normal, schedule"
                    )
                    return

                code.send_mode = mode
                await self.save_config()
                await message.edit(f"✅ Установлен режим отправки: {mode}")

            elif action == "allmsgs":
                if not code_name:
                    await message.edit("❌ Укажите код рассылки")
                    return
                
                code = self.codes.get(code_name)
                if not code:
                    await message.edit(f"❌ Код рассылки {code_name} не найден")
                    return

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

            elif action == "start":
                if not code_name:
                    await message.edit("❌ Укажите код рассылки")
                    return
                
                code = self.codes.get(code_name)
                if not code:
                    await message.edit(f"❌ Код рассылки {code_name} не найден")
                    return
                
                if not code.messages:
                    await message.edit("❌ Добавьте хотя бы одно сообщение в рассылку")
                    return
                if not code.chats:
                    await message.edit("❌ Добавьте хотя бы один чат в рассылку")
                    return
                
                code._active = True
                if (
                    code_name not in self.broadcast_tasks
                    or self.broadcast_tasks[code_name].done()
                ):
                    self.broadcast_tasks[code_name] = asyncio.create_task(
                        self._broadcast_loop(code_name)
                    )
                await message.edit(f"✅ Рассылка {code_name} запущена")

            elif action == "stop":
                if not code_name:
                    await message.edit("❌ Укажите код рассылки")
                    return
                
                code = self.codes.get(code_name)
                if not code:
                    await message.edit(f"❌ Код рассылки {code_name} не найден")
                    return
                
                code._active = False
                if (
                    code_name in self.broadcast_tasks
                    and not self.broadcast_tasks[code_name].done()
                ):
                    self.broadcast_tasks[code_name].cancel()
                await message.edit(f"✅ Рассылка {code_name} остановлена")

            elif action == "watcher":
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

            elif action == "list":
                if not self.codes:
                    await message.edit("❌ Нет активных рассылок")
                    return
                response = "📝 Список рассылок:\n\n"
                current_time = time.time()
                for name, code in self.codes.items():
                    is_running = name in self.broadcast_tasks and not self.broadcast_tasks[name].done()
                    status = "✅ Активна" if code._active and is_running else "❌ Не запущена"
                    last_time = self.last_broadcast_time.get(name, 0)
                    
                    if last_time and current_time > last_time:
                        minutes_ago = int((current_time - last_time) / 60)
                        if minutes_ago == 0:
                            last_active = "(последняя активность: менее минуты назад)"
                        else:
                            last_active = f"(последняя активность: {minutes_ago} мин назад)"
                    else:
                        last_active = ""
                    
                    response += f"• {name}: {status} {last_active}\n"
                    response += f"  ├ Чатов: {len(code.chats)} (активных)\n"
                    response += f"  ├ Сообщений: {len(code.messages)}\n"
                    response += f"  ├ Интервал: {code.interval[0]}-{code.interval[1]} мин\n"
                    response += f"  ├ Режим: {code.send_mode}\n"
                    response += f"  └ Все сообщения: {'да' if code.batch_mode else 'нет'}\n\n"
                await message.edit(response)

            else:
                await message.edit(
                    "❌ Неизвестное действие\n\n"
                    "Доступные команды:\n"
                    "• add <код> - создать рассылку и добавить сообщение (ответом)\n"
                    "• delete <код> - удалить рассылку\n"
                    "• remove <код> - удалить сообщение (ответом)\n"
                    "• addchat <код> - добавить текущий чат\n"
                    "• rmchat <код> - удалить текущий чат\n"
                    "• int <код> <мин> <макс> - установить интервал\n"
                    "• mode <код> <режим> - установить режим (auto/normal/schedule)\n"
                    "• allmsgs <код> <on/off> - отправлять все сообщения/одно\n"
                    "• start <код> - запустить рассылку\n"
                    "• stop <код> - остановить рассылку\n"
                    "• watcher <on/off> - включить/выключить автодобавление чатов\n"
                    "• list - список рассылок"
                )

        except Exception as e:
            logger.error(f"Error handling command: {e}")
            await message.edit(f"❌ Произошла ошибка: {str(e)}")

    async def _send_messages_to_chats(
        self,
        code: Optional[Broadcast],
        code_name: str,
        messages_to_send: List[Union[Message, List[Message]]],
    ) -> Set[int]:
        """Отправляет сообщения в чаты с оптимизированной обработкой ошибок."""
        if not code:
            logger.error(f"Код рассылки {code_name} не найден при отправке сообщений")
            return set()

        if not messages_to_send:
            logger.error(f"Нет сообщений для отправки в рассылке {code_name}")
            return set()

        failed_chats: Set[int] = set()
        success_count: int = 0
        error_counts: Dict[str, int] = {}
        flood_wait_count: int = 0
        consecutive_errors: int = 0

        async def send_to_chat(chat_id: int, base_time: datetime, position_in_batch: int, current_batch_size: int, retry_count: int = 0) -> None:
            nonlocal success_count, consecutive_errors, flood_wait_count
            if not self._active or not code._active:
                return

            try:
                offset_minutes = (position_in_batch * self.OFFSET_MULTIPLIER) // current_batch_size
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
                consecutive_errors = 0

            except FloodWaitError as e:
                flood_wait_count += 1
                consecutive_errors += 1
                
                if flood_wait_count >= self.MAX_FLOOD_WAIT_COUNT:
                    logger.error("Слишком много FloodWaitError, останавливаем рассылку")
                    self._active = False
                    return
                
                wait_time = e.seconds * (2 ** retry_count)
                logger.warning(f"FloodWaitError для чата {chat_id}: ждем {wait_time} секунд")
                await asyncio.sleep(wait_time)
                
                if retry_count < self.MAX_RETRY_COUNT:
                    await send_to_chat(chat_id, base_time, position_in_batch, current_batch_size, retry_count + 1)

            except (ChatWriteForbiddenError, UserBannedInChannelError, ChannelPrivateError, ChatAdminRequiredError) as e:
                error_type = type(e).__name__
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
                failed_chats.add(chat_id)
                logger.warning(f"Ошибка доступа для чата {chat_id}: {str(e)}")

            except Exception as e:
                error_type = type(e).__name__
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
                consecutive_errors += 1
                logger.error(f"Непредвиденная ошибка для чата {chat_id}: {str(e)}")
                
                if consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
                    logger.error("Слишком много последовательных ошибок, увеличиваем задержки")
                    await asyncio.sleep(self.RETRY_DELAY_SHORT * (2 ** retry_count))
                
                if retry_count < self.MAX_RETRY_COUNT:
                    await send_to_chat(chat_id, base_time, position_in_batch, current_batch_size, retry_count + 1)
                else:
                    failed_chats.add(chat_id)

        chats = list(code.chats)
        random.shuffle(chats)

        total_chats = len(chats)
        if total_chats <= self.BATCH_THRESHOLD_SMALL:
            batch_size = self.BATCH_SIZE_SMALL
        elif total_chats <= self.BATCH_THRESHOLD_MEDIUM:
            batch_size = self.BATCH_SIZE_MEDIUM
        elif total_chats <= self.BATCH_THRESHOLD_LARGE:
            batch_size = self.BATCH_SIZE_LARGE
        else:
            batch_size = self.BATCH_SIZE_XLARGE

        min_interval, max_interval = code.normalize_interval()
        base_time = datetime.now().replace(second=0, microsecond=0)
        
        for i in range(0, len(chats), batch_size):
            if not self._active or not code._active:
                break

            last_time = self.last_broadcast_time.get(code_name, 0)
            if last_time:
                wait_time = last_time + (min_interval * 60) - time.time()
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

            current_batch_size = batch_size
            if consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS // 2:
                current_batch_size = max(self.MAX_RETRY_COUNT, batch_size // 2)
                logger.warning(f"Уменьшен размер группы до {current_batch_size} из-за ошибок")

            batch = chats[i:i + current_batch_size]
            random.shuffle(batch)
            
            tasks = [send_to_chat(chat_id, base_time, idx, current_batch_size) for idx, chat_id in enumerate(batch)]
            await asyncio.gather(*tasks)
            
            delay_minutes = min_interval + self.INTERVAL_PADDING
            base_time = base_time + timedelta(minutes=delay_minutes)
            
            self.last_broadcast_time[code_name] = time.time()
            
            if consecutive_errors > 0:
                await asyncio.sleep(self.EXPONENTIAL_DELAY_BASE * (2 ** consecutive_errors))
            else:
                await asyncio.sleep(self.RETRY_DELAY_MINI)

        if total_chats > 0:
            success_rate = (success_count / total_chats) * 100
            logger.info(f"Рассылка завершена. Успешно: {success_count}/{total_chats} ({success_rate:.1f}%)")
            if error_counts:
                logger.info("Статистика ошибок:")
                for error_type, count in error_counts.items():
                    logger.info(f"- {error_type}: {count}")

        return failed_chats

    async def _send_message(
        self,
        code_name: str,
        chat_id: int,
        messages_to_send: Union[Message, List[Message]],
        send_mode: str = "auto",
        schedule_time: Optional[datetime] = None,
    ) -> bool:
        """Отправляет сообщение с ограничением частоты."""
        try:
            async def forward_messages(messages: Union[Message, List[Message]]) -> None:
                """Вспомогательная функция для пересылки сообщений"""
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

            # Режим forward - всегда пересылаем
            if send_mode == "forward":
                await forward_messages(messages_to_send)
                return True

            # Режим normal - всегда отправляем как новое
            if send_mode == "normal":
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
                return True

            # Режим auto - умное определение способа отправки
            if isinstance(messages_to_send, list) or messages_to_send.media:
                await forward_messages(messages_to_send)
            else:
                await self.client.send_message(
                    entity=chat_id,
                    message=self._get_message_content(messages_to_send),
                    schedule=schedule_time,
                )
            return True

        except FloodWaitError as e:
            logger.warning(f"FloodWaitError: необходимо подождать {e.seconds} секунд")
            raise

        except (ChatWriteForbiddenError, UserBannedInChannelError):
            raise

        except Exception as e:
            logger.error(
                f"Error sending message to {chat_id} in broadcast '{code_name}': {e}"
            )
            return False

    async def _handle_failed_chats(
        self, 
        code_name: str, 
        failed_chats: Set[int]
    ) -> None:
        """Обрабатывает чаты, в которые не удалось отправить сообщения."""
        if not failed_chats:
            return

        try:
            async with self._lock:
                code = self.codes.get(code_name)
                if not code:
                    logger.error(f"Код рассылки {code_name} не найден при обработке ошибок")
                    return
                    
                code.chats -= failed_chats
                await self.save_config()

                # Оптимизированная группировка чатов без преобразования в list
                chat_groups = [
                    ", ".join(str(chat_id) for chat_id in tuple(failed_chats)[i:i+self.NOTIFY_GROUP_SIZE])
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
                            schedule=datetime.now() + timedelta(seconds=self.RETRY_DELAY_SHORT),
                        )
                        await asyncio.sleep(self.NOTIFY_DELAY)
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления: {e}")

        except Exception as e:
            logger.error(
                f"Ошибка обработки неудачных чатов для {code_name}: {e}"
            )

    @staticmethod
    def _chunk_messages(
        messages: List[Union[Message, List[Message]]], 
        batch_size: int = 8
    ) -> List[List[Union[Message, List[Message]]]]:
        """Разбивает список сообщений на части оптимального размера."""
        if not messages:
            return []
        return [
            messages[i : i + batch_size]
            for i in range(0, len(messages), batch_size)
        ]

    async def _process_message_batch(
        self, 
        code: Optional[Broadcast], 
        messages: List[dict]
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
                # Проверяем размер медиафайлов
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
                return message.media.document.size <= 10 * 1024 * 1024  # 10MB
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
        retry_count = 0

        while self._active:
            try:
                code = self.codes.get(code_name)
                if not self._should_continue(code, code_name):
                    await asyncio.sleep(self.RETRY_DELAY_SHORT)
                    continue

                messages_to_send = []
                deleted_messages = []

                # Используем _chunk_messages для разбивки на батчи
                batches = self._chunk_messages(code.messages, batch_size=self.BATCH_SIZE_LARGE)
                for batch in batches:
                    if not self._should_continue(code, code_name):
                        break

                    batch_messages, deleted = await self._process_message_batch(
                        code, batch
                    )
                    messages_to_send.extend(batch_messages)
                    deleted_messages.extend(deleted)

                if deleted_messages:
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
                        self.db.set(
                            "broadcast", "last_broadcast_times", saved_times
                        )
                except Exception as e:
                    logger.error(f"Ошибка сохранения времени рассылки: {e}")

            except asyncio.CancelledError:
                logger.info(f"Рассылка {code_name} остановлена")
                break
            except Exception as e:
                logger.error(
                    f"Критическая ошибка в цикле рассылки {code_name}: {e}"
                )
                retry_count += 1
                if retry_count >= self.MAX_RETRY_COUNT:
                    logger.error(
                        f"Достигнут лимит попыток выполнения рассылки {code_name}"
                    )
                    await asyncio.sleep(self.RETRY_DELAY_LONG)
                    retry_count = 0
                else:
                    await asyncio.sleep(self.RETRY_DELAY_SHORT)

    async def watcher(self, message: Message):
        """Автоматически добавляет чаты в рассылку."""
        try:
            if not self.watcher_enabled:
                return

            if not (message and message.text and message.text.startswith("!")):
                return

            if message.sender_id != self.me_id:
                return

            parts = message.text.split()
            if len(parts) != self.COMMAND_PARTS_COUNT:
                return

            code_name = parts[0][1:]
            if not code_name:
                return
                
            chat_id = message.chat_id

            code = self.codes.get(code_name)
            if not code:
                return

            if len(code.chats) >= self.MAX_CHATS_PER_CODE:
                return

            if chat_id not in code.chats:
                code.chats.add(chat_id)
                await self.save_config()

        except Exception as e:
            logger.error(f"Error in watcher: {e}")

    async def on_unload(self):
        """Cleanup on module unload."""
        self._active = False

        for task_name in ["_cleanup_task", "_periodic_task"]:
            task = getattr(self, task_name, None)
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

        for task in [t for t in self.broadcast_tasks.values() if t and not t.done()]:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    async def _fetch_messages(
        self, msg_data: dict
    ) -> Optional[Union[Message, List[Message]]]:
        """Получает сообщения с учетом ограничений размера медиа."""
        key = (msg_data["chat_id"], msg_data["message_id"])

        try:
            cached = await self._message_cache.get(key)
            if cached:
                return cached

            message_ids = msg_data.get("grouped_ids", [msg_data["message_id"]])

            messages = []
            for i in range(0, len(message_ids), 100):
                batch = message_ids[i : i + 100]
                batch_messages = await self.client.get_messages(
                    msg_data["chat_id"], ids=batch
                )
                messages.extend(m for m in batch_messages if m)

            if not messages:
                logger.warning(
                    f"Не удалось получить сообщение {msg_data['message_id']} из чата {msg_data['chat_id']}"
                )
                return None

            for msg in messages:
                if hasattr(msg, "media") and msg.media:
                    if hasattr(msg.media, "document") and hasattr(
                        msg.media.document, "size"
                    ):
                        if msg.media.document.size > 10 * 1024 * 1024:
                            logger.warning(
                                f"Медиа в сообщении {msg.id} превышает лимит размера (10MB)"
                            )
                            return None

            if len(message_ids) > 1:
                messages.sort(key=lambda x: message_ids.index(x.id))

            if messages:
                await self._message_cache.set(key, messages)
                return messages[0] if len(messages) == 1 else messages

            return None

        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Ошибка сети при получении сообщений: {e}")
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
