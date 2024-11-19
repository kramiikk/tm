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

    ANIMATION_TEMPLATE = """\n            await client.hikka_inline.bot.send_animation(
                logging.getLogger().handlers[0].get_logid_by_client(client.tg_id),
                "{url}",
                caption=(
                {caption}
                )
            )\n            """

    def _create_animation_block(self, url, caption_text):
        """Создает блок анимации с форматированным текстом."""
        return self.ANIMATION_TEMPLATE.format(url=url, caption=caption_text)

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
                r"(\s*await\s+client\.hikka_inline\.bot\.send_animation\(\n"
                r"\s*.*?,\n"
                r"\s*(?:\"|\')([^'\"]+)(?:\"|\'),\n"
                r"\s*caption=\(\n"
                r"\s*(.*?)\n"
                r"\s*\)\n"
                r"\s*\)(?:\s*,\s*\)\s*)?)"
            )

            animation_block_match = re.search(
                animation_block_pattern, content, re.DOTALL
            )

            if not animation_block_match:
                raise ValueError("Не удалось найти блок отправки анимации в main.py")
            full_block = animation_block_match.group(1)
            current_url = animation_block_match.group(2)

            if self._is_valid_url(args):
                new_block = self._create_animation_block(
                    url=args, caption_text=animation_block_match.group(3).strip()
                )
            else:
                new_block = self._create_animation_block(
                    url=current_url,
                    caption_text=f"{args}",
                )
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
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc]) and (
                url.lower().endswith(".mp4") or url.lower().endswith(".gif")
            )
        except:
            return False
