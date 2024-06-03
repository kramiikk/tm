import asyncio
import random
from typing import Dict, List
from contextlib import suppress
from itertools import cycle

from telethon.tl.types import Message

from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    """Module for broadcasting messages to chats."""

    strings = {"name": "Broadcast"}

    def __init__(self):
        super().__init__()
        self.allowed_ids: List[int] = []
        self.broadcast: Dict = {}

    async def client_ready(self, client, db):
        """Module initialization when the client starts."""
        self.db = db
        self.client = client
        self.me = await client.get_me()

        self.broadcast = self.db.get(
            "broadcast",
            "Broadcast",
            {"code_chats": {}},
        )

        entity = await self.client.get_entity("iddisihh")
        self.allowed_ids = [
            int(msg.message)
            for msg in await self.client.get_messages(entity, limit=None)
            if msg.message and msg.message.isdigit()
        ]

        asyncio.create_task(self.broadcast_loop())

    @loader.unrestricted
    async def chatcmd(self, message: Message):
        """
        Add/remove a chat from the broadcast list.

        .chat <code_name>
        """
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Specify the code.")
        code_name = args[0]
        await self._update_chat_in_broadcast(code_name, message.chat_id)

    @loader.unrestricted
    async def delcodecmd(self, message: Message):
        """
        Delete a broadcast code.

        .delcode <code_name>
        """
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Specify the code.")
        code_name = args[0]
        await self._delete_code(message, code_name)

    @loader.unrestricted
    async def setcodecmd(self, message: Message):
        """
        Create a broadcast code and set a message for it.

        .setcode <code_name> (reply to a message)
        """
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        if len(args) != 1 or not reply:
            return await utils.answer(
                message,
                "Reply to a message with .setcode <code_name>",
            )
        code_name = args[0]
        await self._set_code(message, code_name, reply)

    @loader.unrestricted
    async def addmsgcmd(self, message: Message):
        """
        Add a message to the broadcast code.

        .addmsg <code_name> (reply to a message)
        """
        await self._message_handler(message, utils.get_args(message))

    @loader.unrestricted
    async def delmsgcmd(self, message: Message):
        """
        Delete a message from the broadcast code.

        .delmsg <code_name> (reply to a message)
        """
        await self._message_handler(message, utils.get_args(message))

    @loader.unrestricted
    async def listcmd(self, message: Message):
        """Show a list of broadcast codes."""
        await self._show_code_list(message)

    @loader.unrestricted
    async def listmsgcmd(self, message: Message):
        """
        Show a list of messages for a broadcast code.

        .listmsg <code_name>
        """
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Specify the code.")
        code_name = args[0]
        await self._show_message_list(message, code_name)

    @loader.unrestricted
    async def watcher(self, message: Message):
        """Message processing and broadcast launch."""
        if self.me.id not in self.allowed_ids:
            return
        if (
            isinstance(message, Message)
            and message.sender_id == self.me.id
            and not message.text.startswith(".")
        ):
            await self._process_message(message)

    async def broadcast_loop(self):
        """Main broadcast loop."""
        while True:
            for code_name in self.broadcast.get("code_chats", {}).copy():
                await self._send_messages_for_code(code_name)
            await asyncio.sleep(random.uniform(60, 180))

    async def _send_messages_for_code(self, code_name: str):
        """Send messages for a specific code concurrently."""
        data = self.broadcast.get("code_chats", {}).get(code_name)
        if not data:
            return
        chat_ids = list(data.get("chats", {}).keys())
        random.shuffle(chat_ids)

        async def send_message(chat_id):
            """Sends a message without flood control."""
            await self._send_message_to_chat(code_name, chat_id, data)

        tasks = [send_message(chat_id) for chat_id in chat_ids]
        await asyncio.gather(*tasks)

    async def _send_message_to_chat(self, code_name: str, chat_id: int, data: Dict):
        """Send a message to a specific chat."""
        messages = cycle(data.get("messages", []))
        message_data = next(messages)

        with suppress(Exception):
            main_message = await self.client.get_messages(
                message_data.get("chat_id"), ids=message_data.get("message_id")
            )
            if main_message:
                with suppress(Exception):
                    if main_message.media:
                        await self.client.send_file(
                            chat_id, main_message.media, caption=main_message.text
                        )
                    else:
                        await self.client.send_message(chat_id, main_message.text)
            await asyncio.sleep(random.uniform(3, 5))

    async def _message_handler(self, message: Message, args: List[str]):
        """Handles commands related to messages in a broadcast code (addmsg, delmsg)."""
        reply = await message.get_reply_message()
        if len(args) != 1 or not reply:
            return await utils.answer(
                message, "Reply to a message with .<command> <code_name>"
            )
        code_name = args[0]
        if code_name not in self.broadcast.get("code_chats", {}):
            return await utils.answer(message, f"Code '{code_name}' not found.")
        if args[0] == "addmsg":
            await self._add_message_to_code(message, code_name, reply)
        elif args[0] == "delmsg":
            await self._delete_message_from_code(message, code_name, reply)

    async def _update_chat_in_broadcast(self, code_name: str, chat_id: int):
        """Add/remove a chat from the broadcast list by code name."""
        chats = (
            self.broadcast.setdefault("code_chats", {})
            .setdefault(code_name, {})
            .get("chats", {})
        )
        if chat_id in chats:
            del chats[chat_id]
            action = "removed"
        else:
            chats[chat_id] = 0
            action = "added"
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await self.client.send_message(
            "me", f"Chat {chat_id} {action} for '{code_name}'."
        )

    async def _delete_code(self, message: Message, code_name: str):
        """Delete a broadcast code."""
        if code_name in self.broadcast.get("code_chats", {}):
            del self.broadcast["code_chats"][code_name]
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(message, f"Code '{code_name}' deleted.")
        else:
            await utils.answer(message, f"Code '{code_name}' not found.")

    async def _set_code(
        self,
        message: Message,
        code_name: str,
        reply: Message,
    ):
        """Create a broadcast code and set a message for it."""
        if code_name in self.broadcast.get("code_chats", {}):
            return await utils.answer(message, f"Code '{code_name}' already exists.")
        self.broadcast.setdefault("code_chats", {})[code_name] = {
            "chats": {},
            "messages": [
                {
                    "chat_id": reply.chat_id,
                    "message_id": reply.id,
                }
            ],
        }
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(message, f"Code '{code_name}' set.")

    async def _add_message_to_code(
        self, message: Message, code_name: str, reply: Message
    ):
        """Add a message to the broadcast code."""
        messages = (
            self.broadcast.setdefault("code_chats", {})
            .setdefault(code_name, {})
            .get("messages", [])
        )
        message_data = {
            "chat_id": reply.chat_id,
            "message_id": reply.id,
        }
        if message_data not in messages:
            messages.append(message_data)
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(message, f"Message added to code '{code_name}'.")
        else:
            await utils.answer(
                message, f"This message is already in the code '{code_name}'."
            )

    async def _delete_message_from_code(
        self, message: Message, code_name: str, reply: Message
    ):
        """Delete a message from the broadcast code."""
        messages = (
            self.broadcast.setdefault("code_chats", {})
            .setdefault(code_name, {})
            .get("messages", [])
        )
        message_data = {
            "chat_id": reply.chat_id,
            "message_id": reply.id,
        }
        if message_data in messages:
            messages.remove(message_data)
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(message, f"Message deleted from code '{code_name}'.")
        else:
            await utils.answer(
                message, f"This message is not in the code '{code_name}'."
            )

    async def _show_code_list(self, message: Message):
        """Show a list of broadcast codes."""
        if not self.broadcast.get("code_chats", {}):
            return await utils.answer(message, "The code list is empty.")
        text = "**Broadcast Codes:**\n"
        for code_name, data in self.broadcast["code_chats"].items():
            chat_list = ", ".join(
                str(chat_id) for chat_id in data.get("chats", {}).keys()
            )
            text += f"- `{code_name}`: {chat_list or '(empty)'}\n"
        await utils.answer(message, text)

    async def _show_message_list(self, message: Message, code_name: str):
        """Show a list of messages for a broadcast code."""
        if code_name not in self.broadcast.get("code_chats", {}):
            return await utils.answer(message, f"Code '{code_name}' not found.")
        messages = self.broadcast["code_chats"][code_name].get("messages", [])
        if not messages:
            return await utils.answer(
                message, f"There are no messages for code '{code_name}'."
            )
        message_text = f"**Messages for code '{code_name}':**\n"
        for i, m_data in enumerate(messages):
            message_text += f"{i+1}. {m_data['chat_id']}({m_data['message_id']})\n"
        await utils.answer(message, message_text)

    async def _process_message(self, message: Message):
        """Message processing for adding/removing chats from broadcasts."""
        for code_name in self.broadcast.get("code_chats", {}):
            if code_name in message.text:
                await self._update_chat_in_broadcast(code_name, message.chat_id)
