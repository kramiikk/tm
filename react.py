import mmh3
from telethon.tl.types import Message
from .. import loader
import firebase_admin
from firebase_admin import credentials, db as firebase_db
import json

@loader.tds
class BroadMod(loader.Module):
    """Модуль для отслеживания сообщений с использованием Firebase Realtime Database."""

    strings = {"name": "Broad"}

    def __init__(self):
        super().__init__()
        self.me = None
        self.client = None
        self.allowed_chats = []
        self.firebase_app = None
        self.db_ref = None

    async def client_ready(self, client, db):
        """Инициализация модуля при готовности клиента."""
        self.client = client

        # Проверяем, не инициализировано ли уже приложение Firebase
        if not firebase_admin._apps:
            try:
                cred = credentials.Certificate(
                    "/home/hikka/Hikka/loll-8a3bd-firebase-adminsdk-4pvtd-6b93a17b70.json"
                )
                self.firebase_app = firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://loll-8a3bd-default-rtdb.firebaseio.com'
                })
            except Exception as e:
                await client.send_message("me", f"Ошибка инициализации Firebase: {str(e)}")
                return
        
        try:
            # Инициализация ссылок на базу данных
            self.db_ref = firebase_db.reference('/')
            
            # Загружаем список разрешенных чатов
            chats_ref = self.db_ref.child('allowed_chats')
            chats_data = chats_ref.get()
            
            # Конвертируем данные в список, если они существуют
            if chats_data:
                if isinstance(chats_data, list):
                    self.allowed_chats = chats_data
                elif isinstance(chats_data, dict):
                    self.allowed_chats = list(chats_data.values())
                else:
                    self.allowed_chats = []
            
            await client.send_message(
                "me", 
                f"Модуль успешно инициализирован\nРазрешенные чаты: {self.allowed_chats}"
            )
            
        except Exception as e:
            await client.send_message(
                "me", 
                f"Ошибка при загрузке данных из Firebase: {str(e)}"
            )

    async def forward_to_channel(self, message: Message):
        """Пересылка сообщения на канал."""
        try:
            # Пересылаем оригинальное сообщение в канал
            forwarded_msg = await message.forward_to(2498567519)
                
        except Exception as e:
            await self.client.send_message(
                "me",
                f"❌ Ошибка при пересылке сообщения в канал: {str(e)}"
            )

    async def watcher(self, message: Message):
        """Обработчик входящих сообщений."""
        if not isinstance(message, Message) or not message.text:
            return
        
        try:
            if message.chat_id not in self.allowed_chats:
                return
            
            message_hash = str(mmh3.hash(message.text))
            
            # Получаем текущие хэши
            hashes_ref = self.db_ref.child('hashes/hash_list')
            current_hashes = hashes_ref.get()
            
            # Проверяем и конвертируем данные
            if current_hashes is None:
                current_hashes = []
            elif isinstance(current_hashes, dict):
                current_hashes = list(current_hashes.values())
            
            if message_hash not in current_hashes:
                # Пересылаем сообщение на канал
                await self.forward_to_channel(message)
                
                # Добавляем новый хэш
                current_hashes.append(message_hash)
                # Обновляем базу данных
                hashes_ref.set(current_hashes)
                
            else:
                # Опционально: можно убрать это сообщение, если не нужно уведомление о дубликатах
                await self.client.send_message(
                    "me", 
                    "⚠️ Сообщение уже существует в базе данных."
                )
                
        except Exception as e:
            await self.client.send_message(
                "me", 
                f"❌ Ошибка при обработке сообщения: {str(e)}"
            )

    async def manage_chat_cmd(self, message: Message):
        """Управление списком разрешенных чатов."""
        try:
            args = message.text.split()

            if len(args) != 3:
                if self.allowed_chats:
                    await message.reply(
                        f"📝 Список разрешенных чатов:\n{', '.join(map(str, self.allowed_chats))}"
                    )
                else:
                    await message.reply("📝 Список разрешенных чатов пуст.")
                return

            try:
                chat_id = int(args[2])
            except ValueError:
                await message.reply("❌ Неверный формат ID чата. Укажите правильное число.")
                return

            # Обновляем список разрешенных чатов
            if chat_id not in self.allowed_chats:
                self.allowed_chats.append(chat_id)
                txt = f"✅ Чат {chat_id} добавлен в список."
            else:
                self.allowed_chats.remove(chat_id)
                txt = f"❌ Чат {chat_id} удален из списка."

            # Обновляем базу данных
            chats_ref = self.db_ref.child('allowed_chats')
            chats_ref.set(self.allowed_chats)
            
            await message.reply(txt)
            
        except Exception as e:
            await message.reply(f"❌ Ошибка при управлении списком чатов: {str(e)}")
