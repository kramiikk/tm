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
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from collections import deque
from typing import Optional, Deque, Dict
from telethon import functions, types, errors
from .. import loader, utils

logger = logging.getLogger(__name__)

# Константы для настройки модуля
DEFAULT_DELAY = 900  # 15 минут
MIN_DELAY = 600     # 10 минут
MAX_DELAY = 3600    # 1 час
JITTER = 0.1       # 10% случайности в задержке
ERROR_THRESHOLD = 3 # Количество ошибок до остановки
RETRY_DELAY = 60   # Задержка между повторными попытками

@loader.tds
class ProfileChangerMod(loader.Module):
    """Автоматическое обновление фото профиля"""
    
    strings = {
        "name": "ProfileChanger",
        
        # Сообщения о статусе
        "starting": (
            "🔄 <b>Запуск смены фото профиля</b>\n\n"
            "• Начальная задержка: <code>{delay}</code> мин\n"
            "• Примерно <code>{updates}</code> обновлений в час\n"
            "• Режим работы: {mode}\n\n"
            "<i>Используйте .pfpstats для просмотра статистики</i>"
        ),
        "stopping": (
            "🛑 <b>Остановка смены фото</b>\n\n"
            "• Всего обновлений: {count}\n"
            "• Время работы: {time}\n"
            "• Ошибок: {errors}"
        ),
        "stats": (
            "📊 <b>Статистика Profile Changer</b>\n\n"
            "• Статус: {status}\n"
            "• Время работы: {uptime}\n"
            "• Всего обновлений: {count}\n"
            "• Обновлений в час: {hourly:.1f}\n"
            "• Текущая задержка: {delay}\n"
            "• Последнее обновление: {last}\n"
            "• Ошибок: {errors}\n"
            "• Флудвейтов: {floods}"
        ),
        
        # Ошибки
        "no_photo": "❌ <b>Ответьте на фото или отправьте фото с командой</b>",
        "already_running": "⚠️ <b>Смена фото уже запущена</b>",
        "not_running": "⚠️ <b>Смена фото не запущена</b>",
        "error": "❌ <b>Произошла ошибка:</b> <code>{}</code>",
        
        # Уведомления
        "flood_wait": (
            "⚠️ <b>Получено ограничение от Telegram</b>\n"
            "• Новая задержка: {delay} мин\n"
            "• Восстановление через: {wait} мин"
        )
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
            "Уведомлять об ошибках"
        )
        self._reset_state()

    def _reset_state(self) -> None:
        """Сброс состояния модуля"""
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.start_time: Optional[datetime] = None
        self.last_update: Optional[datetime] = None
        self.update_count = 0
        self.error_count = 0
        self.flood_count = 0
        self.current_delay = DEFAULT_DELAY
        self.chat_id: Optional[int] = None
        self.message_id: Optional[int] = None
        self.flood_history: Deque[datetime] = deque(maxlen=10)
        self.success_streak = 0

    async def _get_photo(self) -> Optional[types.Photo]:
        """Получение фото из сохраненного сообщения"""
        try:
            if not self.chat_id or not self.message_id:
                return None
            message = await self.client.get_messages(self.chat_id, ids=self.message_id)
            return message.photo if message and message.photo else None
        except Exception as e:
            logger.error(f"Error getting photo: {e}")
            return None

    async def _update_photo(self) -> bool:
        """Обновление фото профиля"""
        try:
            photo = await self._get_photo()
            if not photo:
                return False

            await self.client(
                functions.photos.UpdateProfilePhotoRequest(
                    id=types.InputPhoto(
                        id=photo.id,
                        access_hash=photo.access_hash,
                        file_reference=photo.file_reference
                    )
                )
            )
            
            self.last_update = datetime.now()
            self.update_count += 1
            self.success_streak += 1
            return True

        except errors.FloodWaitError as e:
            self.flood_count += 1
            self.flood_history.append(datetime.now())
            self.success_streak = 0
            
            # Расчет новой задержки
            new_delay = min(MAX_DELAY, self.current_delay * 1.5)
            wait_time = e.seconds / 60
            
            if self.config["notify_errors"]:
                await self.client.send_message(
                    self.chat_id,
                    self.strings["flood_wait"].format(
                        delay=f"{new_delay/60:.1f}",
                        wait=f"{wait_time:.1f}"
                    )
                )
            
            self.current_delay = new_delay
            await asyncio.sleep(e.seconds)
            return False

        except Exception as e:
            logger.error(f"Error updating photo: {e}")
            self.error_count += 1
            self.success_streak = 0
            
            if self.config["notify_errors"]:
                await self.client.send_message(
                    self.chat_id,
                    self.strings["error"].format(str(e))
                )
            
            return False

    def _calculate_delay(self) -> float:
        """Расчет адаптивной задержки"""
        if not self.config["adaptive_delay"]:
            return self.current_delay

        base_delay = self.current_delay
        
        # Уменьшаем задержку при успешных обновлениях
        if self.success_streak >= 5:
            base_delay = max(MIN_DELAY, base_delay * 0.9)
        
        # Увеличиваем при наличии флудвейтов
        recent_floods = sum(1 for t in self.flood_history 
                          if (datetime.now() - t).total_seconds() < 3600)
        if recent_floods:
            base_delay = min(MAX_DELAY, base_delay * (1 + recent_floods * 0.2))
        
        # Добавляем случайность
        jitter = random.uniform(1 - JITTER, 1 + JITTER)
        return base_delay * jitter

    async def _main_loop(self) -> None:
        """Основной цикл работы модуля"""
        while self.running:
            try:
                if await self._update_photo():
                    delay = self._calculate_delay()
                    await asyncio.sleep(delay)
                else:
                    if self.error_count >= ERROR_THRESHOLD:
                        self.running = False
                        break
                    await asyncio.sleep(RETRY_DELAY)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                await asyncio.sleep(RETRY_DELAY)

    def _format_time(self, seconds: float) -> str:
        """Форматирование времени"""
        if seconds < 60:
            return f"{seconds:.0f}с"
        if seconds < 3600:
            return f"{seconds/60:.1f}м"
        return f"{seconds/3600:.1f}ч"

    def _get_stats(self) -> Dict[str, str]:
        """Получение статистики работы"""
        now = datetime.now()
        uptime = (now - self.start_time).total_seconds() if self.start_time else 0
        last_update = (now - self.last_update).total_seconds() if self.last_update else 0
        
        return {
            "status": "✅ Работает" if self.running else "🛑 Остановлен",
            "uptime": self._format_time(uptime),
            "count": str(self.update_count),
            "hourly": (self.update_count / (uptime / 3600)) if uptime > 0 else 0,
            "delay": self._format_time(self.current_delay),
            "last": self._format_time(last_update) if self.last_update else "никогда",
            "errors": str(self.error_count),
            "floods": str(self.flood_count)
        }

    @loader.command()
    async def pfp(self, message):
        """Запустить смену фото (ответьте на фото)"""
        if self.running:
            await utils.answer(message, self.strings["already_running"])
            return

        reply = await message.get_reply_message()
        target = reply if reply and reply.photo else message if message.photo else None

        if not target or not target.photo:
            await utils.answer(message, self.strings["no_photo"])
            return

        try:
            self._reset_state()
            self.running = True
            self.start_time = datetime.now()
            self.chat_id = message.chat_id
            self.message_id = target.id
            
            hourly_updates = 3600 / self.current_delay
            mode = "Безопасный" if self.config["safe_mode"] else "Стандартный"
            
            await utils.answer(
                message,
                self.strings["starting"].format(
                    delay=f"{self.current_delay/60:.1f}",
                    updates=f"{hourly_updates:.1f}",
                    mode=mode
                )
            )
            
            self.task = asyncio.create_task(self._main_loop())
            
        except Exception as e:
            self._reset_state()
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command()
    async def pfpstop(self, message):
        """Остановить смену фото"""
        if not self.running:
            await utils.answer(message, self.strings["not_running"])
            return

        try:
            self.running = False
            if self.task:
                self.task.cancel()
            
            uptime = self._format_time(
                (datetime.now() - self.start_time).total_seconds()
            ) if self.start_time else "0с"
            
            await utils.answer(
                message,
                self.strings["stopping"].format(
                    count=self.update_count,
                    time=uptime,
                    errors=self.error_count
                )
            )
            
            self._reset_state()
            
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command()
    async def pfpstats(self, message):
        """Показать статистику работы"""
        await utils.answer(
            message,
            self.strings["stats"].format(**self._get_stats())
        )
