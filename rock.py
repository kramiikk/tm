from asyncio import sleep, Lock
from typing import Union, Optional, Dict, List, Tuple, Any, TypeVar, Generic
import aiohttp
import logging
import asyncio
from collections import defaultdict
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Message, Channel, User, UserStatusOnline, UserStatusOffline, UserStatusRecently
from telethon.errors.rpcerrorlist import YouBlockedUserError, FloodWaitError
from telethon import Button
from .. import loader, utils
import time
from dataclasses import dataclass

# Настройка логирования
logger = logging.getLogger(__name__)

# Инициализация глобальных объектов
class Metrics:
    """Сборщик метрик"""
    def __init__(self):
        self._metrics = defaultdict(int)
        self._start_time = time.time()
        
    def increment(self, metric: str):
        """Увеличение счетчика метрики"""
        self._metrics[metric] += 1
        
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        uptime = time.time() - self._start_time
        return {
            'requests': dict(self._metrics),
            'uptime': f"{uptime:.0f}s",
            'rps': sum(self._metrics.values()) / uptime if uptime > 0 else 0
        }

metrics = Metrics()

T = TypeVar('T')

@dataclass
class Config:
    """Конфигурация модуля"""
    CACHE_TTL: int = 3600  # 1 час
    CACHE_SIZE: int = 500
    HTTP_TIMEOUT: int = 10
    FUNSTAT_TIMEOUT: int = 10
    MAX_ATTEMPTS: int = 3
    RETRY_DELAY: int = 1
    FUNSTAT_BOT: str = "@Suusbdj_bot"
    LOG_LEVEL: int = logging.INFO
    PHOTO_CACHE_TTL: int = 1800  # 30 минут
    MAX_RETRIES: int = 3
    METRICS_INTERVAL: int = 300  # 5 минут
    
config = Config()  # Создаем единственный экземпляр конфигурации

class AsyncCache(Generic[T]):
    """Асинхронный кэш с поддержкой TTL"""
    def __init__(self, ttl: int, max_size: int = 1000):
        self._cache: Dict[Any, Tuple[T, float]] = {}
        self._lock = Lock()
        self._ttl = ttl
        self._max_size = max_size
        self._metrics = defaultdict(int)
        self._last_cleanup = time.time()
        self._cleanup_interval = 300
        
    async def _cleanup_cache(self):
        """Очистка устаревших и избыточных записей"""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
            
        async with self._lock:
            # Удаляем устаревшие записи
            expired_keys = [
                k for k, (_, timestamp) in self._cache.items()
                if now - timestamp >= self._ttl
            ]
            for k in expired_keys:
                del self._cache[k]
                
            # Если после удаления устаревших всё ещё превышен лимит
            if len(self._cache) > self._max_size:
                # Сортируем по времени последнего доступа и удаляем старые
                sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
                items_to_remove = len(self._cache) - self._max_size
                for old_key, _ in sorted_items[:items_to_remove]:
                    del self._cache[old_key]
                    
            self._last_cleanup = now
            self._metrics['cleanups'] += 1
            self._metrics['cleaned_items'] += len(expired_keys)
        
    async def get(self, key: Any) -> Optional[Any]:
        """Получение значения из кэша"""
        await self._cleanup_cache()
        async with self._lock:
            if key not in self._cache:
                self._metrics['misses'] += 1
                return None
                
            value, _ = self._cache[key]
            self._metrics['hits'] += 1
            return value
            
    async def set(self, key: Any, value: Any):
        """Установка значения в кэш"""
        await self._cleanup_cache()
        async with self._lock:
            self._cache[key] = (value, time.time())

    def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик кэша"""
        total = self._metrics['hits'] + self._metrics['misses']
        return {
            'hits': self._metrics['hits'],
            'misses': self._metrics['misses'],
            'hit_rate': f"{(self._metrics['hits'] / total if total else 0):.2%}",
            'size': len(self._cache)
        }

class RetryHandler:
    """Обработчик повторных попыток"""
    @staticmethod
    async def retry_with_delay(func, *args, max_retries=Config.MAX_RETRIES, **kwargs):
        """Выполнение функции с повторными попытками"""
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except FloodWaitError as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = e.seconds
                logger.warning(f"FloodWaitError: ожидание {wait_time} секунд")
                await asyncio.sleep(wait_time)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = Config.RETRY_DELAY * (attempt + 1)
                logger.warning(f"Ошибка: {str(e)}. Повторная попытка через {wait_time} сек.")
                await asyncio.sleep(wait_time)

class ConnectionPool:
    _session: Optional[aiohttp.ClientSession] = None
    
    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            cls._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=Config.HTTP_TIMEOUT),
                headers={
                    "accept": "*/*",
                    "content-type": "application/x-www-form-urlencoded",
                    "user-agent": "Nicegram/92 CFNetwork/1390 Darwin/22.0.0",
                    "x-api-key": "e758fb28-79be-4d1c-af6b-066633ded128",
                    "accept-language": "en-US,en;q=0.9",
                }
            )
        return cls._session

    @classmethod
    async def close(cls):
        if cls._session and not cls._session.closed:
            await cls._session.close()

def timed_lru_cache(seconds: int, maxsize: int = 128):
    def wrapper_decorator(func):
        cache = {}
        
        async def wrapper(*args, **kwargs):
            current_time = int(time.time() // seconds)
            key = (current_time, args, str(kwargs))
            
            if key not in cache:
                cache[key] = await func(*args, **kwargs)
                
                # Очистка старых записей
                current_keys = list(cache.keys())
                for k in current_keys:
                    if k[0] != current_time:
                        del cache[k]
                        
                # Ограничение размера кэша
                if len(cache) > maxsize:
                    oldest = min(cache.keys(), key=lambda k: k[0])
                    del cache[oldest]
                    
            return cache[key]
            
        return wrapper
    return wrapper_decorator

# Настройка уровня логирования
logging.basicConfig(level=Config.LOG_LEVEL)

class PhotoCache:
    """Кэш для фотографий профилей"""
    _cache = AsyncCache[bytes](Config.PHOTO_CACHE_TTL, max_size=200)
    _download_locks: Dict[int, Lock] = defaultdict(Lock)
    _cleanup_lock = Lock()
    
    @classmethod
    async def get(cls, entity_id: int) -> Optional[bytes]:
        return await cls._cache.get(entity_id)
    
    @classmethod
    async def set(cls, entity_id: int, photo_data: bytes):
        await cls._cache.set(entity_id, photo_data)
    
    @classmethod
    async def cleanup_locks(cls):
        """Очистка неиспользуемых блокировок"""
        async with cls._cleanup_lock:
            current_time = time.time()
            to_remove = []
            for entity_id, lock in cls._download_locks.items():
                if not lock.locked() and current_time - lock._creation_time > 300:  # 5 минут
                    to_remove.append(entity_id)
            for entity_id in to_remove:
                del cls._download_locks[entity_id]
    
    @classmethod
    async def get_or_download(cls, client, entity_id: int) -> Optional[bytes]:
        try:
            # Проверяем кэш только под блокировкой
            if entity_id not in cls._download_locks:
                cls._download_locks[entity_id] = Lock()
                cls._download_locks[entity_id]._creation_time = time.time()
            
            async with cls._download_locks[entity_id]:
                if photo := await cls.get(entity_id):
                    return photo
                
                photo = await RetryHandler.retry_with_delay(
                    client.download_profile_photo,
                    entity_id,
                    bytes
                )
                
                if photo:
                    await cls.set(entity_id, photo)
                    return photo
            
            await cls.cleanup_locks()
            return None
        except Exception as e:
            logger.error(f"Ошибка при загрузке фото для {entity_id}: {e}")
            return None

@timed_lru_cache(seconds=Config.CACHE_TTL, maxsize=Config.CACHE_SIZE)
async def get_creation_date(user_id: int) -> str:
    """Получение даты регистрации аккаунта с кэшированием"""
    session = await ConnectionPool.get_session()
    try:
        async with session.post(
            "https://restore-access.indream.app/regdate",
            json={"telegramId": user_id}
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data", {}).get("date", "Ошибка получения данных")
            return f"Ошибка сервера: {response.status}"
    except aiohttp.ClientError as e:
        return f"Ошибка сети: {str(e)}"
    except Exception as e:
        return f"Неизвестная ошибка: {str(e)}"
    # Не закрываем сессию здесь, так как она управляется ConnectionPool

class DataLoader:
    """Загрузчик данных с поддержкой параллельного выполнения и кэширования"""
    _entity_cache = AsyncCache(Config.CACHE_TTL, max_size=500)
    
    @classmethod
    async def load_all_data(cls, entity: Union[User, Channel], client) -> Dict[str, Any]:
        cache_key = f"{entity.id}_{type(entity).__name__}"
        
        # Проверяем кэш
        if cached_data := await cls._entity_cache.get(cache_key):
            logger.debug(f"Данные для {entity.id} найдены в кэше")
            return cached_data
            
        tasks = {
            "creation_date": asyncio.create_task(get_creation_date(entity.id)),
            "photo": asyncio.create_task(PhotoCache.get_or_download(client, entity.id)),
            "full_info": asyncio.create_task(
                client(GetFullUserRequest(entity.id))
                if isinstance(entity, User)
                else client(GetFullChannelRequest(entity))
            )
        }
        
        results = {}
        errors = []
        
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception as e:
                logger.error(f"Ошибка при загрузке {name}: {e}")
                errors.append(f"{name}: {str(e)}")
                results[name] = None
                
        if errors:
            logger.warning(f"Ошибки при загрузке данных: {', '.join(errors)}")
            
        # Кэшируем результат только если нет критических ошибок
        if results.get("full_info"):
            await cls._entity_cache.set(cache_key, results)
                
        return results

    @staticmethod
    def format_errors(errors: List[str]) -> str:
        """Форматирование списка ошибок для пользователя"""
        if not errors:
            return ""
        return "\n⚠️ Возникли ошибки:\n" + "\n".join(f"• {err}" for err in errors)

@loader.tds
class UserInfoMod(loader.Module):
    """Получение информации о пользователе или канале Telegram"""
    
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
        """Форматирование списка деталей с разделителями"""
        return [f"├ {detail}" for detail in details[:-1]] + [f"└ {details[-1]}"]

    def _format_status_flags(self, flags: List[str]) -> str:
        """Форматирование флагов статуса"""
        return f"⚜️ {' • '.join(flags)}\n" if flags else ""

    async def _send_message(self, chat_id: int, text: str, photo: Optional[bytes] = None, **kwargs):
        """Универсальный метод отправки сообщения с фото или без"""
        try:
            method = self._client.send_file if photo else self._client.send_message
            params = {"file": photo, "caption": text} if photo else {"message": text}
            await RetryHandler.retry_with_delay(method, chat_id, **params, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")
            raise

    def _get_entity_flags(self, entity: Union[User, Channel]) -> List[str]:
        """Получение флагов статуса для сущности"""
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
        elif isinstance(entity, Channel):
            if getattr(entity, 'restricted', False):
                restriction_reason = getattr(entity, 'restriction_reason', None)
                if restriction_reason:
                    # Нормализуем причину ограничения
                    reason = restriction_reason.lower()
                    if any(x in reason for x in ['porn', '18+', 'adult', 'nsfw']):
                        flags.append("⚠️ Ограничен: 18+")
                    else:
                        flags.append(f"⚠️ Ограничен: {restriction_reason}")
                else:
                    flags.append("⚠️ Ограничен")
        return flags

    async def on_unload(self):
        """Закрытие соединений при выгрузке модуля"""
        await ConnectionPool.close()

    async def get_funstat_info(self, user_id: int) -> str:
        """Получение информации из funstat с кэшированием"""
        if cached_info := await self._funstat_cache.get(user_id):
            return cached_info
            
        try:
            await RetryHandler.retry_with_delay(
                self._client.send_message,
                Config.FUNSTAT_BOT,
                str(user_id)
            )
            
            start_time = time.time()
            attempts = 0
            max_attempts = 10  # Максимальное количество попыток
            
            while time.time() - start_time < Config.FUNSTAT_TIMEOUT and attempts < max_attempts:
                attempts += 1
                messages = await RetryHandler.retry_with_delay(
                    self._client.get_messages,
                    Config.FUNSTAT_BOT,
                    limit=5
                )
                
                for msg in messages:
                    if not msg.text:
                        continue
                        
                    if str(user_id) in msg.text:
                        # Проверяем наличие ошибок в ответе
                        if any(err in msg.text.lower() for err in [
                            "не найден", "not found",
                            "error", "ошибка",
                            "произошла ошибка"
                        ]):
                            return "⚠️ Пользователь не найден в базе funstat"
                            
                        # Обрабатываем успешный ответ
                        lines = []
                        
                        for line in msg.text.split("\n"):
                            line = line.strip()
                            
                            # Пропускаем служебные строки
                            if not line or "ID:" in line or any(x in line for x in ["This is", "Это"]):
                                continue
                                
                            # Пропускаем неиспользуемые секции
                            if any(x in line.lower() for x in ["usernames:", "first name / last name:"]):
                                continue
                                
                            # Форматируем числа с разделителями
                            if any(x in line.lower() for x in [
                                "messages in", "сообщений в",
                                "circles:", "кругов:",
                                "admin in", "админ в"
                            ]):
                                try:
                                    label, value = line.split(":", 1)
                                    if value.strip().replace(",", "").isdigit():
                                        value = int(value.strip().replace(",", ""))
                                    line = f"{label}: {value:,}"
                                except:
                                    pass
                                    
                            lines.append(line)
                            
                        if not lines:
                            return "⚠️ Нет данных в ответе funstat"
                            
                        info = "\n".join(lines)
                        await self._funstat_cache.set(user_id, info)
                        return info
                        
                await sleep(1)
                
            return "⚠️ Превышено время ожидания ответа"
                    
        except YouBlockedUserError:
            return self.strings["unblock_bot"]
        except Exception as e:
            return self.strings["error_fetching"].format(str(e))

    async def send_info_message(self, message: Message, entity: Union[User, Channel], info_text: str):
        """Отправка сообщения с информацией и фото"""
        try:
            photo = await PhotoCache.get_or_download(self._client, entity.id)
            buttons = [[Button.inline("🔄 Обновить", data=f"refresh:{entity.id}")]]
            
            await self._send_message(
                message.chat_id,
                info_text,
                photo=photo,
                buttons=buttons
            )
            
            await message.delete()
            
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")
            raise

    async def userinfocmd(self, message: Message):
        """Получить информацию о пользователе или канале"""
        start_time = time.time()
        await utils.answer(message, self.strings["loading"])
        
        try:
            args = utils.get_args_raw(message)
            reply = await message.get_reply_message()
            
            entity = await self.get_entity_safe(
                args or (reply.sender_id if reply else None)
            )
            
            if not entity:
                await utils.answer(message, self.strings["not_found"])
                return
                
            data = await DataLoader.load_all_data(entity, self._client)
            
            if isinstance(entity, Channel):
                info_text = await self.format_channel_info(entity, data['full_info'])
            else:
                info_text = await self.format_user_info(entity, data['full_info'])
                
            if errors := DataLoader.format_errors(data.get('errors', [])):
                info_text += errors
                
            await self.send_info_message(message, entity, info_text)
            
            execution_time = time.time() - start_time
            logger.info(f"Команда выполнена за {execution_time:.2f}с")
            metrics.increment('successful_requests')
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды: {e}")
            metrics.increment('failed_requests')
            await utils.answer(
                message,
                self.strings["error_fetching"].format(str(e))
            )
    async def refresh_callback_handler(self, call):
        """Обработчик нажатия кнопки обновления"""
        logger.debug("Запуск обработчика обновления")
        try:
            entity_id = int(call.data.decode().split(":")[1])
            logger.debug(f"Обновление информации для {entity_id}")
            
            entity = await self.get_entity_safe(entity_id)
            if not entity:
                logger.warning(f"Сущность {entity_id} не найдена при обновлении")
                await call.answer("❌ Не удалось получить информацию", show_alert=True)
                return
            
            if isinstance(entity, Channel):
                channel = await self._client(GetFullChannelRequest(entity))
                info_text = await self.format_channel_info(entity, channel)
            else:
                user = await self._client(GetFullUserRequest(entity.id))
                info_text = await self.format_user_info(entity, user)
            
            photo = await PhotoCache.get_or_download(self._client, entity.id)
            buttons = [[Button.inline("🔄 Обновить", data=f"refresh:{entity.id}")]]
            
            await self._send_message(
                call.chat_id,
                info_text,
                photo=photo,
                buttons=buttons
            )
            
            logger.debug("Обновление успешно выполнено")
            await call.answer("✅ Информация обновлена!")
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении: {e}")
            await call.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

    async def callback_handler(self, call):
        """Маршрутизация callback-запросов"""
        if call.data.decode().startswith("refresh:"):
            await self.refresh_callback_handler(call)

    def _format_status(self, status) -> str:
        """Форматирование статуса пользователя"""
        if isinstance(status, UserStatusOnline):
            return "🟢 В сети"
        elif isinstance(status, UserStatusOffline):
            return f"⚫️ Был(а) {status.was_online.strftime('%d.%m.%Y %H:%M')}"
        elif isinstance(status, UserStatusRecently):
            return "🔵 Недавно"
        return "⚫️ Давно"

    async def get_entity_safe(self, entity_id: Union[str, int]) -> Optional[Union[User, Channel]]:
        """Безопасное получение сущности"""
        if not entity_id:
            return None
        try:
            return await self._client.get_entity(
                int(entity_id) if str(entity_id).isdigit() else entity_id
            )
        except ValueError as e:
            logger.error(f"Неверный формат ID: {e}")
            return None
        except (TypeError, AttributeError) as e:
            logger.error(f"Ошибка при обработке entity_id: {e}")
            return None
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при получении сущности: {e}")
            return None

    async def format_user_info(self, user: User, full_user: GetFullUserRequest) -> str:
        """Форматирование информации о пользователе"""
        metrics.increment('user_info_requests')
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
                f"📝 Username: @{getattr(user, 'username', '🚫')}",
                f"📅 Регистрация: <code>{await get_creation_date(user.id)}</code>",
                f"👥 Общие чаты: {getattr(full_user.full_user, 'common_chats_count', 0)}",
                f"⭐️ Статус: {self._format_status(getattr(user, 'status', None))}"
            ]
            
            if hasattr(full_user.full_user, 'phone_calls_available'):
                details.append(f"📞 Звонки: {'✅' if full_user.full_user.phone_calls_available else '❌'}")
            if hasattr(full_user.full_user, 'video_calls_available'):
                details.append(f"📹 Видеозвонки: {'✅' if full_user.full_user.video_calls_available else '❌'}")
                
            info_parts.extend(self._format_details(details))
            
            # Описание
            if getattr(full_user.full_user, 'about', None):
                info_parts.extend([
                    "",
                    "📋 <b>О пользователе:</b>",
                    f"<i>{full_user.full_user.about}</i>"
                ])
            
            # Ссылки
            if getattr(user, 'username', None):
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
                    "📊 <b>Статистика:</b>",
                    funstat_info
                ])
            
            return "\n".join(info_parts)
            
        except Exception as e:
            logger.error(f"Ошибка при форматировании информации о пользователе: {e}")
            return f"❌ Ошибка при форматировании информации: {str(e)}"

    async def format_channel_info(self, channel: Channel, full_channel: GetFullChannelRequest) -> str:
        """Форматирование информации о канале"""
        metrics.increment('channel_info_requests')
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
                f"📝 Username: @{getattr(channel, 'username', '🚫')}",
                f"📅 Создан: <code>{await get_creation_date(channel.id)}</code>",
                f"👥 Подписчиков: {getattr(full_channel.full_chat, 'participants_count', 0):,}"
            ]
            
            if getattr(full_channel.full_chat, 'slowmode_seconds', None):
                details.append(f"⏱ Медленный режим: {full_channel.full_chat.slowmode_seconds} сек.")
            if getattr(full_channel.full_chat, 'linked_chat_id', None):
                details.append(f"🔗 Связанный чат: {full_channel.full_chat.linked_chat_id}")
            if hasattr(full_channel.full_chat, 'can_view_stats') and full_channel.full_chat.can_view_stats:
                details.append("📊 Доступна статистика: ✅")
            
            if hasattr(full_channel.full_chat, 'online_count'):
                online_count = getattr(full_channel.full_chat, 'online_count', 0)
                if online_count:
                    details.append(f"🟢 Онлайн: {online_count:,}")
            
            if hasattr(full_channel.full_chat, 'messages_count'):
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
            if hasattr(full_channel.full_chat, 'invite_link') and full_channel.full_chat.invite_link:
                links.append(f"└ Приглашение: {full_channel.full_chat.invite_link}")
                
            if links:
                info_parts.extend([
                    "",
                    "🔗 <b>Ссылки:</b>",
                    *links
                ])
            
            # Возможности
            features = []
            if getattr(channel, "signatures", False):
                features.append("✍️ Подписи авторов")
            if getattr(channel, "has_link", False):
                features.append("🔗 Публичные ссылки")
            if getattr(full_channel.full_chat, "can_set_stickers", False):
                features.append("🎨 Стикеры")
            
            if features:
                info_parts.extend([
                    "",
                    "⚙️ <b>Возможности:</b>",
                    " • ".join(features)
                ])
            
            return "\n".join(info_parts)
            
        except Exception as e:
            logger.error(f"Ошибка при форматировании информации о канале: {e}")
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