import asyncio
import logging
import time
from typing import Optional

from hikkatl.errors import FloodWaitError, EntityNotFoundError
from hikkatl.tl.types import Message, User
from .. import loader, utils
from ..tl_cache import CustomTelegramClient

logger = logging.getLogger(__name__)


class AutoMod(loader.Module):
    """Automatically responds to private messages with an image and text"""

    strings = {"name": "Auto"}

    def __init__(self):
        self.config = {
            "enabled": False,
            "message": "<i>Mon esprit s'absente un instant, mais mes mots vous reviendront bientôt.</i>",
            "photo_url": "https://wallpapercave.com/wp/wp5418096.jpg",
            "last": {},
            "cooldown": 1800,
        }
        self.bot_cache = {}
        self.entity_cache = {}
        self.lock = asyncio.Lock()
        self._client: Optional[CustomTelegramClient] = None
        self.db = None

    async def client_ready(self, client: CustomTelegramClient, db):
        """Initialize client and load data from DB"""
        self._client = client
        self.db = db

        for key in self.config:
            self.config[key] = self.db.get("Auto", key, self.config[key])

    async def _get_entity_safe(self, user_id: int) -> Optional[User]:
        """Safely get user entity with caching and error handling"""
        if user_id in self.entity_cache:
            return self.entity_cache[user_id]
        try:
            entity = await self._client.get_entity(user_id)
            self.entity_cache[user_id] = entity
            return entity
        except EntityNotFoundError:
            logger.warning(f"Could not find entity for user {user_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting entity for user {user_id}: {e}")
            return None

    async def _is_bot(self, user_id: int) -> bool:
        """Check if user is a bot with caching"""
        if user_id in self.bot_cache:
            return self.bot_cache[user_id]
        entity = await self._get_entity_safe(user_id)
        if entity is None:
            return False
        is_bot = getattr(entity, "bot", False)
        self.bot_cache[user_id] = is_bot
        return is_bot

    async def _send_safe_message(self, user_id: int) -> bool:
        """Safely send message with error handling"""
        try:
            if not await self._get_entity_safe(user_id):
                logger.error(
                    f"Cannot send message - entity not found for user {user_id}"
                )
                return False
            await self._client.send_file(
                user_id,
                self.config["photo_url"],
                caption=self.config["message"],
            )
            return True
        except FloodWaitError as e:
            wait_time = e.seconds + 5
            logger.warning(f"FloodWait: sleeping for {wait_time} seconds")
            await asyncio.sleep(wait_time)
            return False
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {e}", exc_info=True)
            return False

    async def watcher(self, message):
        """Message handler with improved error handling"""
        if not isinstance(message, Message):
            return
        if (
            not self.config["enabled"]
            or not message.is_private
            or message.out
            or message.chat_id == self.tg_id
            or await self._is_bot(message.sender_id)
        ):
            return
        async with self.lock:
            now = time.time()
            last_time = self.config["last"].get(str(message.sender_id), 0)

            if now - last_time < self.config["cooldown"]:
                return
            if await self._send_safe_message(message.sender_id):
                self.config["last"][str(message.sender_id)] = now
                self.db.set("Auto", "last", self.config["last"])
            self.config["last"] = {
                k: v
                for k, v in self.config["last"].items()
                if now - v < self.config["cooldown"]
            }

    @loader.command()
    async def a(self, message: Message):
        """Command handler for auto-responder settings"""
        args = utils.get_args_raw(message)

        if not args:
            return await self._show_help(message)
        parts = args.split(maxsplit=2)
        command = parts[0].lower()

        handlers = {
            "tg": self._toggle,
            "tt": self._set_text,
            "pt": self._set_photo,
            "st": self._show_status,
            "cd": self._set_cooldown,
        }

        if command not in handlers:
            return await utils.answer(message, "❌ Unknown command")
        await handlers[command](message, parts[1:] if len(parts) > 1 else [])

    async def _toggle(self, message: Message, _args):
        """Toggle auto-responder state"""
        self.config["enabled"] = not self.config["enabled"]
        self.db.set("Auto", "enabled", self.config["enabled"])
        state = "🟢 Enabled" if self.config["enabled"] else "🔴 Disabled"
        await utils.answer(message, state)

    async def _set_text(self, message: Message, args: list):
        """Set response text"""
        if not args:
            return await utils.answer(message, "❌ Please specify the text")
        self.config["message"] = " ".join(args)
        self.db.set("Auto", "message", self.config["message"])
        await utils.answer(message, f"✅ New text set:\n{self.config['message']}")

    async def _set_photo(self, message: Message, args: list):
        """Set response photo URL"""
        if not args:
            return await utils.answer(message, "❌ Please specify the photo URL")
        self.config["photo_url"] = args[0]
        self.db.set("Auto", "photo_url", self.config["photo_url"])
        await utils.answer(
            message, f"✅ New photo URL set:\n{self.config['photo_url']}"
        )

    async def _set_cooldown(self, message: Message, args: list):
        """Set cooldown period in minutes"""
        if not args or not args[0].isdigit():
            return await utils.answer(message, "❌ Please specify cooldown in minutes")
        minutes = int(args[0])
        self.config["cooldown"] = minutes * 60
        self.db.set("Auto", "cooldown", self.config["cooldown"])
        await utils.answer(message, f"✅ Cooldown set to {minutes} minutes")

    async def _show_status(self, message: Message, _args):
        """Show current settings"""
        status = "🟢 Active" if self.config["enabled"] else "🔴 Disabled"
        cooldown_mins = self.config["cooldown"] // 60
        text = (
            f"{status}\n"
            f"⏱ Cooldown: {cooldown_mins} minutes\n"
            f"✉️ Text: {self.config['message']}\n"
            f"🖼 Image: {self.config['photo_url']}"
        )
        await utils.answer(message, text)

    async def _show_help(self, message: Message):
        """Show help message"""
        help_text = (
            "📚 Available commands:\n\n"
            ".a tg - Toggle status\n"
            ".a tt <text> - Change response text\n"
            ".a pt <url> - Change response image\n"
            ".a cd <minutes> - Set cooldown period\n"
            ".a st - Show current settings"
        )
        await utils.answer(message, help_text)
