"""
════════════════════════1══════
    Profile Photo Repeater                       
    Developer: @xdesai                           
    Optimized: @kramiikk                         
════════════════════════2══════

Этот модуль позволяет автоматически обновлять фотографию профиля
каждые 15 минут.

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
from telethon import functions
from .. import loader

logger = logging.getLogger(__name__)

@loader.tds
class PfpRepeaterMod(loader.Module):
    """Модуль для автоматического обновления фото профиля"""

    strings = {"name": "PfpRepeater"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "DELAY", 900, "Задержка между обновлениями фото (в секундах)"
        )
        self.running = False
        self.task = None
        self.message = None
        self.photo = None

    async def client_ready(self, client, db):
        """Инициализация при запуске"""
        self.client = client
        self.db = db
        
        was_running = self.db.get(self.strings["name"], "running", False)
        if was_running:
            message_id = self.db.get(self.strings["name"], "message_id")
            chat_id = self.db.get(self.strings["name"], "chat_id")
            if message_id and chat_id:
                try:
                    self.message = await self.client.get_messages(chat_id, ids=message_id)
                    if self.message and self.message.photo:
                        self.photo = self.message.photo
                        self.running = True
                        self.task = asyncio.create_task(self.set_profile_photo())
                except Exception as e:
                    logger.error(f"Ошибка при восстановлении состояния: {str(e)}")

    async def set_profile_photo(self):
        """Основной цикл обновления фото"""
        while self.running:
            try:
                if not self.message or not self.photo:
                    raise Exception("Фото не найдено")

                photo_bytes = await self.client.download_media(self.photo, bytes)
                
                await self.client(
                    functions.photos.UploadProfilePhotoRequest(
                        file=await self.client.upload_file(photo_bytes)
                    )
                )
                
                await asyncio.sleep(self.config["DELAY"])
                
            except Exception as e:
                self.running = False
                self.db.set(self.strings["name"], "running", False)
                await self.client.send_message(
                    self.db.get(self.strings["name"], "chat_id"),
                    f"❌ Ошибка при обновлении фото: {str(e)}. Остановка модуля."
                )
                break

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
            self.photo = target_message.photo
            self.running = True

            self.db.set(self.strings["name"], "message_id", target_message.id)
            self.db.set(self.strings["name"], "chat_id", message.chat_id)
            self.db.set(self.strings["name"], "running", True)

            self.task = asyncio.create_task(self.set_profile_photo())
            
            await message.edit(
                f"✅ Запущено автообновление фото профиля каждые {self.config['DELAY']} секунд."
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
            if self.task:
                self.task.cancel()
            self.db.set(self.strings["name"], "running", False)
            await message.edit("🛑 Автообновление фото остановлено.")
        except Exception as e:
            await message.edit(f"❌ Ошибка при остановке: {str(e)}")
