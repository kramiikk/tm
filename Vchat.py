import logging
import os
from typing import Dict, Any, Optional

import ffmpeg
import pytgcalls
from youtube_dl import YoutubeDL
from pytgcalls import GroupCallFactory
from telethon import types

from .. import loader, utils

@loader.tds
class VideoModModule(loader.Module):
    """Module for working with video chat in Hikka"""

    strings = {
        "name": "VideoMod",
        "downloading": "<b>📥 Downloading...</b>",
        "converting": "<b>🔄 Converting...</b>",
        "video_playing": "<b>🎥 Playing video...</b>",
        "joined": "<b>✅ Connected to video chat</b>",
        "no_media": "<b>❗ No media found</b>",
        "error": "<b>❌ Error: {}</b>"
    }

    def __init__(self):
        self._group_calls: Dict[str, Any] = {}
        self._client: Optional[Any] = None
        self._db: Optional[Any] = None

    async def client_ready(self, client, db):
        """Initialize client when module is ready"""
        self._client = client
        self._db = db

    def _get_group_call(self, chat_id: int) -> Any:
        """Get or create group call for a chat"""
        chat_str = str(chat_id)
        if chat_str not in self._group_calls:
            try:
                self._group_calls[chat_str] = GroupCallFactory(
                    self._client, 
                    pytgcalls.GroupCallFactory.MTPROTO_CLIENT_TYPE.TELETHON
                ).get_file_group_call()
            except Exception as e:
                logging.error(f"Failed to create group call: {e}")
                raise
        return self._group_calls[chat_str]

    async def _download_video(self, message: types.Message) -> Optional[str]:
        """Download video from message or link"""
        # Try to download video from reply
        try:
            reply = await message.get_reply_message()
            if reply and reply.video:
                return await reply.download_media()

            # Try to download from link
            args = utils.get_args_raw(message)
            if args:
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
                    
                    # Ensure it's a video file
                    if 'vcodec' not in info or info['vcodec'] == 'none':
                        await utils.answer(message, self.strings["no_media"])
                        return None
                    
                    return filename
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))
            return None

    @loader.command()
    async def vplaycmd(self, message: types.Message):
        """Play video in video chat"""
        # Validation and early return
        if not message:
            return

        # Download video
        video_file = await self._download_video(message)
        if not video_file:
            return

        input_file = None
        try:
            # Prepare conversion message
            await utils.answer(message, self.strings["converting"])
            
            # Path for converted file
            input_file = f"media_video_{os.getpid()}.raw"
            
            # Convert video
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
            
            # Get chat and group call
            chat_id = message.chat_id
            group_call = self._get_group_call(chat_id)
            
            # Start call and play video
            await group_call.start(chat_id)
            group_call.input_filename = input_file
            
            # Send success message
            await utils.answer(message, self.strings["video_playing"])
        
        except Exception as e:
            logging.error(f"Video playback error: {e}")
            await utils.answer(message, self.strings["error"].format(str(e)))
        finally:
            # Clean up temporary files
            try:
                if video_file and os.path.exists(video_file):
                    os.remove(video_file)
                if input_file and os.path.exists(input_file):
                    os.remove(input_file)
            except Exception as cleanup_e:
                logging.error(f"Cleanup error: {cleanup_e}")

    @loader.command()
    async def vjoincmd(self, message: types.Message):
        """Join video chat"""
        if not message:
            return

        try:
            chat_id = message.chat_id
            group_call = self._get_group_call(chat_id)
            await group_call.start(chat_id)
            await utils.answer(message, self.strings["joined"])
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))
