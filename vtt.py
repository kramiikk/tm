import os
import random
from time import time

from telethon import events

from .. import loader, utils

try:
    import speech_recognition as sr
    from pydub import AudioSegment
except:
    os.popen("python3 -m pip install pydub speech_recognition --upgrade").read()
    import speech_recognition as sr
    from pydub import AudioSegment

import asyncio

# requires: pydub speechrecognition


@loader.tds
class VoicyMod(loader.Module):
    """Recognize voice messages"""

    strings = {
        "name": "Voicy",
        "converting": "<code>🗣 Распознаю голосовое сообщение...</code>",
        "converted": "<b>{}</b>\n\n🗣<pre>{}</pre>",
        "no_ffmpeg": '<b>Вам необходимо установить ffmpeg.</b> <a href="https://t.me/ftgchatru/454189">Инструкция</a>',
        "voice_not_found": "🗣 <b>Войс не найден</b>",
        "autovoice_off": "<b>🗣 Я больше не буду автоматически распознавать голосовые сообщения в этом чате</b>",
        "autovoice_on": "<b>🗣 Теперь я буду распознавать голосовые сообщения в этом чате</b>",
    }

    async def client_ready(self, client, db):
        self.db = db
        self.chats = self.db.get("vtt", "chats", [])
        self.client = client

    async def recognize(self, event):
        try:
            while True:
                a = random.choice(await self.client.get_messages("notburningout", 3000)).text
                break
            filename = "/tmp/" + str(time()).replace(".", "")
            await event.download_media(file=filename + ".ogg")
            song = AudioSegment.from_ogg(filename + ".ogg")
            song.export(filename + ".wav", format="wav")
            event = await utils.answer(event, self.strings("converting", event))
            try:
                event = event[0]
            except:
                pass
            r = sr.Recognizer()
            with sr.AudioFile(filename + ".wav") as source:
                audio_data = r.record(source)
                text = r.recognize_google(audio_data, language="ru-RU")
                await utils.answer(event, self.strings("converted", event).format(a, text))
        except Exception as e:
            if "ffprobe" in str(e):
                await utils.answer(event, self.strings("no_ffmpeg", event))
            else:
                await event.delete()

    @loader.unrestricted
    async def voicycmd(self, message):
        reply = await message.get_reply_message()
        if not reply or not reply.media or not reply.media.document.attributes[0].voice:
            await utils.answer(message, self.strings("voice_not_found", message))
            await asyncio.sleep(2)
            await message.delete()
            return

        await self.recognize(reply)
        await message.delete()

    async def watcher(self, event):
        chat_id = utils.get_chat_id(event)
        if chat_id not in self.chats:
            return

        try:
            if not event.media or not event.media.document.attributes[0].voice:
                return
        except:
            return

        await self.recognize(event)

    async def autovoicecmd(self, message):
        """Напиши это в чате, чтобы автоматически распознавать в нем голосовые. Если написать ее повторно, распознавание будет отключено."""
        chat_id = utils.get_chat_id(message)
        if chat_id in self.chats:
            self.chats.remove(chat_id)
            await utils.answer(message, self.strings("autovoice_off"))
        else:
            self.chats.append(chat_id)
            await utils.answer(message, self.strings("autovoice_on"))

        self.db.set("vtt", "chats", self.chats)