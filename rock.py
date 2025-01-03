import asyncio
from typing import Union, Optional, Dict, List, Tuple, Any, TypeVar, Generic
import logging
from collections import defaultdict
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Message, Channel, User, UserStatusOnline, UserStatusOffline, UserStatusRecently
from telethon.errors.rpcerrorlist import YouBlockedUserError, FloodWaitError, UserNotParticipantError
from telethon.errors.common import MultiError
from .. import loader, utils
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class Config:
    # Временные константы (в секундах)
    CLEANUP_INTERVAL: int = 300  # Интервал очистки кэша (5 минут)
    
    # Размеры кэша
    CACHE_SIZE: int = 500
    
    # Таймауты и задержки
    TIMEOUT: int = 1  # Базовый таймаут для всех операций
    
    # Количество попыток
    MAX_ATTEMPTS: int = 3     # Максимальное количество попыток для всех операций
    
    # Настройки ботов и логирования
    FUNSTAT_BOT: str = "@Suusbdj_bot"
    HISTORY_BOT: str = "@tgprofile_history_bot"
    
    # Базовые маркеры
    BASE_MARKERS: tuple = ("this is", "это")
    
    # Маркеры для обработки ответов
    ERROR_MARKERS: tuple = ("не найден", "not found", "error", "ошибка", "⚠️")
    VALID_RESPONSE_MARKERS: tuple = BASE_MARKERS
    SKIP_LINE_MARKERS: tuple = ("id:",) + BASE_MARKERS + ("usernames:", "имена пользователя:")
    
config = Config()

class AsyncCache(Generic[T]):
    def __init__(self, ttl: int, max_size: int = Config.CACHE_SIZE):
        self._cache: Dict[Any, Tuple[T, float]] = {}
        self._lock = asyncio.Lock()
        self._ttl = ttl
        self._max_size = max_size
        self._last_cleanup = time.time()
        self._cleanup_interval = Config.CLEANUP_INTERVAL
        
    async def _cleanup_cache(self):
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
            
        async with self._lock:
            # Очистка по TTL и размеру одновременно
            items = sorted(
                [(k, v, t) for k, (v, t) in self._cache.items()],
                key=lambda x: x[2]
            )
            
            # Удаляем устаревшие и оставляем только последние max_size элементов
            valid_items = [(k, v, t) for k, v, t in items if now - t < self._ttl]
            if valid_items:
                valid_items = valid_items[-self._max_size:]
                self._cache = {k: (v, t) for k, v, t in valid_items}
            else:
                self._cache.clear()
            self._last_cleanup = now
        
    async def get(self, key: Any) -> Optional[T]:
        try:
            async with self._lock:
                if key not in self._cache:
                    return None
                value, timestamp = self._cache[key]
                if time.time() - timestamp >= self._ttl:
                    del self._cache[key]
                    return None
                return value
        finally:
            if len(self._cache) > self._max_size or time.time() - self._last_cleanup >= self._cleanup_interval:
                asyncio.create_task(self._cleanup_cache())
            
    async def set(self, key: Any, value: T):
        async with self._lock:
            self._cache[key] = (value, time.time())
            if len(self._cache) > self._max_size:
                asyncio.create_task(self._cleanup_cache())

class RetryHandler:
    @staticmethod
    async def retry_with_delay(func, *args, max_retries=Config.MAX_ATTEMPTS, **kwargs):
        last_error = None
        for attempt in range(max_retries):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=Config.TIMEOUT
                )
            except (FloodWaitError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt == max_retries - 1:
                    raise
                if isinstance(e, FloodWaitError):
                    await asyncio.sleep(e.seconds)
                else:
                    # Ограничиваем максимальную задержку 5 секундами
                    delay = min(Config.TIMEOUT * (2 ** attempt), 5)
                    await asyncio.sleep(delay)
            except Exception as e:
                last_error = e
                if attempt == max_retries - 1:
                    raise
                # Ограничиваем максимальную задержку 5 секундами
                delay = min(Config.TIMEOUT * (2 ** attempt), 5)
                await asyncio.sleep(delay)
        raise last_error if last_error else RuntimeError("Превышено количество попыток")

class PhotoCache:
    _cache = AsyncCache[bytes](Config.CLEANUP_INTERVAL, max_size=200)
    _download_locks: Dict[int, asyncio.Lock] = defaultdict(lambda: asyncio.Lock())
    _last_used: Dict[int, float] = {}
    
    @classmethod
    async def get_or_download(cls, client, entity_id: int) -> Optional[bytes]:
        try:
            # Обновляем время последнего использования
            cls._last_used[entity_id] = time.time()
            
            if photo := await cls._cache.get(entity_id):
                return photo
                
            async with cls._download_locks[entity_id]:
                # Повторная проверка кэша после получения блокировки
                if photo := await cls._cache.get(entity_id):
                    return photo
                    
                photo = await RetryHandler.retry_with_delay(
                    client.download_profile_photo,
                    entity_id,
                    bytes
                )
                
                if photo:
                    await cls._cache.set(entity_id, photo)
                return photo
                    
        except asyncio.TimeoutError:
            logger.warning(f"Таймаут при загрузке фото для {entity_id}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при загрузке фото для {entity_id}: {e}", exc_info=True)
            return None
        finally:
            # Очищаем старые локи
            now = time.time()
            old_locks = [k for k, v in cls._last_used.items() if now - v > Config.CLEANUP_INTERVAL]
            for k in old_locks:
                cls._download_locks.pop(k, None)
                cls._last_used.pop(k, None)

@loader.tds
class UserInfoMod(loader.Module):
    """Модуль для получения информации о пользователе или канале"""
    
    strings = {
        "name": "UserInfo",
        "loading": "🕐 <b>Обработка данных...</b>",
        "not_found": "❗ Не удалось найти пользователя или канал",
        "unblock_bot": "❗ Разблокируйте funstat для получения информации",
        "error_fetching": "⚠️ Ошибка при получении данных: {}"
    }

    def __init__(self):
        self.name = self.strings["name"]
        self._funstat_cache = AsyncCache(Config.CLEANUP_INTERVAL, max_size=100)

    def _format_details(self, details: List[str]) -> List[str]:
        if not details:
            return []
        return [f"├ {detail}" for detail in details[:-1]] + [f"└ {details[-1]}"]

    def _format_status_flags(self, flags: List[str]) -> str:
        return f"⚜️ {' • '.join(flags)}\n" if flags else ""

    def _get_entity_flags(self, entity: Union[User, Channel]) -> List[str]:
        flags = []
        if getattr(entity, 'verified', False):
            flags.append("✅ Верифицирован")
        if getattr(entity, 'premium', False):
            flags.append("💎 Premium")
        if getattr(entity, 'scam', False):
            flags.append("⚠️ Скам")
        if isinstance(entity, User):
            if getattr(entity, 'bot', False):
                flags.append("🤖 Бот")
            if getattr(entity, 'deleted', False):
                flags.append("♻️ Удалён")
        return flags

    async def on_unload(self):
        pass

    async def get_funstat_info(self, user_id: int) -> str:
        """Получение информации о пользователе от funstat бота"""
        try:
            if cached_info := await self._funstat_cache.get(user_id):
                return cached_info

            chat = Config.FUNSTAT_BOT
            error_msg = "⚠️ Не удалось получить ответ от funstat"
            
            for attempt in range(Config.MAX_ATTEMPTS):
                try:
                    await self._client.send_message(chat, str(user_id))
                    await asyncio.sleep(Config.TIMEOUT)
                    
                    messages = await asyncio.wait_for(
                        self._client.get_messages(chat, limit=3),
                        timeout=Config.TIMEOUT
                    )
                    
                    found_valid_response = False
                    for msg in messages:
                        if not msg.text or str(user_id) not in msg.text:
                            continue
                            
                        text_lower = msg.text.lower()
                        
                        # Проверяем ошибки
                        if any(err in text_lower for err in Config.ERROR_MARKERS):
                            return "⚠️ Пользователь не найден в базе funstat"
                        
                        # Проверяем наличие маркеров корректного ответа
                        if any(marker in text_lower for marker in Config.VALID_RESPONSE_MARKERS):
                            found_valid_response = True
                            lines = []
                            for line in msg.text.split("\n"):
                                line = line.strip()
                                if not line or any(x in line.lower() for x in Config.SKIP_LINE_MARKERS) or "@" in line:
                                    continue
                                
                                if ":" in line:
                                    try:
                                        label, value = line.split(":", 1)
                                        value = value.strip().replace(",", "").replace(" ", "")
                                        if value.isdigit():
                                            value = f"{int(value):,}"
                                        lines.append(f"{label}: {value}")
                                    except Exception:
                                        continue
                                else:
                                    lines.append(line)
                            
                            if lines:
                                result = "\n".join(lines)
                                await self._funstat_cache.set(user_id, result)
                                return result
                    
                    # Если не нашли валидный ответ и есть еще попытки
                    if not found_valid_response and attempt < Config.MAX_ATTEMPTS - 1:
                        await asyncio.sleep(Config.TIMEOUT)
                        continue
                
                except YouBlockedUserError:
                    return self.strings["unblock_bot"]
                except FloodWaitError as e:
                    if attempt < Config.MAX_ATTEMPTS - 1:
                        await asyncio.sleep(e.seconds)
                        continue
                    raise
                except asyncio.TimeoutError:
                    if attempt < Config.MAX_ATTEMPTS - 1:
                        await asyncio.sleep(Config.TIMEOUT)
                        continue
                    return f"{error_msg} (таймаут)"
            
            return f"{error_msg} (все попытки исчерпаны)"
                    
        except Exception as e:
            logger.error(f"Ошибка при получении funstat: {e}", exc_info=True)
            return f"⚠️ Ошибка при получении статистики: {str(e)}"

    async def send_info_message(self, message: Message, entity: Union[User, Channel], info_text: str):
        try:
            photo = await PhotoCache.get_or_download(self._client, entity.id)
            await message.respond(info_text, file=photo if photo else None)
            await message.delete()
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}", exc_info=True)
            raise

    async def userinfocmd(self, message: Message):
        """Получить информацию о пользователе или канале
        Использование: .userinfo [@ или ID] или ответ на сообщение"""
        await utils.answer(message, self.strings["loading"])
        
        try:
            args = utils.get_args_raw(message)
            reply = await message.get_reply_message()
            
            if not args and not reply:
                await utils.answer(message, "❌ Укажите пользователя/канал или ответьте на сообщение")
                return
            
            entity = None
            try:
                entity_id = args or (reply.sender_id if reply else None)
                if not entity_id:
                    raise ValueError("Не указан ID")
                    
                entity = await self._client.get_entity(entity_id)
            except (ValueError, AttributeError) as e:
                logger.debug(f"Ошибка получения сущности: {e}")
                await utils.answer(message, self.strings["not_found"])
                return
                
            try:
                if isinstance(entity, Channel):
                    full_info = await self._client(GetFullChannelRequest(entity))
                    info_text = await self.format_channel_info(entity, full_info)
                else:
                    full_info = await self._client(GetFullUserRequest(entity))
                    info_text = await self.format_user_info(entity, full_info)
                    
                await self.send_info_message(message, entity, info_text)
                
            except UserNotParticipantError:
                await utils.answer(message, "⚠️ Нет доступа к информации")
            except MultiError as e:
                if any(isinstance(err, UserNotParticipantError) for err in e.exceptions):
                    await utils.answer(message, "⚠️ Нет доступа к информации")
                else:
                    raise
            except Exception as e:
                logger.error(f"Ошибка при получении информации: {e}", exc_info=True)
                await utils.answer(message, self.strings["error_fetching"].format(str(e)))
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды: {e}", exc_info=True)
            await utils.answer(message, self.strings["error_fetching"].format(str(e)))

    def _format_status(self, status) -> str:
        """Форматирование статуса пользователя"""
        if isinstance(status, UserStatusOnline):
            return "🟢 В сети"
        elif isinstance(status, UserStatusOffline):
            return f"⚫️ Был(а) {status.was_online.strftime('%d.%m.%Y %H:%M')}"
        elif isinstance(status, UserStatusRecently):
            return "🔵 Недавно"
        return "⚫️ Давно"

    async def get_account_creation_date(self, user_id: int) -> Optional[str]:
        """Получение даты создания аккаунта от tgprofile_history_bot"""
        try:
            chat = Config.HISTORY_BOT
            
            await self._client.send_message(chat, str(user_id))
            await asyncio.sleep(Config.TIMEOUT)
            
            messages = await self._client.get_messages(chat, limit=2)
            
            if len(messages) < 2 or not messages[1].text:
                return None
                
            second_message = messages[1].text
            if "Аккаунт создан" in second_message:
                # Извлекаем дату создания из второго сообщения
                creation_date = second_message.split("создан в ~")[1].strip()
                return creation_date
            
            return None
                    
        except YouBlockedUserError:
            return "❌ Разблокируйте бота @tgprofile_history_bot"
        except Exception as e:
            logger.error(f"Ошибка при получении даты создания: {e}", exc_info=True)
            return None

    async def format_user_info(self, user: User, full_user: GetFullUserRequest) -> str:
        """Форматирование информации о пользователе"""
        try:
            def add_section(title: str = "", *lines: str) -> None:
                if title:
                    info_parts.extend(["", f"{title}"])
                if lines:
                    info_parts.extend(lines)

            info_parts = []
            
            # Заголовок
            name = " ".join(filter(None, [user.first_name, user.last_name])) or "🚫"
            info_parts.append(f"👤 <b>{name}</b>")
            
            # Статусы
            status_flags = self._get_entity_flags(user)
            if status_flags:
                info_parts.append(self._format_status_flags(status_flags))
            
            # Детальная информация
            details = [
                f"🆔 ID: <code>{user.id}</code>",
                f"👥 Общие чаты: {full_user.full_user.common_chats_count}",
                f"⭐️ Статус: {self._format_status(user.status)}"
            ]
            
            # Получаем дату создания аккаунта
            creation_date = await self.get_account_creation_date(user.id)
            if creation_date:
                details.append(f"📅 Дата создания: {creation_date}")
            
            # Проверка звонков
            if hasattr(full_user.full_user, 'phone_calls_available'):
                calls_available = full_user.full_user.phone_calls_available and getattr(full_user.full_user, 'video_calls_available', False)
                details.append(f"📞 Звонки: {'✅' if calls_available else '❌'}")
                
            info_parts.extend(self._format_details(details))
            
            # Описание
            if full_user.full_user.about:
                add_section("📋 <b>О пользователе:</b>", f"<i>{full_user.full_user.about}</i>")
            
            # Ссылки
            links = [f"├ Permalink: <code>tg://user?id={user.id}</code>"]
            if user.username:
                links.append(f"└ Username: @{user.username}")
            else:
                links[0] = links[0].replace("├", "└")
            add_section("🔗 <b>Ссылки:</b>", *links)
            
            # Статистика
            funstat_info = await self.get_funstat_info(user.id)
            if funstat_info and not any(err in funstat_info.lower() for err in Config.ERROR_MARKERS):
                add_section("📊 <b>Статистика funstat:</b>", funstat_info)
            
            return "\n".join(info_parts)
            
        except Exception as e:
            logger.error(f"Ошибка при форматировании информации о пользователе: {e}", exc_info=True)
            return f"❌ Ошибка при форматировании информации: {str(e)}"

    async def format_channel_info(self, channel: Channel, full_channel: GetFullChannelRequest) -> str:
        """Форматирование информации о канале"""
        info_parts = []
        
        try:
            # Заголовок
            info_parts.append(f"📣 <b>{channel.title}</b>")
            
            # Статусы
            status_flags = self._get_entity_flags(channel)
            if status_flags:
                info_parts.append(self._format_status_flags(status_flags))
            
            # Детальная информация
            details = [
                f"🆔 ID: <code>{channel.id}</code>",
                f"📝 Username: @{channel.username or '🚫'}",
                f"👥 Подписчиков: {full_channel.full_chat.participants_count:,}"
            ]
            
            if full_channel.full_chat.slowmode_seconds:
                details.append(f"⏱ Медленный режим: {full_channel.full_chat.slowmode_seconds} сек.")
            if full_channel.full_chat.linked_chat_id:
                details.append(f"🔗 Связанный чат: {full_channel.full_chat.linked_chat_id}")
            
            if full_channel.full_chat.online_count:
                details.append(f"🟢 Онлайн: {full_channel.full_chat.online_count:,}")
            
            if full_channel.full_chat.messages_count:
                details.append(f"💬 Сообщений: {full_channel.full_chat.messages_count:,}")
                
            details.append(f"📂 Тип: {self._get_channel_type(channel)}")
            
            info_parts.extend(self._format_details(details))
            
            # Описание
            if full_channel.full_chat.about:
                info_parts.extend([
                    "",
                    "📋 <b>Описание:</b>",
                    f"<i>{full_channel.full_chat.about}</i>"
                ])
            
            # Ссылки
            links = []
            if channel.username:
                links.append(f"├ Канал: https://t.me/{channel.username}")
            if full_channel.full_chat.invite_link:
                links.append(f"└ Приглашение: {full_channel.full_chat.invite_link}")
                
            if links:
                info_parts.extend([
                    "",
                    "🔗 <b>Ссылки:</b>",
                    *links
                ])
            
            # Возможности
            features = []
            if channel.signatures:
                features.append("✍️ Подписи авторов")
            if channel.has_link:
                features.append("🔗 Публичные ссылки")
            
            if features:
                info_parts.extend([
                    "",
                    "⚙️ <b>Возможности:</b>",
                    " • ".join(features)
                ])
            
            return "\n".join(info_parts)
            
        except Exception as e:
            logger.error(f"Ошибка при форматировании информации о канале: {e}", exc_info=True)
            return f"❌ Ошибка при форматировании информации: {str(e)}"

    def _get_channel_type(self, channel: Channel) -> str:
        """Определение типа канала"""
        if channel.megagroup:
            return "Супергруппа"
        elif channel.gigagroup:
            return "Broadcast группа"
        elif channel.broadcast:
            return "Канал"
        return "Группа"