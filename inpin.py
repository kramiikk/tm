from telethon import TelegramClient, types
from telethon.errors import ChatAdminRequiredError
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest

import time
from typing import Union, Dict, Any

from .. import loader, utils

@loader.tds
class InlinePingMod(loader.Module):
    """Compact inline pinger with detailed chat stats"""

    strings = {
        "name": "InlinePing",
        "ping_text": "🏓 <b>Ping:</b> {ping:.2f} ms",
        "stats_text": "📊 <b>{title}:</b>\n"
                      "ID: <code>{chat_id}</code>\n"
                      "Type: {chat_type}\n"
                      "Members: {members}\n"
                      "Online: ~{online_count}\n"
                      "Bots: {bots}\n"
                      "Deleted: {deleted_accounts}\n"
                      "Admins: {admins}\n"
                      "Messages: {total_messages}\n",
        "error_text": "❌ <b>Error:</b> {error}",
    }

    async def client_ready(self, client, db):
        self._client = client

    async def _get_chat_stats(self, chat: Union[types.Channel, types.Chat]) -> Dict[str, Any]:
        try:
            # Базовая информация о чате
            chat_title = utils.escape_html(getattr(chat, 'title', 'Unknown'))
            chat_id = chat.id

            # Определение типа чата
            if isinstance(chat, types.Channel):
                chat_type = "Supergroup" if chat.megagroup else "Channel"
            elif isinstance(chat, types.Chat):
                chat_type = "Group"
            else:
                raise TypeError("Unsupported chat type")

            # Получение участников с более надежной обработкой
            try:
                participants = await self._client.get_participants(chat, limit=None)
            except Exception:
                participants = []

            # Специализированный подсчет статистики
            def count_stats(participants):
                online_statuses = [
                    types.UserStatusOnline, 
                    types.UserStatusRecently, 
                    types.UserStatusLastWeek
                ]
                
                return {
                    "members": len(participants),
                    "online_count": sum(
                        1 for p in participants 
                        if hasattr(p, 'status') and type(p.status) in online_statuses
                    ),
                    "bots": sum(1 for p in participants if p.bot),
                    "deleted_accounts": sum(1 for p in participants if p.deleted),
                    "admins": sum(
                        1 for p in participants 
                        if p.participant and isinstance(p.participant, 
                            (types.ChannelParticipantAdmin, 
                             types.ChannelParticipantCreator, 
                             types.ChatParticipantAdmin, 
                             types.ChatParticipantCreator))
                    )
                }

            # Попытка получения полной информации о чате
            try:
                if isinstance(chat, types.Channel):
                    full_chat = await self._client(GetFullChannelRequest(chat))
                    total_messages = full_chat.full_chat.read_outbox_max_id or 0
                elif isinstance(chat, types.Chat):
                    full_chat = await self._client(GetFullChatRequest(chat.id))
                    total_messages = getattr(full_chat.full_chat, "read_outbox_max_id", 0)
                else:
                    total_messages = 0
            except Exception:
                total_messages = 0

            # Объединение статистики
            stats = count_stats(participants)
            stats.update({
                "title": chat_title,
                "chat_id": chat_id,
                "chat_type": chat_type,
                "total_messages": total_messages
            })

            return stats

        except Exception as e:
            return {
                "title": "Error",
                "chat_id": getattr(chat, 'id', 0),
                "chat_type": "Unknown",
                "members": 0,
                "online_count": 0,
                "bots": 0,
                "deleted_accounts": 0,
                "admins": 0,
                "total_messages": 0,
            }

    @loader.command()
    async def iping(self, message):
        """Get ping and chat statistics"""
        await self._ping(message)

    async def _ping(self, message, call=None):
        # Замер пинга с повышенной точностью
        start = time.perf_counter_ns()
        await self._client.get_me()
        ping = (time.perf_counter_ns() - start) / 1_000_000  # Конвертация в миллисекунды

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
            start = time.perf_counter_ns()
            await self._client.get_me()
            ping = (time.perf_counter_ns() - start) / 1_000_000
            
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
        start = time.perf_counter_ns()
        await self._client.get_me()
        ping = (time.perf_counter_ns() - start) / 1_000_000

        try:
            # Обработка инлайн-запроса с chat_id
            if query.chat_id:
                chat = await self._client.get_entity(query.chat_id)
                stats = await self._get_chat_stats(chat)
                message_text = (f"{self.strings['ping_text'].format(ping=ping)}\n\n"
                                f"{self.strings['stats_text'].format(**stats)}")
                
                # Функция обновления
                async def _update_ping(call):
                    start = time.perf_counter_ns()
                    await self._client.get_me()
                    ping = (time.perf_counter_ns() - start) / 1_000_000
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
