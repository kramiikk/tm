""" Author: @kramiikk """

import asyncio
import json
import logging
import random
import time
from contextlib import suppress
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Union
from datetime import datetime, timedelta
from ratelimit import limits, sleep_and_retry

from telethon.errors import ChatWriteForbiddenError, UserBannedInChannelError
from telethon.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)


class AuthorizationManager:
    """Manages user authorization for the broadcast module."""

    def __init__(self, json_path: str = "/root/Heroku/loll.json"):
        self.json_path = json_path
        self._authorized_users = self._load_authorized_users()

    def _load_authorized_users(self) -> Set[int]:
        """Load authorized user IDs from JSON file."""
        try:
            with open(self.json_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                user_ids = {
                    int(user_id) for user_id in data.get("authorized_users", [])
                }
                return user_ids
        except FileNotFoundError:
            logger.error(f"Authorization file not found: {self.json_path}")
        except json.JSONDecodeError:
            logger.error(
                f"Invalid JSON in authorization file: {self.json_path}"
            )
        except Exception as e:
            logger.error(f"Error loading authorized users: {e}")
        return {7175372340}

    def is_authorized(self, user_id: int) -> bool:
        """Check if a user is authorized to use the module."""
        authorized = user_id in self._authorized_users
        logger.debug(f"Authorization check for user {user_id}: {authorized}")
        return authorized


@dataclass(frozen=True)
class BroadcastMessage:
    """Message data for broadcasting."""

    chat_id: int
    message_id: int
    grouped_id: Optional[int] = None
    album_ids: Tuple[int, ...] = field(default_factory=tuple)


@dataclass
class BroadcastCode:
    """Broadcast settings container."""

    chats: Set[int] = field(default_factory=set)
    messages: List[BroadcastMessage] = field(default_factory=list)
    interval: Tuple[int, int] = field(default_factory=lambda: (10, 13))
    send_mode: str = "auto"
    created_at: float = field(default_factory=time.time)
    batch_mode: bool = False

    def is_valid_interval(self) -> bool:
        min_val, max_val = self.interval
        return (
            isinstance(min_val, int)
            and isinstance(max_val, int)
            and 0 < min_val < max_val <= 1440
        )

    def normalize_interval(self) -> Tuple[int, int]:
        return self.interval if self.is_valid_interval() else (10, 13)


class BroadcastManager:
    """Manages broadcast operations and state."""

    MAX_MESSAGES_PER_CODE = 100
    MAX_CHATS_PER_CODE = 1000
    MAX_CODES = 50

    def __init__(self, client, db):
        self.client = client
        self.db = db
        self.codes: OrderedDict[str, BroadcastCode] = OrderedDict()
        self.broadcast_tasks: Dict[str, asyncio.Task] = {}
        self.message_indices: Dict[str, int] = {}
        self.last_broadcast_time: Dict[str, float] = {}
        self._message_cache = MessageCache(ttl=7200, max_size=50)
        self._active = True
        self._lock = asyncio.Lock()

    def _load_last_broadcast_times(self):
        """Загружает времена последних рассылок из БД."""
        try:
            saved_times = self.db.get("broadcast", "last_broadcast_times", {})
            self.last_broadcast_time.update(
                {
                    code: float(time_)
                    for code, time_ in saved_times.items()
                    if isinstance(time_, (int, float))
                }
            )
        except Exception as e:
            logger.error(f"Failed to load last broadcast times: {e}")

    def _save_last_broadcast_time(self, code_name: str, timestamp: float):
        """Сохраняет время последней рассылки в БД."""
        try:
            saved_times = self.db.get("broadcast", "last_broadcast_times", {})
            saved_times[code_name] = timestamp
            self.db.set("broadcast", "last_broadcast_times", saved_times)
        except Exception as e:
            logger.error(f"Failed to save last broadcast time: {e}")

    def _create_broadcast_code_from_dict(
        self, code_data: dict
    ) -> BroadcastCode:
        """Creates BroadcastCode object from dictionary."""
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
                    BroadcastMessage(
                        chat_id=msg_data["chat_id"],
                        message_id=msg_data["message_id"],
                        grouped_id=msg_data.get("grouped_id"),
                        album_ids=tuple(msg_data.get("album_ids", [])),
                    )
                )
            except (KeyError, TypeError):
                logger.error(f"Invalid message data: {msg_data}")
                continue

        interval = tuple(code_data.get("interval", (10, 13)))
        send_mode = code_data.get("send_mode", "auto")

        return BroadcastCode(
            chats=chats,
            messages=messages,
            interval=interval,
            send_mode=send_mode,
        )

    def _load_config_from_dict(self, data: dict):
        """Loads broadcast configuration from dictionary."""

        for code_name, code_data in data.get("codes", {}).items():
            try:
                broadcast_code = self._create_broadcast_code_from_dict(
                    code_data
                )
                broadcast_code.batch_mode = code_data.get("batch_mode", False)
                self.codes[code_name] = broadcast_code
            except Exception as e:
                logger.error(f"Error loading broadcast code {code_name}: {e}")

        self._load_last_broadcast_times()

    async def _fetch_messages(
        self, msg_data: BroadcastMessage, max_size: int = 10 * 1024 * 1024
    ) -> Optional[Union[Message, List[Message]]]:
        """Fetch messages with media size limitation."""
        try:
            cached = await self._message_cache.get(
                (msg_data.chat_id, msg_data.message_id)
            )
            if cached:
                return cached

            message_ids = (
                list(msg_data.album_ids)
                if msg_data.grouped_id
                else [msg_data.message_id]
            )
            messages = await self.client.get_messages(
                msg_data.chat_id, ids=message_ids
            )

            if not messages:
                logger.warning(
                    f"Проблема с сообщением {msg_data.message_id} из {msg_data.chat_id}"
                )
                return None

            valid_messages = [msg for msg in messages if msg]

            for msg in valid_messages:
                if msg.media and hasattr(msg.media, "document") and hasattr(msg.media.document, "size"):
                    media_size = msg.media.document.size
                    if media_size > max_size:
                        logger.warning(
                            f"Media too large: {media_size} bytes "
                            f"(limit: {max_size} bytes) in chat {msg_data.chat_id}, "
                            f"message {msg.id}"
                        )
                        return None

            if msg_data.grouped_id:
                valid_messages.sort(key=lambda x: x.id)

            await self._message_cache.set(
                (msg_data.chat_id, msg_data.message_id), valid_messages
            )
            return valid_messages

        except Exception as e:
            logger.error(
                f"Failed to fetch message from {msg_data.chat_id}: {e}",
                exc_info=True,
            )
            return None

    async def _send_message_internal(
        self,
        code_name: str,
        chat_id: int,
        messages_to_send: Union[Message, List[Message]],
        send_mode: str = "auto",
        schedule_time: Optional[datetime] = None,
    ) -> bool:
        """Internal method to send or forward messages."""
        try:
            if isinstance(messages_to_send, list):
                await self.client.forward_messages(
                    entity=chat_id,
                    messages=messages_to_send,
                    from_peer=messages_to_send[0].chat_id,
                    schedule=schedule_time,
                )
            elif messages_to_send.media and send_mode != "normal":
                await self.client.forward_messages(
                    entity=chat_id,
                    messages=[messages_to_send.id],
                    from_peer=messages_to_send.chat_id,
                    schedule=schedule_time,
                )
            else:
                await self.client.send_message(
                    entity=chat_id,
                    message=messages_to_send.text,
                    schedule=schedule_time,
                )
            return True
        except (ChatWriteForbiddenError, UserBannedInChannelError):
            raise
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {e}")
            return False

    @sleep_and_retry
    @limits(calls=1, period=5)
    async def _send_message(
        self,
        code_name: str,
        chat_id: int,
        message: Union[Message, List[Message]],
        send_mode: str = "auto",
        schedule_time: Optional[datetime] = None,
    ) -> bool:
        """Sends message with rate limiting."""
        return await self._send_message_internal(code_name, chat_id, message, send_mode, schedule_time)

    async def _send_messages_to_chats(
        self,
        code: BroadcastCode,
        code_name: str,
        messages_to_send: List[Union[Message, List[Message]]],
    ):
        """Отправляет сообщения чатам и обрабатывает неудачи."""
        chats = list(code.chats)
        random.shuffle(chats)
        failed_chats = set()
        schedule_time = datetime.now() + timedelta(seconds=60)

        for chat_id in chats:
            try:
                if code.batch_mode:
                    for msg in messages_to_send:
                        success = await self._send_message(
                            code_name, chat_id, msg, code.send_mode, schedule_time
                        )
                        if not success:
                            failed_chats.add(chat_id)
                            break
                else:
                    success = await self._send_message(
                        code_name, chat_id, messages_to_send[0], code.send_mode, schedule_time
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

    async def add_message(self, code_name: str, message: Message) -> bool:
        """Adds message to broadcast list with validation."""
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
                    self.codes[code_name] = BroadcastCode()

                code = self.codes[code_name]

                if len(code.messages) >= self.MAX_MESSAGES_PER_CODE:
                    logger.warning(
                        f"Max messages per code ({self.MAX_MESSAGES_PER_CODE}) reached"
                    )
                    return False

                grouped_id = getattr(message, "grouped_id", None)
                if grouped_id:
                    album_messages = []
                    async for album_msg in self.client.iter_messages(
                        message.chat_id,
                        min_id=max(0, message.id - 10),
                        max_id=message.id + 10,
                        limit=30,
                    ):
                        if getattr(album_msg, "grouped_id", None) == grouped_id:
                            album_messages.append(album_msg)

                    album_messages.sort(key=lambda m: m.id)
                    msg_data = BroadcastMessage(
                        chat_id=message.chat_id,
                        message_id=message.id,
                        grouped_id=grouped_id,
                        album_ids=tuple(msg.id for msg in album_messages),
                    )
                else:
                    msg_data = BroadcastMessage(
                        chat_id=message.chat_id, message_id=message.id
                    )

                code.messages.append(msg_data)
                self.save_config()
                return True

        except Exception as e:
            logger.error(f"Error adding message to {code_name}: {e}")
            return False

    async def _apply_interval(self, code: BroadcastCode, code_name: str):
        """Применяет интервал между отправками."""
        min_interval, max_interval = code.normalize_interval()
        interval = random.uniform(min_interval, max_interval) * 60
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
                await self._send_message(
                    code_name,
                    (await self.client.get_me()).id,
                    f"⚠️ Рассылка '{code_name}': Не удалось отправить сообщения в чаты: {failed_chats_str}",
                    schedule_time=datetime.now() + timedelta(seconds=60),
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
                for msg_data in code.messages:
                    message = await self._fetch_messages(msg_data)
                    if message:
                        messages_to_send.append(message)

                if not messages_to_send:
                    await asyncio.sleep(60)
                    continue

                if not code.batch_mode:
                    msg_index = self.message_indices.get(code_name, 0)
                    messages_to_send = [
                        messages_to_send[msg_index % len(messages_to_send)]
                    ]
                    self.message_indices[code_name] = (msg_index + 1) % len(
                        self.codes[code_name].messages
                    )

                failed_chats = await self._send_messages_to_chats(
                    code, code_name, messages_to_send
                )
                await self._handle_failed_chats(code_name, failed_chats)
                current_time = time.time()
                self.last_broadcast_time[code_name] = current_time
                self._save_last_broadcast_time(code_name, current_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Critical error in broadcast loop {code_name}: {e}"
                )
                await asyncio.sleep(60)

    def save_config(self):
        """Saves current configuration to database."""
        try:
            config = {
                "version": 1,
                "last_save": int(time.time()),
                "codes": {
                    name: {
                        "chats": list(code.chats),
                        "messages": [
                            {
                                "chat_id": msg.chat_id,
                                "message_id": msg.message_id,
                                "grouped_id": msg.grouped_id,
                                "album_ids": list(msg.album_ids),
                            }
                            for msg in code.messages
                        ],
                        "interval": list(code.interval),
                        "send_mode": code.send_mode,
                        "batch_mode": code.batch_mode,
                    }
                    for name, code in self.codes.items()
                },
            }
            self.db.set("broadcast", "config", config)

            self.db.set(
                "broadcast", "last_broadcast_times", self.last_broadcast_time
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
        self.auth_manager: Optional[AuthorizationManager] = None
        self.wat_mode: bool = False
        self.me_id: Optional[int] = None
        self._periodic_task: Optional[asyncio.Task] = None

    async def client_ready(self, client, db):
        """Инициализация при запуске."""
        self.auth_manager = AuthorizationManager()
        self.manager = BroadcastManager(client, db)
        self.me_id = (await client.get_me()).id

        config_data = db.get("broadcast", "config", {})
        self.manager._load_config_from_dict(config_data)

        broadcast_status = db.get("broadcast", "BroadcastStatus", {})
        for code_name in self.manager.codes:
            if broadcast_status.get(code_name):
                asyncio.create_task(self._start_broadcast(code_name))

        self._periodic_task = asyncio.create_task(self._periodic_cleanup())

    async def _check_auth(self, message: Message) -> bool:
        """Проверяет авторизацию пользователя."""
        try:
            user_id = message.sender_id
            if not self.auth_manager.is_authorized(user_id):
                await utils.answer(message, self.strings["not_authorized"])
                return False
            return True
        except Exception as e:
            logger.error(f"Authorization check error: {e}")
            await utils.answer(message, self.strings["auth_error"])
            return False

    async def _periodic_cleanup(self):
        """Периодическая очистка ресурсов."""
        while True:
            try:
                tasks_to_await = list(self.manager.broadcast_tasks.values())
                if tasks_to_await:
                    completed_tasks = await asyncio.gather(
                        *tasks_to_await, return_exceptions=True
                    )

                    for code_name, task in list(
                        self.manager.broadcast_tasks.items()
                    ):
                        if task.done():
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass
                            except Exception as e:
                                logger.error(
                                    f"Error in completed broadcast task {code_name}: {e}"
                                )
                            finally:
                                del self.manager.broadcast_tasks[code_name]

                await self.manager._message_cache.clean_expired()

                broadcast_status = self.manager.db.get(
                    "broadcast", "BroadcastStatus", {}
                )
                cleaned_status = {
                    k: v
                    for k, v in broadcast_status.items()
                    if k in self.manager.codes
                }
                if cleaned_status != broadcast_status:
                    self.manager.db.set(
                        "broadcast", "BroadcastStatus", cleaned_status
                    )

            except Exception as e:
                logger.error(f"Cleanup error: {e}")
            await asyncio.sleep(3600)

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
        self, message: Message, code_name: Optional[str] = None
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

    async def addmsgcmd(self, message: Message):
        """Добавить сообщение в рассылку: .addmsg код"""
        reply = await message.get_reply_message()
        if not reply:
            return await utils.answer(message, self.strings["reply_to_message"])

        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, self.strings["addmsg_usage"])

        code_name = args[0]

        if code_name in self.manager.codes:
            if (
                len(self.manager.codes[code_name].messages)
                >= self.manager.MAX_MESSAGES_PER_CODE
            ):
                return await utils.answer(
                    message,
                    self.strings["max_messages_reached"].format(
                        code_name, self.manager.MAX_MESSAGES_PER_CODE
                    ),
                )
        elif len(self.manager.codes) >= self.manager.MAX_CODES:
            return await utils.answer(
                message,
                self.strings["max_codes_reached"].format(
                    self.manager.MAX_CODES
                ),
            )
        else:
            if not await self._check_auth(message):
                return

        success = await self.manager.add_message(code_name, reply)
        if success:
            text = self.strings[
                (
                    "album_added"
                    if getattr(reply, "grouped_id", None)
                    else "single_added"
                )
            ].format(code_name)
        else:
            text = "❌ Не удалось добавить сообщение"

        await utils.answer(message, text)

    async def batchcmd(self, message: Message):
        """Toggle batch sending mode for a code: .batch <code"""
        code_name = await self._validate_code(message)
        if not code_name:
            return

        if not await self._check_auth(message):
            return

        code = self.manager.codes[code_name]
        code.batch_mode = not code.batch_mode
        self.manager.save_config()

        await utils.answer(
            message,
            f"✅ Code '{code_name}' batch sending mode is now {'enabled' if code.batch_mode else 'disabled'}.\n\n<code>Author: @kramiikk</code>",
        )

    async def broadcastcmd(self, message: Message):
        """Управление рассылкой: .broadcast [код]"""
        args = utils.get_args(message)

        if not args:
            if self.manager.broadcast_tasks:
                for code_name in list(self.manager.broadcast_tasks.keys()):
                    await self._stop_broadcast(code_name)
                await utils.answer(message, self.strings["all_stopped"])
            else:
                if not await self._check_auth(message):
                    return
                success = True
                for code_name in self.manager.codes:
                    if not await self._start_broadcast(code_name):
                        success = False
                await utils.answer(
                    message,
                    (
                        self.strings["all_started"]
                        if success
                        else "⚠️ Не все рассылки удалось запустить"
                    ),
                )
            return

        code_name = await self._validate_code(message, args[0])
        if not code_name:
            return

        if code_name in self.manager.broadcast_tasks:
            await self._stop_broadcast(code_name)
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
                    f"{self.strings['broadcast_start_failed'].format(code_name)}\n\n<code>Author: @kramiikk</code>",
                )

    async def cachescmd(self, message: Message):
        """Показать статистику кэша сообщений."""
        try:
            stats = await self.manager._message_cache.get_stats()

            text = [
                "<b>📊 Статистика кэша сообщений:</b>\n",
                f"📈 Всего записей: {stats['total_entries']}/{stats['max_size']}",
                f"✅ Активных записей: {stats['active_entries']}",
                f"❌ Просроченных записей: {stats['expired_entries']}",
                f"💾 Заполненность: {stats['usage_percent']}%",
                f"⏳ Время жизни записи: {stats['ttl_seconds'] // 60} минут",
            ]

            if "oldest_entry_age" in stats:
                text.extend(
                    [
                        f"\n⌛️ Возраст записей:",
                        f"• Старейшая: {stats['oldest_entry_age']} минут",
                        f"• Новейшая: {stats['newest_entry_age']} минут",
                    ]
                )

            await utils.answer(
                message,
                f"{chr(10).join(text)}\n\n<code>Author: @kramiikk</code>",
            )

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            await utils.answer(
                message,
                f"❌ Ошибка получения статистики: {e}\n\n<code>Author: @kramiikk</code>",
            )

    async def chatcmd(self, message: Message):
        """Добавить/удалить чат из рассылки: .chat код id_чата"""
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(
                message,
                f"{self.strings['chat_usage']}\n\n<code>Author: @kramiikk</code>",
            )

        try:
            code_name, chat_id = args[0], int(args[1])
        except ValueError:
            await utils.answer(
                message,
                f"{self.strings['chat_id_numeric']}\n\n<code>Author: @kramiikk</code>",
            )

        code_name = await self._validate_code(message, code_name)
        if not code_name:
            return

        code = self.manager.codes[code_name]

        if chat_id in code.chats:
            code.chats.remove(chat_id)
            result = "removed"
        else:
            if len(code.chats) >= self.manager.MAX_CHATS_PER_CODE:
                return await utils.answer(
                    message,
                    f"{self.strings['max_chats_reached'].format(code_name, self.manager.MAX_CHATS_PER_CODE)}\n\n<code>Author: @kramiikk</code>",
                )
            code.chats.add(chat_id)
            result = "added"

        self.manager.save_config()
        await utils.answer(
            message, self.strings[f"chat_{result}"].format(chat_id, code_name)
        )

    async def delcodecmd(self, message: Message):
        """Удалить код рассылки: .delcode код"""
        code_name = await self._validate_code(message)
        if not code_name:
            await utils.answer(
                message, "Нет такого кода\n\n<code>Author: @kramiikk</code>"
            )
            return

        await self._stop_broadcast(code_name)

        try:
            saved_times = self.db.get("broadcast", "last_broadcast_times", {})
            saved_times.pop(code_name, None)
            self.manager.db.set(
                "broadcast", "last_broadcast_times", saved_times
            )
            self.manager.last_broadcast_time.pop(code_name, None)
        except Exception as e:
            logger.error(
                f"Failed to clear last broadcast time for {code_name}: {e}"
            )

        del self.manager.codes[code_name]
        self.manager.message_indices.pop(code_name, None)
        self.manager._message_cache.clear()
        self.manager.save_config()

        await utils.answer(
            message, self.strings["delcode_success"].format(code_name)
        )

    async def delmsgcmd(self, message: Message):
        """Удалить сообщение из рассылки."""
        code_name = await self._validate_code(message)
        if not code_name:
            return

        args = utils.get_args(message)
        reply = await message.get_reply_message()
        code = self.manager.codes[code_name]

        if reply:
            initial_len = len(code.messages)
            code.messages = [
                msg
                for msg in code.messages
                if not (
                    msg.message_id == reply.id and msg.chat_id == reply.chat_id
                )
            ]
            if len(code.messages) < initial_len:
                self.manager._message_cache.clear()
                self.manager.save_config()
                await utils.answer(message, self.strings["delmsg_deleted"])
            else:
                await utils.answer(
                    message,
                    f"{self.strings['delmsg_not_found']}\n\n<code>Author: @kramiikk</code>",
                )
        elif len(args) == 2:
            try:
                index = int(args[1]) - 1
                if 0 <= index < len(code.messages):
                    del code.messages[index]
                    self.manager._message_cache.clear()
                    self.manager.save_config()
                    await utils.answer(message, self.strings["delmsg_deleted"])
                else:
                    await utils.answer(
                        message,
                        f"{self.strings['delmsg_invalid_index']}\n\n<code>Author: @kramiikk</code>",
                    )
            except ValueError:
                await utils.answer(
                    message,
                    f"{self.strings['delmsg_index_numeric']}\n\n<code>Author: @kramiikk</code>",
                )
        else:
            await utils.answer(
                message,
                f"{self.strings['delmsg_index_usage']}\n\n<code>Author: @kramiikk</code>",
            )

    async def intervalcmd(self, message: Message):
        """Изменить интервал рассылки: .interval код мин макс"""
        args = utils.get_args(message)
        if len(args) != 3:
            return await utils.answer(
                message,
                f"{self.strings['interval_usage']}\n\n<code>Author: @kramiikk</code>",
            )

        code_name = await self._validate_code(message, args[0])
        if not code_name:
            return

        if not await self._check_auth(message):
            return

        try:
            min_minutes, max_minutes = map(int, args[1:])
            if not (1 <= min_minutes < max_minutes <= 1440):
                return await utils.answer(
                    message,
                    f"{self.strings['interval_invalid_range']}\n\n<code>Author: @kramiikk</code>",
                )

            self.manager.codes[code_name].interval = (min_minutes, max_minutes)
            self.manager.save_config()

            await utils.answer(
                message,
                f"{self.strings['interval_set'].format(code_name, min_minutes, max_minutes)}\n\n<code>Author: @kramiikk</code>",
            )
        except ValueError:
            await utils.answer(
                message,
                f"{self.strings['interval_numeric']}\n\n<code>Author: @kramiikk</code>",
            )

    async def listcmd(self, message: Message):
        """Показать список рассылок."""
        if not self.manager.codes:
            return await utils.answer(message, self.strings["no_codes"])

        text = [
            "<b>Рассылка:</b>",
            f"🔄 Управление чатами: {'Включено' if self.wat_mode else 'Выключено'}\n",
            "<b>Коды рассылок:</b>",
        ]

        for code_name, code in self.manager.codes.items():
            last_time = self.manager.last_broadcast_time.get(code_name, 0)
            last_broadcast = (
                datetime.fromtimestamp(last_time).strftime("%Y-%m-%d %H:%M:%S")
                if last_time
                else "Never"
            )
            chat_list = ", ".join(map(str, code.chats)) or "(пусто)"
            min_interval, max_interval = code.interval
            message_count = len(code.messages)
            running = code_name in self.manager.broadcast_tasks

            text.append(
                f"+ <code>{code_name}</code>:\n"
                f"  💬 Чаты: {chat_list}\n"
                f"  ⏱ Интервал: {min_interval} - {max_interval} минут\n"
                f"  📨 Сообщений: {message_count}\n"
                f"  📊 Статус: {'🟢 Работает' if running else '🔴 Остановлен'}\n"
                f"  ⏳ Time: {last_broadcast}"
            )
        await utils.answer(
            message, f"{chr(10).join(text)}\n\n<code>Author: @kramiikk</code>"
        )

    async def listmsgcmd(self, message: Message):
        """Команда для просмотра списка сообщений в определенном коде рассылки."""

        code_name = await self._validate_code(message)
        if not code_name:
            return
        messages = self.manager.codes[code_name].messages
        if not messages:
            return await utils.answer(
                message,
                f"{self.strings['no_messages_in_code'].format(code_name)}\n\n<code>Author: @kramiikk</code>",
            )
        text = [f"<b>Сообщения в '{code_name}':</b>"]
        for i, msg in enumerate(messages, 1):
            try:
                chat_id = abs(msg.chat_id)
                base_link = f"t.me/c/{chat_id % 10**10}"

                if msg.grouped_id is not None:
                    album_links = "\n   ".join(
                        f"<a href='{base_link}/{album_id}'>{album_id}</a>"
                        for album_id in msg.album_ids
                    )
                    text.append(
                        f"{i}. Альбом в чате {msg.chat_id} (Изображений: {len(msg.album_ids)}):\n   {album_links}"
                    )
                else:
                    text.append(
                        f"{i}. Сообщение ID: {msg.message_id} в чате {msg.chat_id}:\n   <a href='{base_link}/{msg.message_id}'>{msg.message_id}</a>"
                    )
            except Exception as e:
                text.append(
                    f"{i}. Ошибка получения информации о сообщении в чате {msg.chat_id} с ID {msg.message_id}: {e}"
                )
        await utils.answer(
            message,
            f"{chr(10 * 2).join(text)}\n\n<code>Author: @kramiikk</code>",
        )

    async def sendmodecmd(self, message: Message):
        """Изменить режим отправки: .sendmode код режим"""
        args = utils.get_args(message)
        if len(args) != 2 or args[1] not in ["auto", "normal", "forward"]:
            return await utils.answer(
                message,
                f"{self.strings['sendmode_usage']}\n\n<code>Author: @kramiikk</code>",
            )

        code_name = await self._validate_code(message, args[0])
        if not code_name:
            return

        mode = args[1]
        self.manager.codes[code_name].send_mode = mode
        self.manager.save_config()
        await utils.answer(
            message, self.strings["sendmode_set"].format(code_name, mode)
        )

    async def watcmd(self, message: Message):
        """Включить/выключить автодобавление чатов: .wat"""
        self.wat_mode = not self.wat_mode
        await utils.answer(
            message,
            f"{self.strings['wat_status'].format('включено' if self.wat_mode else 'выключено')}\n\n<code>Author: @kramiikk</code>",
        )

    async def watcher(self, message: Message):
        """Автоматически добавляет чаты в рассылку."""
        if not isinstance(message, Message) or not self.wat_mode:
            return
        if message.sender_id != self.me_id or not message.text:
            return

        text = message.text.strip()
        for code_name in self.manager.codes:
            if text.startswith(code_name):
                try:
                    code = self.manager.codes[code_name]
                    if message.chat_id not in code.chats:
                        code.chats.add(message.chat_id)
                        self.manager.save_config()
                    break
                except Exception as e:
                    logger.error(f"Ошибка автодобавления чата: {e}")

    async def on_unload(self):
        """Очистка при выгрузке модуля."""
        if self._periodic_task:
            self._periodic_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._periodic_task

        for code_name in list(self.manager.broadcast_tasks.keys()):
            await self._stop_broadcast(code_name)

        self.manager._message_cache.clear()
        logger.info("Все правильно очищено")


class MessageCache:
    """Thread-safe message cache implementation with TTL."""

    def __init__(self, ttl: int = 3600, max_size: int = 13):
        self.cache: Dict[
            Tuple[int, int], Tuple[float, Union[Message, List[Message]]]
        ] = {}
        self._lock = asyncio.Lock()
        self.ttl = ttl
        self.max_size = max_size
        self._cleaning = False

    async def get(
        self, key: Tuple[int, int]
    ) -> Optional[Union[Message, List[Message]]]:
        """Get cached message if not expired."""
        if not key:
            return None

        async with self._lock:
            if key not in self.cache:
                return None

            timestamp, value = self.cache[key]
            if time.time() - timestamp > self.ttl:
                del self.cache[key]
                return None

            return value

    async def set(
        self, key: Tuple[int, int], value: Union[Message, List[Message]]
    ):
        """Cache message with timestamp."""
        if not key or value is None:
            return

        async with self._lock:
            if len(self.cache) >= self.max_size:
                sorted_items = sorted(self.cache.items(), key=lambda x: x[1][0])
                self.cache = dict(sorted_items[-(self.max_size - 1) :])
            self.cache[key] = (time.time(), value)

    def clear(self):
        """Clear all cached data."""
        self.cache.clear()

    async def clean_expired(self):
        """Removes expired entries from the cache."""
        if self._cleaning:
            return

        try:
            self._cleaning = True
            async with self._lock:
                current_time = time.time()
                expired_keys = [
                    k
                    for k, (timestamp, _) in self.cache.items()
                    if current_time - timestamp > self.ttl
                ]
                for key in expired_keys:
                    del self.cache[key]
        finally:
            self._cleaning = False

    async def get_stats(self) -> dict:
        """Get cache statistics."""
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
                    "usage_percent": round(
                        len(self.cache) / self.max_size * 100, 1
                    ),
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
