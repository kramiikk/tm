import random
from asyncio import sleep

from .. import loader, utils


class DelMsgMod(loader.Module):
    strings = {"name": "DelMsg"}

    async def delmsgcmd(self, message):
        msg = [msg async for msg in message.client.iter_messages(message.chat_id, from_user="me")]
        if utils.get_args_raw(message):
            args = int(utils.get_args_raw(message))
        else:
            args = len(msg)
        for i in range(args):
            await msg[i].delete()
            await sleep(0.16)

    async def shifrcmd(self, message):
        text = utils.get_args_raw(message).lower()
        txtnorm = dict(zip(map(ord,
                               "йцукенгшщзхъфывапролджэячсмитьбю. ?!,-:;"),
                           "3ëjmqv9ô§üldйa¿42zэouəà>ý5eö$0¡<61¥g8tъ7"
                           ))
        txt = text.translate(txtnorm)
        await message.edit(txt)
        await sleep(300)
        await message.delete()

    async def deshifrcmd(self, message):
        text = str(await message.get_reply_message()).split("'")
        await message.delete()
        txt = text[1]

        txtnorm = dict(zip(map(ord,
                               "3ëjmqv9ô§üldйa¿42zэouəà>ý5eö$0¡<61¥g8tъ7"),
                           "йцукенгшщзхъфывапролджэячсмитьбю. ?!,-:;7"
                           ))
        txte = txt.translate(txtnorm)
        await message.client.send_message("me", txte)

    async def emojicmd(self, message):
        args = utils.get_args_raw(message)
        c = args.split(" ")
        emoji = ['😀', '😃', '😄', '😁', '😆', '😅', '🤣', '🥰', '😇', '😊', '😉', '🙃', '🙂', '😂', '😍', '🤩', '😘', '😗', '☺', '😚', '😙', '🤗', '🤑', '😝', '🤪', '😜', '😛', '😋', '🤭', '🤫', '🤔', '🤐', '🤨', '😐', '😑', '😌', '🤥', '😬', '🙄', '😒', '😏', '😶', '😔', '😪', '🤤',
                 '😴', '😷', '🤒', '🤕', '🤢', '🤯', '🤮', '🤠', '🤧', '🥳', '🥵', '😎', '🥶', '🤓', '🥴', '🧐', '😵', '😕', '😳', '😢', '😲', '😥', '😯', '😰', '😮', '😨', '😧', '🙁', '😦', '😟', '🥺', '😭', '😫', '😱', '🥱', '😖', '😤', '😣', '😡', '😞', '😠', '😓', '🤬', '😩', '😈', '👿']
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

    async def shipcmd(self, message):
        user1 = random.choice([i for i in await message.client.get_participants(message.to_id)])
        user2 = random.choice([i for i in await message.client.get_participants(message.to_id)])
        rand1 = message.edit(
            f"<a href=tg://user?id={user1.id}>{user1.first_name}</a> и <a href=tg://user?id={user2.id}>{user2.first_name}</a> любите друг друга!\nМур-Мур😻")
        rand2 = message.edit(
            f"<a href=tg://user?id={user1.id}>{user1.first_name}</a> и <a href=tg://user?id={user2.id}>{user2.first_name}</a> любовная парочка!\nЧмок😘")
        rand3 = message.edit(
            f"Пара дня❤️:\n<a href=tg://user?id={user1.id}>{user1.first_name}</a> и <a href=tg://user?id={user2.id}>{user2.first_name}</a>")
        rand4 = message.edit(
            f"<a href=tg://user?id={user1.id}>{user1.first_name}</a> любит <a href=tg://user?id={user2.id}>{user2.first_name}</a> 😘")
        rand5 = message.edit(
            f"<a href=tg://user?id={user1.id}>{user1.first_name}</a> пригласил на чай <a href=tg://user?id={user2.id}>{user2.first_name}</a> ☕❤️")
        rand6 = message.edit(
            f"<a href=tg://user?id={user1.id}>{user1.first_name}</a> зашел к <a href=tg://user?id={user2.id}>{user2.first_name}</a>\n😏🔥")
        rand = [rand1, rand2, rand3, rand4, rand5, rand6]
        randchoice = random.choice(rand)
        await randchoice

    async def puntooncmd(self, message):
        """.puntoon включает модуль PuntoSw."""
        self.truefalse = True
        await message.edit("<b>PuntoSw On.</b>")

    async def puntooffcmd(self, message):
        """.puntooff выключает модуль PuntoSw."""
        self.truefalse = False
        await message.edit("<b>Punto Off.</b>")

    async def watcher(self, message):
        await sleep(0.1)
        if self.truefalse == True:
            me = (await message.client.get_me())
            if message.sender_id == me.id:
                text = message.text.lower()
                txtnorm = dict(zip(map(ord,
                                       "qwertyuiop[]asdfghjkl;'zxcvbnm/"
                                       'QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>'),
                                   "йцукенгшщзхъфывапролджэячсмитьбю"
                                   'ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ'
                                   ))
                await message.delete()
                txt = list(text.translate(txtnorm))
                txt1 = txt[0].upper()
                txt2 = txt1 + "".join(txt[1:])
                await message.respond(txt2)

    async def dcmd(self, message):
        """Пример: .d 5s Привет, как дела?\ns - секунды; m - минуты; h - часы."""
        args = utils.get_args_raw(message)
        text = args.split(" ")
        txt = text[1:]
        txtjoin = " ".join(txt)
        numbs = text[0]
        timeq = list(numbs)
        lentime = len(timeq)
        secormin = timeq[lentime - 1]
        timeq.pop(lentime - 1)
        nm = int("".join(timeq))
        if secormin == "s":
            timesmh = nm
        elif secormin == "m":
            timesmh = nm * 60
        elif secormin == "h":
            timesmh = nm * 60 * 60
        else:
            await message.reply("<b>Время указано неверно!\nМожно использовать только: s - секунды, m - минуты, h - часы.</b>")
        await message.edit(txtjoin)
        await sleep(timesmh)
        await message.delete()

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

    async def rpscmd(self, message):
        """Для запуска пишите .rps (камень/ножницы/бумага)"""
        rps = ["камень", "ножницы", "бумага, камень", "ножницы", "бумага, камень", "ножницы",
               "бумага, камень", "ножницы", "бумага, камень", "ножницы", "бумага, камень", "ножницы", "бумага"]
        args = utils.get_args_raw(message)
        rand = random.choice(rps)
        if rand == args:
            await message.edit("<b>Ничья, твой соперник выбрал тоже самое, что и ты!</b>")
        elif rand == "камень" and args == "бумага":
            await message.edit("<b>Поздравляю, ты победил!</b>")
        elif rand == "бумага" and args == "ножницы":
            await message.edit("<b>Поздравляю, ты победил!</b>")
        elif rand == "ножницы" and args == "камень":
            await message.edit("<b>Поздравляю, ты победил!</b>")
        else:
            await message.edit("<b>К сожалению, ты проиграл(</b>")
        await message.respond("Ты выбрал — " + args + ", \nа твой соперник — " + rand + ".")

    def __init__(self):
        self.farm = True
        self.virys = True

    async def farmcmd(self, message):
        """Включает команду "Ферма". Чтобы остановить, используйте "ирисфарм стоп"."""
        while self.farm:
            await message.reply("Ферма\n\n<b>Следующая команда будет произведена через 4 часа.\n\nIrisBot by @CREATIVE_tg1</b>")
            await sleep(14500)

    async def virysncmd(self, message):
        """Включает команду "Заразить =" (Заражает равного по силе соперника). Чтобы остановить, используйте "ирисвирус стоп"."""
        while self.virys:
            await message.reply("Заразить =\n\n<b>Следующая команда будет произведена через 1 час.\n\nIrisBot by @CREATIVE_tg1</b>")
            await sleep(3600)

    async def virysecmd(self, message):
        """Включает команду "Заразить -" (Заражает слабого соперника). Чтобы остановить, используйте "ирисвирус стоп"."""
        while self.virys:
            await message.reply("Заразить -\n\n<b>Следующая команда будет произведена через 1 час.\n\nIrisBot by @CREATIVE_tg1</b>")
            await sleep(3600)

    async def viryshcmd(self, message):
        """Включает команду "Заразить +" (Заражает сильного соперника) . Чтобы остановить, используйте "ирисвирус стоп"."""
        while self.virys:
            await message.reply("Заразить +\n\n<b>Следующая команда будет произведена через 1 час.\n\nIrisBot by @CREATIVE_tg1</b>")
            await sleep(3600)

    async def watcher(self, message):
        me = (await message.client.get_me())
        if message.sender_id == me.id:
            if message.text.lower() == "ирисфарм стоп":
                self.farm = False
                await message.reply("<b>Ирисфарм остановлен.</b>")
            if message.text.lower() == "ирисвирус стоп":
                self.virys = False
                await message.reply("<b>Ирисвирус остановлен.</b>")
