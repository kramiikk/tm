import asyncio
import html
import logging
import os
import re
import time
from typing import List, Dict, Union

import mmh3
from pybloom_live import CountingBloomFilter
from telethon.tl.types import Message, User, Chat

import firebase_admin
from firebase_admin import credentials, db as firebase_db
from .. import loader, utils

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
)
log = logging.getLogger(__name__)

TRADING_KEYWORDS = {
    "акк",
    "прод",
    "куп",
    "обмен",
    "лег",
    "оруж",
    "артефакты",
    "ивент",
    "100",
    "гарант",
    "уд",
    "утер",
    "луна",
    "ранг",
    "AR",
    "ищу",
    "приор",
    "стандарт",
    "евро",
    "уров",
    "старт",
    "сигна",
    "руб",
    "срочн",
    "кто",
}


class BatchProcessor:
    """Processes hashes in batches to reduce Firebase load."""

    def __init__(
        self,
        db_ref: firebase_db.Reference,
        max_hashes: int,
        batch_size: int = 100,
        flush_interval: int = 5,
    ):
        """
        Initializes the BatchProcessor.

        Args:
            db_ref: The Firebase database reference.
            max_hashes: The maximum number of hashes to store.
            batch_size: The number of hashes to accumulate before flushing.
            flush_interval: The time interval (in seconds) to flush automatically.
        """
        self.db_ref = db_ref
        self.max_hashes = max_hashes
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.batch = []
        self.last_flush = time.time()
        self.lock = asyncio.Lock()
        self.log = log

    async def add(self, hash_data: dict[str, float]):
        """Adds a hash to the batch."""
        async with self.lock:
            self.batch.append(hash_data)
            if (
                len(self.batch) >= self.batch_size
                or time.time() - self.last_flush > self.flush_interval
            ):
                await self.flush()

    async def flush(self):
        """Flushes the accumulated hashes to Firebase."""
        if not self.batch:
            return
        async with self.lock:
            try:
                hashes_ref = self.db_ref.child("hashes/hash_list")
                current_hashes = hashes_ref.get() or []
                current_hashes.extend(self.batch)
                current_hashes = current_hashes[-self.max_hashes :]
                hashes_ref.set(current_hashes)
                self.batch = []
                self.last_flush = time.time()
            except Exception as e:
                self.db_ref.child("errors").push(str(e))
                self.log.error(f"Batch flush error: {e}")


@loader.tds
class BroadMod(loader.Module):
    """Module for tracking and forwarding messages with batch processing and duplicate filtering."""

    strings = {
        "name": "Broad",
        "cfg_firebase_path": "Путь к файлу учетных данных Firebase",
        "cfg_firebase_url": "URL базы данных Firebase",
        "cfg_forward_channel": "ID канала для пересылки сообщений",
        "cfg_bloom_capacity": "Емкость Bloom-фильтра",
        "cfg_bloom_error": "Допустимая погрешность Bloom-фильтра",
        "cfg_cleanup_interval": "Интервал очистки кэша (в секундах)",
        "cfg_hash_retention": "Время хранения хэшей (в секундах)",
        "cfg_max_firebase_hashes": "Максимальное количество хэшей в Firebase",
        "cfg_min_text_length": "Минимальная длина текста для обработки",
        "no_firebase_path": "⚠️ Не указан путь к файлу учетных данных Firebase",
        "no_firebase_url": "⚠️ Не указан URL базы данных Firebase",
        "initialization_success": "✅ Модуль успешно инициализирован\nРазрешенные чаты: {chats}\nЗагружено хэшей: {hashes}",
        "firebase_init_error": "❌ Ошибка инициализации Firebase: {error}",
        "firebase_load_error": "❌ Ошибка при загрузке данных из Firebase: {error}",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "firebase_credentials_path",
            "/home/hikka/Hikka/loll-8a3bd-firebase-adminsdk-4pvtd-6b93a17b70.json",
            lambda: self.strings("cfg_firebase_path"),
            "firebase_database_url",
            "https://loll-8a3bd-default-rtdb.firebaseio.com",
            lambda: self.strings("cfg_firebase_url"),
            "forward_channel_id",
            2498567519,
            lambda: self.strings("cfg_forward_channel"),
            "bloom_filter_capacity",
            1000,
            lambda: self.strings("cfg_bloom_capacity"),
            "bloom_filter_error_rate",
            0.001,
            lambda: self.strings("cfg_bloom_error"),
            "cleanup_interval",
            3600,
            lambda: self.strings("cfg_cleanup_interval"),
            "hash_retention_period",
            86400,
            lambda: self.strings("cfg_hash_retention"),
            "max_firebase_hashes",
            1000,
            lambda: self.strings("cfg_max_firebase_hashes"),
            "min_text_length",
            18,
            lambda: self.strings("cfg_min_text_length"),
        )

        self.lock = asyncio.Lock()
        self.allowed_chats = []
        self.firebase_app = None
        self.db_ref = None
        self.bloom_filter = None
        self.hash_cache = {}
        self.last_cleanup_time = 0
        self.batch_processor = None
        self.initialized = False
        self.log = log
        super().__init__()

    def init_bloom_filter(self) -> bool:
        """Initializes the Bloom filter, returning True on success, False on failure."""
        try:
            self.bloom_filter = CountingBloomFilter(
                capacity=self.config["bloom_filter_capacity"],
                error_rate=self.config["bloom_filter_error_rate"],
            )
            return True
        except Exception as e:
            self.log.error(
                f"Bloom filter init error: {e}. Falling back to set(). Performance may be impacted."
            )
            self.bloom_filter = set()
            return False

    async def _initialize_firebase(self) -> bool:
        """Initializes Firebase, returning True on success, False on failure."""
        if not self.config["firebase_credentials_path"]:
            await self.client.send_message("me", self.strings["no_firebase_path"])
            return False
        if not self.config["firebase_database_url"]:
            await self.client.send_message("me", self.strings["no_firebase_url"])
            return False
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(self.config["firebase_credentials_path"])
                self.firebase_app = firebase_admin.initialize_app(
                    cred, {"databaseURL": self.config["firebase_database_url"]}
                )
            self.db_ref = firebase_db.reference("/")
            self.batch_processor = BatchProcessor(
                self.db_ref,
                max_hashes=self.config["max_firebase_hashes"],
                batch_size=50,
                flush_interval=5,
            )
            return True
        except Exception as e:
            await self.client.send_message(
                "me", self.strings["firebase_init_error"].format(error=str(e))
            )
            return False

    async def client_ready(self, client, db):
        self.client = client

        if not self.config["firebase_credentials_path"] or not os.path.exists(
            self.config["firebase_credentials_path"]
        ):
            await self.client.send_message(
                "me", "❌ Firebase credentials file not found or path is incorrect."
            )
            return
        if not self.config["firebase_database_url"]:
            await self.client.send_message(
                "me", "❌ Firebase database URL is not configured."
            )
            return
        if not firebase_admin._apps:
            if not await self._initialize_firebase():
                return
        try:
            self.db_ref = firebase_db.reference("/")
            self.batch_processor = BatchProcessor(
                self.db_ref, self.config["max_firebase_hashes"]
            )

            if not self.init_bloom_filter():
                self.initialized = False
                await client.send_message(
                    "me", "❌ Bloom filter initialization failed. Module disabled."
                )
                return
            await self._load_recent_hashes()

            chats_ref = self.db_ref.child("allowed_chats")
            chats_data = chats_ref.get()
            self.allowed_chats = chats_data if isinstance(chats_data, list) else []

            self.initialized = True
            await self.client.send_message(
                "me",
                self.strings["initialization_success"].format(
                    chats=self.allowed_chats, hashes=len(self.hash_cache)
                ),
            )
        except Exception as e:
            await client.send_message("me", f"❌ Error loading data from Firebase: {e}")
            self.initialized = False

    async def _load_recent_hashes(self):
        try:
            hashes_ref = self.db_ref.child("hashes/hash_list")
            all_hashes = hashes_ref.get() or []

            current_time = time.time()
            self.hash_cache = {}

            for hash_data in all_hashes[-self.config["max_firebase_hashes"] :]:
                if isinstance(hash_data, dict):
                    hash_value = hash_data.get("hash")
                    timestamp = hash_data.get("timestamp")
                    if (
                        hash_value
                        and timestamp
                        and current_time - timestamp
                        < self.config["hash_retention_period"]
                    ):
                        self.hash_cache[hash_value] = timestamp
                        if self.bloom_filter:
                            self.bloom_filter.add(hash_value)
        except Exception as e:
            self.log.error(f"Error loading recent hashes: {e}")
            self.hash_cache = {}

    async def _clear_expired_hashes(self) -> int:
        """Clears expired hashes from the cache and Firebase, returning the number of removed hashes."""
        async with self.lock:
            try:
                current_time = time.time()
                if (
                    current_time - self.last_cleanup_time
                    < self.config["cleanup_interval"]
                ):
                    return 0
                self.last_cleanup_time = current_time
                expiration_time = current_time - self.config["hash_retention_period"]

                new_hash_cache = {}
                removed_count = 0

                for h, timestamp in list(self.hash_cache.items()):
                    if timestamp >= expiration_time:
                        new_hash_cache[h] = timestamp
                    else:
                        if self.bloom_filter:
                            self.bloom_filter.remove(h)
                        removed_count += 1
                self.hash_cache = new_hash_cache

                if self.batch_processor:
                    await self.batch_processor.flush()
                return removed_count
            except Exception as e:
                await self.client.send_message("me", f"Ошибка при очистке хэшей: {e}")
                return 0

    async def add_hash(self, message_hash: str):
        """Adds a message hash to the cache and Firebase."""
        async with self.lock:
            current_time = time.time()
            self.hash_cache[message_hash] = current_time
            if self.bloom_filter:
                self.bloom_filter.add(message_hash)
            try:
                hash_data = {"hash": message_hash, "timestamp": current_time}
                if self.batch_processor:
                    await self.batch_processor.add(hash_data)
                else:
                    hashes_ref = self.db_ref.child("hashes/hash_list")
                    current_hashes = hashes_ref.get() or []
                    if not isinstance(current_hashes, list):
                        current_hashes = []
                    current_hashes.append(hash_data)
                    if len(current_hashes) > self.config["max_firebase_hashes"]:
                        current_hashes = current_hashes[
                            -self.config["max_firebase_hashes"] :
                        ]
                    hashes_ref.set(current_hashes)
            except Exception as e:
                self.log.error(f"Error adding hash: {e}")

    async def forward_to_channel(self, message: Message):
        """Forwards the message to the configured channel, handling potential errors."""
        try:
            await message.forward_to(self.config["forward_channel_id"])
        except telethon.errors.ChannelPrivateError:
            log.error("Could not forward message directly. Trying to send text...")
            try:
                sender_info = self._get_sender_info(message)
                await self.client.send_message(
                    self.config["forward_channel_id"],
                    sender_info + message.raw_text,
                    link_preview=False,
                )
            except Exception as forward_error:
                log.exception(f"Error forwarding message text: {forward_error}")
                await self.client.send_message(
                    "me",
                    f"❌ Ошибка при отправке: {forward_error}",  # Keep this for user notification
                )

    def _get_sender_info(self, message: Message) -> str:
        """Constructs a string with sender information."""
        sender = message.sender
        chat = message.chat
        sender_str = (sender.first_name or sender.title) if sender else "Unknown"
        chat_str = (
            (
                chat.title
                if isinstance(chat, Chat)
                else (chat.first_name if isinstance(chat, User) else "Unknown")
            )
            if chat
            else "Unknown"
        )
        return f"From: {sender_str} in {chat_str}\n\n"

    @loader.command
    async def manage_chat_cmd(self, message: Message):
        """Manages the list of allowed chats."""
        try:
            args = message.text.split()

            if len(args) != 2:
                response = "📝 Список разрешенных чатов:\n"
                response += (
                    ", ".join(map(str, self.allowed_chats))
                    if self.allowed_chats
                    else "пуст"
                )
                await message.reply(response)
                return
            try:
                chat_id = int(args[1])
            except ValueError:
                await message.reply(
                    "❌ Неверный формат ID чата. Укажите правильное число."
                )
                return
            async with self.lock:
                if chat_id in self.allowed_chats:
                    self.allowed_chats.remove(chat_id)
                    txt = f"❌ Чат {chat_id} удален из списка."
                else:
                    self.allowed_chats.append(chat_id)
                    txt = f"✅ Чат {chat_id} добавлен в список."
                chats_ref = self.db_ref.child("allowed_chats")
                chats_ref.set(self.allowed_chats)
            await message.reply(txt)
        except Exception as e:
            await message.reply(f"❌ Ошибка при управлении списком чатов: {e}")

    async def watcher(self, message: Message):
        """Watches for new messages and forwards them if they meet the criteria."""
        if not self.initialized:
            return
        if not message.sender or getattr(message.sender, "bot", False):
            return
        if not message.text or len(message.text) < self.config["min_text_length"]:
            return
        if getattr(message, "chat_id", None) not in self.allowed_chats:
            return
        current_time = time.localtime()
        if current_time.tm_min == 0 and current_time.tm_sec < 10:
            removed_count = await self._clear_expired_hashes()
            if removed_count > 0:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", current_time)
                await self.client.send_message(
                    "me",
                    f"[{timestamp}] Очистка: удалено {removed_count} хэшей. "
                    f"Размер кэша: {len(self.hash_cache)}",
                )
        low = message.text.lower()
        if not any(keyword in low for keyword in TRADING_KEYWORDS):
            return
        try:
            normalized_text = html.unescape(
                re.sub(r"<[^>]+>|[^\w\s,.!?;:—]|\s+", " ", message.text.lower())
            ).strip()

            if not normalized_text:
                return
            message_hash = str(mmh3.hash(normalized_text))

            async with self.lock:
                if (
                    message_hash in self.bloom_filter
                    and message_hash in self.hash_cache
                ):
                    return
            await self.add_hash(message_hash)
            await self.forward_to_channel(message)
        except Exception as e:
            error_message = f"Произошла ошибка: {type(e).__name__}: {e}\nТекст сообщения: {message.text[:100]}..."
            self.log.exception(f"Error in watcher: {error_message}")
            await self.client.send_message("me", error_message)
