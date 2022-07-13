import datetime
import random

from telethon.tl.types import Message

from .. import loader, utils


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
        if m.text.casefold() == "топ":
            top = "Топ багоюзеров:"
            for i in enumerate(
                sorted(self.ass.items(), key=lambda x: x[1], reverse=True), 1
            ):
                a = "🩲" if i[0] == 1 else i[1][1][0]
                top += f"\n{i[0]} | {i[1][1][1]} <code>{a}</code>"
            return await m.respond(top)
        if (
            not m.text.casefold().startswith("закидать ")
            or ("модер" not in m.text.casefold() and "админ" not in m.text.casefold())
            or m.text.count(" ") == 1
        ):
            return
        ct = datetime.datetime.now()
        time = ct.day + ct.minute + ct.second
        num = random.randint(2, 5)
        if "minute" in self.tis and -1 < (time - self.tis["minute"]) < 3:
            a = (
                "когда это все уже закончится👘",
                "надень штаны лох👖",
                "Люблю к-поп и меня не остановить👨🏻‍🚒",
                "스트레이 키즈의 세계 지배.",
                "Я НЕ БУДУ РАБОТАТЬ В ВАШЕМ ЧАТЕ, Я РАБОТАЮ ТОЛЬКО В ОФИЦИАЛЬНОМ ЧАТЕ ЖАБАБОТА",
                "🐈❤️",
                "не отвечаю в лс🧑🏻‍🔬",
                "Не хочу расставаться с тобой💗",
                "вчера было так хорошо,что хотелось даже сдохнуть😺",
                "🖤~Это безусловно пандемия~🖤",
                "Людям тежело без друзей но порой мы задумываюсь что одному лучше👨🏻",
                "Inwardly?🤫",
                "Дайте нормально полениться😘",
                "Technoblade жаль что ты умер от рака, надеюсь у тебя всё хорошо👻",
                "Скучаю👀",
                "Я часто вижу Страх в смотрящих на меня Глазах👙",
            )
            return await m.respond(random.choice(a))
        top = {"дерь": "💩", "говн": "💩", "письк": "💩", "ху": "🥵", "член": "🥵"}
        for i in top:
            cmn = "🤰🏼"
            if i in m.text.casefold():
                cmn = " Смачно отсосали!💦💦💦🥵🥵🥵" if top[i] == "🥵" else top[i]
                break
        self.ass.setdefault(str(m.sender_id), [0, m.sender.first_name])
        self.ass[str(m.sender_id)][0] += num
        await m.respond(
            f"Спасибо! Вы накормили модерку🥞{cmn} \n{num} админа жабабота вам благодарны🎉 \n\n <b>Ваша репутация в тп: -{self.ass[str(m.sender_id)][0]}🤯</b>"
        )
        self.tis.setdefault("minute", time)
        self.tis["minute"] = time
        self.db.set("Su", "ti", self.tis)
        self.db.set("Su", "as", self.ass)
