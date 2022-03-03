from .. import loader, utils
import random
from asyncio import sleep


class emodjiMod(loader.Module):

    strings = {"name": "Emoji"}

    async def client_ready(self, client, db):
        self.db = db
        self.db.set("TestMod", "status", True)

    async def emojicmd(self, message):
        args = utils.get_args_raw(message)
        c = args.split(" ")
        emoji = [
            "😀",
            "😃",
            "😄",
            "😁",
            "😆",
            "😅",
            "🤣",
            "🥰",
            "😇",
            "😊",
            "😉",
            "🙃",
            "🙂",
            "😂",
            "😍",
            "🤩",
            "😘",
            "😗",
            "☺",
            "😚",
            "😙",
            "🤗",
            "🤑",
            "😝",
            "🤪",
            "😜",
            "😛",
            "😋",
            "🤭",
            "🤫",
            "🤔",
            "🤐",
            "🤨",
            "😐",
            "😑",
            "😌",
            "🤥",
            "😬",
            "🙄",
            "😒",
            "😏",
            "😶",
            "😔",
            "😪",
            "🤤",
            "😴",
            "😷",
            "🤒",
            "🤕",
            "🤢",
            "🤯",
            "🤮",
            "🤠",
            "🤧",
            "🥳",
            "🥵",
            "😎",
            "🥶",
            "🤓",
            "🥴",
            "🧐",
            "😵",
            "😕",
            "😳",
            "😢",
            "😲",
            "😥",
            "😯",
            "😰",
            "😮",
            "😨",
            "😧",
            "🙁",
            "😦",
            "😟",
            "🥺",
            "😭",
            "😫",
            "😱",
            "🥱",
            "😖",
            "😤",
            "😣",
            "😡",
            "😞",
            "😠",
            "😓",
            "🤬",
            "😩",
            "😈",
            "👿",
        ]
        d = []
        e = len(c)
        for i in range(e):
            rand = random.choice(emoji)
            d.append(c[i])
            d.append(rand)
        f = len(d) - 1
        d.pop(f)
        t = "".join(d)
        await message.edit(t)

    async def client_ready(self, client, db):
        self.db = db
        self.db.set("TestMod", "status", True)

    async def chatcmd(self, message):
        chat = str(message.chat_id)
        await message.respond(f"Айди чата: <code>{chat}</code>")

    async def logcmd(self, message):
        if utils.get_args_raw(message):
            self.args = int(utils.get_args_raw(message))
        else:
            self.args = "me"
        self.chat = message.chat_id
        status = self.db.get("TestMod", "status")
        if status is not False:
            self.db.set("TestMod", "status", False)
            await message.edit("<b>Логгер для этого чата включен!</b>")
        else:
            self.db.set("TestMod", "status", True)
            await message.edit("<b>Логгер для этого чата выключен!</b>")
        await message.delete()

    async def delmsgcmd(self, message):
        msg = [
            msg
            async for msg in message.client.iter_messages(
                message.chat_id, from_user="me"
            )
        ]
        if utils.get_args_raw(message):
            args = int(utils.get_args_raw(message))
        else:
            args = len(msg)
        for i in range(args):
            await msg[i].delete()
            await sleep(0.16)

    async def edcmd(self, message):
        args = utils.get_args_raw(message)
        text = args.split(" | ")
        words = text[1]
        text1 = text[0].split(" ")
        time = int(text1[0]) * 60
        words1 = " ".join(text1[1:])
        await message.edit(words1)
        await sleep(time)
        await message.edit(words)

    async def shifrcmd(self, message):
        text = utils.get_args_raw(message).lower()
        txtnorm = dict(
            zip(
                map(ord, "йцукенгшщзхъфывапролджэячсмитьбю. ?!,-:;"),
                "3ëjmqv9ô§üldйa¿42zэouəà>ý5eö$0¡<61¥g8tъ7",
            )
        )
        txt = text.translate(txtnorm)
        await message.edit(txt)
        await sleep(300)
        await message.delete()

    async def deshifrcmd(self, message):
        text = str(await message.get_reply_message()).split("'")
        await message.delete()
        txt = text[1]

        txtnorm = dict(
            zip(
                map(ord, "3ëjmqv9ô§üldйa¿42zэouəà>ý5eö$0¡<61¥g8tъ7"),
                "йцукенгшщзхъфывапролджэячсмитьбю. ?!,-:;7",
            )
        )
        txte = txt.translate(txtnorm)
        await message.client.send_message("me", txte)

    async def puntooncmd(self, message):
        self.truefalse = True
        await message.edit("<b>PuntoSw On.</b>")

    async def puntooffcmd(self, message):
        self.truefalse = False
        await message.edit("<b>Punto Off.</b>")

    async def watcher(self, message):
        if message.text == "+":
            await message.client.forward_messages(
                "me", (await message.get_reply_message())
            )
            await message.edit("Ready!")
        
        self.db.get("TestMod", "status")
        if self.chat != message.chat_id:
            return
        sender = await message.get_sender()
        await message.client.send_message(
            self.args,
            f"<a href=tg://user?id={sender.id}>{sender.first_name}</a>: {message.text}",
        )
