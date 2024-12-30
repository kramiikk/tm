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
from ratelimit import limits, sleep_and_retry
from telethon.errors import (
    ChatWriteForbiddenError,
    UserBannedInChannelError,
    ChannelPrivateError,
    ChatAdminRequiredError,
)

from .. import loader, utils

logger = logging.getLogger(__name__)


@dataclass
class Broadcast:
    """Основной класс для управления рассылкой"""

    chats: Set[int] = field(default_factory=set)
    messages: List[dict] = field(default_factory=list)
    interval: Tuple[int, int] = (10, 13)
    send_mode: str = "auto"
    batch_mode: bool = False

    def add_message(
        self, chat_id: int, message_id: int, grouped_ids: List[int] = None
    ):
        self.messages.append(
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "grouped_ids": grouped_ids or [],
            }
        )

    def is_valid_interval(self) -> bool:
        min_val, max_val = self.interval
        return (
            isinstance(min_val, int)
            and isinstance(max_val, int)
            and 0 < min_val < max_val <= 1440
        )

    def normalize_interval(self) -> Tuple[int, int]:
        if self.is_valid_interval():
            return self.interval
        return (10, 13)


class SimpleCache:
    def __init__(self, ttl: int = 3600, max_size: int = 50):
        self.cache = OrderedDict()
        self.ttl = ttl
        self.max_size = max_size
        self._lock = asyncio.Lock()

    async def get(self, key):
        async with self._lock:
            if key not in self.cache:
                return None
            timestamp, value = self.cache[key]
            if time.time() - timestamp > self.ttl:
                del self.cache[key]
                return None
            return value

    async def set(self, key, value):
        async with self._lock:
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
            self.cache[key] = (time.time(), value)

    async def clean_expired(self):
        async with self._lock:
            current_time = time.time()
            expired = [
                k
                for k, (t, _) in self.cache.items()
                if current_time - t > self.ttl
            ]
            for k in expired:
                del self.cache[k]


class BroadcastManager:
    """Manages broadcast operations and state."""

    MAX_MESSAGES_PER_CODE = 100
    MAX_CHATS_PER_CODE = 1000
    MAX_CODES = 50

    def __init__(self, client, db, json_path: str = "/root/Heroku/loll.json"):
        self.client = client
        self.db = db
        self._authorized_users = self._load_authorized_users(json_path)
        self.codes: OrderedDict[str, Broadcast] = OrderedDict()
        self.broadcast_tasks: Dict[str, asyncio.Task] = {}
        self.message_indices: Dict[str, int] = {}
        self.last_broadcast_time: Dict[str, float] = {}
        self.last_schedule_delay: int = 60
        self._message_cache = SimpleCache(ttl=7200, max_size=50)
        self._active = True
        self._lock = asyncio.Lock()

    def _load_authorized_users(self, json_path: str) -> Set[int]:
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
                return {int(uid) for uid in data.get("authorized_users", [])}
        except Exception as e:
            logger.error(f"Error loading auth users: {e}")
            return {7175372340}  # Дефолтный ID

    def is_authorized(self, user_id: int) -> bool:
        return user_id in self._authorized_users

    async def _fetch_messages(
        self, msg_data: dict
    ) -> Optional[Union[Message, List[Message]]]:
        """Получает сообщения с учетом ограничений размера медиа."""
        try:
            key = (msg_data["chat_id"], msg_data["message_id"])
            cached = await self._message_cache.get(key)
            if cached:
                return cached

            message_ids = msg_data.get("grouped_ids", [msg_data["message_id"]])
            messages = await self.client.get_messages(
                msg_data["chat_id"], ids=message_ids
            )

            if not messages:
                logger.warning(
                    f"Проблема с сообщением {msg_data['message_id']} из {msg_data['chat_id']}"
                )
                return None

            valid_messages = [m for m in messages if m]

            # Проверка размера медиа
            for msg in valid_messages:
                if (
                    msg.media
                    and hasattr(msg.media, "document")
                    and hasattr(msg.media.document, "size")
                    and msg.media.document.size > 10 * 1024 * 1024
                ):  # 10MB limit
                    logger.warning(
                        f"Медиа слишком большое в сообщении {msg.id}"
                    )
                    return None

            if len(message_ids) > 1:  # Для альбомов
                valid_messages.sort(key=lambda x: x.id)

            if valid_messages:
                await self._message_cache.set(key, valid_messages)
                return valid_messages

        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            return None

    def _create_broadcast_code_from_dict(self, code_data: dict) -> Broadcast:
        """Создает объект Broadcast из словаря."""
        if not isinstance(code_data, dict):
            raise ValueError("Invalid code data format")

        chats = set(code_data.get("chats", []))
        if not all(isinstance(chat_id, int) for chat_id in chats):
            raise ValueError("Invalid chat ID format")

        messages = []
        for msg_data in code_data.get("messages", []):
            if not isinstance(msg_data, dict):
                continue
            try:
                messages.append(
                    {
                        "chat_id": msg_data["chat_id"],
                        "message_id": msg_data["message_id"],
                        "grouped_ids": msg_data.get("grouped_ids", []),
                    }
                )
            except (KeyError, TypeError):
                logger.error(f"Invalid message data: {msg_data}")
                continue

        return Broadcast(
            chats=chats,
            messages=messages,
            interval=tuple(code_data.get("interval", (10, 13))),
            send_mode=code_data.get("send_mode", "auto"),
            batch_mode=code_data.get("batch_mode", False),
        )

    def _load_config_from_dict(self, data: dict):
        """Загружает конфигурацию рассылки из словаря."""
        for code_name, code_data in data.get("codes", {}).items():
            try:
                broadcast = self._create_broadcast_code_from_dict(code_data)
                self.codes[code_name] = broadcast
            except Exception as e:
                logger.error(f"Error loading broadcast code {code_name}: {e}")

        saved_times = self.db.get("broadcast", "last_broadcast_times", {})
        self.last_broadcast_time.update(
            {
                code: float(time_)
                for code, time_ in saved_times.items()
                if isinstance(time_, (int, float))
            }
        )

    @sleep_and_retry
    @limits(calls=1, period=5)
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
            if isinstance(messages_to_send, list):
                messages = messages_to_send
                from_peer = messages[0].chat_id
            elif messages_to_send.media and send_mode != "normal":
                messages = [messages_to_send]
                from_peer = messages_to_send.chat_id
            else:
                await self.client.send_message(
                    entity=chat_id,
                    message=messages_to_send.text,
                    schedule=schedule_time,
                )
                return True

            await self.client.forward_messages(
                entity=chat_id,
                messages=messages,
                from_peer=from_peer,
                schedule=schedule_time,
            )
            return True
        except (ChatWriteForbiddenError, UserBannedInChannelError):
            raise
        except Exception as e:
            logger.error(
                f"Error sending message to {chat_id} in broadcast '{code_name}': {e}"
            )
            return False

    async def _send_messages_to_chats(
        self,
        code: Broadcast,
        code_name: str,
        messages_to_send: List[Union[Message, List[Message]]],
    ) -> Set[int]:
        """Отправляет сообщения чатам и обрабатывает неудачи."""
        chats = list(code.chats)
        random.shuffle(chats)
        failed_chats = set()

        schedule_options = [60, 120, 180]  # 1, 2 или 3 минуты в секундах
        schedule_delay = random.choice(schedule_options)
        schedule_time = datetime.now() + timedelta(seconds=schedule_delay)
        self.last_schedule_delay = schedule_delay

        for chat_id in chats:
            try:
                if code.batch_mode:
                    for msg in messages_to_send:
                        success = await self._send_message(
                            code_name,
                            chat_id,
                            msg,
                            code.send_mode,
                            schedule_time,
                        )
                        if not success:
                            failed_chats.add(chat_id)
                            break
                else:
                    success = await self._send_message(
                        code_name,
                        chat_id,
                        messages_to_send[0],
                        code.send_mode,
                        schedule_time,
                    )
                    if not success:
                        failed_chats.add(chat_id)
            except (ChatWriteForbiddenError, UserBannedInChannelError):
                failed_chats.add(chat_id)
            except Exception as e:
                logger.error(
                    f"Failed to send to chat {chat_id} for code {code_name}: {e}"
                )
                failed_chats.add(chat_id)

        return failed_chats

    async def add_message(self, code_name: str, message) -> bool:
        """Добавляет сообщение в список рассылки с валидацией."""
        try:
            async with self._lock:
                if (
                    len(self.codes) >= self.MAX_CODES
                    and code_name not in self.codes
                ):
                    logger.warning(
                        f"Max codes limit ({self.MAX_CODES}) reached"
                    )
                    return False

                if code_name not in self.codes:
                    self.codes[code_name] = Broadcast()

                code = self.codes[code_name]

                if len(code.messages) >= self.MAX_MESSAGES_PER_CODE:
                    logger.warning(
                        f"Max messages per code ({self.MAX_MESSAGES_PER_CODE}) reached"
                    )
                    return False

                # Проверка на дубликаты
                message_key = (message.chat_id, message.id)
                for existing_msg in code.messages:
                    if (
                        existing_msg["chat_id"],
                        existing_msg["message_id"],
                    ) == message_key:
                        logger.warning(
                            f"Message {message_key} already exists in code {code_name}"
                        )
                        return False

                grouped_id = getattr(message, "grouped_id", None)
                grouped_ids = []

                if grouped_id:
                    async for album_msg in self.client.iter_messages(
                        message.chat_id,
                        min_id=max(0, message.id - 10),
                        max_id=message.id + 10,
                        limit=30,
                    ):
                        if getattr(album_msg, "grouped_id", None) == grouped_id:
                            grouped_ids.append(album_msg.id)

                code.add_message(
                    chat_id=message.chat_id,
                    message_id=message.id,
                    grouped_ids=grouped_ids,
                )

                self.save_config()
                return True

        except Exception as e:
            logger.error(f"Error adding message to {code_name}: {e}")
            return False

    async def _apply_interval(self, code: Broadcast, code_name: str):
        """Применяет интервал между отправками."""
        min_interval, max_interval = code.normalize_interval()
        schedule_minutes = getattr(self, "last_schedule_delay", 60) / 60

        if min_interval < schedule_minutes:
            adjusted_min = schedule_minutes
            adjusted_max = max(schedule_minutes + 1, max_interval)
        else:
            adjusted_min = min_interval
            adjusted_max = max_interval

        interval = random.uniform(adjusted_min, adjusted_max) * 60
        last_broadcast = self.last_broadcast_time.get(code_name, 0)

        time_since_last_broadcast = time.time() - last_broadcast
        if time_since_last_broadcast < interval:
            sleep_time = interval - time_since_last_broadcast
            await asyncio.sleep(sleep_time)

    async def _handle_failed_chats(
        self, code_name: str, failed_chats: Set[int]
    ):
        """Обрабатывает чаты, в которые не удалось отправить сообщения."""
        if failed_chats:
            code = self.codes[code_name]
            code.chats -= failed_chats
            self.save_config()
            try:
                failed_chats_str = ", ".join(map(str, failed_chats))
                me = await self.client.get_me()
                await self.client.send_message(
                    me.id,
                    f"⚠️ Рассылка '{code_name}': Не удалось отправить сообщения в чаты: {failed_chats_str}",
                    schedule=datetime.now() + timedelta(seconds=60),
                )
            except Exception as e:
                logger.error(
                    f"Failed to send notification about failed chats for {code_name}: {e}"
                )

    async def _broadcast_loop(self, code_name: str):
        """Main broadcast loop."""
        while self._active:
            try:
                code = self.codes.get(code_name)
                if not code or not (code.chats and code.messages):
                    await asyncio.sleep(60)
                    continue

                await self._apply_interval(code, code_name)

                messages_to_send = []
                deleted_messages = []
                for msg_data in code.messages:
                    message = await self._fetch_messages(msg_data)
                    if message:
                        messages_to_send.append(message)
                    else:
                        deleted_messages.append(msg_data)

                # Удаляем недоступные сообщения
                if deleted_messages:
                    code.messages = [
                        m for m in code.messages if m not in deleted_messages
                    ]
                    self.save_config()

                if not messages_to_send:
                    await asyncio.sleep(60)
                    continue

                if not code.batch_mode:
                    msg_index = self.message_indices.get(code_name, 0)
                    messages_to_send = [
                        messages_to_send[msg_index % len(messages_to_send)]
                    ]
                    self.message_indices[code_name] = (msg_index + 1) % len(
                        messages_to_send
                    )

                failed_chats = await self._send_messages_to_chats(
                    code, code_name, messages_to_send
                )
                await self._handle_failed_chats(code_name, failed_chats)

                current_time = time.time()
                self.last_broadcast_time[code_name] = current_time
                try:
                    saved_times = self.db.get(
                        "broadcast", "last_broadcast_times", {}
                    )
                    saved_times[code_name] = current_time
                    self.db.set(
                        "broadcast", "last_broadcast_times", saved_times
                    )
                except Exception as e:
                    logger.error(f"Failed to save last broadcast time: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Critical error in broadcast loop {code_name}: {e}"
                )
                await asyncio.sleep(60)

    async def save_config(self):
        """Saves current configuration to database."""
        async with self._lock:
            try:
                config = {
                    "version": 1,
                    "last_save": int(time.time()),
                    "codes": {
                        name: {
                            "chats": list(code.chats),
                            "messages": code.messages,
                            "interval": list(code.interval),
                            "send_mode": code.send_mode,
                            "batch_mode": code.batch_mode,
                        }
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
                logger.error(f"Failed to save config: {e}")


@loader.tds
class BroadcastMod(loader.Module):
    """Модуль для рассылки сообщений."""

    strings = {
        "name": "Broadcast",
        "code_not_found": "❌ Код рассылки '{}' не найден",
        "success": "✅ Операция выполнена успешно: {}",
        "album_added": "✅ Альбом добавлен в рассылку '{}'",
        "single_added": "✅ Сообщение добавлено в рассылку '{}'",
        "specify_code": "⚠️ Укажите код рассылки",
        "reply_to_message": "⚠️ Ответьте на сообщение командой .addmsg кодовое_слово",
        "addmsg_usage": "ℹ️ Использование: .addmsg кодовое_слово",
        "all_stopped": "🛑 Все рассылки остановлены",
        "all_started": "▶️ Все рассылки запущены",
        "broadcast_stopped": "🛑 Рассылка '{}' остановлена",
        "broadcast_started": "▶️ Рассылка '{}' запущена",
        "broadcast_start_failed": "❌ Не удалось запустить рассылку '{}'",
        "cache_stats": "📊 Статистика кэша:\n• Размер кэша: {}\n• Всего сообщений: {}\n• Процент кэширования: {:.1f}%\n• TTL кэша: {} минут",
        "cache_stats_error": "❌ Ошибка при получении статистики кэша: {}",
        "chat_usage": "ℹ️ Использование: .chat код id_чата",
        "chat_id_numeric": "⚠️ ID чата должен быть числом",
        "chat_added": "✅ Чат {} добавлен в {}",
        "chat_removed": "✅ Чат {} удален из {}",
        "delcode_success": "✅ Код рассылки '{}' удален",
        "no_codes": "❌ Нет настроенных кодов рассылки",
        "interval_usage": "ℹ️ Использование: .interval кодовое_слово мин_минут макс_минут",
        "interval_numeric": "⚠️ Интервал должен быть числом",
        "interval_invalid_range": "⚠️ Некорректный интервал. Убедитесь, что минимум и максимум между 1 и 1440.",
        "interval_set": "✅ Интервал для '{}' установлен: {}-{} минут",
        "sendmode_usage": "ℹ️ Использование: .sendmode <код> <режим>\nРежимы: auto (по умолчанию), normal (обычная отправка), forward (форвард)",
        "sendmode_invalid": "⚠️ Неверный режим отправки. Доступные режимы: auto, normal, forward",
        "sendmode_set": "✅ Режим отправки для '{}' установлен: {}",
        "wat_status": "🔄 Автоматическое управление чатами {}",
        "no_messages_in_code": "❌ Нет сообщений в коде '{}'",
        "max_codes_reached": "⚠️ Достигнут лимит кодов рассылки ({})",
        "max_messages_reached": "⚠️ Достигнут лимит сообщений для кода '{}' ({})",
        "max_chats_reached": "⚠️ Достигнут лимит чатов для кода '{}' ({})",
        "delmsg_deleted": "✅ Сообщение удалено из рассылки",
        "delmsg_not_found": "❌ Сообщение не найдено",
        "delmsg_invalid_index": "❌ Неверный индекс сообщения",
        "delmsg_index_numeric": "⚠️ Индекс должен быть числом",
        "delmsg_index_usage": "ℹ️ Использование: .delmsg код [индекс] или ответьте на сообщение",
        "not_authorized": "❌ У вас нет доступа к использованию этого модуля",
        "auth_error": "❌ Ошибка проверки авторизации",
    }

    def __init__(self):
        self.manager: Optional[BroadcastManager] = None
        self._active = True
        self._cleanup_task = None
        self.wat_mode: bool = False
        self.me_id: Optional[int] = None
        self._periodic_task: Optional[asyncio.Task] = None

    async def client_ready(self, client, db):
        """Инициализация при запуске."""
        self.manager = BroadcastManager(client, db)
        self.me_id = (await client.get_me()).id

        # Загружаем конфигурацию
        config_data = db.get("broadcast", "config", {})
        self.manager._load_config_from_dict(config_data)

        self.wat_mode = self.manager.db.get("broadcast", "wat_mode", False)
        if self.wat_mode:
            self._periodic_task = asyncio.create_task(self._wat_loop())

        # Запускаем существующие рассылки
        broadcast_status = db.get("broadcast", "BroadcastStatus", {})
        for code_name in self.manager.codes:
            if broadcast_status.get(code_name):
                asyncio.create_task(self._start_broadcast(code_name))

        # Запускаем одну задачу очистки
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def _check_auth(self, message) -> bool:
        """Проверяет авторизацию пользователя."""
        try:
            user_id = message.sender_id
            if not self.manager.is_authorized(
                user_id
            ):  # Используем метод из manager
                await utils.answer(message, self.strings["not_authorized"])
                return False
            return True
        except Exception as e:
            logger.error(f"Authorization check error: {e}")
            await utils.answer(message, self.strings["auth_error"])
            return False

    async def _periodic_cleanup(self):
        """Периодическая очистка."""
        while self._active:
            try:
                # Очищаем просроченные записи из кэша сообщений
                await self.manager._message_cache.clean_expired()
                await asyncio.sleep(3600)  # Проверка каждый час
            except Exception as e:
                logger.error(f"Ошибка очистки кэша: {e}")
                await asyncio.sleep(60)  # При ошибке ждем минуту

    async def _start_broadcast(self, code_name: str) -> bool:
        """Запускает рассылку."""
        try:
            if code_name not in self.manager.broadcast_tasks:
                self.manager.broadcast_tasks[code_name] = asyncio.create_task(
                    self.manager._broadcast_loop(code_name)
                )
                broadcast_status = self.manager.db.get(
                    "broadcast", "BroadcastStatus", {}
                )
                broadcast_status[code_name] = True
                self.manager.db.set(
                    "broadcast", "BroadcastStatus", broadcast_status
                )
                return True
        except Exception as e:
            logger.error(f"Failed to start broadcast {code_name}: {e}")
        return False

    async def _stop_broadcast(self, code_name: str):
        """Останавливает рассылку."""
        if code_name in self.manager.broadcast_tasks:
            task = self.manager.broadcast_tasks.pop(code_name)
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            broadcast_status = self.manager.db.get(
                "broadcast", "BroadcastStatus", {}
            )
            broadcast_status.pop(code_name, None)
            self.manager.db.set(
                "broadcast", "BroadcastStatus", broadcast_status
            )

    async def _validate_code(
        self, message, code_name: Optional[str] = None
    ) -> Optional[str]:
        """Проверяет существование кода рассылки."""
        if code_name is None:
            args = utils.get_args(message)
            if not args:
                await utils.answer(message, self.strings["specify_code"])
                return None
            code_name = args[0]
        if code_name not in self.manager.codes:
            await utils.answer(
                message, self.strings["code_not_found"].format(code_name)
            )
            return None
        return code_name

    async def addmsg(self, message):
        """Добавляет сообщение в рассылку."""
        if not await self._check_auth(message):
            return

        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["addmsg_usage"])
            return

        reply = await message.get_reply_message()
        if not reply:
            await utils.answer(message, self.strings["reply_to_message"])
            return

        # Проверяем существование кода
        code_name = await self._validate_code(message, args)
        if not code_name:
            return

        success = await self.manager.add_message(code_name, reply)

        # Используем разные сообщения для альбомов и одиночных сообщений
        if success:
            if getattr(reply, "grouped_id", None):
                result_key = "album_added"
            else:
                result_key = "single_added"
        else:
            result_key = "max_messages_reached"

        await utils.answer(message, self.strings[result_key].format(code_name))

    async def batchcmd(self, message):
        """Переключает режим пакетной отправки для кода: .batch <код>"""
        if not await self._check_auth(message):
            return

        code_name = await self._validate_code(message)
        if not code_name:
            return

        code = self.manager.codes[code_name]
        if not code.messages:
            await utils.answer(
                message, self.strings["no_messages_in_code"].format(code_name)
            )
            return

        code.batch_mode = not code.batch_mode
        self.manager.save_config()

        status = "включен ✅" if code.batch_mode else "выключен ❌"
        await utils.answer(
            message, self.strings["batch_mode"].format(code_name, status)
        )

    async def broadcastcmd(self, message):
        """Управляет рассылкой: .broadcast <код> [start|stop]"""
        if not await self._check_auth(message):
            return

        args = utils.get_args(message)
        if not args:
            # Показываем статус всех рассылок
            status = []
            for code_name in self.manager.codes:
                is_active = code_name in self.manager.broadcast_tasks
                status.append(f"• {code_name}: {'🟢' if is_active else '🔴'}")

            if not status:
                await utils.answer(message, self.strings["no_codes"])
                return

            await utils.answer(message, "\n".join(status))
            return

        code_name = args[0]
        action = args[1].lower() if len(args) > 1 else "start"

        if code_name == "all":
            if action == "stop":
                for task in self.manager.broadcast_tasks.values():
                    task.cancel()
                self.manager.broadcast_tasks.clear()
                self.manager.db.set("broadcast", "BroadcastStatus", {})
                await utils.answer(message, self.strings["all_stopped"])
            else:
                for code in self.manager.codes:
                    await self._start_broadcast(code)
                await utils.answer(message, self.strings["all_started"])
            return

        if code_name not in self.manager.codes:
            await utils.answer(
                message, self.strings["code_not_found"].format(code_name)
            )
            return

        if action == "stop":
            if code_name in self.manager.broadcast_tasks:
                self.manager.broadcast_tasks[code_name].cancel()
                del self.manager.broadcast_tasks[code_name]
                broadcast_status = self.manager.db.get(
                    "broadcast", "BroadcastStatus", {}
                )
                broadcast_status.pop(code_name, None)
                self.manager.db.set(
                    "broadcast", "BroadcastStatus", broadcast_status
                )
                await utils.answer(
                    message, self.strings["broadcast_stopped"].format(code_name)
                )
        else:
            if await self._start_broadcast(code_name):
                await utils.answer(
                    message, self.strings["broadcast_started"].format(code_name)
                )
            else:
                await utils.answer(
                    message,
                    self.strings["broadcast_start_failed"].format(code_name),
                )

    async def cachescmd(self, message):
        """Показывает статистику кэша сообщений."""
        if not await self._check_auth(message):
            return

        try:
            cache_size = len(self.manager._message_cache.cache)
            total_messages = sum(
                len(code.messages) for code in self.manager.codes.values()
            )
            cached_percent = (
                (cache_size / total_messages * 100) if total_messages else 0
            )

            stats = (
                f"📊 Статистика кэша:\n"
                f"• Размер кэша: {cache_size}\n"
                f"• Всего сообщений: {total_messages}\n"
                f"• Процент кэширования: {cached_percent:.1f}%\n"
                f"• TTL кэша: {self.manager._message_cache.ttl // 60} минут"
            )

            await utils.answer(message, stats)
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            await utils.answer(
                message,
                self.strings["success"].format(
                    "Ошибка при получении статистики кэша"
                ),
            )

    async def chatcmd(self, message):
        """Добавляет/удаляет чат из рассылки."""
        if not await self._check_auth(message):
            return

        args = utils.get_args(message)
        if len(args) != 2:
            await utils.answer(message, self.strings["chat_usage"])
            return

        code_name, chat_id = args
        if not code_name in self.manager.codes:
            await utils.answer(
                message, self.strings["code_not_found"].format(code_name)
            )
            return

        try:
            chat_id = int(chat_id)
        except ValueError:
            await utils.answer(message, self.strings["chat_id_numeric"])
            return

        code = self.manager.codes[code_name]
        if chat_id in code.chats:
            code.chats.remove(chat_id)
            result_key = "chat_removed"
        else:
            if len(code.chats) >= self.manager.MAX_CHATS_PER_CODE:
                await utils.answer(
                    message,
                    self.strings["max_chats_reached"].format(
                        code_name, self.manager.MAX_CHATS_PER_CODE
                    ),
                )
                return
            code.chats.add(chat_id)
            result_key = "chat_added"

        self.manager.save_config()
        await utils.answer(
            message, self.strings[result_key].format(chat_id, code_name)
        )

    async def delcodecmd(self, message):
        """Удаляет код рассылки: .delcode <код>"""
        if not await self._check_auth(message):
            return

        code_name = await self._validate_code(message)
        if not code_name:
            return

        # Останавливаем рассылку если она активна
        await self._stop_broadcast(code_name)

        # Удаляем код из менеджера
        del self.manager.codes[code_name]

        # Очищаем связанные данные
        self.manager.message_indices.pop(code_name, None)
        self.manager.last_broadcast_time.pop(code_name, None)

        # Сохраняем обновленную конфигурацию
        self.manager.save_config()

        await utils.answer(
            message, self.strings["delcode_success"].format(code_name)
        )

    async def delmsgcmd(self, message):
        """Удаляет сообщение из рассылки: .delmsg <код> [индекс]"""
        if not await self._check_auth(message):
            return

        args = utils.get_args(message)
        if not args:
            await utils.answer(message, self.strings["delmsg_index_usage"])
            return

        code_name = args[0]
        if code_name not in self.manager.codes:
            await utils.answer(
                message, self.strings["code_not_found"].format(code_name)
            )
            return

        code = self.manager.codes[code_name]

        # Если есть ответ на сообщение
        reply = await message.get_reply_message()
        if reply:
            for i, msg in enumerate(code.messages):
                if msg["message_id"] == reply.id:
                    code.messages.pop(i)
                    self.manager.save_config()
                    await utils.answer(message, self.strings["delmsg_deleted"])
                    return
            await utils.answer(message, self.strings["delmsg_not_found"])
            return

        # Если указан индекс
        if len(args) < 2:
            await utils.answer(message, self.strings["delmsg_index_usage"])
            return

        try:
            index = int(args[1])
        except ValueError:
            await utils.answer(message, self.strings["delmsg_index_numeric"])
            return

        if not 0 <= index < len(code.messages):
            await utils.answer(message, self.strings["delmsg_invalid_index"])
            return

        code.messages.pop(index)
        self.manager.save_config()
        await utils.answer(message, self.strings["delmsg_deleted"])

    async def intervalcmd(self, message):
        """Устанавливает интервал рассылки: .interval <код> <мин_минут> <макс_минут>"""
        if not await self._check_auth(message):
            return

        args = utils.get_args(message)
        if len(args) != 3:
            await utils.answer(message, self.strings["interval_usage"])
            return

        code_name = await self._validate_code(message, args[0])
        if not code_name:
            return

        try:
            min_interval = int(args[1])
            max_interval = int(args[2])
        except ValueError:
            await utils.answer(message, self.strings["interval_numeric"])
            return

        if not (0 < min_interval < max_interval <= 1440):
            await utils.answer(message, self.strings["interval_invalid_range"])
            return

        code = self.manager.codes[code_name]
        code.interval = (min_interval, max_interval)
        self.manager.save_config()

        await utils.answer(
            message,
            self.strings["interval_set"].format(
                code_name, min_interval, max_interval
            ),
        )

    async def listcmd(self, message):
        """Показывает список активных кодов рассылки"""
        if not await self._check_auth(message):
            return

        if not self.manager.codes:
            await utils.answer(message, self.strings["no_codes"])
            return

        result = []
        for code_name, code in self.manager.codes.items():
            is_active = code_name in self.manager.broadcast_tasks
            status = "🟢" if is_active else "🔴"
            msg_count = len(code.messages)
            chat_count = len(code.chats)
            min_int, max_int = code.interval

            result.append(
                f"{status} <b>{code_name}</b>\n"
                f"├ Сообщений: {msg_count}\n"
                f"├ Чатов: {chat_count}\n"
                f"├ Интервал: {min_int}-{max_int} мин\n"
                f"├ Режим: {code.send_mode}\n"
                f"└ Пакетный режим: {'✅' if code.batch_mode else '❌'}"
            )

        await utils.answer(message, "\n\n".join(result))

    async def listmsgcmd(self, message):
        """Показывает сообщения в коде рассылки: .listmsg <код>"""
        if not await self._check_auth(message):
            return

        args = utils.get_args(message)
        if not args:
            await utils.answer(message, self.strings["specify_code"])
            return

        code_name = args[0]
        if code_name not in self.manager.codes:
            await utils.answer(
                message, self.strings["code_not_found"].format(code_name)
            )
            return

        code = self.manager.codes[code_name]
        if not code.messages:
            await utils.answer(
                message, self.strings["no_messages_in_code"].format(code_name)
            )
            return

        result = [f"📝 Сообщения в коде <b>{code_name}</b>:"]
        for i, msg in enumerate(code.messages):
            result.append(
                f"{i}. ID: {msg['message_id']} из чата {msg['chat_id']}"
                + (
                    f" (альбом: {len(msg['grouped_ids'])} фото)"
                    if msg["grouped_ids"]
                    else ""
                )
            )

        await utils.answer(message, "\n".join(result))

    async def sendmodecmd(self, message):
        """Устанавливает режим отправки: .sendmode <код> <режим>
        Режимы: auto (по умолчанию), normal (обычная отправка), forward (форвард)
        """
        if not await self._check_auth(message):
            return

        args = utils.get_args(message)
        if len(args) != 2:
            await utils.answer(message, self.strings["sendmode_usage"])
            return

        code_name = await self._validate_code(message, args[0])
        if not code_name:
            return

        mode = args[1].lower()
        valid_modes = {"auto", "normal", "forward"}

        if mode not in valid_modes:
            await utils.answer(message, self.strings["sendmode_invalid"])
            return

        code = self.manager.codes[code_name]
        code.send_mode = mode
        self.manager.save_config()

        await utils.answer(
            message, self.strings["sendmode_set"].format(code_name, mode)
        )

    async def watcmd(self, message):
        """Переключает режим автоматического управления чатами"""
        if not await self._check_auth(message):
            return

        self.wat_mode = not self.wat_mode

        if self.wat_mode and not self._periodic_task:
            self._periodic_task = asyncio.create_task(self._wat_loop())
        elif not self.wat_mode and self._periodic_task:
            self._periodic_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._periodic_task
            self._periodic_task = None

        self.manager.db.set("broadcast", "wat_mode", self.wat_mode)

        status = "включено ✅" if self.wat_mode else "выключено ❌"
        await utils.answer(message, self.strings["wat_status"].format(status))

    async def _wat_loop(self):
        """Цикл автоматического управления чатами."""
        while self.wat_mode:
            try:
                for code_name, code in self.manager.codes.items():
                    if not code.chats:
                        continue

                    # Проверяем каждый чат
                    for chat_id in list(code.chats):
                        try:
                            chat = await self.client.get_entity(chat_id)
                            participant = await self.client.get_permissions(
                                chat
                            )

                            if not participant.send_messages:
                                code.chats.remove(chat_id)
                                logger.warning(
                                    f"Removed chat {chat_id} from {code_name} (no send permission)"
                                )

                        except (
                            ChatWriteForbiddenError,
                            UserBannedInChannelError,
                            ChannelPrivateError,
                            ChatAdminRequiredError,
                        ):
                            code.chats.remove(chat_id)
                            logger.warning(
                                f"Removed chat {chat_id} from {code_name} (access error)"
                            )

                self.manager.save_config()
                await asyncio.sleep(3600)  # Проверка раз в час

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in WAT loop: {e}")
                await asyncio.sleep(300)  # При ошибке ждем 5 минут

    async def watcher(self, message: Message):
        """Автоматически добавляет чаты в рассылку."""
        if not self.wat_mode or not message:
            return
        try:
            if (
                message.sender_id != self.me_id
                or not message.text
                or not message.text.startswith("!")
            ):
                return

            parts = message.text.split()
            if len(parts) != 2:
                return

            code_name = parts[0][1:]  # Убираем ! из начала
            chat_id = message.chat_id

            # Проверяем существование кода
            if code_name not in self.manager.codes:
                return

            code = self.manager.codes[code_name]

            # Проверяем лимит чатов
            if len(code.chats) >= self.manager.MAX_CHATS_PER_CODE:
                return

            # Добавляем чат
            if chat_id not in code.chats:
                code.chats.add(chat_id)
                self.manager.save_config()

        except Exception as e:
            logger.error(f"Error in watcher: {e}")

    async def on_unload(self):
        """Cleanup on module unload."""
        self._active = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._cleanup_task

        if self._periodic_task:
            self._periodic_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._periodic_task

        for task in self.manager.broadcast_tasks.values():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
