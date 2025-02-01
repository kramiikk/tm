""" Author: kramiikk - Telegram: @kramiikk """

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Union, List
from telethon import functions, types, errors
from telethon.errors.rpcerrorlist import (
    MessageIdInvalidError,
    PhotoInvalidDimensionsError,
    PhotoCropSizeSmallError,
    PhotoSaveFileInvalidError,
)
from collections import deque
from .. import loader, utils
import tempfile
import logging
import zipfile
import asyncio
import random
import shutil
import json
import re
import os

logger = logging.getLogger(__name__)

CONFIG_DEFAULT_DELAY = "default_delay"
CONFIG_MIN_DELAY = "min_delay"
CONFIG_MAX_DELAY = "max_delay"
CONFIG_JITTER = "jitter"
CONFIG_ERROR_THRESHOLD = "error_threshold"
CONFIG_SUCCESS_REDUCTION = "success_reduction"
CONFIG_DELAY_MULTIPLIER = "delay_multiplier"
CONFIG_RECENT_MULTIPLIER_HISTORY_SIZE = "recent_multiplier_history_size"
CONFIG_PFPDIR_PATH = "pfpdir_path"
CONFIG_TIMEZONE_OFFSET = "timezone_offset"
CONFIG_NIGHT_MODE = "night_mode"
CONFIG_NIGHT_START = "night_start"
CONFIG_NIGHT_END = "night_end"
CONFIG_NIGHT_DELAY_MULTIPLIER = "night_delay"


@loader.tds
class ProfileChangerMod(loader.Module):
    """Автоматическое обновление фото профиля с адаптивной системой защиты."""

    strings = {
        "name": "ProfileChanger",
        "starting": "🔄 <b>Запуск смены фото профиля</b>\n\n• Задержка: {} мин\n• ~{} обновлений/час",
        "stopping": "🛑 <b>Остановка</b>\n• Обновлений: {}\n• С момента запуска: {}\n• Ошибок: {}",
        "stats": "📊 <b>Статистика</b>",
        "no_photo": "❌ <b>Ответьте на фото</b>",
        "already_running": "⚠️ <b>Уже запущено</b>",
        "not_running": "⚠️ <b>Не запущено</b>",
        "error": "{} <b>{}:</b> {}",
        "flood_wait": "⚠️ <b>Флудвейт</b>\n\n• Новая задержка: {:.1f} мин\n• Ожидание: {:.1f} мин",
        "pfpone_success": "✅ <b>Аватарка установлена</b>",
        "pfpone_no_reply": "❌ <b>Ответьте на фото, которое хотите установить</b>",
        "delay_details_success": "  • Успешные обновления: снижение задержки",
        "delay_details_recent_flood": "  • Недавний флудвейт: увеличение задержки",
        "delay_details_recent_error": "  • Недавняя ошибка: увеличение задержки",
        "delay_details_weighted_multiplier": "  • Выбор множителя: взвешенный случайный",
        "delay_details_jitter": "  • Случайность: +/- {}%",
        "stopped_successfully": "✅ <b>Успешно остановлено</b>",
        "dir_not_found": "❌ <b>Директория не найдена:</b> <code>{}</code>",
        "no_photos": "❌ <b>В директории нет подходящих фотографий</b>",
        "invalid_delay": "❌ <b>Неверная задержка. Используйте число секунд</b>",
        "loading_from_dir": "🔄 <b>Загрузка фотографий из директории...</b>\n\n• Найдено фото: {}\n• Задержка: {}",
    }

    _state_keys = [
        "running",
        "start_time",
        "last_update",
        "update_count",
        "error_count",
        "flood_count",
        "delay",
        "chat_id",
        "message_id",
        "success_streak",
        "floods",
        "retries",
        "last_error_time",
        "total_updates_cycle",
        "recent_multiplier_uses",
        "pfpdir_running",
    ]

    def _init_state(self):
        """Инициализация состояния модуля"""
        self.running = False
        self._task = None
        self._lock = asyncio.Lock()
        self._photo_lock = asyncio.Lock()
        self.start_time = None
        self.last_update = None
        self.update_count = 0
        self.error_count = 0
        self.flood_count = 0
        self.delay = self.config[CONFIG_DEFAULT_DELAY]
        self.chat_id = None
        self.message_id = None
        self.floods = deque(maxlen=10)
        self.success_streak = 0
        self.retries = 0
        self.last_error_time = None
        self.total_updates_cycle = 0
        self.recent_multiplier_uses: Dict[tuple, datetime] = {}
        self.pfpdir_running = False

    def __init__(self):
        self.config = loader.ModuleConfig(
            CONFIG_DEFAULT_DELAY,
            352,
            "Начальная задержка (сек)",
            CONFIG_MIN_DELAY,
            63,
            "Минимальная задержка (сек)",
            CONFIG_MAX_DELAY,
            781,
            "Максимальная задержка (сек)",
            CONFIG_JITTER,
            0.6,
            "Случайность (0.0-1.0)",
            CONFIG_ERROR_THRESHOLD,
            3,
            "Порог ошибок",
            CONFIG_SUCCESS_REDUCTION,
            0.9,
            "Снижение при успехе",
            CONFIG_DELAY_MULTIPLIER,
            1.7,
            "Множитель задержки при ошибках и флудвейтах",
            CONFIG_RECENT_MULTIPLIER_HISTORY_SIZE,
            5,
            "Размер истории последних использованных множителей",
            CONFIG_PFPDIR_PATH,
            "/root/Heroku/new",
            "Путь к директории для загрузки фото",
            CONFIG_TIMEZONE_OFFSET,
            5,
            "Смещение часового пояса относительно UTC (например: 5 для UTC+5)",
            CONFIG_NIGHT_MODE,
            True,
            "Включить ночной режим (True/False)",
            CONFIG_NIGHT_START,
            23,
            "Час начала ночного режима по местному времени (0-23)",
            CONFIG_NIGHT_END,
            7,
            "Час окончания ночного режима по местному времени (0-23)",
            CONFIG_NIGHT_DELAY_MULTIPLIER,
            5,
            "Множитель задержки для ночного режима",
        )

        self.multiplier_ranges = [
            (0.95, 1.05),
            (1.15, 1.35),
            (1.35, 1.55),
            (1.55, 1.75),
            (1.75, 1.95),
        ]

        self.extreme_ranges = [
            (0.82, 0.92),
            (1.97, 2.17),
        ]

        if random.random() < 0.3:
            self.multiplier_ranges.extend(self.extreme_ranges)
        self._init_state()

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._me = await client.get_me()
        self._load_state()
        if self.running:
            self._task = asyncio.create_task(self._loop())
        if self.pfpdir_running:
            self.pfpdir_running = False
            asyncio.create_task(self._process_pfpdir())
        logger.info("ProfileChanger loaded")

    async def on_unload(self):
        """Выгрузка модуля."""
        if self.running:
            await self._send_stopping()
            if self._task:
                self._task.cancel()
        logger.info("ProfileChanger unloaded")

    def _get_state(self) -> Dict:
        """Получение текущего состояния модуля для сохранения."""
        floods = list(self.floods) if hasattr(self, "floods") and self.floods else []
        return {
            "running": self.running,
            "start_time": (
                self.start_time.astimezone(timezone.utc).isoformat()
                if self.start_time
                else None
            ),
            "last_update": (
                self.last_update.astimezone(timezone.utc).isoformat()
                if self.last_update
                else None
            ),
            "update_count": self.update_count,
            "error_count": self.error_count,
            "flood_count": self.flood_count,
            "delay": self.delay,
            "chat_id": self.chat_id,
            "message_id": self.message_id,
            "success_streak": self.success_streak,
            "floods": [t.astimezone(timezone.utc).isoformat() for t in floods],
            "retries": self.retries,
            "last_error_time": (
                self.last_error_time.astimezone(timezone.utc).isoformat()
                if self.last_error_time
                else None
            ),
            "total_updates_cycle": self.total_updates_cycle,
            "recent_multiplier_uses": {
                str(k): v.astimezone(timezone.utc).isoformat()
                for k, v in self.recent_multiplier_uses.items()
            },
            "pfpdir_running": self.pfpdir_running,
        }

    def _load_state(self) -> None:
        """Загрузка состояния модуля из базы данных."""
        try:
            state_json = self._db.get(self.strings["name"], "state")
            if not state_json:
                return
            state = json.loads(state_json)

            if state.get("start_time"):
                state["start_time"] = datetime.fromisoformat(
                    state["start_time"]
                ).replace(tzinfo=timezone.utc)
            if state.get("last_update"):
                state["last_update"] = datetime.fromisoformat(
                    state["last_update"]
                ).replace(tzinfo=timezone.utc)
            if state.get("last_error_time"):
                state["last_error_time"] = datetime.fromisoformat(
                    state["last_error_time"]
                ).replace(tzinfo=timezone.utc)
            if "floods" in state:
                floods_list = [
                    datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
                    for t in state["floods"]
                ]
                state["floods"] = deque(floods_list, maxlen=10)
            if "recent_multiplier_uses" in state:
                self.recent_multiplier_uses = {
                    eval(k): datetime.fromisoformat(v).replace(tzinfo=timezone.utc)
                    for k, v in state["recent_multiplier_uses"].items()
                }
            if "pfpdir_running" in state:
                self.pfpdir_running = state["pfpdir_running"]
            for key, value in state.items():
                setattr(self, key, value)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON при загрузке состояния: {e}")
            self._reset()
        except Exception as e:
            logger.error(
                f"Непредвиденная ошибка при загрузке состояния: {type(e).__name__}: {e}"
            )
            self._reset()

    async def _get_photo(self) -> Optional[types.Photo]:
        """Получение фотографии профиля из указанного сообщения."""
        if not self.running:
            return None
        try:
            message = await self._client.get_messages(self.chat_id, ids=self.message_id)
            if not message or not message.photo:
                await self._stop()
                return None
            return message.photo
        except MessageIdInvalidError:
            await self._stop()
            return None
        except Exception as e:
            logger.error(f"Ошибка получения фото: {e}")
            return None

    async def _set_profile_photo(
        self, photo: types.Photo
    ) -> Union[bool, errors.FloodWaitError, Exception]:
        """Обновление фотографии профиля."""
        try:
            await self._client(
                functions.photos.UpdateProfilePhotoRequest(
                    id=types.InputPhoto(
                        id=photo.id,
                        access_hash=photo.access_hash,
                        file_reference=photo.file_reference,
                    )
                )
            )
            return True
        except errors.FloodWaitError as e:
            return e
        except (
            PhotoInvalidDimensionsError,
            PhotoCropSizeSmallError,
            PhotoSaveFileInvalidError,
        ) as e:
            return e
        except Exception as e:
            logger.error(f"Ошибка при обновлении фото профиля: {e}")
            return e

    async def _handle_error(
        self, error_type: str, error: Exception, stop: bool = False
    ):
        """Централизованная обработка ошибок."""
        self.error_count += 1
        self.success_streak = 0
        self.last_error_time = datetime.now()

        if isinstance(error, errors.FloodWaitError):
            self.flood_count += 1
            self.floods.append(datetime.now())
            self.delay = min(
                self.config[CONFIG_MAX_DELAY],
                self.delay * self.config[CONFIG_DELAY_MULTIPLIER],
            )
            wait_time = error.seconds
            error_message = self.strings["flood_wait"].format(
                self.delay / 60, wait_time / 60
            )
            log_message = f"Flood error: {str(error)}"
            error_symbol = "⚠️"
            error_name = "Флудвейт"
        else:
            self.retries += 1
            error_symbol = "❌"
            log_message = f"{error_type.capitalize()} error: {str(error)}"
            error_name = "Неверный формат фото" if error_type == "photo" else "Ошибка"
            error_message = self.strings["error"].format(
                error_symbol,
                error_name,
                str(error),
            )
        logger.info(error_message)
        logger.error(log_message)

        if stop:
            await self._stop()
        elif isinstance(error, errors.FloodWaitError):
            await asyncio.sleep(error.seconds)

    async def _handle_operation_result(
        self,
        result: Union[bool, errors.FloodWaitError, Exception],
        operation_type: str = "update",
    ) -> bool:
        """Unified handler for profile operation results"""

        def _handle_success():
            self.last_update = datetime.now()
            self.update_count += 1
            self.success_streak += 1
            self._save_state()
            return True

        if (
            result is True
            or hasattr(result, "photo")
            or isinstance(result, types.Photo)
            or (isinstance(result, (dict, object)) and hasattr(result, "photo"))
        ):
            return _handle_success()
        if isinstance(result, errors.FloodWaitError):
            await self._handle_error("flood", result)
            return False
        if isinstance(
            result,
            (
                PhotoInvalidDimensionsError,
                PhotoCropSizeSmallError,
                PhotoSaveFileInvalidError,
            ),
        ):
            await self._handle_error("photo", result, stop=(operation_type == "update"))
            return False
        await self._handle_error("generic", result)
        return False

    async def _update(self) -> bool:
        """Попытка обновить фотографию профиля."""
        if not self.running:
            return False
        try:
            async with self._photo_lock:
                photo = await self._get_photo()
                if not photo:
                    return False
                result = await self._set_profile_photo(photo)
                return await self._handle_operation_result(result)
        except Exception as e:
            return await self._handle_operation_result(e)

    async def _upload_photo(self, path: str) -> bool:
        """Загрузка фотографии на профиль с валидацией."""
        if not await self._validate_photo(path):
            return False
        try:
            async with self._photo_lock:
                result = await self._client(
                    functions.photos.UploadProfilePhotoRequest(
                        file=await self._client.upload_file(path)
                    )
                )
                return await self._handle_operation_result(result, "upload")
        except Exception as e:
            return await self._handle_operation_result(e, "upload")

    def _get_local_hour(self) -> int:
        """Получение текущего часа в локальном часовом поясе"""
        utc_now = datetime.now(timezone.utc)
        local_offset = timedelta(hours=self.config[CONFIG_TIMEZONE_OFFSET])
        local_time = utc_now + local_offset
        return local_time.hour

    def _get_local_time(self) -> datetime:
        """Получение текущего времени в локальном часовом поясе"""
        utc_now = datetime.now(timezone.utc)
        local_offset = timedelta(hours=self.config[CONFIG_TIMEZONE_OFFSET])
        return utc_now + local_offset

    def _calculate_delay(self) -> float:
        """Расчет задержки с учетом ночного режима."""
        base_delay = self.delay * (1 + (datetime.now().hour % 3) * 0.05)
        now = datetime.now(timezone.utc)

        if self.config[CONFIG_NIGHT_MODE]:
            current_hour = self._get_local_hour()
            night_start = self.config[CONFIG_NIGHT_START]
            night_end = self.config[CONFIG_NIGHT_END]

            is_night_time = False
            if night_start > night_end:
                is_night_time = current_hour >= night_start or current_hour < night_end
            else:
                is_night_time = night_start <= current_hour < night_end
            if is_night_time:
                night_multiplier = self.config[CONFIG_NIGHT_DELAY_MULTIPLIER]
                night_multiplier *= random.uniform(0.8, 1.2)
                base_delay *= night_multiplier
                logger.info(
                    f"Ночной режим активен (UTC+{self.config[CONFIG_TIMEZONE_OFFSET]}). Задержка увеличена в {night_multiplier:.2f} раз"
                )
        if self.success_streak >= 5:
            success_multiplier = max(
                0.85,
                self.config[CONFIG_SUCCESS_REDUCTION] ** (self.success_streak // 7),
            )
            success_multiplier *= random.uniform(0.95, 1.05)
            base_delay *= success_multiplier
        if (
            self.last_error_time
            and (now - self.last_error_time).total_seconds()
            < self.config[CONFIG_MAX_DELAY]
        ):
            error_multiplier = self.config[CONFIG_DELAY_MULTIPLIER] * (
                1 + random.random() * 0.7
            )
            base_delay *= error_multiplier
        if self.floods:
            recent_floods = len(
                [t for t in self.floods if (now - t).total_seconds() < 3600]
            )
            if recent_floods:
                flood_multiplier = self.config[CONFIG_DELAY_MULTIPLIER] ** (
                    recent_floods * 1.2
                )
                flood_multiplier *= 1 + random.random() * recent_floods * 0.4
                base_delay = min(
                    self.config[CONFIG_MAX_DELAY], base_delay * flood_multiplier
                )
        return max(
            self.config[CONFIG_MIN_DELAY],
            min(self.config[CONFIG_MAX_DELAY], base_delay),
        )

    async def _loop(self) -> None:
        """Основной асинхронный цикл для периодического обновления фотографии."""
        consecutive_errors = 0
        base_sleep_time = self.config[CONFIG_MIN_DELAY]
        while self.running:
            try:
                now = datetime.now()
                calculated_delay = self._calculate_delay()

                if self.last_update:
                    elapsed = max(0, (now - self.last_update).total_seconds())
                    sleep_time = calculated_delay - elapsed
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)
                async with self._lock:
                    if await self._update():
                        consecutive_errors = 0
                        await asyncio.sleep(0)
                    else:
                        consecutive_errors += 1
                        sleep_duration = base_sleep_time * (2**consecutive_errors)
                        if consecutive_errors >= self.config[CONFIG_ERROR_THRESHOLD]:
                            logger.warning(
                                f"Достигнут порог ошибок ({self.config[CONFIG_ERROR_THRESHOLD]}). Остановка."
                            )
                            await self._stop()
                            break
                        await asyncio.sleep(
                            min(sleep_duration, self.config[CONFIG_MAX_DELAY])
                        )
            except asyncio.CancelledError:
                logger.info("Процесс смены фото профиля остановлен (CancelledError)")
                break
            except Exception as e:
                logger.exception(f"Ошибка в цикле: {type(e).__name__}: {e}")
                consecutive_errors += 1
                sleep_duration = base_sleep_time * (2**consecutive_errors)
                await asyncio.sleep(min(sleep_duration, self.config[CONFIG_MAX_DELAY]))

    async def _process_pfpdir(self):
        """Обработка команды pfpdir для загрузки фото из директории."""
        async with self._lock:
            if self.running or self.pfpdir_running:
                logger.warning(self.strings["already_running"])
                return
            directory = self.config[CONFIG_PFPDIR_PATH]

            if not os.path.isdir(directory):
                logger.warning(self.strings["dir_not_found"].format(path=directory))
                return
            photos = [
                f
                for f in os.listdir(directory)
                if (
                    f.endswith((".jpg", ".jpeg", ".png"))
                    and any(c.isdigit() for c in f)
                )
            ]

            photos = self._sort_photos(photos)

            logger.info("Отсортированные фото:")
            for photo in photos[:10]:
                number = re.findall(r"\d+", photo)[-1]
                logger.info(f"Файл: {photo}, Номер: {number}")
            if not photos:
                logger.warning(self.strings["no_photos"])
            await self._init_photo_upload_session(photos)

    def _format_time(self, seconds: float) -> str:
        """Форматирование времени в человекочитаемый вид."""
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{int(hours)}ч {int(minutes)}м"
        elif minutes:
            return f"{int(minutes)}м {int(round(seconds))}с"
        return f"{int(round(seconds))}с"

    def _get_delay_details(self) -> str:
        """Формирование информации о факторах, влияющих на задержку."""
        details = []
        now = datetime.now()

        if self.success_streak >= 5:
            details.append(self.strings["delay_details_success"])
        recent_flood = any(
            (now - flood_time).total_seconds() < 3600 for flood_time in self.floods
        )
        if recent_flood:
            details.append(self.strings["delay_details_recent_flood"])
        if (
            self.last_error_time
            and (now - self.last_error_time).total_seconds()
            < self.config[CONFIG_MAX_DELAY]
        ):
            details.append(self.strings["delay_details_recent_error"])
        details.append(self.strings["delay_details_weighted_multiplier"])

        if self.config[CONFIG_JITTER] > 0:
            details.append(
                self.strings["delay_details_jitter"].format(
                    self.config[CONFIG_JITTER] * 100
                )
            )
        return "\n".join(details) if details else "  • Нет активных факторов адаптации"

    def _get_stats(self) -> Dict[str, Union[str, float, int]]:
        """Get comprehensive statistics about the module's operation."""
        now = datetime.now(timezone.utc)

        status = "🟢 Работает" if self.running else "🔴 Остановлен"
        if self.pfpdir_running:
            status = "📁 Загрузка из директории"
        uptime = "0с"
        if self.start_time:
            start_time_utc = (
                self.start_time
                if self.start_time.tzinfo
                else self.start_time.replace(tzinfo=timezone.utc)
            )
            uptime_seconds = (now - start_time_utc).total_seconds()
            uptime = self._format_time(uptime_seconds)
        updates_per_hour = 0
        if self.start_time and self.update_count > 0:
            start_time_utc = (
                self.start_time
                if self.start_time.tzinfo
                else self.start_time.replace(tzinfo=timezone.utc)
            )
            hours = (now - start_time_utc).total_seconds() / 3600
            if hours > 0:
                updates_per_hour = round(self.update_count / hours, 1)
        last_update = "нет"
        if self.last_update:
            last_update_utc = (
                self.last_update
                if self.last_update.tzinfo
                else self.last_update.replace(tzinfo=timezone.utc)
            )
            seconds_ago = (now - last_update_utc).total_seconds()
            last_update = f"{self._format_time(seconds_ago)} назад"
        current_delay = self.delay
        if self.config[CONFIG_JITTER] > 0:
            jitter_range = self.delay * self.config[CONFIG_JITTER]
            current_delay += random.uniform(-jitter_range, jitter_range)
        delay_details = "\n" + self._get_delay_details()

        wait_time = None
        if self.running and self.last_update:
            last_update_utc = (
                self.last_update
                if self.last_update.tzinfo
                else self.last_update.replace(tzinfo=timezone.utc)
            )
            next_update = last_update_utc + timedelta(seconds=current_delay)
            if next_update > now:
                wait_seconds = (next_update - now).total_seconds()
                wait_time = self._format_time(wait_seconds)
        stats = {
            "status": status,
            "uptime": uptime,
            "count": f"{self.update_count}",
            "hourly": f"{updates_per_hour}/час",
            "delay": f"{round(current_delay / 60, 1)}",
            "last": last_update,
            "errors": f"{self.error_count} (флуд: {self.flood_count})",
            "floods": str(self.flood_count),
            "delay_details": delay_details,
        }

        if wait_time:
            stats["wait"] = wait_time
        return stats

    def _save_state(self):
        """Сохранение текущего состояния модуля в базу данных."""
        try:
            self._db.set(self.strings["name"], "state", json.dumps(self._get_state()))
        except TypeError as e:
            logger.error(f"Ошибка сериализации состояния: {e}")

    def _reset(self):
        """Сброс состояния модуля к начальным значениям."""
        self._init_state()

    async def _start(self, chat_id: int, message_id: int) -> None:
        """Запуск процесса автоматической смены фотографии."""
        self._reset()
        async with self._lock:
            if self.running or self.pfpdir_running:
                return
            self.running = True
            self.start_time = datetime.now()
            self.chat_id = chat_id
            self.message_id = message_id
            self._save_state()
            self._task = asyncio.create_task(self._loop())
            logger.info("Profile changer started")

    async def _send_stopping(self):
        """Отправка сообщения об остановке процесса."""
        uptime = (
            self._format_time((datetime.now() - self.start_time).total_seconds())
            if self.start_time
            else "0с"
        )
        logger.info(
            self.strings["stopping"].format(
                self.update_count,
                uptime,
                self.error_count,
            )
        )

    async def _stop(self) -> None:
        """Остановка процесса автоматической смены фотографии."""
        if not self.running and not self.pfpdir_running:
            return
        self.running = False
        self.pfpdir_running = False

        try:
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            await self._save_state()
            await self._send_stopping()

            logger.info("Profile changer stopped successfully")
        except Exception as e:
            logger.error(f"Ошибка при остановке Profile changer: {e}")
            self._reset()

    def _sort_photos(self, photos: List[str]) -> List[str]:
        """Сортировка фотографий по номеру в имени файла в обратном порядке.
        Корректно обрабатывает числа разной длины."""

        def extract_number(filename):
            numbers = re.findall(r"\d+", filename)
            if not numbers:
                return 0
            last_number = numbers[-1]
            return int(last_number.zfill(10))

        return sorted(photos, key=extract_number, reverse=True)

    async def _validate_photo(self, path: str) -> bool:
        """Проверка существования и валидности фото."""
        if not os.path.exists(path):
            logger.error(f"File not found: {path}")
            return False
        max_size = 10 * 1024 * 1024
        if os.path.getsize(path) > max_size:
            logger.error(f"File too large: {path}")
            return False
        return True

    async def _init_photo_upload_session(self, photos: List[str]):
        """Инициализация сессии загрузки фотографий."""
        try:
            if self.running or self.pfpdir_running:
                logger.info("Сессия уже запущена")
                return
            self._reset()

            self.pfpdir_running = True
            self.start_time = datetime.now()

            self._save_state()

            asyncio.create_task(self._process_photo_upload_session(photos))
        except Exception as e:
            self.pfpdir_running = False
            logger.exception(f"Ошибка в _init_photo_upload_session: {e}")
            raise

    async def _process_photo_upload_session(self, photos: List[str]):
        """Обработка сессии загрузки фотографий."""
        uploaded = errors = 0
        total_photos = len(photos)
        pfpdir_path = self.config[CONFIG_PFPDIR_PATH]

        for index, photo in enumerate(photos, 1):
            if not self.pfpdir_running:
                logger.info("Загрузка прервана пользователем.")
                break
            photo_path = os.path.join(pfpdir_path, photo)
            logger.info(f"Обработка фото {index}/{total_photos}: {photo}")

            success = await self._upload_photo(photo_path)
            if success:
                uploaded += 1
                try:
                    os.remove(photo_path)
                except OSError as e:
                    logger.error(f"Ошибка при удалении {photo}: {e}")
            else:
                errors += 1
                logger.error(f"Ошибка при загрузке фотографии: {photo}")
            calculated_delay = self._calculate_delay()
            logger.info(
                f"Ожидание перед следующей загрузкой: {calculated_delay:.1f} секунд"
            )
            await asyncio.sleep(calculated_delay)

            self.last_update = datetime.now()
            self.update_count += 1
            self._save_state()
        self.pfpdir_running = False
        elapsed_time = datetime.now() - self.start_time
        logger.info(
            f"Сессия загрузки завершена. Загружено: {uploaded}, Удалено: {uploaded}, Ошибок: {errors}, Время: {elapsed_time}"
        )

    @loader.command()
    async def pfp(self, message):
        """Запустить смену фото профиля (ответьте на сообщение с фото)."""
        async with self._lock:
            if self.running or self.pfpdir_running:
                await utils.answer(message, self.strings["already_running"])
                return
            target = await message.get_reply_message() if message.is_reply else message
            photo_entity = target.photo if target else None

            if not photo_entity:
                await utils.answer(message, self.strings["no_photo"])
                return
            await self._start(message.chat_id, target.id)
            await utils.answer(
                message,
                self.strings["starting"].format(
                    round(self.delay / 60),
                    round(3600 / self.delay),
                ),
            )

    @loader.command()
    async def pfpstop(self, message):
        """Остановить смену фото профиля."""
        try:
            async with self._lock:
                if not self.running and not self.pfpdir_running:
                    await utils.answer(message, self.strings["not_running"])
                    return
                stop_tasks = []
                if self.running:
                    stop_tasks.append(self._stop())
                if self.pfpdir_running:
                    self.pfpdir_running = False
                    self._save_state()
                if stop_tasks:
                    await asyncio.wait(stop_tasks, timeout=10)
            await utils.answer(message, self.strings["stopped_successfully"])
        except asyncio.TimeoutError:
            await utils.answer(
                message,
                "❌ <b>Превышено время ожидания остановки. Попробуйте позже.</b>",
            )
            self._reset()
        except Exception as e:
            await utils.answer(message, f"❌ Ошибка при остановке: {str(e)}")
            logger.error(f"Ошибка в pfpstop: {e}")
            self._reset()

    @loader.command()
    async def pfpstats(self, message):
        """Показать статистику работы модуля."""
        stats = self._get_stats()

        status = f"{self.strings['stats']}\n"
        status += f"• Статус: {stats['status']}\n"
        status += f"• С момента запуска: {stats['uptime']}\n"
        status += f"• Обновлений: {stats['count']}\n"
        status += f"• В час: {stats['hourly']}\n"
        status += f"• Задержка: {stats['delay']} мин\n"
        status += f"• Последнее: {stats['last']}\n"
        status += f"• Ошибок: {stats['errors']}\n"
        status += f"• Флудвейтов: {stats['floods']}\n"

        if "wait" in stats:
            status += f"• Ожидание: {stats['wait']}\n"
        status += f"\n⚙️ <b>Адаптация задержки:</b>{stats['delay_details']}"

        await utils.answer(message, status)

    @loader.command()
    async def pfpdelay(self, message):
        """Установить задержку между обновлениями в секундах.

        Используйте: .pfpdelay <секунды>
        """
        args = utils.get_args_raw(message)

        if not args:
            return await utils.answer(
                message, "Укажите задержку в секундах после команды."
            )
        try:
            delay = float(args)
            if (
                delay < self.config[CONFIG_MIN_DELAY]
                or delay > self.config[CONFIG_MAX_DELAY]
            ):
                return await utils.answer(
                    message,
                    f"Задержка должна быть от {self.config[CONFIG_MIN_DELAY]} до {self.config[CONFIG_MAX_DELAY]} секунд",
                )
            self.delay = delay
            self._save_state()
            await utils.answer(message, f"✅ Установлена задержка {delay} секунд")
        except ValueError:
            await utils.answer(
                message, "❌ Неверный формат числа. Введите число секунд."
            )

    @loader.command()
    async def pfpdir(self, message):
        """Загрузить фотографии из директории."""
        try:
            await self._process_pfpdir()
        except Exception as e:
            self.pfpdir_running = False
            logger.exception(f"Ошибка в pfpdir: {e}")
            await utils.answer(message, f"❌ Ошибка: {str(e)}")

    @loader.command()
    async def pfpon(self, message):
        """Установить аватарку один раз (ответьте на сообщение с фото)."""
        reply = await message.get_reply_message()
        if not reply or not reply.photo:
            await utils.answer(message, self.strings["pfpone_no_reply"])
            return
        photo = reply.photo
        result = await self._set_profile_photo(photo)
        if isinstance(result, bool) and result:
            await utils.answer(message, self.strings["pfpone_success"])
        else:
            await utils.answer(
                message,
                self.strings["error"].format(
                    error_symbol="❌",
                    error_type="Ошибка установки аватарки",
                    error=result,
                ),
            )

    @loader.command()
    async def pfpnight(self, message):
        """Включить/выключить ночной режим или изменить его настройки.

        Использование:
        .pfpnight - переключить ночной режим
        .pfpnight <start> <end> - установить время (например: .pfpnight 23 7)
        """
        args = utils.get_args_raw(message)

        if not args:
            self.config[CONFIG_NIGHT_MODE] = not self.config[CONFIG_NIGHT_MODE]
            status = "включен ✅" if self.config[CONFIG_NIGHT_MODE] else "выключен ❌"
            local_time = self._get_local_time()
            await utils.answer(
                message,
                f"🌙 Ночной режим {status}\n"
                f"Текущее время: {local_time.strftime('%H:%M')} (UTC+{self.config[CONFIG_TIMEZONE_OFFSET]})",
            )
            return
        try:
            start, end = map(int, args.split())
            if not (0 <= start <= 23 and 0 <= end <= 23):
                raise ValueError
            self.config[CONFIG_NIGHT_START] = start
            self.config[CONFIG_NIGHT_END] = end

            local_time = self._get_local_time()
            await utils.answer(
                message,
                f"🌙 Установлен период ночного режима:\n"
                f"• {start:02d}:00 - {end:02d}:00 (UTC+{self.config[CONFIG_TIMEZONE_OFFSET]})\n"
                f"Текущее время: {local_time.strftime('%H:%M')}",
            )
        except ValueError:
            await utils.answer(
                message,
                "❌ Неверный формат. Используйте: .pfpnight <час_начала> <час_конца> (0-23)",
            )

    @loader.command()
    async def pfpzip(self, message):
        """Загрузить фотографии из zip архива. Ответьте на сообщение с zip файлом."""
        try:
            reply = await message.get_reply_message()
            if (
                not reply
                or not reply.document
                or not reply.document.mime_type == "application/zip"
            ):
                return await utils.answer(
                    message, "❌ <b>Ответьте на сообщение с zip архивом</b>"
                )
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, "photos.zip")
                await reply.download_media(file=zip_path)

                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    photo_files = [
                        f
                        for f in zip_ref.namelist()
                        if f.lower().endswith((".jpg", ".jpeg", ".png"))
                        and not f.startswith("__MACOSX")
                        and not f.startswith(".")
                    ]

                    if not photo_files:
                        return await utils.answer(
                            message, "❌ <b>В архиве нет подходящих фотографий</b>"
                        )
                    pfp_dir = self.config[CONFIG_PFPDIR_PATH]
                    os.makedirs(pfp_dir, exist_ok=True)

                    for photo in photo_files:
                        zip_ref.extract(photo, temp_dir)
                        photo_path = os.path.join(temp_dir, photo)
                        photo_name = os.path.basename(photo)
                        destination = os.path.join(pfp_dir, photo_name)
                        shutil.move(photo_path, destination)
            await utils.answer(
                message,
                f"✅ <b>Успешно распаковано {len(photo_files)} фото в директорию аватарок</b>",
            )

            if photo_files:
                await self._process_pfpdir()
        except zipfile.BadZipFile:
            await utils.answer(message, "❌ <b>Ошибка: Поврежденный zip архив</b>")
        except Exception as e:
            await utils.answer(
                message, f"❌ <b>Ошибка при обработке архива:</b> {str(e)}"
            )
