import asyncio
import random
from typing import Dict, List
from contextlib import suppress

from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    """Module for broadcasting messages to chats."""

    strings = {"name": "Broadcast"}

    async def client_ready(self, client, db):
        """Module initialization when the client starts."""
        self.db = db
        self.client = client
        self.me = await client.get_me()
        self.wat = False
        self.broadcasting = False

        self.broadcast = self.db.get("broadcast", "Broadcast", {"code_chats": {}})

        entity = await self.client.get_entity("iddisihh")
        self.allowed_ids = [
            int(msg.message)
            for msg in await self.client.get_messages(entity, limit=None)
            if msg.message and msg.message.isdigit()
        ]

    @loader.unrestricted
    async def chatcmd(self, message: Message):
        """Add/remove a chat from the broadcast list using .chat <code_name>"""
        if not self.wat:
            args = utils.get_args(message)
            if len(args) != 1:
                return await utils.answer(message, "Specify the code.")
            code_name = args[0]

            if code_name not in self.broadcast["code_chats"]:
                self.broadcast["code_chats"][code_name] = {
                    "chats": {},
                    "messages": [],
                    "interval": (10, 13),
                }
            chats = self.broadcast["code_chats"][code_name]["chats"]
            action = "removed" if message.chat_id in chats else "added"
            if action == "removed":
                del chats[message.chat_id]
            else:
                chats[message.chat_id] = 0
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(
                message, f"Chat {message.chat_id} {action} for '{code_name}'."
            )
        else:
            await utils.answer(message, "Watcher mode is enabled.")

    @loader.unrestricted
    async def delcodecmd(self, message: Message):
        """Delete a broadcast code. .delcode <code_name>"""
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Specify the code.")
        code_name = args[0]
        if code_name in self.broadcast["code_chats"]:
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
        if code_name in self.broadcast["code_chats"]:
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
        if code_name not in self.broadcast["code_chats"]:
            return await utils.answer(message, f"Code '{code_name}' not found.")
        self.broadcast["code_chats"][code_name]["interval"] = (
            min_minutes,
            max_minutes,
        )
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message,
            f"'{code_name}' set to {min_minutes} and {max_minutes} minutes.",
        )

    @loader.unrestricted
    async def listcmd(self, message: Message):
        """Show a list of broadcast codes."""
        code_chats = self.broadcast.get("code_chats", {})
        if not code_chats:
            return await utils.answer(message, "The code list is empty.")
        text = "**Broadcast Codes:**\n"
        for code_name, data in code_chats.items():
            chat_list = ", ".join(
                str(chat_id) for chat_id in data.get("chats", {}).keys()
            )
            text += f"- `{code_name}`: {chat_list or '(empty)'}\n"
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
        message_text = f"**Messages for code '{code_name}':**\n"
        for i, m_data in enumerate(messages):
            message_text += f"{i+1}. {m_data['chat_id']}({m_data['message_id']})\n"
        await utils.answer(message, message_text)

    @loader.unrestricted
    async def startbroadcastingcmd(self, message: Message):
        """Start broadcasting messages. .startbroadcasting"""
        if not self.broadcasting and self.me.id in self.allowed_ids:
            self.broadcasting = True
            asyncio.create_task(self._broadcast_loop())
            await utils.answer(message, "Broadcasting started.")
        else:
            await utils.answer(message, "Broadcasting is already running.")

    @loader.unrestricted
    async def stopbroadcastingcmd(self, message: Message):
        """Stop broadcasting messages. .stopbroadcasting"""
        if self.broadcasting:
            self.broadcasting = False
            await utils.answer(message, "Broadcasting stopped.")
        else:
            await utils.answer(message, "Broadcasting is not running.")

    async def _broadcast_loop(self):
        """Main loop for sending broadcast messages."""
        while self.broadcasting:
            for code_name, data in self.broadcast["code_chats"].items():
                min_minutes, max_minutes = data.get("interval", (10, 13))
                await self._send_messages_for_code(code_name, data["messages"])
                interval = random.uniform(min_minutes * 60, max_minutes * 60)
                await asyncio.sleep(interval)

    async def _send_messages_for_code(self, code_name: str, messages: List[Dict]):
        """Send."""
        for chat_id in self.broadcast["code_chats"][code_name]["chats"]:
            with suppress(Exception):
                message_data = random.choice(messages)
                main_message = await self.client.get_messages(
                    message_data["chat_id"], ids=message_data["message_id"]
                )

                if main_message is None:
                    continue
                if main_message.media:
                    await self.client.send_file(
                        chat_id, main_message.media, caption=main_message.text
                    )
                else:
                    await self.client.send_message(chat_id, main_message.text)
                await asyncio.sleep(random.uniform(3, 9))

    async def _message_handler(self, message: Message, command: str):
        """Handles commands related to messages in a broadcast code (addmsg, delmsg)."""
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        if len(args) != 1 or not reply:
            return await utils.answer(
                message, "Reply to a message with .<command> <code_name>"
            )
        code_name = args[0]
        if code_name not in self.broadcast["code_chats"]:
            return await utils.answer(message, f"Code '{code_name}' not found.")
        if command == "addmsg":
            await self._add_message_to_code(message, code_name, reply)
        elif command == "delmsg":
            await self._delete_message_from_code(message, code_name, reply)

    async def _add_message_to_code(
        self, message: Message, code_name: str, reply: Message
    ):
        """Add a message to the broadcast code."""
        messages = self.broadcast["code_chats"][code_name]["messages"]
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
        messages = self.broadcast["code_chats"][code_name]["messages"]
        message_data = {"chat_id": reply.chat_id, "message_id": reply.id}
        if message_data in messages:
            messages.remove(message_data)
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(message, f"Message deleted from code '{code_name}'.")
        else:
            await utils.answer(
                message, f"This message is not in the code '{code_name}'."
            )

    @loader.unrestricted
    async def watcmd(self, message: Message):
        """Enable/disable the watcher. .wat"""
        self.wat = not self.wat
        await utils.answer(
            message, "Watcher enabled." if self.wat else "Watcher disabled."
        )

    async def watcher(self, message: Message):
        """Automatically adds or removes chats."""
        if not self.wat or message.text.startswith("."):
            return
        for code_name in self.broadcast["code_chats"]:
            if code_name in message.text:
                if message.chat_id in self.broadcast["code_chats"][code_name]["chats"]:
                    del self.broadcast["code_chats"][code_name]["chats"][
                        message.chat_id
                    ]
                    action = "removed from"
                else:
                    self.broadcast["code_chats"][code_name]["chats"][
                        message.chat_id
                    ] = 0
                    action = "added to"
                self.db.set("broadcast", "Broadcast", self.broadcast)
                await self.client.send_message(
                    "me", f"Chat {message.chat_id} {action} '{code_name}'."
                )
