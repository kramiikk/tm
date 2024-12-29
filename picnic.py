"""
╔════════════════════════════════════════════════════════════════╗
║                    Profile Photo Repeater                      ║
║                    Developer: @xdesai                          ║
║                    Optimized: @kramiikk                        ║
╚════════════════════════════════════════════════════════════════╝

Этот модуль позволяет автоматически обновлять фотографию профиля
каждые 15 минут.

📝 Команды:
    • .pfp <путь> - Запустить автообновление фото профиля
    • .pfpstop - Остановить автообновление

💡 Совет: Вы также можете ответить на фото командой .pfp, 
    чтобы установить его как фото профиля

⚠️ Отказ от ответственности:
    Разработчик не несет ответственности за любые проблемы,
    которые могут возникнуть с вашим аккаунтом.
"""

import asyncio
from telethon import functions
from .. import loader

@loader.tds
class PfpRepeaterMod(loader.Module):
    """Profile Photo Repeater Module"""
    strings = {"name": "PfpRepeater"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "DELAY",
            900,
            validator=loader.validators.Integer(),
        )
        self.running = False
        self.task = None

    async def client_ready(self, client, db):
        self.client = client

    async def set_profile_photo(self, photo_path):
        while self.running:
            file = await self.client.upload_file(photo_path)
            await self.client(functions.photos.UploadProfilePhotoRequest(file=file))
            await asyncio.sleep(self.config["DELAY"])

    async def _get_photo_path(self, message):
        reply = await message.get_reply_message()
        if reply and reply.photo:
            return await message.client.download_media(reply.photo)
        elif message.media and message.photo:
            return await message.client.download_media(message)
        return None

    @loader.command()
    async def pfp(self, message):
        """Start repeating profile photo every 15 minutes"""
        photo_path = await self._get_photo_path(message)
        if not photo_path:
            await message.edit("Please provide the photo or reply to a photo.")
            return

        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self.set_profile_photo(photo_path))
            await message.edit(f"Started repeating profile photo every {self.config['DELAY']} seconds.")
        else:
            await message.edit("Profile photo repeater is already running.")

    @loader.command()
    async def pfpstop(self, message):
        """Stop repeating profile photo"""
        if self.running:
            self.running = False
            if self.task:
                self.task.cancel()
            await message.edit("Stopped repeating profile photo.")
        else:
            await message.edit("Profile photo repeater is not running.")
