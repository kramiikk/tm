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
        if isinstance(m, Message) and (
            (
                m.text.casefold() == "сменить"
                and (m.photo or m.gif or m.video or m.audio)
            )
            or m.text.casefold() in ("инфо", "топ", "мяу")
        ):
            ass = self.db.get("Su", "as", {})
            files = None
            if m.text.casefold() == "топ":
                e = await self.inline.bot.send_message(
                    m.chat_id, "🤩", parse_mode="HTML"
                )
                txt = "Топ багоюзеров:"
                for i in enumerate(
                    sorted(ass.items(), key=lambda x: x[1], reverse=True), 1
                ):
                    a = "🩲" if i[0] == 1 else i[1][1][0]
                    txt += f"\n{i[0]} | {i[1][1][1]} <code>{a}</code>"
                    await asyncio.sleep(3)
                    await self.inline.bot.edit_message_text(
                        chat_id=m.chat_id, message_id=e.message_id, text=txt
                    )
                    if i[0] == 10:
                        break
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
                txt = (
                    f"Имя: {ass[str(m.sender_id)][1]}\nОчки: {ass[str(m.sender_id)][0]}"
                )
            else:
                txt = ""
                files = "CAADBQADOgkAAmXZgVYsIyelvGbrZgI"
            if files is not None:
                await m.respond(message=txt, file=files)
            else:
                e = await self.inline.bot.send_message(m.chat_id, e, parse_mode="HTML")
                await asyncio.sleep(3)
                await self.inline.bot.edit_message_text(
                    chat_id=m.chat_id, message_id=e.message_id, text=txt
                )
        elif isinstance(m, Message) and (
            (
                str(m.sender_id) not in tis
                or (
                    str(m.sender_id) in tis
                    and (
                        len(tis[str(m.sender_id)]) < 3
                        or (
                            len(tis[str(m.sender_id)]) == 4
                            and m.dice
                            and m.dice.emoticon == tis[str(m.sender_id)][3]
                        )
                    )
                )
            )
            or (
                m.text.casefold().startswith("закидать ")
                and m.text.count(" ") != 1
                and (
                    "тп" in m.text.casefold()
                    or "поддержку" in m.text.casefold()
                    or "модер" in m.text.casefold()
                    or "админ" in m.text.casefold()
                    or "серв" in m.text.casefold()
                )
            )
        ):
            ass = self.db.get("Su", "as", {})
            tis = self.db.get("Su", "ti", {})
            ct = datetime.datetime.now()
            eco = random.randint(3, 13)
            time = ct.minute + ct.second
            tis.setdefault(str(m.sender_id), [time - eco])
            if (
                not m.dice
                and len(tis[str(m.sender_id)]) == 4
                and -1 < (ct.hour + ct.minute - tis[str(m.sender_id)][1]) < 1
            ):
                return
            ass.setdefault(str(m.sender_id), [0, m.sender.first_name, "2"])
            dic = random.choice(("🎲", "🏀", "⚽️", "🎯", "🎳"))
            e = None
            if m.dice and m.dice.value <= tis[str(m.sender_id)][2]:
                a = await self.inline.bot.send_dice(m.chat_id, emoji=dic)
                tis[str(m.sender_id)][2] = a.dice.value
                tis[str(m.sender_id)][3] = a.dice.emoji
            elif len(tis[str(m.sender_id)]) == 2:
                e = await self.inline.bot.send_message(
                    m.chat_id, "🤫", parse_mode="HTML"
                )
                await asyncio.sleep(3)
                await self.inline.bot.edit_message_text(
                    chat_id=m.chat_id, message_id=e.message_id, text="Поиграем?"
                )
                a = await self.inline.bot.send_dice(m.chat_id, emoji=dic)
                tis[str(m.sender_id)].append(a.dice.value)
                tis[str(m.sender_id)].append(a.dice.emoji)
            else:
                cmn = "🥞🤰🏼"
                n = 0
                if len(tis[str(m.sender_id)]) == 4:
                    if m.dice:
                        n = m.media.value
                        cmn = f"🧘🏿\n+{n} получаете за победу в этой хуйне"
                    else:
                        n = random.randint(2, 6)
                        cmn = f"🦩\n+{n} получаете просто так"
                    tis[str(m.sender_id)] = [time - eco]
                else:
                    num = random.randint(2, 5)
                    top = {
                        "дерь": "💩",
                        "говн": "💩",
                        "письк": "💩",
                        "ху": "🥵",
                        "член": "🥵",
                    }
                    for i in top:
                        if i in m.text.casefold():
                            cmn = (
                                "👄 Смачно отсосали!💦💦💦🥵🥵🥵" if top[i] == "🥵" else top[i]
                            )
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
                await self.inline.bot.send_animation(
                    m.chat_id,
                    animation=random.choice(
                        [
                            "https://i0.wp.com/www.sexecherche.com/fr/blog/wp-content/uploads/2020/08/funny-porn-gifs-00001-1.gif",
                            "https://image.myanimelist.net/ui/OK6W_koKDTOqqqLDbIoPAkajdI1rwIc_Z7jTNA8TNJk",
                            "https://img3.gelbooru.com/images/79/7d/797d0958efc9158905da20521c48edb0.gif",
                            "https://64.media.tumblr.com/512141ad8c03d1760b9f561acd94d60f/tumblr_ou8tyyV4Gk1tlyjpto1_540.gif",
                        ]
                    ),
                    caption=txt,
                )
                if -1 < (time - tis[str(m.sender_id)][0]) < eco:
                    tis[str(m.sender_id)].append(ct.hour + ct.minute)
                else:
                    tis[str(m.sender_id)] = [time]
            self.db.set("Su", "ti", tis)
            self.db.set("Su", "as", ass)
