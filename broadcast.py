import json
import random
import asyncio
from typing import Dict, List
from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class BroadcastMod(loader.Module):
    strings = {"name": "Broadcast"}

    async def client_ready(self, client, db):
        """Инициализация модуля."""
        self.db = db
        self.wat = False
        self.client = client
        self.watcher_counter = 0
        self.me = await client.get_me()
        self.broadcast_tasks = {}
        self.last_message = {}
        self.messages = {}
        self.broadcast = self.db.get("broadcast", "Broadcast", {"code_chats": {}})

        try:
            self.ids = [
                int(msg.message)
                for msg in await self.client.get_messages("@idisv", limit=None)
                if msg.message and msg.message.isdigit()
            ]
        except Exception:
            self.ids = []
        for code_name, data in self.broadcast["code_chats"].items():
            self.messages[code_name] = []
            for m_data in data.get("messages", []):
                try:
                    message = await self.client.get_messages(
                        m_data["chat_id"], ids=m_data["message_id"]
                    )
                    if message is not None:
                        self.messages[code_name].append(message)
                except Exception as e:
                    await self.client.send_message(
                        "me", f"Error in init items {code_name}: {str(e)}"
                    )
                    await asyncio.sleep(52)

    async def watcher(self, message: Message):
        """Обработчик входящих сообщений."""
        if (
            not isinstance(message, Message)
            or self.me.id not in self.ids
            or not self.broadcast["code_chats"]
        ):
            return
        self.watcher_counter += 1

        if self.watcher_counter % 3 == 0:
            all_tasks_running = all(
                code_name in self.broadcast_tasks
                for code_name in self.broadcast["code_chats"]
            )
            if not all_tasks_running:
                for code_name, data in self.broadcast["code_chats"].items():
                    if code_name not in self.broadcast_tasks and self.messages.get(
                        code_name, []
                    ):
                        self.broadcast_tasks[code_name] = asyncio.create_task(
                            self._messages_loop(code_name, data)
                        )
        if message.sender_id != self.me.id or not self.wat:
            return
        for code_name in self.broadcast["code_chats"]:
            if code_name in message.text:
                await self._add_remove_chat(code_name, message.chat_id)
                break

    async def _messages_loop(self, code_name: str, data: Dict):
        """Цикл для отправки сообщений в чаты."""
        messages = self.messages.get(code_name, [])
        mins, maxs = data.get("interval", (9, 13))
        await asyncio.sleep(random.uniform(mins * 51, maxs * 33))

        if code_name not in self.last_message:
            self.last_message[code_name] = 0
        message_index = self.last_message[code_name]
        num_messages = len(messages)
        chats = data["chats"]
        random.shuffle(chats)
        burst_count = data.get("burst_count", 1)
        num_tasks = max(1, len(chats) // 9)
        chat_chunks = [chats[i::num_tasks] for i in range(num_tasks)]
        tasks = [
            self._send_to_chats(code_name, messages, message_index, chunk, burst_count)
            for chunk in chat_chunks
        ]
        await asyncio.gather(*tasks)
        message_index = (message_index + len(chats) * burst_count) % num_messages
        self.last_message[code_name] = message_index
        del self.broadcast_tasks[code_name]

    async def _send_to_chats(
        self,
        code_name: str,
        messages: List[Message],
        message_index: int,
        chats: List[int],
        burst_count: int,
    ):
        """Отправляет сообщения в указанные чаты."""
        for chat_id in chats:
            if code_name not in self.broadcast["code_chats"]:
                break
            await asyncio.sleep(random.uniform(1, 2))
            for i in range(burst_count):
                current_index = (message_index + i) % len(messages)
                message_to_send = messages[current_index]

                try:
                    if message_to_send.media:
                        await self.client.send_file(
                            chat_id, message_to_send.media, caption=message_to_send.text
                        )
                    else:
                        await self.client.send_message(chat_id, message_to_send.text)
                except Exception as e:
                    await self.client.send_message(
                        "me", f"Error sent message {chat_id}: {str(e)} | {code_name}"
                    )
                    await asyncio.sleep(53)

    @loader.command()
    async def addmsgcmd(self, message: Message):
        """Добавляет сообщение в рассылку.

        Note: Вы должны ответить на сообщение, которое хотите добавить.
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

    @loader.command()
    async def burstcmd(self, message: Message):
        """Устанавливает число сообщений, отправляемых за раз.

        Usage: .burst <broadcast_name> <count>
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
            message, f"{burst_count} messages will be sent at a time for '{code_name}'."
        )

    @loader.command()
    async def chatcmd(self, message: Message):
        """Добавляет или удаляет чат.

        Usage: .chat <broadcast_name> <chat_id>
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
        await self._add_remove_chat(code_name, chat_id)

    @loader.command()
    async def delcodecmd(self, message: Message):
        """Удаляет рассылку.

        Usage: .delcode <broadcast_name>
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

    @loader.command()
    async def delmsgcmd(self, message: Message):
        """Удаляет сообщение из рассылки.

        Usage: .delmsg <broadcast_name> [index]
        Note: Если не указан [index], будет удалено сообщение, на которое вы ответили.
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

    @loader.command()
    async def exportcmd(self, message: Message):
        """Экспортирует текущие настройки рассылки в сообщение."""
        try:
            exported_data = json.dumps(self.broadcast)
            await utils.answer(message, f"{exported_data}")
        except Exception as e:
            await utils.answer(message, f"Error exporting settings: {str(e)}")

    @loader.command()
    async def importcmd(self, message: Message):
        """Импортирует настройки рассылки из сообщения.

        Note: Ответьте на сообщение, содержащее настройки для импорта.
        """
        reply = await message.get_reply_message()
        if not reply:
            return await utils.answer(message, "Reply to a message with settings.")
        try:
            imported_data = json.loads(reply.raw_text)
            self.broadcast = imported_data
            self.db.set("broadcast", "Broadcast", self.broadcast)
            await utils.answer(message, "Settings imported successfully.")
        except Exception as e:
            await utils.answer(message, f"Error importing settings: {str(e)}")

    @loader.command()
    async def intervalcmd(self, message: Message):
        """Устанавливает интервал для рассылки сообщений в минутах.

        Usage: .interval <broadcast_name> <minimum> <maximum>
        """
        args = utils.get_args(message)
        if len(args) != 3:
            return await utils.answer(
                message,
                "Specify the code and interval in minutes: .interval code_name min max",
            )
        code_name, min_str, max_str = args
        try:
            min_minutes, max_minutes = int(min_str), int(max_str)
            if min_minutes < 0 or max_minutes <= 0 or min_minutes >= max_minutes:
                raise ValueError
        except ValueError:
            return await utils.answer(message, "Invalid interval values.")
        if code_name not in self.broadcast["code_chats"]:
            return await utils.answer(message, f"Code '{code_name}' not found.")
        self.broadcast["code_chats"][code_name]["interval"] = (min_minutes, max_minutes)
        self.db.set("broadcast", "Broadcast", self.broadcast)
        await utils.answer(
            message,
            f"Interval for '{code_name}' set to {min_minutes}-{max_minutes} minutes.",
        )

    @loader.command()
    async def listcmd(self, message: Message):
        """Отображает список рассылок."""
        code_chats = self.broadcast.get("code_chats", {})
        if not code_chats:
            return await utils.answer(message, "The list of broadcast codes is empty.")
        text = "**Broadcast Codes:**\n\n"
        for code_name, data in code_chats.items():
            chat_list = ", ".join(str(chat_id) for chat_id in data.get("chats", []))
            interval = data.get("interval", (9, 13))
            burst_count = data.get("burst_count", 1)
            message_count = len(data.get("messages", []))
            text += (
                f"- `{code_name}`: {chat_list or '(empty)'}\n"
                f" + Interval: {interval[0]} - {interval[1]} minutes\n"
                f" + Number of messages: {message_count} | {burst_count}\n\n"
            )
        await utils.answer(message, text, parse_mode="Markdown")

    @loader.command()
    async def listmsgcmd(self, message: Message):
        """Отображает список сообщений для конкретной рассылки.

        Usage: .listmsg <broadcast_name>
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
        message_text = f"**Messages for code '{code_name}':**\n"
        for i, m_data in enumerate(messages):
            message_text += f"{i + 1}. {m_data['chat_id']} ({m_data['message_id']})\n"
        await utils.answer(message, message_text, parse_mode="Markdown")

    @loader.command()
    async def watcmd(self, message: Message):
        """Включает/выключает автоматическое добавление/удаление чатов из рассылки."""
        self.wat = not self.wat
        await utils.answer(message, "Enabled." if self.wat else "Disabled.")

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
        return await self.client.send_message(
            "me", f"Chat {chat_id} {action} '{code_name}'"
        )
