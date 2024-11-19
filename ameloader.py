from .. import loader
import os
import re
import urllib.parse
import logging

@loader.tds
class AmeChangeLoaderText(loader.Module):
    """Модуль для изменения текста и баннера загрузчика.014"""

    strings = {"name": "AmeChangeLoaderText"}

    PLACEHOLDERS = {
        "version": "'.'.join(map(str, __version__))",
        "build": "build",
        "build_hash": "build[:7]",
        "upd": "upd",
        "web_url": "web_url",
    }

    async def updateloadercmd(self, message):
        """
        Команда для обновления текста или баннера загрузчика.
        """
        cmd = message.raw_text.split(maxsplit=1)
        if len(cmd) == 1:
            await message.edit(
                "<b>📋 Справка по AmeChangeLoaderText:</b>\n\n"
                "• <code>.updateloader https://site.com/banner.mp4</code> - Заменить баннер\n"
                "• <code>.updateloader текст</code> - Заменить текст\n"
                "• <code>.updateloader текст с placeholder</code> - Заменить текст с переменными:\n"
                "   {version} - версия\n"
                "   {build} - полный билд\n"
                "   {build_hash} - короткий хеш билда\n"
                "   {upd} - статус обновления\n"
                "   {web_url} - веб-URL\n\n"
                "Примеры:\n"
                "<code>.updateloader Апдейт {upd} | Версия {version}</code>\n"
                "<code>.updateloader Билд {build_hash} Статус {upd} Веб {web_url}</code>\n\n"
            )
            return

        try:
            args = cmd[1].strip()
            main_file_path = os.path.join("hikka", "main.py")

            # Чтение файла main.py
            with open(main_file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Поиск блока анимации
            animation_block_pattern = (
                r"([ \t]*)await\s+client\.hikka_inline\.bot\.send_animation\n"
                r"(?:[ \t]*.+,\n)*"
                r"[ \t]*caption=(?:[^)]+),?\n"
                r"[ \t]*"
            )
            animation_block_match = re.search(animation_block_pattern, content)
            if not animation_block_match:
                raise ValueError("Не удалось найти блок отправки анимации в main.py")

            full_block = animation_block_match.group(0)

            # Определение текущего URL
            current_url = re.search(r'"(https://[^"]+\.mp4)"', full_block).group(1)

            # Замена блока
            if self._is_valid_url(args):
                new_block = full_block.replace(current_url, args)
                result_message = f"✅ Баннер обновлен на: <code>{args}</code>"
            else:
                user_text = args.replace('"', '\\"')
                new_block = full_block.replace(
                    re.search(r'caption=(.*?)', full_block).group(1),
                    f'"{user_text}"',
                )
                result_message = f"✅ Текст обновлен на: <code>{user_text}</code>"

            content = content.replace(full_block, new_block)

            # Сохранение файла
            with open(main_file_path, "w", encoding="utf-8") as f:
                f.write(content)

            await message.edit(f"{result_message}\nНапишите <code>.restart -f</code>")

        except Exception as e:
            await message.edit(f"❌ Ошибка: <code>{str(e)}</code>")

    def _is_valid_url(self, url):
        """
        Проверяет, является ли URL валидным и оканчивается на .mp4.
        """
        try:
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc]) and url.lower().endswith(".mp4")
        except:
            return False
