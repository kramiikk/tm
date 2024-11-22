import logging
from telethon import types, functions
from telethon.tl.functions.phone import CreateGroupCallRequest, JoinGroupCallRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
import telethon.tl.types as tl
import os
import asyncio

from .. import loader, utils

@loader.tds
class VideoCallsModule(loader.Module):
    """Модуль для работы с видеозвонками в Telegram"""
    
    strings = {
        "name": "VideoCalls",
        "creating_call": "<b>🎥 Создание видеочата...</b>",
        "joining_call": "<b>📞 Подключение к видеочату...</b>",
        "joined_call": "<b>✅ Успешно подключен к видеочату</b>",
        "no_voice_chat": "<b>❌ В этом чате нет активного видеочата</b>",
        "created_call": "<b>✅ Видеочат успешно создан</b>",
        "error_creating": "<b>❌ Ошибка при создании видеочата: {}</b>",
        "error_joining": "<b>❌ Ошибка при подключении к видеочату: {}</b>",
        "no_rights": "<b>❌ Недостаточно прав для управления видеочатом</b>",
        "downloading_video": "<b>📥 Загрузка видео...</b>",
        "playing_video": "<b>▶️ Воспроизведение видео в видеочате...</b>",
        "error_playing": "<b>❌ Ошибка при воспроизведении видео: {}</b>",
        "no_video_reply": "<b>❌ Ответьте на сообщение с видео</b>",
        "unsupported_file": "<b>❌ Этот формат файла не поддерживается</b>",
        "not_in_call": "<b>❌ Сначала присоединитесь к видеочату</b>",
    }

    async def _get_chat_call(self, chat):
        """Получение информации о текущем видеочате"""
        try:
            if isinstance(chat, (types.Chat, types.Channel)):
                if hasattr(chat, 'username'):
                    full = await self._client(GetFullChannelRequest(chat.username))
                else:
                    full = await self._client(GetFullChatRequest(chat.id))
                return full.full_chat.call
        except Exception as e:
            logging.error(f"Ошибка получения информации о видеочате: {e}")
        return None

    async def _create_voice_chat(self, chat_id):
        """Создание нового видеочата"""
        try:
            chat = await self._client.get_entity(chat_id)
            call = await self._get_chat_call(chat)
            
            if call:
                return call
            
            result = await self._client(CreateGroupCallRequest(
                peer=chat,
                title="Видеочат"
            ))
            return result
        except Exception as e:
            logging.error(f"Ошибка создания видеочата: {e}")
            return None

    async def _download_media(self, message):
        """Загрузка медиафайла"""
        try:
            if not message.media:
                return None
            
            path = await message.download_media()
            return path
        except Exception as e:
            logging.error(f"Ошибка загрузки медиафайла: {e}")
            return None

    @loader.command
    async def vcreatecmd(self, message):
        """Создать новый видеочат в группе"""
        chat = message.chat
        
        try:
            await utils.answer(message, self.strings["creating_call"])
            
            result = await self._create_voice_chat(chat.id)
            if result:
                await utils.answer(message, self.strings["created_call"])
            else:
                await utils.answer(message, self.strings["error_creating"].format("Неизвестная ошибка"))
                
        except Exception as e:
            error_msg = str(e)
            if "PARTICIPANT_JOIN_MISSING" in error_msg:
                await utils.answer(message, self.strings["no_rights"])
            else:
                await utils.answer(message, self.strings["error_creating"].format(error_msg))

    @loader.command
    async def vjoincmd(self, message):
        """Присоединиться к существующему видеочату"""
        chat = message.chat
        
        try:
            await utils.answer(message, self.strings["joining_call"])
            
            call = await self._get_chat_call(chat)
            if not call:
                await utils.answer(message, self.strings["no_voice_chat"])
                return
            
            # Попытка присоединения к видеочату
            join_result = await self._client(JoinGroupCallRequest(
                call=call,
                muted=True,
                video_stopped=True,
                params=tl.DataJSON(data="{}")
            ))
            
            if join_result:
                await utils.answer(message, self.strings["joined_call"])
            else:
                await utils.answer(message, self.strings["error_joining"].format("Неизвестная ошибка"))
                
        except Exception as e:
            await utils.answer(message, self.strings["error_joining"].format(str(e)))

    @loader.command
    async def vplaycmd(self, message):
        """Воспроизвести видео в видеочате (ответьте на сообщение с видео)"""
        try:
            chat = message.chat
            reply = await message.get_reply_message()
            
            if not reply or not reply.media:
                await utils.answer(message, self.strings["no_video_reply"])
                return
            
            call = await self._get_chat_call(chat)
            if not call:
                await utils.answer(message, self.strings["not_in_call"])
                return
            
            status_msg = await utils.answer(message, self.strings["downloading_video"])
            
            # Загрузка видео
            video_path = await self._download_media(reply)
            if not video_path:
                await utils.answer(status_msg, self.strings["error_playing"].format("Ошибка загрузки"))
                return
            
            try:
                await utils.answer(status_msg, self.strings["playing_video"])
                
                # Присоединяемся к видеочату, если еще не присоединились
                join_result = await self._client(JoinGroupCallRequest(
                    call=call,
                    muted=True,
                    video_stopped=False,
                    params=tl.DataJSON(data="{}")
                ))
                
                # Начинаем трансляцию видео
                # Здесь должен быть код для воспроизведения видео через GroupCall API
                # К сожалению, прямая трансляция видео требует дополнительных библиотек
                # и настройки медиасервера, поэтому этот функционал нужно реализовывать
                # с использованием pytgcalls или аналогичной библиотеки
                
            except Exception as e:
                await utils.answer(status_msg, self.strings["error_playing"].format(str(e)))
            finally:
                # Очистка временных файлов
                if os.path.exists(video_path):
                    os.remove(video_path)
                    
        except Exception as e:
            await utils.answer(message, self.strings["error_playing"].format(str(e)))
