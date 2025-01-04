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

class LocalCache:
    """Local cache implementation with backup persistence."""
    
    def __init__(self, max_size: int, retention_period: float):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.retention_period = retention_period
        self.backup_queue = deque(maxlen=1000)  # Store failed writes
        
    def add(self, key: Any, timestamp: float) -> None:
        """Add item to cache with LRU eviction."""
        self.cache[key] = timestamp
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
            
    def get(self, key: Any) -> Optional[float]:
        """Get item from cache if it exists and isn't expired."""
        if key in self.cache:
            timestamp = self.cache[key]
            if time.time() - timestamp < self.retention_period:
                return timestamp
            del self.cache[key]
        return None
        
    def cleanup(self) -> None:
        """Remove expired entries."""
        current_time = time.time()
        self.cache = OrderedDict(
            (k, v) for k, v in self.cache.items()
            if current_time - v < self.retention_period
        )
        
    def backup_failed_write(self, data: dict) -> None:
        """Store failed write for later retry."""
        self.backup_queue.append(data)
        
    async def process_backup_queue(self, processor) -> None:
        """Process backed up writes."""
        while self.backup_queue:
            data = self.backup_queue.popleft()
            try:
                await processor.add(data)
            except Exception as e:
                log.error(f"Error processing backup data: {e}")
                self.backup_queue.append(data)  # Re-add to queue
                break

class BatchProcessor:
    """Handles batched writes to Firebase with local backup."""

    def __init__(
        self, 
        db_ref: firebase_db.Reference, 
        base_path: str, 
        max_entries: int, 
        batch_size: int = 50,
        max_retries: int = 3,
        local_cache: LocalCache = None
    ):
        self.db_ref = db_ref
        self.base_path = base_path
        self.max_entries = max_entries
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.batch = []
        self.retries = 0
        self.local_cache = local_cache
        
    async def add(self, data: dict) -> None:
        """Add data to batch with local caching."""
        self.batch.append(data)
        if self.local_cache:
            if "media_id" in data:
                self.local_cache.add(data["media_id"], data["timestamp"])
            elif "hash" in data:
                self.local_cache.add(data["hash"], data["timestamp"])
                
        if len(self.batch) >= self.batch_size:
            await self.flush()

    async def flush(self) -> None:
        """Flush batch to Firebase with error handling and local backup."""
        if not self.batch:
            return
            
        current_batch = self.batch[:]
        self.batch.clear()
        
        try:
            # Use transaction for atomic updates
            def transaction(current_data):
                if not isinstance(current_data, list):
                    current_data = []
                current_data.extend(current_batch)
                if len(current_data) > self.max_entries:
                    current_data = current_data[-self.max_entries:]
                return current_data
                
            self.db_ref.child(self.base_path).transaction(transaction)
            self.retries = 0
            log.info(f"Flushed {len(current_batch)} entries to Firebase")
            
            # Process any backed up data
            if self.local_cache:
                await self.local_cache.process_backup_queue(self)
                
        except Exception as e:
            log.error(f"Error flushing to Firebase: {e}")
            self.retries += 1
            
            if self.retries <= self.max_retries:
                self.batch.extend(current_batch)
                log.warning(f"Retrying {len(current_batch)} entries later")
            else:
                if self.local_cache:
                    for item in current_batch:
                        self.local_cache.backup_failed_write(item)
                    log.info(f"Backed up {len(current_batch)} failed entries locally")
                else:
                    log.error(f"Discarding {len(current_batch)} entries after max retries")
                self.retries = 0

class NgramSimilarityChecker:
    """Handles message similarity detection with improved caching."""
    
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
        
        # Initialize local caches
        self.text_cache = LocalCache(max_ngram_entries, retention_period)
        self.media_cache = LocalCache(max_media_cache_size, retention_period)
        
        # Initialize Firebase handlers with local cache support
        self.text_handler = BatchProcessor(
            db_ref, 
            "hashes/text_hashes", 
            max_ngram_entries,
            local_cache=self.text_cache
        )
        self.media_handler = BatchProcessor(
            db_ref, 
            "hashes/media_ids", 
            max_media_cache_size,
            local_cache=self.media_cache
        )
        
    def generate_ngrams(self, text: str) -> set[str]:
        """Generate optimized n-grams from text."""
        text = text.lower().strip()
        words = re.findall(r'\w+', text)  # Split on word boundaries
        if not words:
            return set()
            
        padded = f"{'_' * (self.n-1)}{' '.join(words)}{'_' * (self.n-1)}"
        return {padded[i:i + self.n] for i in range(len(padded) - self.n + 1)}
        
    def calculate_similarity(self, ngrams1: set[str], ngrams2: set[str]) -> float:
        """Calculate Jaccard similarity with early exit optimizations."""
        if not ngrams1 or not ngrams2:
            return 0.0
            
        # Quick check - if sizes are very different, similarity will be low
        if min(len(ngrams1), len(ngrams2)) / max(len(ngrams1), len(ngrams2)) < self.similarity_threshold:
            return 0.0
            
        intersection = len(ngrams1.intersection(ngrams2))
        if intersection == 0:
            return 0.0
            
        union = len(ngrams1.union(ngrams2))
        return intersection / union if union > 0 else 0.0

    async def initialize(self) -> None:
        """Load existing data with improved error handling."""
        try:
            text_ref = self.text_handler.db_ref.child("hashes/text_hashes")
            media_ref = self.media_handler.db_ref.child("hashes/media_ids")
            
            # Load data in parallel
            text_data, media_data = await asyncio.gather(
                self._safe_get(text_ref),
                self._safe_get(media_ref)
            )
            
            current_time = time.time()
            
            # Process text entries
            for item in (text_data or []):
                if self._is_valid_entry(item, current_time):
                    self.text_cache.add(item["hash"], item["timestamp"])
                    
            # Process media entries
            for item in (media_data or []):
                if self._is_valid_entry(item, current_time):
                    self.media_cache.add(item["media_id"], item["timestamp"])
                    
            log.info(
                f"Loaded {len(self.text_cache.cache)} text hashes and "
                f"{len(self.media_cache.cache)} media IDs"
            )
            
        except Exception as e:
            log.error(f"Error loading data: {e}", exc_info=True)
            
    async def _safe_get(self, ref) -> Optional[List[Dict]]:
        """Safely get data from Firebase with retries."""
        for attempt in range(3):
            try:
                return ref.get()
            except Exception as e:
                if attempt == 2:
                    log.error(f"Failed to get data after 3 attempts: {e}")
                    return None
                await asyncio.sleep(2 ** attempt)
                
    def _is_valid_entry(self, item: Dict, current_time: float) -> bool:
        """Check if cache entry is valid and not expired."""
        return (
            isinstance(item, dict) 
            and "timestamp" in item
            and current_time - item["timestamp"] < self.retention_period
        )

    async def is_similar_to_cached(self, message: types.Message, timestamp: float) -> bool:
        """Check message similarity with improved caching."""
        # Clean caches periodically
        self.text_cache.cleanup()
        self.media_cache.cleanup()
        
        if message.media:
            return await self._check_media_similarity(message, timestamp)
        else:
            return await self._check_text_similarity(message, timestamp)
            
    async def _check_media_similarity(
        self, 
        message: types.Message, 
        timestamp: float
    ) -> bool:
        """Check media similarity with local cache first."""
        media_id = self._extract_media_id(message)
        if not media_id:
            return False
            
        # Check local cache first
        if self.media_cache.get(media_id):
            return True
            
        # Add to cache and Firebase
        await self.media_handler.add({
            "type": "media",
            "media_id": media_id,
            "timestamp": timestamp
        })
        return False
        
    async def _check_text_similarity(
        self, 
        message: types.Message, 
        timestamp: float
    ) -> bool:
        """Check text similarity with optimized n-gram comparison."""
        text = message.text or message.raw_text
        if not text:
            return False
            
        current_ngrams = self.generate_ngrams(text)
        if not current_ngrams:
            return False
            
        # Check similarity against cached entries
        for hash_val, ts in self.text_cache.cache.items():
            if time.time() - ts >= self.retention_period:
                continue
                
            # Get ngrams from Firebase only if timestamp is valid
            ngrams_data = await self._get_ngrams_for_hash(hash_val)
            if ngrams_data and self.calculate_similarity(
                current_ngrams, 
                set(ngrams_data)
            ) >= self.similarity_threshold:
                return True
                
        # Add new entry
        cache_key = hash(frozenset(current_ngrams))
        await self.text_handler.add({
            "type": "text",
            "hash": cache_key,
            "ngrams": list(current_ngrams),
            "timestamp": timestamp
        })
        return False
        
    def _extract_media_id(self, message: types.Message) -> Optional[int]:
        """Extract media ID with album support."""
        if isinstance(message.media, types.MessageMediaPhoto):
            return message.media.photo.id
        elif isinstance(message.media, types.MessageMediaDocument):
            return message.media.document.id
        return None
        
    async def _get_ngrams_for_hash(self, hash_val: int) -> Optional[List[str]]:
        """Get ngrams for hash value from Firebase."""
        try:
            data = self.text_handler.db_ref.child(
                f"hashes/text_hashes/{hash_val}/ngrams"
            ).get()
            return data if isinstance(data, list) else None
        except Exception as e:
            log.error(f"Error getting ngrams for hash {hash_val}: {e}")
            return None

@loader.tds
class BroadMod(loader.Module):
    """
    Enhanced message forwarding module with improved caching and error handling.
    """
    
    strings = {
        "name": "Broad",
        "cfg_firebase_path": "Path to Firebase credentials file",
        "cfg_firebase_url": "Firebase database URL",
        "cfg_forward_channel": "Forward channel ID",
        "sender_info": "<a href='{sender_url}'>👤 {sender_name}</a> [{sender_id}]\n{scam_warning}\n<a href='{message_url}'>🍜 Original</a>",
        "firebase_init_error": "❌ Firebase initialization error: {error}",
        "reconnecting": "Reconnecting to Firebase...",
        "reconnection_success": "Reconnection successful.",
        "reconnection_failed": "Reconnection failed: {error}",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "firebase_credentials_path",
            "/path/to/credentials.json",
            lambda: self.strings("cfg_firebase_path"),
            "firebase_database_url",
            "https://your-db.firebaseio.com",
            lambda: self.strings("cfg_firebase_url"),
            "forward_channel_id",
            -1001234567890,
            lambda: self.strings("cfg_forward_channel"),
            # Additional config options...
        )
        
        self.message_queue = Queue()
        self.processing_task = None
        self.firebase_app = None
        self.db_ref = None
        self.similarity_checker = None
        self.initialized = False
        self.allowed_chats = set()
        super().__init__()

    async def client_ready(self, client, db):
        """Initialize module with improved error handling."""
        self.client = client
        
        if not await self._validate_config():
            return
            
        if not await self._initialize_firebase():
            return
            
        try:
            self.similarity_checker = NgramSimilarityChecker(
                db_ref=self.db_ref,
                n=self.config.get("ngram_size", 3),
                similarity_threshold=self.config.get("similarity_threshold", 0.7),
                max_ngram_entries=self.config.get("max_ngrams", 1000),
                max_media_cache_size=self.config.get("max_media_cache_size", 500),
                retention_period=self.config.get("ngram_retention_period", 86400),
            )
            await self.similarity_checker.initialize()

            # Load allowed chats with retry logic
            for attempt in range(3):
                try:
                    chats_ref = self.db_ref.child("allowed_chats")
                    chats_data = chats_ref.get()
                    self.allowed_chats = set(chats_data if isinstance(chats_data, list) else [])
                    break
                except Exception as e:
                    if attempt == 2:
                        log.error(f"Failed to load allowed chats: {e}")
                        self.allowed_chats = set()
                    await asyncio.sleep(2 ** attempt)

            self.initialized = True
            
            # Start message processing task
            if not self.processing_task:
                self.processing_task = asyncio.create_task(self.process_queue())
                
        except Exception as e:
            log.error(f"Error in client_ready: {e}", exc_info=True)
            self.initialized = False

    async def _validate_config(self) -> bool:
        """Validate configuration settings."""
        if not self.config["firebase_credentials_path"]:
            log.error("Firebase credentials path not configured")
            return False
            
        if not os.path.exists(self.config["firebase_credentials_path"]):
            log.error("Firebase credentials file not found")
            return False
            
        if not self.config["firebase_database_url"]:
            log.error("Firebase database URL not configured")
            return False
            
        return True

    async def process_queue(self):
        """Process message queue with improved error handling."""
        while True:
            try:
                messages, sender_info = await self.message_queue.get()
                
                # Add delay before forwarding
                await asyncio.sleep(self.config.get("forward_delay", 13))
                
                if not messages:
                    continue
                    
                # Forward messages with retry logic
                forwarded = await self._forward_messages(messages)
                
                if forwarded:
                    # Send sender info
                    await self._send_sender_info(forwarded, sender_info)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error processing message: {e}", exc_info=True)
            finally:
                self.message_queue.task_done()

    async def _forward_messages(self, messages: List[types.Message]) -> Optional[types.Message]:
        """Forward messages with retry logic."""
        for attempt in range(3):
            try:
                forwarded = await self.client.forward_messages(
                    entity=self.config["forward_channel_id"],
                    messages=messages
                )
                log.info(f"Successfully forwarded {len(messages)} messages")
                return forwarded
            except errors.FloodWaitError as e:
                if attempt == 2:
                    log.error(f"Flood wait error: {e.seconds} seconds")
                    return None
                await asyncio.sleep(e.seconds)
            except errors.MessageIdInvalidError:
                log.warning("Message unavailable or deleted")
                return None
            except Exception as e:
                if attempt == 2:
                    log.error(f"Failed to forward message: {e}")
                    return None
                await asyncio.sleep(2 ** attempt)
        return None

    async def _send_sender_info(
        self,
        forwarded: Union[types.Message, List[types.Message]],
        sender_info: dict
    ) -> None:
        """Send sender information message."""
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
                    link_preview=False
                )
        except Exception as e:
            log.error(f"Error sending sender info: {e}", exc_info=True)

    async def _get_sender_info(self, message: types.Message) -> dict:
        """Get sender information with improved formatting."""
        try:
            # Get basic sender info
            sender_name = html.escape(
                "Deleted Account" if getattr(message.sender, "deleted", False)
                else message.sender.first_name
            )
            
            # Get sender URL
            sender_url = (
                f"https://t.me/{message.sender.username}"
                if getattr(message.sender, "username", None)
                else f"tg://openmessage?user_id={message.sender.id}"
            )
            
            # Get message URL
            message_url = (
                f"https://t.me/{message.chat.username}/{message.id}"
                if getattr(message.chat, "username", None)
                else f"https://t.me/c/{str(message.chat_id)[4:]}/{message.id}"
            )
            
            # Check scammer status
            is_scammer, post_link = await self._check_scammer(message.sender.id)
            
            return {
                "sender_name": sender_name,
                "sender_id": message.sender.id,
                "sender_url": sender_url,
                "message_url": message_url,
                "scam_warning": (
                    f"╰┈➤⚠️ <a href='{post_link}'>Found in scammer database.</a>\n"
                    if is_scammer else ""
                )
            }
        except Exception as e:
            log.error(f"Error getting sender info: {e}", exc_info=True)
            return {}

    async def _check_scammer(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """Check if user is in scammer database with caching."""
        cache_key = f"scammer_{user_id}"
        
        try:
            # Search in scammer channel
            messages = await self.client.get_messages(
                1539778138,  # Scammer channel ID
                search=str(user_id),
                limit=1
            )
            
            if messages and messages[0]:
                post_link = f"https://t.me/bezscamasuka/{messages[0].id}"
                return True, post_link
                
        except Exception as e:
            log.error(f"Error checking scammer status: {e}", exc_info=True)
            
        return False, None

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