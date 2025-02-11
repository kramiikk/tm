import asyncio
import logging
import time

from hikkatl.errors import FloodWaitError
from hikkatl.tl.types import Message

from .. import loader, utils, dispatcher
from ..tl_cache import CustomTelegramClient

logger = logging.getLogger(__name__)


class AutoMod(loader.Module):
    """Автоматически отвечает на личные сообщения"""

    strings = {"name": "Auto"}

    def __init__(self):
        self.go = False
        self.msg = "Я временно недоступен, обязательно отвечу."
        self.lock = asyncio.Lock()
        self.last = {}

    async def client_ready(self, client: CustomTelegramClient, db):
        """Инициализация клиента и загрузка данных из БД"""
        self._client = client
        self.db = db

        self.last = await self.db.get(self.strings["name"], "last", {})

        saved_enabled = await self.db.get(self.strings["name"], "enabled", None)
        if saved_enabled is not None:
            self.go = saved_enabled
        saved_message = await self.db.get(self.strings["name"], "message", None)
        if saved_message is not None:
            self.msg = saved_message

    async def watcher(self, message: Message):
        """Обработчик входящих сообщений"""
        if (
            not self.go
            or not message.is_private
            or message.out
            or not message.sender
            or message.sender.bot
        ):
            return
        user = message.sender_id
        if user == self.tg_id:
            return
        now = time.time()
        async with self.lock:
            last_time = self.last.get(str(user), 0)

            if now - last_time < 1800:
                return
            await self.db.set(
                self.strings["name"],
                f"msg_{int(time.time())}_{user}",
                {"user_id": user, "text": message.text, "time": time.time()},
            )

            try:
                await self._send_safe_message(user)
                self.last[str(user)] = now

                await self.db.set(self.strings["name"], "last", self.last)
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения: {e}", exc_info=True)
            finally:
                self.last = {k: v for k, v in self.last.items() if now - v < 1800}

    async def _send_safe_message(self, user_id: int):
        """Безопасная отправка сообщения с обработкой ошибок"""
        try:
            await dispatcher.safe_api_call(self._client.send_message(user_id, self.msg))
        except FloodWaitError as e:
            logger.warning(f"Обнаружен FloodWait: {e.seconds} сек")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            raise

    @loader.command
    async def aa(self, message: Message):
        """Переключить автоответчик"""
        self.go = not self.go

        await self.db.set(self.strings["name"], "enabled", self.go)

        state = "🟢 Включен" if self.go else "🔴 Выключен"
        await utils.answer(message, f"{state}")

    @loader.command
    async def at(self, message: Message):
        """Установить текст ответа"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "❌ Укажите текст")
            return
        self.msg = args

        await self.db.set(self.strings["name"], "message", args)

        await utils.answer(message, f"✅ Новый текст:\n{args}")

    @loader.command
    async def a(self, message: Message):
        """Показать текущие настройки"""
        status = "🟢 Активен" if self.go else "🔴 Выключен"
        text = f"{status}\n⏱ Задержка: 30 мин\n✉️ Текст ответа:\n{self.msg}"
        await utils.answer(message, text)
