from .. import loader
import os
import re
import urllib.parse


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

            # Обновленный паттерн поиска блока анимации
            animation_pattern = (
                r'await\s+client\.hikka_inline\.bot\.send_animation\s*\(\s*'
                r'logging\.getLogger\(\)\.handlers\[0\]\.get_logid_by_client\(client\.tg_id\),\s*'
                r'(?P<url>"[^"]+"),\s*'
                r'caption=\s*\(\s*'
                r'(?P<caption>"[^"]+")\s*'
                r'\)'
            )

            match = re.search(animation_pattern, content, re.DOTALL)
            if not match:
                raise ValueError("Не удалось найти блок отправки анимации в main.py")

            url = match.group('url').strip('"')  # Убираем кавычки из найденного URL
            caption = match.group('caption').strip('"')  # Убираем кавычки из найденного caption
            
            if self._is_valid_url(args):
                # Заменяем URL
                new_url = args
                new_caption = caption
            else:
                # Заменяем текст
                new_url = url
                new_caption = args

            # Формируем новый блок без лишних кавычек
            new_block = (
                f'await client.hikka_inline.bot.send_animation(\n'
                f'    logging.getLogger().handlers[0].get_logid_by_client(client.tg_id),\n'
                f'    "{new_url}",\n'
                f'    caption=(\n'
                f'        "{new_caption}"\n'
                f'    )\n'
                f')'
            )

            # Заменяем весь найденный блок
            updated_content = content.replace(match.group(0), new_block)

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
