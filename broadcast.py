import asyncio
import random
from typing import Dict, List

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

        self.broadcast = self.db.get("broadcast", "Broadcast", {"code_chats": {}})
        entity = await self.client.get_entity("iddisihh")
        self.allowed_ids = [
            int(message.message)
            async for message in self.client.iter_messages(entity)
            if message.message and message.message.isdigit()
        ]

    @loader.unrestricted
    async def chatcmd(self, message: Message):
        """
        Add/remove a chat from the broadcast list.

        Usage: .chat <code_name> <chat_id>
        """
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(message, "Specify the code and chat ID.")
        code_name, chat_id_str = args
        try:
            chat_id = int(chat_id_str)
        except ValueError:
            return await utils.answer(message, "Invalid chat ID.")
        if code_name not in self.broadcast.get("code_chats", {}):
            return await utils.answer(message, f"Code '{code_name}' not found.")
        await self._update_chat_in_broadcast(code_name, chat_id)

    @loader.unrestricted
    async def delcodecmd(self, message: Message):
        """
        Delete a broadcast code.

        Usage: .delcode <code_name>
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

        Usage: .setcode <code_name> <probability> (reply to a message)
        """
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        if len(args) != 2 or not reply:
            return await utils.answer(
                message, "Reply to a message with .setcode <code_name> <probability>"
            )
        code_name, probability_str = args
        await self._set_code(message, code_name, probability_str, reply)

    @loader.unrestricted
    async def addmsgcmd(self, message: Message):
        """
        Add a message to the broadcast code.

        Usage: .addmsg <code_name> (reply to a message)
        """
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        if len(args) != 1 or not reply:
            return await utils.answer(
                message, "Reply to a message with .addmsg <code_name>"
            )
        code_name = args[0]
        await self._add_message_to_code(message, code_name, reply)

    @loader.unrestricted
    async def setprobcmd(self, message: Message):
        """
        Change the sending probability for the broadcast code.

        Usage: .setprob <code_name> <new_probability>
        """
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(
                message, "Usage: .setprob <code_name> <new_probability>"
            )
        code_name, new_probability_str = args
        await self._set_probability(message, code_name, new_probability_str)

    @loader.unrestricted
    async def listcmd(self, message: Message):
        """Show a list of broadcast codes."""
        await self._show_code_list(message)

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
        if random.random() < 0.03:
            await self.broadcast_to_chats()

    async def broadcast_to_chats(self):
        """Broadcast messages to chats."""
        for code_name in self.broadcast.get("code_chats", {}):
            await self._send_message_to_chats(code_name)

    async def _update_chat_in_broadcast(self, code_name: str, chat_id: int):
        """Add/remove a chat from the broadcast list by code name."""
        chats = (
            self.broadcast.setdefault("code_chats", {})
            .setdefault(code_name, {})
            .setdefault("chats", {})
        )
        if chats.pop(chat_id, None):
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
        self, message: Message, code_name: str, probability_str: str, reply: Message
    ):
        """Create a broadcast code and set a message for it."""
        try:
            probability = float(probability_str)
            if not 0 <= probability <= 1:
                raise ValueError
        except ValueError:
            return await utils.answer(
                message, "Probability should be a number between 0 and 1."
            )
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
            "probability": probability,
        }
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message, f"Code '{code_name}' set with probability {probability}."
        )

    async def _add_message_to_code(
        self, message: Message, code_name: str, reply: Message
    ):
        """Add a message to the broadcast code."""
        if code_name not in self.broadcast.get("code_chats", {}):
            return await utils.answer(message, f"Code '{code_name}' not found.")
        self.broadcast.setdefault("code_chats", {}).setdefault(
            code_name, {}
        ).setdefault("messages", []).append(
            {
                "chat_id": reply.chat_id,
                "message_id": reply.id,
            }
        )
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(message, f"Message added to code '{code_name}'.")

    async def _set_probability(
        self, message: Message, code_name: str, new_probability_str: str
    ):
        """Change the sending probability for the broadcast code."""
        try:
            new_probability = float(new_probability_str)
            if not 0 <= new_probability <= 1:
                raise ValueError
        except ValueError:
            return await utils.answer(
                message, "Probability should be a number between 0 and 1."
            )
        if code_name not in self.broadcast.get("code_chats", {}):
            return await utils.answer(message, f"Code '{code_name}' not found.")
        self.broadcast.setdefault("code_chats", {})[code_name][
            "probability"
        ] = new_probability
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message,
            f"Probability for code '{code_name}' changed to {new_probability}.",
        )

    async def _show_code_list(self, message: Message):
        """Show a list of broadcast codes."""
        if not self.broadcast.get("code_chats", {}):
            return await utils.answer(message, "The code list is empty.")
        message_text = "**Broadcast Codes:**\n"
        for code_name, data in self.broadcast["code_chats"].items():
            chat_list = ", ".join(
                str(chat_id) for chat_id in data.get("chats", {}).keys()
            )
            message_text += f"- `{code_name}`: {chat_list or '(empty)'}: {data.get('probability', 0)}\n"
        await utils.answer(message, message_text)

    async def _process_message(self, message: Message):
        """Message processing for adding/removing chats from broadcasts."""
        code_data_dict = self.broadcast.get("code_chats", {})
        for code_name in code_data_dict:
            if code_name in message.text:
                chat_id = message.chat_id
                await self._update_chat_in_broadcast(code_name, chat_id)

    async def _send_message_to_chats(self, code_name: str):
        """Broadcast a message to chats."""
        data = self.broadcast.get("code_chats", {}).get(code_name)
        if not data:
            return
        chats_copy = data.get("chats", {}).copy()

        for chat_id, message_index in chats_copy.items():
            if random.random() > data.get("probability", 0):
                continue
            try:
                messages = data.get("messages", [{}])  # Get the list of messages
                message_data = messages[message_index]
                main_message = await self.client.get_messages(
                    message_data.get("chat_id"), ids=message_data.get("message_id")
                )

                if main_message and main_message.media:
                    await self.client.send_file(
                        chat_id, main_message.media, caption=main_message.text
                    )
                elif main_message:
                    await self.client.send_message(chat_id, main_message)
                data["chats"][chat_id] = (message_index + 1) % len(messages)
                self.db.set("broadcast", "Broadcast", self.broadcast)
                await asyncio.sleep(random.uniform(5, 10))
            except Exception as e:
                await self.client.send_message(
                    "me", f"Error sending to chat {chat_id}: {e}"
                )
