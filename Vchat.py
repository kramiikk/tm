#      Coded by D4n1l3k300       #
#   supplemented by Yahikor0     #
#    This code under AGPL-3.0    #
#          version 1.3.2         #

# requires: ffmpeg-python pytgcalls[telethon] youtube-dl ShazamAPI


import io
import os
import re

import cv2
import ffmpeg
import pytgcalls
import numpy as np
from pytgcalls import GroupCallFactory
from telethon import types
from typing import Dict

from .. import loader, utils


@loader.unrestricted
@loader.ratelimit
@loader.tds
class VoiceMod(loader.Module):
    """Модуль для работы с голосовыми чатами"""

    strings = {
        "name": "VoiceMod",
        "downloading": "<b>[VoiceMod]</b> Загрузка...",
        "converting": "<b>[VoiceMod]</b> Конвертация...",
        "playing": "<b>[VoiceMod]</b> Воспроизведение...",
        "plsjoin": "<b>[VoiceMod]</b> Вы не подключены (введите .vjoin)",
        "stop": "<b>[VoiceMod]</b> Воспроизведение остановлено!",
        "join": "<b>[VoiceMod]</b> Подключено!",
        "leave": "<b>[VoiceMod]</b> Отключено!",
        "pause": "<b>[VoiceMod]</b> Приостановлено!",
        "resume": "<b>[VoiceMod]</b> Продолжено!",
        "error": "<b>[VoiceMod]</b> Ошибка: <code>{}</code>",
        "no_video": "<b>[VoiceMod]</b> Нет видео в ответе",
    }

    group_calls: Dict[str, GroupCallFactory] = {}

    async def get_chat(self, m: types.Message):
        """Получение ID чата"""
        args = utils.get_args_raw(m)
        if not args:
            chat = m.chat.id
        else:
            try:
                chat = int(args)
            except:
                chat = args
            try:
                chat = (await m.client.get_entity(chat)).id
            except Exception as e:
                await utils.answer(m, self.strings("error").format(str(e)))
                return None
        return chat

    def _call(self, m: types.Message, chat: int):
        """Создание группового вызова"""
        if str(chat) not in self.group_calls:
            self.group_calls[str(chat)] = GroupCallFactory(
                m.client, pytgcalls.GroupCallFactory.MTPROTO_CLIENT_TYPE.TELETHON
            ).get_file_group_call()

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    async def vjoincmd(self, m: types.Message):
        """.vjoin
        Присоединиться к войс-чату"""
        try:
            chat = await self.get_chat(m)
            if not chat:
                return
            # Создаем групповой вызов перед подключением

            if str(chat) not in self.group_calls:
                self._call(m, chat)
            # Подключение к войс-чату

            await self.group_calls[str(chat)].start(chat)
            await utils.answer(m, self.strings("join"))
        except Exception as e:
            import traceback

            traceback.print_exc()
            await utils.answer(m, f"Ошибка подключения: {e}")

    async def vplayvideocmd(self, message: types.Message):
        """.vplayvideo [chat (optional)] <reply to video>
        Воспроизведение видео в войс-чате"""
        args = utils.get_args_raw(message)
        r = await message.get_reply_message()

        if not r or not r.media:
            return await utils.answer(message, self.strings("no_video"))
        try:
            # Определение чата

            chat = None
            if args:
                try:
                    chat = int(args)
                except:
                    chat = args
                try:
                    chat = (await message.client.get_entity(chat)).id
                except Exception as e:
                    return await utils.answer(
                        message, self.strings("error").format(str(e))
                    )
            else:
                chat = message.chat.id
            # Проверка подключения к войс-чату

            if str(chat) not in self.group_calls:
                return await utils.answer(message, self.strings("plsjoin"))
            self._call(message, chat)
            input_file = f"{chat}.raw"

            # Загрузка видео

            m = await utils.answer(message, self.strings("downloading"))
            video_original = await r.download_media()

            # Конвертация видео

            m = await utils.answer(m, self.strings("converting"))
            cap = cv2.VideoCapture(video_original)
            fourcc = cv2.VideoWriter_fourcc(*"XVID")

            # Define width and height

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            out = cv2.VideoWriter(input_file, fourcc, 20.0, (width, height))

            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                out.write(frame)
            cap.release()
            out.release()

            try:
                ffmpeg.input(video_original).output(
                    input_file, format="s16le", acodec="pcm_s16le", ac=2, ar="48k"
                ).overwrite_output().run()
            except Exception as convert_error:
                await utils.answer(message, f"Ошибка конвертации: {convert_error}")
                return
            # Удаляем оригинальный файл

            try:
                os.remove(video_original)
            except:
                pass
            # Воспроизведение

            await utils.answer(m, self.strings("playing"))
            self.group_calls[str(chat)].input_filename = input_file
        except Exception as e:
            import traceback

            traceback.print_exc()
            return await utils.answer(message, self.strings("error").format(str(e)))

    # Остальные методы (vleavecmd, vstopcmd и т.д.) остаются без изменений

    async def vleavecmd(self, m: types.Message):
        """Покинуть войс-чат"""
        chat = await self.get_chat(m)
        if not chat:
            return
        self._call(m, chat)
        await self.group_calls[str(chat)].stop()
        del self.group_calls[str(chat)]
        try:
            os.remove(f"{chat}.raw")
        except:
            pass
        await utils.answer(m, self.strings("leave"))

    async def vstopcmd(self, m: types.Message):
        """.vstop
        Stop play in VC"""
        chat = await self.get_chat(m)
        if not chat:
            return
        self._call(m, chat)
        self.group_calls[str(chat)].stop_playout()
        await utils.answer(m, self.strings("stop"))

    async def vpausecmd(self, m: types.Message):
        """.vpause
        Pause player in VC"""
        chat = await self.get_chat(m)
        if not chat:
            return
        self._call(m, chat)
        self.group_calls[str(chat)].pause_playout()
        await utils.answer(m, self.strings("pause"))

    async def vresumecmd(self, m: types.Message):
        """.vresume
        Resume player in VC"""
        chat = await self.get_chat(m)
        if not chat:
            return
        self._call(m, chat)
        self.group_calls[str(chat)].resume_playout()
        await utils.answer(m, self.strings("resume"))

    async def vdebugcmd(self, m: types.Message):
        """.vdebug
        debug"""
        await utils.answer(m, f"DEBUG : {self.group_calls}")

    @loader.unrestricted
    async def smcmd(self, message):
        """.sm
        to find music."""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        if not args:
            return await utils.answer(message, "<b>No args.</b>")
        try:
            message = await utils.answer(message, "<b>Loading...</b>")
            try:
                message = message[0]
            except:
                pass
            music = await self.client.inline_query("lybot", args)
            await message.delete()
            await self.client.send_file(
                message.peer_id,
                music[0].result.document,
                reply_to=reply.id if reply else None,
            )
        except:
            return await self.client.send_message(
                message.chat_id,
                f"<b> Music named <code> {args} </code> not found. </b>",
            )
