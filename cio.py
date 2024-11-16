import asyncio
import html
import logging
import os
import re
import time
import bisect
from asyncio import Queue
from typing import List, Dict, Tuple, Optional, Set

import firebase_admin
from firebase_admin import credentials, db as firebase_db
from telethon import errors, types, utils as telethon_utils
from .. import loader, utils

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
)

# Добавляем name вместо name

log = logging.getLogger(name)


class NgramFirebaseHandler:
    """Handles storage and retrieval of n-grams in Firebase."""

    def init(
        self,
        db_ref: firebase_db.Reference,
        max_entries: int = 1000,
        batch_size: int = 50,
    ):
        # Исправлено init на init

        self.db_ref = db_ref
        self.max_entries = max_entries
        self.batch_size = batch_size
        self.batch = []
        self.ngram_ref = self.db_ref.child("ngrams/entries")

    async def add_entry(self, ngram_data: dict) -> None:
        """Adds an n-gram entry to the batch. Flushes if batch is full."""
        self.batch.append(ngram_data)
        if len(self.batch) >= self.batch_size:
            await self.flush()

    async def flush(self) -> None:
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

    async def load_entries(
        self, retention_period: float
    ) -> Dict[int, Tuple[Set[str], float]]:
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
        # Исправлено init на init

        self.n = n
        self.similarity_threshold = similarity_threshold
        self.retention_period = retention_period
        self.ngram_cache: Dict[int, Tuple[Set[str], float]] = {}
        self.firebase_handler = NgramFirebaseHandler(db_ref, max_entries)

    def generate_ngrams(self, text: str) -> Set[str]:
        """Generate n-grams from input text."""
        text = text.lower().strip()
        padded = f"{'_' * (self.n-1)}{text}{'_' * (self.n-1)}"
        return {padded[i : i + self.n] for i in range(len(padded) - self.n + 1)}

    def calculate_similarity(self, ngrams1: Set[str], ngrams2: Set[str]) -> float:
        """Calculate Jaccard similarity between two sets of n-grams."""
        if not ngrams1 or not ngrams2:
            return 0.0
        intersection = len(ngrams1.intersection(ngrams2))
        union = len(ngrams1.union(ngrams2))
        return intersection / union if union > 0 else 0.0

    async def initialize(self) -> None:
        """Load existing n-grams from Firebase."""
        self.ngram_cache = await self.firebase_handler.load_entries(
            self.retention_period
        )

    async def is_similar_to_cached(self, text: str, timestamp: float) -> bool:
        """Check if text is similar to any cached messages."""
        current_ngrams = self.generate_ngrams(text)

        # Обновляем кэш, удаляя устаревшие записи

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
            "hash": cache_key,
            "ngrams": list(current_ngrams),
            "timestamp": timestamp,
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
        self.message_queue: Queue = Queue()
        self.processing_task: Optional[asyncio.Task] = None
        self.allowed_chats: List[int] = []
        self.firebase_app = None
        self.db_ref: Optional[firebase_db.Reference] = None
        self.similarity_checker: Optional[NgramSimilarityChecker] = None
        self.initialized: bool = False
        self.client = None
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

    async def client_ready(self, client, db) -> None:
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
                max_entries=self.config["max_ngram_entries"],
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

    async def process_queue(self) -> None:
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

    @loader.command
    async def managecmd(self, message: types.Message) -> None:
        """Manages the list of allowed chats."""
        if not self.initialized:
            await message.reply(
                "❌ Модуль не инициализирован. Проверьте настройки Firebase."
            )
            return
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
            if self.db_ref:
                chats_ref = self.db_ref.child("allowed_chats")
                chats_ref.set(self.allowed_chats)
                await message.reply(txt)
            else:
                await message.reply("❌ Ошибка доступа к Firebase.")
        except Exception as e:
            log.error(f"Error in managecmd: {e}", exc_info=True)
            await message.reply(f"❌ Ошибка при управлении списком чатов: {str(e)}")

    async def watcher(self, message: types.Message) -> None:
        """Process and forward messages"""
        if not message or not hasattr(message, "chat_id"):
            return
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
            current_time = time.time()
            if not self.similarity_checker:
                log.error("Similarity checker not initialized")
                return
            if await self.similarity_checker.is_similar_to_cached(
                normalized_text, current_time
            ):
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
                # Сортируем сгруппированные сообщения по ID

                messages = sorted(grouped_messages, key=lambda m: m.id)
            else:
                messages = [message]
            sender_info = await self._get_sender_info(message)
            if sender_info:
                await self.message_queue.put((messages, sender_info))
        except Exception as e:
            log.error(f"Error in watcher: {e}", exc_info=True)














# Добавляем в класс NgramFirebaseHandler новые методы:


class NgramFirebaseHandler:
    def init(
        self,
        db_ref: firebase_db.Reference,
        max_entries: int = 1000,
        batch_size: int = 50,
        cleanup_threshold: int = 5000,  # Порог для запуска очистки
        max_cleanup_attempts: int = 3,  # Максимальное количество попыток очистки
    ):
        self.db_ref = db_ref
        self.max_entries = max_entries
        self.batch_size = batch_size
        self.batch = []
        self.ngram_ref = self.db_ref.child("ngrams/entries")
        self.cleanup_threshold = cleanup_threshold
        self.max_cleanup_attempts = max_cleanup_attempts
        self.last_cleanup_time = 0
        self.cleanup_interval = 3600  # Минимальный интервал между очистками (1 час)

    async def cleanup_old_ngrams(self, retention_period: float) -> bool:
        """
        Очищает старые n-граммы из Firebase.

        Args:
            retention_period: Период хранения в секундах

        Returns:
            bool: True если очистка успешна, False в противном случае
        """
        current_time = time.time()

        # Проверяем, прошло ли достаточно времени с последней очистки

        if current_time - self.last_cleanup_time < self.cleanup_interval:
            return True
        for attempt in range(self.max_cleanup_attempts):
            try:
                # Получаем все записи

                entries = self.ngram_ref.get() or []
                if not isinstance(entries, list):
                    log.warning(
                        "Invalid data type for n-grams in Firebase during cleanup"
                    )
                    return False
                # Фильтруем устаревшие записи

                filtered_entries = [
                    entry
                    for entry in entries
                    if isinstance(entry, dict)
                    and current_time - entry.get("timestamp", 0) < retention_period
                ]

                # Если количество записей не уменьшилось, пропускаем обновление

                if len(filtered_entries) == len(entries):
                    return True
                # Обновляем записи в Firebase

                self.ngram_ref.set(filtered_entries)
                self.last_cleanup_time = current_time

                log.info(
                    f"Cleaned up {len(entries) - len(filtered_entries)} old n-grams"
                )
                return True
            except Exception as e:
                log.error(f"Cleanup attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2**attempt)  # Экспоненциальная задержка
        return False

    async def check_and_cleanup(self, retention_period: float) -> None:
        """Проверяет необходимость очистки и выполняет её при необходимости."""
        try:
            entries = self.ngram_ref.get() or []
            if isinstance(entries, list) and len(entries) > self.cleanup_threshold:
                await self.cleanup_old_ngrams(retention_period)
        except Exception as e:
            log.error(f"Error during cleanup check: {e}")


# Добавляем в класс BroadMod новые методы и модифицируем существующие:


@loader.tds
class BroadMod(loader.Module):
    strings = {
        # ... (существующие строки) ...
        "reconnecting": "🔄 Переподключение к Firebase...",
        "reconnection_success": "✅ Переподключение к Firebase успешно выполнено",
        "reconnection_failed": "❌ Ошибка переподключения к Firebase: {error}",
        "cleanup_success": "🧹 Очистка старых n-грамм завершена успешно",
        "cleanup_failed": "❌ Ошибка при очистке старых n-грамм: {error}",
    }

    def init(self):
        # ... (существующая инициализация) ...

        self.reconnection_attempts = 0
        self.max_reconnection_attempts = 5
        self.last_reconnection_time = 0
        self.reconnection_cooldown = 300  # 5 минут между попытками
        super().init()

    async def _ensure_firebase_connection(self) -> bool:
        """
        Проверяет соединение с Firebase и пытается переподключиться при необходимости.

        Returns:
            bool: True если соединение активно, False в противном случае
        """
        if self.initialized and self.db_ref:
            try:
                # Пробуем выполнить тестовый запрос

                self.db_ref.child("test_connection").get()
                return True
            except Exception as e:
                log.warning(f"Firebase connection test failed: {e}")
        current_time = time.time()
        if (
            self.reconnection_attempts >= self.max_reconnection_attempts
            or current_time - self.last_reconnection_time < self.reconnection_cooldown
        ):
            return False
        try:
            log.info(self.strings["reconnecting"])
            self.reconnection_attempts += 1
            self.last_reconnection_time = current_time

            # Пытаемся переинициализировать Firebase

            if await self._initialize_firebase():
                # Переинициализируем обработчик n-грамм

                self.similarity_checker = NgramSimilarityChecker(
                    db_ref=self.db_ref,
                    n=self.config["ngram_size"],
                    similarity_threshold=self.config["similarity_threshold"],
                    max_entries=self.config["max_ngram_entries"],
                    retention_period=self.config["ngram_retention_period"],
                )
                await self.similarity_checker.initialize()

                # Загружаем список разрешенных чатов

                chats_ref = self.db_ref.child("allowed_chats")
                chats_data = chats_ref.get()
                self.allowed_chats = chats_data if isinstance(chats_data, list) else []

                self.initialized = True
                self.reconnection_attempts = (
                    0  # Сбрасываем счетчик после успешного подключения
                )
                log.info(self.strings["reconnection_success"])
                return True
        except Exception as e:
            log.error(self.strings["reconnection_failed"].format(error=str(e)))
        return False

    @loader.command
    async def cleanupcmd(self, message: types.Message) -> None:
        """Очищает старые n-граммы из базы данных."""
        if not self.initialized or not self.similarity_checker:
            await message.reply("❌ Модуль не инициализирован.")
            return
        try:
            if not await self._ensure_firebase_connection():
                await message.reply("❌ Нет подключения к Firebase.")
                return
            await message.reply("🔄 Начинаю очистку старых n-грамм...")

            success = await self.similarity_checker.firebase_handler.cleanup_old_ngrams(
                self.config["ngram_retention_period"]
            )

            if success:
                await message.reply(self.strings["cleanup_success"])
            else:
                await message.reply(
                    self.strings["cleanup_failed"].format(
                        error="превышено количество попыток"
                    )
                )
        except Exception as e:
            await message.reply(self.strings["cleanup_failed"].format(error=str(e)))

    # Модифицируем метод watcher для использования нового функционала

    async def watcher(self, message: types.Message) -> None:
        """Process and forward messages"""
        if not message or not hasattr(message, "chat_id"):
            return
        if (
            not self.initialized
            or message.chat_id not in self.allowed_chats
            or (sender := getattr(message, "sender", None)) is None
            or getattr(sender, "bot", False)
        ):
            return
        # Проверяем соединение с Firebase

        if not await self._ensure_firebase_connection():
            log.error("Firebase connection lost and reconnection failed")
            return
        try:
            # ... (существующий код watcher) ...

            # Добавляем периодическую проверку необходимости очистки

            await self.similarity_checker.firebase_handler.check_and_cleanup(
                self.config["ngram_retention_period"]
            )

            # ... (оставшийся код watcher) ...
        except Exception as e:
            log.error(f"Error in watcher: {e}", exc_info=True)
