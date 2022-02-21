import logging
from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class QazGrammarMod(loader.Module):
    strings = {"name": "QAZAQ GRAMMAR"}

    async def client_ready(self, client, db):
        self.client = client

    @loader.owner
    async def qgcmd(self, m):
        jup = await m.get_reply_message()
        egz = utils.get_args_raw(m)
        if not egz:
            jzb = jup.raw_text
        else:
            jzb = egz
        jup = ""
        for a in jzb:
            if a.lower() in arp:
                arp = arp[a.lower()]
                if a.isupper():
                    arp = arp.upper()
            else:
                arp = a
            jup += arp
        await utils.answer(m, jup)


arp = {
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
