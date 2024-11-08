import asyncio
import html
import re
import mmh3
from telethon.tl.types import Message
from .. import loader
import firebase_admin
from firebase_admin import credentials, db as firebase_db

# Константы для удобства настройки


FIREBASE_CREDENTIALS_PATH = (
    "/home/hikka/Hikka/loll-8a3bd-firebase-adminsdk-4pvtd-6b93a17b70.json"
)
FORWARD_TO_CHANNEL_ID = 2498567519


@loader.tds
class BroadMod(loader.Module):
    """Модуль для отслеживания новых сообщений в заданных чатах и пересылки уникальных сообщений в указанный канал.
    Использует Firebase Realtime Database для хранения хэшей сообщений и предотвращения дубликатов.
    """

    strings = {"name": "Broad"}

    def __init__(self):
        super().__init__()
        self.lock = asyncio.Lock()  # Блокировка для предотвращения race conditions
        self.allowed_chats = []  # Список ID чатов, которые нужно отслеживать
        self.firebase_app = None  # Экземпляр приложения Firebase
        self.db_ref = None  # Ссылка на базу данных Firebase

    async def client_ready(self, client, db):
        """Инициализирует модуль, устанавливает соединение с Firebase и загружает список разрешенных чатов."""
        self.client = client

        if (
            not firebase_admin._apps
        ):  # Инициализируем Firebase, если еще не инициализировано
            try:
                cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
                self.firebase_app = firebase_admin.initialize_app(
                    cred,
                    {"databaseURL": "https://loll-8a3bd-default-rtdb.firebaseio.com"},
                )
            except Exception as e:
                await client.send_message("me", f"Ошибка инициализации Firebase: {e}")
                return
        try:
            self.db_ref = firebase_db.reference(
                "/"
            )  # Получаем ссылку на корень базы данных

            chats_ref = self.db_ref.child(
                "allowed_chats"
            )  # Ссылка на список разрешенных чатов
            chats_data = chats_ref.get()  # Загружаем данные из Firebase

            if chats_data:  # Если данные существуют, преобразуем их в список
                if isinstance(chats_data, list):
                    self.allowed_chats = chats_data
                elif isinstance(chats_data, dict):
                    self.allowed_chats = list(chats_data.values())
                else:
                    self.allowed_chats = []
            await client.send_message(
                "me",
                f"Модуль успешно инициализирован\nРазрешенные чаты: {self.allowed_chats}",
            )
        except Exception as e:
            await client.send_message(
                "me", f"Ошибка при загрузке данных из Firebase: {e}"
            )

    async def forward_to_channel(self, message: Message):
        """Пересылает сообщение в заданный канал."""
        try:
            await message.forward_to(FORWARD_TO_CHANNEL_ID)
        except Exception as e:
            await self.client.send_message(
                "me", f"❌ Ошибка при пересылке сообщения в канал: {e}"
            )

    async def manage_chat_cmd(self, message: Message):
        """Добавляет или удаляет чат из списка разрешенных чатов для мониторинга.

        Использование: .manage_chat <add|remove> <chat_id>
        """
        try:
            args = message.text.split()

            if len(args) != 3:  # Проверяем количество аргументов
                if self.allowed_chats:
                    await message.reply(
                        f"📝 Список разрешенных чатов:\n{', '.join(map(str, self.allowed_chats))}"
                    )
                else:
                    await message.reply("📝 Список разрешенных чатов пуст.")
                return
            try:
                chat_id = int(args[2])  # Получаем ID чата из аргументов
            except ValueError:
                await message.reply(
                    "❌ Неверный формат ID чата. Укажите правильное число."
                )
                return
            if chat_id not in self.allowed_chats:  # Добавляем чат в список
                self.allowed_chats.append(chat_id)
                txt = f"✅ Чат {chat_id} добавлен в список."
            else:  # Удаляем чат из списка
                self.allowed_chats.remove(chat_id)
                txt = f"❌ Чат {chat_id} удален из списка."
            chats_ref = self.db_ref.child(
                "allowed_chats"
            )  # Обновляем данные в Firebase
            chats_ref.set(self.allowed_chats)

            await message.reply(txt)
        except Exception as e:
            await message.reply(f"❌ Ошибка при управлении списком чатов: {e}")

    async def watcher(self, message: Message):
        """Отслеживает новые сообщения в разрешенных чатах и пересылает уникальные сообщения в канал.
        Уникальность определяется на основе хэша текста сообщения после нормализации.
        """
        if not isinstance(message, Message) or not message.text:
            return  # Игнорируем сообщения без текста
        if message.chat_id not in self.allowed_chats:
            return  # Игнорируем сообщения из неразрешенных чатов
        if not self.db_ref:  # Проверяем перед началом работы
            await self.client.send_message("me", "Firebase не инициализирован")
            return
        try:
            # Нормализация текста сообщения: удаление HTML-тегов, лишних пробелов, эмодзи и спецсимволов

            normalized_text = html.unescape(
                re.sub(
                    r"\s+",  # Заменяем несколько пробелов одним
                    " ",
                    re.sub(
                        r"[^\w\s,.!?;:—]",
                        "",  # Удаляем все символы, кроме букв, цифр, пробелов и знаков препинания
                        re.sub(r"<[^>]+>", "", message.text),
                    ),  # Удаляем HTML-теги
                )
            )

            message_hash = str(mmh3.hash(normalized_text.lower()))

            async with self.lock:
                hashes_ref = self.db_ref.child("hashes/hash_list")
                locks_ref = self.db_ref.child("locks")  # Ensure 'locks' node exists
                lock_ref = locks_ref.child(message_hash)

                try:

                    def hash_transaction(current_data):
                        lock_value = lock_ref.get()  # Get the lock value
                        if (
                            lock_value
                        ):  # Check if lock exists and is True (or any value)
                            return None  # Explicitly return None to abort
                        lock_ref.set(True)

                        current_data = current_data or []
                        if isinstance(current_data, dict):
                            current_data = list(current_data.values())
                        if message_hash not in current_data:
                            current_data.append(message_hash)
                            return current_data
                        return None  # Explicitly return None if hash already exists

                    update_result = hashes_ref.transaction(hash_transaction)

                    if update_result:  # Check if update_result is not None
                        if update_result.committed:
                            await self.forward_to_channel(message)
                        else:  # Transaction aborted, but not due to an error
                            # Log or handle the aborted transaction (optional)

                            print(f"Transaction aborted for {message_hash}")
                    else:  # Transaction failed due to an error
                        await self.client.send_message(
                            "me",
                            f"Transaction failed: {message_hash} "
                            f"(Original message: {message.text[:100]}...)",
                        )
                finally:
                    lock_ref.delete()
        except Exception as e:
            await self.client.send_message("me", f"Error processing message: {e}")
