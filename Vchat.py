import logging
import os
from typing import Optional

import ffmpeg
from telethon import types
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest

from .. import loader, utils

@loader.tds
class VideoModModule(loader.Module):
    """Модуль для работы с видео в чате Hikka"""

    strings = {
        "name": "VideoMod",
        "converting": "<b>🔄 Конвертация видео...</b>",
        "video_playing": "<b>🎥 Воспроизведение видео...</b>",
        "joined_video_chat": "<b>✅ Подключено к видео чату</b>",
        "no_video_chat": "<b>❗ Видео чат не найден</b>",
        "no_media": "<b>❗ Медиафайл не найден</b>",
        "error": "<b>❌ Ошибка: {}</b>"
    }

    def __init__(self):
        self._client = None

    async def client_ready(self, client, db):
        """Инициализация клиента"""
        self._client = client

    async def _get_video_chat(self, chat_id):
        """Получение информации о видео чате"""
        try:
            # Для супергрупп и каналов
            if str(chat_id).startswith('-100'):
                full_chat = await self._client(GetFullChannelRequest(
                    channel=await self._client.get_input_entity(chat_id)
                ))
            # Для обычных групп
            else:
                full_chat = await self._client(GetFullChatRequest(
                    chat_id=chat_id
                ))
            
            # Проверяем наличие активных видео чатов
            if hasattr(full_chat, 'full_chat') and full_chat.full_chat.call:
                return full_chat.full_chat.call
            
            return None
        
        except Exception as e:
            logging.error(f"Ошибка получения видео чата: {e}")
            return None

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

    async def _convert_video(self, video_file: str) -> Optional[str]:
        """Конвертация видео в совместимый формат"""
        try:
            input_file = f"media_video_{os.getpid()}.raw"
            
            # Конвертация с обработкой ошибок
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
            
            return input_file
        
        except Exception as conv_error:
            logging.error(f"Ошибка конвертации видео: {conv_error}")
            return None

    @loader.command()
    async def vjoincmd(self, message: types.Message):
        """Присоединение к видео чату"""
        try:
            chat_id = message.chat_id
            
            # Получаем информацию о видео чате
            video_chat = await self._get_video_chat(chat_id)
            
            if not video_chat:
                await utils.answer(message, self.strings["no_video_chat"])
                return

            # Попытка присоединения к видео чату
            await self._client.send_message(chat_id, '📞 Присоединяюсь к видео чату')
            
            await utils.answer(message, self.strings["joined_video_chat"])
        
        except Exception as e:
            logging.error(f"Ошибка подключения к видео чату: {e}")
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command()
    async def vplaycmd(self, message: types.Message):
        """Воспроизведение видео в чате"""
        try:
            # Проверка наличия видео чата
            chat_id = message.chat_id
            video_chat = await self._get_video_chat(chat_id)
            
            if not video_chat:
                await utils.answer(message, self.strings["no_video_chat"])
                return

            # Загрузка видео
            await utils.answer(message, self.strings["converting"])
            video_file = await self._download_video(message)
            
            if not video_file:
                return

            # Конвертация видео
            converted_file = await self._convert_video(video_file)
            
            if not converted_file:
                await utils.answer(message, self.strings["error"].format("Не удалось конвертировать видео"))
                return

            # Отправка видео в чат
            await self._client.send_file(
                chat_id, 
                converted_file, 
                caption='🎥 Воспроизведение видео'
            )
            
            # Очистка временных файлов
            try:
                if video_file and os.path.exists(video_file):
                    os.remove(video_file)
                if converted_file and os.path.exists(converted_file):
                    os.remove(converted_file)
            except Exception as cleanup_e:
                logging.error(f"Ошибка очистки: {cleanup_e}")

            await utils.answer(message, self.strings["video_playing"])
        
        except Exception as e:
            logging.error(f"Ошибка воспроизведения видео: {e}")
            await utils.answer(message, self.strings["error"].format(str(e)))
