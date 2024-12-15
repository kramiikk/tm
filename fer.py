    async def _broadcast_loop(self, code_name: str):
        """Основной цикл рассылки для конкретного кода."""
        while self._active:
            try:
                code = self.config.codes.get(code_name)
                if not code or not code.chats:
                    continue

                interval = random.uniform(
                    code.interval[0] * 58, code.interval[1] * 59
                )

                current_time = time.time()
                last_broadcast = self._last_broadcast_time.get(code_name, 0)

                if current_time - last_broadcast < interval:
                    continue

                await asyncio.sleep(interval)

                messages = [
                    await self._fetch_messages(msg_data)
                    for msg_data in code.messages
                ]
                messages = [m for m in messages if m]

                if not messages:
                    continue

                chats = list(code.chats)
                random.shuffle(chats)

                message_index = self.message_indices.get(code_name, 0)
                messages_to_send = messages[message_index % len(messages)]
                self.message_indices[code_name] = (message_index + 1) % len(
                    messages
                )

                send_mode = getattr(code, "send_mode", "auto")

                failed_chats = set()
                for chat_id in chats:
                    try:
                        await self._send_message(
                            chat_id,
                            messages_to_send,
                            send_mode,
                            code_name,
                            interval,
                        )
                    except Exception as send_error:
                        logger.error(
                            f"Sending error to {chat_id}: {send_error}"
                        )
                        failed_chats.add(chat_id)
                if failed_chats:
                    code.chats -= failed_chats
                    self.save_config()
                self._last_broadcast_time[code_name] = time.time()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Critical error in broadcast loop {code_name}: {e}"
                )

    async def start_broadcasts(self):
        """Запускает все настроенные рассылки."""
        for code_name in self.config.codes:
            if code_name not in self.broadcast_tasks:
                try:
                    self.broadcast_tasks[code_name] = asyncio.create_task(
                        self._broadcast_loop(code_name)
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to start broadcast loop for {code_name}: {e}"
                    )


@loader.tds
class BroadcastMod(loader.Module):
    """Профессиональный модуль массовой рассылки сообщений с расширенным управлением."""

    strings = {
        "name": "Broadcast",
        "code_not_found": "Код рассылки '{}' не найден",
        "success": "Операция выполнена успешно: {}",
        "album_added": "Альбом добавлен в рассылку '{}'",
        "single_added": "Сообщение добавлено в рассылку '{}'",
    }

    def __init__(self):
        """Инициализация модуля."""
        self._manager: Optional[BroadcastManager] = None
        self._wat_mode = False
        self._last_broadcast_check: float = 0
        self._me_id: Optional[int] = None

    async def client_ready(self, client: TelegramClient, db: Any):
        """Вызывается при готовности клиента, инициализирует менеджер рассылок."""
        self._manager = BroadcastManager(client, db)
        self._manager._load_config_from_dict(
            db.get("broadcast", "Broadcast", {})
        )
        self._me_id = client.tg_id

    async def _validate_broadcast_code(
        self, message: Message, code_name: Optional[str] = None
    ) -> Optional[str]:
        """Проверяет и возвращает код рассылки."""
        args = utils.get_args(message)

        if code_name is None:
            if not args:
                await utils.answer(message, "Укажите код рассылки")
                return None
            code_name = args[0]
        if code_name not in self._manager.config.codes:
            await utils.answer(
                message, self.strings["code_not_found"].format(code_name)
            )
            return None
        return code_name

    async def addmsgcmd(self, message: Message):
        """Команда для добавления сообщения в рассылку."""
        reply = await message.get_reply_message()
        if not reply:
            return await utils.answer(
                message, "Ответьте на сообщение командой .addmsg <код>"
            )
        args = utils.get_args(message)
        if len(args) != 1:
            return await utils.answer(message, "Использование: .addmsg <код>")
        code_name = args[0]
        success = await self._manager.add_message(code_name, reply)

        if success:
            await utils.answer(
                message,
                (
                    self.strings["album_added"].format(code_name)
                    if getattr(reply, "grouped_id", None)
                    else self.strings["single_added"].format(code_name)
                ),
            )
        else:
            await utils.answer(message, "Не удалось добавить сообщение")

    async def chatcmd(self, message: Message):
        """Команда для добавления или удаления чата из рассылки."""
        args = utils.get_args(message)
        if len(args) != 2:
            return await utils.answer(
                message, "Использование: .chat <код> <id_чата>"
            )
        try:
            code_name, chat_id = args[0], int(args[1])
        except ValueError:
            return await utils.answer(message, "ID чата должен быть числом")
        code_name = await self._validate_broadcast_code(message, code_name)
        if not code_name:
            return
        try:
            code = self._manager.config.codes[code_name]

            if chat_id in code.chats:
                code.chats.remove(chat_id)
                action = "удален"
            else:
                code.chats.add(chat_id)
                action = "добавлен"
            self._manager.save_config()
            await utils.answer(message, f"Чат {chat_id} {action} в {code_name}")
        except Exception as e:
            await utils.answer(message, f"Ошибка: {str(e)}")

    async def delcodecmd(self, message: Message):
        """Команда для удаления кода рассылки."""
        code_name = await self._validate_broadcast_code(message)
        if not code_name:
            return
        if code_name in self._manager.broadcast_tasks:
            task = self._manager.broadcast_tasks.pop(code_name)
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await self._manager.config.remove_code(code_name)

        self._manager.cached_messages.pop(code_name, None)
        self._manager.message_indices.pop(code_name, None)

        self._manager.save_config()

        await utils.answer(
            message,
            self.strings["success"].format(
                f"Код рассылки '{code_name}' удален"
            ),
        )

    async def delmsgcmd(self, message: Message):
        """Команда для удаления сообщения из рассылки."""
        args = utils.get_args(message)
        code_name = await self._validate_broadcast_code(message)
        if not code_name:
            return
        reply = await message.get_reply_message()

        if len(args) == 1 and reply:
            code = self._manager.config.codes[code_name]
            matching_messages = [
                idx
                for idx, msg in enumerate(code.messages)
                if msg.message_id == reply.id and msg.chat_id == reply.chat_id
            ]

            if matching_messages:
                del code.messages[matching_messages[0]]
                self._manager.save_config()
                await utils.answer(message, "Сообщение удалено")
            else:
                await utils.answer(message, "Сообщение не найдено")
        elif len(args) == 2:
            try:
                index = int(args[1]) - 1
                code = self._manager.config.codes[code_name]

                if 0 <= index < len(code.messages):
                    del code.messages[index]
                    self._manager.save_config()
                    await utils.answer(message, "Сообщение удалено")
                else:
                    await utils.answer(message, "Неверный индекс")
            except ValueError:
                await utils.answer(message, "Индекс должен быть числом")

    async def intervalcmd(self, message: Message):
        """Команда для установки интервала рассылки."""
        args = utils.get_args(message)
        if len(args) != 3:
            return await utils.answer(
                message,
                "Использование: .interval <код> <мин_минут> <макс_минут>",
            )
        code_name, min_str, max_str = args
        code_name = await self._validate_broadcast_code(message, code_name)
        if not code_name:
            return
        try:
            min_minutes, max_minutes = map(int, (min_str, max_str))

            if not (0 < min_minutes < max_minutes <= 1440):
                await utils.answer(message, "Некорректный интервал")
                return
            code = self._manager.config.codes[code_name]
            code.interval = (min_minutes, max_minutes)
            self._manager.save_config()

            await utils.answer(
                message,
                self.strings["success"].format(
                    f"Интервал для '{code_name}' установлен: {min_minutes}-{max_minutes} минут"
                ),
            )
        except ValueError:
            await utils.answer(message, "Интервал должен быть числом")

    async def listcmd(self, message: Message):
        """Команда для получения информации о рассылках."""
        if not self._manager.config.codes:
            return await utils.answer(message, "Нет настроенных кодов рассылки")
        text = [
            "**Рассылка:**",
            f"🔄 Управление чатами: {'Включено' if self._wat_mode else 'Выключено'}\n",
            "**Коды рассылок:**",
        ]

        for code_name, code in self._manager.config.codes.items():
            chat_list = ", ".join(map(str, code.chats)) or "(пусто)"
            min_interval, max_interval = code.interval
            message_count = len(code.messages)
            running = code_name in self._manager.broadcast_tasks

            text.append(
                f"- `{code_name}`:\n"
                f"  💬 Чаты: {chat_list}\n"
                f"  ⏱ Интервал: {min_interval} - {max_interval} минут\n"
                f"  📨 Сообщений: {message_count}\n"
                f"  📊 Статус: {'🟢 Работает' if running else '🔴 Остановлен'}\n"
            )
        await utils.answer(message, "\n".join(text))

    async def listmsgcmd(self, message: Message):
        """Команда для получения списка сообщений в коде рассылки."""
        code_name = await self._validate_broadcast_code(message)
        if not code_name:
            return
        messages = self._manager.config.codes[code_name].messages
        if not messages:
            return await utils.answer(
                message, f"Нет сообщений в коде '{code_name}'"
            )
        text = [f"**Сообщения в '{code_name}':**"]
        for i, msg in enumerate(messages, 1):
            try:
                chat_id = int(str(abs(msg.chat_id))[-10:])

                if msg.grouped_id is not None:
                    message_text = f"{i}. Альбом в чате {msg.chat_id} (Всего изображений: {len(msg.album_ids)})"
                    message_links = [
                        f"t.me/c/{chat_id}/{album_id}"
                        for album_id in msg.album_ids
                    ]
                    message_text += f"\nСсылки: {' , '.join(message_links)}"
                else:
                    message_text = f"{i}. Сообщение в чате {msg.chat_id}\n"
                    message_text += f"Ссылка: t.me/c/{chat_id}/{msg.message_id}"
                text.append(message_text)
            except Exception as e:
                text.append(f"{i}. Ошибка получения информации: {str(e)}")
        await utils.answer(message, "\n\n".join(text))

    async def sendmodecmd(self, message: Message):
        """Команда для установки режима отправки сообщений."""
        args = utils.get_args(message)
        if len(args) != 2 or args[1] not in ["auto", "normal", "forward"]:
            return await utils.answer(
                message,
                "Использование: .sendmode <код> <режим>\n"
                "Режимы: auto (по умолчанию), normal (обычная отправка), forward (форвард)",
            )
        code_name, mode = args
        code_name = await self._validate_broadcast_code(message, code_name)
        if not code_name:
            return
        code = self._manager.config.codes[code_name]
        code.send_mode = mode
        self._manager.save_config()

        await utils.answer(
            message,
            self.strings["success"].format(
                f"Режим отправки для '{code_name}' установлен: {mode}"
            ),
        )

    async def watcmd(self, message: Message):
        """Команда для переключения автоматического управления чатами."""
        self._wat_mode = not self._wat_mode
        await utils.answer(
            message,
            self.strings["success"].format(
                f"Автоматическое управление чатами {'включено' if self._wat_mode else 'выключено'}"
            ),
        )

    async def watcher(self, message: Message):
        """Наблюдатель сообщений для автоматического управления чатами."""
        if not isinstance(message, Message):
            return
        current_time = time.time()
        if current_time - self._last_broadcast_check >= 600:
            self._last_broadcast_check = current_time
            await self._manager.start_broadcasts()
        if (
            self._wat_mode
            and message.sender_id == self._me_id
            and message.text
            and message.text.strip()
        ):
            for code_name in self._manager.config.codes:
                if message.text.strip().endswith(code_name):
                    try:
                        code = self._manager.config.codes[code_name]
                        code.chats.add(message.chat_id)
                        self._manager.save_config()
                        break
                    except Exception as e:
                        logger.error(f"Ошибка автодобавления чата: {e}")
