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

            message_hash = str(
                mmh3.hash(normalized_text.lower())
            )  # Вычисляем хэш сообщения

            async with self.lock:  # Блокируем для предотвращения race conditions
                hashes_ref = self.db_ref.child(
                    "hashes/hash_list"
                )  # Ссылка на список хэшей сообщений
                locks_ref = self.db_ref.child(
                    "locks"
                )  # Ссылка на блокировки транзакций
                lock_ref = locks_ref.child(
                    message_hash
                )  # Блокировка для текущего сообщения

                try:

                    def hash_transaction(
                        current_data,
                    ):  # Функция для выполнения транзакции
                        if (
                            lock_ref.get()
                        ):  # Проверяем, обработано ли уже сообщение другим экземпляром бота
                            return
                        lock_ref.set(
                            True
                        )  # Устанавливаем блокировку, чтобы другие экземпляры не обработали это сообщение

                        current_data = (
                            current_data or []
                        )  # Если данных нет, создаем пустой список
                        if isinstance(
                            current_data, dict
                        ):  # Преобразуем словарь в список, если необходимо
                            current_data = list(current_data.values())
                        if (
                            message_hash not in current_data
                        ):  # Если хэш еще не существует, добавляем его
                            current_data.append(message_hash)
                            return current_data  # Возвращаем обновленный список хэшей
                        return  # Если хэш уже существует, ничего не возвращаем (транзакция не выполнится)

                    update_result = hashes_ref.transaction(
                        hash_transaction
                    )  # Выполняем транзакцию

                    if (
                        update_result.committed
                    ):  # Если транзакция успешна, пересылаем сообщение
                        await self.forward_to_channel(message)
                    elif message_hash not in (
                        update_result.snapshot.val() or []
                    ):  # Если транзакция не выполнена и хэша нет в базе, значит произошла ошибка
                        await self.client.send_message(
                            "me",
                            f"Transaction failed: {message_hash} "
                            f"(Original message: {message.text[max(0, len(message.text)-100):][:100]}...)",  # Ограничиваем длину с обеих сторон
                        )
                finally:
                    lock_ref.delete()  # Удаляем блокировку после завершения транзакции
        except Exception as e:
            await self.client.send_message(
                "me", f"❌ Ошибка при обработке сообщения: {e}"
            )
