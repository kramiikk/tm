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
    """Модуль для автоматического обновления фото профиля"""

    strings = {"name": "PfpRepeater"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "MIN_DELAY", 3600, "Минимальная задержка между обновлениями (в секундах)",
            "MAX_DELAY", 7200, "Максимальная задержка между обновлениями (в секундах)",
            "COOLDOWN_MULTIPLIER", 2.0, "Множитель задержки при получении ошибок"
        )
        self.running = False
        self.task = None
        self.message = None
        self.current_delay = None
        self.error_count = 0
        self.last_update = None
        self.chat_id = None
        self.message_id = None

    async def get_fresh_photo(self):
        """Получение актуального сообщения с фото"""
        try:
            fresh_message = await self.client.get_messages(self.chat_id, ids=self.message_id)
            if fresh_message and fresh_message.photo:
                self.message = fresh_message  # Обновляем self.message свежим сообщением
                return fresh_message.photo
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении свежего фото: {str(e)}")
            return None

    async def client_ready(self, client, db):
        """Инициализация при запуске"""
        self.client = client
        self.db = db
        
        was_running = self.db.get(self.strings["name"], "running", False)
        if was_running:
            self.message_id = self.db.get(self.strings["name"], "message_id")
            self.chat_id = self.db.get(self.strings["name"], "chat_id")
            if self.message_id and self.chat_id:
                try:
                    fresh_photo = await self.get_fresh_photo()  # Используем get_fresh_photo вместо get_messages
                    if fresh_photo:  # self.message уже обновлен в get_fresh_photo
                        self.running = True
                        self.task = asyncio.create_task(self.set_profile_photo())
                except Exception as e:
                    logger.error(f"Ошибка при восстановлении состояния: {str(e)}")

    async def set_profile_photo(self):
        """Основной цикл обновления фото с адаптивной задержкой"""
        self.current_delay = self.config["MIN_DELAY"]
        self.error_count = 0
        
        while self.running:
            try:
                if not self.message_id or not self.chat_id:
                    raise Exception("Данные сообщения не найдены")

                # Проверка времени с последнего обновления
                if self.last_update:
                    time_since_update = (datetime.now() - self.last_update).total_seconds()
                    if time_since_update < self.current_delay:
                        await asyncio.sleep(self.current_delay - time_since_update)

                # Получаем свежее фото перед каждым обновлением
                fresh_photo = await self.get_fresh_photo()
                if not fresh_photo:
                    raise Exception("Не удалось получить актуальное фото")

                try:
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
                    
                    # Успешное обновление - постепенно уменьшаем задержку
                    if self.error_count > 0:
                        self.error_count -= 1
                        self.current_delay = max(
                            self.config["MIN_DELAY"],
                            self.current_delay / 1.5
                        )
                    
                    # Добавляем случайность к задержке
                    random_delay = random.uniform(
                        self.current_delay,
                        self.current_delay * 1.5
                    )
                    await asyncio.sleep(random_delay)

                except errors.FloodWaitError as e:
                    self.error_count += 1
                    self.current_delay = min(
                        self.config["MAX_DELAY"],
                        self.current_delay * self.config["COOLDOWN_MULTIPLIER"]
                    )
                    
                    wait_time = max(e.seconds, self.current_delay)
                    await self.client.send_message(
                        self.chat_id,
                        f"⚠️ Обнаружено ограничение Telegram. Увеличиваем задержку до {wait_time//3600} часов."
                    )
                    await asyncio.sleep(wait_time)
                    continue
                    
            except errors.FloodWaitError as e:
                self.error_count += 1
                wait_time = max(e.seconds, self.current_delay * self.config["COOLDOWN_MULTIPLIER"])
                await asyncio.sleep(wait_time)
                continue
                
            except Exception as e:
                logger.error(f"Ошибка в модуле PfpRepeater: {str(e)}")
                self.error_count += 1
                
                if self.error_count >= 5:
                    self.running = False
                    self.db.set(self.strings["name"], "running", False)
                    await self.client.send_message(
                        self.chat_id,
                        "❌ Слишком много ошибок подряд. Модуль остановлен."
                    )
                    break
                    
                await asyncio.sleep(self.current_delay)

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
