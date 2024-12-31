from telethon import types
from telethon.tl.types import (
    MessageService,
    MessageActionChatJoinedByLink,
    MessageActionChatAddUser
)
import shlex
from .. import loader, utils

def parse_arguments(args_raw):
    """Парсит аргументы командной строки с поддержкой параметров"""
    try:
        args = shlex.split(args_raw)
    except:
        args = args_raw.split()
    
    if not args:
        return None
        
    result = {
        "group": args[0],
        "first_name": "",
        "last_name": "",
        "limit": 10000,
        "exact_match": False,
        "show_all": False
    }
    
    i = 1
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
            
        if not result["first_name"]:
            if arg in ['""', "''", '" "', "' '"]:
                result["show_all"] = True
            else:
                result["first_name"] = arg
                if args_raw.find(f'"{arg}"') != -1 or args_raw.find(f"'{arg}'") != -1:
                    result["exact_match"] = True
        elif not result["last_name"]:
            if arg in ['""', "''", '" "', "' '"]:
                result["show_all"] = True
            else:
                result["last_name"] = arg
                if args_raw.find(f'"{arg}"') != -1 or args_raw.find(f"'{arg}'") != -1:
                    result["exact_match"] = True
            
        i += 1
    
    return result

@loader.tds
class JoinSearchMod(loader.Module):
    """Поиск сообщений о присоединении пользователей к группе"""
    
    strings = {
        "name": "JoinSearch",
        "no_query": "❌ <b>Укажите аргументы!</b>",
        "searching": "🔍 <b>Начинаю поиск в группе {}\nИмя: {}\nФамилия: {}\nБудет проверено сообщений: {}</b>",
        "progress": "🔄 <b>Проверено {} служебных сообщений...\nНайдено: {}</b>",
        "no_results": "❌ <b>Результаты не найдены (проверено {} служебных сообщений)</b>",
        "results": "✅ <b>Промежуточные результаты поиска в группе {}!\nПроверено: {}\nНайдено: {}</b>\n\n{}",
        "final_results": "✅ <b>Поиск завершен в группе {}!\nВсего проверено: {}\nВсего найдено: {}</b>",
        "group_not_found": "❌ <b>Группа не найдена</b>",
        "invalid_args": "❌ <b>Неверные аргументы!</b>"
    }

    def __init__(self):
        self.name = self.strings["name"]
        self._running = False

    async def client_ready(self, client, db):
        self._client = client

    async def _get_user_name(self, client, user_id):
        """Получает имя и фамилию пользователя по ID"""
        try:
            user = await client.get_entity(user_id)
            return (user.first_name or "").lower(), (user.last_name or "").lower()
        except:
            return "", ""

    def _check_match(self, first_name, last_name, search_first_name, search_last_name, exact_match=False):
        """Проверяет совпадение имени и фамилии с поисковым запросом"""
        if exact_match:
            if (search_first_name and first_name != search_first_name.lower()) or \
               (search_last_name and last_name != search_last_name.lower()):
                return False
        else:
            if (search_first_name and search_first_name.lower() not in first_name) or \
               (search_last_name and search_last_name.lower() not in last_name):
                return False
        return True

    async def _send_results_chunk(self, message, group, messages_checked, results, is_final=False):
        """Отправляет chunk результатов"""
        if is_final:
            text = self.strings["final_results"].format(group, messages_checked, len(results))
        else:
            text = self.strings["results"].format(
                group, 
                messages_checked, 
                len(results),
                "\n".join(results[-30:])
            )
        await message.respond(text)

    async def joinsearchcmd(self, message):
        """Поиск сообщений о присоединении пользователей в указанной группе"""
        if self._running:
            await utils.answer(message, "⚠️ <b>Поиск уже выполняется</b>")
            return

        args = utils.get_args_raw(message)
        parsed_args = parse_arguments(args)
        if not parsed_args:
            await utils.answer(message, self.strings["invalid_args"])
            return

        try:
            target_group = await message.client.get_entity(parsed_args["group"])
        except Exception:
            await utils.answer(message, self.strings["group_not_found"])
            return

        self._running = True
        try:
            results = []
            messages_checked = 0
            last_update = 0
            last_results_count = 0
            
            status_message = await utils.answer(
                message, 
                self.strings["searching"].format(
                    parsed_args["group"],
                    parsed_args["first_name"] or "не указано",
                    parsed_args["last_name"] or "не указано",
                    parsed_args["limit"]
                )
            )
            
            async for msg in message.client.iter_messages(
                target_group,
                limit=parsed_args["limit"],
                filter=types.InputMessagesFilterEmpty()
            ):
                if not isinstance(msg, MessageService) or not isinstance(msg.action, (MessageActionChatJoinedByLink, MessageActionChatAddUser)):
                    continue
                    
                messages_checked += 1
                
                if messages_checked % 250 == 0 and messages_checked != last_update:
                    last_update = messages_checked
                    await status_message.edit(
                        self.strings["progress"].format(messages_checked, len(results))
                    )

                user_id = None
                if isinstance(msg.action, MessageActionChatAddUser) and msg.action.users:
                    user_id = msg.action.users[0]
                elif isinstance(msg.action, MessageActionChatJoinedByLink) and msg.from_id:
                    user_id = msg.from_id.user_id

                if not user_id:
                    continue

                if parsed_args["show_all"]:
                    first_name, last_name = await self._get_user_name(message.client, user_id)
                    user_name = f"{first_name} {last_name}".strip()
                    results.append(f"• {user_name} | ID: {user_id} | <a href='t.me/{target_group.username}/{msg.id}'>Ссылка</a> | {msg.date.strftime('%d.%m.%Y %H:%M:%S')}")
                else:
                    if not (parsed_args["first_name"] or parsed_args["last_name"]):
                        continue
                        
                    first_name, last_name = await self._get_user_name(message.client, user_id)
                    if self._check_match(first_name, last_name, 
                                      parsed_args["first_name"], parsed_args["last_name"],
                                      parsed_args["exact_match"]):
                        user_name = f"{first_name} {last_name}".strip()
                        results.append(f"• {user_name} | ID: {user_id} | <a href='t.me/{target_group.username}/{msg.id}'>Ссылка</a> | {msg.date.strftime('%d.%m.%Y %H:%M:%S')}")

                if len(results) >= last_results_count + 30:
                    await self._send_results_chunk(message, parsed_args["group"], messages_checked, results)
                    last_results_count = len(results)

            if not results:
                await utils.answer(status_message, self.strings["no_results"].format(messages_checked))
            else:
                await self._send_results_chunk(message, parsed_args["group"], messages_checked, results, is_final=True)

        except Exception as e:
            await utils.answer(status_message, f"❌ <b>Ошибка:</b>\n{str(e)}")
        finally:
            self._running = False
