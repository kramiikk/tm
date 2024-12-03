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
            "message": await self._get_ping_and_stats_text(message=query.peer),
            "reply_markup": [{"text": "⏱️ Ping & Stats", "callback": self._ping_callback}],
        }

    async def _ping_callback(self, call: InlineCall):
        """Специальный обработчик коллбэка для перезагрузки статистики"""
        await call.edit(
            await self._get_ping_and_stats_text(message=call.message),
            reply_markup=[{"text": "⏱️ Ping & Stats", "callback": self._ping_callback}]
        )

    async def _ping(self, query):
        """Handles both inline queries and manual command"""
        if isinstance(query, Message):
            # Для команды .iping отправляем форму
            await self.inline.form(
                await self._get_ping_and_stats_text(message=query),
                reply_markup=[{"text": "⏱️ Ping & Stats", "callback": self._ping_callback}],
                message=query,
            )

    async def _get_ping_text(self):
        """Generates the ping text (now actually measures ping)"""
        start = time.perf_counter()
        await self._client.get_me()
        end = time.perf_counter()
        return self.strings("results_ping").format((end - start) * 1000)

    async def _get_chat_stats_text(self, message, chat_id=None):
        """Generates the chat stats text"""
        try:
            # Если chat_id не передан, используем из сообщения
            if chat_id is None:
                chat_id = utils.get_chat_id(message)
            
            stats = await self._get_chat_stats(message, chat_id)

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
            return self.strings("stats_error").format(error_message)

    async def _get_ping_and_stats_text(self, message, chat_id=None):
        """Combines ping and chat stats text"""
        # Если chat_id не передан, используем из сообщения
        if chat_id is None:
            chat_id = utils.get_chat_id(message)
        
        ping_text = await self._get_ping_text()
        stats_text = await self._get_chat_stats_text(message, chat_id)
        return f"{ping_text}\n\n{stats_text}"

    async def _get_chat_stats(self, message, chat_id):
        """Gets chat stats with extensive error handling"""
        try:
            # Получаем полную информацию о чате
            full_chat = await self._client(GetFullChannelRequest(chat_id))
            
            # Получаем участников
            participants = await self._client(GetParticipantsRequest(
                channel=chat_id,
                filter=ChannelParticipantsSearch(''),
                offset=0,
                limit=0,  # Получаем только количество
                hash=0
            ))

            # Получаем название чата
            chat = await self._client.get_entity(chat_id)

            # Расчет администраторов и удаленных аккаунтов
            admins = sum(1 for p in participants.participants if hasattr(p, 'admin_rights') and p.admin_rights)
            deleted_accounts = sum(1 for p in participants.participants if hasattr(p, 'deleted') and p.deleted)

            total_messages = getattr(full_chat.full_chat, 'read_inbox_max_id', 0)

            return {
                "total_messages": total_messages,
                "total_members": participants.count,
                "admins": admins,
                "deleted_accounts": deleted_accounts,
                "chat_title": getattr(chat, 'title', 'Unknown Chat')
            }

        except Exception as e:
            # Подробный вывод ошибки для диагностики
            return {
                "error": f"{type(e).__name__}: {str(e)}",
                "chat_title": "Error"
            }
