import time
import asyncio
from telethon.tl.types import Message
from telethon.errors import ChatAdminRequiredError
from telethon.tl.functions.channels import GetFullChannelRequest, GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch

from .. import loader, utils
from ..inline.types import InlineCall, InlineQuery


@loader.tds
class PingeMod(loader.Module):
    """Inline Pinger with Chat Stats"""

    strings = {
        "name": "InlinePing",
        "results_ping": "✨ <b>Telegram ping:</b> <code>{:.3f}</code> <b>ms</b>",
        "stats_error": "**Ошибка получения статистики чата.**",
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

    async def _get_chat_stats_text(self, chat_id):
        """Generates the chat stats text"""
        try:
            stats = await self._get_chat_stats(chat_id)
            
            # Проверка, что stats это словарь и содержит все ожидаемые ключи
            if not isinstance(stats, dict) or not all(key in stats for key in ['total_members', 'admins', 'deleted_accounts', 'total_messages', 'chat_title']):
                return self.strings("stats_error")

            return self.strings("chat_stats").format(
                stats['chat_title'],
                stats['total_members'],
                stats['admins'],
                stats['deleted_accounts'],
                stats['total_messages']
            )

        except ChatAdminRequiredError:
            return self.strings("no_admin_rights")
        except Exception as e:
            return f"Error: {e}"

    async def _get_ping_and_stats_text(self, chat_id):
        ping_text = await self._get_ping_text()
        stats_text = await self._get_chat_stats_text(chat_id)
        return f"{ping_text}\n\n{stats_text}"

    async def _get_chat_stats(self, chat_id):
        """Gets chat stats - improved error handling and logic"""
        try:
            # Получаем полную информацию о чате
            full_chat = await self._client(GetFullChannelRequest(chat_id))
            
            # Получаем участников
            participants = await self._client(GetParticipantsRequest(
                channel=chat_id,
                filter=ChannelParticipantsSearch(''),
                offset=0,
                limit=0,
                hash=0
            ))

            # Получаем название чата
            chat = await self._client.get_entity(chat_id)
            chat_title = getattr(chat, 'title', 'Unknown Chat')

            total_members = participants.count
            admins = sum(1 for p in participants.participants if p.admin_rights)
            deleted_accounts = sum(1 for p in participants.participants if p.deleted)
            total_messages = full_chat.full_chat.read_inbox_max_id

            return {
                "total_messages": total_messages,
                "total_members": total_members,
                "admins": admins,
                "deleted_accounts": deleted_accounts,
                "chat_title": chat_title
            }

        except Exception as e:
            return {"error": f"Error getting stats: {e}"}
