"""
♨️ Profile Changer
➕ Developer: @xdesai
♻️ Optimized: @kramiikk

Модуль автоматического обновления фото профиля
с адаптивной системой защиты от ограничений.
"""

import asyncio
import logging
from datetime import datetime
from collections import deque
from typing import Optional, Dict
from telethon import functions, types, errors
from telethon.errors.rpcerrorlist import (
    MessageIdInvalidError,
    PhotoInvalidDimensionsError,
    PhotoCropSizeSmallError,
    PhotoSaveFileInvalidError,
)
from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class ProfileChangerMod(loader.Module):
    """Автоматическое обновление фото профиля с адаптивной системой защиты"""

    strings = {
        "name": "ProfileChanger",
        "starting": "🔄 <b>Запуск смены фото профиля</b>\n\n• Задержка: {delay_minutes:.1f} мин\n• ~{updates_per_hour:.1f} обновлений/час\n• Режим: {mode}",
        "stopping": "🛑 <b>Остановка</b>\n\n• Обновлений: {count}\n• Время: {uptime}\n• Ошибок: {errors}",
        "stats": "📊 <b>Статистика</b>\n\n• Статус: {status}\n• Время: {uptime}\n• Обновлений: {count}\n• В час: {hourly}\n• Задержка: {delay:.1f} мин\n• Последнее: {last}\n• Ошибок: {errors}\n• Флудвейтов: {floods}",
        "no_photo": "❌ <b>Ответьте на фото</b>",
        "already_running": "⚠️ <b>Уже запущено</b>",
        "not_running": "⚠️ <b>Не запущено</b>",
        "error": "❌ <b>Ошибка:</b> {error}",
        "flood_wait": "⚠️ <b>Флудвейт</b>\n\n• Новая задержка: {delay:.1f} мин\n• Ожидание: {wait:.1f} мин",
        "photo_invalid": "⚠️ <b>Неверный формат фото:</b> {error}",
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
    ]

    def __init__(self):
        self.config = loader.ModuleConfig(
            "safe_mode",
            True,
            "Безопасный режим",
            "adaptive_delay",
            True,
            "Адаптивные задержки",
            "notify_errors",
            True,
            "Уведомления об ошибках",
            "default_delay",
            780,
            "Начальная задержка (сек)",
            "min_delay",
            420,
            "Минимальная задержка (сек)",
            "max_delay",
            1980,
            "Максимальная задержка (сек)",
            "jitter",
            0.3,
            "Случайность (0.0-1.0)",
            "error_threshold",
            2,
            "Порог ошибок",
            "flood_multiplier",
            1.2,
            "Множитель флудвейта",
            "success_reduction",
            0.9,
            "Снижение при успехе",
        )
        self._reset()

    def _reset(self) -> None:
        """Сброс состояния"""
        self.running = False
        self._task = None
        self.start_time = None
        self.last_update = None
        self.update_count = 0
        self.error_count = 0
        self.flood_count = 0
        self.delay = self.config["default_delay"]
        self.chat_id = None
        self.message_id = None
        self.floods = deque(maxlen=10)
        self.success_streak = 0
        self._retries = 0
        self._lock = asyncio.Lock()
        self._last_command_time = None

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._me = await client.get_me()
        self._load_state()
        if self.running:
            self._task = asyncio.create_task(self._loop())
        logger.info("ProfileChanger loaded")

    async def on_unload(self):
        """Выгрузка модуля"""
        if self.running:
            await self._stop("модуль выгружен")
        logger.info("ProfileChanger unloaded")

    def _get_state(self) -> Dict:
        return {key: getattr(self, key) for key in self._state_keys}

    def _save_state(self) -> None:
        try:
            self._db.set(self.strings["name"], "state", self._get_state())
        except Exception as e:
            logger.error(f"Ошибка сохранения состояния: {e}")

    def _load_state(self) -> None:
        state = self._db.get(self.strings["name"], "state")
        if not state:
            return
        try:
            for key, value in state.items():
                if key == "start_time" and value:
                    setattr(self, key, datetime.fromisoformat(value))
                elif key == "last_update" and value:
                    setattr(self, key, datetime.fromisoformat(value))
                elif key == "floods":
                    setattr(
                        self,
                        key,
                        deque([datetime.fromisoformat(t) for t in value], maxlen=10),
                    )
                else:
                    setattr(self, key, value)
        except Exception as e:
            logger.error(f"Ошибка загрузки состояния: {e}")
            self._reset()

    async def _get_photo(self) -> Optional[types.Photo]:
        """Получение фото"""
        if not self.running:
            return None
        try:
            message = await self._client.get_messages(self.chat_id, ids=self.message_id)
            if not message or not message.photo:
                await self._stop("фото удалено")
                return None
            return message.photo
        except MessageIdInvalidError:
            await self._stop("фото удалено")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения фото: {e}")
            return None

    async def _update(self) -> bool:
        """Обновление фото"""
        if not self.running:
            return False
        photo = await self._get_photo()
        if not photo:
            return False
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

            self.last_update = datetime.now()
            self.update_count += 1
            self.success_streak += 1
            self._retries = 0
            logger.info(
                f"Photo updated successfully. Total updates: {self.update_count}"
            )
            return True
        except errors.FloodWaitError as e:
            self.flood_count += 1
            self.floods.append(datetime.now())
            self.success_streak = 0
            self.delay = min(
                self.config["max_delay"], self.delay * self.config["flood_multiplier"]
            )

            if self.config["notify_errors"]:
                await self._client.send_message(
                    self.chat_id,
                    self.strings["flood_wait"].format(
                        delay=self.delay / 60, wait=e.seconds / 60
                    ),
                )
            logger.warning(f"FloodWait error: {e.seconds}s. New delay: {self.delay}s")
            await asyncio.sleep(e.seconds)
            return False
        except (
            PhotoInvalidDimensionsError,
            PhotoCropSizeSmallError,
            PhotoSaveFileInvalidError,
        ) as e:
            self.error_count += 1
            if self.config["notify_errors"]:
                await self._client.send_message(
                    self.chat_id, self.strings["photo_invalid"].format(error=str(e))
                )
            await self._stop(f"неверный формат: {e}")
            return False
        except Exception as e:
            self.error_count += 1
            self.success_streak = 0
            self._retries += 1

            if self.config["notify_errors"]:
                await self._client.send_message(
                    self.chat_id, self.strings["error"].format(error=str(e))
                )
            logger.error(f"Update error: {e}")
            return False

    def _calculate_delay(self) -> float:
        """Расчет задержки"""
        if not self.config["adaptive_delay"]:
            return self.delay
        delay = self.delay

        now = datetime.now()
        while self.floods and (now - self.floods[0]).total_seconds() > 3600:
            self.floods.popleft()
        if self.success_streak >= 5:
            delay = max(
                self.config["min_delay"], delay * self.config["success_reduction"]
            )
        if self.floods:
            recent = len(self.floods)
            delay = min(
                self.config["max_delay"],
                delay * (self.config["flood_multiplier"] ** recent),
            )
        import random

        jitter = random.uniform(1 - self.config["jitter"], 1 + self.config["jitter"])
        return max(self.config["min_delay"], delay * jitter)

    async def _loop(self) -> None:
        """Основной цикл"""
        while self.running:
            try:
                if await self._update():
                    await asyncio.sleep(self._calculate_delay())
                else:
                    if self._retries >= self.config["error_threshold"]:
                        await self._stop("превышен порог ошибок")
                        break
                    await asyncio.sleep(self.config["min_delay"])
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Ошибка в цикле: {e}")
                await asyncio.sleep(self.config["min_delay"])

    def _format_time(self, seconds: float) -> str:
        """Форматирование времени"""
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{int(hours)}ч {int(minutes)}м"
        elif minutes:
            return f"{int(minutes)}м {round(seconds)}с"
        return f"{round(seconds)}с"

    def _get_stats(self) -> Dict[str, str]:
        """Получение статистики"""
        now = datetime.now()
        uptime = (now - self.start_time).total_seconds() if self.start_time else 0
        last = (now - self.last_update).total_seconds() if self.last_update else 0

        return {
            "status": "✅ Работает" if self.running else "🛑 Остановлен",
            "uptime": self._format_time(uptime),
            "count": str(self.update_count),
            "hourly": f"{self.update_count / (uptime/3600):.1f}" if uptime > 0 else "0",
            "delay": self.delay / 60,
            "last": self._format_time(last) if self.last_update else "никогда",
            "errors": str(self.error_count),
            "floods": str(self.flood_count),
        }

    async def _start(self, chat_id: int, message_id: int) -> None:
        """Запуск смены фото"""
        self.running = True
        self.start_time = datetime.now()
        self.chat_id = chat_id
        self.message_id = message_id
        self._retries = 0
        self._save_state()
        self._task = asyncio.create_task(self._loop())
        logger.info("Profile changer started")

    async def _stop(self, reason: Optional[str] = None) -> None:
        """Остановка смены фото"""
        if self.running:
            self.running = False
            self._save_state()
            if self._task:
                self._task.cancel()
            await self._client.send_message(
                self.chat_id,
                self.strings["stopping"].format(
                    count=self.update_count,
                    uptime=(
                        self._format_time(
                            (datetime.now() - self.start_time).total_seconds()
                        )
                        if self.start_time
                        else "0с"
                    ),
                    errors=self.error_count,
                )
                + (f"\n\nПричина: {reason}" if reason else ""),
            )
            logger.info(f"Profile changer stopped. {reason if reason else ''}")
            self._reset()

    @loader.command()
    async def pfp(self, message):
        """Запустить смену фото (ответ на фото)"""
        async with self._lock:
            if self.running:
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
                    delay_minutes=self.delay / 60,
                    updates_per_hour=3600 / self.delay,
                    mode="Безопасный" if self.config["safe_mode"] else "Стандартный",
                ),
            )

    @loader.command()
    async def pfpstop(self, message):
        """Остановить смену фото"""
        async with self._lock:
            if not self.running:
                await utils.answer(message, self.strings["not_running"])
                return
            await self._stop("остановлено пользователем")

    @loader.command()
    async def pfpstats(self, message):
        """Показать статистику"""
        await utils.answer(message, self.strings["stats"].format(**self._get_stats()))

    @loader.command()
    async def pfpdelay(self, message):
        """Установить задержку в секундах (используйте: .pfpdelay <секунды>)"""
        args = utils.get_args_raw(message)

        if not args:
            return await utils.answer(
                message, "Укажите задержку в секундах после команды."
            )
        try:
            delay = float(args)
            if delay < self.config["min_delay"] or delay > self.config["max_delay"]:
                return await utils.answer(
                    message,
                    f"Задержка должна быть от {self.config['min_delay']} до {self.config['max_delay']} секунд",
                )
            self.delay = delay
            self._save_state()
            await utils.answer(message, f"✅ Установлена задержка {delay} секунд")
        except ValueError:
            await utils.answer(message, "❌ Неверный формат числа")
