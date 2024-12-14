import asyncio
import bisect
import logging
import random
import time
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Union, Any
from datetime import datetime, timedelta

from telethon import TelegramClient, functions
from telethon.errors import ChatWriteForbiddenError, UserBannedInChannelError
from telethon.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)


@dataclass
class BroadcastMessage:
    """
    chat_id (int): ID чата, в котором находится сообщение.
    message_id (int): ID сообщения.
    grouped_id (Optional[int]): ID группы, если сообщение является частью альбома.
    album_ids (List[int]): Список ID сообщений, входящих в альбом.
    """

    chat_id: int
    message_id: int
    grouped_id: Optional[int] = None
    album_ids: List[int] = field(default_factory=list)


@dataclass
class BroadcastCode:
    """
    chats (Set[int]): Множество ID чатов, куда будет производиться рассылка.
    messages (List[BroadcastMessage]): Список сообщений для рассылки.
    interval (Tuple[int, int]): Интервал задержки между рассылками (мин. и макс. значения в минутах).
    send_mode (str): Режим отправки сообщений ("auto", "normal", "forward").
    """

    chats: Set[int] = field(default_factory=set)
    messages: List[BroadcastMessage] = field(default_factory=list)
    interval: Tuple[int, int] = field(default_factory=lambda: (1, 13))
    send_mode: str = "auto"


class BroadcastConfig:
    """
    codes (Dict[str, BroadcastCode]): Словарь, хранящий конфигурации рассылок, где ключ - название кода, а значение - BroadcastCode.
    _lock (asyncio.Lock): Асинхронная блокировка для обеспечения потокобезопасного доступа к данным.
    """

    def __init__(self):
        """Инициализирует конфигурацию рассылки."""
        self.codes: Dict[str, BroadcastCode] = {}
        self._lock = asyncio.Lock()

    async def add_code(self, code_name: str) -> None:
        """Добавляет новый код рассылки, если он еще не существует."""
        async with self._lock:
            self.codes.setdefault(code_name, BroadcastCode())

    async def remove_code(self, code_name: str) -> bool:
        """Удаляет код рассылки."""
        async with self._lock:
            return bool(self.codes.pop(code_name, None))


class BroadcastManager:
    """
    client (TelegramClient): Клиент Telethon для взаимодействия с Telegram API.
    db: Объект базы данных для хранения конфигурации.
    config (BroadcastConfig): Объект конфигурации рассылок.
    broadcast_tasks (Dict[str, asyncio.Task]): Словарь задач рассылки, где ключ - название кода.
    message_indices (Dict[str, int]): Словарь для хранения индексов текущих сообщений для каждого кода.
    _active (bool): Флаг, определяющий активность менеджера рассылок.
    _last_broadcast_time (Dict[str, float]): Словарь для хранения времени последней рассылки для каждого кода.
    _scheduled_messages (Dict[str, Set[int]]): Словарь для хранения ID запланированных сообщений для каждого кода, чтобы избегать дублирования.
    """

    def __init__(self, client: TelegramClient, db):
        """Инициализирует менеджер рассылок."""
        self.client = client
        self.db = db
        self.config = BroadcastConfig()
        self.broadcast_tasks: Dict[str, asyncio.Task] = {}
        self.message_indices: Dict[str, int] = {}
        self._active = True
        self._last_broadcast_time: Dict[str, float] = {}
        self._scheduled_messages: Dict[str, Set[int]] = {}

    def _load_config_from_dict(self, data: dict):
        """Загружает конфигурацию рассылок из словаря."""
        for code_name, code_data in data.get("code_chats", {}).items():
            try:
                chats = {int(chat_id) for chat_id in code_data.get("chats", [])}
                messages = [
                    BroadcastMessage(
                        chat_id=int(msg_data["chat_id"]),
                        message_id=int(msg_data["message_id"]),
                        grouped_id=msg_data.get("grouped_id"),
                        album_ids=msg_data.get("album_ids", []),
                    )
                    for msg_data in code_data.get("messages", [])
                ]
                interval = tuple(code_data.get("interval", (1, 13)))

                broadcast_code = BroadcastCode(
                    chats=chats,
                    messages=messages,
                    interval=(
                        interval
                        if 0 < interval[0] < interval[1] <= 1440
                        else (3, 13)
                    ),
                    send_mode=code_data.get("send_mode", "auto"),
                )
                self.config.codes[code_name] = broadcast_code
            except Exception as e:
                logger.error(f"Error loading broadcast code {code_name}: {e}")

    def save_config(self):
        """Сохраняет текущую конфигурацию рассылок в базу данных."""
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
                                "album_ids": msg.album_ids,
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
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    async def _fetch_messages(
        self, msg_data: BroadcastMessage
    ) -> Union[Message, List[Message], None]:
        """Получает сообщение или альбом сообщений из Telegram API."""
        try:
            if msg_data.grouped_id is not None:
                messages = []
                for msg_id in msg_data.album_ids:
                    msg = await self.client.get_messages(
                        msg_data.chat_id, ids=msg_id
                    )
                    if msg:
                        messages.append(msg)
                return messages if messages else None
            else:
                return await self.client.get_messages(
                    msg_data.chat_id, ids=msg_data.message_id
                )
        except Exception as e:
            logger.error(f"Failed to fetch message: {e}")
            return None

    async def add_message(self, code_name: str, message: Message) -> bool:
        """Добавляет сообщение или альбом сообщений в рассылку."""
        try:
            await self.config.add_code(code_name)
            code = self.config.codes[code_name]
            grouped_id = getattr(message, "grouped_id", None)

            if grouped_id:
                album_messages = [message]
                async for album_msg in self.client.iter_messages(
                    message.chat_id, limit=10, offset_date=message.date
                ):
                    if (
                        hasattr(album_msg, "grouped_id")
                        and album_msg.grouped_id == message.grouped_id
                    ):
                        album_messages.append(album_msg)
                bisect.insort(album_messages, key=lambda m: m.id)
                msg_data = BroadcastMessage(
                    chat_id=message.chat_id,
                    message_id=message.id,
                    grouped_id=grouped_id,
                    album_ids=[msg.id for msg in album_messages],
                )
            else:
                msg_data = BroadcastMessage(
                    chat_id=message.chat_id, message_id=message.id
                )
            code.messages.append(msg_data)
            self.save_config()
            return True
        except Exception as e:
            logger.error(f"Failed to add message: {str(e)}")
            return False

    async def _check_existing_scheduled_messages(self, code_name: str):
        """Проверяет наличие запланированных сообщений для данного кода рассылки, чтобы избежать дубликатов."""
        try:
            # Используем peer с правильным способом получения

            peer = await self.client.get_input_entity(self.client.tg_id)

            # Получаем запланированные сообщения

            scheduled_messages = await self.client(
                functions.messages.GetScheduledHistoryRequest(peer=peer, hash=0)
            )

            # Безопасная проверка сообщений

            code_scheduled_ids = {
                msg.id
                for msg in scheduled_messages.messages
                if hasattr(msg, "message")
                and msg.message
                and code_name in msg.message
            }

            self._scheduled_messages[code_name] = code_scheduled_ids
        except Exception as e:
            logger.error(
                f"Failed to check scheduled messages for {code_name}: {e}"
            )
            self._scheduled_messages[code_name] = set()

    async def _send_message(
        self,
        chat_id: int,
        message_to_send: Union[Message, List[Message]],
        send_mode: str = "auto",
        code_name: Optional[str] = None,
        interval: Optional[float] = None,
    ):
        """Отправляет сообщение в указанный чат."""
        try:
            code_name = code_name or "default"

            if code_name not in self._scheduled_messages:
                await self._check_existing_scheduled_messages(code_name)

            async def _schedule_message(entity, messages, schedule_time):
                async def _send_single_message(entity, message):
                    if send_mode == "forward" or (
                        send_mode == "auto" and message.media
                    ):
                        return await self.client.forward_messages(
                            entity=entity,
                            messages=[message.id],
                            from_peer=message.chat_id,
                            schedule=schedule_time,
                        )
                    if message.media:
                        return await self.client.send_file(
                            entity=entity,
                            file=message.media,
                            caption=message.text,
                            schedule=schedule_time,
                        )
                    return await self.client.send_message(
                        entity=entity,
                        message=message.text,
                        schedule=schedule_time,
                    )

                if isinstance(messages, list) and len(messages) > 1:
                    return await self.client.forward_messages(
                        entity=chat_id,
                        messages=[m.id for m in messages],
                        from_peer=messages[0].chat_id,
                        schedule=schedule_time,
                    )
                message = (
                    messages[0] if isinstance(messages, list) else messages
                )
                return await _send_single_message(chat_id, message)

            base_delay = (
                random.choice([60, 120, 180])
                if interval and interval > 60
                else (interval or 60)
            )

            schedule_time = datetime.now() + timedelta(seconds=base_delay)

            await _schedule_message(chat_id, message_to_send, schedule_time)
        except (ChatWriteForbiddenError, UserBannedInChannelError) as e:
            logger.info(f"Cannot send message to {chat_id}: {e}")
            raise

    async def _broadcast_loop(self, code_name: str):
        """Основной цикл рассылки для конкретного кода."""
        while self._active:
            try:
                code = self.config.codes.get(code_name)
                if not code or not code.chats:
                    continue

                interval = random.uniform(
                    code.interval[0] * 58, code.interval[1] * 59
                )

                current_time = time.time()
                last_broadcast = self._last_broadcast_time.get(code_name, 0)

                if current_time - last_broadcast < interval:
                    continue

                await asyncio.sleep(interval)

                messages = [
                    await self._fetch_messages(msg_data)
                    for msg_data in code.messages
                ]
                messages = [m for m in messages if m]

                if not messages:
                    continue

                chats = list(code.chats)
                random.shuffle(chats)

                message_index = self.message_indices.get(code_name, 0)
                messages_to_send = messages[message_index % len(messages)]
                self.message_indices[code_name] = (message_index + 1) % len(
                    messages
                )

                send_mode = getattr(code, "send_mode", "auto")

                failed_chats = set()
                for chat_id in chats:
                    try:
                        await self._send_message(
                            chat_id,
                            messages_to_send,
                            send_mode,
                            code_name,
                            interval,
                        )
                    except Exception as send_error:
                        logger.error(
                            f"Sending error to {chat_id}: {send_error}"
                        )
                        failed_chats.add(chat_id)
                if failed_chats:
                    code.chats -= failed_chats
                    self.save_config()
                self._last_broadcast_time[code_name] = time.time()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Critical error in broadcast loop {code_name}: {e}"
                )

    async def start_broadcasts(self):
        """Запускает все настроенные рассылки."""
        for code_name in self.config.codes:
            if code_name not in self.broadcast_tasks:
                try:
                    self.broadcast_tasks[code_name] = asyncio.create_task(
                        self._broadcast_loop(code_name)
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to start broadcast loop for {code_name}: {e}"
                    )


@loader.tds
class BroadcastMod(loader.Module):
    """Профессиональный модуль массовой рассылки сообщений с расширенным управлением."""

    strings = {
        "name": "Broadcast",
        "code_not_found": "Код рассылки '{}' не найден",
        "success": "Операция выполнена успешно: {}",
        "album_added": "Альбом добавлен в рассылку '{}'",
        "single_added": "Сообщение добавлено в рассылку '{}'",
    }

    def __init__(self):
        """Инициализация модуля."""
        self._manager: Optional[BroadcastManager] = None
        self._wat_mode = False
        self._last_broadcast_check: float = 0
        self._me_id: Optional[int] = None

    async def client_ready(self, client: TelegramClient, db: Any):
        """Вызывается при готовности клиента, инициализирует менеджер рассылок."""
        self._manager = BroadcastManager(client, db)
        self._manager._load_config_from_dict(
            db.get("broadcast", "Broadcast", {})
        )
        self._me_id = client.tg_id

    async def _validate_broadcast_code(
        self, message: Message, code_name: Optional[str] = None
    ) -> Optional[str]:
        """Проверяет и возвращает код рассылки."""
        args = utils.get_args(message)

        if code_name is None:
            if not args:
                await utils.answer(message, "Укажите код рассылки")
                return None
            code_name = args[0]
        if code_name not in self._manager.config.codes:
            await utils.answer(
                message, self.strings["code_not_found"].format(code_name)
            )
            return None
        return code_name

    async def addmsgcmd(self, message: Message):
        """Команда для добавления сообщения в рассылку."""
        reply = await message.get_reply_message()
        if not reply:
            return await utils.answer(
                message, "Ответьте на сообщение командой .addmsg <код>"
            )
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Использование: .addmsg <код>")
        code_name = args[0]
        success = await self._manager.add_message(code_name, reply)

        if success:
            await utils.answer(
                message,
                (
                    self.strings["album_added"].format(code_name)
                    if getattr(reply, "grouped_id", None)
                    else self.strings["single_added"].format(code_name)
                ),
            )
        else:
            await utils.answer(message, "Не удалось добавить сообщение")

    async def chatcmd(self, message: Message):
        """Команда для добавления или удаления чата из рассылки."""
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(
                message, "Использование: .chat <код> <id_чата>"
            )
        try:
            code_name, chat_id = args[0], int(args[1])
        except ValueError:
            return await utils.answer(message, "ID чата должен быть числом")
        code_name = await self._validate_broadcast_code(message, code_name)
        if not code_name:
            return
        try:
            code = self._manager.config.codes[code_name]

            if chat_id in code.chats:
                code.chats.remove(chat_id)
                action = "удален"
            else:
                code.chats.add(chat_id)
                action = "добавлен"
            self._manager.save_config()
            await utils.answer(message, f"Чат {chat_id} {action} в {code_name}")
        except Exception as e:
            await utils.answer(message, f"Ошибка: {str(e)}")

    async def delcodecmd(self, message: Message):
        """Команда для удаления кода рассылки."""
        code_name = await self._validate_broadcast_code(message)
        if not code_name:
            return
        if code_name in self._manager.broadcast_tasks:
            task = self._manager.broadcast_tasks.pop(code_name)
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await self._manager.config.remove_code(code_name)

        self._manager.cached_messages.pop(code_name, None)
        self._manager.message_indices.pop(code_name, None)

        self._manager.save_config()

        await utils.answer(
            message,
            self.strings["success"].format(
                f"Код рассылки '{code_name}' удален"
            ),
        )

    async def delmsgcmd(self, message: Message):
        """Команда для удаления сообщения из рассылки."""
        args = utils.get_args(message)
        code_name = await self._validate_broadcast_code(message)
        if not code_name:
            return
        reply = await message.get_reply_message()

        if len(args) == 1 and reply:
            code = self._manager.config.codes[code_name]
            matching_messages = [
                idx
                for idx, msg in enumerate(code.messages)
                if msg.message_id == reply.id and msg.chat_id == reply.chat_id
            ]

            if matching_messages:
                del code.messages[matching_messages[0]]
                self._manager.save_config()
                await utils.answer(message, "Сообщение удалено")
            else:
                await utils.answer(message, "Сообщение не найдено")
        elif len(args) == 2:
            try:
                index = int(args[1]) - 1
                code = self._manager.config.codes[code_name]

                if 0 <= index < len(code.messages):
                    del code.messages[index]
                    self._manager.save_config()
                    await utils.answer(message, "Сообщение удалено")
                else:
                    await utils.answer(message, "Неверный индекс")
            except ValueError:
                await utils.answer(message, "Индекс должен быть числом")

    async def intervalcmd(self, message: Message):
        """Команда для установки интервала рассылки."""
        args = utils.get_args(message)
        if len(args) != 3:
            return await utils.answer(
                message,
                "Использование: .interval <код> <мин_минут> <макс_минут>",
            )
        code_name, min_str, max_str = args
        code_name = await self._validate_broadcast_code(message, code_name)
        if not code_name:
            return
        try:
            min_minutes, max_minutes = map(int, (min_str, max_str))

            if not (0 < min_minutes < max_minutes <= 1440):
                await utils.answer(message, "Некорректный интервал")
                return
            code = self._manager.config.codes[code_name]
            code.interval = (min_minutes, max_minutes)
            self._manager.save_config()

            await utils.answer(
                message,
                self.strings["success"].format(
                    f"Интервал для '{code_name}' установлен: {min_minutes}-{max_minutes} минут"
                ),
            )
        except ValueError:
            await utils.answer(message, "Интервал должен быть числом")

    async def listcmd(self, message: Message):
        """Команда для получения информации о рассылках."""
        if not self._manager.config.codes:
            return await utils.answer(message, "Нет настроенных кодов рассылки")
        text = [
            "**Рассылка:**",
            f"🔄 Управление чатами: {'Включено' if self._wat_mode else 'Выключено'}\n",
            "**Коды рассылок:**",
        ]

        for code_name, code in self._manager.config.codes.items():
            chat_list = ", ".join(map(str, code.chats)) or "(пусто)"
            min_interval, max_interval = code.interval
            message_count = len(code.messages)
            running = code_name in self._manager.broadcast_tasks

            text.append(
                f"- `{code_name}`:\n"
                f"  💬 Чаты: {chat_list}\n"
                f"  ⏱ Интервал: {min_interval} - {max_interval} минут\n"
                f"  📨 Сообщений: {message_count}\n"
                f"  📊 Статус: {'🟢 Работает' if running else '🔴 Остановлен'}\n"
            )
        await utils.answer(message, "\n".join(text))

    async def listmsgcmd(self, message: Message):
        """Команда для получения списка сообщений в коде рассылки."""
        code_name = await self._validate_broadcast_code(message)
        if not code_name:
            return
        messages = self._manager.config.codes[code_name].messages
        if not messages:
            return await utils.answer(
                message, f"Нет сообщений в коде '{code_name}'"
            )
        text = [f"**Сообщения в '{code_name}':**"]
        for i, msg in enumerate(messages, 1):
            try:
                chat_id = int(str(abs(msg.chat_id))[-10:])

                if msg.grouped_id is not None:
                    message_text = f"{i}. Альбом в чате {msg.chat_id} (Всего изображений: {len(msg.album_ids)})"
                    message_links = [
                        f"t.me/c/{chat_id}/{album_id}"
                        for album_id in msg.album_ids
                    ]
                    message_text += f"\nСсылки: {' , '.join(message_links)}"
                else:
                    message_text = f"{i}. Сообщение в чате {msg.chat_id}\n"
                    message_text += f"Ссылка: t.me/c/{chat_id}/{msg.message_id}"
                text.append(message_text)
            except Exception as e:
                text.append(f"{i}. Ошибка получения информации: {str(e)}")
        await utils.answer(message, "\n\n".join(text))

    async def sendmodecmd(self, message: Message):
        """Команда для установки режима отправки сообщений."""
        args = utils.get_args(message)
        if len(args) != 2 or args[1] not in ["auto", "normal", "forward"]:
            return await utils.answer(
                message,
                "Использование: .sendmode <код> <режим>\n"
                "Режимы: auto (по умолчанию), normal (обычная отправка), forward (форвард)",
            )
        code_name, mode = args
        code_name = await self._validate_broadcast_code(message, code_name)
        if not code_name:
            return
        code = self._manager.config.codes[code_name]
        code.send_mode = mode
        self._manager.save_config()

        await utils.answer(
            message,
            self.strings["success"].format(
                f"Режим отправки для '{code_name}' установлен: {mode}"
            ),
        )

    async def watcmd(self, message: Message):
        """Команда для переключения автоматического управления чатами."""
        self._wat_mode = not self._wat_mode
        await utils.answer(
            message,
            self.strings["success"].format(
                f"Автоматическое управление чатами {'включено' if self._wat_mode else 'выключено'}"
            ),
        )

    async def watcher(self, message: Message):
        """Наблюдатель сообщений для автоматического управления чатами."""
        if not isinstance(message, Message):
            return
        current_time = time.time()
        if current_time - self._last_broadcast_check >= 600:
            self._last_broadcast_check = current_time
            await self._manager.start_broadcasts()
        if (
            self._wat_mode
            and message.sender_id == self._me_id
            and message.text
            and message.text.strip()
        ):
            for code_name in self._manager.config.codes:
                if message.text.strip().endswith(code_name):
                    try:
                        code = self._manager.config.codes[code_name]
                        code.chats.add(message.chat_id)
                        self._manager.save_config()
                        break
                    except Exception as e:
                        logger.error(f"Ошибка автодобавления чата: {e}")
