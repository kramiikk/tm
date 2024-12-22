import asyncio
import logging
import random
import time
from contextlib import suppress
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Union, Any
from datetime import datetime, timedelta
from ratelimit import limits, sleep_and_retry

from telethon import functions
from telethon.errors import ChatWriteForbiddenError, UserBannedInChannelError
from telethon.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BroadcastMessage:
    """Message data for broadcasting."""
    chat_id: int
    message_id: int
    grouped_id: Optional[int] = None
    album_ids: Tuple[int, ...] = field(default_factory=tuple)


@dataclass
class BroadcastCode:
    """Broadcast settings container."""
    chats: Set[int] = field(default_factory=set)
    messages: List[BroadcastMessage] = field(default_factory=list)
    interval: Tuple[int, int] = field(default_factory=lambda: (10, 13))
    send_mode: str = "auto"

    def is_valid_interval(self) -> bool:
        min_val, max_val = self.interval
        return (
            isinstance(min_val, int)
            and isinstance(max_val, int)
            and 0 < min_val < max_val <= 1440
        )

    def normalize_interval(self) -> Tuple[int, int]:
        return self.interval if self.is_valid_interval() else (10, 13)


class MessageCache:
    """Thread-safe message cache implementation."""
    def __init__(self):
        self.cache = OrderedDict()
        self._lock = asyncio.Lock()
        
    async def get(self, key: Tuple[int, int]) -> Optional[Union[Message, List[Message]]]:
        async with self._lock:
            return self.cache.get(key)
            
    async def set(self, key: Tuple[int, int], value: Union[Message, List[Message]]):
        async with self._lock:
            self.cache[key] = value
            
    def clear(self):
        self.cache.clear()

class BroadcastManager:
    """Manages broadcast operations and state."""
    def __init__(self, client, db):
        self.client = client
        self.db = db
        self.codes = OrderedDict()
        self.broadcast_tasks = OrderedDict()
        self.message_indices = OrderedDict()
        self.last_broadcast_time = OrderedDict()
        self._message_cache = MessageCache()
        self._active = True
    
    async def cleanup_manager(self):
        """Cleanup all tasks and caches."""
        # Clean inactive tasks
        for code_name in list(self.broadcast_tasks.keys()):
            task = self.broadcast_tasks[code_name]
            if task.done():
                del self.broadcast_tasks[code_name]
            else:
                self.broadcast_tasks.move_to_end(code_name)
                
        # Clean outdated broadcast times
        current_time = time.time()
        max_age = 24 * 60 * 60  # 24 hours
        self.last_broadcast_time = OrderedDict(
            (k, v) for k, v in self.last_broadcast_time.items()
            if current_time - v < max_age
        )

    def _create_broadcast_code_from_dict(self, code_data: dict) -> BroadcastCode:
        """Creates BroadcastCode object from dictionary."""
        return BroadcastCode(
            chats=set(code_data.get("chats", [])),
            messages=[
                BroadcastMessage(
                    chat_id=msg_data["chat_id"],
                    message_id=msg_data["message_id"],
                    grouped_id=msg_data.get("grouped_id"),
                    album_ids=tuple(msg_data.get("album_ids", [])),
                )
                for msg_data in code_data.get("messages", [])
            ],
            interval=tuple(code_data.get("interval", (10, 13))),
            send_mode=code_data.get("send_mode", "auto"),
        )

    def _load_config_from_dict(self, data: dict):
        """Loads broadcast configuration from dictionary."""
        for code_name, code_data in data.get("codes", {}).items():
            try:
                self.codes[code_name] = self._create_broadcast_code_from_dict(code_data)
            except Exception:
                logger.error(f"Error loading broadcast code {code_name}")

    def save_config(self):
        """Saves current configuration to database."""
        try:
            config = {
                "codes": {
                    name: {
                        "chats": list(code.chats),
                        "messages": [
                            {
                                "chat_id": msg.chat_id,
                                "message_id": msg.message_id,
                                "grouped_id": msg.grouped_id,
                                "album_ids": list(msg.album_ids),
                            }
                            for msg in code.messages
                        ],
                        "interval": list(code.interval),
                        "send_mode": code.send_mode,
                    }
                    for name, code in self.codes.items()
                }
            }
            self.db.set("broadcast", "config", config)
        except Exception:
            logger.error("Failed to save config")

    async def _fetch_messages(self, msg_data: BroadcastMessage) -> Optional[Union[Message, List[Message]]]:
        """Fetches messages with caching."""
        try:
            cached = await self._message_cache.get((msg_data.chat_id, msg_data.message_id))
            if cached:
                return cached
                
            message_ids = list(msg_data.album_ids) if msg_data.grouped_id else [msg_data.message_id]
            messages = await self.client.get_messages(msg_data.chat_id, ids=message_ids)
            
            if msg_data.grouped_id:
                messages = [msg for msg in messages if msg]
                messages.sort(key=lambda x: x.id)
                
            if messages:
                await self._message_cache.set((msg_data.chat_id, msg_data.message_id), messages)
                return messages
                
        except Exception:
            logger.error(f"Failed to fetch message from {msg_data.chat_id}")
            
        return None

    async def add_message(self, code_name: str, message: Message) -> bool:
        """Adds message to broadcast list."""
        try:
            if code_name not in self.codes:
                self.codes[code_name] = BroadcastCode()
                
            code = self.codes[code_name]
            grouped_id = getattr(message, "grouped_id", None)

            if grouped_id:
                album_messages = [message]
                async for album_msg in self.client.iter_messages(
                    message.chat_id, min_id=message.id
                ):
                    if (
                        hasattr(album_msg, "grouped_id")
                        and album_msg.grouped_id == message.grouped_id
                    ):
                        album_messages.append(album_msg)
                    elif album_msg.id < message.id - 10:
                        break
                album_messages.sort(key=lambda m: m.id)
                msg_data = BroadcastMessage(
                    chat_id=message.chat_id,
                    message_id=message.id,
                    grouped_id=grouped_id,
                    album_ids=tuple(msg.id for msg in album_messages),
                )
            else:
                msg_data = BroadcastMessage(
                    chat_id=message.chat_id,
                    message_id=message.id
                )

            code.messages.append(msg_data)
            self.save_config()
            return True
        except Exception:
            logger.exception("Failed to add message")
            return False

    @sleep_and_retry
    @limits(calls=1, period=5)
    async def _send_message(
        self,
        chat_id: int,
        message: Union[Message, List[Message]],
        send_mode: str = "auto",
        schedule_time: Optional[datetime] = None,
    ):
        """Sends message with rate limiting."""
        try:
            if isinstance(message, list):
                await self.client.forward_messages(
                    entity=chat_id,
                    messages=message,
                    from_peer=message[0].chat_id,
                    schedule=schedule_time,
                )
            elif message.media and send_mode != "normal":
                await self.client.forward_messages(
                    entity=chat_id,
                    messages=[message.id],
                    from_peer=message.chat_id,
                    schedule=schedule_time,
                )
            else:
                await self.client.send_message(
                    entity=chat_id,
                    message=message.text,
                    schedule=schedule_time,
                )
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {str(e)}")
            raise

    async def _broadcast_loop(self, code_name: str):
        """Main broadcast loop."""
        while self._active:
            try:
                await self.cleanup_manager()
                code = self.codes.get(code_name)
                
                if not code or not (code.chats and code.messages):
                    await asyncio.sleep(60)
                    continue

                min_interval, max_interval = code.normalize_interval()
                schedule_delay = random.randint(60, 180)
                time_until_schedule = random.uniform(min_interval, max_interval) * 60 - schedule_delay
                
                last_broadcast = self.last_broadcast_time.get(code_name)
                if last_broadcast and time.time() - last_broadcast < time_until_schedule:
                    await asyncio.sleep(time_until_schedule)

                messages_to_send = []
                for msg_data in code.messages:
                    msg = await self._fetch_messages(msg_data)
                    if msg:
                        messages_to_send.append(msg)
                
                if not messages_to_send:
                    continue

                chats = list(code.chats)
                random.shuffle(chats)
                msg_index = self.message_indices.get(code_name, 0)
                message_to_send = messages_to_send[msg_index % len(messages_to_send)]
                self.message_indices[code_name] = (msg_index + 1) % len(messages_to_send)

                schedule_time = datetime.now() + timedelta(seconds=schedule_delay)
                failed_chats = set()
                
                for chat_id in chats:
                    try:
                        await self._send_message(
                            chat_id, message_to_send, code.send_mode, schedule_time
                        )
                    except (ChatWriteForbiddenError, UserBannedInChannelError):
                        failed_chats.add(chat_id)
                    except Exception as e:
                        logger.error(f"Failed to send to chat {chat_id}: {str(e)}")
                
                if failed_chats:
                    code.chats -= failed_chats
                    self.save_config()
                    
                await asyncio.sleep(schedule_delay)
                self.last_broadcast_time[code_name] = time.time()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Critical error in broadcast loop {code_name}: {str(e)}")
                await asyncio.sleep(60)


@loader.tds
class BroadcastMod(loader.Module):
    """Модуль для рассылки сообщений."""

    strings = {
        "name": "Broadcast",
        "code_not_found": "Код рассылки '{}' не найден",
        "success": "Операция выполнена успешно: {}",
        "album_added": "Альбом добавлен в рассылку '{}'",
        "single_added": "Сообщение добавлено в рассылку '{}'",
        "specify_code": "Укажите код рассылки",
        "reply_to_message": "Ответьте на сообщение командой .addmsg кодовое_слово",
        "addmsg_usage": "Использование: .addmsg кодовое_слово",
        "all_stopped": "Все рассылки остановлены",
        "all_started": "Все рассылки запущены",
        "broadcast_stopped": "Рассылка '{}' остановлена",
        "broadcast_started": "Рассылка '{}' запущена",
        "broadcast_start_failed": "Не удалось запустить рассылку '{}'",
        "chat_usage": "Использование: .chat кодовое_слово id_чата",
        "chat_id_numeric": "ID чата должен быть числом",
        "chat_added": "Чат {} добавлен в {}",
        "chat_removed": "Чат {} удален из {}",
        "delcode_success": "Код рассылки '{}' удален",
        "delmsg_no_reply": "Ответьте на сообщение, которое хотите удалить",
        "delmsg_deleted": "Сообщение удалено",
        "delmsg_not_found": "Сообщение не найдено",
        "delmsg_index_usage": "Использование: .delmsg кодовое_слово индекс",
        "delmsg_index_numeric": "Индекс должен быть числом",
        "delmsg_invalid_index": "Неверный индекс",
        "interval_usage": "Использование: .interval кодовое_слово мин_минут макс_минут",
        "interval_numeric": "Интервал должен быть числом",
        "interval_invalid_range": "Некорректный интервал. Убедитесь, что минимальное значение 1, а максимальное 1440.",
        "interval_set": "Интервал для '{}' установлен: {}-{} минут",
        "no_codes": "Нет настроенных кодов рассылки",
        "sendmode_usage": "Использование: .sendmode <код> <режим>\nРежимы: auto (по умолчанию), normal (обычная отправка), forward (форвард)",
        "sendmode_invalid": "Неверный режим отправки. Доступные режимы: auto, normal, forward",
        "sendmode_set": "Режим отправки для '{}' установлен: {}",
        "wat_status": "Автоматическое управление чатами {}",
        "no_messages_in_code": "Нет сообщений в коде '{}'",
    }

    def __init__(self):
        self.manager = None
        self.wat_mode = False
        self.me_id = None
        self._periodic_task = None

    def save_broadcast_status(self):
        """Сохраняет статус запущенных рассылок."""

        broadcast_status = {
            code_name: True for code_name in self._manager.broadcast_tasks
        }
        self._manager.db.set("broadcast", "BroadcastStatus", broadcast_status)

    async def client_ready(self, client, db):
        """Инициализация при запуске."""
        self.manager = BroadcastManager(client, db)
        self.me_id = await client.get_me()
        self.me_id = self.me_id.id
        
        # Загружаем конфигурацию
        config_data = db.get("broadcast", "config", {})
        self.manager._load_config_from_dict(config_data)
        
        # Восстанавливаем активные рассылки
        broadcast_status = db.get("broadcast", "BroadcastStatus", {})
        for code_name in self.manager.codes:
            if broadcast_status.get(code_name):
                await self._start_broadcast(code_name)
        
        # Запускаем периодическую очистку
        self._periodic_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self):
        """Периодическая очистка ресурсов."""
        while True:
            try:
                await self.manager.cleanup_manager()
                # Очищаем неактивные коды из статуса
                broadcast_status = self.manager.db.get("broadcast", "BroadcastStatus", {})
                cleaned_status = {
                    k: v for k, v in broadcast_status.items() 
                    if k in self.manager.codes
                }
                if cleaned_status != broadcast_status:
                    self.manager.db.set("broadcast", "BroadcastStatus", cleaned_status)
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
            await asyncio.sleep(3600)  # Раз в час

    async def _start_broadcast(self, code_name: str) -> bool:
        """Запускает рассылку."""
        try:
            if code_name not in self.manager.broadcast_tasks:
                self.manager.broadcast_tasks[code_name] = asyncio.create_task(
                    self.manager._broadcast_loop(code_name)
                )
                broadcast_status = self.manager.db.get("broadcast", "BroadcastStatus", {})
                broadcast_status[code_name] = True
                self.manager.db.set("broadcast", "BroadcastStatus", broadcast_status)
                return True
        except Exception:
            logger.exception(f"Failed to start broadcast {code_name}")
        return False

    async def _stop_broadcast(self, code_name: str):
        """Останавливает рассылку."""
        if code_name in self.manager.broadcast_tasks:
            task = self.manager.broadcast_tasks.pop(code_name)
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            # Обновляем статус
            broadcast_status = self.manager.db.get("broadcast", "BroadcastStatus", {})
            if code_name in broadcast_status:
                del broadcast_status[code_name]
                self.manager.db.set("broadcast", "BroadcastStatus", broadcast_status)

    async def _check_and_adjust_message_index(self, code_name: str):
        """Проверяет и корректирует индекс сообщения для рассылки."""

        code = self._manager.config.codes.get(code_name)
        if not code or not code.chats:
            return

        chats_list = list(code.chats)
        if chats_list:
            chat_id = random.choice(chats_list)
            try:
                peer = await self._manager.client.get_input_entity(chat_id)
                scheduled_messages = await self._manager.client(
                    functions.messages.GetScheduledHistoryRequest(
                        peer=peer, hash=0
                    )
                )

                if not scheduled_messages.messages:
                    return

                for index, msg_data in enumerate(code.messages):
                    original_message = await self._manager._fetch_messages(
                        msg_data
                    )
                    if not original_message:
                        continue

                    def match_messages(orig, scheduled):
                        if orig.media and scheduled.media:
                            has_photo = hasattr(
                                orig.media, "photo"
                            ) and hasattr(scheduled.media, "photo")
                            has_document = hasattr(
                                orig.media, "document"
                            ) and hasattr(scheduled.media, "document")
                            if (
                                has_photo
                                and orig.media.photo.id
                                == scheduled.media.photo.id
                            ):
                                return True
                            if (
                                has_document
                                and orig.media.document.id
                                == scheduled.media.document.id
                            ):
                                return True
                            return False
                        return orig.text == scheduled.message

                    match = next(
                        (
                            msg
                            for msg in scheduled_messages.messages
                            if isinstance(original_message, list)
                            and hasattr(msg, "grouped_id")
                            and match_messages(original_message[0], msg)
                            or not isinstance(original_message, list)
                            and match_messages(original_message, msg)
                        ),
                        None,
                    )

                    if match:
                        self._manager.message_indices[code_name] = index
                        if hasattr(match, "date"):
                            self._manager._last_broadcast_time[code_name] = (
                                match.date.timestamp()
                            )
                        return
            except Exception:
                logger.warning(
                    f"Error checking scheduled messages for {code_name} in chat {chat_id}"
                )

    async def _validate_code(self, message: Message, code_name: Optional[str] = None) -> Optional[str]:
        """Проверяет существование кода рассылки."""
        args = utils.get_args(message)
        if code_name is None:
            if not args:
                await utils.answer(message, self.strings["specify_code"])
                return None
            code_name = args[0]
        if code_name not in self.manager.codes:
            await utils.answer(
                message,
                self.strings["code_not_found"].format(code_name)
            )
            return None
        return code_name

    async def addmsgcmd(self, message: Message):
        """Добавить сообщение в рассылку."""
        reply = await message.get_reply_message()
        if not reply:
            return await utils.answer(message, self.strings["reply_to_message"])
            
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, self.strings["addmsg_usage"])
            
        code_name = args[0]
        success = await self.manager.add_message(code_name, reply)
        
        await utils.answer(
            message,
            self.strings["album_added" if getattr(reply, "grouped_id", None) else "single_added"].format(code_name) 
            if success else "Не удалось добавить сообщение"
        )

    async def broadcastcmd(self, message: Message):
        """Управление рассылкой."""
        await self.manager.cleanup_manager()
        args = utils.get_args(message)
        
        if not args:
            # Управление всеми рассылками
            if self.manager.broadcast_tasks:
                for code_name in list(self.manager.broadcast_tasks.keys()):
                    await self._stop_broadcast(code_name)
                await utils.answer(message, self.strings["all_stopped"])
            else:
                success = True
                for code_name in self.manager.codes:
                    if not await self._start_broadcast(code_name):
                        success = False
                await utils.answer(
                    message, 
                    self.strings["all_started"] if success else "Не все рассылки удалось запустить"
                )
            return

        # Управление конкретной рассылкой
        code_name = args[0]
        if code_name not in self.manager.codes:
            return await utils.answer(
                message,
                self.strings["code_not_found"].format(code_name)
            )

        if code_name in self.manager.broadcast_tasks:
            await self._stop_broadcast(code_name)
            await utils.answer(
                message,
                self.strings["broadcast_stopped"].format(code_name)
            )
        else:
            if await self._start_broadcast(code_name):
                await utils.answer(
                    message,
                    self.strings["broadcast_started"].format(code_name)
                )
            else:
                await utils.answer(
                    message,
                    self.strings["broadcast_start_failed"].format(code_name)
                )

    async def chatcmd(self, message: Message):
        """Добавить/удалить чат из рассылки."""
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(message, self.strings["chat_usage"])
            
        try:
            code_name, chat_id = args[0], int(args[1])
        except ValueError:
            return await utils.answer(message, self.strings["chat_id_numeric"])
            
        code_name = await self._validate_code(message, code_name)
        if not code_name:
            return
            
        code = self.manager.codes[code_name]
        if chat_id in code.chats:
            code.chats.remove(chat_id)
            result = "removed"
        else:
            code.chats.add(chat_id)
            result = "added"
            
        self.manager.save_config()
        await utils.answer(
            message,
            self.strings[f"chat_{result}"].format(chat_id, code_name)
        )

    async def delcodecmd(self, message: Message):
        """Удалить код рассылки."""
        code_name = await self._validate_code(message)
        if not code_name:
            return

        await self._stop_broadcast(code_name)
        del self.manager.codes[code_name]
        self.manager.message_indices.pop(code_name, None)
        self.manager._message_cache.clear()
        self.manager.save_config()
        
        await utils.answer(
            message,
            self.strings["delcode_success"].format(code_name)
        )

    async def delmsgcmd(self, message: Message):
        """Удалить сообщение из рассылки."""
        code_name = await self._validate_code(message)
        if not code_name:
            return

        args = utils.get_args(message)
        reply = await message.get_reply_message()
        code = self.manager.codes[code_name]

        if reply:
            # Удаление по ответу на сообщение
            initial_len = len(code.messages)
            code.messages = [
                msg for msg in code.messages
                if not (msg.message_id == reply.id and msg.chat_id == reply.chat_id)
            ]
            if len(code.messages) < initial_len:
                self.manager._message_cache.clear()
                self.manager.save_config()
                await utils.answer(message, self.strings["delmsg_deleted"])
            else:
                await utils.answer(message, self.strings["delmsg_not_found"])
        elif len(args) == 2:
            # Удаление по индексу
            try:
                index = int(args[1]) - 1
                if 0 <= index < len(code.messages):
                    del code.messages[index]
                    self.manager._message_cache.clear()
                    self.manager.save_config()
                    await utils.answer(message, self.strings["delmsg_deleted"])
                else:
                    await utils.answer(message, self.strings["delmsg_invalid_index"])
            except ValueError:
                await utils.answer(message, self.strings["delmsg_index_numeric"])
        else:
            await utils.answer(message, self.strings["delmsg_index_usage"])

    async def intervalcmd(self, message: Message):
        """Изменить интервал рассылки."""
        args = utils.get_args(message)
        if len(args) != 3:
            return await utils.answer(message, self.strings["interval_usage"])
            
        code_name = await self._validate_code(message)
        if not code_name:
            return
            
        try:
            min_minutes, max_minutes = map(int, args[1:])
            if not (1 <= min_minutes < max_minutes <= 1440):
                return await utils.answer(message, self.strings["interval_invalid_range"])
                
            self.manager.codes[code_name].interval = (min_minutes, max_minutes)
            self.manager.save_config()
            
            await utils.answer(
                message,
                self.strings["interval_set"].format(code_name, min_minutes, max_minutes)
            )
        except ValueError:
            await utils.answer(message, self.strings["interval_numeric"])

    async def listcmd(self, message: Message):
        """Показать список рассылок."""
        if not self.manager.codes:
            return await utils.answer(message, self.strings["no_codes"])
            
        text = [
            "<b>Рассылка:</b>",
            f"🔄 Управление чатами: {'Включено' if self.wat_mode else 'Выключено'}\n",
            "<b>Коды рассылок:</b>",
        ]

        for code_name, code in self.manager.codes.items():
            chat_list = ", ".join(map(str, code.chats)) or "(пусто)"
            min_interval, max_interval = code.interval
            message_count = len(code.messages)
            running = code_name in self.manager.broadcast_tasks

            text.append(
                f"+ <code>{code_name}</code>:\n"
                f"  💬 Чаты: {chat_list}\n"
                f"  ⏱ Интервал: {min_interval} - {max_interval} минут\n"
                f"  📨 Сообщений: {message_count}\n"
                f"  📊 Статус: {'🟢 Работает' if running else '🔴 Остановлен'}\n"
            )
        await utils.answer(message, "\n".join(text))

    async def listmsgcmd(self, message: Message):
        """Команда для просмотра списка сообщений в определенном коде рассылки."""

        code_name = await self._validate_broadcast_code(message)
        if not code_name:
            return
        messages = self._manager.config.codes[code_name].messages
        if not messages:
            return await utils.answer(
                message, self.strings["no_messages_in_code"].format(code_name)
            )
        text = [f"<b>Сообщения в '{code_name}':</b>"]
        for i, msg in enumerate(messages, 1):
            try:
                chat_id = abs(msg.chat_id)
                base_link = f"t.me/c/{chat_id % 10**10}"

                if msg.grouped_id is not None:
                    album_links = ", ".join(
                        f"<a href='{base_link}/{album_id}'>{album_id}</a>"
                        for album_id in msg.album_ids
                    )
                    text.append(
                        f"{i}. Альбом в чате {msg.chat_id} (Изображений: {len(msg.album_ids)}):\n   {album_links}"
                    )
                else:
                    text.append(
                        f"{i}. Сообщение ID: {msg.message_id} в чате {msg.chat_id}:\n   <a href='{base_link}/{msg.message_id}'>{msg.message_id}</a>"
                    )
            except Exception as e:
                text.append(f"{i}. Ошибка получения информации: {e}")
        await utils.answer(message, "\n\n".join(text))

    async def sendmodecmd(self, message: Message):
        """Команда для изменения режима отправки сообщений."""

        args = utils.get_args(message)
        if len(args) != 2 or args[1] not in ["auto", "normal", "forward"]:
            return await utils.answer(message, self.strings["sendmode_usage"])
        code_name = await self._validate_broadcast_code(message)
        if not code_name:
            return
        mode = args[1]
        self._manager.config.codes[code_name].send_mode = mode
        self._manager.save_config()
        await utils.answer(
            message,
            self.strings["success"].format(
                self.strings["sendmode_set"].format(code_name, mode)
            ),
        )

    async def watcmd(self, message: Message):
        """Команда для включения/выключения автоматического добавления чатов в рассылку."""

        self._wat_mode = not self._wat_mode
        await utils.answer(
            message,
            self.strings["success"].format(
                self.strings["wat_status"].format(
                    "включено" if self._wat_mode else "выключено"
                )
            ),
        )

    async def watcher(self, message: Message):
        """Автоматически добавляет чаты в рассылку, если режим автоматического управления чатами включен."""

        if not isinstance(message, Message) or not self._wat_mode:
            return
        if message.sender_id == self._me_id and message.text:
            for code_name in self._manager.config.codes:
                if message.text.strip().endswith(code_name):
                    try:
                        code = self._manager.config.codes[code_name]
                        if message.chat_id not in code.chats:
                            code.chats.add(message.chat_id)
                            self._manager.save_config()
                        break
                    except Exception:
                        logger.error("Ошибка автодобавления чата")
