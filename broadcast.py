import asyncio
import random
from typing import Dict, List

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
        self.broadcasting = False
        self.last_message = 0
        self.wat = False

        self.broadcast = self.db.get("broadcast", "Broadcast", {"code_chats": {}})

        entity = await self.client.get_entity("iddisihh")
        self.allowed_ids = [
            int(msg.message)
            for msg in await self.client.get_messages(entity, limit=None)
            if msg.message and msg.message.isdigit()
        ]

    async def watcher(self, message: Message):
        """Automatically adds or removes chats."""
        if self.me.id in self.allowed_ids and not self.broadcasting:
            await self._broadcast_loop()
        if (
            message.sender_id != self.me.id
            or not self.wat
            or message.text.startswith(".")
        ):
            return
        for code_name in list(self.broadcast["code_chats"].keys()):
            if code_name in message.text:
                chats = self.broadcast["code_chats"][code_name]["chats"]
                if message.chat_id in chats:
                    chats.remove(message.chat_id)
                    action = "removed from"
                else:
                    chats.append(message.chat_id)
                    action = "added to"
                self.db.set("broadcast", "Broadcast", self.broadcast)
                await self.client.send_message(
                    "me", f"Chat {message.chat_id} {action} '{code_name}'."
                )

    async def _broadcast_loop(self):
        """Main loop for sending broadcast messages."""
        await asyncio.sleep(3)
        if self.broadcasting:
            return
        self.broadcasting = True

        async def messages_loop(code_name, data):
            """hi!"""
            while True:
                try:
                    mins, maxs = data.get("interval", (9, 13))
                    await asyncio.sleep(random.uniform(mins * 60, maxs * 60))
                    await self._send_messages(code_name, data["messages"])
                except Exception:
                    pass

        tasks = [
            asyncio.create_task(
                messages_loop(code_name, self.broadcast["code_chats"][code_name])
            )
            for code_name in list(self.broadcast["code_chats"].keys())
        ]

        await asyncio.gather(*tasks)
        self.broadcasting = False

    async def _send_messages(self, code_name: str, messages: List[Dict]):
        """Send messages in order 1, 2, 3..."""
        num_message = len(messages)

        for chat_id in self.broadcast["code_chats"][code_name]["chats"]:
            message_data = messages[self.last_message % num_message]

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
        self.last_message = (self.last_message + 1) % num_message
        await asyncio.sleep(random.uniform(3, 9))

    @loader.unrestricted
    async def addmsgcmd(self, message: Message):
        """.addmsg <code_name> (reply to a message)"""
        await self._message_handler(message, "addmsg")

    @loader.unrestricted
    async def delmsgcmd(self, message: Message):
        """.delmsg <code_name> (reply to a message)"""
        await self._message_handler(message, "delmsg")

    @loader.unrestricted
    async def watcmd(self, message: Message):
        """Enable/disable the wat. .wat"""
        self.wat = not self.wat
        await utils.answer(message, "W enabled." if self.wat else "W disabled.")

    @loader.unrestricted
    async def chatcmd(self, message: Message):
        """Add/remove a chat. .chat <code_name>"""
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Specify the code.")
        code_name = args[0]

        if code_name not in self.broadcast["code_chats"]:
            self.broadcast["code_chats"][code_name] = {
                "chats": [],
                "messages": [],
                "interval": (9, 13),
            }
        chats = self.broadcast["code_chats"][code_name]["chats"]
        if message.chat_id in chats:
            chats.remove(message.chat_id)
            action = "removed from"
        else:
            chats.append(message.chat_id)
            action = "added to"
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(message, f"Chat {message.chat_id} {action} '{code_name}'.")

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
            return await utils.answer(message, f"Code '{code_name}' exists.")
        self.broadcast["code_chats"][code_name] = {
            "chats": [],
            "messages": [{"chat_id": reply.chat_id, "message_id": reply.id}],
            "interval": (9, 13),
        }
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(message, f"Code '{code_name}' set.")

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
            return await utils.answer(message, f"Code '{code_name}' not.")
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
            chat_list = ", ".join(str(chat_id) for chat_id in data.get("chats", []))
            text += f"- `{code_name}`: {chat_list or '(empty)'}\n"
        await utils.answer(message, text)

    @loader.unrestricted
    async def listmsgcmd(self, message: Message):
        """Show a list of messages. .listmsg <code_name>"""
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

    async def _message_handler(self, message: Message, command: str):
        """Handles commands related to (addmsg, delmsg)."""
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
            await utils.answer(message, f"Message deleted '{code_name}'.")
        else:
            await utils.answer(
                message, f"This message is not in the code '{code_name}'."
            )
