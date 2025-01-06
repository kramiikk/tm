"""
♨️ Profile Changer
➕ Developer: @xdesai
♻️ Optimized: @kramiikk

Модуль для автоматического обновления фото профиля
с адаптивной системой защиты от ограничений.

🛠️ Команды:
• .pfp <reply to photo> - Запустить смену фото
• .pfpstop - Остановить смену фото
• .pfpstats - Статистика работы

ℹ️ Возможности:
• Частое обновление фото профиля
• Защита от флудвейтов и блокировок
• Умное управление задержками
• Статистика работы
• Сохранение состояния после перезапуска
"""

import asyncio
import logging
import random
from datetime import datetime
from collections import deque
from typing import Optional, Deque, Dict
from telethon import functions, types, errors
from telethon.errors.rpcerrorlist import MessageIdInvalidError
from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class ProfileChangerMod(loader.Module):
    """Автоматическое обновление фото профиля"""

    strings = {
        "name": "ProfileChanger",
        "starting": (
            "🔄 <b>Запуск смены фото профиля</b>\n\n"
            "• Начальная задержка: <code>{delay_minutes}</code> мин\n"
            "• Примерно <code>{updates_per_hour}</code> обновлений в час (начальное значение)\n"
            "• Режим работы: {mode}\n\n"
            "<i>Используйте .pfpstats для просмотра статистики</i>"
        ),
        "stopping": (
            "🛑 <b>Остановка смены фото</b>\n\n"
            "• Всего обновлений: {count}\n"
            "• Время работы: {uptime}\n"
            "• Ошибок: {errors}\n\n"
            "<i>Смена фото остановлена пользователем.</i>"
        ),
        "stats": (
            "📊 <b>Статистика Profile Changer</b>\n\n"
            "• Статус: {status}\n"
            "• Время работы: {uptime}\n"
            "• Всего обновлений: {count}\n"
            "• Обновлений в час: {hourly:.1f}\n"
            "• Текущая задержка: {current_delay_minutes} мин\n"
            "• Последнее обновление: {last}\n"
            "• Ошибок: {errors}\n"
            "• Флудвейтов: {floods}"
        ),
        "no_photo": "❌ <b>Ответьте на фото или отправьте фото с командой</b>",
        "already_running": "⚠️ <b>Смена фото уже запущена</b>",
        "not_running": "⚠️ <b>Смена фото не запущена</b>",
        "error": "❌ <b>Произошла ошибка:</b> <code>{error}</code>",
        "flood_wait": (
            "⚠️ <b>Получено ограничение от Telegram</b>\n"
            "• Новая задержка: {new_delay_minutes} мин\n"
            "• Восстановление через: {wait_minutes} мин"
        ),
        "photo_deleted": "📸 <b>Сообщение с фото было удалено. Остановка смены фото.</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "safe_mode",
            True,
            "Безопасный режим работы (рекомендуется)",
            "adaptive_delay",
            True,
            "Умное управление задержками",
            "notify_errors",
            True,
            "Уведомлять об ошибках",
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
            "Случайность задержки",
            "error_threshold",
            2,
            "Порог ошибок до остановки",
            "retry_delay",
            330,
            "Начальная задержка повтора (сек)",
            "max_retry_delay",
            3600,
            "Макс. задержка повтора (сек)",
            "min_adaptive_delay",
            300,
            "Мин. задержка адаптивного режима (сек)",
        )
        self._reset_state(initial=True)
        self._running_lock = asyncio.Lock()

    async def client_ready(self, client, db):
        """Инициализация при запуске клиента."""
        self.client = client
        self.db = db
        self._me = await client.get_me()
        self._load_state()
        if self.running:
            self.task = asyncio.create_task(self._main_loop())

    def _load_state(self):
        """Загрузка состояния модуля из базы данных."""
        saved_state = self.db.get(self.strings["name"], "state", None)
        if saved_state:
            self._apply_state(saved_state)

    def _save_state(self):
        """Сохранение текущего состояния модуля."""
        self.db.set(self.strings["name"], "state", self._get_current_state())

    def _get_current_state(self) -> Dict:
        """Получение текущего состояния модуля для сохранения."""
        return {
            "running": self.running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "update_count": self.update_count,
            "error_count": self.error_count,
            "flood_count": self.flood_count,
            "current_delay": self.current_delay,
            "chat_id": self.chat_id,
            "message_id": self.message_id,
            "success_streak": self.success_streak,
            "_retry_delay": self._retry_delay,
        }

    def _apply_state(self, state: Dict):
        """Применение сохраненного состояния модуля."""
        self.running = state.get("running", False)
        try:
            self.start_time = (
                datetime.fromisoformat(state.get("start_time"))
                if state.get("start_time")
                else None
            )
            self.last_update = (
                datetime.fromisoformat(state.get("last_update"))
                if state.get("last_update")
                else None
            )
        except ValueError as e:
            logger.warning(
                f"Ошибка при загрузке даты из сохраненного состояния: {e}. Состояние будет сброшено."
            )
            return
        self.update_count = state.get("update_count", 0)
        self.error_count = state.get("error_count", 0)
        self.flood_count = state.get("flood_count", 0)
        self.current_delay = state.get("current_delay", self.config["default_delay"])
        self.chat_id = state.get("chat_id")
        self.message_id = state.get("message_id")
        self.success_streak = state.get("success_streak", 0)
        self._retry_delay = state.get("_retry_delay", self.config["retry_delay"])

    async def _get_photo(self) -> Optional[types.Photo]:
        """Получение фото из сохраненного сообщения"""
        if not self.chat_id or not self.message_id:
            return None
        try:
            message = await self.client.get_messages(self.chat_id, ids=self.message_id)
            return message.photo if message and message.photo else None
        except MessageIdInvalidError:
            logger.warning("Сообщение с фото не найдено.")
            if self.running:
                await self._handle_photo_deletion()
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении фото: {e}")
            return None

    async def _handle_photo_deletion(self):
        """Обработка ситуации, когда фото удалено."""
        await self._stop_pfp(notify=True, reason="удаления сообщения с фото")
        self.chat_id = None
        self.message_id = None
        self._save_state()

    async def _update_photo(self) -> bool:
        """Обновление фото профиля"""
        photo = await self._get_photo()
        if not photo:
            return False
        try:
            await self.client(
                functions.photos.UpdateProfilePhotoRequest(
                    id=types.InputPhoto(
                        id=photo.id,
                        access_hash=photo.access_hash,
                        file_reference=photo.file_reference,
                    )
                )
            )
            self._on_photo_updated()
            return True
        except errors.FloodWaitError as e:
            await self._handle_flood_wait(e)
            return False
        except Exception as e:
            await self._handle_update_error(e)
            return False

    def _on_photo_updated(self):
        """Действия после успешного обновления фото."""
        self.last_update = datetime.now()
        self.update_count += 1
        self.success_streak += 1
        self._retry_delay = self.config["retry_delay"]
        self._retries_attempted = 0
        self._save_state()

    async def _handle_flood_wait(self, error: errors.FloodWaitError):
        """Обработка ошибки FloodWait."""
        self._update_state(flood_count=self.flood_count + 1, success_streak=0)
        self.flood_history.append(datetime.now())
        new_delay = min(self.config["max_delay"], self.current_delay * 1.5)
        wait_time = error.seconds / 60
        logger.warning(
            f"FloodWaitError encountered. New delay: {new_delay / 60:.1f} min, Wait time: {wait_time:.1f} min"
        )
        if self.config["notify_errors"]:
            asyncio.create_task(
                self.client.send_message(
                    self.chat_id,
                    self.strings["flood_wait"].format(
                        new_delay_minutes=f"{new_delay/60:.1f}",
                        wait_minutes=f"{wait_time:.1f}",
                    ),
                )
            )
        self.current_delay = new_delay
        self._save_state()
        asyncio.create_task(asyncio.sleep(error.seconds))

    async def _handle_update_error(self, error: Exception):
        """Обработка ошибок при обновлении фото."""
        logger.error(f"Ошибка обновления фото пользователя {self._me.id}: {error}")
        self._update_state(error_count=self.error_count + 1, success_streak=0)
        self._retries_attempted += 1
        self._retry_delay = min(self._retry_delay * 2, self.config["max_retry_delay"])
        logger.info(
            f"Ошибка обновления, увеличена задержка повторной попытки до {self._retry_delay} секунд."
        )
        if self.config["notify_errors"]:
            asyncio.create_task(
                self.client.send_message(
                    self.chat_id, self.strings["error"].format(error=str(error))
                )
            )
        self._save_state()

    def _update_state(self, **kwargs):
        """Обновление состояния модуля и сохранение."""
        for key, value in kwargs.items():
            setattr(self, key, value)
        self._save_state()

    def _calculate_delay(self) -> float:
        """Расчет адаптивной задержки"""
        if not self.config["adaptive_delay"]:
            return self.current_delay
        base_delay = self.current_delay

        if self.success_streak >= 5:
            base_delay = max(self.config["min_delay"], base_delay * 0.9)
        time_since_last_flood = float("inf")
        if self.flood_history:
            time_since_last_flood = (
                datetime.now() - self.flood_history[-1]
            ).total_seconds()
        if time_since_last_flood < 3600 * 3:
            recent_floods = sum(
                1
                for t in self.flood_history
                if (datetime.now() - t).total_seconds() < 3600
            )
            if recent_floods > 0:
                base_delay = min(
                    self.config["max_delay"], base_delay * (1 + recent_floods * 0.2)
                )
        jitter = random.uniform(1 - self.config["jitter"], 1 + self.config["jitter"])
        calculated_delay = base_delay * jitter
        calculated_delay = max(self.config["min_adaptive_delay"], calculated_delay)
        logger.debug(
            f"Рассчитанная задержка: {calculated_delay:.1f}с, success_streak: {self.success_streak}, time_since_last_flood: {time_since_last_flood:.1f}"
        )
        return calculated_delay

    async def _main_loop(self) -> None:
        """Основной цикл работы модуля"""
        while self.running:
            try:
                if await self._update_photo():
                    await asyncio.sleep(self._calculate_delay())
                else:
                    if self._retries_attempted >= self.config["error_threshold"]:
                        logger.warning(
                            f"Смена фото остановлена из-за {self._retries_attempted} неудачных попыток или достижения порога ошибок."
                        )
                        await self._stop_pfp()
                        break
                    logger.info(
                        f"Повторная попытка обновления через {self.config['retry_delay']} секунд."
                    )
                    await asyncio.sleep(self.config["retry_delay"])
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(
                    f"Ошибка в главном цикле пользователя {self._me.id}: {e}"
                )
                await asyncio.sleep(self.config["retry_delay"])

    def _format_time(self, seconds: float) -> str:
        """Форматирование времени"""
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:.0f}ч {minutes:.0f}м"
        elif minutes:
            return f"{minutes:.0f}м {seconds:.0f}с"
        else:
            return f"{seconds:.0f}с"

    def _get_stats(self) -> Dict[str, str]:
        """Получение статистики работы"""
        now = datetime.now()
        uptime_seconds = (
            (now - self.start_time).total_seconds() if self.start_time else 0
        )
        last_update_seconds = (
            (now - self.last_update).total_seconds() if self.last_update else 0
        )

        return {
            "status": "✅ Работает" if self.running else "🛑 Остановлен",
            "uptime": self._format_time(uptime_seconds),
            "count": str(self.update_count),
            "hourly": (
                f"{self.update_count / (uptime_seconds / 3600):.1f}"
                if uptime_seconds > 0
                else "0"
            ),
            "current_delay_minutes": f"{self.current_delay / 60:.1f}",
            "last": (
                self._format_time(last_update_seconds)
                if self.last_update
                else "никогда"
            ),
            "errors": str(self.error_count),
            "floods": str(self.flood_count),
        }

    @loader.command()
    async def pfp(self, message):
        """Запустить смену фото (ответьте на фото)"""
        async with self._running_lock:
            if self.running:
                await utils.answer(message, self.strings["already_running"])
                return
            reply = await message.get_reply_message()
            target = (
                reply if reply and reply.photo else message if message.photo else None
            )

            if not target or not target.photo:
                await utils.answer(message, self.strings["no_photo"])
                return
            try:
                self._start_pfp(message.chat_id, target.id)
                await utils.answer(
                    message,
                    self.strings["starting"].format(
                        delay_minutes=f"{self.current_delay/60:.1f}",
                        updates_per_hour=f"{3600 / self.current_delay:.1f}",
                        mode=f"{'Безопасный' if self.config['safe_mode'] else 'Стандартный'}",
                    ),
                )
                logger.info(f"Profile changer started by user {self._me.id}.")
                self.task = asyncio.create_task(self._main_loop())
            except Exception as e:
                logger.exception(
                    f"Ошибка при запуске смены фото пользователем {self._me.id}: {e}"
                )
                await utils.answer(message, self.strings["error"].format(error=str(e)))
                self._reset_state()
                logger.error("Ошибка при запуске смены фото, состояние сброшено.")

    def _start_pfp(self, chat_id: int, message_id: int):
        """Запуск смены фото."""
        self.running = True
        self.start_time = datetime.now()
        self.chat_id = chat_id
        self.message_id = message_id
        self._save_state()
        self._retry_delay = self.config["retry_delay"]
        self._retries_attempted = 0

    @loader.command()
    async def pfpstop(self, message):
        """Остановить смену фото"""
        async with self._running_lock:
            if not self.running:
                await utils.answer(message, self.strings["not_running"])
                return
            await self._stop_pfp(notify=True)

    async def _stop_pfp(self, notify: bool = True, reason: Optional[str] = None):
        """Остановка смены фото."""
        if self.running:
            self.running = False
            self._save_state()
            if self.task:
                self.task.cancel()
                self.task = None
            if notify:
                uptime = (
                    self._format_time(
                        (datetime.now() - self.start_time).total_seconds()
                    )
                    if self.start_time
                    else "0с"
                )
                await self.client.send_message(
                    self.chat_id,
                    self.strings["stopping"].format(
                        count=self.update_count, uptime=uptime, errors=self.error_count
                    ),
                )
            log_message = f"Profile changer stopped by user {self._me.id}."
            if reason:
                log_message += f" Reason: {reason}"
            logger.info(log_message)
            self._reset_state()

    def _reset_state(self, initial: bool = False) -> None:
        """Сброс состояния модуля."""
        self.running = False
        if self.task:
            self.task.cancel()
            self.task = None
        self.start_time: Optional[datetime] = None
        self.last_update: Optional[datetime] = None
        self.update_count = 0
        self.error_count = 0
        self.flood_count = 0
        self.current_delay = self.config["default_delay"]
        self.chat_id: Optional[int] = None
        self.message_id: Optional[int] = None
        self.flood_history: Deque[datetime] = deque(maxlen=10)
        self.success_streak = 0
        self._retry_delay = self.config["retry_delay"]
        self._retries_attempted = 0
        if not initial:
            self.db.set(self.strings["name"], "state", None)

    @loader.command()
    async def pfpstats(self, message):
        """Показать статистику работы"""
        await utils.answer(message, self.strings["stats"].format(**self._get_stats()))
