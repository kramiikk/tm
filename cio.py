import asyncio
import html
import logging
import os
import re
import time
from asyncio import Queue
from typing import List, Dict

import firebase_admin
from firebase_admin import credentials, db as firebase_db
from telethon import errors, types, utils as telethon_utils
from .. import loader, utils

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
)
log = logging.getLogger(name)


class NgramFirebaseHandler:
    """Handles storage and retrieval of n-grams in Firebase."""

    def init(
        self,
        db_ref: firebase_db.Reference,
        max_entries: int = 1000,
        batch_size: int = 50,
    ):
        self.db_ref = db_ref
        self.max_entries = max_entries
        self.batch_size = batch_size
        self.batch = []
        self.ngram_ref = self.db_ref.child("ngrams/entries")

    async def add_entry(self, ngram_data: dict):
        """Adds an n-gram entry to the batch. Flushes if batch is full."""
        self.batch.append(ngram_data)
        if len(self.batch) >= self.batch_size:
            await self.flush()

    async def flush(self):
        """Writes accumulated n-gram entries to Firebase."""
        if not self.batch:
            return
        try:
            current_batch = self.batch[:]
            self.batch.clear()

            current_entries = self.ngram_ref.get() or []
            if not isinstance(current_entries, list):
                log.warning("Invalid data type for n-grams in Firebase. Resetting.")
                current_entries = []
            current_entries.extend(current_batch)
            if len(current_entries) > self.max_entries:
                current_entries = current_entries[-self.max_entries :]
            self.ngram_ref.set(current_entries)
        except Exception as e:
            log.error(f"Error flushing n-grams to Firebase: {e}", exc_info=True)
            self.batch.extend(current_batch)

    async def load_entries(self, retention_period: float) -> dict:
        """Loads and filters n-gram entries from Firebase."""
        try:
            entries = self.ngram_ref.get() or []
            current_time = time.time()

            ngram_dict = {}
            for entry in entries:
                if isinstance(entry, dict):
                    timestamp = entry.get("timestamp", 0)
                    if current_time - timestamp < retention_period:
                        hash_val = entry.get("hash")
                        ngrams = set(entry.get("ngrams", []))
                        if hash_val and ngrams:
                            ngram_dict[hash_val] = (ngrams, timestamp)
            return ngram_dict
        except Exception as e:
            log.error(f"Error loading n-grams from Firebase: {e}", exc_info=True)
            return {}


class NgramSimilarityChecker:
    """Handles message similarity detection using n-grams."""

    def init(
        self,
        db_ref: firebase_db.Reference,
        n: int = 3,
        similarity_threshold: float = 0.7,
        max_entries: int = 1000,
        retention_period: float = 86400,
    ):
        self.n = n
        self.similarity_threshold = similarity_threshold
        self.retention_period = retention_period
        self.ngram_cache = {}
        self.firebase_handler = NgramFirebaseHandler(db_ref, max_entries)

    def generate_ngrams(self, text: str) -> set:
        """Generate n-grams from input text."""
        text = text.lower().strip()
        padded = f"{'_' * (self.n-1)}{text}{'_' * (self.n-1)}"
        return {padded[i : i + self.n] for i in range(len(padded) - self.n + 1)}

    def calculate_similarity(self, ngrams1: set, ngrams2: set) -> float:
        """Calculate Jaccard similarity between two sets of n-grams."""
        if not ngrams1 or not ngrams2:
            return 0.0
        intersection = len(ngrams1.intersection(ngrams2))
        union = len(ngrams1.union(ngrams2))
        return intersection / union if union > 0 else 0.0

    async def initialize(self):
        """Load existing n-grams from Firebase."""
        self.ngram_cache = await self.firebase_handler.load_entries(self.retention_period)

    async def is_similar_to_cached(self, text: str, timestamp: float) -> bool:
        """Check if text is similar to any cached messages."""
        current_ngrams = self.generate_ngrams(text)
        
        self.ngram_cache = {
            hash_val: (ngrams, ts) 
            for hash_val, (ngrams, ts) in self.ngram_cache.items()
            if timestamp - ts < self.retention_period
        }
        
        for ngrams, _ in self.ngram_cache.values():
            similarity = self.calculate_similarity(current_ngrams, ngrams)
            if similarity >= self.similarity_threshold:
                return True
        
        cache_key = hash(frozenset(current_ngrams))
        self.ngram_cache[cache_key] = (current_ngrams, timestamp)
        
        ngram_data = {
            'hash': cache_key,
            'ngrams': list(current_ngrams),
            'timestamp': timestamp
        }
        
        await self.firebase_handler.add_entry(ngram_data)
        return False

@loader.tds
class BroadMod(loader.Module):
    """Forwards messages containing specific keywords to a designated channel."""

    strings = {
        "name": "Broad",
        "cfg_firebase_path": "Путь к файлу учетных данных Firebase",
        "cfg_firebase_url": "URL базы данных Firebase",
        "cfg_forward_channel": "ID канала для пересылки сообщений",
        "cfg_ngram_size": "Размер n-грамм для сравнения сообщений",
        "cfg_similarity_threshold": "Порог схожести сообщений (от 0 до 1)",
        "cfg_ngram_retention": "Время хранения n-грамм (в секундах)",
        "cfg_max_ngram_entries": "Максимальное количество n-грамм в Firebase",
        "cfg_min_text_length": "Минимальная длина текста для обработки",
        "firebase_init_error": "❌ Ошибка инициализации Firebase: {error}",
        "sender_info": "👤 Отправитель: <a href='{sender_url}'>{sender_name}</a> ({sender_id})\n{scam_warning}\n💬 Источник: <a href='{message_url}'>{chat_title}</a>",
    }

    def init(self):
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
            "ngram_size",
            3,
            lambda: self.strings("cfg_ngram_size"),
            "similarity_threshold",
            0.7,
            lambda: self.strings("cfg_similarity_threshold"),
            "ngram_retention_period",
            86400,
            lambda: self.strings("cfg_ngram_retention"),
            "max_ngram_entries",
            1000,
            lambda: self.strings("cfg_max_ngram_entries"),
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
        self.similarity_checker = None
        self.initialized = False
        super().init()

    async def _initialize_firebase(self) -> bool:
        """Initialize Firebase connection."""
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
            
            self.similarity_checker = NgramSimilarityChecker(
                db_ref=self.db_ref,
                n=self.config["ngram_size"],
                similarity_threshold=self.config["similarity_threshold"],
                max_entries=self.config["max_ngram_entries"],
                retention_period=self.config["ngram_retention_period"]
            )
            
            await self.similarity_checker.initialize()

            chats_ref = self.db_ref.child("allowed_chats")
            chats_data = chats_ref.get()
            self.allowed_chats = chats_data if isinstance(chats_data, list) else []

            self.initialized = True
        except Exception as e:
            log.error(f"❌ Error loading data from Firebase: {e}")
            self.initialized = False
            
        if not self.processing_task:
            self.processing_task = asyncio.create_task(self.process_queue())

    async def process_queue(self):
        """Processes messages from the queue with a delay."""
        while True:
            messages, sender_info = await self.message_queue.get()
            try:
                await asyncio.sleep(13)
                forwarded = await self.client.forward_messages(
                    entity=self.config["forward_channel_id"], messages=messages
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
        """Get formatted sender information."""
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
        """Check if user ID exists in scammer database."""
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

            if chat_i