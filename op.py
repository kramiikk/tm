import asyncio
import logging

from telethon.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class StatusesMod(loader.Module):
    """AFK Module analog with extended functionality"""

    strings = {
        "name": "Statuses",
        "status_not_found": "<b>🚫 Status not found</b>",
        "status_set": "<b>✅ Status set\n</b><code>{}</code>",
        "pzd_with_args": "<b>🚫 Args are incorrect</b>",
        "status_created": "<b>✅ Status {} created\n</b><code>{}</code>\n",
        "status_removed": "<b>✅ Status {} deleted</b>",
        "no_status": "<b>🚫 No status is active</b>",
        "status_unset": "<b>✅ Status removed</b>",
        "available_statuses": "<b>🦊 Available statuses:</b>\n\n",
    }

    def __init__(self):
        self._ratelimit = []
        self._sent_messages = []

    @loader.tag("only_messages", "in")
    async def watcher(self, message: Message):
        if not self.get("status", False):
            return
        if not message.is_private:
            return
        user = await message.get_sender()
        if user.id in self._ratelimit or user.is_self or user.bot or user.verified:
            return
        chat = utils.get_chat_id(message)

        if chat in self._ratelimit:
            return
        txt = self.get("texts", {"": ""})[self.get("status", "")]
        t = f"{user.id}"
        txt += f"\nВаш ID: <code>{t}</code>"
        try:
            p = await self.client.get_messages(1539778138, search=t)
            if p.total == 0:
                p = await self.client.get_messages(1474490997, search=t)
                if p.total == 0:
                    txt += ""
                else:
                    txt += " <b>ss:</b> ⚠️"
            else:
                txt += " <b>ss:</b> 🚷"
            p = await self.client.get_messages(1660119676, search=t)
            if p.total == 0:
                p = await self.client.get_messages(1661258940, search=t)
                if p.total == 0:
                    txt += ""
                else:
                    txt += " <b>sgb:</b> ⚠️"
            else:
                txt += " <b>sgb:</b> 🚷"
            p = await self.client.get_messages(1584117978, search=t)
            if p.total == 0:
                p = await self.client.get_messages(1629001634, search=t)
                if p.total == 0:
                    txt += ""
                else:
                    txt += " <b>bk:</b> ⚠️"
            else:
                txt += " <b>bk:</b> 🚷"
        except Exception:
            logger.exception("Res Not Avi")
        m = await utils.answer(message, txt)
        self._sent_messages += [m]
        self._ratelimit += [chat]

    async def statuscmd(self, message: Message):
        """<short_name> - Set status"""
        args = utils.get_args_raw(message)
        if args not in self.get("texts", {}):
            await utils.answer(message, self.strings("status_not_found"))
            await asyncio.sleep(3)
            await message.delete()
            return
        self.set("status", args)
        self._ratelimit = []
        await utils.answer(
            message,
            self.strings("status_set").format(
                utils.escape_html(self.get("texts", {})[args])
            ),
        )

    async def newstatuscmd(self, message: Message):
        """<short_name> <text> - New status
        Example: .newstatus test Hello!"""
        args = utils.get_args_raw(message)
        args = args.split(" ", 1)
        if len(args) < 2:
            await utils.answer(message, self.strings("pzd_with_args"))
            await asyncio.sleep(3)
            await message.delete()
            return
        texts = self.get("texts", {})
        texts[args[0]] = args[1]
        self.set("texts", texts)

        await utils.answer(
            message,
            self.strings("status_created").format(
                utils.escape_html(args[0]),
                args[1],
            ),
        )

    async def delstatuscmd(self, message: Message):
        """<short_name> - Delete status"""
        args = utils.get_args_raw(message)
        if args not in self.get("texts", {}):
            await utils.answer(message, self.strings("status_not_found"))
            await asyncio.sleep(3)
            await message.delete()
            return
        texts = self.get("texts", {})
        del texts[args]
        self.set("texts", texts)

    async def unstatuscmd(self, message: Message):
        """Remove status"""
        if not self.get("status", False):
            await utils.answer(message, self.strings("no_status"))
            await asyncio.sleep(3)
            await message.delete()
            return
        self.set("status", False)
        self._ratelimit = []

        for m in self._sent_messages:
            try:
                await m.delete()
            except Exception:
                logger.exception("Message not deleted due to")
        self._sent_messages = []

        await utils.answer(message, self.strings("status_unset"))

    async def statusescmd(self, message: Message):
        """Show available statuses"""
        res = self.strings("available_statuses")
        for short_name, status in self.get("texts", {}).items():
            res += f"<b><u>{short_name}</u></b>\n{status}\n➖➖➖➖➖➖➖➖➖\n"
        await utils.answer(message, res)
