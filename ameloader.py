from .. import loader, utils
import os
import re
import urllib.parse


@loader.tds
class AmeChangeLoaderText(loader.Module):
    """Модуль для изменения текста и баннера загрузчика."""

    strings = {"name": "AmeChangeLoaderText"}

    strings_ru = {
        "help": "<b>📋 Справка по AmeChangeLoaderText:</b>\n\n"
        "
    }

    async def updateloadercmd(self, message):
        """
        Для баннера подходят только файлы с форматом mp4 и gif.
        Они должны быть загружены на сайт, и добавлены по ссылке.
        • .updateloader https://site.com/banner.mp4</code> - Заменить баннер\n
        • .updateloader текст</code> - Заменить текст\n
        """
        cmd = utils.get_args_raw(message)
        
        if not cmd:
            await message.edit(self.strings("help"))
            return
        
        try:
            main_file_path = os.path.join("hikka", "main.py")

            with open(main_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            pattern = r'(await\s+client\.hikka_inline\.bot\.send_animation\(\s*logging\.getLogger\(\)\.handlers\[0\]\.get_logid_by_client\(client\.tg_id\),\s*)"([^"]+)",(.*?caption=\()(.*?)(\),\s*\))\s*(\s*)\n(\s*)logging\.debug\('

            def replace_handler(match):
                prefix, current_url, caption_start, current_caption_content, caption_end, prev_line_indent, logging_indent = match.groups()
                
                if self._is_valid_url(cmd):
                    return (
                        f'{prefix}"{cmd.replace('"', "\\")}",{caption_start}{current_caption_content}{caption_end}\n'
                        f"{prev_line_indent}{logging_indent}logging.debug("
                    )
                else:
                    return (
                        f'{prefix}"{current_url}",{caption_start}f"{cmd.replace('"', "\\")}"{caption_end}\n'
                        f"{prev_line_indent}{logging_indent}logging.debug("
                    )

            new_content = re.sub(pattern, replace_handler, content, flags=re.DOTALL)

            try:
                with open(main_file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                await message.edit(
                    f"✅ Обновлено на: <code>{cmd}</code>\nНапишите <code>.restart -f</code>"
                )
            except OSError as e:
                await message.edit(f"❌ Ошибка записи в файл: {e}")
        except Exception as e:
            await message.edit(f"❌ Ошибка: <code>{e}</code>")

    def _is_valid_url(self, url):
        """Проверкк URL."""
        try:
            result = urllib.parse.urlparse(url)
            return (
                all([result.scheme, result.netloc]) and 
                (url.lower().endswith(".mp4") or url.lower().endswith(".gif"))
            )
        except Exception:
            return False
