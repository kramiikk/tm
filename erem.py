from telethon import types
from telethon.tl.types import (
    MessageService,
    MessageActionChatJoinedByLink,
    MessageActionChatAddUser
)
import logging
import re
import shlex
from .. import loader, utils
import asyncio

logger = logging.getLogger(__name__)

def parse_arguments(args_raw):
    """Парсит аргументы командной строки с поддержкой параметров"""
    try:
        args = shlex.split(args_raw)
    except:
        args = args_raw.split()
    
    result = {
        "group": None,
        "first_name": "",
        "last_name": "",
        "limit": 10000,
        "exact_match": False,
        "show_all": False
    }
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg in ('-l', '--limit'):
            if i + 1 < len(args):
                try:
                    result["limit"] = max(int(args[i + 1]), 1)
                    i += 2
                    continue
                except ValueError:
                    pass
            i += 1
            continue
            
        if result["group"] is None:
            result["group"] = arg
        elif not result["first_name"]:
            if arg == "''" or arg == '""' or arg == '" "' or arg == "' '":
                result["show_all"] = True
            else:
                result["first_name"] = arg
                if args_raw.find(f'"{arg}"') != -1 or args_raw.find(f"'{arg}'") != -1:
                    result["exact_match"] = True
        elif not result["last_name"]:
            if arg == "''" or arg == '""' or arg == '" "' or arg == "' '":
                result["show_all"] = True
            else:
                result["last_name"] = arg
                if args_raw.find(f'"{arg}"') != -1 or args_raw.find(f"'{arg}'") != -1:
                    result["exact_match"] = True
            
        i += 1
    
    return result if result["group"] else None

@loader.tds
class JoinSearchMod(loader.Module):
    """Поиск сообщений о присоединении пользователей к группе"""
    
    strings = {
        "name": "JoinSearch",
        "no_query": "❌ <b>Укажите аргументы!</b>",
        "searching": "🔍 <b>Начинаю поиск в группе {}\nИмя: {}\nФамилия: {}\nБудет проверено сообщений: {}</b>",
        "progress": "🔄 <b>Проверено {} служебных сообщений...\nНайдено: {}</b>",
        "no_results": "❌ <b>Результаты не найдены (проверено {} служебных сообщений)</b>",
        "results": "✅ <b>Промежуточные результаты поиска в группе {}!\nПроверено служебных сообщений: {}\nНайдено совпадений: {}</b>\n\n{}",
        "final_results": "✅ <b>Поиск завершен в группе {}!\nВсего проверено служебных сообщений: {}\nВсего найдено совпадений: {}</b>",
        "group_not_found": "❌ <b>Группа не найдена</b>",
        "invalid_args": (
            "❌ <b>Неверные аргументы!</b>\n\n"
            "<b>Использование:</b>\n"
            "➠ <code>.joinsearch группа [имя] [фамилия] [-l количество]</code>\n\n"
            "<b>Параметры:</b>\n"
            "• <code>группа</code> - username или ID группы\n"
            "• <code>имя</code> - имя для поиска (опционально)\n"
            "• <code>фамилия</code> - фамилия для поиска (опционально)\n"
            "• <code>-l</code> или <code>--limit</code> - количество проверяемых сообщений\n\n"
            "<b>Примеры:</b>\n"
            "• <code>.joinsearch @group_name Иван</code>\n"
            "• <code>.joinsearch @group_name Иван Петров</code>\n"
            "• <code>.joinsearch @group_name \"\" Петров</code>\n"
            "• <code>.joinsearch @group_name Иван -l 5000</code>\n"
            "• <code>.joinsearch @group_name Иван Петров --limit 20000</code>"
        )
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
            MessageActionChatJoinedByLink,
            MessageActionChatAddUser
        ))

    async def _get_user_name(self, client, user_id):
        """Получает имя и фамилию пользователя по ID"""
        try:
            user = await client.get_entity(user_id)
            return user.first_name or "", user.last_name or ""
        except:
            return "", ""

    def _check_match(self, first_name, last_name, search_first_name, search_last_name, exact_match=False):
        """Проверяет совпадение имени и фамилии с поисковым запросом"""
        if not first_name and not last_name:
            return False
            
        first_name = first_name.lower() if first_name else ""
        last_name = last_name.lower() if last_name else ""
        search_first_name = search_first_name.lower() if search_first_name else ""
        search_last_name = search_last_name.lower() if search_last_name else ""
        
        if exact_match:
            if search_first_name and first_name != search_first_name:
                return False
            if search_last_name and last_name != search_last_name:
                return False
        else:
            if search_first_name and search_first_name not in first_name:
                return False
            if search_last_name and search_last_name not in last_name:
                return False
            
        return bool(search_first_name or search_last_name)

    async def _send_results_chunk(self, message, group, messages_checked, results, is_final=False):
        """Отправляет chunk результатов"""
        if is_final:
            result_text = self.strings["final_results"].format(
                group,
                messages_checked,
                len(results)
            )
        else:
            result_text = self.strings["results"].format(
                group,
                messages_checked,
                len(results),
                "\n".join(results[-50:])  # Берем последние 50 результатов
            )
        
        await message.respond(result_text)
        await asyncio.sleep(0.3)

    async def joinsearchcmd(self, message):
        """Поиск сообщений о присоединении пользователей в указанной группе"""
        if self._running:
            await utils.answer(message, "⚠️ <b>Поиск уже выполняется. Дождитесь завершения.</b>")
            return

        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["invalid_args"])
            return
            
        parsed_args = parse_arguments(args)
        if not parsed_args:
            await utils.answer(message, self.strings["invalid_args"])
            return
            
        if not parsed_args["show_all"] and not (parsed_args["first_name"] or parsed_args["last_name"]):
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
                parsed_args["first_name"] or "не указано",
                parsed_args["last_name"] or "не указано",
                parsed_args["limit"]
            )
        )
        
        try:
            results = []
            messages_checked = 0
            last_update = 0
            last_results_count = 0
            
            async for msg in message.client.iter_messages(
                target_group,
                limit=parsed_args["limit"],
                filter=types.InputMessagesFilterEmpty()
            ):
                if not self._is_join_message(msg):
                    continue
                    
                messages_checked += 1
                
                if messages_checked % 250 == 0 and messages_checked != last_update:
                    last_update = messages_checked
                    await status_message.edit(
                        self.strings["progress"].format(
                            messages_checked, len(results)
                        )
                    )
                    await asyncio.sleep(0.1)

                user_id = None
                if isinstance(msg.action, MessageActionChatAddUser):
                    user_id = msg.action.users[0] if msg.action.users else None
                elif isinstance(msg.action, MessageActionChatJoinedByLink):
                    user_id = msg.from_id.user_id if msg.from_id else None

                if user_id:
                    if parsed_args["show_all"]:
                        first_name, last_name = await self._get_user_name(message.client, user_id)
                        user_name = f"{first_name} {last_name}".strip()
                        action_text = "присоединился по ссылке" if isinstance(msg.action, MessageActionChatJoinedByLink) else "был добавлен"
                        results.append(f"• {user_name} {action_text} | ID: {user_id} | <a href='t.me/{target_group.username}/{msg.id}'>Ссылка</a> | {msg.date.strftime('%d.%m.%Y %H:%M:%S')}")
                    else:
                        first_name, last_name = await self._get_user_name(message.client, user_id)
                        if self._check_match(first_name, last_name, 
                                          parsed_args["first_name"], parsed_args["last_name"],
                                          parsed_args["exact_match"]):
                            user_name = f"{first_name} {last_name}".strip()
                            action_text = "присоединился по ссылке" if isinstance(msg.action, MessageActionChatJoinedByLink) else "был добавлен"
                            if parsed_args["exact_match"]:
                                results.append(f"• {user_name} {action_text} | ID: {user_id} | <a href='t.me/{target_group.username}/{msg.id}'>Ссылка</a> | {msg.date.strftime('%d.%m.%Y %H:%M:%S')}")
                            else:
                                results.append(f"• {user_name} {action_text} | ID: {user_id} | <a href='t.me/{target_group.username}/{msg.id}'>Ссылка</a>")

                # Отправляем промежуточные результаты каждые 50 найденных сообщений
                if len(results) >= last_results_count + 50:
                    await self._send_results_chunk(message, parsed_args["group"], messages_checked, results)
                    last_results_count = len(results)
                
                if messages_checked % 100 == 0:
                    await asyncio.sleep(0.05)

            if not results:
                await utils.answer(status_message, self.strings["no_results"].format(messages_checked))
            else:
                # Отправляем финальное сообщение
                await self._send_results_chunk(message, parsed_args["group"], messages_checked, results, is_final=True)

        except Exception as e:
            await utils.answer(status_message, f"❌ <b>Произошла ошибка:</b>\n{str(e)}")
        finally:
            self._running = False
