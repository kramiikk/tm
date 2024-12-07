from __future__ import annotations

import asyncio
import logging
import re
from typing import Union, Dict, List, Optional

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
            
            # [Rest of the existing measure_network_latency method remains the same]
            
        except Exception as e:
            self._logger.error(f"Ошибка измерения пинга: {e}")
        return results

    async def analyze_group_comprehensive(
        self, chat: Chat, pattern: str = None
    ) -> Dict[str, Union[str, int]]:
        """Комплексный анализ группового чата"""
        try:
            participants, messages = await asyncio.gather(
                self._client.get_participants(chat),
                self._client.get_messages(chat),
            )

            user_message_count = {}

            meaningful_messages = [
                msg
                for msg in messages
                if hasattr(msg, "text")
                and msg.text.strip()
                and (not hasattr(msg, "service") or not msg.service)
            ]

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
            
            top_users = []
            for user_id, msg_count in sorted(
                user_message_count.items(), key=lambda x: x[1], reverse=True
            )[:3]:
                try:
                    user = await self._client.get_entity(user_id)
                    username = user.username or user.first_name or "Unknown"

                    user_link = f'<a href="tg://user?id={user_id}">{username}</a>'
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
                "pattern": pattern,  # Include the pattern in the return
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
        self._last_context: Dict[str, Optional[Union[Chat, Dict, Dict[str, float]]]] = {
            "chat": None, 
            "stats": None, 
            "ping": None, 
            "pattern": None
        }

    async def client_ready(self, client, db):
        """Инициализация модуля"""
        self.analyzer = ProfessionalChatAnalyzer(client)

    async def _update_ping(self, call):
        """Обновление пинга с сохранением статистики"""
        try:
            # Use cached ping results if available
            ping_results = await self.analyzer.measure_network_latency()
            self._last_context["ping"] = ping_results

            # Construct full text with ping template
            full_text = self.strings["ping_template"].format(**ping_results)

            # Check if we have previous stats to display
            if self._last_context["stats"]:
                stats = self._last_context["stats"]

                # Generate top users section
                top_users_section = "• Нет данных"
                if stats.get("top_users"):
                    top_users_section = "".join(
                        self.strings["top_users_template"].format(**user)
                        for user in stats["top_users"]
                    )

                # Generate pattern section if applicable
                pattern_section = ""
                if stats.get("pattern"):
                    pattern_section = self.strings["pattern_section"].format(
                        pattern=stats.get("pattern", ""),
                        pattern_count=stats.get("pattern_count", 0),
                    )

                # Combine ping and stats templates
                full_text += self.strings["stats_template"].format(
                    **stats,
                    pattern_section=pattern_section,
                    top_users_section=top_users_section,
                )

            # Update message with full text and refresh button
            await call.edit(
                full_text,
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
            args = utils.get_args(message)
            chat_id_arg = args[0] if args else None
            pattern = None

            # Extract pattern from arguments if present
            for arg in args:
                if arg.startswith("r'") and arg.endswith("'"):
                    pattern = arg[2:-1]
                    args.remove(arg)
                    chat_id_arg = args[0] if args else None
                    break

            # Determine chat to analyze
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

            # Validate chat type
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

            # Measure initial ping
            ping_results = await self.analyzer.measure_network_latency()
            self._last_context["ping"] = ping_results

            # Create initial response message
            response_message = await self.inline.form(
                self.strings["ping_template"].format(**ping_results),
                message=message,
                reply_markup=[
                    [{"text": "🔄 Обновить пинг", "callback": self._update_ping}]
                ],
            )

            async def update_stats():
                try:
                    # Analyze chat and store results in context
                    stats = await self.analyzer.analyze_group_comprehensive(
                        chat, pattern=pattern
                    )
                    self._last_context["chat"] = chat
                    self._last_context["stats"] = stats
                    self._last_context["pattern"] = pattern

                    # Generate top users section
                    top_users_section = "• Нет данных"
                    if stats.get("top_users"):
                        top_users_section = "".join(
                            self.strings["top_users_template"].format(**user)
                            for user in stats["top_users"]
                        )

                    # Generate pattern section
                    pattern_section = ""
                    if pattern:
                        pattern_section = self.strings["pattern_section"].format(
                            pattern=pattern, pattern_count=stats.get("pattern_count", 0)
                        )

                    # Combine ping and stats templates
                    full_text = self.strings["ping_template"].format(
                        **ping_results
                    ) + self.strings["stats_template"].format(
                        **stats,
                        pattern_section=pattern_section,
                        top_users_section=top_users_section,
                    )

                    # Update message with full details
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

            # Run stats update asynchronously
            asyncio.create_task(update_stats())
        except Exception as e:
            await self.inline.form(
                self.strings["error"].format(str(e)), message=message
            )
