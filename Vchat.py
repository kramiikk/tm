import logging
import os
from typing import Dict, Any, Optional

import ffmpeg
import pytgcalls
from pytgcalls import GroupCallFactory
from telethon import types

from .. import loader, utils

@loader.tds
class VideoModModule(loader.Module):
    """Модуль для работы с видео в чате"""

    strings = {
        "name": "VideoMod",
        "converting": "<b>🔄 Конвертация видео...</b>",
        "video_playing": "<b>🎥 Воспроизведение видео...</b>",
        "joined": "<b>✅ Подключено к видео чату</b>",
        "no_media": "<b>❗ Медиафайл не найден</b>",
        "error": "<b>❌ Ошибка: {}</b>"
    }

    def __init__(self):
        self._group_calls: Dict[str, Any] = {}
        self._client = None
        self._db = None

    async def client_ready(self, client, db):
        """Инициализация клиента при готовности модуля"""
        self._client = client
        self._db = db

    def _get_group_call(self, chat_id: int) -> Any:
        """Получение или создание группового звонка"""
        chat_str = str(chat_id)
        if chat_str not in self._group_calls:
            self._group_calls[chat_str] = GroupCallFactory(
                self._client, 
                pytgcalls.GroupCallFactory.MTPROTO_CLIENT_TYPE.TELETHON
            ).get_file_group_call()
        return self._group_calls[chat_str]

    async def _download_video(self, message: types.Message) -> Optional[str]:
        """Загрузка видео из сообщения"""
        try:
            # Проверяем ответное сообщение на наличие видео
            reply = await message.get_reply_message()
            if not reply or not reply.file or not reply.file.mime_type.startswith('video/'):
                await utils.answer(message, self.strings["no_media"])
                return None

            # Загружаем видео
            video_file = await reply.download_media()
            return video_file
        
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))
            return None

    @loader.command()
    async def vplaycmd(self, message: types.Message):
        """Воспроизведение видео в видео чате"""
        # Загрузка видео
        video_file = await self._download_video(message)
        if not video_file:
            return

        input_file = None
        try:
            # Подготовка к конвертации
            await utils.answer(message, self.strings["converting"])
            
            # Путь для конвертированного файла
            input_file = f"media_video_{os.getpid()}.raw"
            
            # Конвертация видео
            conversion_cmd = (
                ffmpeg.input(video_file)
                .output(
                    input_file, 
                    format='rawvideo', 
                    vcodec='rawvideo', 
                    pix_fmt='yuv420p',
                    acodec='pcm_s16le', 
                    ac=2, 
                    ar='48k'
                )
                .overwrite_output()
            )
            conversion_cmd.run()
            
            # Получение группового звонка
            chat_id = message.chat_id
            group_call = self._get_group_call(chat_id)
            
            # Начало звонка и воспроизведение видео
            await group_call.start(chat_id)
            group_call.input_filename = input_file
            
            # Сообщение об успешном воспроизведении
            await utils.answer(message, self.strings["video_playing"])
        
        except Exception as e:
            logging.error(f"Ошибка воспроизведения видео: {e}")
            await utils.answer(message, self.strings["error"].format(str(e)))
        finally:
            # Очистка временных файлов
            try:
                if video_file and os.path.exists(video_file):
                    os.remove(video_file)
                if input_file and os.path.exists(input_file):
                    os.remove(input_file)
            except Exception as cleanup_e:
                logging.error(f"Ошибка очистки: {cleanup_e}")

    @loader.command()
    async def vjoincmd(self, message: types.Message):
        """Присоединение к видео чату"""
        try:
            chat_id = message.chat_id
            group_call = self._get_group_call(chat_id)
            await group_call.start(chat_id)
            await utils.answer(message, self.strings["joined"])
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))
