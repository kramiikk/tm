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
    _last_message_index: int = field(default=0, init=False)
    _active: bool = field(default=True, init=False)

    def add_message(
        self, chat_id: int, message_id: int, grouped_ids: List[int] = None
    ) -> bool:
        """Добавляет сообщение с проверкой дубликатов"""
        message_data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "grouped_ids": grouped_ids or [],
        }
        
        # Проверка на дубликаты
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
            m for m in self.messages 
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
            "batch_mode": self.batch_mode
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Broadcast':
        """Создает объект из словаря"""
        return cls(
            chats=set(data.get("chats", [])),
            messages=data.get("messages", []),
            interval=tuple(data.get("interval", (10, 13))),
            send_mode=data.get("send_mode", "auto"),
            batch_mode=data.get("batch_mode", False)
        )


class SimpleCache:
    def __init__(self, ttl: int = 3600, max_size: int = 50):
        self.cache = OrderedDict()
        self.ttl = ttl
        self.max_size = max_size
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 минут

    async def get(self, key):
        async with self._lock:
            await self._maybe_cleanup()
            if key not in self.cache:
                return None
            timestamp, value = self.cache[key]
            if time.time() - timestamp > self.ttl:
                del self.cache[key]
                return None
            # Обновляем позицию в OrderedDict
            self.cache.move_to_end(key)
            return value

    async def set(self, key, value):
        async with self._lock:
            await self._maybe_cleanup()
            if len(self.cache) >= self.max_size:
                # Удаляем 25% старых записей при достижении лимита
                to_remove = max(1, len(self.cache) // 4)
                for _ in range(to_remove):
                    self.cache.popitem(last=False)
            self.cache[key] = (time.time(), value)

    async def _maybe_cleanup(self):
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            await self.clean_expired()
            self._last_cleanup = current_time

    async def clean_expired(self):
        async with self._lock:
            current_time = time.time()
            self.cache = OrderedDict(
                (k, v) for k, v in self.cache.items() 
                if current_time - v[0] <= self.ttl
            )


class BroadcastManager:
    """Manages broadcast operations and state."""

    MAX_MESSAGES_PER_CODE = 100
    MAX_CHATS_PER_CODE = 1000
    MAX_CODES = 50

    def __init__(self, client, db, json_path: str = "/root/Heroku/loll.json"):
        self.client = client
        self.db = db
        self._authorized_users = self._load_authorized_users(json_path)
        self.codes: Dict[str, Broadcast] = {}
        self.broadcast_tasks: Dict[str, asyncio.Task] = {}
        self.last_broadcast_time: Dict[str, float] = {}
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
        key = (msg_data["chat_id"], msg_data["message_id"])
        
        try:
            # Проверяем кеш первым делом
            cached = await self._message_cache.get(key)
            if cached:
                return cached

            message_ids = msg_data.get("grouped_ids", [msg_data["message_id"]])
            
            # Оптимизация: получаем сообщения пакетами по 100
            messages = []
            for i in range(0, len(message_ids), 100):
                batch = message_ids[i:i + 100]
                batch_messages = await self.client.get_messages(
                    msg_data["chat_id"],
                    ids=batch
                )
                messages.extend(m for m in batch_messages if m)

            if not messages:
                logger.warning(
                    f"Не удалось получить сообщение {msg_data['message_id']} из чата {msg_data['chat_id']}"
                )
                return None

            # Проверка размера медиа с ранним возвратом
            for msg in messages:
                if hasattr(msg, 'media') and msg.media:
                    if hasattr(msg.media, 'document') and hasattr(msg.media.document, 'size'):
                        if msg.media.document.size > 10 * 1024 * 1024:  # 10MB
                            logger.warning(
                                f"Медиа в сообщении {msg.id} превышает лимит размера (10MB)"
                            )
                            return None

            # Сортируем только если это действительно нужно
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

    def _create_broadcast_code_from_dict(self, code_data: dict) -> Broadcast:
        """Создает объект Broadcast из словаря с валидацией."""
        if not isinstance(code_data, dict):
            raise ValueError("Invalid code data format")

        try:
            return Broadcast.from_dict(code_data)
        except Exception as e:
            logger.error(f"Error creating broadcast from dict: {e}")
            return Broadcast()

    def _load_config_from_dict(self, data: dict):
        """Загружает конфигурацию рассылки из словаря."""
        try:
            for code_name, code_data in data.get("codes", {}).items():
                try:
                    broadcast = self._create_broadcast_code_from_dict(code_data)
                    self.codes[code_name] = broadcast
                except Exception as e:
                    logger.error(f"Error loading broadcast code {code_name}: {e}")

            # Загружаем времена последних рассылок
            saved_times = self.db.get("broadcast", "last_broadcast_times", {})
            self.last_broadcast_time.update(
                {
                    code: float(time_)
                    for code, time_ in saved_times.items()
                    if isinstance(time_, (int, float))
                }
            )
        except Exception as e:
            logger.error(f"Error loading config: {e}")

    async def save_config(self):
        """Сохраняет текущую конфигурацию в базу данных."""
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
                logger.error(f"Failed to save config: {e}")

    async def add_message(self, code_name: str, message) -> bool:
        """Добавляет сообщение в список рассылки с валидацией."""
        try:
            async with self._lock:
                if (
                    len(self.codes) >= self.MAX_CODES
                    and code_name not in self.codes
                ):
                    logger.warning(f"Max codes limit ({self.MAX_CODES}) reached")
                    return False

                if code_name not in self.codes:
                    self.codes[code_name] = Broadcast()

                code = self.codes[code_name]

                if len(code.messages) >= self.MAX_MESSAGES_PER_CODE:
                    logger.warning(
                        f"Max messages per code ({self.MAX_MESSAGES_PER_CODE}) reached"
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

                success = code.add_message(
                    chat_id=message.chat_id,
                    message_id=message.id,
                    grouped_ids=grouped_ids,
                )

                if success:
                    await self.save_config()
                return success

        except Exception as e:
            logger.error(f"Error adding message to {code_name}: {e}")
            return False

    async def _send_messages_to_chats(
        self,
        code: Broadcast,
        code_name: str,
        messages_to_send: List[Union[Message, List[Message]]],
    ) -> Set[int]:
        """Отправляет сообщения в чаты с оптимизированной обработкой ошибок."""
        failed_chats = set()
        success_count = 0
        error_counts = {}
        
        async def send_to_chat(chat_id: int):
            nonlocal success_count
            
            if not self._active or not code._active:
                return
                
            try:
                schedule_time = None
                if code.send_mode == "schedule":
                    delay = code.get_random_delay()
                    schedule_time = datetime.now() + timedelta(seconds=delay)

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
                
            except (ChatWriteForbiddenError, UserBannedInChannelError,
                   ChannelPrivateError, ChatAdminRequiredError) as e:
                error_type = type(e).__name__
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
                failed_chats.add(chat_id)
                logger.warning(f"Ошибка доступа для чата {chat_id}: {str(e)}")
                
            except Exception as e:
                error_type = type(e).__name__
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
                failed_chats.add(chat_id)
                logger.error(f"Непредвиденная ошибка для чата {chat_id}: {str(e)}")

        # Отправляем сообщения пакетами для контроля нагрузки
        batch_size = 10
        chats = list(code.chats)
        random.shuffle(chats)  # Рандомизируем порядок отправки
        
        for i in range(0, len(chats), batch_size):
            if not self._active or not code._active:
                break
                
            batch = chats[i:i + batch_size]
            tasks = [send_to_chat(chat_id) for chat_id in batch]
            await asyncio.gather(*tasks)
            
            # Небольшая пауза между пакетами
            await asyncio.sleep(2)

        # Логируем статистику
        total_chats = len(code.chats)
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

    async def _apply_interval(self, code: Broadcast, code_name: str):
        """Применяет интервал между отправками с адаптивной задержкой."""
        try:
            min_interval, max_interval = code.normalize_interval()
            last_broadcast = self.last_broadcast_time.get(code_name, 0)
            current_time = time.time()
            
            # Рассчитываем базовый интервал
            base_interval = code.get_random_delay()
            
            # Адаптивная корректировка интервала на основе нагрузки
            active_broadcasts = len([t for t in self.broadcast_tasks.values() if not t.done()])
            if active_broadcasts > 5:  # Если много активных рассылок
                base_interval *= 1.2  # Увеличиваем интервал
            
            # Проверяем время с последней рассылки
            time_since_last = current_time - last_broadcast
            if time_since_last < base_interval:
                sleep_time = base_interval - time_since_last
                await asyncio.sleep(sleep_time)
                
        except Exception as e:
            logger.error(f"Ошибка применения интервала для {code_name}: {e}")
            await asyncio.sleep(60)  # Fallback интервал

    async def _handle_failed_chats(
        self, code_name: str, failed_chats: Set[int]
    ):
        """Обрабатывает чаты, в которые не удалось отправить сообщения."""
        if not failed_chats:
            return
            
        try:
            async with self._lock:
                code = self.codes[code_name]
                # Удаляем проблемные чаты
                code.chats -= failed_chats
                await self.save_config()

                # Группируем чаты для уведомления
                chat_groups = []
                current_group = []
                
                for chat_id in failed_chats:
                    current_group.append(str(chat_id))
                    if len(current_group) >= 50:  # Ограничиваем размер группы
                        chat_groups.append(", ".join(current_group))
                        current_group = []
                
                if current_group:
                    chat_groups.append(", ".join(current_group))

                # Отправляем уведомления частями
                me = await self.client.get_me()
                base_message = f"⚠️ Рассылка '{code_name}': Не удалось отправить сообщения в чаты:\n"
                
                for group in chat_groups:
                    message = base_message + group
                    try:
                        await self.client.send_message(
                            me.id,
                            message,
                            schedule=datetime.now() + timedelta(seconds=60)
                        )
                        await asyncio.sleep(1)  # Пауза между отправками
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления: {e}")

        except Exception as e:
            logger.error(f"Ошибка обработки неудачных чатов для {code_name}: {e}")

    @staticmethod
    def _chunk_messages(messages: List[Union[Message, List[Message]]], chunk_size: int = 10) -> List[List[Union[Message, List[Message]]]]:
        """Разбивает список сообщений на части оптимального размера."""
        return [messages[i:i + chunk_size] for i in range(0, len(messages), chunk_size)]

    async def _process_message_batch(self, code: Broadcast, messages: List[dict]) -> Tuple[List[Union[Message, List[Message]]], List[dict]]:
        """Обрабатывает пакет сообщений с оптимизированной загрузкой."""
        messages_to_send = []
        deleted_messages = []
        
        results = await asyncio.gather(
            *[self._fetch_messages(msg) for msg in messages],
            return_exceptions=True
        )
        
        for msg_data, result in zip(messages, results):
            if isinstance(result, Exception):
                logger.error(f"Ошибка загрузки сообщения {msg_data['message_id']}: {result}")
                deleted_messages.append(msg_data)
            elif result:
                messages_to_send.append(result)
            else:
                deleted_messages.append(msg_data)
                
        return messages_to_send, deleted_messages

    async def _broadcast_loop(self, code_name: str):
        """Main broadcast loop."""
        retry_count = 0
        max_retries = 3
        
        while self._active:
            try:
                code = self.codes.get(code_name)
                if not code or not code._active:
                    await asyncio.sleep(60)
                    continue

                if not code.chats or not code.messages:
                    await asyncio.sleep(60)
                    continue

                await self._apply_interval(code, code_name)

                # Получаем сообщения пакетами для оптимизации памяти
                messages_to_send = []
                deleted_messages = []
                batch_size = 20  # Оптимальный размер пакета
                
                for i in range(0, len(code.messages), batch_size):
                    if not self._active or not code._active:
                        break
                        
                    batch = code.messages[i:i + batch_size]
                    batch_messages = await asyncio.gather(
                        *[self._fetch_messages(msg) for msg in batch],
                        return_exceptions=True
                    )
                    
                    for msg_data, result in zip(batch, batch_messages):
                        if isinstance(result, Exception):
                            logger.error(f"Ошибка получения сообщения: {result}")
                            deleted_messages.append(msg_data)
                        elif result:
                            messages_to_send.append(result)
                        else:
                            deleted_messages.append(msg_data)

                # Очищаем недоступные сообщения
                if deleted_messages:
                    code.messages = [
                        m for m in code.messages 
                        if m not in deleted_messages
                    ]
                    await self.save_config()
                    
                    if not code.messages:  # Если все сообщения удалены
                        logger.warning(f"Все сообщения в коде {code_name} недоступны")
                        continue

                if not messages_to_send:
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.error(f"Достигнут лимит попыток получения сообщений для {code_name}")
                        await asyncio.sleep(300)  # Длительная пауза после серии неудач
                        retry_count = 0
                    else:
                        await asyncio.sleep(60)
                    continue

                retry_count = 0  # Сбрасываем счетчик после успешного получения сообщений

                # Выбираем сообщения для отправки
                if not code.batch_mode:
                    next_index = code.get_next_message_index()
                    messages_to_send = [messages_to_send[next_index % len(messages_to_send)]]

                # Отправляем сообщения и обрабатываем ошибки
                failed_chats = await self._send_messages_to_chats(
                    code, code_name, messages_to_send
                )

                if failed_chats:
                    await self._handle_failed_chats(code_name, failed_chats)

                # Обновляем время последней рассылки
                current_time = time.time()
                self.last_broadcast_time[code_name] = current_time
                
                try:
                    async with self._lock:
                        saved_times = self.db.get("broadcast", "last_broadcast_times", {})
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
                if retry_count >= max_retries:
                    logger.error(f"Достигнут лимит попыток выполнения рассылки {code_name}")
                    await asyncio.sleep(300)
                    retry_count = 0
                else:
                    await asyncio.sleep(60)

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
            if code_name not in self.codes:
                return

            code = self.codes[code_name]

            # Проверяем лимит чатов
            if len(code.chats) >= self.MAX_CHATS_PER_CODE:
                return

            # Добавляем чат
            if chat_id not in code.chats:
                code.chats.add(chat_id)
                self.save_config()

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

        for task in self.broadcast_tasks.values():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
