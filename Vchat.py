import logging
import os
from typing import Dict, Any

import ffmpeg
import pytgcalls
from ShazamAPI import Shazam
from youtube_dl import YoutubeDL
from pytgcalls import GroupCallFactory
from telethon import types

from .. import loader, utils

@loader.tds
class VoiceModModule(loader.Module):
    """Module for working with voice and video chat in Hikka"""

    strings = {
        "name": "VoiceMod",
        "downloading": "<b>📥 Загрузка...</b>",
        "converting": "<b>🔄 Конвертация...</b>",
        "playing": "<b>🎵 Воспроизведение аудио...</b>",
        "video_playing": "<b>🎥 Воспроизведение видео...</b>",
        "joined": "<b>✅ Подключен к голосовому чату</b>",
        "left": "<b>❌ Покинул голосовой чат</b>",
        "no_media": "<b>❗ Медиа не найдено</b>",
        "error": "<b>❌ Ошибка: {}</b>"
    }

    def __init__(self):
        self.group_calls: Dict[str, Any] = {}

    async def client_ready(self, client, db):
        """Initialize client when module is ready"""
        self.client = client
        self.db = db

    def _get_group_call(self, chat_id: int) -> Any:
        """Get or create group call for a chat"""
        chat_str = str(chat_id)
        if chat_str not in self.group_calls:
            self.group_calls[chat_str] = GroupCallFactory(
                self.client, 
                pytgcalls.GroupCallFactory.MTPROTO_CLIENT_TYPE.TELETHON
            ).get_file_group_call()
        return self.group_calls[chat_str]

    async def _download_media(self, message: types.Message):
        """Download media from message or link"""
        # Попытка скачать медиа из реплая
        reply = await message.get_reply_message()
        if reply:
            if reply.video:
                return await reply.download_media(), True
            elif reply.audio:
                return await reply.download_media(), False

        # Попытка скачать по ссылке
        args = utils.get_args_raw(message)
        if args:
            try:
                ytdl_opts = {
                    "format": "bestvideo+bestaudio/best",
                    "outtmpl": "%(title)s.%(ext)s",
                    "nooverwrites": True,
                    "no_warnings": True,
                    "quiet": True,
                }
                
                with YoutubeDL(ytdl_opts) as ydl:
                    info = ydl.extract_info(args, download=True)
                    filename = ydl.prepare_filename(info)
                    
                    # Определяем, является ли медиа видео
                    is_video = 'vcodec' in info and info['vcodec'] != 'none'
                    
                    return filename, is_video
            except Exception as e:
                await utils.answer(message, self.strings["error"].format(str(e)))
                return None, None

        return None, None

    @loader.command(ru_doc="Воспроизвести аудио/видео в голосовом чате")
    async def vplaycmd(self, message: types.Message):
        """Play audio/video in voice chat"""
        # Скачиваем медиа
        media, is_video = await self._download_media(message)
        if not media:
            return await utils.answer(message, self.strings["no_media"])
        
        try:
            # Подготавливаем сообщение о конвертации
            await utils.answer(message, self.strings["converting"])
            
            # Путь для конвертированного файла
            input_file = f"media_{'video' if is_video else 'audio'}_{os.getpid()}.raw"
            
            # Конвертируем медиа
            conversion_cmd = (
                ffmpeg.input(media)
                .output(
                    input_file, 
                    format='rawvideo' if is_video else 's16le', 
                    vcodec='rawvideo' if is_video else 'pcm_s16le', 
                    pix_fmt='yuv420p' if is_video else None,
                    acodec='pcm_s16le', 
                    ac=2, 
                    ar='48k'
                )
                .overwrite_output()
            )
            conversion_cmd.run()
            
            # Определяем чат
            chat_id = message.chat_id
            
            # Получаем group call
            group_call = self._get_group_call(chat_id)
            
            # Начинаем звонок и воспроизведение
            await group_call.start(chat_id)
            group_call.input_filename = input_file
            
            # Отправляем сообщение об успешном воспроизведении
            await utils.answer(
                message, 
                self.strings["video_playing" if is_video else "playing"]
            )
        
        except Exception as e:
            logging.error(f"Playback error: {e}")
            await utils.answer(message, self.strings["error"].format(str(e)))
        finally:
            # Очищаем временные файлы
            try:
                if os.path.exists(media):
                    os.remove(media)
                if os.path.exists(input_file):
                    os.remove(input_file)
            except Exception as cleanup_e:
                logging.error(f"Cleanup error: {cleanup_e}")

    @loader.command(ru_doc="Подключиться к голосовому чату")
    async def vjoincmd(self, message: types.Message):
        """Join voice chat"""
        try:
            chat_id = message.chat_id
            group_call = self._get_group_call(chat_id)
            await group_call.start(chat_id)
            await utils.answer(message, self.strings["joined"])
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command(ru_doc="Покинуть голосовой чат")
    async def vleavecmd(self, message: types.Message):
        """Leave voice chat"""
        try:
            chat_id = message.chat_id
            chat_str = str(chat_id)
            
            if chat_str in self.group_calls:
                await self.group_calls[chat_str].stop()
                del self.group_calls[chat_str]
            
            await utils.answer(message, self.strings["left"])
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))
