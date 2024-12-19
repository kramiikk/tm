import asyncio
import logging
import random
import time
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Union, Any
from ratelimit import limits, sleep_and_retry
from datetime import datetime, timedelta

from telethon import TelegramClient, functions
from telethon.errors import ChatWriteForbiddenError, UserBannedInChannelError
from telethon.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BroadcastMessage:
    """Сообщение для рассылки."""

    chat_id: int
    message_id: int
    grouped_id: Optional[int] = None
    album_ids: Tuple[int, ...] = field(default_factory=tuple)


@dataclass
class BroadcastCode:
    """Набор настроек для рассылки."""

    chats: Set[int] = field(default_factory=set)
    messages: List[BroadcastMessage] = field(default_factory=list)
    interval: Tuple[int, int] = field(default_factory=lambda: (10, 13))
    send_mode: str = "auto"

    def is_valid_interval(self) -> bool:
        """Проверяет корректность интервала."""
        min_val, max_val = self.interval
        return (
            isinstance(min_val, int)
            and isinstance(max_val, int)
            and 0 < min_val < max_val <= 1440
        )

    def normalize_interval(self) -> Tuple[int, int]:
        """Нормализует интервал, если он некорректный."""
        return self.interval if self.is_valid_interval() else (10, 13)


class BroadcastConfig:
    """Управляет конфигурацией рассылки, хранит все коды рассылок."""

    def __init__(self):
        self.codes: Dict[str, BroadcastCode] = {}
        self._lock = asyncio.Lock()

    async def add_code(self, code_name: str) -> None:
        """Добавляет новый код рассылки, если он не существует."""
        async with self._lock:
            if code_name not in self.codes:
                self.codes[code_name] = BroadcastCode()

    async def remove_code(self, code_name: str) -> bool:
        """Удаляет код рассылки."""
        async with self._lock:
            return self.codes.pop(code_name, None) is not None


class BroadcastManager:
    """Управляет рассылками, хранит и обрабатывает информацию о рассылках."""

    def __init__(self, client: TelegramClient, db):
        """Инициализирует менеджер рассылок."""
        self.client = client
        self.db = db
        self.config = BroadcastConfig()
        self.broadcast_tasks: Dict[str, asyncio.Task] = {}
        self.message_indices: Dict[str, int] = {}
        self._active = True
        self._last_broadcast_time: Dict[str, float] = {}
        self._message_cache: Dict[
            Tuple[int, int], Union[Message, List[Message]]
        ] = {}

    def _create_broadcast_code_from_dict(
        self, code_data: dict
    ) -> BroadcastCode:
        """Создает объект BroadcastCode из словаря."""
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
        """Загружает конфигурацию рассылки из словаря."""
        for code_name, code_data in data.get("code_chats", {}).items():
            try:
                self.config.codes[code_name] = (
                    self._create_broadcast_code_from_dict(code_data)
                )
            except Exception:
                logger.exception(f"Error loading broadcast code {code_name}")

    def save_config(self):
        """Сохраняет текущую конфигурацию рассылки в базу данных."""
        try:
            config_dict = {
                "code_chats": {
                    code_name: {
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
                    for code_name, code in self.config.codes.items()
                }
            }
            self.db.set("broadcast", "Broadcast", config_dict)
        except Exception:
            logger.exception("Failed to save config")

    async def _fetch_messages(
        self, msg_data: BroadcastMessage
    ) -> Optional[Union[Message, List[Message]]]:
        """Получает сообщение или список сообщений из Telegram, используя кэш."""
        cache_key = (msg_data.chat_id, msg_data.message_id)
        if cache_key in self._message_cache:
            return self._message_cache[cache_key]

        try:
            if msg_data.grouped_id is not None:
                messages = await self.client.get_messages(
                    msg_data.chat_id, ids=list(msg_data.album_ids)
                )
                if messages:
                    for msg in messages:
                        self._message_cache[(msg_data.chat_id, msg.id)] = msg
                    return messages
            else:
                message = await self.client.get_messages(
                    msg_data.chat_id, ids=msg_data.message_id
                )
                if message:
                    self._message_cache[cache_key] = message
                    return message
        except Exception:
            logger.exception("Failed to fetch message")
        return None

    async def add_message(self, code_name: str, message: Message) -> bool:
        """Добавляет сообщение в список рассылки."""
        try:
            await self.config.add_code(code_name)
            code = self.config.codes[code_name]
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
                    chat_id=message.chat_id, message_id=message.id
                )

            code.messages.append(msg_data)
            self.save_config()
            return True
        except Exception:
            logger.exception("Failed to add message")
            return False

    @sleep_and_retry
    @limits(calls=1, period=1)
    async def _send_message(
        self,
        chat_id: int,
        message_to_send: Union[Message, List[Message]],
        send_mode: str = "auto",
        schedule_time: Optional[datetime] = None,
    ):
        """Отправляет сообщение в указанный чат."""
        try:
            if isinstance(message_to_send, list):
                await self.client.forward_messages(
                    entity=chat_id,
                    messages=[m.id for m in message_to_send],
                    from_peer=message_to_send[0].chat_id,
                    schedule=schedule_time,
                )
            elif message_to_send.media and send_mode != "normal":
                await self.client.forward_messages(
                    entity=chat_id,
                    messages=[message_to_send.id],
                    from_peer=message_to_send.chat_id,
                    schedule=schedule_time,
                )
            else:
                await self.client.send_message(
                    entity=chat_id,
                    message=message_to_send.text,
                    schedule=schedule_time,
                )
        except (ChatWriteForbiddenError, UserBannedInChannelError) as e:
            logger.warning(f"Cannot send message to {chat_id}: {e}")
        except Exception:
            logger.exception(f"Error sending message to {chat_id}")
            raise

    async def _broadcast_loop(self, code_name: str):
        """Бесконечный цикл рассылки сообщений."""
        while self._active:
            try:
                code = self.config.codes.get(code_name)
                if not code or not code.chats or not code.messages:
                    await asyncio.sleep(60)
                    continue

                start_time = time.time()
                min_interval, max_interval = code.normalize_interval()
                interval_sec = random.uniform(
                    min_interval * 60, max_interval * 60
                )

                last_broadcast = self._last_broadcast_time.get(code_name, 0)
                time_since_last_broadcast = start_time - last_broadcast
                if time_since_last_broadcast < interval_sec:
                    await asyncio.sleep(
                        interval_sec - time_since_last_broadcast
                    )
                    continue

                messages_to_send = [
                    msg
                    for msg in [
                        await self._fetch_messages(msg_data)
                        for msg_data in code.messages
                    ]
                    if msg
                ]
                if not messages_to_send:
                    await asyncio.sleep(60)
                    continue

                chats = list(code.chats)
                random.shuffle(chats)
                message_index = self.message_indices.get(code_name, 0)
                message_to_send = messages_to_send[
                    message_index % len(messages_to_send)
                ]
                self.message_indices[code_name] = (message_index + 1) % len(
                    messages_to_send
                )

                send_tasks = [
                    self._send_message(chat_id, message_to_send, code.send_mode)
                    for chat_id in chats
                ]
                results = await asyncio.gather(
                    *send_tasks, return_exceptions=True
                )

                failed_chats = {
                    chats[i]
                    for i, result in enumerate(results)
                    if isinstance(result, BaseException)
                }
                if failed_chats:
                    code.chats -= failed_chats
                    self.save_config()

                self._last_broadcast_time[code_name] = time.time()

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception(
                    f"Critical error in broadcast loop {code_name}"
                )
                await asyncio.sleep(60)

    async def start_broadcasts(self):
        """Запускает все активные рассылки."""
        for code_name in self.config.codes:
            if code_name not in self.broadcast_tasks:
                try:
                    self.broadcast_tasks[code_name] = asyncio.create_task(
                        self._broadcast_loop(code_name)
                    )
                except Exception:
                    logger.exception(
                        f"Failed to start broadcast loop for {code_name}"
                    )


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
        """Инициализация модуля."""
        self._manager: Optional[BroadcastManager] = None
        self._wat_mode = False
        self._me_id = None

    def save_broadcast_status(self):
        """Сохраняет статус запущенных рассылок."""
        broadcast_status = {
            code_name: True for code_name in self._manager.broadcast_tasks
        }
        self._manager.db.set("broadcast", "BroadcastStatus", broadcast_status)

    async def client_ready(self, client: TelegramClient, db: Any):
        """Выполняется при готовности клиента Telegram."""
        self._manager = BroadcastManager(client, db)
        self._me_id = client.tg_id

        config_data = db.get("broadcast", "Broadcast", {})
        self._manager._load_config_from_dict(config_data)

        broadcast_status = db.get("broadcast", "BroadcastStatus", {})

        for code_name in self._manager.config.codes:
            if (
                broadcast_status.get(code_name)
                and code_name not in self._manager.broadcast_tasks
            ):
                try:
                    await self._check_and_adjust_message_index(code_name)
                    self._manager.broadcast_tasks[code_name] = (
                        asyncio.create_task(
                            self._manager._broadcast_loop(code_name)
                        )
                    )
                except Exception:
                    logger.exception(
                        f"Не удалось восстановить рассылку {code_name}"
                    )

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

    async def _validate_broadcast_code(
        self, message: Message, code_name: Optional[str] = None
    ) -> Optional[str]:
        """Проверяет существование кода рассылки."""
        args = utils.get_args(message)
        if code_name is None:
            if not args:
                await utils.answer(message, self.strings["specify_code"])
                return None
            code_name = args[0]
        if code_name not in self._manager.config.codes:
            await utils.answer(
                message, self.strings["code_not_found"].format(code_name)
            )
            return None
        return code_name

    async def addmsgcmd(self, message: Message):
        """Команда добавления сообщения в рассылку."""
        reply = await message.get_reply_message()
        if not reply:
            return await utils.answer(message, self.strings["reply_to_message"])
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, self.strings["addmsg_usage"])
        code_name = args[0]
        success = await self._manager.add_message(code_name, reply)
        (
            await utils.answer(
                message,
                (
                    self.strings["album_added"].format(code_name)
                    if getattr(reply, "grouped_id", None)
                    else self.strings["single_added"].format(code_name)
                ),
            )
            if success
            else await utils.answer(message, "Не удалось добавить сообщение")
        )

    async def broadcastcmd(self, message: Message):
        """Команда управления рассылкой."""
        args = utils.get_args(message)
        if not args:
            if self._manager.broadcast_tasks:
                for code_name, task in list(
                    self._manager.broadcast_tasks.items()
                ):
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
                self._manager.broadcast_tasks.clear()
                self._manager.db.set("broadcast", "BroadcastStatus", {})
                await utils.answer(message, self.strings["all_stopped"])
            else:
                await self._manager.start_broadcasts()
                self.save_broadcast_status()
                await utils.answer(message, self.strings["all_started"])
        else:
            code_name = args[0]
            if code_name not in self._manager.config.codes:
                return await utils.answer(
                    message, self.strings["code_not_found"].format(code_name)
                )
            if code_name in self._manager.broadcast_tasks:
                task = self._manager.broadcast_tasks.pop(code_name)
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
                self._manager.db.set(
                    "broadcast",
                    "BroadcastStatus",
                    {
                        k: v
                        for k, v in self._manager.db.get(
                            "broadcast", "BroadcastStatus", {}
                        ).items()
                        if k != code_name
                    },
                )
                await utils.answer(
                    message, self.strings["broadcast_stopped"].format(code_name)
                )
            else:
                try:
                    self._manager.broadcast_tasks[code_name] = (
                        asyncio.create_task(
                            self._manager._broadcast_loop(code_name)
                        )
                    )
                    broadcast_status = self._manager.db.get(
                        "broadcast", "BroadcastStatus", {}
                    )
                    broadcast_status[code_name] = True
                    self._manager.db.set(
                        "broadcast", "BroadcastStatus", broadcast_status
                    )
                    await utils.answer(
                        message,
                        self.strings["broadcast_started"].format(code_name),
                    )
                except Exception:
                    logger.exception(
                        f"Failed to start broadcast loop for {code_name}"
                    )
                    await utils.answer(
                        message,
                        self.strings["broadcast_start_failed"].format(
                            code_name
                        ),
                    )

    async def chatcmd(self, message: Message):
        """Команда добавления/удаления чата из рассылки."""
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(message, self.strings["chat_usage"])
        try:
            code_name, chat_id = args[0], int(args[1])
        except ValueError:
            return await utils.answer(message, self.strings["chat_id_numeric"])
        code_name = await self._validate_broadcast_code(message, code_name)
        if not code_name:
            return
        code = self._manager.config.codes[code_name]
        action_str, method = (
            ("удален", code.chats.remove)
            if chat_id in code.chats
            else ("добавлен", code.chats.add)
        )
        method(chat_id)
        self._manager.save_config()
        await utils.answer(
            message,
            self.strings[
                f"chat_{'added' if action_str == 'добавлен' else 'removed'}"
            ].format(chat_id, code_name),
        )

    async def delcodecmd(self, message: Message):
        """Команда удаления кода рассылки."""
        code_name = await self._validate_broadcast_code(message)
        if not code_name:
            return
        if code_name in self._manager.broadcast_tasks:
            task = self._manager.broadcast_tasks.pop(code_name)
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await self._manager.config.remove_code(code_name)
        self._manager.message_indices.pop(code_name, None)
        self._manager._message_cache.clear()
        self._manager.save_config()
        await utils.answer(
            message,
            self.strings["success"].format(
                self.strings["delcode_success"].format(code_name)
            ),
        )

    async def delmsgcmd(self, message: Message):
        """Команда удаления сообщения из рассылки."""
        args = utils.get_args(message)
        code_name = await self._validate_broadcast_code(message)
        if not code_name:
            return
        reply = await message.get_reply_message()

        if reply:
            code = self._manager.config.codes[code_name]
            initial_len = len(code.messages)
            code.messages = [
                msg
                for msg in code.messages
                if not (
                    msg.message_id == reply.id and msg.chat_id == reply.chat_id
                )
            ]
            if len(code.messages) < initial_len:
                self._manager._message_cache.clear()
                self._manager.save_config()
                await utils.answer(message, self.strings["delmsg_deleted"])
            else:
                await utils.answer(message, self.strings["delmsg_not_found"])
        elif len(args) == 2:
            try:
                index = int(args[1]) - 1
                code = self._manager.config.codes[code_name]
                if 0 <= index < len(code.messages):
                    del code.messages[index]
                    self._manager._message_cache.clear()
                    self._manager.save_config()
                    await utils.answer(message, self.strings["delmsg_deleted"])
                else:
                    await utils.answer(
                        message, self.strings["delmsg_invalid_index"]
                    )
            except ValueError:
                await utils.answer(
                    message, self.strings["delmsg_index_numeric"]
                )
        else:
            await utils.answer(message, self.strings["delmsg_index_usage"])

    async def intervalcmd(self, message: Message):
        """Команда изменения интервала рассылки."""
        args = utils.get_args(message)
        if len(args) != 3:
            return await utils.answer(message, self.strings["interval_usage"])
        code_name = await self._validate_broadcast_code(message)
        if not code_name:
            return
        try:
            min_minutes, max_minutes = map(int, args[1:])
            if not (1 <= min_minutes < max_minutes <= 1440):
                return await utils.answer(
                    message, self.strings["interval_invalid_range"]
                )
            self._manager.config.codes[code_name].interval = (
                min_minutes,
                max_minutes,
            )
            self._manager.save_config()
            await utils.answer(
                message,
                self.strings["success"].format(
                    self.strings["interval_set"].format(
                        code_name, min_minutes, max_minutes
                    )
                ),
            )
        except ValueError:
            await utils.answer(message, self.strings["interval_numeric"])

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
