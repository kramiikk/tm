import asyncio
import bisect
import html
import logging
import os
import re
import time
from asyncio import Queue
from typing import List, Dict

import mmh3
from bloom_filter import BloomFilter
from telethon import errors, types, utils as telethon_utils

import firebase_admin
from firebase_admin import credentials, db as firebase_db
from .. import loader, utils


logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
)
log = logging.getLogger(__name__)


class BatchProcessor:
    """Handles batched writes to Firebase to reduce overhead."""

    def __init__(
        self, db_ref: firebase_db.Reference, max_hashes: int, batch_size: int = 50
    ):
        self.db_ref = db_ref
        self.max_hashes = max_hashes
        self.batch_size = batch_size
        self.batch = []

    async def add(self, hash_data: dict):
        """Adds a hash to the batch. Flushes the batch if it's full."""
        self.batch.append(hash_data)
        if len(self.batch) >= self.batch_size:
            await self.flush()

    async def flush(self):
        """Writes the accumulated batch of hashes to Firebase."""
        if not self.batch:
            return
        try:
            current_batch = self.batch[:]
            self.batch.clear()

            hashes_ref = self.db_ref.child("hashes/hash_list")
            current_hashes = hashes_ref.get() or []

            if not isinstance(current_hashes, list):
                log.warning(
                    "Invalid data type received from Firebase. Resetting hash list."
                )
                current_hashes = []
            current_hashes.extend(current_batch)

            if len(current_hashes) > self.max_hashes:
                current_hashes = current_hashes[-self.max_hashes :]
            hashes_ref.set(current_hashes)
        except Exception as e:
            log.error(f"Error flushing batch to Firebase: {e}", exc_info=True)
            self.batch.extend(current_batch)


@loader.tds
class BroadMod(loader.Module):
    """Forwards messages containing specific keywords to a designated channel."""

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
        "firebase_init_error": "❌ Ошибка инициализации Firebase: {error}",
        "sender_info": "👤 Отправитель: <a href='{sender_url}'>{sender_name}</a> ({sender_id})\n{scam_warning}\n💬 Источник: <a href='{message_url}'>{chat_title}</a>",
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
            "trading_keywords",
            [
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
                "крыл",
                "срочн",
                "кто",
            ],
            lambda: "Keywords to trigger forwarding (list of strings)",
        )

        self.message_queue = Queue()
        self.processing_task = None
        self.allowed_chats = []
        self.firebase_app = None
        self.db_ref = None
        self.bloom_filter = None
        self.hash_cache = {}
        self.last_cleanup_time = 0
        self.batch_processor = None
        self.initialized = False
        super().__init__()

    def init_bloom_filter(self) -> bool:
        """Initializes the Bloom filter for duplicate detection.  Falls back to a set if there's an error."""
        try:
            self.bloom_filter = BloomFilter(
                self.config["bloom_filter_capacity"],
                self.config["bloom_filter_error_rate"],
            )
            return True
        except Exception as e:
            log.error(f"Bloom filter initialization failed, using set instead: {e}")
            self.bloom_filter = set()
            return False

    async def client_ready(self, client, db):
        """Initializes the module when the Telethon client is ready."""
        self.client = client

        if not self.config["firebase_credentials_path"] or not os.path.exists(
            self.config["firebase_credentials_path"]
        ):
            log.warning("❌ Firebase credentials file not found or path is incorrect.")
            return
        if not self.config["firebase_database_url"]:
            log.warning("❌ Firebase database URL is not configured.")
            return
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
                log.warning("❌ Bloom filter initialization failed. Module disabled.")
                return
            await self._load_recent_hashes()

            chats_ref = self.db_ref.child("allowed_chats")
            chats_data = chats_ref.get()
            self.allowed_chats = chats_data if isinstance(chats_data, list) else []

            self.initialized = True
        except Exception as e:
            log.error(f"❌ Error loading data from Firebase: {e}")
            self.initialized = False
        if not self.processing_task:
            self.processing_task = asyncio.create_task(self.process_queue())

    async def _initialize_firebase(self) -> bool:
        """Initialize Firebase connection"""
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(self.config["firebase_credentials_path"])
                self.firebase_app = firebase_admin.initialize_app(
                    cred, {"databaseURL": self.config["firebase_database_url"]}
                )
            self.db_ref = firebase_db.reference("/")
            return True
        except Exception as e:
            log.error(self.strings["firebase_init_error"].format(error=str(e)))
            return False

    async def _load_recent_hashes(self):
        """Load recent hashes from Firebase"""
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
            log.error(f"Error loading recent hashes: {e}", exc_info=True)
            self.hash_cache = {}

    async def _clear_expired_hashes(self):
        """Clear expired hashes from cache"""
        current_time = time.time()
        if current_time - self.last_cleanup_time < self.config["cleanup_interval"]:
            return
        self.last_cleanup_time = current_time
        expiration_time = current_time - self.config["hash_retention_period"]

        self.hash_cache = {
            h: ts for h, ts in self.hash_cache.items() if ts >= expiration_time
        }

        if self.bloom_filter is not None and isinstance(self.bloom_filter, BloomFilter):
            self.bloom_filter = BloomFilter(
                self.config["bloom_filter_capacity"],
                self.config["bloom_filter_error_rate"],
            )
            for h, ts in self.hash_cache.items():
                self.bloom_filter.add(h)
        elif isinstance(self.bloom_filter, set):
            self.bloom_filter = set(
                h for h, ts in self.hash_cache.items() if ts >= expiration_time
            )

    async def process_queue(self):
        """Processes messages from the queue with a delay."""
        while True:
            messages, sender_info = await self.message_queue.get()
            try:
                await asyncio.sleep(13)
                forwarded = await self.client.forward_messages(
                    entity=self.config["forward_channel_id"],
                    messages=messages,
                    silent=True,
                )

                if forwarded:
                    reply_to_id = (
                        forwarded[0].id if isinstance(forwarded, list) else forwarded.id
                    )
                    await self.client.send_message(
                        entity=self.config["forward_channel_id"],
                        message=self.strings["sender_info"].format(**sender_info),
                        reply_to=reply_to_id,
                        parse_mode="html",
                        link_preview=False,
                    )
            except errors.FloodWaitError as e:
                await asyncio.sleep(900 + e.seconds)
            except Exception as e:
                log.error(f"Error processing message: {e}", exc_info=True)
            finally:
                self.message_queue.task_done()

    async def _get_sender_info(self, message: types.Message) -> dict:
        """Get formatted sender information"""
        try:
            sender_name = (
                "Deleted Account"
                if hasattr(message.sender, "deleted") and message.sender.deleted
                else message.sender.first_name
            )

            sender_url = (
                f"https://t.me/{message.sender.username}"
                if hasattr(message.sender, "username") and message.sender.username
                else f"tg://user?id={message.sender.id}"
            )

            message_url = (
                f"https://t.me/{message.chat.username}/{message.id}"
                if hasattr(message.chat, "username") and message.chat.username
                else f"https://t.me/c/{str(message.chat_id)[4:]}/{message.id}"
            )
            is_scammer, post_link = await self.check_scammer(message.sender.id)

            return {
                "sender_name": html.escape(sender_name),
                "sender_id": message.sender.id,
                "sender_url": sender_url,
                "chat_title": html.escape(message.chat.title),
                "message_url": message_url,
                "scam_warning": (
                    f"⚠️ Осторожно! Пользователь <a href='{post_link}'>обнаружен в базе скамеров</a>.\n"
                    if is_scammer
                    else ""
                ),
            }
        except Exception as e:
            log.error(f"Error getting sender info: {e}")
            return {}

    async def check_scammer(self, user_id: int) -> tuple[bool, str | None]:
        """
        Check if user ID exists in the special channel and return post link.
        Uses message search instead of iteration for better performance.
        """
        try:
            messages = await self.client.get_messages(
                1539778138, search=str(user_id), limit=1
            )

            if messages and messages[0]:
                post_link = f"https://t.me/bezscamasuka/{messages[0].id}"
                return True, post_link
        except Exception as e:
            log.error(f"Error checking scammer: {e}")
            return False, None
        return False, None

    @loader.command
    async def managecmd(self, message: types.Message):
        """Manages the list of allowed chats"""
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

    async def watcher(self, message: types.Message):
        """Process and forward messages"""
        if (
            not self.initialized
            or message.chat_id not in self.allowed_chats
            or (sender := getattr(message, "sender", None)) is None
            or getattr(sender, "bot", False)
        ):
            return
        try:
            text_to_check = message.text or ""
            if len(text_to_check) < self.config["min_text_length"]:
                return
            low = text_to_check.lower()
            found_keywords = [kw for kw in self.config["trading_keywords"] if kw in low]
            if not found_keywords:
                return
            normalized_text = html.unescape(
                re.sub(r"<[^>]+>|[^\w\s,.!?;:—]|\s+", " ", low)
            ).strip()
            if not normalized_text:
                return
            message_hash = str(mmh3.hash(normalized_text))
            if message_hash in self.hash_cache:
                await self._clear_expired_hashes()
                return
            current_time = time.time()
            self.hash_cache[message_hash] = current_time

            if self.bloom_filter is not None:
                if isinstance(self.bloom_filter, BloomFilter):
                    self.bloom_filter.add(message_hash)
                elif isinstance(self.bloom_filter, set):
                    self.bloom_filter.add(message_hash)
            try:
                hash_data = {"hash": message_hash, "timestamp": current_time}
                if self.batch_processor:
                    await self.batch_processor.add(hash_data)
            except Exception as e:
                log.error(f"Error adding hash to Firebase: {e}", exc_info=True)
                self.hash_cache.pop(message_hash, None)
                return
            messages = [message]
            if hasattr(message, "grouped_id") and message.grouped_id:
                async for msg in self.client.iter_messages(
                    message.chat_id, limit=10, offset_date=message.date
                ):
                    if (
                        hasattr(msg, "grouped_id")
                        and msg.grouped_id == message.grouped_id
                        and msg.id != message.id
                    ):
                        bisect.insort(messages, msg, key=lambda m: m.id)
            sender_info = await self._get_sender_info(message)
            await self.message_queue.put((messages, sender_info))
        except Exception as e:
            log.error(f"Error in watcher: {e}", exc_info=True)
