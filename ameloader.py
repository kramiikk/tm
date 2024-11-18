from .. import loader
import os
import re
import urllib.parse


@loader.tds
class AmeChangeLoaderText(loader.Module):
    """Модуль для изменения текста и баннера загрузчика."""

    strings = {"name": "AmeChangeLoaderText"}

    def is_valid_url(self, url):
        """Проверка, является ли строка валидным URL"""
        try:
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    async def updateloadercmd(self, message):
        """
        .updateloader reset hikari - вернуть дефолтные настройки Hikka
        .updateloader reset coddrago - вернуть дефолтные настройки CodDrago
        .updateloader https://example.com/banner.mp4 - заменить баннер
        .updateloader текст - заменить текст
        """

        args = message.raw_text.split(" ", 3)

        if len(args) == 1:
            help_text = (
                "<b>📋 Справка по AmeChangeLoaderText:</b>\n\n"
                "• <code>.updateloader reset hikari</code> - Сброс к настройкам Hikka\n"
                "• <code>.updateloader reset coddrago</code> - Сброс к настройкам CodDrago\n"
                "• <code>.updateloader https://site.com/banner.mp4</code> - Заменить баннер\n"
                "• <code>.updateloader текст</code> - Заменить текст\n\n"
            )
            await message.edit(help_text)
            return
        reset = len(args) >= 3 and args[1] == "reset"
        reset_type = args[2] if reset else None

        try:
            main_file_path = os.path.join("hikka", "main.py")

            with open(main_file_path, "r", encoding="utf-8") as file:
                content = file.read()
            if reset:
                if reset_type == "hikari":
                    url = "https://github.com/hikariatama/assets/raw/master/hikka_banner.mp4"
                    repo_link = "https://github.com/hikariatama/Hikka"
                elif reset_type == "coddrago":
                    url = "https://x0.at/pYQV.mp4"
                    repo_link = "https://github.com/coddrago/Hikka"
                else:
                    await message.edit(
                        "❌ <b>Неверный тип сброса. Используйте hikari или coddrago</b>"
                    )
                    return
                caption = (
                    'caption=(\n                    "🌘 <b>Hikka {} started!</b>\n\n🌳 <b>GitHub commit SHA: <a"'
                    f' href="{repo_link}/commit/{{}}">{{}}</a></b>\n✊'
                    ' <b>Update status: {}</b>\n<b>{}</b>".format(\n'
                    '                        ".".join(list(map(str, list(version)))),\n'
                    "                        build,\n"
                    "                        build[:7],\n"
                    "                        upd,\n"
                    "                        web_url,\n"
                    "                    )\n                ),"
                )

                content = re.sub(
                    r"([\'\"]\s*https://)[^\'\"]+([\'\"])",
                    f"\\1{url}\\2",
                    content,
                )
                content = re.sub(r"caption=\([\s\S]*?\),", caption, content)

                result_message = (
                    f"✅ <b>Восстановлены дефолтные настройки {reset_type}</b>"
                )
            else:
                default_url = (
                    "https://github.com/hikariatama/assets/raw/master/hikka_banner.mp4"
                )
                if self.is_valid_url(args[1]):
                    url = args[1]
                    content = re.sub(
                        r"([\'\"]\s*https://)[^\'\"]+([\'\"])",
                        f"\\1{url}\\2",
                        content,
                    )
                    result_message = f"✅ <b>Баннер обновлен на:</b> <code>{url}</code>"
                else:
                    url = default_url
                    custom_text = args[1]
                    new_caption = (
                        'caption=(\n                    "{0}"\n                ),'
                    ).format(custom_text)
                    content = re.sub(r"caption=\([\s\S]*?\),", new_caption, content)
                    result_message = (
                        f"✅ <b>Текст обновлен на:</b> <code>{custom_text}</code>"
                    )
            with open(main_file_path, "w", encoding="utf-8") as file:
                file.write(content)
            result_message += "\n<b>Напишите</b> <code>.restart -f</code>"
            await message.edit(result_message)
        except Exception as e:
            await message.edit(f"❌ <b>Ошибка:</b> <code>{e}</code>")
