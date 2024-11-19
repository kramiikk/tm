from .. import loader
import os
import re
import urllib.parse
import logging


@loader.tds
class AmeChangeLoaderText(loader.Module):
    """Модуль для изменения текста и баннера загрузчика."""

    strings = {"name": "AmeChangeLoaderText"}

    PLACEHOLDERS = {
        "version": "'.'.join(map(str, version))",
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
                r"([ \t]*)await\s+client\.hikka_inline\.bot\.send_animation\(\n"
                r"(?:[ \t]+[^\n]+\n)*"
                r"[ \t]+\)"
            )
            animation_block_match = re.search(animation_block_pattern, content)
            if not animation_block_match:
                raise ValueError("Не удалось найти блок отправки анимации в main.py")
            indent = animation_block_match.group(1)

            # Формирование нового блока с нужными переменными

            new_block = (
                f"{indent}await client.hikka_inline.bot.send_animation(\n"
                f"{indent}    logging.getLogger().handlers[0].get_logid_by_client(client.tg_id),\n"
                f'{indent}    "{args}"'
                if self._is_valid_url(args)
                else (
                    '"https://x0.at/pYQV.mp4",\n' f'{indent}    caption=("{args}"'
                    if not self._is_valid_url(args)
                    else "caption=(\n"
                    f'{indent}    "🌘 <b>Hikka {self.PLACEHOLDERS["version"]} started!</b>\\n\\n"\n'
                    f'{indent}    "🌳 <b>GitHub commit SHA: <a href=\\"https://github.com/coddrago/Hikka/commit/{self.PLACEHOLDERS["build"]}\\">{self.PLACEHOLDERS["build_hash"]}</a></b>\\n"\n'
                    f'{indent}    "✊ <b>Update status: {self.PLACEHOLDERS["upd"]}</b>\\n"\n'
                    f'{indent}    "<b>{self.PLACEHOLDERS["web_url"]}</b>")\n'
                    f"{indent})\n"
                )
            )

            # Замена старого блока на новый

            content = content.replace(animation_block_match.group(0), new_block)

            # Сохранение файла

            with open(main_file_path, "w", encoding="utf-8") as f:
                f.write(content)
            result_message = f"✅ Обновлено на: <code>{args}</code>\nНапишите <code>.restart -f</code>"
            await message.edit(result_message)
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
