import asyncio
import logging
import random
import time
from typing import List, Dict, Optional, Union

from telethon import TelegramClient
from telethon.errors import (
    ChatWriteForbiddenError, 
    UserBannedInChannelError, 
    FloodWaitError,
    MessageNotModifiedError
)
from telethon.tl.types import Message, InputMediaPhoto, InputMediaDocument

from .. import loader, utils

logger = logging.getLogger(__name__)

class BroadcastConfig:
    """Конфигурация и управление широковещательными кодами"""
    
    def __init__(self, db):
        self._db = db
        self._config_key = "broadcast_config"
        self._codes: Dict[str, Dict] = self._load_config()

    def _load_config(self) -> Dict[str, Dict]:
        """Загрузка конфигурации из базы данных"""
        return self._db.get(self._config_key, {})

    def save_config(self):
        """Сохранение конфигурации в базу данных"""
        self._db.set(self._config_key, self._codes)

    def create_code(self, code_name: str) -> bool:
        """Создание нового кода рассылки"""
        if code_name in self._codes:
            return False
        
        self._codes[code_name] = {
            'chats': set(),
            'messages': [],
            'min_interval': 540,   # 9 минут
            'max_interval': 780,   # 13 минут
            'last_broadcast': 0
        }
        self.save_config()
        return True

    def delete_code(self, code_name: str) -> bool:
        """Удаление кода рассылки"""
        return bool(self._codes.pop(code_name, None))

    def add_chat(self, code_name: str, chat_id: int) -> bool:
        """Добавление чата в код рассылки"""
        if code_name not in self._codes:
            return False
        
        self._codes[code_name]['chats'].add(chat_id)
        self.save_config()
        return True

    def remove_chat(self, code_name: str, chat_id: int) -> bool:
        """Удаление чата из кода рассылки"""
        if code_name not in self._codes or chat_id not in self._codes[code_name]['chats']:
            return False
        
        self._codes[code_name]['chats'].remove(chat_id)
        self.save_config()
        return True

    def add_message(self, code_name: str, message: Message) -> bool:
        """Добавление сообщения в код рассылки"""
        if code_name not in self._codes:
            return False
        
        msg_data = {
            'chat_id': message.chat_id,
            'message_id': message.id,
            'grouped_id': getattr(message, 'grouped_id', None)
        }
        
        self._codes[code_name]['messages'].append(msg_data)
        self.save_config()
        return True

    def get_codes(self) -> Dict[str, Dict]:
        """Получение всех кодов рассылки"""
        return self._codes

class BroadcastManager:
    """Основной менеджер широковещательной рассылки"""
    
    def __init__(self, client: TelegramClient, db):
        self._client = client
        self._config = BroadcastConfig(db)
        self._tasks: Dict[str, asyncio.Task] = {}
        self._active = True

    async def start(self):
        """Запуск широковещательных циклов"""
        for code_name in self._config.get_codes():
            await self.start_broadcast(code_name)

    async def start_broadcast(self, code_name: str):
        """Запуск широковещательного цикла для конкретного кода"""
        if code_name in self._tasks:
            return

        task = asyncio.create_task(self._broadcast_loop(code_name))
        self._tasks[code_name] = task

    async def stop_broadcast(self, code_name: str):
        """Остановка широковещательного цикла"""
        task = self._tasks.pop(code_name, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _broadcast_loop(self, code_name: str):
        """Основной цикл широковещательной рассылки"""
        codes = self._config.get_codes()
        code = codes.get(code_name)
        
        while self._active:
            try:
                if not code or not code['chats'] or not code['messages']:
                    await asyncio.sleep(300)
                    continue

                # Проверка интервала между рассылками
                current_time = time.time()
                interval = random.uniform(code['min_interval'], code['max_interval'])
                
                if current_time - code['last_broadcast'] < interval:
                    await asyncio.sleep(interval)
                    continue

                # Получение и отправка сообщения
                message = await self._get_message(code_name)
                if not message:
                    continue

                await self._send_to_chats(code_name, message)
                
                # Обновление времени последней рассылки
                code['last_broadcast'] = current_time
                self._config.save_config()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Broadcast error in {code_name}: {e}")
                await asyncio.sleep(60)

    async def _get_message(self, code_name: str) -> Optional[Message]:
        """Получение следующего сообщения для рассылки"""
        codes = self._config.get_codes()
        code = codes.get(code_name)
        
        if not code or not code['messages']:
            return None

        try:
            msg_data = code['messages'][0]
            message = await self._client.get_messages(
                msg_data['chat_id'], 
                ids=msg_data['message_id']
            )

            if not message:
                code['messages'].pop(0)
                self._config.save_config()
                return None

            return message
        except Exception as e:
            logger.error(f"Message retrieval error: {e}")
            return None

    async def _send_to_chats(self, code_name: str, message: Message):
        """Отправка сообщения во все чаты кода"""
        codes = self._config.get_codes()
        code = codes.get(code_name)
        
        chats = list(code['chats'])
        random.shuffle(chats)

        for chat_id in list(chats):
            try:
                await self._safe_send(chat_id, message)
            except (ChatWriteForbiddenError, UserBannedInChannelError):
                code['chats'].remove(chat_id)
                logger.info(f"Removed chat {chat_id} from {code_name}")

        self._config.save_config()

    async def _safe_send(self, chat_id: int, message: Message):
        """Безопасная отправка сообщения с защитой от флуда"""
        try:
            if message.media:
                # Обработка медиафайлов с дополнительной безопасностью
                media = message.media
                caption = message.text or ''
                
                if isinstance(media, (InputMediaPhoto, InputMediaDocument)):
                    await self._client.send_file(
                        entity=chat_id, 
                        file=media, 
                        caption=caption
                    )
                else:
                    logger.warning(f"Unsupported media type: {type(media)}")
            else:
                await self._client.send_message(
                    entity=chat_id, 
                    message=message.text or ''
                )
            
            await asyncio.sleep(random.uniform(1, 3))
        
        except FloodWaitError as flood:
            logger.warning(f"Flood wait: {flood.seconds} seconds")
            await asyncio.sleep(flood.seconds)
        
        except MessageNotModifiedError:
            logger.info("Message not modified, skipping")

@loader.tds
class BroadcastModule(loader.Module):
    """Профессиональный модуль распределенной широковещательной рассылки"""

    strings = {
        "name": "Broadcast",
        "code_created": "Код рассылки '{}' создан",
        "code_deleted": "Код рассылки '{}' удален",
        "chat_added": "Чат {} добавлен в рассылку '{}'",
        "chat_removed": "Чат {} удален из рассылки '{}'",
        "message_added": "Сообщение добавлено в рассылку '{}'",
    }

    def __init__(self):
        self._manager = None

    async def client_ready(self, client, db):
        self._manager = BroadcastManager(client, db)
        await self._manager.start()

    async def addcodecmd(self, message):
        """Создать код рассылки"""
        args = utils.get_args(message)
        if not args:
            return await utils.answer(message, "Укажите код рассылки")
        
        code_name = args[0]
        success = self._manager._config.create_code(code_name)
        
        response = (
            self.strings["code_created"].format(code_name) 
            if success else "Код уже существует"
        )
        await utils.answer(message, response)

    async def delcodecmd(self, message):
        """Удалить код рассылки"""
        args = utils.get_args(message)
        if not args:
            return await utils.answer(message, "Укажите код рассылки")
        
        code_name = args[0]
        await self._manager.stop_broadcast(code_name)
        success = self._manager._config.delete_code(code_name)
        
        response = (
            self.strings["code_deleted"].format(code_name) 
            if success else "Код не найден"
        )
        await utils.answer(message, response)

    async def addmsgcmd(self, message):
        """Добавить сообщение в рассылку"""
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        
        if not args or not reply:
            return await utils.answer(message, "Укажите код и ответьте на сообщение")
        
        code_name = args[0]
        success = self._manager._config.add_message(code_name, reply)
        
        response = (
            self.strings["message_added"].format(code_name) 
            if success else "Не удалось добавить сообщение"
        )
        await utils.answer(message, response)

    async def addchatcmd(self, message):
        """Добавить чат в рассылку"""
        args = utils.get_args(message)
        if len(args) < 2:
            return await utils.answer(message, "Укажите код и ID чата")
        
        code_name, chat_id = args[0], int(args[1])
        success = self._manager._config.add_chat(code_name, chat_id)
        
        response = (
            self.strings["chat_added"].format(chat_id, code_name) 
            if success else "Не удалось добавить чат"
        )
        await utils.answer(message, response)

    async def delchatcmd(self, message):
        """Удалить чат из рассылки"""
        args = utils.get_args(message)
        if len(args) < 2:
            return await utils.answer(message, "Укажите код и ID чата")
        
        code_name, chat_id = args[0], int(args[1])
        success = self._manager._config.remove_chat(code_name, chat_id)
        
        response = (
            self.strings["chat_removed"].format(chat_id, code_name) 
            if success else "Не удалось удалить чат"
        )
        await utils.answer(message, response)
