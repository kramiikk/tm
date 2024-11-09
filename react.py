import asyncio
import html
import re
import mmh3
import time
import datetime
from telethon.tl.types import Message
from .. import loader, utils

import firebase_admin
from firebase_admin import credentials, db as firebase_db
from bloompy import CountingBloomFilter


TRADING_KEYWORDS = set(
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
        "срочн",
        "кто",
    ]
)


@loader.tds
class BroadMod(loader.Module):
    """Модуль для отслеживания и пересылки сообщений"""

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
            2500,
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
            10000,
            lambda: self.strings("cfg_max_firebase_hashes"),
            "min_text_length",
            18,
            lambda: self.strings("cfg_min_text_length"),
        )

        super().__init__()
        self.lock = asyncio.Lock()
        self.allowed_chats = []
        self.firebase_app = None
        self.db_ref = None
        try:
            self.bloom_filter = CountingBloomFilter(
                capacity=self.config["bloom_filter_capacity"],
                error_rate=self.config["bloom_filter_error_rate"],
            )
        except Exception as e:
            self.bloom_filter = None
        self.hash_cache = {}
        self.last_cleanup_time = 0
        self.CLEANUP_INTERVAL = self.config["cleanup_interval"]
        self.HASH_RETENTION_PERIOD = self.config["hash_retention_period"]
        self.MAX_FIREBASE_HASHES = self.config["max_firebase_hashes"]

    async def client_ready(self, client, db):
        self.client = client

        if not self.config["firebase_credentials_path"]:
            await self.client.send_message("me", self.strings["no_firebase_path"])
            return
        if not self.config["firebase_database_url"]:
            await self.client.send_message("me", self.strings["no_firebase_url"])
            return
        if not firebase_admin._apps:
            try:
                cred = credentials.Certificate(self.config["firebase_credentials_path"])
                self.firebase_app = firebase_admin.initialize_app(
                    cred,
                    {"databaseURL": self.config["firebase_database_url"]},
                )
            except Exception as e:
                await client.send_message(
                    "me", self.strings["firebase_init_error"].format(error=str(e))
                )
                return
        try:
            self.db_ref = firebase_db.reference("/")
            chats_ref = self.db_ref.child("allowed_chats")
            self.allowed_chats = chats_ref.get() or []

            await self._load_recent_hashes()

            await client.send_message(
                "me",
                self.strings["initialization_success"].format(
                    chats=self.allowed_chats, hashes=len(self.hash_cache)
                ),
            )
        except Exception as e:
            await client.send_message(
                "me", self.strings["firebase_load_error"].format(error=str(e))
            )

    async def _load_recent_hashes(self):
        """Загружает только хэши за последние 24 часа."""
        async with self.lock:
            try:
                hashes_ref = self.db_ref.child("hashes/hash_list")
                all_hashes = hashes_ref.get() or []
                current_time = time.time()

                # Загружаем только хэши с временными метками за последние 24 часа

                recent_hashes = {}
                for hash_data in all_hashes[
                    -self.MAX_FIREBASE_HASHES :
                ]:  # Ограничиваем количество обрабатываемых хэшей
                    if (
                        isinstance(hash_data, dict)
                        and "hash" in hash_data
                        and "timestamp" in hash_data
                    ):
                        if (
                            current_time - hash_data["timestamp"]
                            < self.HASH_RETENTION_PERIOD
                        ):
                            hash_value = hash_data["hash"]
                            self.bloom_filter.add(hash_value)
                            recent_hashes[hash_value] = hash_data["timestamp"]
                self.hash_cache = recent_hashes
            except Exception as e:
                await self.client.send_message("me", f"Ошибка при загрузке хэшей: {e}")

    async def _clear_expired_hashes(self):
        """Очищает устаревшие хэши как из локального кэша, так и из Firebase."""
        async with self.lock:
            try:
                current_time = time.time()
                if current_time - self.last_cleanup_time < self.CLEANUP_INTERVAL:
                    return 0
                self.last_cleanup_time = current_time
                expiration_time = current_time - self.HASH_RETENTION_PERIOD

                # Очистка локального кэша

                new_hash_cache = {}
                removed_count = 0
                for h, timestamp in self.hash_cache.items():
                    if timestamp >= expiration_time:
                        new_hash_cache[h] = timestamp
                    else:
                        self.bloom_filter.remove(h)
                        removed_count += 1
                self.hash_cache = new_hash_cache

                # Очистка Firebase

                hashes_ref = self.db_ref.child("hashes/hash_list")
                all_hashes = hashes_ref.get() or []

                # Фильтруем и обновляем хэши в Firebase

                valid_hashes = [
                    hash_data
                    for hash_data in all_hashes
                    if isinstance(hash_data, dict)
                    and "timestamp" in hash_data
                    and hash_data["timestamp"] >= expiration_time
                ]

                # Ограничиваем количество хэшей

                if len(valid_hashes) > self.MAX_FIREBASE_HASHES:
                    valid_hashes = valid_hashes[-self.MAX_FIREBASE_HASHES :]
                # Обновляем Firebase

                hashes_ref.set(valid_hashes)

                return removed_count
            except Exception as e:
                await self.client.send_message("me", f"Ошибка при очистке хэшей: {e}")
                return 0

    async def add_hash(self, message_hash):
        """Добавляет новый хэш в кэш и Firebase с учетом конкурентного доступа."""
        async with self.lock:
            current_time = time.time()
            self.hash_cache[message_hash] = current_time
            self.bloom_filter.add(message_hash)

            try:
                hashes_ref = self.db_ref.child("hashes/hash_list")
                current_hashes = hashes_ref.get() or []

                # Добавляем новый хэш с временной меткой

                new_hash_data = {"hash": message_hash, "timestamp": current_time}

                current_hashes.append(new_hash_data)

                # Ограничиваем размер списка хэшей

                if len(current_hashes) > self.MAX_FIREBASE_HASHES:
                    current_hashes = current_hashes[-self.MAX_FIREBASE_HASHES :]
                hashes_ref.set(current_hashes)
            except firebase_admin.exceptions.FirebaseError as e:
                await self.client.send_message(
                    "me", f"Ошибка Firebase при добавлении хэша: {e}"
                )

    async def forward_to_channel(self, message: Message):
        try:
            await message.forward_to(
                self.config["forward_channel_id"]
            )  # Use config instead of global
        except Exception as e:
            # Log specific exception type

            logger.error(f"Forward error: {type(e).__name__}: {e}")
            try:
                sender_info = self._format_sender_info(
                    message
                )  # Extract to helper method
                await self.client.send_message(
                    self.config["forward_channel_id"],
                    sender_info + message.text,
                    link_preview=False,
                )
            except Exception as forward_error:
                logger.error(
                    f"Fallback forward error: {type(forward_error).__name__}: {forward_error}"
                )
                await self.client.send_message(
                    "me", f"❌ Ошибка при отправке: {forward_error}"
                )

    async def manage_chat_cmd(self, message: Message):
        try:
            args = message.text.split()

            if len(args) != 2:
                if self.allowed_chats:
                    await message.reply(
                        f"📝 Список разрешенных чатов:\n{', '.join(map(str, self.allowed_chats))}"
                    )
                else:
                    await message.reply("📝 Список разрешенных чатов пуст.")
                return
            try:
                chat_id = int(args[1])
            except ValueError:
                await message.reply(
                    "❌ Неверный формат ID чата. Укажите правильное число."
                )
                return
            async with self.lock:  # Добавляем блокировку
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
        if not self.db_ref:
            return
        if (
            not message.sender
            or (
                getattr(message, "sender", None)
                and getattr(message.sender, "bot", False)
            )
            or not message.text
            or len(message.text) < self.config["min_text_length"]
            or getattr(message, "chat_id", None) not in self.allowed_chats
        ):
            return
        if message.date.minute == 0 and message.date.second == 0:
            removed_count = await self._clear_expired_hashes()
            if removed_count > 0:
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_message = f"[{current_time}] Очистка: удалено {removed_count} хэшей. Размер кэша: {len(self.hash_cache)}, Bloom filter: {len(self.bloom_filter)}"
                await self.client.send_message("me", log_message)
        low = message.text.lower()
        if not any(keyword in low for keyword in TRADING_KEYWORDS):
            return
        try:
            normalized_text_pattern = re.compile(r"<[^>]+>|[^\w\s,.!?;:—]|\s+")
            normalized_text = html.unescape(
                normalized_text_pattern.sub(" ", low)
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
            await self.client.send_message("me", error_message)
