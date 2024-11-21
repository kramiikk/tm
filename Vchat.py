#      Coded by D4n1l3k300       #
#   supplemented by Yahikor0     #
#    This code under AGPL-3.0    #

# requires: ffmpeg-python pytgcalls[telethon] youtube-dl ShazamAPI

import io
import os
import re
import logging
import asyncio

import ffmpeg
import pytgcalls
from ShazamAPI import Shazam
from youtube_dl import YoutubeDL
from pytgcalls import GroupCallFactory
from pytgcalls.implementation.group_call_file import GroupCallFile
from telethon import types
from typing import *

from .. import loader, utils

@loader.tds
class VoiceMod(loader.Module):
    """Module for working with voice and video chat"""

    strings = {
        "name": "VoiceMod",
        "downloading": "<b>[VoiceMod]</b> Downloading...",
        "converting": "<b>[VoiceMod]</b> Converting...",
        "playing": "<b>[VoiceMod]</b> Playing...",
        "plsjoin": "<b>[VoiceMod]</b> You are not joined (type .vjoin)",
        "stop": "<b>[VoiceMod]</b> Playing stopped!",
        "join": "<b>[VoiceMod]</b> Joined!",
        "leave": "<b>[VoiceMod]</b> Leaved!",
        "pause": "<b>[VoiceMod]</b> Paused!",
        "resume": "<b>[VoiceMod]</b> Resumed!",
        "mute": "<b>[VoiceMod]</b> Muted!",
        "unmute": "<b>[VoiceMod]</b> Unmuted!",
        "replay": "<b>[VoiceMod]</b> Replaying...",
        "error": "<b>[VoiceMod]</b> Error: <code>{}</code>",
        "video_playing": "<b>[VoiceMod]</b> Video playing...",
        "no_media": "<b>[VoiceMod]</b> No audio/video found.",
    }
    
    ytdlopts = {
        "format": "bestvideo+bestaudio/best",
        "addmetadata": True,
        "key": "FFmpegMetadata",
        "writethumbnail": True,
        "prefer_ffmpeg": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            },
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": "%(title)s.%(ext)s",
        "quiet": True,
        "nooverwrites": True,
        "no_warnings": True,
        "default_search": "ytsearch",
    }
    
    def __init__(self):
        self.group_calls = {}
        self.client = None
        self.db = None

    async def client_ready(self, client, db):
        """Initialize client and database"""
        self.client = client
        self.db = db
        return True

    async def _get_chat(self, m: types.Message):
        """Get chat ID from message"""
        args = utils.get_args_raw(m)
        if not args:
            return m.chat.id
        
        try:
            # Try to get chat ID directly
            chat = int(args)
        except:
            # If not a number, try to get entity
            try:
                chat = (await m.client.get_entity(args)).id
            except Exception as e:
                await utils.answer(m, self.strings("error").format(str(e)))
                return None
        
        return chat

    def _init_group_call(self, client, chat):
        """Initialize group call for a chat"""
        chat_str = str(chat)
        if chat_str not in self.group_calls:
            self.group_calls[chat_str] = GroupCallFactory(
                client, 
                pytgcalls.GroupCallFactory.MTPROTO_CLIENT_TYPE.TELETHON
            ).get_file_group_call()
        return self.group_calls[chat_str]

    async def _download_media(self, m: types.Message):
        """Download media from message or link"""
        args = utils.get_args_raw(m)
        r = await m.get_reply_message()
        
        # Check replied media first
        if r:
            if r.video:
                return await r.download_media(bytes), True
            elif r.audio:
                return await r.download_media(bytes), False
        
        # Try to download from link
        if args:
            try:
                with YoutubeDL(self.ytdlopts) as ydl:
                    info = ydl.extract_info(args, download=True)
                    filename = ydl.prepare_filename(info)
                    
                    # Determine if it's a video
                    is_video = 'vcodec' in info and info['vcodec'] != 'none'
                    return filename, is_video
            except Exception as e:
                await utils.answer(m, self.strings("error").format(str(e)))
                return None, None
        
        return None, None

    async def vplaycmd(self, m: types.Message):
        """Play audio/video in voice chat"""
        # Download media
        media, is_video = await self._download_media(m)
        if not media:
            return await utils.answer(m, self.strings("no_media"))
        
        # Get chat
        chat = await self._get_chat(m)
        if not chat:
            return
        
        try:
            # Prepare message
            m = await utils.answer(m, self.strings("converting"))
            
            # Prepare media for playback
            input_file = f"media_{'video' if is_video else 'audio'}_{os.getpid()}.raw"
            
            # Convert media
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
            
            # Initialize group call
            group_call = self._init_group_call(self.client, chat)
            
            # Start call and play
            await group_call.start(chat)
            group_call.input_filename = input_file
            
            # Send success message
            await utils.answer(m, self.strings("video_playing" if is_video else "playing"))
        
        except Exception as e:
            logging.error(f"Playback error: {e}")
            await utils.answer(m, self.strings("error").format(str(e)))
        finally:
            # Cleanup files
            try:
                if isinstance(media, str) and os.path.exists(media):
                    os.remove(media)
                if os.path.exists(input_file):
                    os.remove(input_file)
            except Exception as cleanup_e:
                logging.error(f"Cleanup error: {cleanup_e}")

    async def vjoincmd(self, m: types.Message):
        """Join voice chat"""
        chat = await self._get_chat(m)
        if not chat:
            return
        
        try:
            group_call = self._init_group_call(self.client, chat)
            await group_call.start(chat)
            await utils.answer(m, self.strings("join"))
        except Exception as e:
            await utils.answer(m, self.strings("error").format(str(e)))

    async def vleavecmd(self, m: types.Message):
        """Leave voice chat"""
        chat = await self._get_chat(m)
        if not chat:
            return
        
        try:
            chat_str = str(chat)
            if chat_str in self.group_calls:
                await self.group_calls[chat_str].stop()
                del self.group_calls[chat_str]
            await utils.answer(m, self.strings("leave"))
        except Exception as e:
            await utils.answer(m, self.strings("error").format(str(e)))

    async def vreplaycmd(self, m: types.Message):
        """.vreplay
        Replay audio in VC"""
        chat = await self.get_chat(m)
        if not chat:
            return
        self._call(m, chat)
        self.group_calls[str(chat)].restart_playout()
        await utils.answer(m, self.strings("replay"))

    async def vstopcmd(self, m: types.Message):
        """.vstop
        Stop play in VC"""
        chat = await self.get_chat(m)
        if not chat:
            return
        self._call(m, chat)
        self.group_calls[str(chat)].stop_playout()
        await utils.answer(m, self.strings("stop"))

    async def vmutecmd(self, m: types.Message):
        """.vmute
        Mute player in VC"""
        chat = await self.get_chat(m)
        if not chat:
            return
        self._call(m, chat)
        self.group_calls[str(chat)].set_is_mute(True)
        await utils.answer(m, self.strings("unmute"))

    async def vunmutecmd(self, m: types.Message):
        """.vmute
        Unmute player in VC"""
        chat = await self.get_chat(m)
        if not chat:
            return
        self._call(m, chat)
        self.group_calls[str(chat)].set_is_mute(False)
        await utils.answer(m, self.strings("mute"))

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

    async def shazamcmd(self, message):
        """.shazam <reply to audio> - recognize track"""
        s = await get_audio_shazam(message)
        if not s:
            return
        try:
            shazam = Shazam(s.track.read())
            recog = shazam.recognizeSong()
            track = next(recog)[1]["track"]
            await self.client.send_file(
                message.peer_id,
                file=track["images"]["background"],
                caption=self.tag + "recognized track: " + track["share"]["subject"],
                reply_to=s.reply.id,
            )
            await message.delete()
        except:
            await utils.answer(message, self.tag + "Could not recognize...")


async def get_audio_shazam(message):
    class rct:
        track = io.BytesIO()
        reply = None

    reply = await message.get_reply_message()
    if reply and reply.file and reply.file.mime_type.split("/")[0] == "audio":
        ae = rct()
        await utils.answer(message, "<b>Downloading...</b>")
        ae.track = io.BytesIO(await reply.download_media(bytes))
        ae.reply = reply
        await utils.answer(message, "<b>Recognizing...</b>")
        return ae
    else:
        await utils.answer(message, "<b>reply to audio...</b>")
        return None
