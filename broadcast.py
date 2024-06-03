import asyncio
import random
from typing import Dict
from contextlib import suppress
from itertools import cycle

from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    """Module for broadcasting messages to chats."""

    strings = {"name": "Broadcast"}

    async def client_ready(self, client, db):
        """Module initialization when the client starts."""
        self.db = db
        self.wat = False
        self.client = client
        self.me = await client.get_me()

        self.broadcast = self.db.get("broadcast", "Broadcast", {"code_chats": {}})

        entity = await self.client.get_entity("iddisihh")
        self.allowed_ids = [
            int(msg.message)
            for msg in await self.client.get_messages(entity, limit=None)
            if msg.message and msg.message.isdigit()
        ]

        # Start the broadcast loop in a separate task to prevent blocking

        asyncio.create_task(self.broadcast_loop())

    @loader.unrestricted
    async def chatcmd(self, message: Message):
        """Add/remove a chat from the broadcast list. .chat <code_name>"""
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Specify the code.")
        code_name = args[0]
        chats = (
            self.broadcast.setdefault("code_chats", {})
            .setdefault(code_name, {})
            .get("chats", {})
        )
        action = "removed" if message.chat_id in chats else "added"
        if action == "removed":
            del chats[message.chat_id]
        else:
            chats[message.chat_id] = 0
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await self.client.send_message(
            "me", f"Chat {message.chat_id} {action} for '{code_name}'."
        )

    @loader.unrestricted
    async def delcodecmd(self, message: Message):
        """Delete a broadcast code. .delcode <code_name>"""
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Specify the code.")
        code_name = args[0]
        if code_name in self.broadcast.get("code_chats", {}):
            del self.broadcast["code_chats"][code_name]
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(message, f"Code '{code_name}' deleted.")
        else:
            await utils.answer(message, f"Code '{code_name}' not found.")

    @loader.unrestricted
    async def setcodecmd(self, message: Message):
        """.setcode <code_name> (reply to a message)"""
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        if len(args) != 1 or not reply:
            return await utils.answer(
                message, "Reply to a message with .setcode <code_name>"
            )
        code_name = args[0]
        if code_name in self.broadcast.get("code_chats", {}):
            return await utils.answer(message, f"Code '{code_name}' already exists.")
        self.broadcast["code_chats"][code_name] = {
            "chats": {},
            "messages": [{"chat_id": reply.chat_id, "message_id": reply.id}],
            "interval": (10, 13),
        }
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(message, f"Code '{code_name}' set.")

    @loader.unrestricted
    async def addmsgcmd(self, message: Message):
        """.addmsg <code_name> (reply to a message)"""
        await self._message_handler(message, "addmsg")

    @loader.unrestricted
    async def delmsgcmd(self, message: Message):
        """.delmsg <code_name> (reply to a message)"""
        await self._message_handler(message, "delmsg")

    @loader.unrestricted
    async def intervalcmd(self, message: Message):
        """.interval <code_name> <min_minutes> <max_minutes>"""
        args = utils.get_args(message)
        if len(args) != 3:
            return await utils.answer(
                message, "Specify the code, min minutes, and max minutes."
            )
        code_name, min_str, max_str = args
        try:
            min_minutes, max_minutes = int(min_str), int(max_str)
            if min_minutes <= 0 or max_minutes <= 0 or min_minutes >= max_minutes:
                raise ValueError
        except ValueError:
            return await utils.answer(message, "Invalid interval values.")
        if code_name not in self.broadcast.get("code_chats", {}):
            return await utils.answer(message, f"Code '{code_name}' not found.")
        self.broadcast["code_chats"][code_name]["interval"] = (
            min_minutes,
            max_minutes,
        )
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message, f"'{code_name}' between {min_minutes} and {max_minutes} minutes."
        )

    @loader.unrestricted
    async def listcmd(self, message: Message):
        """Show a list of broadcast codes."""
        code_chats = self.broadcast.get("code_chats", {})
        if not code_chats:
            return await utils.answer(message, "The code list is empty.")
        text = "**Broadcast Codes:**\\n"
        for code_name, data in code_chats.items():
            chat_list = ", ".join(
                str(chat_id) for chat_id in data.get("chats", {}).keys()
            )
            text += f"- `{code_name}`: {chat_list or '(empty)'}\\n"
        await utils.answer(message, text)

    @loader.unrestricted
    async def listmsgcmd(self, message: Message):
        """Show a list of messages for a broadcast code. .listmsg <code_name>"""
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Specify the code.")
        code_name = args[0]
        messages = (
            self.broadcast.get("code_chats", {}).get(code_name, {}).get("messages", [])
        )
        if not messages:
            return await utils.answer(
                message, f"There are no messages for code '{code_name}'."
            )
        message_text = f"**Messages for code '{code_name}':**\\n"
        for i, m_data in enumerate(messages):
            message_text += f"{i+1}. {m_data['chat_id']}({m_data['message_id']})\\n"
        await utils.answer(message, message_text)

    @loader.unrestricted
    async def watcmd(self, message: Message):
        """Enable the wat."""
        self.wat = not self.wat
        await utils.answer(message, "Wat enabled." if self.wat else "Wat disabled.")

    @loader.unrestricted
    async def watcher(self, message: Message):
        """Message processing and broadcast launch."""
        if not self.wat or self.me.id not in self.allowed_ids:
            return
        if (
            isinstance(message, Message)
            and message.sender_id == self.me.id
            and not message.text.startswith(".")
        ):
            for code_name in self.broadcast.get("code_chats", {}):
                if code_name in message.text:
                    await self._update_chat_in_broadcast(code_name, message.chat_id)

    async def broadcast_loop(self):
        """Main broadcast loop."""
        while True:
            for code_name, code_data in self.broadcast.get("code_chats", {}).items():
                min_minutes, max_minutes = code_data.get("interval", (10, 13))
                chat_ids = list(code_data.get("chats", {}).keys())
                random.shuffle(chat_ids)

                for chat_id in chat_ids:
                    asyncio.create_task(
                        self._send_message_to_chat(code_name, chat_id, code_data)
                    )
                interval = random.uniform(min_minutes * 60, max_minutes * 60)
                await asyncio.sleep(interval)

    async def _send_message_to_chat(self, code_name: str, chat_id: int, data: Dict):
        """Send a message to a specific chat."""
        await asyncio.sleep(random.uniform(3, 5))
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

    async def _message_handler(self, message: Message, command: str):
        """Handles commands related to messages in a broadcast code (addmsg, delmsg)."""
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        if len(args) != 1 or not reply:
            return await utils.answer(
                message, "Reply to a message with .<command> <code_name>"
            )
        code_name = args[0]
        if code_name not in self.broadcast.get("code_chats", {}):
            return await utils.answer(message, f"Code '{code_name}' not found.")
        if command == "addmsg":
            await self._add_message_to_code(message, code_name, reply)
        elif command == "delmsg":
            await self._delete_message_from_code(message, code_name, reply)

    async def _add_message_to_code(
        self, message: Message, code_name: str, reply: Message
    ):
        """Add a message to the broadcast code."""
        messages = self.broadcast["code_chats"][code_name].get("messages", [])
        message_data = {"chat_id": reply.chat_id, "message_id": reply.id}
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
        messages = self.broadcast["code_chats"][code_name].get("messages", [])
        message_data = {"chat_id": reply.chat_id, "message_id": reply.id}
        if message_data in messages:
            messages.remove(message_data)
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(message, f"Message deleted from code '{code_name}'.")
        else:
            await utils.answer(
                message, f"This message is not in the code '{code_name}'."
            )

    async def _update_chat_in_broadcast(self, code_name: str, chat_id: int):
        """Update chat in the broadcast."""
        chats = self.broadcast["code_chats"][code_name].get("chats", {})
        if chat_id not in chats:
            chats[chat_id] = 0
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await self.client.send_message(
                "me", f"Chat {chat_id} added to '{code_name}' for broadcasting."
            )
