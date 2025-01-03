import asyncio
import html
import logging
import os
import re
import time
from asyncio import Queue

import firebase_admin
from firebase_admin import credentials, db as firebase_db
from telethon import errors, types

from .. import loader

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
)
log = logging.getLogger(__name__)


class BatchProcessor:
    """Handles batched writes of n-grams to Firebase to reduce overhead."""

    def __init__(
        self, db_ref: firebase_db.Reference, max_entries: int, batch_size: int = 50
    ):
        self.db_ref = db_ref
        self.max_entries = max_entries
        self.batch_size = batch_size
        self.batch = []

    async def add(self, ngram_data: dict):
        """Adds n-gram data to the batch. Flushes the batch if it's full."""
        self.batch.append(ngram_data)
        if len(self.batch) >= self.batch_size:
            await self.flush()

    async def flush(self):
        """Writes the accumulated n-gram data to Firebase."""
        if not self.batch:
            return
        try:
            current_batch = self.batch[:]
            self.batch.clear()

            ngrams_ref = self.db_ref.child("hashes/hash_list")
            current_entries = ngrams_ref.get() or []

            if not isinstance(current_entries, list):
                log.warning(
                    "Invalid data type received from Firebase. Resetting entries list."
                )
                current_entries = []
            current_entries.extend(current_batch)

            if len(current_entries) > self.max_entries:
                current_entries = current_entries[-self.max_entries :]
            ngrams_ref.set(current_entries)
        except Exception as e:
            log.error(f"Error flushing n-grams to Firebase: {e}", exc_info=True)
            self.batch.extend(current_batch)


class NgramSimilarityChecker:
    """Handles message similarity detection using n-grams."""

    def __init__(
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
        self.firebase_handler = BatchProcessor(db_ref, max_entries)

    def generate_ngrams(self, text: str) -> set[str]:
        """Generate n-grams from input text."""
        text = text.lower().strip()
        padded = f"{'_' * (self.n-1)}{text}{'_' * (self.n-1)}"
        return {padded[i : i + self.n] for i in range(len(padded) - self.n + 1)}

    def calculate_similarity(self, ngrams1: set[str], ngrams2: set[str]) -> float:
        """Calculate Jaccard similarity between two sets of n-grams."""
        if not ngrams1 or not ngrams2:
            return 0.0
        intersection = len(ngrams1.intersection(ngrams2))
        union = len(ngrams1.union(ngrams2))
        return intersection / union if union > 0 else 0.0

    async def initialize(self) -> None:
        """Load existing n-grams from Firebase."""
        try:
            hashes_ref = self.firebase_handler.db_ref.child("hashes/hash_list")
            all_hashes = hashes_ref.get() or []
            current_time = time.time()

            for hash_data in all_hashes:
                if isinstance(hash_data, dict):
                    timestamp = hash_data.get("timestamp", 0)
                    if current_time - timestamp < self.retention_period:
                        ngrams = set(hash_data.get("ngrams", []))
                        if ngrams:
                            self.ngram_cache[hash(frozenset(ngrams))] = (ngrams, timestamp)
        except Exception as e:
            log.error(f"Error loading n-grams: {e}", exc_info=True)

    async def is_similar_to_cached(self, text: str, timestamp: float) -> bool:
        """Check if text is similar to any cached messages."""
        current_ngrams = self.generate_ngrams(text)
        
        # Обновляем кэш, удаляя устаревшие записи
        self.ngram_cache = {
            hash_val: (ngrams, ts)
            for hash_val, (ngrams, ts) in self.ngram_cache.items()
            if timestamp - ts < self.retention_period
        }

        # Проверяем схожесть с существующими n-граммами
        for ngrams, _ in self.ngram_cache.values():
            similarity = self.calculate_similarity(current_ngrams, ngrams)
            if similarity >= self.similarity_threshold:
                return True

        # Добавляем новые n-граммы в кэш и Firebase
        cache_key = hash(frozenset(current_ngrams))
        self.ngram_cache[cache_key] = (current_ngrams, timestamp)

        ngram_data = {
            "hash": cache_key,
            "ngrams": list(current_ngrams),
            "timestamp": timestamp,
        }
        await self.firebase_handler.add(ngram_data)
        return False


@loader.tds
class BroadMod(loader.Module):
    """Forwards messages containing specific keywords to a designated channel."""

    strings = {
        "name": "Broad",
        "cfg_firebase_path": "Путь к файлу учетных данных Firebase",
        "cfg_firebase_url": "URL базы данных Firebase",
        "cfg_forward_channel": "ID канала для пересылки сообщений",
        "cfg_cleanup_interval": "Интервал очистки кэша (в секундах)",
        "cfg_ngram_retention": "Время хранения n-грамм (в секундах)",
        "cfg_max_ngrams": "Максимальное количество n-грамм в Firebase",
        "cfg_min_text_length": "Минимальная длина текста для обработки",
        "firebase_init_error": "❌ Ошибка инициализации Firebase: {error}",
        "sender_info": "<a href='{sender_url}'>👤 {sender_name}</a> [{sender_id}]\n{scam_warning}\n<a href='{message_url}'>🍜 жмяк</a>",
        "cfg_ngram_size": "Размер n-грамм для сравнения сообщений",
        "cfg_similarity_threshold": "Порог схожести сообщений (от 0 до 1)",
        "reconnecting": "Переподключение к Firebase...",
        "reconnection_success": "Переподключение успешно завершено.",
        "reconnection_failed": "Переподключение не удалось: {error}",
        "cleanup_success": "Старые n-граммы успешно очищены.",
        "cleanup_failed": "Очистка старых n-грамм не удалась: {error}",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "firebase_credentials_path",
            "/root/Heroku/loll-8a3bd-firebase-adminsdk-4pvtd-18ca6920ec.json",
            lambda: self.strings("cfg_firebase_path"),
            "firebase_database_url",
            "https://loll-8a3bd-default-rtdb.firebaseio.com",
            lambda: self.strings("cfg_firebase_url"),
            "forward_channel_id",
            2498567519,
            lambda: self.strings("cfg_forward_channel"),
            "cleanup_interval",
            3600,
            lambda: self.strings("cfg_cleanup_interval"),
            "ngram_retention_period",
            86400,
            lambda: self.strings("cfg_ngram_retention"),
            "max_ngrams",
            1000,
            lambda: self.strings("cfg_max_ngrams"),
            "min_text_length",
            18,
            lambda: self.strings("cfg_min_text_length"),
            "max_cleanup_attempts",
            3,
            lambda: "Максимальное количество попыток очистки",
            "max_reconnection_attempts",
            5,
            lambda: "Максимальное количество попыток переподключения",
            "reconnection_cooldown",
            300,
            lambda: "Время ожидания между попытками переподключения (в секундах)",
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
            "ngram_size",
            3,
            lambda: self.strings("cfg_ngram_size"),
            "similarity_threshold",
            0.7,
            lambda: self.strings("cfg_similarity_threshold"),
        )

        self.message_queue = Queue()
        self.processing_task = None
        self.allowed_chats = []
        self.firebase_app = None
        self.db_ref = None
        self.last_cleanup_time = 0
        self.initialized = False
        self.similarity_checker = None
        self.reconnection_attempts = 0
        self.last_reconnection_time = 0
        super().__init__()

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
            self.similarity_checker = NgramSimilarityChecker(
                db_ref=self.db_ref,
                n=self.config["ngram_size"],
                similarity_threshold=self.config["similarity_threshold"],
                max_entries=self.config["max_ngrams"],
                retention_period=self.config["ngram_retention_period"],
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

    async def process_queue(self):
        """Processes messages from the queue with a delay."""
        while True:
            messages, sender_info = await self.message_queue.get()
            try:
                await asyncio.sleep(13)
                if messages:
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
            except errors.MessageIdInvalidError:
                log.warning(
                    "Невозможно переслать сообщение. Возможно, оно было удалено или недоступно."
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
                else f"tg://openmessage?user_id={message.sender.id}"
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
                "message_url": message_url,
                "scam_warning": (
                    f"╰┈➤⚠️ <a href='{post_link}'>Есть в базе скамеров.</a>\n"
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

    @loader.command(func=lambda _: True)
    async def managecmd(self, message):
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

    async def watcher(self, message):
        """Process and forward messages"""
        if (
            not self.initialized
            or message.chat_id not in self.allowed_chats
            or (sender := getattr(message, "sender", None)) is None
            or getattr(sender, "bot", False)
            or not self.similarity_checker
        ):
            return

        if not await self._ensure_firebase_connection():
            log.error("Firebase connection lost and reconnection failed")
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

            current_time = time.time()
            
            # Проверяем схожесть с существующими сообщениями
            if await self.similarity_checker.is_similar_to_cached(normalized_text, current_time):
                return

            messages = []
            if hasattr(message, "grouped_id") and message.grouped_id:
                grouped_messages = []
                async for msg in self.client.iter_messages(
                    message.chat_id, limit=10, offset_date=message.date
                ):
                    if (
                        hasattr(msg, "grouped_id")
                        and msg.grouped_id == message.grouped_id
                    ):
                        grouped_messages.append(msg)
                # Сортируем сообщения по ID
                messages = sorted(grouped_messages, key=lambda m: m.id)
            else:
                messages = [message]

            sender_info = await self._get_sender_info(message)
            await self.message_queue.put((messages, sender_info))

        except Exception as e:
            log.error(f"Error in watcher: {e}", exc_info=True)

    async def _ensure_firebase_connection(self) -> bool:
        """
        Проверяет соединение с Firebase и пытается переподключиться при необходимости.
        """
        if self.initialized and self.db_ref:
            try:
                self.db_ref.child("test_connection").get()
                return True
            except Exception as e:
                log.warning(f"Firebase connection test failed: {e}")

        current_time = time.time()
        if (
            self.reconnection_attempts >= self.config["max_reconnection_attempts"]
            or current_time - self.last_reconnection_time < self.config["reconnection_cooldown"]
        ):
            return False

        try:
            log.info(self.strings["reconnecting"])
            self.reconnection_attempts += 1
            self.last_reconnection_time = current_time

            if await self._initialize_firebase():
                await self.similarity_checker.initialize()
                
                chats_ref = self.db_ref.child("allowed_chats")
                chats_data = chats_ref.get()
                self.allowed_chats = chats_data if isinstance(chats_data, list) else []

                self.initialized = True
                self.reconnection_attempts = 0
                log.info(self.strings["reconnection_success"])
                return True
        except Exception as e:
            log.error(self.strings["reconnection_failed"].format(error=str(e)))
        return False

    async def _cleanup_old_ngrams(self) -> bool:
        """
        Очищает старые n-граммы из Firebase.
        """
        current_time = time.time()
        if current_time - self.last_cleanup_time < self.config["cleanup_interval"]:
            return True

        for attempt in range(self.config["max_cleanup_attempts"]):
            try:
                ngrams_ref = self.db_ref.child("hashes/hash_list")  # оставляем для совместимости
                all_entries = ngrams_ref.get() or []

                if not isinstance(all_entries, list):
                    log.warning("Invalid data type for n-grams in Firebase during cleanup")
                    return False

                filtered_entries = [
                    entry for entry in all_entries
                    if isinstance(entry, dict)
                    and current_time - entry.get("timestamp", 0) < self.config["ngram_retention_period"]
                ]

                if len(filtered_entries) == len(all_entries):
                    return True

                ngrams_ref.set(filtered_entries)
                self.last_cleanup_time = current_time

                log.info(f"Cleaned up {len(all_entries) - len(filtered_entries)} old n-grams")
                return True

            except Exception as e:
                log.error(f"Cleanup attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2**attempt)
        return False

    @loader.command
    async def cleanupcmd(self, message: types.Message) -> None:
        """Очищает старые n-граммы из базы данных."""
        if not self.initialized:
            await message.reply("❌ Модуль не инициализирован.")
            return

        try:
            if not await self._ensure_firebase_connection():
                await message.reply("❌ Нет подключения к Firebase.")
                return

            await message.reply("🔄 Начинаю очистку старых n-грамм...")
            success = await self._cleanup_old_ngrams()

            if success:
                await message.reply(self.strings["cleanup_success"])
            else:
                await message.reply(self.strings["cleanup_failed"].format(
                    error="превышено количество попыток"
                ))
        except Exception as e:
            await message.reply(self.strings["cleanup_failed"].format(error=str(e)))
