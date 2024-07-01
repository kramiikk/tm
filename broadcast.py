import asyncio
import random
import contextlib
from typing import Dict, List

from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    """Module for broadcasting messages to a list of chats."""

    strings = {"name": "Broadcast"}

    async def client_ready(self, client, db):
        """Initializes the module when the client is started."""
        self.db = db
        self.wat = False
        self.client = client
        self.watcher_counter = 0
        self.me = await client.get_me()
        self.allowed = await self._get_allowed()
        self.send_success_messages = False
        self.broadcast_tasks = {}
        self.last_message = {}
        self.messages = {}
        self.broadcast = self.db.get(
            "broadcast",
            "Broadcast",
            {"code_chats": {}},
        )
        await self._load_messages()

    async def watcher(self, message: Message):
        """Handles incoming messages and manages broadcast tasks."""
        if (
            not isinstance(message, Message)
            or self.me.id not in self.allowed
            or not self.broadcast["code_chats"]
        ):
            return
        self.watcher_counter += 1
        if self.watcher_counter % 10 == 0:
            all_tasks_running = all(
                code_name in self.broadcast_tasks
                for code_name in self.broadcast["code_chats"]
            )
            if not all_tasks_running:
                if self.watcher_counter % 1000 == 0:
                    self.allowed = await self._get_allowed()
                    await self._load_messages()
                    return
                for code_name, data in self.broadcast["code_chats"].items():
                    if code_name not in self.broadcast_tasks:
                        self.broadcast_tasks[code_name] = asyncio.create_task(
                            self._messages_loop(code_name, data)
                        )
        if (
            message.sender_id != self.me.id
            or not self.wat
            or message.text.startswith(".")
        ):
            return
        for code_name in self.broadcast["code_chats"]:
            if code_name in message.text:
                action = await self._add_remove_chat(code_name, message.chat_id)
                await self.client.send_message(
                    "me", f"Chat {message.chat_id} {action} '{code_name}'."
                )
                return

    # --- Module commands ---

    @loader.unrestricted
    async def addmsgcmd(self, message: Message):
        """Adds a message to the broadcast.

        Usage:
        ```
        .addmsg <broadcast_name>
        ```
        <broadcast_name> - the name of the broadcast to add the message to.

        **You need to reply to this command with the message you want to add.**
        """
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        if len(args) != 1:
            return await utils.answer(message, "Specify the broadcast code.")
        if not reply:
            return await utils.answer(message, "Reply to the message you want to add.")
        code_name = args[0]
        message_data = {"chat_id": reply.chat_id, "message_id": reply.id}
        if code_name not in self.broadcast["code_chats"]:
            self.broadcast["code_chats"][code_name] = {
                "chats": [],
                "messages": [],
                "interval": (9, 13),
            }
        messages = self.broadcast["code_chats"][code_name]["messages"]
        if message_data not in messages:
            messages.append(message_data)
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(message, f"Added to code '{code_name}'.")
        else:
            await utils.answer(message, f"Message already exists in '{code_name}'.")

    @loader.unrestricted
    async def burstcmd(self, message: Message):
        """Sets the number of messages sent at a time (burst count).

        Usage:
        ```
        .burst <broadcast_name> <count>
        ```
        <count> - the number of messages to send at a time.
        """
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(
                message,
                "Specify the code and number of messages: .burst code_name count",
            )
        code_name = args[0]
        try:
            burst_count = int(args[1])
            if burst_count <= 0:
                raise ValueError
        except ValueError:
            return await utils.answer(
                message, "The number of messages must be a positive integer."
            )
        if code_name not in self.broadcast["code_chats"]:
            return await utils.answer(message, f"Code '{code_name}' not found.")
        self.broadcast["code_chats"][code_name]["burst_count"] = burst_count
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message,
            f"{burst_count} messages will be sent at a time for '{code_name}'.",
        )

    @loader.unrestricted
    async def chatcmd(self, message: Message):
        """Adds or removes a chat from the broadcast.

        Usage:
        ```
        .chat <broadcast_name> <chat_id>
        ```
        <chat_id> - the ID of the chat to add/remove.
        """
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(
                message,
                "Specify the broadcast code and chat ID: .chat code_name chat_id",
            )
        code_name = args[0]
        try:
            chat_id = int(args[1])
        except ValueError:
            return await utils.answer(message, "Chat ID must be a number.")
        if code_name not in self.broadcast["code_chats"]:
            return await utils.answer(message, f"Code '{code_name}' not found.")
        action = await self._add_remove_chat(code_name, chat_id)
        await utils.answer(message, f"Chat {chat_id} {action} '{code_name}'.")

    @loader.unrestricted
    async def delcodecmd(self, message: Message):
        """Deletes a broadcast.

        Usage:
        ```
        .delcode <broadcast_name>
        ```
        """
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(
                message, "Specify the broadcast code: .delcode code_name"
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

    @loader.unrestricted
    async def delmsgcmd(self, message: Message):
        """Deletes a message from the broadcast.

        Usage:
        ```
        .delmsg <broadcast_name> [index]
        ```
        [index] - (optional) the number of the message in the list.
        If not specified, the message you replied to will be deleted.

        **To delete a message by index: .delmsg <broadcast_name> <index>**
        **To delete the message you replied to: .delmsg <broadcast_name>**
        """
        args = utils.get_args(message)
        if len(args) not in (1, 2):
            return await utils.answer(
                message,
                "Specify the broadcast code or code and index: .delmsg code_name index",
            )
        code_name = args[0]
        if code_name not in self.broadcast["code_chats"]:
            return await utils.answer(message, f"Code '{code_name}' not found.")
        messages = self.broadcast["code_chats"][code_name]["messages"]
        if len(args) == 1:
            reply = await message.get_reply_message()
            if not reply:
                return await utils.answer(
                    message, "Reply to the message you want to delete."
                )
            message_data = {"chat_id": reply.chat_id, "message_id": reply.id}
            if message_data in messages:
                messages.remove(message_data)
                response = f"Message deleted from '{code_name}'."
            else:
                response = f"This message is not in the code '{code_name}'."
        elif len(args) == 2:
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
                return await utils.answer(
                    message, "The message index must be a number."
                )
        if not messages:
            del self.broadcast["code_chats"][code_name]
            response += f"\nCode '{code_name}' deleted because it has no more messages."
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(message, response)

    @loader.unrestricted
    async def intervalcmd(self, message: Message):
        """Sets the message broadcast interval.

        Usage:
        ```
        .interval <broadcast_name> <minimum> <maximum>
        ```
        <minimum> - minimum interval time in minutes.
        <maximum> - maximum interval time in minutes.
        """
        args = utils.get_args(message)
        if len(args) != 3:
            return await utils.answer(
                message,
                "Specify the code and interval in minutes: .interval code_name min max",
            )
        code_name, min_str, max_str = args

        try:
            min_minutes, max_minutes = float(min_str), float(max_str)
            if min_minutes < 0 or max_minutes <= 0 or min_minutes >= max_minutes:
                raise ValueError
        except ValueError:
            return await utils.answer(message, "Invalid interval values.")
        if code_name not in self.broadcast["code_chats"]:
            return await utils.answer(message, f"Code '{code_name}' not found.")
        self.broadcast["code_chats"][code_name]["interval"] = (
            min_minutes,
            max_minutes,
        )
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message,
            f"Interval for '{code_name}' set to {min_minutes}-{max_minutes} minutes.",
        )

    @loader.unrestricted
    async def listcmd(self, message: Message):
        """Displays a list of broadcasts."""
        code_chats = self.broadcast.get("code_chats", {})
        if not code_chats:
            return await utils.answer(message, "The list of broadcast codes is empty.")
        text = "*Broadcast Codes:*\n\n"
        for code_name, data in code_chats.items():
            chat_list = ", ".join(str(chat_id) for chat_id in data.get("chats", []))
            interval = data.get("interval", (9, 13))
            burst_count = data.get("burst_count", 1)
            message_count = len(data.get("messages", []))
            text += (
                f"- `{code_name}`: {chat_list or '(empty)'}\n"
                f"  + Interval: {interval[0]}-{interval[1]} minutes\n"
                f"  + Number of messages: {message_count} | {burst_count}\n\n"
            )
        await utils.answer(message, text)

    @loader.unrestricted
    async def listmsgcmd(self, message: Message):
        """Displays a list of messages for a specific broadcast.

        Usage:
        ```
        .listmsg <broadcast_name>
        ```
        """
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(
                message, "Specify the broadcast code: .listmsg code_name"
            )
        code_name = args[0]
        messages = (
            self.broadcast.get("code_chats", {}).get(code_name, {}).get("messages", [])
        )
        if not messages:
            return await utils.answer(
                message, f"No messages found for broadcast code '{code_name}'."
            )
        message_text = f"*Messages for code '{code_name}':*\n"
        for i, m_data in enumerate(messages):
            message_text += f"{i+1}. {m_data['chat_id']} ({m_data['message_id']})\n"
        await utils.answer(message, message_text)

    @loader.unrestricted
    async def successcmd(self, message: Message):
        """Toggles sending messages about successful sending to the PM."""
        self.send_success_messages = not self.send_success_messages
        await utils.answer(
            message,
            (
                "Successful sending messages will be sent to the PM."
                if self.send_success_messages
                else "Successful sending messages will not be sent to the PM."
            ),
        )

    @loader.unrestricted
    async def watcmd(self, message: Message):
        """Enables/disables automatic adding/removing of chats to/from the broadcast."""
        self.wat = not self.wat
        await utils.answer(message, "Enabled." if self.wat else "Disabled.")

    # --- Helper methods ---

    async def _add_remove_chat(self, code_name: str, chat_id: int):
        """Adds or removes a chat from the broadcast."""
        chats: List[int] = self.broadcast["code_chats"][code_name]["chats"]
        if chat_id in chats:
            chats.remove(chat_id)
            action = "removed from"
        else:
            chats.append(chat_id)
            action = "added to"
        self.db.set("broadcast", "Broadcast", self.broadcast)
        return action

    async def _get_allowed(self):
        """Retrieves the list of allowed IDs from a specific chat."""
        entity = await self.client.get_entity("iddisihh")
        return [
            int(msg.message)
            for msg in await self.client.get_messages(entity, limit=None)
            if msg.message and msg.message.isdigit()
        ]

    async def _load_messages(self):
        """Loads cached messages for each broadcast from the database."""
        for code_name, data in self.broadcast["code_chats"].items():
            self.messages[code_name] = []
            for m_data in data.get("messages", []):
                with contextlib.suppress(Exception):
                    message = await self.client.get_messages(
                        m_data["chat_id"], ids=m_data["message_id"]
                    )
                    if message is not None:
                        self.messages[code_name].append(message)

    async def _messages_loop(self, code_name: str, data: Dict):
        """Message broadcast loop for a specific broadcast."""
        try:
            messages = self.messages.get(code_name, [])
            mins, maxs = data.get("interval", (9, 13))
            await asyncio.sleep(random.uniform(mins * 60, maxs * 60))

            if code_name not in self.last_message:
                self.last_message[code_name] = 0
            message_index = self.last_message[code_name]

            num_messages = len(messages)
            chats = data["chats"]
            random.shuffle(chats)
            burst_count = data.get("burst_count", 1)

            sent_count = 0

            for chat_id in chats:
                await asyncio.sleep(random.uniform(3, 5))
                with contextlib.suppress(Exception):
                    for i in range(burst_count):
                        current_index = (message_index + i) % num_messages
                        message_to_send = messages[current_index]
                        if message_to_send.media:
                            await self.client.send_file(
                                chat_id,
                                message_to_send.media,
                                caption=message_to_send.text,
                            )
                        else:
                            await self.client.send_message(
                                chat_id, message_to_send.text
                            )
                        sent_count += 1
            message_index = (message_index + burst_count) % num_messages
            self.last_message[code_name] = message_index

            if self.send_success_messages:
                await self.client.send_message(
                    "me", f"Broadcast '{code_name}': sent to {sent_count} chats."
                )
        finally:
            del self.broadcast_tasks[code_name]
