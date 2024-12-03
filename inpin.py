import asyncio
import time
import traceback
from telethon import types
from telethon.tl.functions.channels import GetFullChannelRequest

from .. import loader, utils
from ..inline.types import InlineCall, InlineQuery

@loader.tds
class PingerMod(loader.Module):
    """Точный инлайн пингер"""

    strings = {
        "name": "InlinePing",
        "ping_text": (
            "🏓 <b>Ping:</b>\n"
            "├ <code>{dc_ping:.2f} мс</code> • DC\n"
            "├ <code>{client_ping:.2f} мс</code> • Client\n"
            "└ <code>{overall_ping:.2f} мс</code> • Overall\n\n"
        )
    }

    async def client_ready(self, client, db):
        self._client = client

    async def _measure_ping(self):
        """Точное измерение пинга"""
        # Измерение пинга до ДЦ
        dc_start = time.perf_counter()
        await self._client.get_me()
        dc_ping = (time.perf_counter() - dc_start) * 1000

        # Измерение пинга клиента
        client_start = time.perf_counter()
        await asyncio.sleep(0.1)
        client_ping = (time.perf_counter() - client_start) * 1000

        # Общий пинг
        overall_ping = (dc_ping + client_ping) / 2

        return {
            "dc_ping": dc_ping,
            "client_ping": client_ping,
            "overall_ping": overall_ping
        }

    async def _get_chat_stats(self, message):
        """Получение статистики чата"""
        try:
            # Получаем chat_id напрямую
            chat_id = message.chat_id if hasattr(message, 'chat_id') else None

            # Если chat_id не определен
            if not chat_id:
                chat = await message.get_chat()
                chat_id = chat.id

            # Получаем полную информацию о чате
            full_chat = await self._client(GetFullChannelRequest(chat_id))

            # Получаем участников
            participants = await self._client.get_participants(chat_id)

            # Подсчет статистики
            total_members = len(participants)
            admins = sum(1 for p in participants if p.admin_rights)
            
            # Максимальный ID сообщения как приблизительное количество сообщений
            total_messages = getattr(full_chat.full_chat, 'read_inbox_max_id', 0)

            return {
                "title": getattr(message.chat, 'title', 'Unknown'),
                "members": total_members,
                "admins": admins,
                "messages": total_messages
            }
        except Exception as e:
            return {"error": f"Ошибка: {str(e)}"}

    @loader.command()
    async def iping(self, message):
        """Команда для получения пинга и статистики"""
        ping_data = await self._measure_ping()
        chat_stats = await self._get_chat_stats(message)

        # Формирование текста
        ping_text = self.strings["ping_text"].format(**ping_data)
        
        stats_text = (
            "📊 <b>Статистика чата:</b>\n"
            "├ <b>Название:</b> <code>{title}</code>\n"
            "├ 👥 <b>Участников:</b> <code>{members}</code>\n"
            "├ 🛡️ <b>Администраторов:</b> <code>{admins}</code>\n"
            "└ 💬 <b>Сообщений:</b> <code>{messages}</code>\n"
        ).format(**chat_stats) if not "error" in chat_stats else ""

        await self.inline.form(
            f"{ping_text}{stats_text}",
            message=message,
            reply_markup=[
                [{"text": "🔄 Пинг", "callback": self._refresh_ping}]
            ]
        )

    async def _refresh_ping(self, call: InlineCall):
        """Обновление только пинга"""
        ping_data = await self._measure_ping()
        ping_text = self.strings["ping_text"].format(**ping_data)

        await call.edit(
            ping_text,
            reply_markup=[
                [{"text": "🔄 Пинг", "callback": self._refresh_ping}]
            ]
        )

    async def ping_inline_handler(self, query: InlineQuery):
        """Инлайн хэндлер для пинга"""
        ping_data = await self._measure_ping()
        return {
            "title": f"Ping: {ping_data['overall_ping']:.2f} мс",
            "description": "Пинг",
            "message": self.strings["ping_text"].format(**ping_data),
            "thumb": "https://te.legra.ph/file/5d8c7f1960a3e126d916a.jpg"
        }
