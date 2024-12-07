from __future__ import annotations

import asyncio
import logging
import re
from typing import Union, Dict, List

from telethon import TelegramClient
from telethon.tl.types import Chat

from .. import loader, utils


class ProfessionalChatAnalyzer:
    def __init__(self, client: TelegramClient):
        self._client = client
        self._logger = logging.getLogger(self.__class__.__name__)

    async def measure_network_latency(
        self, attempts: int = 3, timeout: float = 3.0
    ) -> Dict[str, float]:
        """
        Комплексное измерение сетевой задержки с улучшенным RTT
        """
        results = {"telethon": -1.0, "rtt": -1.0, "comprehensive": -1.0}

        try:
            # Метод 1: Telethon get_me()

            telethon_latencies = []
            for _ in range(attempts):
                start = asyncio.get_event_loop().time()
                try:
                    await asyncio.wait_for(self._client.get_me(), timeout=timeout / 3)
                    latency = (asyncio.get_event_loop().time() - start) * 1000
                    telethon_latencies.append(latency)
                except Exception:
                    pass
            if telethon_latencies:
                results["telethon"] = sum(telethon_latencies) / len(telethon_latencies)
            # Метод 2: Улучшенный RTT с использованием сетевых замеров

            rtt_latencies = []
            try:
                # Попытка использовать прямое измерение через socket

                import socket
                import time

                def measure_rtt(host="8.8.8.8", port=53):
                    try:
                        start = time.time()
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.settimeout(timeout / 3)
                            s.connect((host, port))
                        return (time.time() - start) * 1000
                    except Exception:
                        return -1.0

                # Несколько попыток измерения

                for _ in range(attempts):
                    rtt = measure_rtt()
                    if rtt > 0:
                        rtt_latencies.append(rtt)
                if rtt_latencies:
                    results["rtt"] = sum(rtt_latencies) / len(rtt_latencies)
            except Exception:
                # Резервный метод через Telegram DC

                try:
                    dc_options = self._client.session.dc_options
                    if dc_options:
                        dc = dc_options[0]
                        start = asyncio.get_event_loop().time()
                        await asyncio.wait_for(
                            self._client._connection.connect(
                                dc.ip_address, dc.port, dc.id
                            ),
                            timeout=timeout / 3,
                        )
                        results["rtt"] = (
                            asyncio.get_event_loop().time() - start
                        ) * 1000
                except Exception:
                    pass
            # Метод 3: Комплексное измерение

            comprehensive_latencies = []

            # Замер через получение диалогов

            try:
                start = asyncio.get_event_loop().time()
                await asyncio.wait_for(
                    self._client.get_dialogs(limit=1), timeout=timeout / 3
                )
                comprehensive_latencies.append(
                    (asyncio.get_event_loop().time() - start) * 1000
                )
            except Exception:
                pass
            # Замер через отправку служебного сообщения самому себе

            try:
                start = asyncio.get_event_loop().time()
                me = await self._client.get_me()
                await asyncio.wait_for(
                    self._client.send_message(me.id, "ping"), timeout=timeout / 3
                )
                comprehensive_latencies.append(
                    (asyncio.get_event_loop().time() - start) * 1000
                )
            except Exception:
                pass
            if comprehensive_latencies:
                results["comprehensive"] = sum(comprehensive_latencies) / len(
                    comprehensive_latencies
                )
        except Exception as e:
            self._logger.error(f"Ошибка измерения пинга: {e}")
        return results

    async def analyze_group_comprehensive(
        self, chat: Chat, message_limit: int = 5000, pattern: str = None
    ) -> Dict[str, Union[str, int]]:
        """Комплексный анализ группового чата"""
        try:
            participants, messages = await asyncio.gather(
                self._client.get_participants(chat),
                self._client.get_messages(chat, limit=message_limit),
            )

            # Словарь для подсчета сообщений каждого пользователя

            user_message_count = {}

            meaningful_messages = [
                msg
                for msg in messages
                if hasattr(msg, "text")
                and msg.text.strip()
                and (not hasattr(msg, "service") or not msg.service)
            ]

            # Фильтрация по регулярному выражению, если передано

            if pattern:
                meaningful_messages = [
                    msg
                    for msg in meaningful_messages
                    if re.search(pattern, msg.text or "")
                ]
            for msg in meaningful_messages:
                if msg.sender_id:
                    user_message_count[msg.sender_id] = (
                        user_message_count.get(msg.sender_id, 0) + 1
                    )
            # Определение топ-3 самых активных пользователей

            top_users = []
            for user_id, msg_count in sorted(
                user_message_count.items(), key=lambda x: x[1], reverse=True
            )[:3]:
                try:
                    user = await self._client.get_entity(user_id)
                    username = user.username or user.first_name or "Unknown"
                    user_link = f"[{username}](tg://user?id={user_id})"
                    top_users.append({"name": user_link, "messages": msg_count})
                except Exception:
                    pass
            bots = {p.id for p in participants if getattr(p, "bot", False)}
            active_users = {
                msg.sender_id
                for msg in meaningful_messages
                if msg.sender_id and msg.sender_id not in bots
            }

            return {
                "title": getattr(chat, "title", "Неизвестно"),
                "chat_id": chat.id,
                "total_messages": len(meaningful_messages),
                "active_members": len(active_users),
                "bots": len(bots),
                "top_users": top_users,
                "pattern_count": len(meaningful_messages) if pattern else 0,
            }
        except Exception as e:
            self._logger.error(f"Ошибка анализа чата: {e}")
            return {}


@loader.tds
class AnalDestrModule(loader.Module):
    """Расширенный анализатор чата"""

    strings = {
        "name": "AnalDestroy",
        "error": "❌ <b>Ошибка:</b> {}",
        "ping_template": (
            "🌐 <b>Ping: {comprehensive:.2f} мс</b>\n"
            "• Telethon: {telethon:.2f} мс\n"
            "• RTT: {rtt:.2f} мс\n"
        ),
        "stats_template": (
            "\n<b>Статистика чата:</b>\n"
            "🏷️ Название: {title}\n"
            "🆔 ID: <code>{chat_id}</code>\n"
            "💬 Сообщений: {total_messages}\n"
            "👥 Активные участники: {active_members}\n"
            "🤖 Боты: {bots}\n"
            "{pattern_section}"
            "\n<b>Топ-3 активных пользователей:</b>\n"
            "{top_users_section}"
        ),
        "pattern_section": "🔍 Сообщений с '{pattern}': {pattern_count}\n",
        "top_users_template": "• {name}: {messages} сообщений\n",
    }

    def __init__(self):
        self.analyzer = None
        self._last_context = {"chat": None, "stats": None, "ping": None}

    async def client_ready(self, client, db):
        """Инициализация модуля"""
        self.analyzer = ProfessionalChatAnalyzer(client)

    async def _update_ping(self, call):
        """Обновление пинга с сохранением статистики"""
        try:
            # Измеряем пинг всеми методами

            ping_results = await self.analyzer.measure_network_latency()

            # Формируем текст

            ping_text = self.strings["ping_template"].format(**ping_results)

            # Добавляем статистику, если была

            if self._last_context["stats"]:
                ping_text += self.strings["stats_template"].format(
                    **self._last_context["stats"]
                )
            # Обновляем сообщение

            await call.edit(
                ping_text,
                reply_markup=[
                    [{"text": "🔄 Обновить пинг", "callback": self._update_ping}]
                ],
            )
        except Exception as e:
            await call.answer(f"Ошибка обновления: {str(e)}", show_alert=True)

    @loader.command()
    async def pstat(self, message):
        """Команда получения расширенной статистики чата"""
        try:
            # Разбор аргументов

            args = utils.get_args(message)
            chat_id_arg = args[0] if args else None
            pattern = None

            # Поиск регулярного выражения в аргументах

            for arg in args:
                if arg.startswith("r'") and arg.endswith("'"):
                    pattern = arg[2:-1]
                    args.remove(arg)
                    chat_id_arg = args[0] if args else None
                    break
            if chat_id_arg:
                try:
                    chat = await self._client.get_entity(int(chat_id_arg))
                except (ValueError, TypeError):
                    try:
                        chat = await self._client.get_entity(chat_id_arg)
                    except Exception:
                        await self.inline.form(
                            self.strings["error"].format(
                                "Не удалось найти чат по указанному ID/Username"
                            ),
                            message=message,
                        )
                        return
            else:
                chat = await message.get_chat()
            # Проверяем, что это группа или супергруппа

            from telethon.tl.types import ChatForbidden, ChatFull
            from telethon.tl.types import ChatParticipantsForbidden

            if not (
                isinstance(chat, Chat)
                or getattr(chat, "megagroup", False)
                or (
                    hasattr(chat, "chat_type")
                    and chat.chat_type in ["group", "supergroup"]
                )
            ):
                await self.inline.form(
                    self.strings["error"].format(
                        "Статистика доступна только для групп и супергрупп"
                    ),
                    message=message,
                )
                return
            # Измеряем пинг

            ping_results = await self.analyzer.measure_network_latency()

            # Отправляем первичное сообщение с пингом

            response_message = await self.inline.form(
                self.strings["ping_template"].format(**ping_results),
                message=message,
                reply_markup=[
                    [{"text": "🔄 Обновить пинг", "callback": self._update_ping}]
                ],
            )

            # Асинхронный сбор статистики

            async def update_stats():
                try:
                    # Собираем статистику

                    stats = await self.analyzer.analyze_group_comprehensive(
                        chat, pattern=pattern
                    )

                    # Подготовка секции топ-3 пользователей

                    top_users_section = "• Нет данных"
                    if stats.get("top_users"):
                        top_users_section = "".join(
                            self.strings["top_users_template"].format(**user)
                            for user in stats["top_users"]
                        )
                    # Подготовка секции регулярного выражения

                    pattern_section = ""
                    if pattern:
                        pattern_section = self.strings["pattern_section"].format(
                            pattern=pattern, pattern_count=stats.get("pattern_count", 0)
                        )
                    # Формирование полного текста

                    full_text = self.strings["ping_template"].format(
                        **ping_results
                    ) + self.strings["stats_template"].format(
                        **stats,
                        pattern_section=pattern_section,
                        top_users_section=top_users_section,
                    )

                    # Обновляем сообщение

                    await response_message.edit(
                        full_text,
                        reply_markup=[
                            [
                                {
                                    "text": "🔄 Обновить пинг",
                                    "callback": self._update_ping,
                                }
                            ]
                        ],
                    )
                except Exception as e:
                    logging.error(f"Ошибка обновления статистики: {e}")

            # Запускаем сбор статистики в фоне

            asyncio.create_task(update_stats())
        except Exception as e:
            await self.inline.form(
                self.strings["error"].format(str(e)), message=message
            )
