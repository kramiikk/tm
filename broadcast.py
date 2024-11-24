from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import asyncio
import logging
import random
import time
from collections import deque

from telethon.errors import (
    ChatWriteForbiddenError,
    UserBannedInChannelError,
    MessageIdInvalidError,
    FileReferenceExpiredError,
)
from telethon.tl.types import Message
from .. import loader, utils

logger = logging.getLogger(__name__)


@dataclass
class BroadcastMessage:
    chat_id: int
    message_id: int


@dataclass
class BroadcastCode:
    chats: Set[int] = field(default_factory=set)
    messages: List[BroadcastMessage] = field(default_factory=list)
    interval: Tuple[int, int] = field(default_factory=lambda: (9, 13))

    def validate_interval(self) -> bool:
        """Validate that interval values are correct"""
        min_interval, max_interval = self.interval
        return (
            isinstance(min_interval, int)
            and isinstance(max_interval, int)
            and 0 < min_interval < max_interval <= 1440
        )


class BroadcastConfig:
    def __init__(self):
        self.codes: Dict[str, BroadcastCode] = {}
        self._lock = asyncio.Lock()

    async def add_code(self, code_name: str) -> None:
        """Thread-safe method to add a new broadcast code"""
        async with self._lock:
            if code_name not in self.codes:
                self.codes[code_name] = BroadcastCode()

    async def remove_code(self, code_name: str) -> bool:
        """Thread-safe method to remove a broadcast code"""
        async with self._lock:
            return bool(self.codes.pop(code_name, None))

    async def get_code(self, code_name: str) -> Optional[BroadcastCode]:
        """Thread-safe method to get a broadcast code"""
        async with self._lock:
            return self.codes.get(code_name)

    @classmethod
    def from_dict(cls, data: dict) -> "BroadcastConfig":
        config = cls()
        code_chats = data.get("code_chats", {})

        for code_name, code_data in code_chats.items():
            try:
                chats = set(int(chat_id) for chat_id in code_data.get("chats", []))
                messages = []
                for msg_data in code_data.get("messages", []):
                    try:
                        chat_id = int(msg_data["chat_id"])
                        message_id = int(msg_data["message_id"])
                        messages.append(BroadcastMessage(chat_id, message_id))
                    except (KeyError, ValueError, TypeError):
                        continue
                interval = tuple(code_data.get("interval", (9, 13)))
                if not (0 < interval[0] < interval[1] <= 1440):
                    interval = (9, 13)
                broadcast_code = BroadcastCode(
                    chats=chats, messages=messages, interval=interval
                )
                config.codes[code_name] = broadcast_code
            except Exception as e:
                logger.error(f"Error loading broadcast code {code_name}: {e}")
                continue
        return config

    def to_dict(self) -> dict:
        return {
            "code_chats": {
                code_name: {
                    "chats": list(code.chats),
                    "messages": [
                        {"chat_id": msg.chat_id, "message_id": msg.message_id}
                        for msg in code.messages
                    ],
                    "interval": list(code.interval),
                }
                for code_name, code in self.codes.items()
            }
        }


class BroadcastManager:
    """Manages message broadcasting operations and state"""

    CACHE_LIFETIME = 1800
    MIN_BROADCAST_INTERVAL = 60

    def __init__(self, client, db):
        self.client = client
        self.db = db
        self.config = BroadcastConfig()
        self.cached_messages: Dict[str, List[Message]] = {}
        self.broadcast_tasks: Dict[str, asyncio.Task] = {}
        self.message_indices: Dict[str, int] = {}
        self.last_cache_cleanup = 0
        self._cache_lock = asyncio.Lock()
        self._broadcast_lock = asyncio.Lock()
        self._last_broadcast_time: Dict[str, float] = {}
        self._active = True

    async def initialize(self):
        """Initialize the broadcast manager with stored configuration"""
        try:
            stored_data = self.db.get("broadcast", "Broadcast", {})
            self.config = BroadcastConfig.from_dict(stored_data)
            await self._cache_messages()
            asyncio.create_task(self._periodic_cache_check())
        except Exception as e:
            logger.error(f"Failed to initialize broadcast manager: {e}")
            self.config = BroadcastConfig()

    async def _periodic_cache_check(self):
        """Периодически проверяет и обновляет кэш"""
        while self._active:
            try:
                await self._check_cache_lifetime()
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"Error in periodic cache check: {e}")
                await asyncio.sleep(60)

    def save_config(self):
        """Save current configuration to database"""
        try:
            self.db.set("broadcast", "Broadcast", self.config.to_dict())
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    async def _cache_messages(self):
        """Cache all broadcast messages with error handling"""
        async with self._cache_lock:
            self.last_cache_cleanup = time.time()
            new_cache = {}

            for code_name, code in self.config.codes.items():
                new_cache[code_name] = []
                for msg_data in code.messages:
                    try:
                        message = await self.client.get_messages(
                            msg_data.chat_id, ids=msg_data.message_id
                        )
                        if message:
                            new_cache[code_name].append(message)
                        await asyncio.sleep(random.uniform(1, 2))
                    except Exception as e:
                        logger.error(f"Failed to cache message for {code_name}: {e}")
            self.cached_messages = new_cache

    async def _check_cache_lifetime(self):
        """Check if cache needs to be refreshed"""
        async with self._cache_lock:
            current_time = time.time()
            if current_time - self.last_cache_cleanup >= self.CACHE_LIFETIME:
                await self._cache_messages()

    async def add_message(self, code_name: str, message: Message) -> bool:
        """Add a message to a broadcast code"""
        if code_name not in self.config.codes:
            await self.config.add_code(code_name)
        msg_data = BroadcastMessage(message.chat_id, message.id)
        code = self.config.codes[code_name]

        if any(
            m.chat_id == msg_data.chat_id and m.message_id == msg_data.message_id
            for m in code.messages
        ):
            return False
        code.messages.append(msg_data)
        self.save_config()
        await self._cache_messages()
        return True

    async def remove_message(
        self,
        code_name: str,
        message: Optional[Message] = None,
        index: Optional[int] = None,
    ) -> bool:
        """Remove a message from a broadcast code"""
        if code_name not in self.config.codes:
            return False
        code = self.config.codes[code_name]
        removed = False

        if message:
            msg_data = BroadcastMessage(message.chat_id, message.id)
            if msg_data in code.messages:
                code.messages.remove(msg_data)
                removed = True
        elif index is not None and 0 <= index < len(code.messages):
            code.messages.pop(index)
            removed = True
        if removed:
            if not code.messages:
                await self.config.remove_code(code_name)
            self.save_config()
            await self._cache_messages()
        return removed

    async def manage_chat(self, code_name: str, chat_id: int) -> Tuple[bool, str]:
        """Add or remove a chat from a broadcast code"""
        try:
            chat_id = int(chat_id)
            if chat_id == 0:
                return False, "Invalid chat ID"
        except ValueError:
            return False, "Chat ID must be a number"
        if code_name not in self.config.codes:
            return False, "Code not found"
        code = self.config.codes[code_name]
        if chat_id in code.chats:
            code.chats.remove(chat_id)
            action = "removed from"
        else:
            code.chats.add(chat_id)
            action = "added to"
        self.save_config()
        return True, f"Chat {chat_id} {action} broadcast code '{code_name}'"

    async def set_interval(
        self, code_name: str, min_interval: int, max_interval: int
    ) -> bool:
        """Set broadcast interval for a code"""
        if code_name not in self.config.codes:
            return False
        code = self.config.codes[code_name]
        code.interval = (min_interval, max_interval)

        if not code.validate_interval():
            code.interval = (9, 13)
            return False
        self.save_config()
        return True

    async def _broadcast_loop(self, code_name: str):
        """Main broadcasting loop for a code"""
        while self._active:
            try:
                async with self._broadcast_lock:
                    if code_name not in self.config.codes:
                        break
                    code = self.config.codes[code_name]
                    messages = self.cached_messages.get(code_name, [])

                    if not messages or not code.chats:
                        await asyncio.sleep(13)
                        continue
                    current_time = time.time()
                    last_broadcast = self._last_broadcast_time.get(code_name, 0)
                    if current_time - last_broadcast < self.MIN_BROADCAST_INTERVAL:
                        await asyncio.sleep(
                            self.MIN_BROADCAST_INTERVAL
                            - (current_time - last_broadcast)
                        )
                        continue
                    min_interval, max_interval = code.interval
                    chats = list(code.chats)
                    random.shuffle(chats)

                    current_index = self.message_indices.get(code_name, 0)
                    delay = random.uniform(min_interval * 60, max_interval * 60)
                    await asyncio.sleep(delay)

                    failed_chats = set()
                    for i, chat_id in enumerate(chats):
                        try:
                            message = messages[i % len(messages)]
                            await self._send_message(message, chat_id)
                        except (ChatWriteForbiddenError, UserBannedInChannelError):
                            failed_chats.add(chat_id)
                            logger.info(
                                f"Removing chat {chat_id} from broadcast {code_name} due to permissions"
                            )
                        except Exception as e:
                            logger.error(
                                f"Error sending to {chat_id} in {code_name}: {str(e)}"
                            )
                            continue
                    # Удаление проблемных чатов

                    if failed_chats:
                        code.chats -= failed_chats
                        self.save_config()
                    self.message_indices[code_name] = (
                        current_index + len(chats)
                    ) % len(messages)
                    self._last_broadcast_time[code_name] = time.time()
            except asyncio.CancelledError:
                logger.info(f"Broadcast loop cancelled for {code_name}")
                break
            except Exception as e:
                logger.error(f"Broadcast loop error for {code_name}: {e}")
                await asyncio.sleep(13)

    async def _send_message(self, message: Message, chat_id: int):
        """Send a single message to a chat"""
        if message.media:
            return await self.client.send_file(
                chat_id, message.media, caption=message.text
            )
        else:
            return await self.client.send_message(chat_id, message.text)

    async def cleanup_tasks(self):
        """Clean up completed or failed tasks"""
        for code_name, task in list(self.broadcast_tasks.items()):
            if task.done():
                try:
                    await task
                except Exception as e:
                    logger.error(f"Task cleanup error for {code_name}: {e}")
                finally:
                    del self.broadcast_tasks[code_name]

    async def start_broadcasts(self):
        """Start broadcast tasks for all codes"""
        await self.cleanup_tasks()
        for code_name in self.config.codes:
            if (
                code_name not in self.broadcast_tasks
                and self.cached_messages.get(code_name)
                and not (
                    self.broadcast_tasks.get(code_name)
                    and not self.broadcast_tasks[code_name].done()
                )
            ):
                try:
                    self.broadcast_tasks[code_name] = asyncio.create_task(
                        self._broadcast_loop(code_name)
                    )
                except Exception as e:
                    logger.error(f"Failed to start broadcast loop for {code_name}: {e}")

    async def stop_broadcasts(self):
        """Stop all broadcast tasks"""
        self._active = False
        for code_name, task in list(self.broadcast_tasks.items()):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.broadcast_tasks[code_name]


@loader.tds
class BroadcastMod(loader.Module):
    """Professional broadcast module for managing message broadcasts across multiple chats. v 2.4.0"""

    strings = {
        "name": "Broadcast",
        "code_not_found": "Broadcast code '{}' not found",
        "success": "Operation completed successfully: {}",
    }

    def __init__(self):
        self.manager: Optional[BroadcastManager] = None
        self.wat_mode = False
        self._command_locks: Dict[int, float] = {}

    async def client_ready(self, client, db):
        """Initialize the module"""
        self.manager = BroadcastManager(client, db)
        await self.manager.initialize()
        self.me_id = self.manager.client.tg_id

    async def addmsgcmd(self, message: Message):
        """Add a message to broadcast. Usage: .addmsg code"""
        args = utils.get_args(message)
        reply = await message.get_reply_message()

        if len(args) != 1 or not reply:
            return await utils.answer(message, "Reply to a message with .addmsg code")
        success = await self.manager.add_message(args[0], reply)
        await utils.answer(
            message,
            f"Message {'added to' if success else 'already in'} broadcast '{args[0]}'",
        )

    async def chatcmd(self, message: Message):
        """Add or remove a chat from broadcast. Usage: .chat code <chat_id>"""
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(message, "Usage: .chat code <chat_id>")
        try:
            code_name, chat_id = args[0], int(args[1])
        except ValueError:
            return await utils.answer(message, "Chat ID must be a number")
        success, response = await self.manager.manage_chat(code_name, chat_id)
        if success:
            await utils.answer(message, self.strings["success"].format(response))

    async def delcodecmd(self, message: Message):
        """Delete a broadcast code. Usage: .delcode code"""
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Usage: .delcode code")
        code_name = args[0]
        if code_name not in self.manager.config.codes:
            return await utils.answer(
                message, self.strings["code_not_found"].format(code_name)
            )
        if task := self.manager.broadcast_tasks.pop(code_name, None):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await self.manager.config.remove_code(code_name)
        if code_name in self.manager.cached_messages:
            del self.manager.cached_messages[code_name]
        if code_name in self.manager.message_indices:
            del self.manager.message_indices[code_name]
        self.manager.save_config()
        await utils.answer(
            message,
            self.strings["success"].format(f"Broadcast code '{code_name}' deleted"),
        )

    async def delmsgcmd(self, message: Message):
        """Delete a message from broadcast. Usage: .delmsg code [index]"""
        args = utils.get_args(message)
        if len(args) not in (1, 2):
            return await utils.answer(
                message, "Usage: .delmsg code [index] or reply to message"
            )
        code_name = args[0]
        if code_name not in self.manager.config.codes:
            return await utils.answer(
                message, self.strings["code_not_found"].format(code_name)
            )
        if len(args) == 1:
            reply = await message.get_reply_message()
            if not reply:
                return await utils.answer(
                    message, "Reply to a message with this command"
                )
            success = await self.manager.remove_message(code_name, message=reply)
            action_text = "removed from" if success else "not found in"
        else:
            try:
                index = int(args[1]) - 1
                success = await self.manager.remove_message(code_name, index=index)
                action_text = "removed from" if success else "invalid index for"
            except ValueError:
                return await utils.answer(message, "Index must be a number")
        await utils.answer(
            message,
            self.strings["success"].format(f"Message {action_text} '{code_name}'"),
        )

    async def intervalcmd(self, message: Message):
        """Set broadcast interval. Usage: .interval code <min> <max>"""
        args = utils.get_args(message)
        if len(args) != 3:
            return await utils.answer(
                message, "Usage: .interval code <min_minutes> <max_minutes>"
            )
        code_name, min_str, max_str = args
        try:
            min_minutes = int(min_str)
            max_minutes = int(max_str)
        except ValueError:
            return await utils.answer(message, "Interval values must be numbers")
        success = await self.manager.set_interval(code_name, min_minutes, max_minutes)
        if success:
            await utils.answer(
                message,
                self.strings["success"].format(
                    f"Interval for '{code_name}' set to {min_minutes}-{max_minutes} minutes"
                ),
            )

    async def listcmd(self, message: Message):
        """List all broadcast codes and settings. Usage: .list"""
        if not self.manager.config.codes:
            return await utils.answer(message, "No broadcast codes configured")
        text = "**Broadcast Codes:**\n"
        for code_name, code in self.manager.config.codes.items():
            chat_list = ", ".join(str(chat_id) for chat_id in code.chats) or "(empty)"
            min_interval, max_interval = code.interval
            message_count = len(code.messages)
            running = code_name in self.manager.broadcast_tasks
            text += f"- `{code_name}`:\n  Chats: {chat_list}\n  Interval: {min_interval} - {max_interval} minutes\n  Messages: {message_count}\n  Status: {'Running' if running else 'Stopped'}\n\n"
        await utils.answer(message, text)

    async def listmsgcmd(self, message: Message):
        """List messages in a broadcast code. Usage: .listmsg code"""
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Usage: .listmsg code")
        code_name = args[0]
        if code_name not in self.manager.config.codes:
            return await utils.answer(
                message, self.strings["code_not_found"].format(code_name)
            )
        messages = self.manager.config.codes[code_name].messages
        if not messages:
            return await utils.answer(
                message, f"No messages in broadcast code '{code_name}'"
            )
        text = [f"**Messages in '{code_name}':**"]
        for i, msg in enumerate(messages, 1):
            text.append(f"{i}. Chat ID: {msg.chat_id} (Message ID: {msg.message_id})")
        await utils.answer(message, "\n".join(text))

    async def watcmd(self, message: Message):
        """Toggle automatic chat management. Usage: .wat"""
        self.wat_mode = not self.wat_mode
        await utils.answer(
            message,
            self.strings["success"].format(
                f"Auto chat management {'enabled' if self.wat_mode else 'disabled'}"
            ),
        )

    async def watcher(self, message: Message):
        """Watch for messages to handle automatic chat management"""
        if not isinstance(message, Message):
            return
        current_time = time.time()
        if (
            not hasattr(self, "_last_broadcast_check")
            or current_time - self._last_broadcast_check >= 600
        ):
            self._last_broadcast_check = current_time
            await self.manager.start_broadcasts()
        if self.wat_mode and message.sender_id == self.me_id:
            text = message.text.strip() if message.text else ""
            for code_name in self.manager.config.codes:
                if text.endswith(code_name):
                    await self.manager.manage_chat(code_name, message.chat_id)
                    break
