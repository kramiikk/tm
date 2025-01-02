import asyncio
from typing import Union, Optional, Dict, List, Tuple, Any, TypeVar, Generic
import aiohttp
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
    CACHE_TTL: int = 3600
    CACHE_SIZE: int = 500
    HTTP_TIMEOUT: int = 3
    FUNSTAT_TIMEOUT: int = 3  # Уменьшено для лучшей отзывчивости
    MAX_ATTEMPTS: int = 3
    RETRY_DELAY: int = 1
    FUNSTAT_BOT: str = "@Suusbdj_bot"
    LOG_LEVEL: int = logging.INFO
    PHOTO_CACHE_TTL: int = 1800
    MAX_RETRIES: int = 3
    REQUEST_TIMEOUT: int = 3  # Таймаут для запросов
    
config = Config()

class AsyncCache(Generic[T]):
    def __init__(self, ttl: int, max_size: int = 1000):
        self._cache: Dict[Any, Tuple[T, float]] = {}
        self._lock = asyncio.Lock()
        self._ttl = ttl
        self._max_size = max_size
        self._last_cleanup = time.time()
        self._cleanup_interval = 300
        
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
            valid_items = [(k, v, t) for k, v, t in items if now - t < self._ttl][-self._max_size:]
            self._cache = {k: (v, t) for k, v, t in valid_items}
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
    async def retry_with_delay(func, *args, max_retries=Config.MAX_RETRIES, **kwargs):
        last_error = None
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(Config.REQUEST_TIMEOUT):
                    return await func(*args, **kwargs)
            except (FloodWaitError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt == max_retries - 1:
                    raise
                if isinstance(e, FloodWaitError):
                    await asyncio.sleep(e.seconds)
                else:
                    await asyncio.sleep(Config.RETRY_DELAY * (2 ** attempt))
            except Exception as e:
                last_error = e
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(Config.RETRY_DELAY * (2 ** attempt))
        raise last_error if last_error else RuntimeError("Превышено количество попыток")

class ConnectionPool:
    _session: Optional[aiohttp.ClientSession] = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        async with cls._lock:
            if cls._session is None or cls._session.closed:
                timeout = aiohttp.ClientTimeout(
                    total=Config.HTTP_TIMEOUT,
                    connect=Config.HTTP_TIMEOUT/2,
                    sock_read=Config.HTTP_TIMEOUT
                )
                cls._session = aiohttp.ClientSession(
                    timeout=timeout,
                    headers={
                        "accept": "*/*",
                        "content-type": "application/json",
                        "user-agent": "Nicegram/92 CFNetwork/1390 Darwin/22.0.0",
                        "x-api-key": "e758fb28-79be-4d1c-af6b-066633ded128",
                        "accept-language": "en-US,en;q=0.9",
                    }
                )
            return cls._session

    @classmethod
    async def close(cls):
        async with cls._lock:
            if cls._session and not cls._session.closed:
                await cls._session.close()
                cls._session = None

class PhotoCache:
    _cache = AsyncCache[bytes](Config.PHOTO_CACHE_TTL, max_size=200)
    _download_locks: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
    _cleanup_lock = asyncio.Lock()
    _lock_timeout = 30
    
    @classmethod
    async def get_or_download(cls, client, entity_id: int) -> Optional[bytes]:
        try:
            if photo := await cls._cache.get(entity_id):
                return photo
                
            async with cls._download_locks[entity_id]:
                # Повторная проверка кэша после получения блокировки
                if photo := await cls._cache.get(entity_id):
                    return photo
                    
                async with asyncio.timeout(cls._lock_timeout):
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

async def get_creation_date(user_id: int) -> str:
    if not user_id:
        return "Ошибка: ID не указан"
        
    session = await ConnectionPool.get_session()
    try:
        async with asyncio.timeout(Config.HTTP_TIMEOUT):
            async with session.post(
                "https://restore-access.indream.app/regdate",
                json={"telegramId": user_id}
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("data", {}).get("date", "Ошибка получения данных")
    except aiohttp.ClientResponseError as e:
        return f"Ошибка сервера: {e.status}"
    except asyncio.TimeoutError:
        return "Таймаут при получении даты"
    except Exception as e:
        return f"Ошибка при получении даты: {str(e)}"

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
        self._funstat_cache = AsyncCache(Config.CACHE_TTL, max_size=100)

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
        await ConnectionPool.close()

    async def get_funstat_info(self, user_id: int) -> str:
        try:
            if cached_info := await self._funstat_cache.get(user_id):
                return cached_info

            chat = Config.FUNSTAT_BOT
            
            for attempt in range(Config.MAX_ATTEMPTS):
                try:
                    async with asyncio.timeout(Config.FUNSTAT_TIMEOUT):
                        await self._client.send_message(chat, str(user_id))
                        await asyncio.sleep(3)  # Короткая пауза перед чтением
                        
                        messages = await self._client.get_messages(chat, limit=3)
                        for msg in messages:
                            if not msg.text or str(user_id) not in msg.text:
                                continue
                                
                            if any(err in msg.text.lower() for err in ["не найден", "not found", "error", "ошибка"]):
                                return "⚠️ Пользователь не найден в базе funstat"
                            
                            lines = []
                            for line in msg.text.split("\n"):
                                line = line.strip()
                                if not line or any(x in line for x in ["ID:", "This is", "Это", "usernames:", "имена пользователя:"]) or "@" in line:
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
                        
                        if attempt < Config.MAX_ATTEMPTS - 1:
                            await asyncio.sleep(Config.RETRY_DELAY)
                    
                except YouBlockedUserError:
                    return self.strings["unblock_bot"]
                except FloodWaitError as e:
                    if attempt == Config.MAX_ATTEMPTS - 1:
                        raise
                    await asyncio.sleep(e.seconds)
                except asyncio.TimeoutError:
                    if attempt == Config.MAX_ATTEMPTS - 1:
                        return "⚠️ Таймаут при получении статистики"
                    continue
                    
            return "⚠️ Не удалось получить ответ от funstat"
                    
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

    async def format_user_info(self, user: User, full_user: GetFullUserRequest) -> str:
        """Форматирование информации о пользователе"""
        info_parts = []
        
        try:
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
                f"📝 Username: @{user.username or '🚫'}",
                f"📅 Регистрация: <code>{await get_creation_date(user.id)}</code>",
                f"👥 Общие чаты: {full_user.full_user.common_chats_count}",
                f"⭐️ Статус: {self._format_status(user.status)}"
            ]
            
            # Проверка звонков
            if hasattr(full_user.full_user, 'phone_calls_available'):
                calls_available = full_user.full_user.phone_calls_available and getattr(full_user.full_user, 'video_calls_available', False)
                details.append(f"📞 Звонки: {'✅' if calls_available else '❌'}")
                
            info_parts.extend(self._format_details(details))
            
            # Описание
            if full_user.full_user.about:
                info_parts.extend([
                    "",
                    "📋 <b>О пользователе:</b>",
                    f"<i>{full_user.full_user.about}</i>"
                ])
            
            # Ссылки
            if user.username:
                info_parts.extend([
                    "",
                    "🔗 <b>Ссылки:</b>",
                    f"├ Telegram: @{user.username}",
                    f"└ Профиль: <a href='tg://user?id={user.id}'>открыть</a>"
                ])
            
            # Статистика
            funstat_info = await self.get_funstat_info(user.id)
            if funstat_info and not any(err in funstat_info.lower() for err in ["ошибка", "error", "⚠️"]):
                info_parts.extend([
                    "",
                    "📊 <b>Статистика funstat:</b>",
                    funstat_info
                ])
            
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
                f"📅 Создан: <code>{await get_creation_date(channel.id)}</code>",
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