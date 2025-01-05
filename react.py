import asyncio
import html
import logging
import os
import re
import time
from asyncio import Queue
from collections import OrderedDict, deque
from typing import Optional, Tuple, List, Dict, Any, Set

import firebase_admin
from firebase_admin import credentials, db as firebase_db
from telethon import types, errors

from .. import loader

logging.basicConfig(format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

BATCH_SIZE = 50
MAX_BATCH_RETRIES = 3
LOCAL_QUEUE_MAXSIZE = 2000
NGRAM_CACHE_CHUNK_SIZE = 100

class LocalQueue:
    def __init__(self, max_size: int):
        self.queue = deque(maxlen=max_size)
    def add(self, data: dict) -> None:
        self.queue.append(data)
    def get_all(self) -> List[dict]:
        items = list(self.queue)
        self.queue.clear()
        return items
    def __len__(self) -> int:
        return len(self.queue)

class BatchProcessor:
    # ... (остальная часть класса BatchProcessor без изменений)
    def __init__(self, db_reference: firebase_db.Reference, batch_path: str, max_elements_in_firebase: int, batch_size: int, max_retries: int, local_queue_max_size: int):
        self.db_reference = db_reference
        self.batch_path = batch_path
        self.max_elements_in_firebase = max_elements_in_firebase
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.current_batch: List[Dict] = []
        self.retries_count = 0
        self.local_queue = LocalQueue(maxsize=local_queue_max_size)
        self.local_queue_max_size = local_queue_max_size
    async def add(self, data: Dict) -> None:
        self.current_batch.append(data)
        if len(self.current_batch) >= self.batch_size:
            await self.flush()
    async def flush(self) -> None:
        if not self.current_batch:
            return
        batch_to_process = self.current_batch[:]
        self.current_batch.clear()
        pending_items = self.local_queue.get_all()
        if pending_items:
            batch_to_process.extend(pending_items)
            log.warning("LocalQueue->CurrentBatch '%s'. LocalQueue size: %s", self.batch_path, len(self.local_queue))
        try:
            async def transaction(current_data):
                current_data = current_data or []; current_data.extend(batch_to_process); return current_data[-self.max_elements_in_firebase:]
            await self.db_reference.child(self.batch_path).transaction(transaction)
            self.retries_count = 0
            log.info("Flushed %s to '%s'.", len(batch_to_process), self.batch_path)
        except Exception as e:
            log.error("Flush error '%s' (Attempt %s): %s", self.batch_path, self.retries_count + 1, e)
            self.retries_count += 1
            if self.retries_count <= self.max_retries:
                for item in batch_to_process:
                    self.local_queue.add(item)
                log.warning("CurrentBatch->LocalQueue '%s'. LocalQueue size: %s", self.batch_path, len(self.local_queue))
                if len(self.local_queue) >= self.local_queue_max_size * 0.8:
                    log.warning("LocalQueue near capacity '%s': %s/%s", self.batch_path, len(self.local_queue), self.local_queue_max_size)
            else:
                log.error("Max retries for '%s'. Discarding %s.", self.batch_path, len(batch_to_process))

class NgramSimilarityChecker:
    # ... (остальная часть класса NgramSimilarityChecker без изменений)
    def __init__(self, db_reference: firebase_db.Reference, ngram_size: int, similarity_threshold: float, max_ngram_records: int, max_media_cache_records: int, ngram_retention_period: float, text_hash_processor: BatchProcessor, media_hash_processor: BatchProcessor):
        self.ngram_size = ngram_size
        self.similarity_threshold = similarity_threshold
        self.ngram_retention_period = ngram_retention_period
        self.text_cache: OrderedDict[Any, Any] = OrderedDict()
        self.media_cache: OrderedDict[Any, Any] = OrderedDict()
        self.max_ngram_cache_size = max_ngram_records
        self.max_media_cache_size = max_media_cache_records
        self.text_hash_processor = text_hash_processor
        self.media_hash_processor = media_hash_processor
        self._load_lock = asyncio.Lock()
    def _maintain_cache_size(self, cache: OrderedDict, max_size: int) -> None:
        while len(cache) > max_size:
            cache.popitem(last=False)
    async def load_chunk_from_db(self, db_reference: firebase_db.Reference, start_after: Optional[str] = None, chunk_size: int = NGRAM_CACHE_CHUNK_SIZE) -> List[Tuple[str, Dict[str, Any]]]:
        query = db_reference.order_by_key()
        if start_after:
            query = query.start_at(start_after)
        query = query.limit_to_first(chunk_size)
        try:
            data = await asyncio.wait_for(query.get(), timeout=10)
            return list(data.items()) if data else []
        except Exception as e:
            log.error("Error loading chunk from %s: %s", db_reference.path, e)
            return []
    async def initialize(self) -> None:
        async with self._load_lock:
            current_time = time.time()
            await self._load_cache_from_firebase(self.text_hash_processor.db_reference.child("hashes/text_hashes"), self.text_cache, self.max_ngram_cache_size, current_time)
            await self._load_cache_from_firebase(self.media_hash_processor.db_reference.child("hashes/media_ids"), self.media_cache, self.max_media_cache_size, current_time)
            log.info("Loaded %s text, %s media.", len(self.text_cache), len(self.media_cache))
    async def _load_cache_from_firebase(self, db_reference: firebase_db.Reference, cache: OrderedDict, max_size: int, current_time: float):
        last_key = None
        while True:
            chunk = await self.load_chunk_from_db(db_reference, last_key)
            if not chunk:
                break
            for key, item in chunk:
                if isinstance(item, dict) and "timestamp" in item and current_time - item["timestamp"] < self.ngram_retention_period:
                    if db_reference.path == "/hashes/text_hashes" and "hash" in item and "ngrams" in item:
                        cache[item["hash"]] = tuple(item["ngrams"])
                    elif db_reference.path == "/hashes/media_ids" and "media_id" in item:
                        cache[item["media_id"]] = item["timestamp"]
                    self._maintain_cache_size(cache, max_size)
            if len(chunk) < NGRAM_CACHE_CHUNK_SIZE:
                break
            last_key = chunk[-1][0] if chunk else None
    def generate_ngrams(self, text: str) -> Set[str]:
        normalized_text = re.sub(r"\s+", " ", text.lower().strip())
        normalized_text = re.sub(r"[^\w\s]", "", normalized_text)
        padded_text = f"{'_' * (self.ngram_size - 1)}{normalized_text}{'_' * (self.ngram_size - 1)}"
        return {padded_text[i:i + self.ngram_size] for i in range(len(padded_text) - self.ngram_size + 1)}
    def calculate_similarity(self, ngrams1: Set[str], ngrams2: Set[str]) -> float:
        if not ngrams1 or not ngrams2:
            return 0.0
        intersection_length = len(ngrams1.intersection(ngrams2))
        union_length = len(ngrams1.union(ngrams2))
        return intersection_length / union_length if union_length > 0 else 0.0
    async def _get_media_id(self, message: types.Message) -> Optional[int]:
        media_funcs = {
            types.MessageMediaPhoto: lambda m: m.photo.id,
            types.MessageMediaDocument: lambda m: m.document.id,
        }
        try:
            if message.media:
                for media_type, func in media_funcs.items():
                    if isinstance(message.media, media_type):
                        return func(message.media)

            if hasattr(message, "grouped_id") and message.grouped_id:
                async for msg in message.client.iter_messages(message.chat_id, ids=message.id):
                    if msg.grouped_id == message.grouped_id and msg.media:
                        for media_type, func in media_funcs.items():
                            if isinstance(msg.media, media_type):
                                return func(msg.media)
            return None
        except Exception as e:
            log.error("Error getting media ID: %s", e)
            return None
    async def is_duplicate_cached(self, message: types.Message, timestamp: float, album_messages: Optional[List[types.Message]] = None) -> bool:
        if message.media:
            media_id = await self._get_media_id(message)
            if media_id and media_id in self.media_cache:
                return True
            if media_id:
                await self.media_hash_processor.add({"type": "media", "media_id": media_id, "timestamp": timestamp})
            return False
        else:
            text = message.text or message.raw_text
            if not text:
                return False
            current_ngrams = self.generate_ngrams(text)
            if not current_ngrams:
                return False
            for cached_ngrams in self.text_cache.values():
                if self.calculate_similarity(current_ngrams, set(cached_ngrams)) >= self.similarity_threshold:
                    return True
            cache_key = hash(frozenset(current_ngrams))
            await self.text_hash_processor.add({"type": "text", "hash": cache_key, "ngrams": list(current_ngrams), "timestamp": timestamp})
            self.text_cache[cache_key] = tuple(current_ngrams)
            self._maintain_cache_size(self.text_cache, self.max_ngram_cache_size)
            return False

class BroadMod(loader.Module):
    strings = {
        "name": "Broad", "cfg_firebase_path": "Firebase creds path", "cfg_firebase_url": "Firebase DB URL",
        "cfg_forward_channel": "Forward channel ID", "cfg_cleanup_interval": "Cache cleanup interval (s)",
        "cfg_ngram_retention": "Record retention (s)", "cfg_max_ngrams": "Max n-gram records",
        "cfg_max_media_cache": "Max local media cache", "cfg_min_text_length": "Min text length",
        "firebase_init_error": "Firebase init err: {error}",
        "sender_info": "<a href='{sender_url}'>👤 {sender_name}</a> [{sender_id}]\n{scam_warning}\n<a href='{message_url}'>🍜</a>",
        "cfg_ngram_size": "N-gram size", "cfg_similarity_threshold": "Similarity threshold (0-1)",
        "reconnecting": "Reconnecting to Firebase...", "reconnection_success": "Reconnected!",
        "reconnection_failed": "Reconnect failed: {error}", "cleanup_success": "Old records cleaned.",
        "cleanup_failed": "Cleanup failed: {error}", "queue_full": "Queue full. Msg from {sender_id} dropped.",
    }
    def __init__(self):
        self.config = loader.ModuleConfig(
            "firebase_credentials_path", "/root/...", lambda: self.strings("cfg_firebase_path"),
            "firebase_database_url", "https://...", lambda: self.strings("cfg_firebase_url"),
            "forward_channel_id", 123, lambda: self.strings("cfg_forward_channel"),
            "cleanup_interval", 3600, lambda: self.strings("cfg_cleanup_interval"),
            "ngram_retention_period", 86400, lambda: self.strings("cfg_ngram_retention"),
            "max_ngrams", 1000, lambda: self.strings("cfg_max_ngrams"),
            "max_media_cache_size", 500, lambda: self.strings("cfg_max_media_cache"),
            "min_text_length", 18, lambda: self.strings("cfg_min_text_length"),
            "ngram_size", 3, lambda: self.strings("cfg_ngram_size"),
            "similarity_threshold", 0.7, lambda: self.strings("cfg_similarity_threshold"),
            "max_cleanup_attempts", 3, lambda: "Max cleanup attempts",
            "max_reconnection_attempts", 5, lambda: "Max reconnect attempts",
            "reconnection_cooldown", 300, lambda: "Reconnect cooldown (s)",
            "trading_keywords", [], lambda: "Keywords",
            "forward_delay", 13, lambda: "Forward delay (s)",
            "max_queue_size", 1000, lambda: "Max queue size",
            "batch_size", BATCH_SIZE, lambda: "Batch size",
            "max_batch_retries", MAX_BATCH_RETRIES, lambda: "Max batch retries",
            "local_queue_maxsize", LOCAL_QUEUE_MAXSIZE, lambda: "Local queue max size",
            "forward_retries", 3, lambda: "Forward attempts", # Добавлено для гибкости
        )
        self.message_queue: Queue[Tuple[List[types.Message], Dict[str, Any]]] = Queue(maxsize=self.config["max_queue_size"])
        self.processing_task: Optional[asyncio.Task] = None
        self.firebase_app: Any = None
        self.db_reference: Optional[firebase_db.Reference] = None
        self.similarity_checker: Optional[NgramSimilarityChecker] = None
        self._database_lock = asyncio.Lock()
        self.allowed_chat_ids: Set[int] = set()
        self.is_initialized = False
        self.last_cleanup_time = 0
        self.reconnection_attempt_count = 0
        self.last_reconnection_time = 0
        self.processed_message_count = 0
        self.forwarded_message_count = 0
        self.failure_event_count = 0
    async def client_ready(self, client, db):
        self.client = client
        if not os.path.exists(self.config["firebase_credentials_path"]):
            log.warning("Firebase creds not found.")
            return
        if not self.config["firebase_database_url"]:
            log.warning("Firebase DB URL not set.")
            return
        if not await self._initialize_firebase():
            return
        try:
            text_hasher = BatchProcessor(db_reference=self.db_reference, batch_path="hashes/text_hashes",
                max_elements_in_firebase=self.config["max_ngrams"], batch_size=self.config["batch_size"],
                max_retries=self.config["max_batch_retries"], local_queue_max_size=self.config["local_queue_maxsize"])
            media_hasher = BatchProcessor(db_reference=self.db_reference, batch_path="hashes/media_ids",
                max_elements_in_firebase=self.config["max_media_cache_size"], batch_size=self.config["batch_size"],
                max_retries=self.config["max_batch_retries"], local_queue_max_size=self.config["local_queue_maxsize"])
            self.similarity_checker = NgramSimilarityChecker(db_reference=self.db_reference, ngram_size=self.config["ngram_size"],
                similarity_threshold=self.config["similarity_threshold"], max_ngram_records=self.config["max_ngrams"],
                max_media_cache_records=self.config["max_media_cache_size"],
                ngram_retention_period=self.config["ngram_retention_period"],
                text_hash_processor=text_hasher, media_hash_processor=media_hasher)
            await self.similarity_checker.initialize()
            await self._load_allowed_chats()
            self.is_initialized = True
        except Exception as e:
            log.error(self.strings["firebase_init_error"].format(error=e), exc_info=True)
            self.is_initialized = False
        if not self.processing_task or self.processing_task.done():
            self.processing_task = asyncio.create_task(self._process_queue())
    async def _initialize_firebase(self) -> bool:
        try:
            if not firebase_admin._apps:
                creds = credentials.Certificate(self.config["firebase_credentials_path"])
                self.firebase_app = firebase_admin.initialize_app(creds, {"databaseURL": self.config["firebase_database_url"]})
            self.db_reference = firebase_db.reference("/")
            return True
        except Exception as e:
            log.error(self.strings["firebase_init_error"].format(error=e), exc_info=True)
            return False
    async def _load_allowed_chats(self):
        try:
            allowed_chats_data = await self.db_reference.child("allowed_chats").get()
            self.allowed_chat_ids = set(allowed_chats_data) if isinstance(allowed_chats_data, list) else set()
            log.info("Loaded allowed chats: %s", self.allowed_chat_ids)
        except Exception as e:
            log.error("Error loading allowed chats: %s", e, exc_info=True)
    async def _process_queue(self):
        while True:
            try:
                messages, sender_info = await self.message_queue.get()
                await asyncio.sleep(self.config["forward_delay"])
                await self._forward_and_inform(messages, sender_info)
                self.processed_message_count += len(messages)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("Error processing queue: %s", e, exc_info=True)
            finally:
                self.message_queue.task_done()
    async def _forward_messages(self, messages: List[types.Message]) -> Optional[List[types.Message]]:
        for attempt in range(self.config["forward_retries"]): # Используем конфигурацию
            try:
                return await self.client.forward_messages(self.config["forward_channel_id"], messages)
            except errors.FloodWaitError as e:
                log.warning("Flood wait, sleeping for %ss", e.seconds); await asyncio.sleep(e.seconds)
            except errors.MessageIdInvalidError:
                log.warning("Cannot forward some messages, probably deleted.")
                return None
            except Exception as e:
                log.error("Error forwarding messages (Attempt %s): %s", attempt + 1, e, exc_info=True); await asyncio.sleep(2**attempt)
        return None
    async def _forward_and_inform(self, messages: List[types.Message], sender_info: Dict[str, Any]):
        forwarded_messages = await self._forward_messages(messages)
        if forwarded_messages:
            self.forwarded_message_count += len(forwarded_messages)
            first_forwarded_message = forwarded_messages[0]
            for attempt in range(self.config["max_batch_retries"]): # Добавлена логика повторных попыток
                try:
                    await self.client.send_message(self.config["forward_channel_id"],
                        self.strings["sender_info"].format(**sender_info), reply_to=first_forwarded_message.id,
                        parse_mode="html", link_preview=False)
                    break # Выйти из цикла, если отправка успешна
                except errors.FloodWaitError as e:
                    log.warning("Flood wait при отправке информации об отправителе, сплю %ss", e.seconds)
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    log.error("Ошибка отправки информации об отправителе (Попытка %s): %s", attempt + 1, e, exc_info=True)
                    await asyncio.sleep(2**attempt) # Экспоненциальная задержка
            else:
                log.error("Не удалось отправить информацию об отправителе после нескольких попыток.")

    async def _get_sender_info(self, message: types.Message) -> Dict[str, Any]:
        try:
            sender = await self.client.get_entity(message.sender_id)
            chat = await self.client.get_entity(message.chat_id)
            sender_url = f"tg://user?id={sender.id}"
            sender_name = html.escape(sender.first_name or "Unknown")
            scammer_info = await self._check_scammer(message.sender_id)
            chat_type_prefix = "c" if isinstance(chat, types.Channel) else "t.me"
            chat_username = getattr(chat, "username", None)
            message_id = message.id
            chat_id_or_username = chat.id if isinstance(chat, types.Channel) else chat_username
            message_url = f"https://t.me/{chat_type_prefix}/{chat_id_or_username}/{message_id}" if chat_id_or_username else ""
            return {
                "sender_id": sender.id, "sender_url": sender_url, "sender_name": sender_name,
                "scam_warning": f"⚠️ <a href='{scammer_info[1]}'>Scammer in DB.</a>\n" if scammer_info[0] else "",
                "message_url": message_url,
            }
        except Exception as e:
            log.error("Error getting sender info: %s", e, exc_info=True)
            return {}
    async def _check_scammer(self, user_id: int) -> Tuple[bool, Optional[str]]:
        try:
            entity = await self.client.get_entity("bezscamasuka")
            async for msg in self.client.iter_messages(entity, search=str(user_id), limit=1):
                return True, f"https://t.me/bezscamasuka/{msg.id}"
        except Exception as e:
            log.error("Error checking scammer: %s", e, exc_info=True)
            return False, None
    async def _process_album(self, message: types.Message, timestamp: float):
        album_messages = await self._get_album_messages(message)
        if album_messages and not await self.similarity_checker.is_duplicate_cached(album_messages[0], timestamp, album_messages):
            await self._enqueue_messages(album_messages, await self._get_sender_info(message))

    async def _get_album_messages(self, message: types.Message) -> Optional[List[types.Message]]:
        if not getattr(message, "grouped_id", None):
            return None
        messages = []
        try:
            async for msg in self.client.iter_messages(message.chat_id, grouped_id=message.grouped_id):
                messages.append(msg)
        except Exception as e:
            log.error("Error getting album messages: %s", e, exc_info=True)
            return None
        return messages

    async def _enqueue_messages(self, messages: List[types.Message], sender_info: Dict[str, Any]):
        if self.message_queue.full():
            log.warning(self.strings["queue_full"].format(sender_id=sender_info.get("sender_id", "Unknown")))
            return
        await self.message_queue.put((messages, sender_info))

    async def _process_media_message(self, message: types.Message, timestamp: float):
        if not await self.similarity_checker.is_duplicate_cached(message, timestamp):
            await self._enqueue_messages([message], await self._get_sender_info(message))

    async def _process_text_message(self, message: types.Message, timestamp: float):
        text = message.text or message.raw_text or ""
        if len(text) >= self.config["min_text_length"] and any(kw in text.lower() for kw in self.config["trading_keywords"]):
            if not await self.similarity_checker.is_duplicate_cached(message, timestamp):
                await self._enqueue_messages([message], await self._get_sender_info(message))

    async def watcher(self, message: types.Message):
        if not self.is_initialized or message.chat_id not in self.allowed_chat_ids or getattr(message.sender, "bot", False):
            return
        if not await self._ensure_firebase_connection():
            return
        try:
            timestamp = time.time()
            if getattr(message, "grouped_id", None):
                await self._process_album(message, timestamp)
            elif message.media:
                await self._process_media_message(message, timestamp)
            else:
                await self._process_text_message(message, timestamp)
            await self._cleanup_old_data()
        except Exception as e:
            log.error("Error in watcher: %s", e, exc_info=True)

    async def _ensure_firebase_connection(self) -> bool:
        if self.is_initialized and self.db_reference:
            try:
                await self.db_reference.child(".info/connected").get()
                return True
            except Exception:
                log.warning("Firebase connection lost.")
        current_time = time.time()
        if self.reconnection_attempt_count >= self.config["max_reconnection_attempts"] or current_time - self.last_reconnection_time < self.config["reconnection_cooldown"]:
            return False
        self.reconnection_attempt_count += 1
        self.last_reconnection_time = current_time
        log.info(self.strings["reconnecting"])
        try:
            if await self._initialize_firebase():
                if self.similarity_checker:
                    await self.similarity_checker.initialize()
                await self._load_allowed_chats()
                self.is_initialized = True
                self.reconnection_attempt_count = 0
                log.info(self.strings["reconnection_success"])
                return True
        except Exception as e:
            log.error(self.strings["reconnection_failed"].format(error=str(e)), exc_info=True)
            self.failure_event_count += 1
        return False

    async def _cleanup_old_data(self):
        current_time = time.time()
        if current_time - self.last_cleanup_time < self.config["cleanup_interval"]:
            return
        for attempt in range(self.config["max_cleanup_attempts"]):
            try:
                log.info("Starting cleanup (Attempt %s).", attempt + 1)
                start_time = time.time()
                await self._cleanup_collection("hashes/text_hashes", self.config["ngram_retention_period"])
                await self._cleanup_collection("hashes/media_ids", self.config["ngram_retention_period"])
                self.last_cleanup_time = current_time
                log.info("Cleanup finished in %.2fs.", time.time() - start_time)
                return
            except Exception as e:
                log.error("Cleanup failed (Attempt %s): %s", attempt + 1, e, exc_info=True)
                await asyncio.sleep(2**attempt)
                self.failure_event_count += 1
        log.warning("Maximum cleanup attempts reached.")

    async def _cleanup_collection(self, path: str, retention_period: float):
        reference = self.db_reference.child(path)
        current_time = time.time()
        deleted_count = 0
        batch_keys = []
        try:
            # Получаем ключи записей, которые нужно удалить
            snapshot = await reference.order_by_child("timestamp").end_at(current_time - retention_period).limit_to_first(1000).get()
            if snapshot:
                batch_keys = list(snapshot.keys())

                # Удаляем записи батчами
                for i in range(0, len(batch_keys), 100):
                    batch = batch_keys[i:i + 100]
                    update_data = {key: None for key in batch}
                    await reference.update(update_data)
                    deleted_count += len(batch)

            log.info("Cleaned %s old records from %s", deleted_count, path)
        except Exception as e:
            log.error("Error cleaning %s: %s", path, e)

    async def managecmd(self, message):
        args = message.text.split()
        if len(args) != 3 or args[1] not in ["add", "remove"]:
            return await message.respond("Use: .managecmd [add|remove] <chat_id>")
        try:
            chat_id = int(args[2])
        except ValueError:
            return await message.respond("Invalid chat ID.")
        if args[1] == "add":
            if chat_id not in self.allowed_chat_ids:
                self.allowed_chat_ids.add(chat_id)
                await self._update_allowed_chats()
                await message.respond(f"Chat {chat_id} added.")
            else:
                await message.respond("Chat already added.")
        elif args[1] == "remove":
            if chat_id in self.allowed_chat_ids:
                self.allowed_chat_ids.discard(chat_id)
                await self._update_allowed_chats()
                await message.respond(f"Chat {chat_id} removed.")
            else:
                await message.respond("Chat not found.")

    async def _update_allowed_chats(self):
        await self.db_reference.child("allowed_chats").set(list(self.allowed_chat_ids))
