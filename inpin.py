from telethon import TelegramClient, types
from telethon.errors import ChatAdminRequiredError
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest

import time
from typing import Union, Dict, Any

from .. import loader, utils

@loader.tds
class InlinePingMod(loader.Module):
    """Compact inline pinger with chat stats"""

    strings = {
        "name": "InlinePing",
        "ping_text": "🏓 <b>Ping:</b> {ping:.2f} ms",
        "stats_text": "📊 <b>{title}:</b>\n"
                      "ID: <code>{chat_id}</code>\n"
                      "Type: {chat_type}\n"
                      "Created: {created_at}\n"
                      "Members: {members}\n"
                      "Online: ~{online_count}\n"
                      "Bots: {bots}\n"
                      "Admins: {admins}\n"
                      "Messages: {total_messages}\n",
        "error_text": "❌ <b>Error:</b> {error}",
    }

    async def client_ready(self, client, db):
        self._client = client

    async def _get_chat_stats(self, chat: Union[types.Channel, types.Chat]) -> Dict[str, Any]:
        try:
            chat_title = utils.escape_html(getattr(chat, 'title', 'Unknown'))
            chat_id = chat.id
            created_at = chat.date.strftime("%Y-%m-%d") if chat.date else "Unknown"

            # Получение участников
            try:
                participants = await self._client.get_participants(chat)
            except Exception:
                participants = []

            # Определение типа чата
            if isinstance(chat, types.Channel):
                try:
                    full_chat = await self._client(GetFullChannelRequest(chat))
                    chat_type = "Supergroup" if chat.megagroup else "Channel"
                    members_count = full_chat.full_chat.participants_count or len(participants)
                    admins_count = full_chat.full_chat.admins_count or 0
                    total_messages = full_chat.full_chat.read_outbox_max_id or 0
                except Exception:
                    chat_type = "Supergroup" if chat.megagroup else "Channel"
                    members_count = len(participants)
                    admins_count = sum(
                        1 for p in participants 
                        if p.participant and isinstance(p.participant, 
                            (types.ChannelParticipantAdmin, types.ChannelParticipantCreator))
                    )
                    total_messages = 0

            elif isinstance(chat, types.Chat):
                try:
                    full_chat = await self._client(GetFullChatRequest(chat.id))
                    chat_type = "Group"
                    members_count = full_chat.full_chat.participants_count or len(participants)
                    total_messages = getattr(full_chat.full_chat, "read_outbox_max_id", 0)
                    admins_count = sum(
                        1 for p in participants 
                        if isinstance(p.participant, 
                            (types.ChatParticipantAdmin, types.ChatParticipantCreator))
                    )
                except Exception:
                    chat_type = "Group"
                    members_count = len(participants)
                    admins_count = sum(
                        1 for p in participants 
                        if isinstance(p.participant, 
                            (types.ChatParticipantAdmin, types.ChatParticipantCreator))
                    )
                    total_messages = 0
            else:
                raise TypeError("Unsupported chat type")

            # Подсчет онлайн участников
            online_count = sum(
                1 for p in participants 
                if hasattr(p, 'status') and isinstance(p.status, 
                    (types.UserStatusOnline, types.UserStatusRecently))
            )

            # Подсчет ботов
            bots_count = sum(1 for p in participants if p.bot)

            return {
                "title": chat_title,
                "chat_id": chat_id,
                "chat_type": chat_type,
                "created_at": created_at,
                "members": members_count,
                "online_count": online_count,
                "bots": bots_count,
                "admins": admins_count,
                "total_messages": total_messages,
            }
        except Exception:
            return {
                "title": "Error",
                "chat_id": getattr(chat, 'id', 0),
                "chat_type": "Unknown",
                "created_at": "Unknown",
                "members": 0,
                "online_count": 0,
                "bots": 0,
                "admins": 0,
                "total_messages": 0,
            }

    @loader.command()
    async def iping(self, message):
        """Get ping and chat statistics"""
        await self._ping(message)

    async def _ping(self, message, call=None):
        # Замер пинга
        start = time.perf_counter()
        await self._client.get_me()
        ping = (time.perf_counter() - start) * 1000

        try:
            # Получение статистики чата
            chat = await self._client.get_entity(message.chat_id)
            stats = await self._get_chat_stats(chat)
            
            # Формирование текста
            text = (f"{self.strings['ping_text'].format(ping=ping)}\n\n"
                    f"{self.strings['stats_text'].format(**stats)}")
        except (ChatAdminRequiredError, TypeError, ValueError) as e:
            text = self.strings["error_text"].format(error=str(e))
        except Exception as e:
            text = self.strings["error_text"].format(
                error=f"An unexpected error occurred: {e}"
            )

        # Функция обновления пинга
        async def refresh_callback(call):
            start = time.perf_counter()
            await self._client.get_me()
            ping = (time.perf_counter() - start) * 1000
            
            text_updated = (f"{self.strings['ping_text'].format(ping=ping)}\n\n"
                            f"{self.strings['stats_text'].format(**stats)}")
            
            await call.edit(text_updated, reply_markup=[refresh_button])

        # Кнопка обновления
        refresh_button = [
            {"text": "🔄 Refresh", "callback": refresh_callback}
        ]

        # Отправка сообщения
        if call:
            await call.edit(text, reply_markup=[refresh_button])
        else:
            await self.inline.form(text, message=message, reply_markup=[refresh_button])

    async def ping_inline_handler(self, query):
        # Замер пинга
        start = time.perf_counter()
        await self._client.get_me()
        ping = (time.perf_counter() - start) * 1000

        try:
            # Обработка инлайн-запроса с chat_id
            if query.chat_id:
                chat = await self._client.get_entity(query.chat_id)
                stats = await self._get_chat_stats(chat)
                message_text = (f"{self.strings['ping_text'].format(ping=ping)}\n\n"
                                f"{self.strings['stats_text'].format(**stats)}")
                
                # Функция обновления
                async def _update_ping(call):
                    start = time.perf_counter()
                    await self._client.get_me()
                    ping = (time.perf_counter() - start) * 1000
                    await call.edit(
                        f"{self.strings['ping_text'].format(ping=ping)}\n\n"
                        f"{self.strings['stats_text'].format(**stats)}",
                        reply_markup=[[{"text": "🔄 Refresh", "callback": _update_ping}]]
                    )

                reply_markup = [[{"text": "🔄 Refresh", "callback": _update_ping}]]
            else:
                message_text = self.strings["ping_text"].format(ping=ping)
                reply_markup = None

            # Возврат результата инлайн-запроса
            return [
                {
                    "type": "article",
                    "id": "ping_result",
                    "title": f"Ping: {ping:.2f} ms",
                    "description": "Ping и статистика чата" if query.chat_id else "Ping",
                    "input_message_content": {
                        "message_text": message_text,
                        "parse_mode": "HTML",
                    },
                    "reply_markup": reply_markup,
                    "thumb_url": "https://te.legra.ph/file/5d8c7f1960a3e126d916a.jpg",
                }
            ]
        except Exception as e:
            return [
                {
                    "type": "article",
                    "id": "error_result",
                    "title": "Ошибка",
                    "description": "Произошла ошибка",
                    "input_message_content": {
                        "message_text": self.strings["error_text"].format(error=str(e)),
                        "parse_mode": "HTML",
                    },
                }
            ]
