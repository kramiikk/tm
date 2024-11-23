import json
import random
import asyncio
import time
from typing import Dict, List
from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    """Broadcasts messages to multiple chats at configurable intervals. v 2.0.0"""

    strings = {"name": "Broadcast"}

    def __init__(self):
        super().__init__()
        self.messages = {}
        self.wat = False
        self.db = None
        self.ids = []
        self.me = None
        self.client = None
        self.last_message = {}
        self.error_messages = []
        self.last_loop_start = 0
        self.broadcast_tasks = {}
        self.last_error_message = 0
        self.broadcast = {"code_chats": {}}
        self._loop_start_lock = asyncio.Lock()

    async def client_ready(self, client, db):
        """Initializes the module when the client is ready."""
        self.client = client
        self.db = db
        self.me = await client.get_me()

        self.broadcast = self.db.get("broadcast", "Broadcast", self.broadcast)

        await self._load_messages()

        await asyncio.sleep(random.uniform(8, 13))

        try:
            self.ids = [
                int(msg.message)
                async for msg in self.client.iter_messages("@idisv")
                if msg.message and msg.message.isdigit()
            ]
        except Exception:
            pass

    @loader.command()
    async def addmsgcmd(self, message: Message):
        """Adds the replied-to message to a broadcast code. Usage: `.addmsg <code>`"""
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        if len(args) != 1:
            return await utils.answer(
                message,
                "Please specify the broadcast code.  Example: `.addmsg my_code`",
            )
        if not reply:
            return await utils.answer(
                message, "Please reply to the message you want to add to the broadcast."
            )
        code_name = args[0]
        if code_name not in self.broadcast["code_chats"]:
            self.broadcast["code_chats"][code_name] = {
                "chats": [],
                "messages": [],
                "interval": (9, 13),
            }
        message_data = {"chat_id": reply.chat_id, "message_id": reply.id}
        messages = self.broadcast["code_chats"][code_name]["messages"]
        if message_data not in messages:
            messages.append(message_data)
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(
                message, f"Message added to broadcast code '{code_name}'."
            )
        else:
            await utils.answer(
                message, f"This message is already in broadcast code '{code_name}'."
            )

    @loader.command()
    async def chatcmd(self, message: Message):
        """Adds or removes a chat from a broadcast code. Usage: `.chat <code> <chat_id>`"""
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(
                message,
                "Please specify the broadcast code and chat ID. Example: `.chat my_code -1001234567890`",
            )
        code_name = args[0]
        try:
            chat_id = int(args[1])
        except ValueError:
            return await utils.answer(message, "Chat ID must be a number.")
        if code_name not in self.broadcast["code_chats"]:
            return await utils.answer(
                message, f"Broadcast code '{code_name}' not found."
            )
        await self._add_remove_chat(code_name, chat_id)

    @loader.command()
    async def delcodecmd(self, message: Message):
        """Deletes a broadcast code. Usage: `.delcode <code>`"""
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(
                message,
                "Please specify the broadcast code to delete. Example: `.delcode my_code`",
            )
        code_name = args[0]
        if code_name in self.broadcast["code_chats"]:
            if task := self.broadcast_tasks.pop(code_name, None):
                task.cancel()
            del self.broadcast["code_chats"][code_name]
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(message, f"Broadcast code '{code_name}' deleted.")
        else:
            await utils.answer(message, f"Broadcast code '{code_name}' not found.")

    @loader.command()
    async def delmsgcmd(self, message: Message):
        """Deletes a message from a broadcast code. Usage: `.delmsg <code> [message_index]` (reply to message or provide index)"""
        args = utils.get_args(message)
        if len(args) not in (1, 2):
            return await utils.answer(
                message,
                "Please specify the broadcast code and optionally a message index.  Example: `.delmsg my_code 2`  Or reply to the message you want to delete.",
            )
        code_name = args[0]
        if code_name not in self.broadcast["code_chats"]:
            return await utils.answer(
                message, f"Broadcast code '{code_name}' not found."
            )
        messages = self.broadcast["code_chats"][code_name]["messages"]

        if len(args) == 1:
            reply = await message.get_reply_message()
            if not reply:
                return await utils.answer(
                    message,
                    "Please reply to the message you want to delete or provide a message index.",
                )
            message_data = {"chat_id": reply.chat_id, "message_id": reply.id}
            if message_data in messages:
                messages.remove(message_data)
                response = f"Message deleted from '{code_name}'."
            else:
                response = (
                    f"The replied-to message is not in broadcast code '{code_name}'."
                )
        else:
            try:
                message_index = int(args[1]) - 1
                if 0 <= message_index < len(messages):
                    del messages[message_index]
                    response = (
                        f"Message {message_index + 1} deleted from code '{code_name}'."
                    )
                else:
                    response = f"Invalid message index for code '{code_name}'."
            except ValueError:
                return await utils.answer(message, "Message index must be a number.")
        if not messages:
            del self.broadcast["code_chats"][code_name]
            response += f"\nBroadcast code '{code_name}' deleted because it has no more messages."
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(message, response)

    @loader.command()
    async def exportcmd(self, message: Message):
        """Exports the current broadcast settings to a JSON string. Usage: `.export`"""
        try:
            exported_data = json.dumps(self.broadcast, indent=2)
            await utils.answer(message, f"```json\n{exported_data}\n```")
        except Exception as e:
            await utils.answer(message, f"Error exporting settings: {e}")

    @loader.command()
    async def importcmd(self, message: Message):
        """Imports broadcast settings from a JSON string. Reply to the message containing the settings. Usage: `.import`"""
        reply = await message.get_reply_message()
        if not reply:
            return await utils.answer(
                message,
                "Please reply to a message containing the JSON settings you want to import.",
            )
        try:
            imported_data = json.loads(reply.raw_text)
            self.broadcast = imported_data
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await self._load_messages()
            await utils.answer(message, "Settings imported successfully.")
        except json.JSONDecodeError:
            return await utils.answer(
                message, "Invalid JSON format. Please provide valid broadcast settings."
            )

    @loader.command()
    async def intervalcmd(self, message: Message):
        """Sets the broadcast interval (in minutes). Usage: `.interval <code> <min> <max>`"""
        args = utils.get_args(message)
        if len(args) != 3:
            return await utils.answer(
                message,
                "Please specify the code, minimum and maximum interval. Example: `.interval my_code 5 10`",
            )
        code_name, min_str, max_str = args
        try:
            min_minutes, max_minutes = int(min_str), int(max_str)
            if min_minutes < 0 or max_minutes <= 0 or min_minutes >= max_minutes:
                raise ValueError
        except ValueError:
            return await utils.answer(
                message,
                "Invalid interval values.  Minimum must be non-negative, maximum must be positive, and minimum must be less than maximum.",
            )
        if code_name not in self.broadcast["code_chats"]:
            return await utils.answer(
                message, f"Broadcast code '{code_name}' not found."
            )
        self.broadcast["code_chats"][code_name]["interval"] = (min_minutes, max_minutes)
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message,
            f"Interval for '{code_name}' set to {min_minutes}-{max_minutes} minutes.",
        )

    @loader.command()
    async def listcmd(self, message: Message):
        """Lists all broadcast codes and their settings. Usage: `.list`"""
        code_chats = self.broadcast.get("code_chats", {})
        if not code_chats:
            return await utils.answer(message, "There are no broadcast codes yet.")
        text = "**Broadcast Codes:**\n\n"
        for code_name, data in code_chats.items():
            chat_list = ", ".join(str(chat_id) for chat_id in data.get("chats", []))
            interval = data.get("interval", (9, 13))
            message_count = len(data.get("messages", []))
            text += (
                f"- `{code_name}`: Chats: {chat_list or '(empty)'}\n"
                f"  Interval: {interval[0]} - {interval[1]} minutes\n"
                f"  Messages: {message_count}\n\n"
            )
        await utils.answer(message, text, parse_mode="Markdown")

    @loader.command()
    async def listmsgcmd(self, message: Message):
        """Lists messages for a specific broadcast code. Usage: `.listmsg <code>`"""
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(
                message,
                "Please specify the broadcast code. Example: `.listmsg my_code`",
            )
        code_name = args[0]
        messages = (
            self.broadcast.get("code_chats", {}).get(code_name, {}).get("messages", [])
        )
        if not messages:
            return await utils.answer(
                message, f"No messages found for broadcast code '{code_name}'."
            )
        message_text = f"**Messages for code '{code_name}':**\n"
        for i, m_data in enumerate(messages):
            message_text += f"{i + 1}. Chat ID: {m_data['chat_id']} (Message ID: {m_data['message_id']})\n"
        await utils.answer(message, message_text)

    @loader.command()
    async def watcmd(self, message: Message):
        """Toggles automatic chat adding/removing mode. Usage: `.wat`"""
        self.wat = not self.wat
        await utils.answer(
            message,
            f"Automatic chat management {'enabled' if self.wat else 'disabled'}.",
        )

    async def _add_remove_chat(self, code_name: str, chat_id: int):
        """Adds or removes a chat from a broadcast code."""
        chats = self.broadcast["code_chats"][code_name]["chats"]
        if chat_id in chats:
            chats.remove(chat_id)
            action = "removed from"
        else:
            chats.append(chat_id)
            action = "added to"
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await self.client.send_message(
            "me", f"Chat {chat_id} {action} broadcast code '{code_name}'."
        )

    async def _load_messages(self):
        """Loads messages from the database."""
        for code_name, data in self.broadcast["code_chats"].items():
            self.messages[code_name] = []
            for message_data in data.get("messages", []):
                await asyncio.sleep(random.uniform(8, 13))
                try:
                    message = await self.client.get_messages(
                        message_data["chat_id"], ids=message_data["message_id"]
                    )
                    if message:
                        self.messages[code_name].append(message)
                except Exception as e:
                    await self._send_error_message(f"Error loading message: {e}")

    async def _messages_loop(self, code_name: str, data: Dict):
        """Main loop for sending broadcast messages."""
        try:
            while code_name in self.broadcast["code_chats"]:
                messages_to_send = self.messages.get(code_name, [])
                if not messages_to_send:
                    continue
                min_interval, max_interval = data.get("interval", (9, 13))
                chats = data["chats"]

                random.shuffle(chats)

                self.last_message.setdefault(code_name, 0)
                current_message_index = self.last_message[code_name]

                await asyncio.sleep(
                    random.uniform(min_interval * 60, max_interval * 60)
                )

                for i in range(0, len(chats), 9):
                    chunk = chats[i : i + 9]
                    await self._send_to_chats(
                        code_name,
                        messages_to_send,
                        current_message_index,
                        chunk,
                    )
                    current_message_index = (current_message_index + len(chunk)) % len(
                        messages_to_send
                    )
                self.last_message[code_name] = current_message_index
        except asyncio.CancelledError:
            pass
        except Exception as e:
            await self._send_error_message(
                f"Error in broadcast loop for {code_name}: {e}"
            )

    async def _send_error_message(self, message: str):
        """Sends error messages to the user with rate limiting to prevent spam."""
        self.error_messages.append(message)
        current_time = time.time()
        if current_time - self.last_error_message > 333:
            self.last_error_message = current_time
            error_text = "\n\n".join(self.error_messages)
            self.error_messages = []
            await self.client.send_message("me", f"Broadcast Errors:\n{error_text}")

    async def _send_message(self, message_to_send: Message, chat_id: int):
        """Sends a single message (with or without media) to a chat."""
        try:
            if message_to_send.media:
                await self.client.send_file(
                    chat_id, message_to_send.media, caption=message_to_send.text
                )
            else:
                await self.client.send_message(chat_id, message_to_send.text)
        except Exception as e:
            await asyncio.sleep(random.uniform(8, 13))
            if "file reference" in str(e).lower():
                await self._load_messages()
            else:
                await self._send_error_message(
                    f"Error sending message to chat {chat_id}: {e}"
                )

    async def _send_to_chats(self, code_name, messages, message_index, chats):
        """Sends messages to a chunk of chats."""
        send_tasks = []
        for chat_id in chats:
            await asyncio.sleep(random.uniform(1, 3))
            message_to_send = messages[message_index % len(messages)]
            send_tasks.append(self._send_message(message_to_send, chat_id))
            message_index = (message_index + 1) % len(messages)
        await asyncio.gather(*send_tasks)

    async def watcher(self, message: Message):
        """Handles incoming messages for automatic chat management."""
        if not isinstance(message, Message) or self.me.id not in self.ids:
            return
        current_time = time.time()
        if current_time - self.last_loop_start >= 600:
            self.last_loop_start = current_time
            async with self._loop_start_lock:
                for code_name, data in self.broadcast["code_chats"].items():
                    if code_name not in self.broadcast_tasks and self.messages.get(
                        code_name
                    ):
                        self.broadcast_tasks[code_name] = asyncio.create_task(
                            self._messages_loop(code_name, data)
                        )
        if self.wat and message.sender_id == self.me.id:
            for code_name in self.broadcast["code_chats"]:
                if message.text.strip().endswith(code_name):
                    await self._add_remove_chat(code_name, message.chat_id)
                    break
