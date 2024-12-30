from telethon import types
from telethon.tl.types import (
    MessageService,
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
        "no_query": "❌ <b>Укажите аргументы!\nПример: .joinsearch группа имя фамилия [количество_сообщений]</b>",
        "searching": "🔍 <b>Начинаю поиск в группе {} по запросу: {} {}\nБудет проверено сообщений: {}</b>",
        "progress": "🔄 <b>Проверено {} служебных сообщений...\nНайдено: {}</b>",
        "no_results": "❌ <b>Результаты не найдены (проверено {} служебных сообщений)</b>",
        "results": "✅ <b>Поиск завершен в группе {}!\nПроверено служебных сообщений: {}\nНайдено совпадений: {}</b>\n\n{}",
        "group_not_found": "❌ <b>Группа не найдена</b>",
        "invalid_args": "❌ <b>Неверные аргументы!\nИспользование: .joinsearch группа имя фамилия [количество_сообщений]</b>"
    }

    def __init__(self):
        self.name = self.strings["name"]
        self._running = False

    async def client_ready(self, client, db):
        self._client = client

    def _is_join_message(self, msg):
        """Проверяет, является ли сообщение сообщением о входе в группу"""
        if not isinstance(msg, MessageService):
            return False
            
        return isinstance(msg.action, (
            MessageActionChatJoinedByLink,  # Вход по ссылке
            MessageActionChatAddUser        # Добавление пользователя
        ))

    async def _get_user_name(self, client, user_id):
        """Получает имя пользователя по ID"""
        try:
            user = await client.get_entity(user_id)
            return f"{user.first_name} {user.last_name if user.last_name else ''}"
        except:
            return "Неизвестный пользователь"

    def _check_match(self, user_name, first_name, last_name):
        """Проверяет, соответствует ли имя пользователя поисковому запросу"""
        if not user_name:
            return False
            
        user_name_lower = user_name.lower()
        first_name_lower = first_name.lower()
        last_name_lower = last_name.lower() if last_name else ""
        
        if first_name_lower not in user_name_lower:
            return False
            
        if last_name and last_name_lower not in user_name_lower:
            return False
            
        return True

    def _parse_args(self, args):
        """Парсит аргументы команды"""
        if len(args) < 2:
            return None
            
        result = {
            "group": args[0],
            "first_name": args[1],
            "last_name": None,
            "limit": 10000
        }
        
        remaining_args = args[2:]
        for arg in remaining_args:
            try:
                num = int(arg)
                result["limit"] = min(max(num, 1), 50000)
            except ValueError:
                result["last_name"] = arg
                
        return result

    async def joinsearchcmd(self, message):
        """Поиск сообщений о присоединении пользователей в указанной группе.
        Использование: .joinsearch <группа> <имя> [фамилия] [количество_сообщений]
        Примеры: 
        .joinsearch @group_name John Doe 20000
        .joinsearch @group_name John 5000
        .joinsearch @group_name John Doe"""
        
        if self._running:
            await utils.answer(message, "⚠️ <b>Поиск уже выполняется. Дождитесь завершения.</b>")
            return

        args = utils.get_args_raw(message).split()
        parsed_args = self._parse_args(args)
        
        if not parsed_args:
            await utils.answer(message, self.strings["invalid_args"])
            return

        try:
            target_group = await message.client.get_entity(parsed_args["group"])
        except Exception:
            await utils.answer(message, self.strings["group_not_found"])
            return

        self._running = True
        status_message = await utils.answer(
            message, 
            self.strings["searching"].format(
                parsed_args["group"],
                parsed_args["first_name"],
                parsed_args["last_name"] if parsed_args["last_name"] else "",
                parsed_args["limit"]
            )
        )
        
        try:
            results = []
            messages_checked = 0
            last_update = 0
            
            async for msg in message.client.iter_messages(
                target_group,
                limit=parsed_args["limit"],
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

                # Получаем ID пользователя из действия
                user_id = None
                if isinstance(msg.action, MessageActionChatAddUser):
                    user_id = msg.action.users[0] if msg.action.users else None
                elif isinstance(msg.action, MessageActionChatJoinedByLink):
                    user_id = msg.from_id.user_id if msg.from_id else None

                if user_id:
                    user_name = await self._get_user_name(message.client, user_id)
                    if self._check_match(user_name, parsed_args["first_name"], parsed_args["last_name"]):
                        action_text = "присоединился по ссылке" if isinstance(msg.action, MessageActionChatJoinedByLink) else "был добавлен"
                        results.append(f"• {user_name} {action_text} | ID: {user_id} | <a href='t.me/{target_group.username}/{msg.id}'>Ссылка</a>")
                
                if messages_checked % 50 == 0:
                    await asyncio.sleep(0.1)

            if not results:
                await utils.answer(status_message, self.strings["no_results"].format(messages_checked))
            else:
                result_text = self.strings["results"].format(
                    parsed_args["group"],
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
