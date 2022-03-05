from .. import loader, utils
import random
from asyncio import sleep


class emodjiMod(loader.Module):

    strings = {"name": "Emoji"}

    async def client_ready(self, client, db):
        self.db = db
        self.client = client

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

    async def chatcmd(self, message):
        for i in dgn:
            await self.client.send_message(message.chat_id, f"<b>скрафтить {i}</b>")
        chat = str(message.chat_id)
        await message.respond(f"Айди чата: <code>{chat}</code>")

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

dgn = ["клюв цапли", "букашкомет", "наголовник из клюва цапли", "нагрудник из клюва цапли", "налапники из клюва цапли"]
