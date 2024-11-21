# meta developers: @amm1e & @AmeMods, @me_rne


from .. import loader, utils
import os
import re
import urllib.parse


@loader.tds
class AmeChangeLoaderText(loader.Module):
    """Модуль для изменения текста и баннера загрузки Хикка в hikka-logs."""

    strings = {"name": "AmeChangeLoaderText"}

    async def updlcmd(self, message):
        """
        Для баннера используйте ссылки на файлы с форматом mp4 и gif.
        Они должны быть загружены на сайт, чтобы добавить командой!

        • .updl https://x0.at/pYQV.mp4 - заменит баннер

        • .updl Hello, World! - заменит текст
        """
        cmd = utils.get_args_raw(message).replace('"', '\\"')

        if not cmd:
            await message.edit("Вводить так: .updl ваш текст")
            return
        try:
            main_file_path = os.path.join("hikka", "main.py")

            with open(main_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            pattern = r'(await\s+client\.hikka_inline\.bot\.send_animation\(\s*logging\.getLogger\(\)\.handlers\[0\]\.get_logid_by_client\(client\.tg_id\),\s*)"([^"]+)",(.*?caption=\()(.*?)(\),\s*\))\s*(\s*)\n(\s*)logging\.debug\('

            def replace_handler(match):
                (
                    prefix,
                    current_url,
                    caption_start,
                    current_caption_content,
                    caption_end,
                    prev_line_indent,
                    logging_indent,
                ) = match.groups()

                if self._is_valid_url(cmd):
                    return (
                        f'{prefix}"{cmd}",{caption_start}{current_caption_content}{caption_end}\n'
                        f"{prev_line_indent}{logging_indent}logging.debug("
                    )
                else:
                    return (
                        f'{prefix}"{current_url}",{caption_start}f"{cmd}"{caption_end}\n'
                        f"{prev_line_indent}{logging_indent}logging.debug("
                    )

            new_content = re.sub(pattern, replace_handler, content, flags=re.DOTALL)

            try:
                with open(main_file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                await message.edit(
                    f"✅ Обновлено на: <code>{cmd}</code>\nНапишите <code>.restart -f</code>, результат будет в hikka-logs"
                )
            except OSError as e:
                await message.edit(f"❌ Ошибка записи в файл: {e}")
        except Exception as e:
            await message.edit(f"❌ Ошибка: <code>{e}</code>")

    def _is_valid_url(self, url):
        """Проверкк URL."""
        try:
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc]) and (
                url.lower().endswith(".mp4") or url.lower().endswith(".gif")
            )
        except Exception:
            return False
