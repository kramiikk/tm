import random
from asyncio import sleep

from .. import loader, utils


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

    @loader.owner
    async def qgcmd(self, m):
        jup = ""
        for a in utils.get_args_raw(m):
            if a.lower() in alp:
                arp = alp[a.lower()]
                if a.isupper():
                    arp = arp.upper()
            else:
                arp = a
            jup += arp
        await utils.answer(m, jup)


alp = {
    "а": "a",
    "ә": "ä",
    "б": "b",
    "в": "v",
    "г": "g",
    "ғ": "ğ",
    "д": "d",
    "е": "e",
    "ж": "j",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "қ": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "ң": "ń",
    "о": "o",
    "ө": "ö",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "w",
    "ұ": "u",
    "ү": "ü",
    "ф": "f",
    "х": "h",
    "һ": "h",
    "ы": "ı",
    "і": "i",
    "ч": "ch",
    "ц": "ts",
    "ш": "c",
    "щ": "cc",
    "э": "e",
    "я": "ya",
}

# src = f"Клан Вадим и его жабехи Состав:"
#     msg = f"жмякнул {call.from_user.id}\n\nКлан Вадим и его жабехи:\n"
#     get = await self.client.get_messages(1655814348, search=src)
#     for i in get:
#         ids = re.search(r"id: (.+)", i.text).group(1)
#         reg = re.findall(r"\n(\d+)", i.text)
#         for s in reg:
#             src = f"{ids} {s} Уровень:"
#             get = await self.client.get_messages(1655814348, search=src)
#             for p in get:
#                 ger = re.search(r"ь: (\d+)", p.text)
#                 msg += f"\nУровень: {ger.group(1)}"
#                 if "Жаба:" in p.text:
#                     ger = re.search(r"а: (.+)", p.text).group(1)
#                     msg += f" Жаба: {ger}"
#     await call.edit(msg)
