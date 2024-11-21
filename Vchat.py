# meta: 0.0.1

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
        reply = await message
