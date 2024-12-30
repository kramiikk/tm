from telethon import events, types
from telethon.tl.types import (
    MessageService,
    PeerChannel,
    PeerChat,
    MessageActionChatJoinedByLink,
    MessageActionChatAddUser
)
import logging
import re
from .. import loader, utils
import asyncio

logger = logging.getLogger(__name__)

@loader.tds
class JoinSearchMod(loader.Module):
    """Поиск сообщений о присоединении пользователей к группе"""
    
    strings = {
        "name": "JoinSearch",
        "no_query": "❌ <b>Укажите поисковый запрос (текст или ID пользователя)</b>",
        "searching": "🔍 <b>Начинаю поиск в {} сообщениях...</b>",
        "progress": "🔄 <b>Проверено {} служебных сообщений...\nНайдено: {}</b>",
        "no_results": "❌ <b>Результаты не найдены (проверено {} служебных сообщений)</b>",
        "results": "✅ <b>Поиск завершен!\nПроверено служебных сообщений: {}\nНайдено совпадений: {}</b>\n\n{}"
    }

    def __init__(self):
        self.name = self.strings["name"]
        self._lock = asyncio.Lock()
        self._task = None
        self._running = False

    async def client_ready(self, client, db):
        self._client = client

    def _is_join_message(self, msg):
        """Проверяет, является ли сообщение сообщением о входе в группу"""
        if not isinstance(msg, MessageService) or not msg.action:
            return False
            
        return isinstance(msg.action, (
            MessageActionChatJoinedByLink,  # Вход по ссылке
            MessageActionChatAddUser        # Добавление пользователя
        ))

    def _check_match(self, msg, query):
        """Проверяет, соответствует ли сообщение поисковому запросу"""
        try:
            user_id = int(query)
            if isinstance(msg.action, MessageActionChatAddUser):
                return user_id in msg.action.users
            if msg.from_id:
                return user_id == msg.from_id.user_id
            return False
        except ValueError:
            return re.search(query.lower(), msg.action_message.lower())

    async def joinsearchcmd(self, message):
        """Поиск сообщений о присоединении пользователей к группе. 
        Использование: .joinsearch <запрос/ID> [количество_сообщений]
        Запрос может быть текстом или ID пользователя"""
        
        if self._running:
            await utils.answer(message, "⚠️ <b>Поиск уже выполняется. Дождитесь завершения.</b>")
            return

        args = utils.get_args_raw(message).split()
        if not args:
            await utils.answer(message, self.strings["no_query"])
            return

        query = args[0]
        try:
            limit = min(int(args[1]) if len(args) > 1 else 10000, 50000)
        except ValueError:
            limit = 10000

        self._running = True
        status_message = await utils.answer(message, self.strings["searching"].format(limit))
        
        try:
            results = []
            messages_checked = 0
            last_update = 0
            
            async for msg in message.client.iter_messages(
                message.chat_id,
                limit=limit,
                filter=types.InputMessagesFilterEmpty()
            ):
                if not self._is_join_message(msg):
                    continue
                    
                messages_checked += 1
                
                if messages_checked % 100 == 0 and messages_checked != last_update:
                    last_update = messages_checked
                    await status_message.edit(
                        self.strings["progress"].format(
                            messages_checked, len(results)
                        )
                    )
                    await asyncio.sleep(0.3)
                
                if self._check_match(msg, query):
                    user_info = f"ID: {msg.from_id.user_id}" if msg.from_id else "ID не доступен"
                    results.append(f"• {msg.action_message} | {user_info} | <a href='t.me/{message.chat.username}/{msg.id}'>Ссылка</a>")
                
                if messages_checked % 50 == 0:
                    await asyncio.sleep(0.1)

            if not results:
                await utils.answer(status_message, self.strings["no_results"].format(messages_checked))
            else:
                result_text = self.strings["results"].format(
                    messages_checked,
                    len(results),
                    "\n".join(results[:50])
                )
                
                if len(results) > 50:
                    result_text += f"\n\n<b>⚠️ Показаны первые 50 из {len(results)} результатов</b>"
                
                await utils.answer(status_message, result_text)

        except Exception as e:
            await utils.answer(status_message, f"❌ <b>Произошла ошибка:</b>\n{str(e)}")
        finally:
            self._running = False
