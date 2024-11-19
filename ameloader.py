from .. import loader
import os
import re
import urllib.parse


@loader.tds
class AmeChangeLoaderText(loader.Module):
    """Модуль для изменения текста и баннера загрузчика. 07"""

    strings = {"name": "AmeChangeLoaderText"}

    PLACEHOLDERS = {
        "version": "'.'.join(map(str, version))",
        "build": "build",
        "build_hash": "build[:7]",
        "upd": "upd",
        "web_url": "web_url",
    }

    def _replace_placeholders(self, text):
        for key, value in self.PLACEHOLDERS.items():
            text = text.replace(f"{{{key}}}", value)
        return text

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
                "Пример:\n"
                "<code>.updateloader Статус {upd} Веб {web_url}</code>\n\n"
            )
            return
        try:
            args = cmd[1].strip()
            main_file_path = os.path.join("hikka", "main.py")

            with open(main_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            animation_block_pattern = (
                r"(\s*await\s+client\.hikka_inline\.bot\.send_animation\(\n"
                r"\s*.*?,\n"
                r"\s*.*?caption=\(\n"
                r"\s*.*?\n"
                r"\s*\),\n"
                r"\s*\))"
            )

            animation_block_match = re.search(
                animation_block_pattern, content, re.DOTALL
            )

            if not animation_block_match:
                raise ValueError("Не удалось найти блок отправки анимации в main.py")
            full_block = animation_block_match.group(1)

            if self._is_valid_url(args):
                new_block = re.sub(r'"https://[^"]+\.mp4"', f'"{args}"', full_block)
            else:
                user_text = self._replace_placeholders(args)
                new_block = re.sub(
                    r"caption=\(\n.*?\),",
                    f'caption=(\n                    "{user_text}"\n                ),',
                    full_block,
                    flags=re.DOTALL,
                )
            content = content.replace(full_block, new_block)

            with open(main_file_path, "w", encoding="utf-8") as f:
                f.write(content)
            await message.edit(
                f"✅ Обновлено на: <code>{args}</code>\nНапишите <code>.restart -f</code>"
            )
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
