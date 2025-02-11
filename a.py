import asyncio
import logging
import time

from hikkatl.errors import FloodWaitError
from hikkatl.tl.types import Message

from .. import loader, utils
from ..tl_cache import CustomTelegramClient

logger = logging.getLogger(__name__)

class AutoResponderMod(loader.Module):
    """Автоматически отвечает на личные сообщения"""

    strings = {"name": "AutoResponder"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "enabled",
                False,
                "Активация автоответчика",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "message",
                "Я временно недоступен. Оставьте сообщение, и я отвечу позже.",
                "Текст автоматического ответа",
                validator=loader.validators.String(),
            ),
        )
        self.last_responses = {}

    async def client_ready(self, client: CustomTelegramClient, db):
        self._client = client

    async def watcher(self, message: Message):
        if not self.config["enabled"]:
            return
        if not message.is_private or message.out:
            return
        user = message.sender_id
        if user == self._client.tg_id:
            return
        now = time.time()
        last_time = self.last_responses.get(user, 0)

        if now - last_time < 1800:
            return
        try:
            await self._send_safe_message(user)
            self.last_responses[user] = now
        except Exception as e:
            logger.error(f"Ошибка: {e}", exc_info=True)

    async def _send_safe_message(self, user_id: int):
        try:
            await self._client.send_message(user_id, self.config["message"])
        except FloodWaitError as e:
            logger.warning(f"Обнаружен FloodWait: {e.seconds} сек")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            raise

    @loader.command()
    async def aa(self, message: Message):
        """Переключить автоответчик"""
        self.config["enabled"] = not self.config["enabled"]
        state = "🟢 Включен" if self.config["enabled"] else "🔴 Выключен"
        await utils.answer(message, f"{state}")

    @loader.command()
    async def at(self, message: Message):
        """Установить текст ответа"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "❌ Укажите текст")
            return
        self.config["message"] = args
        await utils.answer(message, f"✅ Новый текст:\n{args}")

    @loader.command()
    async def a(self, message: Message):
        """Показать текущие настройки"""
        status = "🟢 Активен" if self.config["enabled"] else "🔴 Выключен"
        text = f"{status}\n⏱ Задержка: 30 мин\n✉️ Текст ответа:\n{self.config['message']}"
        await utils.answer(message, text)
