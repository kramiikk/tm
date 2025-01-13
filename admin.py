import json
import logging
from typing import Union

from .. import loader, utils
from telethon.tl.types import Message

logger = logging.getLogger(__name__)

@loader.tds
class AuthManagerMod(loader.Module):
    """Модуль управления авторизацией пользователей для broadcast модуля"""

    strings = {
        "name": "AuthManager",
        "user_added": "✅ Пользователь {} добавлен в список авторизованных",
        "user_removed": "✅ Пользователь {} удален из списка авторизованных",
        "user_exists": "⚠️ Пользователь {} уже в списке авторизованных",
        "user_not_found": "⚠️ Пользователь {} не найден в списке авторизованных",
        "invalid_id": "❌ Неверный формат ID пользователя",
        "auth_list": "📝 <b>Список авторизованных пользователей:</b>\n{}",
        "auth_list_empty": "📝 Список авторизованных пользователей пуст",
        "need_user_id": "⚠️ Укажите ID пользователя",
        "json_created": "✅ Файл конфигурации создан успешно",
        "json_error": "❌ Ошибка при работе с файлом: {}"
    }

    async def client_ready(self, client, db):
        """Инициализация при запуске."""
        self._client = client
        self._db = db
        self._me = await client.get_me()

    async def _load_json(self) -> Union[dict, None]:
        """Загрузка данных из JSON файла."""
        try:
            with open("/root/Heroku/loll.json", 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            return {"authorized_users": []}
        except Exception as e:
            logger.error(f"Error loading JSON: {e}")
            return None

    async def _save_json(self, data: dict) -> bool:
        """Сохранение данных в JSON файл."""
        try:
            with open("/root/Heroku/loll.json", 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error saving JSON: {e}")
            return False

    async def createjsoncmd(self, message: Message):
        """Создать JSON файл для авторизации."""
        try:
            data = {"authorized_users": [self._me.id]}
            if await self._save_json(data):
                await utils.answer(message, self.strings["json_created"])
            else:
                await utils.answer(message, self.strings["json_error"].format("Ошибка сохранения"))
        except Exception as e:
            await utils.answer(message, self.strings["json_error"].format(str(e)))

    async def addusercmd(self, message: Message):
        """Добавить пользователя в список авторизованных."""
        args = utils.get_args(message)
        if not args:
            return await utils.answer(message, self.strings["need_user_id"])

        try:
            user_id = int(args[0])
            data = await self._load_json()
            if data is None:
                return await utils.answer(
                    message, self.strings["json_error"].format("Ошибка чтения файла")
                )

            if user_id in data["authorized_users"]:
                return await utils.answer(
                    message, self.strings["user_exists"].format(user_id)
                )

            data["authorized_users"].append(user_id)
            if await self._save_json(data):
                await utils.answer(message, self.strings["user_added"].format(user_id))
            else:
                await utils.answer(
                    message, self.strings["json_error"].format("Ошибка сохранения")
                )
        except ValueError:
            await utils.answer(message, self.strings["invalid_id"])
        except Exception as e:
            await utils.answer(message, self.strings["json_error"].format(str(e)))

    async def delusercmd(self, message: Message):
        """Удалить пользователя из списка авторизованных."""
        args = utils.get_args(message)
        if not args:
            return await utils.answer(message, self.strings["need_user_id"])

        try:
            user_id = int(args[0])
            data = await self._load_json()
            if data is None:
                return await utils.answer(
                    message, self.strings["json_error"].format("Ошибка чтения файла")
                )

            if user_id == self._me.id:
                return await utils.answer(
                    message, "❌ Невозможно удалить администратора из списка"
                )

            if user_id not in data["authorized_users"]:
                return await utils.answer(
                    message, self.strings["user_not_found"].format(user_id)
                )

            data["authorized_users"].remove(user_id)
            if await self._save_json(data):
                await utils.answer(message, self.strings["user_removed"].format(user_id))
            else:
                await utils.answer(
                    message, self.strings["json_error"].format("Ошибка сохранения")
                )
        except ValueError:
            await utils.answer(message, self.strings["invalid_id"])
        except Exception as e:
            await utils.answer(message, self.strings["json_error"].format(str(e)))

    async def listusercmd(self, message: Message):
        """Показать список авторизованных пользователей."""
        try:
            data = await self._load_json()
            if data is None:
                return await utils.answer(
                    message, self.strings["json_error"].format("Ошибка чтения файла")
                )

            users = data.get("authorized_users", [])
            if users:
                user_list = "\n".join(f"• {user_id}" + (" (админ)" if user_id == self._me.id else "") 
                                    for user_id in users)
                await utils.answer(message, self.strings["auth_list"].format(user_list))
            else:
                await utils.answer(message, self.strings["auth_list_empty"])
        except Exception as e:
            await utils.answer(message, self.strings["json_error"].format(str(e)))
