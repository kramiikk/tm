import time
import asyncio
from telethon.tl.types import Message
from telethon.errors import ChatAdminRequiredError

from .. import loader, utils
from ..inline.types import InlineCall, InlineQuery
import hikkatl


@loader.tds
class PingerMod(loader.Module):
    """Inline Pinger with Chat Stats"""

    strings = {
        "name": "InlinePing",
        "results_ping": "✨ <b>Telegram ping:</b> <code>{:.3f}</code> <b>ms</b>",
        "stats_error": "**Ошибка получения статистики чата.**",
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

    def _get_ping_text(self):
        """Generates the ping text"""
        start = time.perf_counter_ns()
        end = time.perf_counter_ns()
        return self.strings("results_ping").format((end - start) / 10**6)

    async def _get_chat_stats_text(self, chat_id):
        """Generates the chat stats text"""
        try:
            stats = await self._get_chat_stats(chat_id)
            chat = await self._client.get_entity(chat_id)
            chat_title = getattr(chat, "title", None) or "this channel"

            return (
                f"<emoji document_id=5931472654660800739>📊</emoji> Статистика чата <u>'{chat_title}'</u>:\n\n"
                f"<emoji document_id=5942877472163892475>👥</emoji> Участников: <b>{stats['total_members']}</b>\n"
                f"└ <emoji document_id=5778423822940114949>🛡</emoji> Администраторов: <b>{stats['admins']}</b>\n"
                f"└ <emoji document_id=5872829476143894491>🚫</emoji> Удаленных аккаунтов: <b>{stats['deleted_accounts']}</b>\n\n"
                f"<emoji document_id=5886436057091673541>💬</emoji> Всего сообщений: <b>{stats['total_messages']}</b>\n"
                f"└ <emoji document_id=6048390817033228573>📷</emoji> Медиа сообщений: <b>{stats['media_messages']}</b>\n"
            )
        except ChatAdminRequiredError:
            return "**Нет прав администратора для получения статистики.**"
        except Exception:
            return self.strings("stats_error")

    async def _get_ping_and_stats_text(self, chat_id):
        ping_text = self._get_ping_text()
        stats_text = await self._get_chat_stats_text(chat_id)
        return f"{ping_text}\n\n{stats_text}"

    async def _get_chat_stats(self, chat_id):
        """Gets chat stats efficiently using a single gather call"""

        async def get_participants():
            return await self._client.get_participants(chat_id)

        async def get_messages():
            return await self._client(
                hikkatl.functions.messages.SearchRequest(
                    peer=chat_id,
                    q="",
                    filter=hikkatl.types.InputMessagesFilterEmpty(),
                    limit=0,
                )
            )

        async def get_media():
            return await self._client(
                hikkatl.functions.messages.SearchRequest(
                    peer=chat_id,
                    q="",
                    filter=hikkatl.types.InputMessagesFilterPhotoVideo(),
                    limit=0,
                )
            )

        participants, messages, media = await asyncio.gather(
            get_participants(), get_messages(), get_media()
        )

        total_members = len(participants)
        deleted_accounts = sum(1 for u in participants if u.deleted)
        admins = sum(
            1
            for u in participants
            if u.participant and getattr(u.participant, "admin_rights", None)
        )
        total_messages = messages.count
        media_count = media.count

        return {
            "total_messages": total_messages,
            "total_members": total_members,
            "admins": admins,
            "deleted_accounts": deleted_accounts,
            "media_messages": media_count,
        }
