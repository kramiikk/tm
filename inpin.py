import time
import traceback
from telethon.tl.types import Message
from telethon.errors import ChatAdminRequiredError, FloodWaitError
from telethon.tl.functions.channels import GetFullChannelRequest, GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch

from .. import loader, utils
from ..inline.types import InlineCall, InlineQuery


@loader.tds
class PingerMod(loader.Module):
    """Inline Pinger with Chat Stats"""

    strings = {
        "name": "InlinePing",
        "results_ping": "✨ <b>Telegram ping:</b> <code>{:.3f}</code> <b>ms</b>",
        "stats_error": "**Ошибка получения статистики чата:**\n`{}`",
        "no_admin_rights": "**Нет прав администратора для получения статистики.**",
        "chat_stats": (
            "<emoji document_id=5931472654660800739>📊</emoji> Статистика чата <u>'{}'</u>:\n\n"
            "<emoji document_id=5942877472163892475>👥</emoji> Участников: <b>{}</b>\n"
            "└ <emoji document_id=5778423822940114949>🛡</emoji> Администраторов: <b>{}</b>\n"
            "└ <emoji document_id=5872829476143894491>🚫</emoji> Удаленных аккаунтов: <b>{}</b>\n\n"
            "<emoji document_id=5886436057091673541>💬</emoji> Всего сообщений: <b>{}</b>\n"
        )
    }

    async def client_ready(self, client, db):
        self._client = client

    @loader.command()
    async def iping(self, message: Message):
        """Test your userbot ping and get chat stats"""
        await self._ping(message)

    async def ping_inline_handler(self, query: InlineQuery):
        """Test your userbot ping and get chat stats"""
        return {
            "title": "Ping & Stats",
            "description": "Tap here",
            "thumb": "https://te.legra.ph/file/5d8c7f1960a3e126d916a.jpg",
            "message": await self._get_ping_and_stats_text(query.peer),
            "reply_markup": [{"text": "⏱️ Ping & Stats", "callback": self._ping}],
        }

    async def _ping(self, query):
        """Handles both inline queries and callbacks"""
        if isinstance(query, InlineCall):
            await query.edit(
                await self._get_ping_and_stats_text(query.chat),
                reply_markup=[{"text": "⏱️ Ping & Stats", "callback": self._ping}],
            )
        elif isinstance(query, Message):
            await self.inline.form(
                await self._get_ping_and_stats_text(query.peer_id),
                reply_markup=[{"text": "⏱️ Ping & Stats", "callback": self._ping}],
                message=query,
            )

    async def _get_ping_text(self):
        """Generates the ping text (now actually measures ping)"""
        start = time.perf_counter()
        await self._client.get_me()
        end = time.perf_counter()
        return self.strings("results_ping").format((end - start) * 1000)

    async def _get_chat_stats_text(self, message, chat_id):
        """Generates the chat stats text"""
        try:
            stats = await self._get_chat_stats(message, chat_id)
            
            # Отправка отладочной информации
            if stats.get('debug_messages'):
                for debug_msg in stats['debug_messages']:
                    await message.reply(debug_msg)

            return self.strings("chat_stats").format(
                stats.get('chat_title', 'Unknown Chat'),
                stats.get('total_members', 0),
                stats.get('admins', 0),
                stats.get('deleted_accounts', 0),
                stats.get('total_messages', 0)
            )

        except Exception as e:
            # Подробный вывод ошибки для диагностики
            error_message = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            await message.reply(f"Detailed error in stats retrieval:\n{error_message}")
            return self.strings("stats_error").format(error_message)

    async def _get_ping_and_stats_text(self, message):
        ping_text = await self._get_ping_text()
        stats_text = await self._get_chat_stats_text(message, message.peer_id)
        return f"{ping_text}\n\n{stats_text}"

    async def _get_chat_stats(self, message, chat_id):
        """Gets chat stats with extensive error handling"""
        debug_messages = []

        try:
            # Отладочное сообщение о типе чата
            chat = await self._client.get_entity(chat_id)
            debug_messages.append(f"Chat type: {type(chat)}")
            debug_messages.append(f"Chat title: {getattr(chat, 'title', 'No title')}")

            # Получаем полную информацию о чате
            full_chat = await self._client(GetFullChannelRequest(chat_id))
            debug_messages.append(f"Full chat retrieved: {full_chat is not None}")
            
            # Получаем участников
            try:
                participants = await self._client(GetParticipantsRequest(
                    channel=chat_id,
                    filter=ChannelParticipantsSearch(''),
                    offset=0,
                    limit=0,  # Получаем только количество
                    hash=0
                ))
                debug_messages.append(f"Total members count: {participants.count}")
            except Exception as participants_error:
                debug_messages.append(f"Participants error: {participants_error}")
                participants = type('', (), {'count': 0, 'participants': []})()

            # Расчет администраторов и удаленных аккаунтов
            try:
                admins = sum(1 for p in participants.participants if hasattr(p, 'admin_rights') and p.admin_rights)
                deleted_accounts = sum(1 for p in participants.participants if hasattr(p, 'deleted') and p.deleted)
                debug_messages.append(f"Admins count: {admins}")
                debug_messages.append(f"Deleted accounts: {deleted_accounts}")
            except Exception as count_error:
                debug_messages.append(f"Count calculation error: {count_error}")
                admins = 0
                deleted_accounts = 0

            total_messages = getattr(full_chat.full_chat, 'read_inbox_max_id', 0)
            debug_messages.append(f"Total messages: {total_messages}")

            return {
                "total_messages": total_messages,
                "total_members": participants.count,
                "admins": admins,
                "deleted_accounts": deleted_accounts,
                "chat_title": getattr(chat, 'title', 'Unknown Chat'),
                "debug_messages": debug_messages
            }

        except FloodWaitError as flood:
            # Специфическая обработка FloodWaitError
            debug_messages.append(f"Flood Wait: Wait for {flood.seconds} seconds")
            return {
                "error": f"Flood Wait: Wait for {flood.seconds} seconds",
                "chat_title": "Error",
                "debug_messages": debug_messages
            }
        except Exception as e:
            # Подробный вывод ошибки для диагностики
            debug_messages.append(f"Full error in _get_chat_stats: {e}")
            debug_messages.append(traceback.format_exc())
            return {
                "error": f"{type(e).__name__}: {str(e)}",
                "chat_title": "Error",
                "debug_messages": debug_messages
            }
