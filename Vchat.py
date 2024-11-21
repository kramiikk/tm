import logging
import os
from typing import Optional, Union

from telethon import types, functions, errors
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.functions.phone import (
    GetGroupCallRequest,
    JoinGroupCallPresentationRequest,
    CreateGroupCallRequest,
    LeaveGroupCallRequest
)
from telethon.tl.types import (
    InputGroupCall,
    DocumentAttributeVideo,
    Chat,
    Channel,
    Message
)
import ffmpeg

from .. import loader, utils

@loader.tds
class GroupVideoModule(loader.Module):
    """Модуль для работы с видеочатом группы"""
    
    strings = {
        "name": "GroupVideo",
        "starting": "<b>🎥 Запуск трансляции в видеочате...</b>",
        "joining": "<b>📺 Подключение к видеочату группы...</b>",
        "joined": "<b>✅ Успешно подключен к видеочату группы</b>",
        "error": "<b>❌ Ошибка: {}</b>",
        "no_reply_video": "<b>❌ Ответьте на сообщение с видео</b>",
        "leave_success": "<b>✅ Успешно покинул видеочат</b>",
        "not_group": "<b>❌ Эта команда работает только в группах</b>",
        "downloading": "<b>⏳ Загрузка видео...</b>",
        "converting": "<b>🔄 Конвертация видео...</b>",
        "playing": "<b>▶️ Воспроизведение видео в видеочате...</b>",
        "invalid_file": "<b>❌ Файл не является видео</b>",
        "download_error": "<b>❌ Ошибка при загрузке видео: {}</b>",
        "convert_error": "<b>❌ Ошибка при конвертации видео: {}</b>",
        "creating_chat": "<b>🎥 Создание видеочата...</b>",
        "already_in_call": "<b>⚠️ Уже подключен к видеочату</b>"
    }

    async def _get_group_call(self, chat: Union[Chat, Channel], create: bool = False) -> Optional[types.phone.GroupCall]:
        """Получение информации о текущем видеочате группы"""
        try:
            if isinstance(chat, Channel):
                full = await self._client(GetFullChannelRequest(channel=chat))
                if full.full_chat.call is not None:
                    return await self._client(GetGroupCallRequest(call=full.full_chat.call))
            elif isinstance(chat, Chat):
                full = await self._client(GetFullChatRequest(chat_id=chat.id))
                if full.full_chat.call is not None:
                    return await self._client(GetGroupCallRequest(call=full.full_chat.call))
                    
            if create:
                return await self._create_group_call(chat)
                
        except Exception as e:
            logging.error(f"Ошибка получения информации о видеочате: {e}")
        return None

    async def _create_group_call(self, chat: Union[Chat, Channel]) -> Optional[types.phone.GroupCall]:
        """Создание нового видеочата"""
        try:
            await self._client.send_message(chat, self.strings["creating_chat"])
            call = await self._client(CreateGroupCallRequest(
                peer=chat,
                title="Видеочат",
                random_id=self._client.random_id()
            ))
            return await self._client(GetGroupCallRequest(call=call.updates[0].call))
        except Exception as e:
            logging.error(f"Ошибка создания видеочата: {e}")
            return None

    async def _download_video(self, message: Message) -> Optional[str]:
        """Загрузка видео из сообщения"""
        reply = await message.get_reply_message()
        if not reply or not reply.media:
            return None
            
        try:
            if not hasattr(reply.media, 'document') or not any(
                isinstance(attr, DocumentAttributeVideo)
                for attr in reply.media.document.attributes
            ):
                return None
                
            video_path = await reply.download_media()
            return video_path
            
        except Exception as e:
            logging.error(f"Ошибка загрузки видео: {e}")
            await self._client.send_message(message.chat, self.strings["download_error"].format(str(e)))
            return None

    async def _convert_video(self, input_path: str) -> Optional[str]:
        """Конвертация видео в формат, подходящий для видеочата"""
        output_path = None
        try:
            output_path = input_path + "_converted.mp4"
            
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(stream, output_path,
                                 vcodec='h264',
                                 acodec='aac',
                                 video_bitrate='1M',
                                 audio_bitrate='128k',
                                 f='mp4')
            
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            
            return output_path
            
        except Exception as e:
            logging.error(f"Ошибка конвертации видео: {e}")
            if output_path and os.path.exists(output_path):
                os.remove(output_path)
            return None
        finally:
            if input_path and os.path.exists(input_path):
                os.remove(input_path)

    @loader.command
    async def vjoincmd(self, message: Message):
        """Присоединиться к видеочату группы"""
        chat = message.chat
        
        if not isinstance(chat, (Chat, Channel)):
            await self._client.send_message(message.chat, self.strings["not_group"])
            return
            
        try:
            await self._client.send_message(message.chat, self.strings["joining"])
            
            call = await self._get_group_call(chat, create=True)
            if not call:
                await self._client.send_message(message.chat, self.strings["error"].format("Не удалось получить информацию о видеочате"))
                return

            try:
                await self._client(JoinGroupCallPresentationRequest(
                    call=InputGroupCall(
                        id=call.call.id,
                        access_hash=call.call.access_hash
                    ),
                    params={
                        "muted": True,
                        "video_stopped": True,
                        "screen_sharing": False,
                        "raise_hand": False
                    }
                ))
                
                await self._client.send_message(message.chat, self.strings["joined"])
                
            except errors.ChatAdminRequiredError:
                await self._client.send_message(message.chat, self.strings["error"].format("Требуются права администратора"))
            except errors.GroupCallJoinMissingError:
                await self._client.send_message(message.chat, self.strings["error"].format("Не удалось присоединиться к видеочату"))
            
        except Exception as e:
            await self._client.send_message(message.chat, self.strings["error"].format(str(e)))

    @loader.command
    async def vplaycmd(self, message: Message):
        """Воспроизвести видео в видеочате (ответьте на сообщение с видео)"""
        chat = message.chat
        
        if not isinstance(chat, (Chat, Channel)):
            await self._client.send_message(message.chat, self.strings["not_group"])
            return
            
        if not await message.get_reply_message():
            await self._client.send_message(message.chat, self.strings["no_reply_video"])
            return
            
        try:
            call = await self._get_group_call(chat, create=True)
            if not call:
                await self._client.send_message(message.chat, self.strings["error"].format("Не удалось получить информацию о видеочате"))
                return
                
            try:
                await self.vjoincmd(message)
            except Exception as e:
                logging.warning(f"Ошибка при присоединении к видеочату: {e}")
                
            video_path = await self._download_video(message)
            if not video_path:
                await self._client.send_message(message.chat, self.strings["invalid_file"])
                return
                
            await self._client.send_message(message.chat, self.strings["converting"])
            
            converted_path = await self._convert_video(video_path)
            if not converted_path:
                await self._client.send_message(message.chat, self.strings["convert_error"].format("Ошибка конвертации"))
                return
                
            try:
                await self._client.send_file(
                    chat.id,
                    converted_path,
                    caption=self.strings["playing"],
                    reply_to=message.reply_to_msg_id,
                    video_note=True
                )
            finally:
                if os.path.exists(converted_path):
                    os.remove(converted_path)
                
        except Exception as e:
            await self._client.send_message(message.chat, self.strings["error"].format(str(e)))

    @loader.command
    async def vleavecmd(self, message: Message):
        """Покинуть видеочат группы"""
        chat = message.chat
        
        if not isinstance(chat, (Chat, Channel)):
            await self._client.send_message(message.chat, self.strings["not_group"])
            return
            
        try:
            call = await self._get_group_call(chat)
            if not call:
                await self._client.send_message(message.chat, self.strings["error"].format("Нет активного видеочата"))
                return
            
            try:
                await self._client(LeaveGroupCallRequest(
                    call=InputGroupCall(
                        id=call.call.id,
                        access_hash=call.call.access_hash
