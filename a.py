import asyncio
import logging
import time

from hikkatl.errors import FloodWaitError
from hikkatl.tl.types import Message

from .. import loader, utils
from ..tl_cache import CustomTelegramClient

logger = logging.getLogger(__name__)


class AutoMod(loader.Module):
    """Автоматически отвечает на личные сообщения с изображением и текстом"""

    strings = {"name": "Auto"}

    def __init__(self):
        self.go = {
            "enabled": False,
            "message": "<i>Mon esprit s'absente un instant, mais mes mots vous reviendront bientôt.</i>",
            "photo_url": "https://wallpapercave.com/wp/wp5418096.jpg",
            "last": {},
        }
        self.lock = asyncio.Lock()

    async def client_ready(self, client: CustomTelegramClient, db):
        """Инициализация клиента и загрузка данных из БД"""
        self._client = client
        self.db = db

        for key in self.go:
            self.go[key] = self.db.get("Auto", key, self.go[key])

    async def watcher(self, message: Message):
        """Обработчик входящих сообщений"""
        if (
            not self.go["enabled"]
            or not message.is_private
            or message.out
            or message.chat_id == self.tg_id
            or getattr(await message.get_sender(), "bot", False)
        ):
            return
        async with self.lock:
            now = time.time()
            user = message.sender_id
            logger.info(f"{user}_msg_{message.text}")
            if user == 1271266957:
                return
            last_time = self.go["last"].get(str(user), 0)
            if now - last_time < 1800:
                return
            try:
                await self._send_safe_message(user)
                self.go["last"][str(user)] = now
                self.db.set("Auto", "last", self.go["last"])
            except Exception as e:
                logger.error(f"Ошибка отправки: {e}", exc_info=True)
            finally:
                self.go["last"] = {
                    k: v for k, v in self.go["last"].items() if now - v < 1800
                }

    async def _send_safe_message(self, user_id: int):
        """Безопасная отправка сообщения с обработкой ошибок"""
        try:
            await self._client.dispatcher.safe_api_call(
                self._client.send_file(
                    user_id,
                    self.go["photo_url"],
                    caption=self.go["message"],
                )
            )
        except FloodWaitError as e:
            logger.warning(f"FloodWait: {e.seconds} сек")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            raise

    @loader.command()
    async def a(self, message: Message):
        """Управление автоответчиком"""
        args = utils.get_args_raw(message)

        if not args:
            return await self._show_help(message)
        parts = args.split(maxsplit=2)
        command = parts[0].lower()

        handlers = {
            "tg": self._toggle,
            "tt": self._set_text,
            "pt": self._set_photo,
            "st": self._show_status,
        }

        if command not in handlers:
            return await utils.answer(message, "❌ Неизвестная команда")
        await handlers[command](message, parts[1:] if len(parts) > 1 else [])

    async def _toggle(self, message: Message, args: list):
        """Переключение состояния"""
        self.go["enabled"] = not self.go["enabled"]
        self.db.set("Auto", "enabled", self.go["enabled"])
        state = "🟢 Включен" if self.go["enabled"] else "🔴 Выключен"
        await utils.answer(message, f"{state}")

    async def _set_text(self, message: Message, args: list):
        """Установка текста"""
        if not args:
            return await utils.answer(message, "❌ Укажите текст")
        self.go["message"] = " ".join(args)
        self.db.set("Auto", "message", self.go["message"])
        await utils.answer(message, f"✅ Новый текст:\n{self.go['message']}")

    async def _set_photo(self, message: Message, args: list):
        """Установка фото"""
        if not args:
            return await utils.answer(message, "❌ Укажите URL изображения")
        self.go["photo_url"] = args[0]
        self.db.set("Auto", "photo_url", self.go["photo_url"])
        await utils.answer(message, f"✅ Новая ссылка на фото:\n{self.go['photo_url']}")

    async def _show_status(self, message: Message, args: list):
        """Показать статус"""
        status = "🟢 Активен" if self.go["enabled"] else "🔴 Выключен"
        text = (
            f"{status}\n⏱ Задержка: 30 мин\n"
            f"✉️ Текст: {self.go['message']}\n"
            f"🖼 Изображение: {self.go['photo_url']}"
        )
        await utils.answer(message, text)

    async def _show_help(self, message: Message):
        """Показать справку"""
        help_text = (
            "📚 Доступные команды:\n\n"
            ".a tg - Переключить статус\n"
            ".a tt текст - Изменить текст\n"
            ".a pt url - Изменить изображение\n"
            ".a st - Показать настройки"
        )
        await utils.answer(message, help_text)
