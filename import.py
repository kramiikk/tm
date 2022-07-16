import datetime
import random

from telethon.tl.types import Message

from .. import loader


@loader.tds
class AssMod(loader.Module):
    """Модуль"""

    strings = {"name": "Ass"}

    async def client_ready(self, client, db):
        """ready"""
        self.client = client
        self.db = db
        self.ass = db.get("Su", "as", {})
        self.tis = db.get("Su", "ti", {})

    async def watcher(self, m):
        """алко"""
        if not isinstance(m, Message):
            return
        if m.text.casefold() == "сменить" and (m.photo or m.gif):
            a = await self.client.send_message(1688531303, m)
            self.ass.setdefault(str(m.sender_id), [0, m.sender.first_name, "2"])
            self.ass[str(m.sender_id)] = [
                self.ass[str(m.sender_id)][0],
                m.sender.first_name,
                str(a.id),
            ]
            self.db.set("Su", "as", self.ass)
            return await m.respond("Модерация успешно подрочила😊👍")
        if m.text.casefold() == "инфо":
            self.ass.setdefault(str(m.sender_id), [0, m.sender.first_name, "2"])
            if len(self.ass[str(m.sender_id)]) == 2:
                self.ass[str(m.sender_id)] = [
                    self.ass[str(m.sender_id)][0],
                    m.sender.first_name,
                    "2",
                ]
                self.db.set("Su", "as", self.ass)
            a = await self.client.get_messages(
                1688531303, ids=int(self.ass[str(m.sender_id)][2])
            )
            return await m.respond(
                f"Имя: {self.ass[str(m.sender_id)][1]}\nОчки: {self.ass[str(m.sender_id)][0]}",
                file=a.photo if a.photo else a.gif,
            )
        if m.text.casefold() == "топ":
            top = "Топ багоюзеров:"
            for i in enumerate(
                sorted(self.ass.items(), key=lambda x: x[1], reverse=True), 1
            ):
                a = "🩲" if i[0] == 1 else i[1][1][0]
                top += f"\n{i[0]} | {i[1][1][1]} <code>{a}</code>"
                if i[0] == 10:
                    break
            self.db.set("Su", "as", self.ass)
            return await m.respond(top)
        if m.text.casefold() == "мяу":
            return await m.respond(file="CAADBQADOgkAAmXZgVYsIyelvGbrZgI")
        if (
            not m.text.casefold().startswith("закидать ")
            or (
                "тп" not in m.text.casefold()
                and "поддержку" not in m.text.casefold()
                and "модер" not in m.text.casefold()
                and "админ" not in m.text.casefold()
                and "серв" not in m.text.casefold()
            )
            or m.text.count(" ") == 1
        ):
            return
        ct = datetime.datetime.now()
        time = ct.minute + ct.second
        n = 0
        txt = ""
        self.tis.setdefault(str(m.sender_id), [time - 3])
        if len(self.tis[str(m.sender_id)]) == 7 and (
            (
                datetime.timedelta(days=-1)
                < (
                    datetime.timedelta(
                        hours=ct.hour, minutes=ct.minute, seconds=ct.second
                    )
                    - datetime.timedelta(
                        hours=self.tis[str(m.sender_id)][3],
                        minutes=self.tis[str(m.sender_id)][4],
                        seconds=self.tis[str(m.sender_id)][5],
                    )
                )
                < datetime.timedelta(minutes=1)
            )
            and not m.dice
        ):
            return
        elif len(self.tis[str(m.sender_id)]) == 7 and m.dice:
            if m.media.value < self.tis[str(m.sender_id)][6]:
                self.tis[str(m.sender_id)][6] = (await m.respond(file=InputMediaDice("🎲"))).media.value
                self.db.set("Su", "ti", self.tis)
                return
            n = m.media.value
            txt = f"\n+{n} получаете за победу в хуйне"
        if len(self.tis[str(m.sender_id)]) == 7:
            self.tis[str(m.sender_id)] = [time - 3]
            self.db.set("Su", "ti", self.tis)
        if len(self.tis[str(m.sender_id)]) == 3:
            await m.reply("Поиграем?😏🤭🤫")
            self.tis[str(m.sender_id)].append(ct.hour)
            self.tis[str(m.sender_id)].append(ct.minute)
            self.tis[str(m.sender_id)].append(ct.second)
            self.tis[str(m.sender_id)].append((await m.respond(file=InputMediaDice("🎲")).media.value))
            self.db.set("Su", "ti", self.tis)
            return
        top = {"дерь": "💩", "говн": "💩", "письк": "💩", "ху": "🥵", "член": "🥵"}
        for i in top:
            cmn = "🤰🏼"
            if i in m.text.casefold():
                cmn = " Смачно отсосали!💦💦💦🥵🥵🥵" if top[i] == "🥵" else top[i]
                break
        num = random.randint(2, 5) - n
        self.ass.setdefault(str(m.sender_id), [0, m.sender.first_name, "2"])
        self.ass[str(m.sender_id)][0] += num
        await m.respond(
            f"Спасибо! Вы накормили модерку🥞{cmn} \n{num} админа жабабота вам благодарны🎉 \n\n <b>Ваша репутация в тп: -{self.ass[str(m.sender_id)][0]}🤯</b>{txt}"
        )
        go = 0 if len(self.tis[str(m.sender_id)]) == 1 else 1
        if -1 < (time - self.tis[str(m.sender_id)][go]) < 3:
            self.tis[str(m.sender_id)].append(time)
        else:
            self.tis[str(m.sender_id)] = [time]
        self.db.set("Su", "ti", self.tis)
        self.db.set("Su", "as", self.ass)
