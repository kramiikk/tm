from .. import loader
import os
import re
import urllib.parse


@loader.tds
class AmeChangeLoaderText(loader.Module):
    """Модуль для изменения текста и баннера загрузчика.1"""

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

            # Более гибкий паттерн
            animation_pattern = (
                r'(await\s+client\.hikka_inline\.bot\.send_animation\s*\('
                r'[^,]+,'  # первый аргумент (логгер)
                r'\s*(?P<url>"[^"]+")\s*,'  # URL в кавычках
                r'\s*caption\s*=\s*\([^)]+\)'  # весь блок caption
                r'\s*\))'  # закрывающая скобка
            )

            match = re.search(animation_pattern, content, re.DOTALL)
            if not match:
                raise ValueError("Не удалось найти блок отправки анимации в main.py")

            full_block = match.group(1)
            indent = re.match(r'^\s*', full_block).group(0)
            
            if self._is_valid_url(args):
                # Заменяем только URL
                new_block = content[match.start():match.end()].replace(
                    match.group('url'),
                    f'"{args}"'
                )
            else:
                # Создаем новый простой блок с текстом
                new_block = (
                    f"{indent}await client.hikka_inline.bot.send_animation(\n"
                    f"{indent}    logging.getLogger().handlers[0].get_logid_by_client(client.tg_id),\n"
                    f"{indent}    {match.group('url')},\n"
                    f"{indent}    caption=(\n"
                    f"{indent}        \"{args}\"\n"
                    f"{indent}    ),\n"
                    f"{indent})"
                )

            updated_content = content.replace(full_block, new_block)

            try:
                with open(main_file_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)
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
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc]) and (
                url.lower().endswith(".mp4") or url.lower().endswith(".gif")
            )
        except:
            return False
