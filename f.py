"""Author: kramiikk - Telegram: @kramiikk"""

import asyncio
import logging
import random
import time
from collections import deque, OrderedDict
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, List, Optional, Set, Tuple

from hikkatl.tl.types import Message
from hikkatl.errors import (
    ChatWriteForbiddenError,
    FloodWaitError,
    UserBannedInChannelError,
)

from .. import loader, utils

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        self._lock = asyncio.Lock()
        self.max_requests = max_requests
        self.time_window = time_window
        self.timestamps = deque(maxlen=max_requests * 2)

    async def acquire(self):
        async with self._lock:
            current_time = time.monotonic()

            while (
                self.timestamps
                and self.timestamps[0] <= current_time - self.time_window
            ):
                self.timestamps.popleft()
            if len(self.timestamps) >= self.max_requests:
                wait_time = self.timestamps[0] + self.time_window - current_time
                await asyncio.sleep(wait_time)
                current_time = time.monotonic()
                while (
                    self.timestamps
                    and self.timestamps[0] <= current_time - self.time_window
                ):
                    self.timestamps.popleft()
            self.timestamps.append(current_time)


class SimpleCache:
    def __init__(self, ttl: int = 7200, max_size: int = 20):
        self.cache = OrderedDict()
        self.ttl = ttl
        self.max_size = max_size
        self._lock = asyncio.Lock()

    async def clean_expired(self, force: bool = False):
        async with self._lock:
            if not force and len(self.cache) < self.max_size // 2:
                return
            current_time = time.time()
            expired = [
                k
                for k, (expire_time, _) in self.cache.items()
                if current_time > expire_time
            ]
            for key in expired:
                del self.cache[key]

    async def get(self, key: tuple):
        """Get a value from cache using a tuple key"""
        async with self._lock:
            entry = self.cache.get(key)
            if not entry:
                return None
            expire_time, value = entry
            if time.time() > expire_time:
                del self.cache[key]
                return None
            self.cache.move_to_end(key)
            return value

    async def set(self, key: tuple, value, expire: Optional[int] = None):
        """Set a value in cache using a tuple key"""
        async with self._lock:
            if expire is not None and expire <= 0:
                return
            ttl = expire if expire is not None else self.ttl
            expire_time = time.time() + ttl
            if key in self.cache:
                del self.cache[key]
            self.cache[key] = (expire_time, value)
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)

    async def start_auto_cleanup(self):
        """Запускает фоновую задачу для периодической очистки кэша"""
        while True:
            await self.clean_expired()
            await asyncio.sleep(self.ttl)


class BroadcastMod(loader.Module):
    """Модуль для массовой рассылки."""
    
    strings = {"name": "Broadcast"}

    def __init__(self):
        self.manager = None
        self._answered_users = set()
        self.answer_lock = asyncio.Lock()
        self._auto_config = {
            "enabled": True,
            "photo_url": "https://flawlessend.com/wp-content/uploads/2019/03/BEAUTY-LIFE-HACKS.jpg",
            "text": "Привет! Это автоответчик, скоро обязательно отвечу. 🌕",
        }

    @loader.command()
    async def b(self, message):
        """Команда для управления рассылкой."""
        await self.manager.handle_command(message)

    async def client_ready(self):
        """Инициализация модуля при загрузке"""
        self._auto_config = self.db.get(
            "auto_responder",
            "config",
            self._auto_config,
        )
        self.db.set("auto_responder", "config", self._auto_config)

        self.manager = BroadcastManager(self.client, self.db, self.tg_id)
        await self.manager.load_config()

        self.manager.adaptive_interval_task = asyncio.create_task(
            self.manager.start_adaptive_interval_adjustment()
        )
        self.manager.cache_cleanup_task = asyncio.create_task(
            self.manager._message_cache.start_auto_cleanup()
        )

        for code_name, code in self.manager.codes.items():
            if code._active and code.messages and code.chats:
                self.manager.broadcast_tasks[code_name] = asyncio.create_task(
                    self.manager._broadcast_loop(code_name)
                )

    async def on_unload(self):
        if not hasattr(self, "manager"):
            return
        self.manager._active = False

        tasks = [
            task for task in self.manager.broadcast_tasks.values() if not task.done()
        ]

        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        await self.manager._message_cache.clean_expired(force=True)

    async def watcher(self, message):
        """Автоматически отвечает на первое сообщение."""
        if not isinstance(message, Message):
            return
        if (
            self._auto_config.get("enabled", False)
            and message.is_private
            and message.sender
            and not message.sender.bot
            and message.sender_id not in self._answered_users
        ):
            await message.reply("xj")
            async with self.answer_lock:
                if message.sender_id not in self._answered_users:
                    try:
                        await message.client.send_file(
                            message.sender_id,
                            self._auto_config["photo_url"],
                            caption=self._auto_config["text"],
                        )
                        self._answered_users.add(message.sender_id)
                    except Exception as e:
                        logger.error(f"Auto-responder error: {e}")
        if not hasattr(self, "manager") or self.manager is None:
            return
        if self.manager.watcher_enabled:
            if message.text and message.text.startswith("💫"):
                if message.sender_id == self.tg_id:
                    parts = message.text.split()
                    code_name = parts[0][1:]
                    if code_name.isalnum():
                        chat_id = message.chat_id
                        code = self.manager.codes.get(code_name)
                        if code and len(code.chats) < 500 and chat_id not in code.chats:
                            code.chats.add(chat_id)
                            await self.manager.save_config()


@dataclass
class Broadcast:
    chats: Set[int] = field(default_factory=set)
    messages: Set[Tuple[int, int]] = field(default_factory=set)
    interval: Tuple[int, int] = (11, 13)
    _active: bool = field(default=False, init=False)
    original_interval: Tuple[int, int] = (11, 13)
    start_time: float = field(default_factory=time.time)
    total_sent: int = 0
    total_failed: int = 0
    groups: List[List[int]] = field(default_factory=list)
    last_group_chats: Set[int] = field(default_factory=set)

    def is_valid_interval(self) -> bool:
        min_val, max_val = self.interval
        return 0 < min_val < max_val <= 1440


class BroadcastManager:
    """Manages broadcast operations and state."""

    GLOBAL_LIMITER = RateLimiter(max_requests=20, time_window=60)

    def __init__(self, client, db, tg_id):
        self.client = client
        self.db = db
        self.codes: Dict[str, Broadcast] = {}
        self.broadcast_tasks: Dict[str, asyncio.Task] = {}
        self._message_cache = SimpleCache(ttl=7200, max_size=20)
        self._active = True
        self._lock = asyncio.Lock()
        self.watcher_enabled = False
        self.cache_cleanup_task = None
        self.tg_id = tg_id
        self.pause_event = asyncio.Event()
        self.pause_event.clear()
        self.last_flood_time = 0
        self.flood_wait_times = []
        self.adaptive_interval_task = None

    async def _broadcast_loop(self, code_name: str):
        code = self.codes.get(code_name)
        if not code or not code.messages or not code.chats:
            return
        while self._active and code._active and not self.pause_event.is_set():
            try:
                min_interval, max_interval = code.interval
                safe_min, safe_max = self.calculate_safe_interval(len(code.chats))

                if min_interval < safe_min:
                    code.interval = (safe_min, safe_max)
                    await self.save_config()
                    await self.client.send_message(
                        self.tg_id,
                        f"⚠️ Интервал для {code_name} автоматически скорректирован до {safe_min}-{safe_max} мин",
                    )
                total_seconds = random.uniform(min_interval, max_interval) * 60
                await asyncio.sleep(total_seconds)

                if code.last_group_chats != code.chats:
                    chats_list = list(code.chats)
                    random.shuffle(chats_list)
                    code.groups = [
                        chats_list[i : i + 20] for i in range(0, len(chats_list), 20)
                    ]
                    code.last_group_chats = code.chats.copy()
                groups = code.groups
                if not groups:
                    await asyncio.sleep(10)
                    continue
                total_groups = len(groups)
                msg_tuple = random.choice(tuple(code.messages))
                message = await self._fetch_message(*msg_tuple)
                if not message:
                    code.messages.remove(msg_tuple)
                    await self.save_config()
                    continue
                for group_index, group in enumerate(groups):
                    for chat_id in group:
                        send_start = time.monotonic()
                        result = await self._send_message(chat_id, message)

                        if result:
                            code.total_sent += 1
                        else:
                            code.total_failed += 1
                        await asyncio.sleep(
                            max(
                                0,
                                max(
                                    (
                                        total_seconds
                                        * (1 - 0.2)
                                        / total_groups
                                        / len(group)
                                        if group
                                        else 0
                                    ),
                                    2.0,
                                )
                                - time.monotonic()
                                - send_start,
                            )
                        )
                    if group_index < total_groups - 1:
                        time_between_groups = (
                            total_seconds * 0.2 / (total_groups - 1)
                            if total_groups > 1
                            else 0
                        )
                        await asyncio.sleep(time_between_groups)
            except Exception as e:
                logger.error(f"[{code_name}] Error in broadcast loop: {e}")
                await asyncio.sleep(10)

    async def _check_and_adjust_intervals(self):
        """Проверка условий для восстановления интервалов"""
        async with self._lock:
            if not self.flood_wait_times:
                return
            if (time.time() - self.last_flood_time) > 43200:
                for code in self.codes.values():
                    code.interval = code.original_interval
                    if not code.is_valid_interval():
                        code.interval = (11, 13)
                self.flood_wait_times = []
                await self.client.send_message(
                    self.tg_id,
                    "🔄 12 часов без ошибок! Интервалы восстановлены до исходных",
                )
            else:
                for code_name, code in self.codes.items():
                    new_min = max(1, int(code.interval[0] * 0.85))
                    new_max = min(
                        max(max(2, int(code.interval[1] * 0.85)), new_min + 1), 1440
                    )

                    code.interval = (new_min, new_max)
                    if not code.is_valid_interval():
                        code.interval = code.original_interval
                        logger.error(
                            f"Invalid interval for {code_name}, reset to original"
                        )
                    await self.client.send_message(
                        self.tg_id,
                        f"⏱ Автокоррекция интервалов для {code_name}: {new_min}-{new_max} минут",
                    )
            await self.save_config()

    async def _fetch_message(self, chat_id: int, message_id: int):
        """Fetch a message from cache or Telegram"""
        cache_key = (chat_id, message_id)

        cached = await self._message_cache.get(cache_key)
        if cached:
            return cached
        try:
            msg = await self.client.get_messages(entity=chat_id, ids=message_id)
            if msg:
                await self._message_cache.set(cache_key, msg)
                return msg
            logger.error(f"Сообщение {chat_id}:{message_id} не найдено")
            return None
        except ValueError as e:
            logger.error(f"Чат/сообщение не существует: {chat_id} {message_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении сообщения: {e}", exc_info=True)
            return None

    async def _generate_stats_report(self) -> str:
        """Генерация отчета: .br l"""
        if not self.codes:
            return "😶‍🌫️ Нет активных рассылок"
        report = ["🎩 <strong>Статистика рассылок</strong>"]
        for code_name, code in self.codes.items():
            status = "✨" if code._active else "🧊"
            runtime = str(timedelta(seconds=int(time.time() - code.start_time)))[:-3]

            report.append(
                f"\n▸ <code>{code_name}</code> {status} {runtime}\n"
                f"├ Сообщений: {len(code.messages)}\n"
                f"├ Чатов: {len(code.chats)}\n"
                f"├ Интервал: {code.interval[0]}-{code.interval[1]} мин\n"
                f"└ Отправлено: 🎐{code.total_sent} ⛓‍💥{code.total_failed}"
            )
        return "".join(report)

    async def _handle_add(self, message, code, code_name, args) -> str:
        """Добавление сообщения в рассылку: .br a [code]"""
        reply = await message.get_reply_message()
        if not reply:
            return "🫵 Ответьте на сообщение"
        if not code:
            code = Broadcast()
            self.codes[code_name] = code
        key = (reply.chat_id, reply.id)
        if key in code.messages:
            return "ℹ️ Сообщение уже добавлено"
        code.messages.add(key)
        await self._message_cache.set(key, reply)
        await self.save_config()

        return f"🍑 <code>{code_name}</code> | Сообщений: {len(code.messages)}"

    async def _handle_add_chat(self, message, code, code_name, args) -> str:
        """Добавление чата: .br ac [code] [@chat]"""
        target = args[2] if len(args) > 2 else message.chat_id
        chat_id = await self._parse_chat_identifier(target)

        if not chat_id:
            return "🫵 Неверный формат чата"
        if chat_id in code.chats:
            return "ℹ️ Чат уже добавлен"
        if len(code.chats) >= 500:
            return "🫵 Лимит 500 чатов"
        code.chats.add(chat_id)
        await self.save_config()
        return f"🪴 +1 чат | Всего: {len(code.chats)}"

    async def _handle_auto(self, args) -> str:
        """Обработчик команд автоответчика: .b auto [on/off/text/photo]"""
        auto_config = self.db.get("auto_responder", "config")

        if len(args) < 2:
            status = "вкл" if auto_config.get("enabled", False) else "выкл"
            return (
                f"🔧 <b>Настройки автоответчика</b>\n"
                f"• Статус: <code>{status}</code>\n"
                f"• Фото: <code>{auto_config['photo_url']}</code>\n"
                f"• Текст: <code>{auto_config['text']}</code>"
            )
        subcmd = args[1].lower()
        new_config = auto_config.copy()

        if subcmd == "on":
            new_config["enabled"] = True
            response = "✅ Автоответчик включен"
        elif subcmd == "off":
            new_config["enabled"] = False
            response = "✅ Автоответчик выключен"
        elif subcmd == "text":
            if len(args) < 3:
                return "🫵 Укажите текст"
            new_config["text"] = " ".join(args[2:])
            response = "✅ Текст автоответчика обновлен"
        elif subcmd == "photo":
            if len(args) < 3:
                return "🫵 Укажите URL фото"
            new_url = args[2]
            if not new_url.startswith(("http://", "https://")):
                return "❌ Неверный URL. Используйте http:// или https://"
            new_config["photo_url"] = new_url
            response = "✅ Ссылка на фото обновлена"
        else:
            return "❌ Неизвестная подкоманда. Доступно: on, off, text, photo"
        self.db.set("auto_responder", "config", new_config)
        return response

    async def _handle_delete(self, message, code, code_name, args) -> str:
        """Удаление рассылки: .br d [code]"""
        if code_name in self.broadcast_tasks:
            self.broadcast_tasks[code_name].cancel()
        del self.codes[code_name]
        await self.save_config()
        return f"🗑 {code_name} удалена"

    async def _handle_interval(self, message, code, code_name, args) -> str:
        """Установка интервала с проверкой безопасности: .br i [code] [min] [max]"""
        if len(args) < 4:
            return "🫵 Укажите мин/макс интервалы"
        try:
            requested_min = int(args[2])
            requested_max = int(args[3])
        except ValueError:
            return "🫵 Некорректные значения"
        if not (0 < requested_min < requested_max <= 1440):
            return "🫵 Интервал 1-1440 мин (min < max)"
        safe_min, safe_max = self.calculate_safe_interval(len(code.chats))

        if requested_min < safe_min:
            new_interval = (safe_min, safe_max)
            response = (
                f"⚠️ Для {len(code.chats)} чатов минимальный безопасный интервал: "
                f"{safe_min}-{safe_max} мин\n"
                f"Установлено: {safe_min}-{safe_max} мин"
            )
        else:
            new_interval = (requested_min, requested_max)
            response = f"⏱️ {code_name}: {requested_min}-{requested_max} мин"
        code.interval = new_interval
        code.original_interval = new_interval
        await self.save_config()

        return response

    async def _handle_flood_wait(self, e: FloodWaitError, chat_id: int):
        """Глобальная обработка FloodWait с остановкой всех рассылок"""
        async with self._lock:
            if self.pause_event.is_set():
                return False
            self.pause_event.set()
            avg_wait = (
                sum(self.flood_wait_times[-3:]) / len(self.flood_wait_times[-3:])
                if self.flood_wait_times
                else 0
            )
            wait_time = min(max(e.seconds + 15, avg_wait * 1.5), 7200)

            self.last_flood_time = time.time()
            self.flood_wait_times.append(wait_time)
            if len(self.flood_wait_times) > 10:
                self.flood_wait_times = self.flood_wait_times[-10:]
            await self.client.send_message(
                self.tg_id,
                f"🚨 Обнаружен FloodWait {e.seconds}s! Все рассылки приостановлены на {wait_time}s",
            )
            logger.error(
                f"🚨 FloodWait {e.seconds} сек. в чате {chat_id}. Среднее время ожидания: {avg_wait:.1f} сек. "
                f"Всего FloodWait за последние 12 часов: {len(self.flood_wait_times)}"
            )

            tasks = list(self.broadcast_tasks.values())
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(wait_time)

            self.pause_event.clear()
            await self._restart_all_broadcasts()

            await self.client.send_message(
                self.tg_id,
                "🐈 Глобальная пауза снята. Рассылки возобновлены",
            )

            for code in self.codes.values():
                code.interval = (
                    min(code.interval[0] * 2, 120),
                    min(code.interval[1] * 2, 240),
                )
                if not hasattr(code, "original_interval"):
                    code.original_interval = code.interval
            await self.save_config()

    async def _handle_permanent_error(self, chat_id: int):
        async with self._lock:
            for code in self.codes.values():
                code.chats.discard(chat_id)
                logger.error(f"🚫 Ошибка в чате {chat_id}. Удален из рассылок.")
        await self.save_config()

    async def _handle_remove(self, message, code, code_name, args) -> str:
        """Удаление сообщения: .br r [code]"""
        reply = await message.get_reply_message()
        if not reply:
            return "🫵 Ответьте на сообщение"
        key = (reply.chat_id, reply.id)
        if key not in code.messages:
            return "🫵 Сообщение не найдено"
        code.messages.remove(key)
        await self._message_cache.set(key, None)
        await self.save_config()
        return f"🐀 Удалено | Осталось: {len(code.messages)}"

    async def _handle_remove_chat(self, message, code, code_name, args) -> str:
        """Удаление чата: .br rc [code] [@chat]"""
        target = args[2] if len(args) > 2 else message.chat_id
        chat_id = await self._parse_chat_identifier(target)

        if not chat_id:
            return "🫵 Неверный формат чата"
        if chat_id not in code.chats:
            return "ℹ️ Чат не найден"
        code.chats.remove(chat_id)
        await self.save_config()
        return f"🐲 -1 чат | Осталось: {len(code.chats)}"

    async def _handle_start(self, message, code, code_name, args) -> str:
        """Запуск рассылки: .br s [code]"""
        if not code.messages:
            return "🫵 Нет сообщений для отправки"
        if not code.chats:
            return "🫵 Нет чатов для рассылки"
        if code._active:
            return "ℹ️ Рассылка уже активна"
        code._active = True
        code.start_time = time.time()
        self.broadcast_tasks[code_name] = asyncio.create_task(
            self._broadcast_loop(code_name)
        )

        await self.save_config()

        return f"🚀 {code_name} запущена | Чатов: {len(code.chats)}"

    async def _handle_stop(self, message, code, code_name, args) -> str:
        """Остановка рассылки: .br x [code]"""
        if not code._active:
            return "ℹ️ Рассылка не активна"
        code._active = False
        if code_name in self.broadcast_tasks:
            self.broadcast_tasks[code_name].cancel()
        await self.save_config()

        return f"🧊 {code_name} остановлена"

    async def _parse_chat_identifier(self, identifier) -> Optional[int]:
        """Парсинг идентификатора чата"""
        try:
            if isinstance(identifier, int) or str(identifier).lstrip("-").isdigit():
                return int(identifier)
            entity = await self.client.get_entity(identifier)
            return entity.id
        except Exception:
            return None

    async def _restart_all_broadcasts(self):
        async with self._lock:
            for code_name, code in self.codes.items():
                if code._active:
                    if task := self.broadcast_tasks.get(code_name):
                        if not task.done() and not task.cancelled():
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass
                    self.broadcast_tasks[code_name] = asyncio.create_task(
                        self._broadcast_loop(code_name)
                    )
                    logger.info(f"Перезапуск рассылки: {code_name}")

    async def _send_message(self, chat_id: int, msg) -> bool:
        if not self.pause_event.is_set():
            try:
                await self.GLOBAL_LIMITER.acquire()
                await self.client.forward_messages(
                    entity=chat_id, messages=msg.id, from_peer=msg.chat_id
                )
                return True
            except FloodWaitError as e:
                await self._handle_flood_wait(e, chat_id)
            except (ChatWriteForbiddenError, UserBannedInChannelError):
                await self._handle_permanent_error(chat_id)
            except Exception as e:
                logger.error(f"In {chat_id}: {repr(e)}")
        return False

    def _toggle_watcher(self, args) -> str:
        """Переключение авто-добавления: .br w [on/off]"""
        if len(args) < 2:
            return f"🔍 Автодобавление: {'ON' if self.watcher_enabled else 'OFF'}"
        self.watcher_enabled = args[1].lower() == "on"
        return f"🐺 Автодобавление: {'ВКЛ' if self.watcher_enabled else 'ВЫКЛ'}"

    async def _validate_loaded_data(self):
        """Базовая проверка загруженных данных"""
        for code_name, code in self.codes.items():
            if code._active and (not code.messages or not code.chats):
                logger.info(f"Отключение {code_name}: нет сообщений/чатов")
                code._active = False
            if not (0 < code.interval[0] < code.interval[1] <= 1440):
                logger.info(f"Сброс интервала для {code_name}")
                code.interval = (11, 13)
                code.original_interval = (11, 13)

    def calculate_safe_interval(self, total_chats: int) -> Tuple[int, int]:
        """Рассчитывает безопасный интервал на основе количества чатов"""
        min_interval = max(
            5, int((20 * 2.0 * ((total_chats + 20 - 1) // 20)) / (1 - 0.2) / 60) + 1
        )
        return min_interval, min_interval + max(1, min_interval // 15)

    async def handle_command(self, message):
        """Обработчик команд управления рассылкой"""
        response = None
        args = message.text.split()[1:]

        if not args:
            response = "🫵 Недостаточно аргументов"
        else:
            action = args[0].lower()

            if action == "l":
                response = await self._generate_stats_report()
            elif action == "w":
                response = self._toggle_watcher(args)
            elif action == "auto":
                response = await self._handle_auto(args)
            else:
                code_name = args[1] if len(args) > 1 else None
                if not code_name:
                    response = "🫵 Укажите код рассылки"
                else:
                    code = self.codes.get(code_name)
                    handler_map = {
                        "a": self._handle_add,
                        "d": self._handle_delete,
                        "r": self._handle_remove,
                        "ac": self._handle_add_chat,
                        "rc": self._handle_remove_chat,
                        "i": self._handle_interval,
                        "s": self._handle_start,
                        "x": self._handle_stop,
                    }

                    if action not in handler_map:
                        response = "🫵 Неизвестная команда"
                    elif action != "a" and not code:
                        response = f"🫵 Рассылка {code_name} не найдена"
                    else:
                        try:
                            handler = handler_map[action]
                            result = await handler(message, code, code_name, args)
                            response = result
                        except Exception as e:
                            logger.error(f"Command error: {e}")
                            response = f"🚨 Ошибка: {str(e)}"
        await utils.answer(message, response)

    async def load_config(self):
        """Загрузка конфигурации с базовой валидацией"""
        try:
            raw_config = self.db.get("broadcast", "config") or {}

            for code_name, code_data in raw_config.get("codes", {}).items():
                try:
                    code = Broadcast(
                        chats=set(map(int, code_data.get("chats", []))),
                        messages={
                            (int(msg["chat_id"]), int(msg["message_id"]))
                            for msg in code_data.get("messages", [])
                        },
                        interval=tuple(map(int, code_data.get("interval", (11, 13)))),
                        original_interval=tuple(
                            map(int, code_data.get("original_interval", (11, 13)))
                        ),
                    )

                    code.groups = [
                        [int(chat) for chat in group if int(chat) in code.chats]
                        for group in code_data.get("groups", [])
                    ]
                    code.last_group_chats = set(
                        map(int, code_data.get("last_group_chats", []))
                    )

                    status = code_data.get("status", {})
                    code._active = status.get("active", False)
                    code.start_time = float(status.get("start_time", time.time()))
                    code.total_sent = int(status.get("total_sent", 0))
                    code.total_failed = int(status.get("total_failed", 0))

                    self.codes[code_name] = code
                except Exception as e:
                    logger.error(f"Ошибка загрузки {code_name}: {str(e)}")
                    continue
            await self._validate_loaded_data()
        except Exception as e:
            logger.error(f"Критическая ошибка загрузки: {str(e)}", exc_info=True)
            self.codes = {}

    async def save_config(self):
        """Сохранение конфигурации"""
        try:
            config = {
                "codes": {
                    name: {
                        "chats": list(code.chats),
                        "messages": [
                            {"chat_id": cid, "message_id": mid}
                            for cid, mid in code.messages
                        ],
                        "interval": list(code.interval),
                        "original_interval": list(code.original_interval),
                        "status": {
                            "active": code._active,
                            "start_time": code.start_time,
                            "total_sent": code.total_sent,
                            "total_failed": code.total_failed,
                        },
                        "groups": code.groups,
                        "last_group_chats": list(code.last_group_chats),
                    }
                    for name, code in self.codes.items()
                }
            }
            self.db.set("broadcast", "config", config)
        except Exception as e:
            logger.error(f"Ошибка сохранения: {str(e)}")

    async def start_adaptive_interval_adjustment(self):
        """Фоновая задача для адаптации интервалов"""
        while self._active:
            try:
                await asyncio.sleep(3600)
                await self._check_and_adjust_intervals()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в адаптивной регулировке: {e}", exc_info=True)
