import logging
from telethon import types, functions
from telethon.tl.functions.phone import CreateGroupCallRequest, JoinGroupCallRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
import telethon.tl.types as tl

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

    @loader.command
    async def vcreate(self, message):
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
    async def vjoin(self, message):
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
