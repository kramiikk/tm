import asyncio
import datetime
import random

from telethon.tl.types import Message

from .. import loader


@loader.tds
class AssMod(loader.Module):
    """add"""

    strings = {"name": "Ass"}

    async def client_ready(self, client, db):
        """ready"""
        self.client = client
        self.db = db

    async def watcher(self, m):
        """алко"""
        tis = self.db.get("Su", "ti", {})
        if not isinstance(m, Message) or (
            (
                not m.dice
                or str(m.sender_id) not in tis
                or len(tis[str(m.sender_id)]) != 4
                or m.dice.emoticon != tis[str(m.sender_id)][3]
            )
            and (
                not m.text.casefold().startswith("закидать ")
                or m.text.count(" ") == 1
                or (
                    "тп" not in m.text.casefold()
                    and "поддержку" not in m.text.casefold()
                    and "модер" not in m.text.casefold()
                    and "админ" not in m.text.casefold()
                    and "серв" not in m.text.casefold()
                )
            )
            and (
                m.text.casefold() != "сменить"
                or (not m.photo and not m.gif and not m.video and not m.audio)
            )
            and m.text.casefold() not in ("инфо", "топ", "мяу")
        ):
            return
        ct = datetime.datetime.now()
        time = ct.minute + ct.second
        tis.setdefault(str(m.sender_id), [time - 7])
        if (
            not m.dice
            and len(tis[str(m.sender_id)]) == 4
            and -1 < (ct.hour + ct.minute - tis[str(m.sender_id)][1]) < 1
        ):
            return
        ass = self.db.get("Su", "as", {})
        ass.setdefault(str(m.sender_id), [0, m.sender.first_name, "2"])
        dic = random.choice(("🎲", "🏀", "⚽️", "🎯", "🎳"))
        files = None
        e = None
        if m.dice and m.dice.value <= tis[str(m.sender_id)][2]:
            a = await self.inline.bot.send_dice(m.chat_id, emoji=dic)
            tis[str(m.sender_id)][2] = a.dice.value
            tis[str(m.sender_id)][3] = a.dice.emoji
            self.db.set("Su", "ti", tis)
            return
        if len(tis[str(m.sender_id)]) == 2:
            e = await self.inline.bot.send_message(
                m.chat_id, "🤫", parse_mode="HTML", reply_to_message_id=m.id
            )
            await asyncio.sleep(1)
            await self.inline.bot.edit_message_text(
                chat_id=m.chat_id, message_id=e.message_id, text="Поиграем?"
            )
            a = await self.inline.bot.send_dice(m.chat_id, emoji=dic)
            tis[str(m.sender_id)].append(a.dice.value)
            tis[str(m.sender_id)].append(a.dice.emoji)
            self.db.set("Su", "ti", tis)
            return
        if m.text.casefold() == "сменить":
            a = await self.client.send_message(1688531303, m)
            ass[str(m.sender_id)] = [
                ass[str(m.sender_id)][0],
                m.sender.first_name,
                str(a.id),
            ]
            txt = "Модерация успешно подрочила😊"
            e = "👍"
        elif m.text.casefold() == "инфо":
            files = await self.client.get_messages(
                1688531303, ids=int(ass[str(m.sender_id)][2])
            )
            txt = f"Имя: {ass[str(m.sender_id)][1]}\nОчки: {ass[str(m.sender_id)][0]}"
        elif m.text.casefold() == "топ":
            txt = "Топ багоюзеров:"
            for i in enumerate(
                sorted(ass.items(), key=lambda x: x[1], reverse=True), 1
            ):
                a = "🩲" if i[0] == 1 else i[1][1][0]
                txt += f"\n{i[0]} | {i[1][1][1]} <code>{a}</code>"
                if i[0] == 10:
                    break
            e = "🤩"
        elif m.text.casefold() == "мяу":
            txt = ""
            files = "CAADBQADOgkAAmXZgVYsIyelvGbrZgI"
        else:
            cmn = "🥞🤰🏼"
            n = 0
            if len(tis[str(m.sender_id)]) == 4:
                if m.dice:
                    n = m.media.value
                    cmn = f"🛀\n+{n} получаете за победу в этой хуйне"
                else:
                    n = random.randint(2, 5)
                tis[str(m.sender_id)] = [time - 7]
            else:
                num = random.randint(2, 5)
                top = {"дерь": "💩", "говн": "💩", "письк": "💩", "ху": "🥵", "член": "🥵"}
                for i in top:
                    if i in m.text.casefold():
                        cmn = "👄 Смачно отсосали!💦💦💦🥵🥵🥵" if top[i] == "🥵" else top[i]
                        break
                cmn += f"\n{num} админа жабабота вам благодарны🎉"
            num = -n if n != 0 else num
            ass[str(m.sender_id)][0] += num
            n = ass[str(m.sender_id)][0]
            txt = (
                f"Спасибо! Вы накормили модерку{cmn}\n\n <b>Ваша репутация в тп:</b> "
                + ("-" if n > -1 else "+")
                + f"{ass[str(m.sender_id)][0]}🤯"
            )
            files = 0
        if -1 < (time - tis[str(m.sender_id)][0]) < 7:
            tis[str(m.sender_id)].append(ct.hour + ct.minute)
        else:
            tis[str(m.sender_id)] = [time]
        self.db.set("Su", "ti", tis)
        self.db.set("Su", "as", ass)
        if files == 0:
            await self.inline.bot.send_animation(
                m.chat_id,
                animation=random.choice(
                    [
                        "https://i0.wp.com/www.sexecherche.com/fr/blog/wp-content/uploads/2020/08/funny-porn-gifs-00001-1.gif",
                        "https://image.myanimelist.net/ui/OK6W_koKDTOqqqLDbIoPAkajdI1rwIc_Z7jTNA8TNJk",
                    ]
                ),
                caption=txt,
            )
        elif files is not None:
            await m.respond(message=txt, file=files)
        else:
            e = await self.inline.bot.send_message(m.chat_id, e, parse_mode="HTML")
            await asyncio.sleep(1)
            await self.inline.bot.edit_message_text(
                chat_id=m.chat_id, message_id=e.message_id, text=txt
            )
