import asyncio
import html
import re
import mmh3
from telethon.tl.types import Message
from .. import loader
import firebase_admin
from firebase_admin import credentials, db as firebase_db

FIREBASE_CREDENTIALS_PATH = (
    "/home/hikka/Hikka/loll-8a3bd-firebase-adminsdk-4pvtd-6b93a17b70.json"
)
FORWARD_TO_CHANNEL_ID = 2498567519

TRADING_KEYWORDS = [
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
]


@loader.tds
class BroadMod(loader.Module):
    strings = {"name": "Broad"}

    def __init__(self):
        super().__init__()
        self.lock = asyncio.Lock()
        self.allowed_chats = []
        self.firebase_app = None
        self.db_ref = None

    async def client_ready(self, client, db):
        self.client = client

        if not firebase_admin._apps:
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
            self.db_ref = firebase_db.reference("/")
            chats_ref = self.db_ref.child("allowed_chats")
            chats_data = chats_ref.get()

            if chats_data:
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
        try:
            # Сначала пробуем переслать сообщение

            await message.forward_to(FORWARD_TO_CHANNEL_ID)
        except Exception as forward_error:
            try:
                # Если пересылка не удалась, пробуем отправить как новое сообщение

                full_message = f"Переслано из {message.chat.title if message.chat.title else 'чата'}\n"
                if message.sender:
                    sender_name = message.sender.first_name
                    if message.sender.last_name:
                        sender_name += f" {message.sender.last_name}"
                    if message.sender.username:
                        sender_name += f" (@{message.sender.username})"
                    full_message += f"От: {sender_name}\n"
                full_message += f"➖➖➖➖➖➖➖➖➖\n {message.text}"

                await self.client.send_message(
                    FORWARD_TO_CHANNEL_ID, full_message, link_preview=False
                )
            except Exception as e:
                error_msg = f"❌ Ошибка при отправке: {e}"
                await self.client.send_message("me", error_msg)

    async def manage_chat_cmd(self, message: Message):
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
                await message.reply(
                    "❌ Неверный формат ID чата. Укажите правильное число."
                )
                return
            if args[1].lower() == "add":
                if chat_id not in self.allowed_chats:
                    self.allowed_chats.append(chat_id)
                    txt = f"✅ Чат {chat_id} добавлен в список."
                else:
                    txt = f"❗ Чат {chat_id} уже в списке."
            elif args[1].lower() == "remove":
                if chat_id in self.allowed_chats:
                    self.allowed_chats.remove(chat_id)
                    txt = f"❌ Чат {chat_id} удален из списка."
                else:
                    txt = f"❗ Чат {chat_id} не найден в списке."
            else:
                txt = "❌ Неверная команда. Используйте 'add' или 'remove'."
            chats_ref = self.db_ref.child("allowed_chats")
            chats_ref.set(self.allowed_chats)
            await message.reply(txt)
        except Exception as e:
            await message.reply(f"❌ Ошибка при управлении списком чатов: {e}")

    async def watcher(self, message: Message):
        if (
            not isinstance(message, Message)
            or not message.sender
            or message.sender.bot
            or not message.text
            or len(message.text) < 18
            or message.chat_id not in self.allowed_chats
        ):
            return
        if not self.db_ref:
            await self.client.send_message("me", "Firebase не инициализирован")
            return
        low = message.text.lower()
        if not any(keyword.lower() in low for keyword in TRADING_KEYWORDS):
            return
        try:
            normalized_text = html.unescape(
                re.sub(
                    r"\s+",
                    " ",
                    re.sub(
                        r"[^\w\s,.!?;:—]",
                        "",
                        re.sub(r"<[^>]+>", "", low),
                    ),
                )
            ).strip()

            if not normalized_text:
                return
            message_hash = str(mmh3.hash(normalized_text))

            async with self.lock:
                hashes_ref = self.db_ref.child("hashes/hash_list")
                current_hashes = hashes_ref.get() or []
                if isinstance(current_hashes, dict):
                    current_hashes = list(current_hashes.values())
                if message_hash not in current_hashes:
                    current_hashes.append(message_hash)
                    hashes_ref.set(current_hashes)
                    await self.forward_to_channel(message)
        except Exception as e:
            error_message = f"Error processing message: {str(e)}\nMessage text: {message.text[:100]}..."
            await self.client.send_message("me", error_message)
