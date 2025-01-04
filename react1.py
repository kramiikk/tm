import asyncio
import html
import logging
import os
import re
import time
from asyncio import Queue
from collections import OrderedDict, deque
from typing import Optional, Tuple, List, Dict, Any

import firebase_admin
from firebase_admin import credentials, db as firebase_db
from telethon import errors, types

from .. import loader

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", 
    level=logging.WARNING
)
log = logging.getLogger(__name__)

class LocalQueue:
    """Local queue for failed Firebase operations."""
    
    def __init__(self, maxsize: int = 1000):
        self.queue = deque(maxlen=maxsize)
        
    def add(self, data: dict) -> None:
        self.queue.append(data)
        
    def get_all(self) -> List[dict]:
        items = list(self.queue)
        self.queue.clear()
        return items

class BatchProcessor:
    """Handles batched writes to Firebase with local fallback."""

    def __init__(
        self, 
        db_ref: firebase_db.Reference, 
        base_path: str, 
        max_entries: int, 
        batch_size: int = 50, 
        max_retries: int = 3
    ):
        self.db_ref = db_ref
        self.base_path = base_path
        self.max_entries = max_entries
        self.batch_size = batch_size
        self.batch = []
        self.max_retries = max_retries
        self.retries = 0
        self.local_queue = LocalQueue()
        self.last_successful_write = 0
        
    async def add(self, data: dict) -> None:
        """Adds data to the batch with backup to local queue if Firebase fails."""
        self.batch.append(data)
        if len(self.batch) >= self.batch_size:
            if not await self.flush():
                # If Firebase flush fails, store in local queue
                for item in self.batch:
                    self.local_queue.add(item)
                log.info(f"Added {len(self.batch)} items to local queue after Firebase failure")
                self.batch.clear()

    async def flush(self) -> bool:
        """Writes the accumulated data to Firebase with improved error handling."""
        if not self.batch:
            return True
            
        try:
            current_batch = self.batch[:]
            self.batch.clear()

            # Try to write any pending items from local queue first
            pending_items = self.local_queue.get_all()
            if pending_items:
                current_batch.extend(pending_items)
                log.info(f"Attempting to write {len(pending_items)} pending items from local queue")

            list_ref = self.db_ref.child(self.base_path)
            staging_ref = self.db_ref.child(f"{self.base_path}_staging")

            # Use transaction to ensure atomic updates
            def transaction(current_data):
                if current_data is None:
                    current_data = []
                if not isinstance(current_data, list):
                    current_data = []
                current_data.extend(current_batch)
                if len(current_data) > self.max_entries:
                    current_data = current_data[-self.max_entries:]
                return current_data

            list_ref.transaction(transaction)
            self.last_successful_write = time.time()
            self.retries = 0
            log.info(f"Successfully flushed {len(current_batch)} entries to Firebase")
            return True

        except Exception as e:
            log.error(f"Error flushing to Firebase (Attempt {self.retries + 1}): {e}", exc_info=True)
            self.retries += 1
            if self.retries <= self.max_retries:
                # Store failed batch in local queue
                for item in current_batch:
                    self.local_queue.add(item)
                log.warning(f"Stored {len(current_batch)} items in local queue for retry")
                return False
            else:
                log.error(f"Maximum retry attempts reached. Discarding {len(current_batch)} entries")
                self.retries = 0
                return False

class NgramSimilarityChecker:
    """Handles message similarity detection using n-grams and media IDs."""

    def __init__(
        self,
        db_ref: firebase_db.Reference,
        n: int = 3,
        similarity_threshold: float = 0.7,
        max_ngram_entries: int = 1000,
        max_media_cache_size: int = 500,
        retention_period: float = 86400,
    ):
        self.n = n
        self.similarity_threshold = similarity_threshold
        self.retention_period = retention_period
        self.ngram_cache = OrderedDict()  # Changed to OrderedDict for LRU behavior
        self.media_cache = OrderedDict()
        self.max_ngram_cache_size = max_ngram_entries
        self.max_media_cache_size = max_media_cache_size
        self.ngram_firebase_handler = BatchProcessor(db_ref, "hashes/text_hashes", max_ngram_entries)
        self.media_firebase_handler = BatchProcessor(db_ref, "hashes/media_ids", max_media_cache_size)
        self._load_lock = asyncio.Lock()
        
    def _maintain_cache_size(self, cache: OrderedDict, max_size: int) -> None:
        """Maintains cache size using LRU eviction."""
        while len(cache) > max_size:
            cache.popitem(last=False)
            
    async def load_data_chunk(
        self, 
        ref: firebase_db.Reference, 
        start_at: Optional[str] = None,
        chunk_size: int = 100
    ) -> List[Dict[str, Any]]:
        """Loads data from Firebase in chunks to avoid memory issues."""
        query = ref.order_by_key()
        if start_at:
            query = query.start_at(start_at)
        query = query.limit_to_first(chunk_size)
        try:
            return query.get() or []
        except Exception as e:
            log.error(f"Error loading data chunk: {e}")
            return []

    async def initialize(self) -> None:
        """Load existing data from Firebase with improved chunking and error handling."""
        async with self._load_lock:  # Prevent concurrent initialization
            try:
                current_time = time.time()
                
                # Load text hashes in chunks
                text_hashes_ref = self.ngram_firebase_handler.db_ref.child("hashes/text_hashes")
                last_key = None
                while True:
                    chunk = await self.load_data_chunk(text_hashes_ref, last_key)
                    if not chunk:
                        break
                        
                    for item in chunk:
                        if (
                            isinstance(item, dict) 
                            and item.get("timestamp", 0) > current_time - self.retention_period
                            and item.get("type") == "text" 
                            and "hash" in item
                        ):
                            self.ngram_cache[item["hash"]] = (set(item.get("ngrams", [])), item["timestamp"])
                            self._maintain_cache_size(self.ngram_cache, self.max_ngram_cache_size)
                    
                    if len(chunk) < 100:  # No more data
                        break
                    last_key = list(chunk.keys())[-1]
                
                # Load media IDs similarly
                media_ids_ref = self.media_firebase_handler.db_ref.child("hashes/media_ids")
                last_key = None
                while True:
                    chunk = await self.load_data_chunk(media_ids_ref, last_key)
                    if not chunk:
                        break
                        
                    for item in chunk:
                        if (
                            isinstance(item, dict) 
                            and item.get("timestamp", 0) > current_time - self.retention_period
                            and item.get("type") == "media" 
                            and "media_id" in item
                        ):
                            self.media_cache[item["media_id"]] = item["timestamp"]
                            self._maintain_cache_size(self.media_cache, self.max_media_cache_size)
                    
                    if len(chunk) < 100:
                        break
                    last_key = list(chunk.keys())[-1]
                
                log.info(f"Successfully loaded {len(self.ngram_cache)} text hashes and {len(self.media_cache)} media IDs")
                
            except Exception as e:
                log.error(f"Error during initialization: {e}", exc_info=True)
                raise

    async def is_similar_to_cached(self, message: types.Message, timestamp: float) -> bool:
        """Check message similarity with improved caching and error handling."""
        current_time = time.time()
        
        # Clean up caches using LRU
        self.ngram_cache = OrderedDict(
            (k, v) for k, v in self.ngram_cache.items()
            if current_time - v[1] < self.retention_period
        )
        self.media_cache = OrderedDict(
            (k, v) for k, v in self.media_cache.items()
            if current_time - v < self.retention_period
        )
        
        if message.media:
            media_id = await self._get_media_id(message)
            if not media_id:
                return False
                
            if media_id in self.media_cache:
                return True
                
            # Check Firebase only if not found in cache
            try:
                query = (self.media_firebase_handler.db_ref
                        .child("hashes/media_ids")
                        .order_by_child("media_id")
                        .equal_to(media_id)
                        .limit_to_first(1))
                result = query.get()
                
                if result:
                    self.media_cache[media_id] = timestamp
                    self._maintain_cache_size(self.media_cache, self.max_media_cache_size)
                    return True
                    
                await self.media_firebase_handler.add({
                    "type": "media",
                    "media_id": media_id,
                    "timestamp": timestamp
                })
                self.media_cache[media_id] = timestamp
                self._maintain_cache_size(self.media_cache, self.max_media_cache_size)
                return False
                
            except Exception as e:
                log.error(f"Error checking media similarity: {e}")
                return False
        
        else:
            text = message.text or message.raw_text
            if not text:
                return False
                
            try:
                current_ngrams = self.generate_ngrams(text)
                
                # Check cache first
                for hash_val, (ngrams, _) in self.ngram_cache.items():
                    if self.calculate_similarity(current_ngrams, ngrams) >= self.similarity_threshold:
                        return True
                        
                # If not found in cache, check Firebase
                cache_key = hash(frozenset(current_ngrams))
                self.ngram_cache[cache_key] = (current_ngrams, timestamp)
                self._maintain_cache_size(self.ngram_cache, self.max_ngram_cache_size)
                
                await self.ngram_firebase_handler.add({
                    "type": "text",
                    "hash": cache_key,
                    "ngrams": list(current_ngrams),
                    "timestamp": timestamp
                })
                return False
                
            except Exception as e:
                log.error(f"Error checking text similarity: {e}")
                return False

    async def _get_media_id(self, message: types.Message) -> Optional[int]:
        """Extract media ID from message with album support."""
        try:
            if isinstance(message.media, types.MessageMediaPhoto):
                return message.media.photo.id
            elif isinstance(message.media, types.MessageMediaDocument):
                return message.media.document.id
            elif hasattr(message, 'grouped_id') and message.grouped_id:
                async for msg in message.client.iter_messages(
                    message.chat_id, 
                    ids=message.id
                ):
                    if msg.grouped_id == message.grouped_id and msg.media:
                        if isinstance(msg.media, types.MessageMediaPhoto):
                            return msg.media.photo.id
                        elif isinstance(msg.media, types.MessageMediaDocument):
                            return msg.media.document.id
            return None
        except Exception as e:
            log.error(f"Error getting media ID: {e}")
            return None

    def generate_ngrams(self, text: str) -> set[str]:
        """Generate n-grams with improved text normalization."""
        text = re.sub(r'\s+', ' ', text.lower().strip())
        text = re.sub(r'[^\w\s]', '', text)
        padded = f"{'_' * (self.n-1)}{text}{'_' * (self.n-1)}"
        return {padded[i:i + self.n] for i in range(len(padded) - self.n + 1)}

    def calculate_similarity(self, ngrams1: set[str], ngrams2: set[str]) -> float:
        """Calculate Jaccard similarity with validation."""
        if not ngrams1 or not ngrams2:
            return 0.0
        try:
            intersection = len(ngrams1.intersection(ngrams2))
            union = len(ngrams1.union(ngrams2))
            return intersection / union if union > 0 else 0.0
        except Exception as e:
            log.error(f"Error calculating similarity: {e}")
            return 0.0

@loader.tds
class BroadMod(loader.Module):
    """Forwards messages containing specific keywords to a designated channel with improved handling."""

    strings = {
        "name": "Broad",
        "cfg_firebase_path": "Path to Firebase credentials file",
        "cfg_firebase_url": "Firebase database URL",
        "cfg_forward_channel": "Target channel ID for forwarding",
        "cfg_cleanup_interval": "Cache cleanup interval (seconds)",
        "cfg_ngram_retention": "Data retention period (seconds)",
        "cfg_max_ngrams": "Maximum n-gram entries in Firebase",
        "cfg_max_media_cache": "Maximum media cache size",
        "cfg_min_text_length": "Minimum text length for processing",
        "firebase_init_error": "❌ Firebase initialization error: {error}",
        "sender_info": "<a href='{sender_url}'>👤 {sender_name}</a> [{sender_id}]\n{scam_warning}\n<a href='{message_url}'>🍜 Source</a>",
        "cfg_ngram_size": "N-gram size for comparison",
        "cfg_similarity_threshold": "Similarity threshold (0-1)",
        "reconnecting": "Reconnecting to Firebase...",
        "reconnection_success": "Successfully reconnected.",
        "reconnection_failed": "Reconnection failed: {error}",
        "cleanup_success": "Old records cleaned up.",
        "cleanup_failed": "Cleanup failed: {error}",
    }

    FORWARD_DELAY = 13  # Delay before forwarding (seconds)
    MAX_QUEUE_SIZE = 1000  # Maximum size for message queue
    FLOOD_WAIT_BASE = 900  # Base delay for flood control (seconds)

    def __init__(self):
        self.config = loader.ModuleConfig(
            "firebase_credentials_path",
            os.getenv("FIREBASE_CREDENTIALS_PATH", "/root/Heroku/loll-8a3bd-firebase-adminsdk-4pvtd-18ca6920ec.json"),
            lambda: self.strings("cfg_firebase_path"),
            
            "firebase_database_url",
            os.getenv("FIREBASE_DATABASE_URL", "https://loll-8a3bd-default-rtdb.firebaseio.com"),
            lambda: self.strings("cfg_firebase_url"),
            
            "forward_channel_id",
            int(os.getenv("FORWARD_CHANNEL_ID", "2498567519")),
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
            
            "max_media_cache_size",
            500,
            lambda: self.strings("cfg_max_media_cache"),
            
            "min_text_length",
            18,
            lambda: self.strings("cfg_min_text_length"),
            
            "max_cleanup_attempts",
            3,
            lambda: "Maximum cleanup attempts",
            
            "max_reconnection_attempts",
            5,
            lambda: "Maximum reconnection attempts",
            
            "reconnection_cooldown",
            300,
            lambda: "Reconnection cooldown period (seconds)",
            
            "trading_keywords",
            [
                "акк", "прод", "куп", "обмен", "лег", "оруж", "артефакты",
                "ивент", "100", "гарант", "уд", "утер", "луна", "ранг",
                "AR", "ищу", "приор", "стандарт", "евро", "уров", "старт",
                "сигна", "руб", "крыл", "срочн", "кто",
            ],
            lambda: "Keywords triggering message forwarding",
            
            "ngram_size",
            3,
            lambda: self.strings("cfg_ngram_size"),
            
            "similarity_threshold",
            0.7,
            lambda: self.strings("cfg_similarity_threshold"),
        )

        self.message_queue = Queue(maxsize=self.MAX_QUEUE_SIZE)
        self.processing_task = None
        self.allowed_chats = set()  # Changed to set for O(1) lookups
        self.firebase_app = None
        self.db_ref = None
        self.last_cleanup_time = 0
        self.initialized = False
        self.similarity_checker = None
        self.reconnection_attempts = 0
        self.last_reconnection_time = 0
        self._db_lock = asyncio.Lock()  # Lock for database operations
        super().__init__()

    async def client_ready(self, client, db):
        """Initialize module when Telethon client is ready."""
        self.client = client
        
        if not await self._validate_config():
            return

        if not await self._initialize_firebase():
            return

        try:
            self.similarity_checker = NgramSimilarityChecker(
                db_ref=self.db_ref,
                n=self.config["ngram_size"],
                similarity_threshold=self.config["similarity_threshold"],
                max_ngram_entries=self.config["max_ngrams"],
                max_media_cache_size=self.config["max_media_cache_size"],
                retention_period=self.config["ngram_retention_period"],
            )
            await self.similarity_checker.initialize()

            async with self._db_lock:
                chats_ref = self.db_ref.child("allowed_chats")
                chats_data = chats_ref.get()
                self.allowed_chats = set(chats_data if isinstance(chats_data, list) else [])

            self.initialized = True
            if not self.processing_task or self.processing_task.done():
                self.processing_task = asyncio.create_task(self.process_queue())
                
        except Exception as e:
            log.error(f"Error during initialization: {e}", exc_info=True)
            self.initialized = False

    async def _validate_config(self) -> bool:
        """Validate configuration parameters."""
        if not self.config["firebase_credentials_path"] or not os.path.exists(
            self.config["firebase_credentials_path"]
        ):
            log.error("Firebase credentials file not found or path is incorrect")
            return False
            
        if not self.config["firebase_database_url"]:
            log.error("Firebase database URL is not configured")
            return False
            
        if not self.config["forward_channel_id"]:
            log.error("Forward channel ID is not configured")
            return False
            
        return True

    async def process_queue(self):
        """Process messages from queue with improved error handling."""
        while True:
            try:
                messages, sender_info = await self.message_queue.get()
                
                try:
                    await asyncio.sleep(self.FORWARD_DELAY)
                    
                    if not messages:
                        continue
                        
                    forwarded = await self._forward_messages(messages)
                    
                    if forwarded:
                        await self._send_sender_info(forwarded, sender_info)
                        
                    await self._cleanup_old_ngrams()
                    
                except Exception as e:
                    log.error(f"Error processing queue item: {e}", exc_info=True)
                    
                finally:
                    self.message_queue.task_done()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Critical error in queue processing: {e}", exc_info=True)
                await asyncio.sleep(5)  # Prevent tight error loop

    async def _forward_messages(self, messages: List[types.Message]) -> Optional[types.Message]:
        """Forward messages with retry logic."""
        for attempt in range(3):  # Max 3 attempts
            try:
                forwarded = await self.client.forward_messages(
                    entity=self.config["forward_channel_id"],
                    messages=messages
                )
                log.info(f"Successfully forwarded {len(messages)} messages")
                return forwarded
                
            except errors.FloodWaitError as e:
                wait_time = self.FLOOD_WAIT_BASE + e.seconds
                log.warning(f"FloodWaitError: waiting {wait_time} seconds")
                await asyncio.sleep(wait_time)
                
            except errors.MessageIdInvalidError:
                log.warning("Message unavailable or deleted")
                return None
                
            except Exception as e:
                log.error(f"Error forwarding messages (attempt {attempt + 1}): {e}")
                await asyncio.sleep(2 ** attempt)
                
        return None

    async def _send_sender_info(self, forwarded: types.Message, sender_info: dict):
        """Send sender information as reply to forwarded message."""
        try:
            reply_to_id = None
            if isinstance(forwarded, list) and forwarded:
                reply_to_id = forwarded[0].id
            elif forwarded:
                reply_to_id = forwarded.id

            if reply_to_id:
                await self.client.send_message(
                    entity=self.config["forward_channel_id"],
                    message=self.strings["sender_info"].format(**sender_info),
                    reply_to=reply_to_id,
                    parse_mode="html",
                    link_preview=False,
                )
                
        except Exception as e:
            log.error(f"Error sending sender info: {e}", exc_info=True)

    async def _get_sender_info(self, message: types.Message) -> dict:
        """Get formatted sender information with improved error handling."""
        try:
            sender = message.sender
            if not sender:
                return {}

            sender_name = (
                "Deleted Account"
                if getattr(sender, "deleted", False)
                else getattr(sender, "first_name", "Unknown")
            )

            sender_url = (
                f"https://t.me/{sender.username}"
                if getattr(sender, "username", None)
                else f"tg://openmessage?user_id={sender.id}"
            )

            chat = message.chat
            message_url = (
                f"https://t.me/{chat.username}/{message.id}"
                if getattr(chat, "username", None)
                else f"https://t.me/c/{str(chat.id)[4:]}/{message.id}"
            )

            is_scammer, post_link = await self.check_scammer(sender.id)

            return {
                "sender_name": html.escape(sender_name),
                "sender_id": sender.id,
                "sender_url": sender_url,
                "message_url": message_url,
                "scam_warning": f"╰┈➤⚠️ <a href='{post_link}'>Scammer database match.</a>\n" if is_scammer else "",
            }
            
        except Exception as e:
            log.error(f"Error getting sender info: {e}", exc_info=True)
            return {}

    async def check_scammer(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """Check if user is in scammer database with improved search."""
        try:
            messages = await self.client.get_messages(
                1539778138,  # Scammer database channel ID
                search=str(user_id),
                limit=1,
                filter=lambda m: str(user_id) in (m.text or "")
            )

            if messages and messages[0]:
                post_link = f"https://t.me/bezscamasuka/{messages[0].id}"
                return True, post_link

        except Exception as e:
            log.error(f"Error checking scammer status: {e}", exc_info=True)
            
        return False, None

    async def watcher(self, message):
        """Process and forward messages with improved validation and error handling."""
        if not self._should_process_message(message):
            return

        if not await self._ensure_firebase_connection():
            log.error("Firebase connection lost and reconnection failed")
            return

        try:
            current_time = time.time()

            if message.media:
                if await self._process_media_message(message, current_time):
                    return
            else:
                if await self._process_text_message(message, current_time):
                    return

        except Exception as e:
            log.error(f"Error in watcher: {e}", exc_info=True)

    def _should_process_message(self, message) -> bool:
        """Check if message should be processed."""
        return (
            self.initialized
            and message.chat_id in self.allowed_chats
            and hasattr(message, "sender")
            and message.sender
            and not getattr(message.sender, "bot", False)
            and self.similarity_checker
        )

    async def _process_media_message(self, message: types.Message, current_time: float) -> bool:
        """Process media message."""
        try:
            if await self.similarity_checker.is_similar_to_cached(message, current_time):
                return True

            sender_info = await self._get_sender_info(message)
            await self.message_queue.put(([message], sender_info))
            return True
            
        except Exception as e:
            log.error(f"Error processing media message: {e}", exc_info=True)
            return False

    async def _process_text_message(self, message: types.Message, current_time: float) -> bool:
        """Process text message."""
        try:
            text = message.text or message.raw_text or ""
            if len(text) < self.config["min_text_length"]:
                return True

            if not self._contains_keywords(text):
                return True

            if await self.similarity_checker.is_similar_to_cached(message, current_time):
                return True

            messages = await self._get_grouped_messages(message) if message.grouped_id else [message]
            sender_info = await self._get_sender_info(message)
            await self.message_queue.put((messages, sender_info))
            return True
            
        except Exception as e:
            log.error(f"Error processing text message: {e}", exc_info=True)
            return False

    def _contains_keywords(self, text: str) -> bool:
        """Check if text contains any keywords."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.config["trading_keywords"])

    async def _get_grouped_messages(self, message: types.Message) -> List[types.Message]:
        """Get all messages in an album."""
        try:
            messages = []
            async for msg in self.client.iter_messages(
                message.chat_id,
                limit=10,
                offset_date=message.date
            ):
                if msg.grouped_id == message.grouped_id:
                    messages.append(msg)
            return sorted(messages, key=lambda m: m.id)
        except Exception as e:
            log.error(f"Error getting grouped messages: {e}", exc_info=True)
            return [message]

    @loader.command
    async def managecmd(self, message: types.Message) -> None:
        """Manage allowed chats with improved validation."""
        try:
            args = message.text.split()
            
            # Display current chats if no arguments
            if len(args) != 2:
                response = "📝 Allowed chats:\n"
                response += ", ".join(map(str, self.allowed_chats)) or "empty"
                await message.reply(response)
                return
                
            # Validate chat ID
            try:
                chat_id = int(args[1])
            except ValueError:
                await message.reply("❌ Invalid chat ID format")
                return
                
            # Update allowed chats
            if chat_id in self.allowed_chats:
                self.allowed_chats.remove(chat_id)
                action = "removed from"
            else:
                self.allowed_chats.add(chat_id)
                action = "added to"
                
            # Update Firebase
            await self._update_allowed_chats()
            
            await message.reply(f"✅ Chat {chat_id} {action} allowed list")
            
        except Exception as e:
            log.error(f"Error in managecmd: {e}", exc_info=True)
            await message.reply("❌ Error managing allowed chats")

    async def _update_allowed_chats(self) -> None:
        """Update allowed chats in Firebase with retry logic."""
        for attempt in range(3):
            try:
                chats_ref = self.db_ref.child("allowed_chats")
                chats_ref.set(list(self.allowed_chats))
                break
            except Exception as e:
                if attempt == 2:
                    log.error(f"Failed to update allowed chats: {e}")
                await asyncio.sleep(2 ** attempt)

    async def watcher(self, message: types.Message) -> None:
        """Watch and process messages with improved filtering."""
        if not self._should_process_message(message):
            return
            
        try:
            current_time = time.time()
            
            # Process media messages
            if message.media:
                await self._process_media_message(message, current_time)
                return
                
            # Process text messages
            await self._process_text_message(message, current_time)
                
        except Exception as e:
            log.error(f"Error in watcher: {e}", exc_info=True)

    def _should_process_message(self, message: types.Message) -> bool:
        """Check if message should be processed."""
        return (
            self.initialized
            and message.chat_id in self.allowed_chats
            and getattr(message, "sender", None) is not None
            and not getattr(message.sender, "bot", False)
            and self.similarity_checker is not None
        )

    async def _process_media_message(self, message: types.Message, timestamp: float) -> None:
        """Process media messages."""
        if await self.similarity_checker.is_similar_to_cached(message, timestamp):
            return
            
        sender_info = await self._get_sender_info(message)
        await self.message_queue.put(([message], sender_info))

    async def _process_text_message(self, message: types.Message, timestamp: float) -> None:
        """Process text messages with keyword filtering."""
        text = message.text or ""
        if len(text) < self.config.get("min_text_length", 18):
            return
            
        # Check keywords
        low = text.lower()
        if not any(kw in low for kw in self.config.get("trading_keywords", [])):
            return
            
        # Clean text
        normalized_text = html.unescape(
            re.sub(r"<[^>]+>|[^\w\s,.!?;:—]|\s+", " ", low)
        ).strip()
        if not normalized_text:
            return
            
        # Check similarity
        if await self.similarity_checker.is_similar_to_cached(message, timestamp):
            return
            
        # Process message or album
        messages = await self._get_album_messages(message) or [message]
        sender_info = await self._get_sender_info(message)
        await self.message_queue.put((messages, sender_info))

    async def _get_album_messages(self, message: types.Message) -> Optional[List[types.Message]]:
        """Get all messages in an album."""
        if not (hasattr(message, "grouped_id") and message.grouped_id):
            return None
            
        grouped_messages = []
        async for msg in self.client.iter_messages(
            message.chat_id,
            limit=10,
            offset_date=message.date
        ):
            if (
                hasattr(msg, "grouped_id")
                and msg.grouped_id == message.grouped_id
            ):
                grouped_messages.append(msg)
                
        return sorted(grouped_messages, key=lambda m: m.id) if grouped_messages else None