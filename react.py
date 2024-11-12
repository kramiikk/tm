import asyncio
import html
import logging
import os
import re
import time
from typing import List, Dict, Union

import mmh3
from bloom_filter import BloomFilter
from telethon.tl.types import User, Chat
from telethon import errors, types

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
    """Simplified batch processor for Firebase operations"""

    def __init__(
        self,
        db_ref: firebase_db.Reference,
        max_hashes: int,
        batch_size: int = 100,
    ):
        self.db_ref = db_ref
        self.max_hashes = max_hashes
        self.batch_size = batch_size
        self.batch = []

    async def add(self, hash_data: dict):
        """add"""
        self.batch.append(hash_data)

        if len(self.batch) >= self.batch_size:
            await self.flush()

    async def flush(self):
        """flush"""
        if not self.batch:
            return
        try:
            current_batch = self.batch
            self.batch = []

            hashes_ref = self.db_ref.child("hashes/hash_list")
            current_hashes = hashes_ref.get() or []

            if not isinstance(current_hashes, list):
                current_hashes = []
            current_hashes.extend(current_batch)

            if len(current_hashes) > self.max_hashes:
                current_hashes = current_hashes[-self.max_hashes :]
            hashes_ref.set(current_hashes)
        except Exception as e:
            self.batch.extend(current_batch)


@loader.tds
class BroadMod(loader.Module):
    """Module for tracking and forwarding messages with batch processing and duplicate filtering. v 0.02"""

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
        """Initialize the Bloom filter."""
        try:
            self.bloom_filter = BloomFilter(
                self.config["bloom_filter_capacity"],
                self.config["bloom_filter_error_rate"],
            )
            return True
        except Exception as e:
            self.bloom_filter = set()
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
                db_ref=self.db_ref,
                max_hashes=self.config["max_firebase_hashes"],
                batch_size=50,
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
                db_ref=self.db_ref,
                max_hashes=self.config["max_firebase_hashes"],
                batch_size=50,
            )
            return True
        except Exception as e:
            await self.client.send_message(
                "me", self.strings["firebase_init_error"].format(error=str(e))
            )
            return False

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
            self.hash_cache = {}

    async def _clear_expired_hashes(self) -> int:
        """Clear"""
        try:
            current_time = time.time()
            if current_time - self.last_cleanup_time < self.config["cleanup_interval"]:
                return 0
            self.last_cleanup_time = current_time
            expiration_time = current_time - self.config["hash_retention_period"]

            new_hash_cache = {
                h: ts for h, ts in self.hash_cache.items() if ts >= expiration_time
            }

            removed_count = len(self.hash_cache) - len(new_hash_cache)
            self.hash_cache = new_hash_cache

            if self.bloom_filter is not None:
                self.bloom_filter = BloomFilter(
                    self.config["bloom_filter_capacity"],
                    self.config["bloom_filter_error_rate"],
                )
                for h in self.hash_cache:
                    self.bloom_filter.add(h)
            if self.batch_processor:
                await self.batch_processor.flush()
            return removed_count
        except Exception as e:
            self.log.error(f"Error clearing hashes: {e}")
            return 0

    async def _get_sender_info(self, message) -> str:
        """Constructs a string with sender information asynchronously."""
        try:
            sender = getattr(message, "sender", None)
            chat = getattr(message, "chat", None)
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
        except Exception:
            return "From: Unknown in Unknown\n\n"

    @loader.command
    async def managecmd(self, message: types.Message):
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

    async def _forward_album(self, messages: List[types.Message]) -> bool:
        """Forward an entire album of messages."""
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                try:
                    channel = await self.client.get_entity(
                        self.config["forward_channel_id"]
                    )
                except Exception as e:
                    self.log.error(f"Error getting forward channel: {e}")
                    return False
                await self.client.forward_messages(
                    entity=self.config["forward_channel_id"],
                    messages=messages,
                    silent=True,
                )
                return True
            except errors.FloodWaitError as e:
                wait_time = e.seconds
                self.log.warning(f"Hit rate limit, waiting {wait_time} seconds")
                await asyncio.sleep(wait_time)
                continue
            except errors.ChannelPrivateError:
                self.log.error("Bot doesn't have access to the forward channel")
                return False
            except errors.ChatWriteForbiddenError:
                self.log.error(
                    "Bot doesn't have permission to write in the forward channel"
                )
                return False
            except Exception as e:
                if attempt == max_retries - 1:
                    self.log.error(
                        f"Failed to forward album after {max_retries} attempts: {e}"
                    )
                    return False
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
        return False

    async def watcher(self, message: types.Message):
        """Watcher method for processing and forwarding messages with improved error handling"""
        try:
            if (
                not self.initialized
                or message.chat_id not in self.allowed_chats
                or getattr(message.sender, "bot", False)
            ):
                return
            text_to_check = message.text or ""
            if len(text_to_check) < self.config["min_text_length"]:
                return
            low = text_to_check.lower()
            found_keywords = [kw for kw in TRADING_KEYWORDS if kw in low]
            if not found_keywords:
                return
            normalized_text = html.unescape(
                re.sub(r"<[^>]+>|[^\w\s,.!?;:—]|\s+", " ", low)
            ).strip()
            if not normalized_text:
                return
            message_hash = str(mmh3.hash(normalized_text))
            if message_hash in self.hash_cache:
                return
            current_time = time.time()
            self.hash_cache[message_hash] = current_time
            if self.bloom_filter is not None:
                self.bloom_filter.add(message_hash)
            hash_data = {"hash": message_hash, "timestamp": current_time}

            try:
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
                self.log.error(f"Error adding hash to Firebase: {e}")
                self.hash_cache.pop(message_hash, None)
                return
            if hasattr(message, "grouped_id") and message.grouped_id:
                chat = await message.get_chat()
                album_messages = []
                async for msg in self.client.iter_messages(
                    chat,
                    limit=50,
                    offset_date=message.date,
                ):
                    if (
                        hasattr(msg, "grouped_id")
                        and msg.grouped_id == message.grouped_id
                    ):
                        album_messages.append(msg)
                    if len(album_messages) >= 10:
                        break
                if album_messages:
                    album_messages.sort(key=lambda m: m.id)
                    await self._forward_album(album_messages)
                    return
            max_retries = 3

            for attempt in range(max_retries):
                try:
                    await message.forward_to(
                        self.config["forward_channel_id"],
                        silent=True,
                    )
                    break
                except errors.FloodWaitError as e:
                    wait_time = time.time() + e.seconds
                    self.log.warning(
                        f"Hit rate limit {e.seconds}, waiting {wait_time} seconds"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                except errors.ChannelPrivateError:
                    self.log.error("Doesn't have access to the forward channel")
                    return
        except Exception as e:
            self.log.error(f"Error in watcher: {str(e)}", exc_info=True)
            return
