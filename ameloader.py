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
            animation_block_pattern = (
                r"(\s*)\)(\s*)"
                r"(\s*self\.omit_log\s*=\s*True\s*)"
                r"(\s*)"
                r"(await\s+client\.hikka_inline\.bot\.send_animation\(\s*)"
                r"(logging\.getLogger\(\)\.handlers\[0\]\.get_logid_by_client\(client\.tg_id\),\s*)"
                r'(".*?"),\s*'
                r"(caption=\(.*?\)),\s*"
                r"(\))"
                r"(\s*)"
                r"(logging\.debug\()"
            )

            def replace_block(match):
                pre_close_paren = match.group(1)
                post_close_paren = match.group(2)
                omit_log_line = match.group(3)
                omit_log_indent = match.group(4)
                send_animation_start = match.group(5)
                log_line = match.group(6)
                current_url = match.group(7)
                current_caption = match.group(8)
                send_animation_end = match.group(9)
                post_animation_space = match.group(10)
                logging_debug = match.group(11)

                if self._is_valid_url(args):
                    new_url = f'"{args}"'
                    new_caption = current_caption
                else:
                    new_url = current_url
                    caption_lines = current_caption.split("\n")
                    if len(caption_lines) > 2:
                        first_line_indent = len(caption_lines[1]) - len(
                            caption_lines[1].lstrip()
                        )
                        new_caption = f'caption=(\n{" " * first_line_indent}"{args}"\n{" " * (first_line_indent - 2)}))'
                    else:
                        new_caption = f'caption=("{args}")'
                return (
                    f"{pre_close_paren}){post_close_paren}"
                    f"{omit_log_line}{omit_log_indent}"
                    f"{send_animation_start}"
                    f"{log_line}"
                    f"{new_url}, "
                    f"{new_caption}, "
                    f"{send_animation_end}"
                    f"{post_animation_space}"
                    f"{logging_debug}"
                )

            new_content = re.sub(
                animation_block_pattern,
                replace_block,
                content,
                flags=re.DOTALL | re.MULTILINE,
            )

            try:
                with open(main_file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
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
            clean_url = url.strip("\"'")
            result = urllib.parse.urlparse(clean_url)
            return all([result.scheme, result.netloc]) and (
                clean_url.lower().endswith(".mp4") or clean_url.lower().endswith(".gif")
            )
        except:
            return False
