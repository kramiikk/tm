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

    RETRY_DELAYS = [3, 8, 13]
    CACHE_LIFETIME = 3600
    ERROR_REPORT_INTERVAL = 300

    def __init__(self, client, db):
        self.client = client
        self.db = db
        self.config = BroadcastConfig()
        self.cached_messages: Dict[str, List[Message]] = {}
        self.broadcast_tasks: Dict[str, asyncio.Task] = {}
        self.message_indices: Dict[str, int] = {}
        self.error_queue = deque(maxlen=100)
        self.last_error_time = 0
        self.last_cache_cleanup = 0
        self._loop_lock = asyncio.Lock()
        self._message_lock = asyncio.Lock()
        self._cache_lock = asyncio.Lock()

    async def initialize(self):
        """Initialize the broadcast manager with stored configuration"""
        try:
            stored_data = self.db.get("broadcast", "Broadcast", {})
            self.config = BroadcastConfig.from_dict(stored_data)
            await self._cache_messages()
        except Exception as e:
            logger.error(f"Failed to initialize broadcast manager: {e}")
            self.config = BroadcastConfig()

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
                        await asyncio.sleep(random.uniform(2, 4))
                    except Exception as e:
                        await self._log_error(
                            f"Failed to cache message for {code_name}: {e}"
                        )
            self.cached_messages = new_cache

    async def _check_cache_lifetime(self):
        """Check if cache needs to be refreshed"""
        current_time = time.time()
        if current_time - self.last_cache_cleanup >= self.CACHE_LIFETIME:
            await self._cache_messages()

    async def add_message(self, code_name: str, message: Message) -> bool:
        """Add a message to a broadcast code"""
        async with self._message_lock:
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
        async with self._message_lock:
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
        try:
            while True:
                async with self._loop_lock:
                    if code_name not in self.config.codes:
                        break
                    code = self.config.codes[code_name]
                    messages = self.cached_messages.get(code_name, [])

                    if not messages or not code.chats:
                        await asyncio.sleep(60)
                        continue
                    min_interval, max_interval = code.interval
                    chats = list(code.chats)
                    random.shuffle(chats)

                    current_index = self.message_indices.get(code_name, 0)

                    await asyncio.sleep(
                        random.uniform(min_interval * 60, max_interval * 60)
                    )

                    for i in range(0, len(chats), 9):
                        chunk = chats[i : i + 9]
                        await self._broadcast_to_chunk(
                            code_name, messages, current_index, chunk
                        )
                        current_index = (current_index + len(chunk)) % len(messages)
                    self.message_indices[code_name] = current_index
                    await self._check_cache_lifetime()
        except asyncio.CancelledError:
            logger.info(f"Broadcast loop cancelled for {code_name}")
        except Exception as e:
            await self._log_error(f"Broadcast loop error for {code_name}: {e}")

    async def _broadcast_to_chunk(
        self,
        code_name: str,
        messages: List[Message],
        start_index: int,
        chats: List[int],
    ):
        """Broadcast messages to a chunk of chats"""
        tasks = []
        for i, chat_id in enumerate(chats):
            message = messages[(start_index + i) % len(messages)]
            await asyncio.sleep(random.uniform(1, 3))
            tasks.append(self._send_message_with_retry(message, chat_id))
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for chat_id, result in zip(chats, results):
            if isinstance(result, Exception):
                await self._handle_send_error(code_name, chat_id, result)

    async def _send_message_with_retry(
        self, message: Message, chat_id: int, retry_count: int = 0
    ):
        """Send a message with retry mechanism"""
        try:
            return await self._send_message(message, chat_id)
        except (FileReferenceExpiredError, MessageIdInvalidError):
            if retry_count < len(self.RETRY_DELAYS):
                await self._cache_messages()
                await asyncio.sleep(self.RETRY_DELAYS[retry_count])
                return await self._send_message_with_retry(
                    message, chat_id, retry_count + 1
                )
            raise
        except (ChatWriteForbiddenError, UserBannedInChannelError):
            raise
        except Exception as e:
            if retry_count < len(self.RETRY_DELAYS):
                await asyncio.sleep(self.RETRY_DELAYS[retry_count])
                return await self._send_message_with_retry(
                    message, chat_id, retry_count + 1
                )
            raise

    async def _send_message(self, message: Message, chat_id: int):
        """Send a single message to a chat"""
        if message.media:
            return await self.client.send_file(
                chat_id, message.media, caption=message.text
            )
        else:
            return await self.client.send_message(chat_id, message.text)

    async def _handle_send_error(self, code_name: str, chat_id: int, error: Exception):
        """Handle errors during message sending"""
        error_msg = f"Error sending to {chat_id} in {code_name}: {str(error)}"

        if isinstance(error, (ChatWriteForbiddenError, UserBannedInChannelError)):
            if code := self.config.codes.get(code_name):
                code.chats.discard(chat_id)
                self.save_config()
                error_msg += " (chat removed from broadcast)"
        await self._log_error(error_msg)

    async def _log_error(self, error_msg: str):
        """Log errors with rate limiting"""
        self.error_queue.append(error_msg)
        current_time = time.time()

        if current_time - self.last_error_time > self.ERROR_REPORT_INTERVAL:
            self.last_error_time = current_time
            errors = "\n".join(self.error_queue)
            self.error_queue.clear()
            logger.error(errors)
            await self.client.send_message("me", f"Broadcast Errors:\n{errors}")

    async def cleanup_tasks(self):
        """Clean up completed or failed tasks"""
        for code_name, task in list(self.broadcast_tasks.items()):
            if task.done():
                try:
                    await task
                except Exception as e:
                    await self._log_error(f"Task cleanup error for {code_name}: {e}")
                finally:
                    del self.broadcast_tasks[code_name]

    async def start_broadcasts(self):
        """Start broadcast tasks for all codes"""
        async with self._loop_lock:
            await self.cleanup_tasks()
            for code_name in self.config.codes:
                if code_name not in self.broadcast_tasks and self.cached_messages.get(
                    code_name
                ):
                    self.broadcast_tasks[code_name] = asyncio.create_task(
                        self._broadcast_loop(code_name)
                    )


@loader.tds
class BroadcastMod(loader.Module):
    """Professional broadcast module for managing message broadcasts across multiple chats. v 2.2.0"""

    strings = {
        "name": "Broadcast",
        "invalid_args": "Invalid arguments. {}",
        "code_not_found": "Broadcast code '{}' not found",
        "need_reply": "Reply to a message with this command",
        "success": "Operation completed successfully: {}",
        "error": "Error: {}",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "admin_id",
            None,
            "Admin user ID for error reporting",
            "max_retries",
            3,
            "Maximum number of retries for failed broadcasts",
            "cooldown",
            5,
            "Command cooldown in seconds",
        )
        self.manager: Optional[BroadcastManager] = None
        self.wat_mode = False
        self._command_locks: Dict[int, float] = {}

    async def client_ready(self, client, db):
        """Initialize the module"""
        self.manager = BroadcastManager(client, db)
        await self.manager.initialize()

    async def _check_cooldown(self, user_id: int) -> bool:
        """Check if user is on cooldown"""
        current_time = time.time()
        if user_id in self._command_locks:
            if current_time - self._command_locks[user_id] < self.config["cooldown"]:
                return False
        self._command_locks[user_id] = current_time
        return True

    async def _handle_command(self, message: Message, action: callable):
        """Generic command handler with cooldown and error handling"""
        if not await self._check_cooldown(message.sender_id):
            return await utils.answer(
                message,
                self.strings["error"].format("Please wait before using commands again"),
            )
        try:
            result = await action()
            if result is not None:
                await utils.answer(message, result)
        except Exception as e:
            logger.exception(e)
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command
    async def addmsgcmd(self, message: Message):
        """Add a message to broadcast. Usage: .addmsg <code>"""

        async def action():
            args = utils.get_args(message)
            reply = await message.get_reply_message()

            if len(args) != 1 or not reply:
                return self.strings["invalid_args"].format(
                    "Reply to a message with .addmsg <code>"
                )
            success = await self.manager.add_message(args[0], reply)
            return self.strings["success"].format(
                f"Message {'added to' if success else 'already in'} broadcast '{args[0]}'"
            )

        await self._handle_command(message, action)

    @loader.command
    async def chatcmd(self, message: Message):
        """Add or remove a chat from broadcast. Usage: .chat <code> <chat_id>"""

        async def action():
            args = utils.get_args(message)
            if len(args) != 2:
                return self.strings["invalid_args"].format(
                    "Usage: .chat <code> <chat_id>"
                )
            try:
                code_name, chat_id = args[0], int(args[1])
            except ValueError:
                return self.strings["invalid_args"].format("Chat ID must be a number")
            success, response = await self.manager.manage_chat(code_name, chat_id)
            if success:
                return self.strings["success"].format(response)
            return self.strings["error"].format(response)

        await self._handle_command(message, action)

    @loader.command
    async def delcodecmd(self, message: Message):
        """Delete a broadcast code. Usage: .delcode <code>"""

        async def action():
            args = utils.get_args(message)
            if len(args) != 1:
                return self.strings["invalid_args"].format("Usage: .delcode <code>")
            code_name = args[0]
            if code_name not in self.manager.config.codes:
                return self.strings["code_not_found"].format(code_name)
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
            return self.strings["success"].format(
                f"Broadcast code '{code_name}' deleted"
            )

        await self._handle_command(message, action)

    @loader.command
    async def delmsgcmd(self, message: Message):
        """Delete a message from broadcast. Usage: .delmsg <code> [index]"""

        async def action():
            args = utils.get_args(message)
            if len(args) not in (1, 2):
                return self.strings["invalid_args"].format(
                    "Usage: .delmsg <code> [index] or reply to message"
                )
            code_name = args[0]
            if code_name not in self.manager.config.codes:
                return self.strings["code_not_found"].format(code_name)
            if len(args) == 1:
                reply = await message.get_reply_message()
                if not reply:
                    return self.strings["need_reply"]
                success = await self.manager.remove_message(code_name, message=reply)
                action_text = "removed from" if success else "not found in"
            else:
                try:
                    index = int(args[1]) - 1
                    success = await self.manager.remove_message(code_name, index=index)
                    action_text = "removed from" if success else "invalid index for"
                except ValueError:
                    return self.strings["invalid_args"].format("Index must be a number")
            return self.strings["success"].format(
                f"Message {action_text} '{code_name}'"
            )

        await self._handle_command(message, action)

    @loader.command
    async def intervalcmd(self, message: Message):
        """Set broadcast interval. Usage: .interval <code> <min> <max>"""

        async def action():
            args = utils.get_args(message)
            if len(args) != 3:
                return self.strings["invalid_args"].format(
                    "Usage: .interval <code> <min_minutes> <max_minutes>"
                )
            code_name, min_str, max_str = args
            try:
                min_minutes = int(min_str)
                max_minutes = int(max_str)
            except ValueError:
                return self.strings["invalid_args"].format(
                    "Interval values must be numbers"
                )
            success = await self.manager.set_interval(
                code_name, min_minutes, max_minutes
            )
            if success:
                return self.strings["success"].format(
                    f"Interval for '{code_name}' set to {min_minutes}-{max_minutes} minutes"
                )
            return self.strings["error"].format(
                f"Invalid interval values or code '{code_name}' not found"
            )

        await self._handle_command(message, action)

    @loader.command
    async def listcmd(self, message: Message):
        """List all broadcast codes and settings. Usage: .list"""

        async def action():
            if not self.manager.config.codes:
                return "No broadcast codes configured"
            text = ["**Broadcast Codes:**\n"]
            for code_name, code in self.manager.config.codes.items():
                chat_list = ", ".join(str(chat_id) for chat_id in code.chats)
                min_interval, max_interval = code.interval
                message_count = len(code.messages)
                running = code_name in self.manager.broadcast_tasks

                text.extend(
                    [
                        f"- `{code_name}`:",
                        f"  Chats: {chat_list or '(empty)'}",
                        f"  Interval: {min_interval} - {max_interval} minutes",
                        f"  Messages: {message_count}",
                        f"  Status: {'Running' if running else 'Stopped'}\n",
                    ]
                )
            return "\n".join(text)

        await self._handle_command(message, action)

    @loader.command
    async def listmsgcmd(self, message: Message):
        """List messages in a broadcast code. Usage: .listmsg <code>"""

        async def action():
            args = utils.get_args(message)
            if len(args) != 1:
                return self.strings["invalid_args"].format("Usage: .listmsg <code>")
            code_name = args[0]
            if code_name not in self.manager.config.codes:
                return self.strings["code_not_found"].format(code_name)
            messages = self.manager.config.codes[code_name].messages
            if not messages:
                return f"No messages in broadcast code '{code_name}'"
            text = [f"**Messages in '{code_name}':**"]
            for i, msg in enumerate(messages, 1):
                text.append(
                    f"{i}. Chat ID: {msg.chat_id} (Message ID: {msg.message_id})"
                )
            return "\n".join(text)

        await self._handle_command(message, action)

    @loader.command
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
        if self.wat_mode and message.sender_id == self.manager.client.uid:
            text = message.text.strip() if message.text else ""
            for code_name in self.manager.config.codes:
                if text.endswith(code_name):
                    await self.manager.manage_chat(code_name, message.chat_id)
                    break
