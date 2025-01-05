import asyncio
import html
import logging
import re
import time
from asyncio import Queue
from collections import OrderedDict, deque
from typing import Optional, Tuple, List, Dict, Any, Set

import firebase_admin
from firebase_admin import credentials, db as firebase_db
from telethon import types, errors

from .. import loader

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
)
log = logging.getLogger(__name__)


class LocalQueue:
    def __init__(self, maxsize: int = 1000):
        self.queue = deque(maxlen=maxsize)

    def add(self, data: dict) -> None:
        self.queue.append(data)

    def get_all(self) -> List[dict]:
        items = list(self.queue)
        self.queue.clear()
        return items


class BatchProcessor:
    def __init__(
        self,
        db_ref: firebase_db.Reference,
        base_path: str,
        max_entries: int,
        batch_size: int = 50,
        max_retries: int = 3,
    ):
        (
            self.db_ref,
            self.base_path,
            self.max_entries,
            self.batch_size,
            self.max_retries,
        ) = (db_ref, base_path, max_entries, batch_size, max_retries)
        self.batch: List[Dict] = []
        self.retries = 0
        self.local_queue = LocalQueue()

    async def add(self, data: Dict) -> None:
        self.batch.append(data)
        if len(self.batch) >= self.batch_size:
            await self.flush()

    async def flush(self) -> None:
        if not self.batch:
            return
        current_batch = self.batch[:]
        self.batch.clear()
        pending_items = self.local_queue.get_all()
        if pending_items:
            current_batch.extend(pending_items)
        try:

            def transaction(current_data):
                current_data = current_data or []
                current_data.extend(current_batch)
                return current_data[-self.max_entries :]

            await self.db_ref.child(self.base_path).transaction(transaction)
            self.retries = 0
            log.info(f"Flushed {len(current_batch)} to {self.base_path}")
        except Exception as e:
            log.error(f"Flush error ({self.retries + 1}): {e}")
            self.retries += 1
            if self.retries <= self.max_retries:
                self.local_queue.add(current_batch)
                log.warning(f"Added {len(current_batch)} to local queue.")
            else:
                log.error(f"Max retries. Discarding {len(current_batch)}.")


class NgramSimilarityChecker:
    def __init__(
        self,
        db_ref: firebase_db.Reference,
        n: int,
        similarity_threshold: float,
        max_ngram_entries: int,
        max_media_cache_size: int,
        retention_period: float,
    ):
        self.n, self.threshold, self.retention = (
            n,
            similarity_threshold,
            retention_period,
        )
        self.text_cache, self.media_cache = OrderedDict(), OrderedDict()
        self.max_ngram_cache_size, self.max_media_cache_size = (
            max_ngram_entries,
            max_media_cache_size,
        )
        self.text_handler = BatchProcessor(
            db_ref, "hashes/text_hashes", max_ngram_entries
        )
        self.media_handler = BatchProcessor(
            db_ref, "hashes/media_ids", max_media_cache_size
        )
        self._load_lock = asyncio.Lock()

    def _maintain_cache_size(self, cache: OrderedDict, max_size: int) -> None:
        while len(cache) > max_size:
            cache.popitem(last=False)

    async def load_data_chunk(
        self,
        ref: firebase_db.Reference,
        start_at: Optional[str] = None,
        chunk_size: int = 100,
    ) -> List[Dict[str, Any]]:
        query = ref.order_by_key()
        if start_at:
            query = query.start_at(start_at)
        query = query.limit_to_first(chunk_size)
        try:
            data = await asyncio.wait_for(query.get(), timeout=10)
            return list(data.values()) if data else []
        except Exception as e:
            log.error(f"Error loading chunk: {e}")
            return []

    async def initialize(self) -> None:
        async with self._load_lock:
            try:
                current_time = time.time()
                text_hashes_ref = self.text_handler.db_ref.child("hashes/text_hashes")
                last_key = None
                while True:
                    chunk = await self.load_data_chunk(text_hashes_ref, last_key)
                    if not chunk:
                        break
                    for item in chunk:
                        if (
                            isinstance(item, dict)
                            and "hash" in item
                            and "ngrams" in item
                            and "timestamp" in item
                            and current_time - item["timestamp"] < self.retention
                        ):
                            self.text_cache[item["hash"]] = tuple(item["ngrams"])
                            self._maintain_cache_size(
                                self.text_cache, self.max_ngram_cache_size
                            )
                    if len(chunk) < 100:
                        break
                    last_key = list(chunk.keys())[-1]
                media_ids_ref = self.media_handler.db_ref.child("hashes/media_ids")
                last_key = None
                while True:
                    chunk = await self.load_data_chunk(media_ids_ref, last_key)
                    if not chunk:
                        break
                    for item in chunk:
                        if (
                            isinstance(item, dict)
                            and "media_id" in item
                            and "timestamp" in item
                            and current_time - item["timestamp"] < self.retention
                        ):
                            self.media_cache[item["media_id"]] = item["timestamp"]
                            self._maintain_cache_size(
                                self.media_cache, self.max_media_cache_size
                            )
                    if len(chunk) < 100:
                        break
                    last_key = list(chunk.keys())[-1]
                log.info(
                    f"Loaded {len(self.text_cache)} text, {len(self.media_cache)} media."
                )
            except Exception as e:
                log.error(f"Firebase load error: {e}")

    def generate_ngrams(self, text: str) -> Set[str]:
        text = re.sub(r"\s+", " ", text.lower().strip())
        text = re.sub(r"[^\w\s]", "", text)
        padded = f"{'_' * (self.n - 1)}{text}{'_' * (self.n - 1)}"
        return {padded[i : i + self.n] for i in range(len(padded) - self.n + 1)}

    def calculate_similarity(self, ngrams1: Set[str], ngrams2: Set[str]) -> float:
        if not ngrams1 or not ngrams2:
            return 0.0
        intersection = len(ngrams1.intersection(ngrams2))
        union = len(ngrams1.union(ngrams2))
        return intersection / union if union > 0 else 0.0

    async def _get_media_id(self, message: types.Message) -> Optional[int]:
        try:
            if isinstance(message.media, types.MessageMediaPhoto):
                return message.media.photo.id
            elif isinstance(message.media, types.MessageMediaDocument):
                return message.media.document.id
            elif hasattr(message, "grouped_id") and message.grouped_id:
                async for msg in message.client.iter_messages(
                    message.chat_id, ids=message.id
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

    async def is_similar_to_cached(
        self, message: types.Message, timestamp: float
    ) -> bool:
        if message.media:
            media_id = await self._get_media_id(message)
            if media_id and media_id in self.media_cache:
                return True
            if media_id:
                await self.media_handler.add(
                    {"type": "media", "media_id": media_id, "timestamp": timestamp}
                )
            return False
        else:
            text = message.text or message.raw_text
            if not text:
                return False
            current_ngrams = self.generate_ngrams(text)
            if not current_ngrams:
                return False
            for cached_ngrams in self.text_cache.values():
                if (
                    self.calculate_similarity(current_ngrams, set(cached_ngrams))
                    >= self.threshold
                ):
                    return True
            cache_key = hash(frozenset(current_ngrams))
            await self.text_handler.add(
                {
                    "type": "text",
                    "hash": cache_key,
                    "ngrams": list(current_ngrams),
                    "timestamp": timestamp,
                }
            )
            self.text_cache[cache_key] = tuple(current_ngrams)
            self._maintain_cache_size(self.text_cache, self.max_ngram_cache_size)
            return False


@loader.tds
class BroadMod(loader.Module):
    strings = {
        "name": "Broad",
        "cfg_firebase_path": "Firebase creds path",
        "cfg_firebase_url": "Firebase DB URL",
        "cfg_forward_channel": "Forward channel ID",
        "sender_info": "<a href='{sender_url}'>👤 {sender_name}</a> [{sender_id}]\n{scam_warning}\n<a href='{message_url}'>🍜 View</a>",
    }
    FORWARD_DELAY, MAX_QUEUE_SIZE, FLOOD_WAIT_BASE = 13, 1000, 900

    def __init__(self):
        self.config = loader.ModuleConfig(
            "firebase_credentials_path",
            "/root/Heroku/...",
            lambda: self.strings("cfg_firebase_path"),
            "firebase_database_url",
            "https://...",
            lambda: self.strings("cfg_firebase_url"),
            "forward_channel_id",
            123456789,
            lambda: self.strings("cfg_forward_channel"),
            "trading_keywords",
            ["акк", "прод"],
            lambda: "Keywords",
            "ngram_size",
            3,
            lambda: "N-gram size",
            "similarity_threshold",
            0.7,
            lambda: "Similarity threshold",
            "max_ngrams",
            1000,
            lambda: "Max n-grams",
            "max_media_cache_size",
            500,
            lambda: "Max media cache",
            "ngram_retention_period",
            86400,
            lambda: "N-gram retention",
            "min_text_length",
            18,
            lambda: "Min text len",
        )
        self.message_queue = Queue(maxsize=self.MAX_QUEUE_SIZE)
        self.processing_task = None
        self.firebase_app, self.db_ref, self.similarity_checker, self._db_lock = (
            None,
            None,
            None,
            asyncio.Lock(),
        )
        self.allowed_chats: Set[int] = set()
        self.initialized = False

    async def client_ready(self, client, db):
        self.client = client
        cred = credentials.Certificate(self.config["firebase_credentials_path"])
        self.firebase_app = firebase_admin.initialize_app(
            cred, {"databaseURL": self.config["firebase_database_url"]}
        )
        self.db_ref = firebase_db.reference()
        self.similarity_checker = NgramSimilarityChecker(
            db_ref=self.db_ref,
            n=self.config["ngram_size"],
            similarity_threshold=self.config["similarity_threshold"],
            max_ngram_entries=self.config["max_ngrams"],
            max_media_cache_size=self.config["max_media_cache_size"],
            retention_period=self.config["ngram_retention_period"],
        )
        await self.similarity_checker.initialize()
        chats = await self.db_ref.child("allowed_chats").get()
        self.allowed_chats = set(chats) if isinstance(chats, list) else set()
        self.initialized = True
        if not self.processing_task or self.processing_task.done():
            self.processing_task = asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        while True:
            try:
                messages, sender_info = await self.message_queue.get()
                await asyncio.sleep(self.FORWARD_DELAY)
                await self._forward_and_inform(messages, sender_info)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Queue error: {e}")
            finally:
                self.message_queue.task_done()

    async def _forward_messages(
        self, messages: List[types.Message]
    ) -> Optional[types.Message]:
        for attempt in range(3):
            try:
                return await self.client.forward_messages(
                    self.config["forward_channel_id"], messages
                )
            except errors.FloodWaitError as e:
                await asyncio.sleep(self.FLOOD_WAIT_BASE + e.seconds)
            except Exception as e:
                log.error(f"Forward error: {e}")
            await asyncio.sleep(2**attempt)
        return None

    async def _forward_and_inform(self, messages, sender_info):
        fwd_msgs = await self._forward_messages(messages)
        if fwd_msgs:
            msg_id = fwd_msgs[0].id if isinstance(fwd_msgs, list) else fwd_msgs.id
            await self.client.send_message(
                self.config["forward_channel_id"],
                self.strings["sender_info"].format(**sender_info),
                reply_to=msg_id,
                parse_mode="html",
                link_preview=False,
            )

    async def _get_sender_info(self, message):
        try:
            sender = await self.client.get_entity(message.sender_id)
            chat = await self.client.get_entity(message.chat_id)
            sender_url = f"tg://user?id={sender.id}"
            sender_name = html.escape(sender.first_name or "Unknown")
            scammer_info = await self._check_scammer(message.sender_id)
            msg_url = (
                f"https://t.me/c/{chat.id}/{message.id}"
                if isinstance(chat, types.Channel)
                else f"https://t.me/{getattr(chat, 'username', None)}/{message.id}"
            )
            return {
                "sender_id": sender.id,
                "sender_url": sender_url,
                "sender_name": sender_name,
                "scam_warning": (
                    f"⚠️ <a href='{scammer_info[1]}'>Possible scammer</a>"
                    if scammer_info[0]
                    else ""
                ),
                "message_url": msg_url,
            }
        except Exception as e:
            log.error(f"Sender info error: {e}")
        return {}

    async def _check_scammer(self, user_id):
        try:
            entity = await self.client.get_entity("bezscamasuka")
            async for msg in self.client.iter_messages(
                entity, search=str(user_id), limit=1
            ):
                return True, f"https://t.me/bezscamasuka/{msg.id}"
        except Exception as e:
            log.error(f"Scammer check error: {e}")
        return False, None

    async def _process_album(self, message, timestamp):
        messages = await self._get_album_messages(message)
        if messages and not await self.similarity_checker.is_similar_to_cached(
            messages[0], timestamp
        ):
            sender_info = await self._get_sender_info(message)
            await self.message_queue.put((messages, sender_info))

    async def _get_album_messages(self, message):
        if not getattr(message, "grouped_id", None):
            return None
        messages = []
        async for msg in self.client.iter_messages(
            message.chat_id, grouped_id=message.grouped_id
        ):
            messages.append(msg)
        return messages

    async def _process_media_message(self, message, timestamp):
        if not await self.similarity_checker.is_similar_to_cached(message, timestamp):
            sender_info = await self._get_sender_info(message)
            await self.message_queue.put(([message], sender_info))

    async def _process_text_message(self, message, timestamp):
        text = message.text or message.raw_text or ""
        if len(text) >= self.config.get("min_text_length", 0) and any(
            kw in text.lower() for kw in self.config.get("trading_keywords", [])
        ):
            if not await self.similarity_checker.is_similar_to_cached(
                message, timestamp
            ):
                sender_info = await self._get_sender_info(message)
                await self.message_queue.put(([message], sender_info))

    async def watcher(self, message):
        if (
            not self.initialized
            or message.chat_id not in self.allowed_chats
            or getattr(message.sender, "bot", False)
        ):
            return
        try:
            timestamp = time.time()
            if getattr(message, "grouped_id", None):
                await self._process_album(message, timestamp)
            elif message.media:
                await self._process_media_message(message, timestamp)
            else:
                await self._process_text_message(message, timestamp)
        except Exception as e:
            log.error(f"Watcher error: {e}")

    @loader.command()
    async def managecmd(self, message):
        args = message.text.split()
        if len(args) != 3 or args[1] not in ["add", "remove"]:
            return await message.respond("Usage: .managecmd [add|remove] <chat_id>")
        try:
            chat_id = int(args[2])
        except ValueError:
            return await message.respond("Invalid chat ID.")
        if args[1] == "add":
            if chat_id not in self.allowed_chats:
                self.allowed_chats.add(chat_id)
            else:
                return await message.respond("Chat already allowed.")
        elif args[1] == "remove":
            if chat_id in self.allowed_chats:
                self.allowed_chats.discard(chat_id)
            else:
                return await message.respond("Chat not in allowed list.")
        await self._update_allowed_chats()
        await message.respond("Done.")

    async def _update_allowed_chats(self):
        await self.db_ref.child("allowed_chats").set(list(self.allowed_chats))
