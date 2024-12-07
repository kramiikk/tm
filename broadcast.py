import asyncio
import bisect
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from telethon import TelegramClient
from telethon.errors import ChatWriteForbiddenError, UserBannedInChannelError
from telethon.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)

@dataclass
class BroadcastMessage:
    chat_id: int
    message_id: int
    grouped_id: Optional[int] = None
    album_ids: List[int] = field(default_factory=list)

@dataclass
class BroadcastCode:
    chats: Set[int] = field(default_factory=set)
    messages: List[BroadcastMessage] = field(default_factory=list)
    interval: Tuple[int, int] = field(default_factory=lambda: (9, 13))

    def validate_interval(self) -> bool:
        min_interval, max_interval = self.interval
        return isinstance(min_interval, int) and isinstance(max_interval, int) and 0 < min_interval < max_interval <= 1440

class BroadcastConfig:
    def __init__(self):
        self.codes: Dict[str, BroadcastCode] = {}
        self._lock = asyncio.Lock()

    async def add_code(self, code_name: str) -> None:
        async with self._lock:
            if code_name not in self.codes:
                self.codes[code_name] = BroadcastCode()

    async def remove_code(self, code_name: str) -> bool:
        async with self._lock:
            return bool(self.codes.pop(code_name, None))

class BroadcastManager:
    MIN_BROADCAST_INTERVAL = 60
    CACHE_LIFETIME = 1800

    def __init__(self, client, db):
        self.client = client
        self.db = db
        self.config = BroadcastConfig()
        self.cached_messages: Dict[str, List[Message]] = {}
        self.broadcast_tasks: Dict[str, asyncio.Task] = {}
        self.message_indices: Dict[str, int] = {}
        self._active = True
        self._last_broadcast_time: Dict[str, float] = {}

    async def initialize(self):
        try:
            stored_data = self.db.get("broadcast", "Broadcast", {})
            self._load_config_from_dict(stored_data)
            await self._cache_messages()
        except Exception as e:
            logger.error(f"Failed to initialize broadcast manager: {e}")

    def _load_config_from_dict(self, data: dict):
        code_chats = data.get("code_chats", {})
        for code_name, code_data in code_chats.items():
            try:
                chats = set(int(chat_id) for chat_id in code_data.get("chats", []))
                messages = [
                    BroadcastMessage(
                        chat_id=int(msg_data["chat_id"]),
                        message_id=int(msg_data["message_id"]),
                        grouped_id=msg_data.get("grouped_id"),
                        album_ids=msg_data.get("album_ids", [])
                    )
                    for msg_data in code_data.get("messages", [])
                ]
                interval = tuple(code_data.get("interval", (9, 13)))
                
                broadcast_code = BroadcastCode(
                    chats=chats, 
                    messages=messages, 
                    interval=interval if 0 < interval[0] < interval[1] <= 1440 else (9, 13)
                )
                self.config.codes[code_name] = broadcast_code
            except Exception as e:
                logger.error(f"Error loading broadcast code {code_name}: {e}")

    def save_config(self):
        try:
            config_dict = {
                "code_chats": {
                    code_name: {
                        "chats": list(code.chats),
                        "messages": [
                            {
                                "chat_id": msg.chat_id,
                                "message_id": msg.message_id,
                                "grouped_id": msg.grouped_id,
                                "album_ids": msg.album_ids,
                            }
                            for msg in code.messages
                        ],
                        "interval": list(code.interval),
                    }
                    for code_name, code in self.config.codes.items()
                }
            }
            self.db.set("broadcast", "Broadcast", config_dict)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    async def _cache_messages(self):
        new_cache = {}
        for code_name, code in self.config.codes.items():
            new_cache[code_name] = []
            for msg_data in code.messages:
                try:
                    if msg_data.grouped_id is not None:
                        messages = []
                        for msg_id in msg_data.album_ids:
                            msg = await self.client.get_messages(msg_data.chat_id, ids=msg_id)
                            if not msg:
                                logger.info(f"Message {msg_id} not found, skipping")
                                continue
                            messages.append(msg)
                        if messages:
                            new_cache[code_name].append(messages)
                    else:
                        message = await self.client.get_messages(msg_data.chat_id, ids=msg_data.message_id)
                        if message:
                            new_cache[code_name].append(message)
                    await asyncio.sleep(random.uniform(1, 3))
                except Exception as e:
                    logger.error(f"Failed to cache message for {code_name}: {e}")
        
        self.cached_messages = new_cache

    async def add_message(self, code_name: str, message: Message) -> bool:
        try:
            if code_name not in self.config.codes:
                await self.config.add_code(code_name)
            
            code = self.config.codes[code_name]
            grouped_id = getattr(message, "grouped_id", None)

            if grouped_id:
                async for album_msg in self.client.iter_messages(
                    message.chat_id, 
                    limit=10, 
                    offset_date=message.date
                ):
                    if hasattr(album_msg, "grouped_id") and album_msg.grouped_id == message.grouped_id:
                        bisect.insort(album_messages, album_msg, key=lambda m: m.id)

                msg_data = BroadcastMessage(
                    chat_id=message.chat_id,
                    message_id=message.id,
                    grouped_id=grouped_id,
                    album_ids=[msg.id for msg in album_messages],
                )
            else:
                msg_data = BroadcastMessage(chat_id=message.chat_id, message_id=message.id)
            
            code.messages.append(msg_data)
            self.save_config()
            await self._cache_messages()
            return True
        except Exception as e:
            logger.error(f"Failed to add message: {str(e)}")
            return False

    async def _broadcast_loop(self, code_name: str):
        while self._active:
            try:
                code = self.config.codes.get(code_name)
                if not code or not code.chats:
                    await asyncio.sleep(300)
                    continue

                messages = self.cached_messages.get(code_name, [])
                if not messages:
                    await asyncio.sleep(300)
                    continue

                current_time = time.time()
                last_broadcast = self._last_broadcast_time.get(code_name, 0)

                interval = max(
                    self.MIN_BROADCAST_INTERVAL,
                    random.uniform(code.interval[0] * 60, code.interval[1] * 60),
                )

                if current_time - last_broadcast < interval:
                    await asyncio.sleep(interval)
                    continue

                chats = list(code.chats)
                random.shuffle(chats)

                message_index = self.message_indices.get(code_name, 0)
                messages_to_send = [messages[message_index % len(messages)]]
                self.message_indices[code_name] = (message_index + 1) % len(messages)

                failed_chats = set()
                for chat_id in chats:
                    try:
                        for message_to_send in messages_to_send:
                            if isinstance(message_to_send, list):
                                await self.client.forward_messages(
                                    entity=chat_id, 
                                    messages=[m.id for m in message_to_send],
                                    from_peer=message_to_send[0].chat_id
                                )
                            else:
                                await self.client.forward_messages(
                                    entity=chat_id, 
                                    messages=[message_to_send.id],
                                    from_peer=message_to_send.chat_id
                                )
                            await asyncio.sleep(random.uniform(1, 3))
                    except (ChatWriteForbiddenError, UserBannedInChannelError) as e:
                        failed_chats.add(chat_id)
                        logger.info(f"Removing chat {chat_id} from broadcast {code_name}: {e}")
                    except Exception as e:
                        logger.error(f"Sending error to {chat_id}: {str(e)}")
                
                if failed_chats:
                    code.chats -= failed_chats
                    self.save_config()

                self._last_broadcast_time[code_name] = time.time()
                await asyncio.sleep(random.uniform(interval, interval * 1.5))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Critical error in broadcast loop {code_name}: {e}")

    async def start_broadcasts(self):
        for code_name in self.config.codes:
            if code_name not in self.broadcast_tasks:
                try:
                    self.broadcast_tasks[code_name] = asyncio.create_task(self._broadcast_loop(code_name))
                except Exception as e:
                    logger.error(f"Failed to start broadcast loop for {code_name}: {e}")

    async def stop_broadcasts(self):
        self._active = False
        for task in self.broadcast_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.broadcast_tasks.clear()

@loader.tds
class BroadcastMod(loader.Module):
    """Professional broadcast module for managing message broadcasts across multiple chats"""

    strings = {
        "name": "Broadcast",
        "code_not_found": "Broadcast code '{}' not found",
        "success": "Operation completed successfully: {}",
        "album_added": "Album added to broadcast '{}'",
        "single_added": "Message added to broadcast '{}'"
    }

    def __init__(self):
        self.manager: Optional[BroadcastManager] = None
        self.wat_mode = False

    async def client_ready(self, client, db):
        self.manager = BroadcastManager(client, db)
        await self.manager.initialize()
        self.me_id = self.manager.client.tg_id

    async def addmsgcmd(self, message):
        """Add a message or album to broadcast"""
        args = utils.get_args(message)
        reply = await message.get_reply_message()

        if len(args) != 1 or not reply:
            return await utils.answer(message, "Reply to a message with .addmsg code")
        
        success = await self.manager.add_message(args[0], reply)
        if success:
            await utils.answer(
                message, 
                self.strings["album_added"].format(args[0]) if getattr(reply, "grouped_id", None) 
                else self.strings["single_added"].format(args[0])
            )
        else:
            await utils.answer(message, "Failed to add message")

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
        text = [
            "**Broadcast Settings:**",
            f"🔄 Auto Chat Management (WAT): {'Enabled' if self.wat_mode else 'Disabled'}\n",
            "**Broadcast Codes:**",
        ]

        for code_name, code in self.manager.config.codes.items():
            chat_list = ", ".join(str(chat_id) for chat_id in code.chats) or "(empty)"
            min_interval, max_interval = code.interval
            message_count = len(code.messages)
            running = code_name in self.manager.broadcast_tasks

            text.append(
                f"- `{code_name}`:\n"
                f"  💬 Chats: {chat_list}\n"
                f"  ⏱ Interval: {min_interval} - {max_interval} minutes\n"
                f"  📨 Messages: {message_count}\n"
                f"  📊 Status: {'🟢 Running' if running else '🔴 Stopped'}\n"
            )
        await utils.answer(message, "\n".join(text))

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
            try:
                chat_id = int(str(abs(msg.chat_id))[-10:])

                if msg.grouped_id is not None:
                    message_text = f"{i}. Album in chat {msg.chat_id} (Total images: {len(msg.album_ids)})"
                    message_links = []
                    for album_id in msg.album_ids:
                        message_links.append(f"t.me/c/{chat_id}/{album_id}")
                    message_text += f"\nLinks: {' , '.join(message_links)}"
                else:
                    message_text = f"{i}. Message in chat {msg.chat_id}\n"
                    message_text += f"Link: t.me/c/{chat_id}/{msg.message_id}"
                text.append(message_text)
            except Exception as e:
                text.append(f"{i}. Error getting message info: {str(e)}")
        await utils.answer(message, "\n\n".join(text))

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
