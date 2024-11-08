import asyncio
import html
import re
import mmh3
from telethon.tl.types import Message, User
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
    "кто",
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
            self.allowed_chats = chats_ref.get()
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
            await message.forward_to(FORWARD_TO_CHANNEL_ID)
        except Exception as e:
            try:
                sender_info = f"Переслано из {message.chat.title or 'чата'}\nОт: {message.sender.first_name or ''} {message.sender.last_name or ''} {f'(@{message.sender.username})' if message.sender.username else ''}\n➖➖➖➖➖➖➖➖➖\n"
                await self.client.send_message(
                    FORWARD_TO_CHANNEL_ID,
                    sender_info + message.text,
                    link_preview=False,
                )
            except Exception as forward_error:
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
        if (
            not message.sender
            or isinstance(message.sender, User)
            and message.sender.bot
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
                if message_hash in current_hashes:
                    return
                current_hashes.append(message_hash)
                hashes_ref.set(current_hashes)  # Update Firebase after adding the hash
                await self.forward_to_channel(message)
        except Exception as e:
            error_message = f"Error processing message: {str(e)}\nMessage text: {message.text[:100]}..."
            await self.client.send_message("me", error_message)
