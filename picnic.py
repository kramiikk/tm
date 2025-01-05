"""
════════════════════════1══════
    Profile Photo Repeater                       
    Developer: @xdesai                           
    Optimized: @kramiikk                         
════════════════════════2══════

Этот модуль позволяет автоматически обновлять фотографию профиля
с адаптивной задержкой для избежания ограничений Telegram.

📝 Команды:
    • .pfp - Запустить автообновление фото профиля
    • .pfpstop - Остановить автообновление

💡 Совет: Ответьте на фото командой .pfp или отправьте фото 
    с командой .pfp для установки его как фото профиля

⚠️ Отказ от ответственности:
    Разработчик не несет ответственности за любые проблемы,
    которые могут возникнуть с вашим аккаунтом.
"""

import asyncio
import logging
import random
from datetime import datetime
from telethon import functions, types, errors
from .. import loader

logger = logging.getLogger(__name__)

@loader.tds
class PfpRepeaterMod(loader.Module):
    """Модуль для автоматического обновления фото профиля с защитой от ограничений"""

    strings = {"name": "PfpRepeater"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "MIN_DELAY", 1800, "Минимальная задержка между обновлениями (в секундах)",
            "MAX_DELAY", 3600, "Максимальная задержка между обновлениями (в секундах)",
            "COOLDOWN_MULTIPLIER", 1.2, "Множитель задержки при получении ошибок",
            "INITIAL_DELAY", 2400, "Начальная задержка между обновлениями (в секундах)",
            "SAFE_MODE", True, "Использовать безопасный режим работы"
        )
        self.running = False
        self.task = None
        self.message = None
        self.current_delay = None
        self.error_count = 0
        self.last_update = None
        self.chat_id = None
        self.message_id = None
        self.success_streak = 0
        self.last_flood_wait = None
        self.flood_wait_history = []

    async def set_profile_photo(self):
        """Основной цикл обновления фото с защитой от флудвейта"""
        self.current_delay = self.config["INITIAL_DELAY"]
        self.error_count = 0
        self.success_streak = 0
        
        while self.running:
            try:
                if not self.message_id or not self.chat_id:
                    raise Exception("Данные сообщения не найдены")

                # Проверяем историю флудвейтов
                if self.flood_wait_history:
                    # Если были флудвейты в последние 24 часа, увеличиваем базовую задержку
                    recent_floods = [t for t in self.flood_wait_history 
                                   if (datetime.now() - t).total_seconds() < 86400]
                    if recent_floods:
                        safe_delay = self.current_delay * (1 + (len(recent_floods) * 0.1))
                        self.current_delay = min(self.config["MAX_DELAY"], safe_delay)

                # Проверяем время с последнего обновления
                if self.last_update:
                    time_since_update = (datetime.now() - self.last_update).total_seconds()
                    if time_since_update < self.current_delay:
                        await asyncio.sleep(self.current_delay - time_since_update)

                fresh_photo = await self.get_fresh_photo()
                if not fresh_photo:
                    raise Exception("Не удалось получить фото")

                # Если включен безопасный режим, добавляем дополнительную задержку
                if self.config["SAFE_MODE"]:
                    safe_sleep = random.uniform(81, 243)
                    await asyncio.sleep(safe_sleep)

                await self.client(
                    functions.photos.UpdateProfilePhotoRequest(
                        id=types.InputPhoto(
                            id=fresh_photo.id,
                            access_hash=fresh_photo.access_hash,
                            file_reference=fresh_photo.file_reference
                        )
                    )
                )
                
                self.last_update = datetime.now()
                self.success_streak += 1
                
                # Осторожное уменьшение задержки при успехе
                if self.success_streak >= 5 and not self.flood_wait_history:
                    self.current_delay = max(
                        self.config["MIN_DELAY"],
                        self.current_delay * 0.95  # Уменьшаем всего на 5%
                    )
                    self.error_count = max(0, self.error_count - 1)
                
                # Добавляем случайность к задержке
                jitter = random.uniform(0.9, 1.1)  # Уменьшенный разброс
                await asyncio.sleep(self.current_delay * jitter)

            except errors.FloodWaitError as e:
                self.error_count += 1
                self.success_streak = 0
                self.last_flood_wait = datetime.now()
                self.flood_wait_history.append(datetime.now())
                
                # Очищаем старые записи о флудвейтах
                self.flood_wait_history = [t for t in self.flood_wait_history 
                                         if (datetime.now() - t).total_seconds() < 86400]
                
                # Значительно увеличиваем задержку при флудвейте
                self.current_delay = min(
                    self.config["MAX_DELAY"],
                    max(
                        e.seconds * 1.5,  # Берем 150% от требуемого времени ожидания
                        self.current_delay * self.config["COOLDOWN_MULTIPLIER"]
                    )
                )
                
                await self.client.send_message(
                    self.chat_id,
                    f"⚠️ Получено ограничение от Telegram. Увеличиваем задержку до {self.current_delay//3600:.1f}ч."
                )
                
                # Ждем указанное время плюс небольшой запас
                wait_time = e.seconds + random.uniform(60, 300)
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"Ошибка в работе модуля: {str(e)}")
                self.error_count += 1
                self.success_streak = 0
                
                if self.error_count >= 5:
                    self.running = False
                    self.db.set(self.strings["name"], "running", False)
                    await self.client.send_message(
                        self.chat_id,
                        "❌ Модуль остановлен из-за множественных ошибок."
                    )
                    break
                
                await asyncio.sleep(self.current_delay)

    @loader.command()
    async def pfpstats(self, message):
        """Показать текущую статистику работы модуля"""
        if not self.running:
            await message.edit("⚠️ Модуль не запущен")
            return
            
        stats = (
            f"📊 Статистика PfpRepeater:\n"
            f"• Текущая задержка: {self.current_delay//60:.1f}мин\n"
            f"• Успешных обновлений подряд: {self.success_streak}\n"
            f"• Ошибок: {self.error_count}\n"
            f"• Флудвейтов за 24ч: {len(self.flood_wait_history)}\n"
            f"• Последнее обновление: {self.last_update.strftime('%H:%M:%S') if self.last_update else 'нет'}"
        )
        await message.edit(stats)

    @loader.command()
    async def pfp(self, message):
        """Запустить автообновление фото профиля. Отправьте команду с фото или ответом на фото."""
        if self.running:
            await message.edit("⚠️ Автообновление фото уже запущено.")
            return

        reply = await message.get_reply_message()
        target_message = reply if reply and reply.photo else message if message.photo else None

        if not target_message or not target_message.photo:
            await message.edit("❌ Пожалуйста, отправьте команду с фото или ответом на сообщение с фото.")
            return

        try:
            self.message = target_message
            self.chat_id = message.chat_id
            self.message_id = target_message.id
            self.running = True
            self.last_update = None
            self.error_count = 0

            self.db.set(self.strings["name"], "message_id", target_message.id)
            self.db.set(self.strings["name"], "chat_id", message.chat_id)
            self.db.set(self.strings["name"], "running", True)

            self.task = asyncio.create_task(self.set_profile_photo())
            
            await message.edit(
                f"✅ Запущено автообновление фото профиля с адаптивной задержкой от "
                f"{self.config['MIN_DELAY']//3600} до {self.config['MAX_DELAY']//3600} часов."
            )
        except Exception as e:
            await message.edit(f"❌ Ошибка при запуске: {str(e)}")
            self.running = False
            self.db.set(self.strings["name"], "running", False)

    @loader.command()
    async def pfpstop(self, message):
        """Остановить автообновление фото профиля"""
        if not self.running:
            await message.edit("⚠️ Автообновление фото не запущено.")
            return

        try:
            self.running = False
            if self.task and not self.task.done():
                self.task.cancel()
            self.db.set(self.strings["name"], "running", False)
            await message.edit("🛑 Автообновление фото остановлено.")
        except Exception as e:
            await message.edit(f"❌ Ошибка при остановке: {str(e)}")
