from .. import loader
import os
import re
import urllib.parse
import logging


@loader.tds
class AmeChangeLoaderText(loader.Module):
    """Модуль для изменения текста и баннера загрузчика."""

    strings = {"name": "AmeChangeLoaderText"}

    strings_ru = {
        "help": "<b>📋 Справка по AmeChangeLoaderText:</b>\n\n"
        "• <code>.updateloader https://site.com/banner.mp4</code> - Заменить баннер\n"
        "• <code>.updateloader текст</code> - Заменить текст\n"
    }

    async def updateloadercmd(self, message):
        """
        Команда для обновления текста или баннера загрузчика.
        """
        cmd = message.raw_text.split(maxsplit=1)
        if len(cmd) == 1:
            await message.edit(self.strings("help"))
            return
        
        try:
            args = cmd[1].strip()
            main_file_path = os.path.join("hikka", "main.py")

            with open(main_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # More robust regex to handle varied formatting
            animation_block_pattern = (
                r'(\s*self\.omit_log\s*=\s*True\s*\n'
                r'\s*\n'
                r'\s*await\s+client\.hikka_inline\.bot\.send_animation\(\s*\n'
                r'\s*logging\.getLogger\(\)\.handlers\[0\]\.get_logid_by_client\(client\.tg_id\),\s*\n'
                r'\s*([^\n,]+),\s*\n'
                r'\s*caption=\(\s*\n'
                r'\s*([^\)]+)\s*\n'
                r'\s*\).*?\))'
            )

            animation_block_match = re.search(
                animation_block_pattern, content, re.DOTALL | re.MULTILINE
            )

            if not animation_block_match:
                raise ValueError("Не удалось найти блок отправки анимации в main.py")
            
            full_block = animation_block_match.group(1)
            current_url = animation_block_match.group(2).strip()
            current_text = animation_block_match.group(3).strip()

            # Determine what needs to be replaced
            if self._is_valid_url(args):
                new_url = f'"{args}"'
                new_text = f'"{current_text}"'
            else:
                new_url = current_url
                new_text = f'"{args}"'

            # Create new block with consistent formatting
            new_block = (
                "        self.omit_log = True\n\n"
                "        await client.hikka_inline.bot.send_animation(\n"
                "            logging.getLogger().handlers[0].get_logid_by_client(client.tg_id),\n"
                f"            {new_url},\n"
                "            caption=(\n"
                f"            {new_text}\n"
                "            )\n"
                "        )"
            )

            # Replace the old block with the new one
            content = content.replace(full_block, new_block)

            try:
                with open(main_file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                    await message.edit(
                        f"✅ Обновлено на: <code>{args}</code>\nНапишите <code>.restart -f</code>"
                    )
            except OSError as e:
                await message.edit(f"❌ Ошибка записи в файл: {e}")
        except Exception as e:
            await message.edit(f"❌ Ошибка: <code>{str(e)}</code>")

    def _is_valid_url(self, url):
        """Проверяет URL."""
        try:
            result = urllib.parse.urlparse(url.strip('"\''))
            return all([result.scheme, result.netloc]) and (
                url.lower().strip('"\'').endswith(".mp4") or url.lower().strip('"\'').endswith(".gif")
            )
        except:
            return False
