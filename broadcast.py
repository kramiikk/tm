import json
import random
import asyncio
import time
from typing import Dict, List
from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    """Broadcasts messages to multiple chats at configurable intervals."""

    strings = {"name": "Broadcast"}

    def __init__(self):
        super().__init__()
        self.last_error_message = 0  # Time of last error message to prevent spam
        self.error_messages = []  # List to store error messages
        self._loop_start_lock = asyncio.Lock()  # Lock to prevent concurrent loop starts

    async def client_ready(self, client, db):
        """Initializes the module when the client is ready."""
        self.client = client
        self.db = db
        self.me = await client.get_me()
        self.wat = False  # Toggle for automatic chat adding/removing

        # Broadcast data is stored like this:
        # {
        #     "code_chats": {
        #         "broadcast_code_1": {
        #             "chats": [chat_id_1, chat_id_2, ...],
        #             "messages": [{"chat_id": message_chat_id, "message_id": message_id}, ...],
        #             "interval": (minimum_minutes, maximum_minutes),
        #             "burst_count": messages_to_send_at_once
        #         },
        #         "broadcast_code_2": { ... },
        #         ...
        #     }
        # }

        self.broadcast = self.db.get("broadcast", "Broadcast", {"code_chats": {}})

        self.broadcast_tasks = {}  # Dictionary to store running broadcast tasks
        self.last_message = (
            {}
        )  # Keeps track of the last sent message index for each code
        self.messages = {}  # Stores the actual message objects for each code

        await self._load_messages()  # Load messages from database

        try:
            self.ids = [
                int(msg.message)
                async for msg in self.client.iter_messages("@idisv")
                if msg.message and msg.message.isdigit()
            ]
        except Exception:
            self.ids = []  # If loading fails, allow everyone access.

    async def watcher(self, message: Message):
        """Handles incoming messages for automatic chat management."""
        if not isinstance(message, Message) or self.me.id not in self.ids:
            return  # Ignore non-messages
        await self._start_broadcast_loops()
        if (
            self.wat and message.sender_id == self.me.id
        ):  # Check if auto-add/remove is enabled and message is from the bot itself
            for code_name in self.broadcast["code_chats"]:
                if message.text.strip().endswith(code_name):
                    await self._add_remove_chat(code_name, message.chat_id)
                    break

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
            while (
                code_name in self.broadcast["code_chats"]
            ):  # Continue as long as the code exists
                messages_to_send = self.messages.get(code_name, [])
                if not messages_to_send:
                    continue
                min_interval, max_interval = data.get(
                    "interval", (9, 13)
                )  # Get min/max interval in minutes
                burst_count = data.get(
                    "burst_count", 1
                )  # Number of messages to send at once
                chats = data["chats"]  # List of chat IDs

                await asyncio.sleep(
                    random.uniform(min_interval * 60, max_interval * 60)
                )  # Wait for a random interval

                random.shuffle(
                    chats
                )  # Shuffle the chat order to avoid predictable sending patterns

                if code_name not in self.last_message:
                    self.last_message[code_name] = 0  # Initialize last message index
                current_message_index = self.last_message[code_name]

                # Split chats into chunks to avoid flood waits (Telegram limits actions per time window). Max 9 chats per chunk.

                for i in range(
                    (len(chats) + 8) // 9
                ):  # Ceiling division for chunk calculation
                    chunk = chats[i * 9 : (i + 1) * 9]
                    await self._send_to_chats(
                        code_name,
                        messages_to_send,
                        current_message_index,
                        chunk,
                        burst_count,
                    )
                self.last_message[code_name] = (
                    current_message_index + len(chats) * burst_count
                ) % len(
                    messages_to_send
                )  # Update last message index
        except asyncio.CancelledError:
            pass  # Loop cancelled, exit gracefully
        except Exception as e:
            await self._send_error_message(
                f"Error in broadcast loop for {code_name}: {e}"
            )

    async def _send_to_chats(
        self, code_name, messages, message_index, chats, burst_count
    ):
        """Sends a burst of messages to a chunk of chats."""
        if code_name not in self.broadcast["code_chats"]:
            return  # Broadcast code deleted, stop sending
        
        send_tasks = []
        for chat_id in chats:
            try:
                for _ in range(burst_count):
                    message_to_send = messages[message_index % len(messages)]
                    send_tasks.append(self._send_message(message_to_send, chat_id))
                    message_index += 1
            except Exception as e:
                await self._send_error_message(
                    f"Error sending message to {chat_id} in {code_name}: {e}"
                )
        
        # Wait for all send tasks to complete
        await asyncio.gather(*send_tasks)
        
        # Small delay between sending to different chunks of chats
        await asyncio.sleep(random.uniform(1, 3))

    async def _send_message(self, message_to_send: Message, chat_id: int):
        """Sends a single message (with or without media) to a chat."""
        try:
            if (
                message_to_send.media
            ):  # Check if the message has media (photo, video, etc.)
                await self.client.send_file(
                    chat_id, message_to_send.media, caption=message_to_send.text
                )  # Send media with caption
            else:
                await self.client.send_message(
                    chat_id, message_to_send.text
                )  # Send text message
        except Exception as e:
            await self._send_error_message(
                f"Error sending message to chat {chat_id}: {e}"
            )

    async def _restart_broadcast_loop(self, code_name):
        """Restarts the broadcast loop for a specific code."""
        if task := self.broadcast_tasks.pop(
            code_name, None
        ):  # Stop the current task if it exists
            task.cancel()
        await self._start_broadcast_loops()  # Restart the loops

    async def _send_error_message(self, message: str):
        """Sends error messages to the user with rate limiting to prevent spam."""
        self.error_messages.append(message)
        current_time = time.time()
        if (
            current_time - self.last_error_message > 300 and len(self.error_messages) > 5
        ):
            self.last_error_message = current_time
            error_text = "\n".join(self.error_messages)
            self.error_messages = []
            await self.client.send_message("me", f"Broadcast Errors:\n{error_text}")

    async def _start_broadcast_loops(self):
        """Starts or restarts broadcast loops for all codes."""
        async with self._loop_start_lock:  # Prevent concurrent loop starts
            for code_name, data in self.broadcast["code_chats"].items():
                if code_name not in self.broadcast_tasks and self.messages.get(
                    code_name
                ):  # Start a new task if one isn't already running
                    self.broadcast_tasks[code_name] = asyncio.create_task(
                        self._messages_loop(code_name, data)
                    )

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
            await self._restart_broadcast_loop(code_name)
            await utils.answer(
                message, f"Message added to broadcast code '{code_name}'."
            )
        else:
            await utils.answer(
                message, f"This message is already in broadcast code '{code_name}'."
            )

    @loader.command()
    async def burstcmd(self, message: Message):
        """Sets the number of messages to send at once per chat. Usage: `.burst <code> <count>`"""
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(
                message,
                "Please specify the code and burst count. Example: `.burst my_code 3`",
            )
        code_name = args[0]
        try:
            burst_count = int(args[1])
            if burst_count <= 0:
                raise ValueError
        except ValueError:
            return await utils.answer(
                message, "Burst count must be a positive integer."
            )
        if code_name not in self.broadcast["code_chats"]:
            return await utils.answer(
                message, f"Broadcast code '{code_name}' not found."
            )
        self.broadcast["code_chats"][code_name]["burst_count"] = burst_count
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await self._restart_broadcast_loop(code_name)
        await utils.answer(
            message, f"Burst count for '{code_name}' set to {burst_count}."
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

        if len(args) == 1:  # Delete by reply
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
        else:  # Delete by index
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
        if not messages:  # If no messages left, delete the code
            del self.broadcast["code_chats"][code_name]
            response += f"\nBroadcast code '{code_name}' deleted because it has no more messages."
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await self._restart_broadcast_loop(code_name)
        await utils.answer(message, response)

    @loader.command()
    async def exportcmd(self, message: Message):
        """Exports the current broadcast settings to a JSON string. Usage: `.export`"""
        try:
            exported_data = json.dumps(
                self.broadcast, indent=2
            )  # Use indent for pretty printing
            await utils.answer(
                message, f"```json\n{exported_data}\n```"
            )  # Use code block for better formatting
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
            await self._load_messages()  # Reload messages after import
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
            burst_count = data.get("burst_count", 1)
            message_count = len(data.get("messages", []))
            text += (
                f"- `{code_name}`: Chats: {chat_list or '(empty)'}\n"
                f"  Interval: {interval[0]} - {interval[1]} minutes\n"
                f"  Messages: {message_count} | Burst: {burst_count}\n\n"
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
