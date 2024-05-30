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
            int(msg.message)
            for msg in await self.client.get_messages(entity, limit=None)
            if msg.message and msg.message.isdigit()
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

        Usage: .setcode <code_name> <prob> (reply to a message)
        """
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        if len(args) != 2 or not reply:
            return await utils.answer(
                message, "Reply to a message with .setcode <code_name> <prob>"
            )
        code_name, prob_str = args
        await self._set_code(message, code_name, prob_str, reply)

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
    async def delmsgcmd(self, message: Message):
        """
        Delete a message from the broadcast code.

        Usage: .delmsg <code_name> (reply to a message)
        """
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        if len(args) != 1 or not reply:
            return await utils.answer(
                message, "Reply to a message with .delmsg <code_name>"
            )
        code_name = args[0]
        await self._delete_message_from_code(message, code_name, reply)

    @loader.unrestricted
    async def setprobcmd(self, message: Message):
        """
        Change the sending prob for the broadcast code.

        Usage: .setprob <code_name> <new_prob>
        """
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(message, "Usage: .setprob <code_name> <prob>")
        code_name, new_prob_str = args
        await self._set_prob(message, code_name, new_prob_str)

    @loader.unrestricted
    async def listcmd(self, message: Message):
        """Show a list of broadcast codes."""
        await self._show_code_list(message)

    @loader.unrestricted
    async def listmsgcmd(self, message: Message):
        """Show a list of messages for a broadcast code.

        Usage: .listmsg <code_name>
        """
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Specify the code.")
        code_name = args[0]
        await self._show_message_list(message, code_name)

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
        self, message: Message, code_name: str, prob_str: str, reply: Message
    ):
        """Create a broadcast code and set a message for it."""
        try:
            prob = float(prob_str)
            if not 0 <= prob <= 1:
                raise ValueError
        except ValueError:
            return await utils.answer(
                message, "prob should be a number between 0 and 1."
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
            "prob": prob,
        }
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(message, f"Code '{code_name}' set with prob {prob}.")

    async def _add_message_to_code(
        self, message: Message, code_name: str, reply: Message
    ):
        """Add a message to the broadcast code."""
        if code_name not in self.broadcast.get("code_chats", {}):
            return await utils.answer(message, f"Code '{code_name}' not found.")
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
        if code_name not in self.broadcast.get("code_chats", {}):
            return await utils.answer(message, f"Code '{code_name}' not found.")
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

    async def _set_prob(self, message: Message, code_name: str, new_prob_str: str):
        """Change the sending prob for the broadcast code."""
        try:
            new_prob = float(new_prob_str)
            if not 0 <= new_prob <= 1:
                raise ValueError
        except ValueError:
            return await utils.answer(
                message, "prob should be a number between 0 and 1."
            )
        if code_name not in self.broadcast.get("code_chats", {}):
            return await utils.answer(message, f"Code '{code_name}' not found.")
        self.broadcast.setdefault("code_chats", {})[code_name]["prob"] = new_prob
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message,
            f"prob for code '{code_name}' changed to {new_prob}.",
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
            text += (
                f"- `{code_name}`: {chat_list or '(empty)'}: {data.get('prob', 0)}\n"
            )
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

    async def _send_message_to_chats(self, code_name: str):
        """Broadcast a message to chats."""
        data = self.broadcast.get("code_chats", {}).get(code_name)
        if not data:
            return
        chat_ids = list(data.get("chats", {}).keys())
        random.shuffle(chat_ids)

        for chat_id in chat_ids:
            if random.random() > data.get("prob", 0):
                continue
            try:
                messages = data.get("messages", [])
                if not messages:
                    continue
                message_data = messages[data["chats"][chat_id]]

                main_message = await self.client.get_messages(
                    message_data.get("chat_id"), ids=message_data.get("message_id")
                )

                if main_message:
                    if main_message.media:
                        await self.client.send_file(
                            int(chat_id), main_message.media, caption=main_message.text
                        )
                    else:
                        await self.client.send_message(int(chat_id), main_message)
                    data["chats"][int(chat_id)] = (data["chats"][chat_id] + 1) % len(
                        messages
                    )
                    self.db.set("broadcast", "Broadcast", self.broadcast)
                await asyncio.sleep(random.uniform(10, 20))
            except ValueError:
                await self.client.send_message("me", f"Invalid chat ID: {chat_id}")
            except Exception as e:
                await self.client.send_message(
                    "me", f"Error sending to chat {chat_id}: {e}"
                )
