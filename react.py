import mmh3
from telethon.tl.types import Message
from .. import loader
import firebase_admin
from firebase_admin import credentials, db


@loader.tds
class BroadMod(loader.Module):
    """Configurable module."""

    strings = {"name": "Broad"}

    def __init__(self):
        super().__init__()
        self.db = None
        self.me = None
        self.client = None

    async def client_ready(self, client, db):
        """Initializes the module when the client is ready."""
        self.client = client
        self.db = db

        cred = credentials.Certificate(
            "loll-8a3bd-firebase-adminsdk-4pvtd-6b93a17b70.json"
        )

        firebase_admin.initialize_app(
            cred, {"databaseURL": "https://loll-8a3bd-default-rtdb.firebaseio.com"}
        )

    async def watcher(self, message: Message):
        """Handles incoming messages."""
        if not isinstance(message, Message) or not message.text:
            return
        ref_chats = db.reference("allowed_chats")

        allowed_chats = ref_chats.get() or []

        if message.chat_id not in allowed_chats:
            return
        message_hash = mmh3.hash(message.text)

        ref_hashes = db.reference("hashes/hash_list")

        existing_hashes = ref_hashes.get() or []

        if str(message_hash) not in existing_hashes:
            existing_hashes.append(str(message_hash))
            ref_hashes.set(existing_hashes)
            await self.client.send_message(
                "me", f"New message added and saved: {message.text}"
            )
        else:
            await self.client.send_message(
                "me", "Message already exists in the database."
            )

    async def manage_chat_cmd(self, message: Message):
        """Adds or removes a chat from the allowed list."""
        args = message.text.split()

        ref_chats = db.reference("allowed_chats")
        allowed_chats = ref_chats.get() or []

        if len(args) != 3:
            if allowed_chats:
                await message.reply(
                    f"List of allowed chats: {', '.join(allowed_chats)}"
                )
            else:
                await message.reply("List of allowed chats is empty.")
            return
        chat_id = int(args[2])
        if chat_id not in allowed_chats:
            allowed_chats.append(chat_id)
            txt = f"Chat {chat_id} added to the list."
        else:
            allowed_chats.remove(chat_id)
            txt = f"Chat {chat_id} removed from the list."
        ref_chats.set(allowed_chats)
        await message.reply(txt)
