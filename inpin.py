import re
import asyncio
import random
import json
import logging
import socket
import time
from typing import Dict, Any, List, Optional, Union

import aiohttp
from telethon import TelegramClient
from telethon.tl.types import Chat, Message
from aiohttp import web

from .. import utils, loader

class NetworkUtils:
    @staticmethod
    async def measure_network_performance(client: TelegramClient) -> Dict[str, float]:
        """Advanced network performance measurement with multi-method latency check"""
        async def _safe_timer(coro, timeout: float = 2.0) -> Optional[float]:
            try:
                start = time.perf_counter()
                await asyncio.wait_for(coro, timeout=timeout)
                return (time.perf_counter() - start) * 1000
            except (asyncio.TimeoutError, Exception):
                return None

        async def _rtt_check():
            async with asyncio.timeout(2):
                async with aiohttp.ClientSession() as session:
                    async with session.get('http://8.8.8.8', timeout=2) as response:
                        await response.text()

        results = {
            "telethon": await _safe_timer(client.get_me()),
            "rtt": await _safe_timer(_rtt_check()),
            "comprehensive": await _safe_timer(client.get_dialogs(limit=1))
        }

        return {k: v if v is not None else -1.0 for k, v in results.items()}

class ChatStatistics:
    @staticmethod
    async def analyze_chat(
        client: TelegramClient,
        chat: Union[Chat, int],
        limit: int = 10000,
        pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """Comprehensive chat analysis with advanced filtering and performance optimizations"""
        try:
            participants, messages = await asyncio.gather(
                client.get_participants(chat, limit=limit),
                client.get_messages(chat, limit=limit)
            )

            meaningful_messages = [
                msg for msg in messages 
                if (msg.text and msg.text.strip() and not getattr(msg, 'service', False))
            ]

            if pattern:
                meaningful_messages = [
                    msg for msg in meaningful_messages 
                    if re.search(pattern, msg.text, re.IGNORECASE)
                ]

            user_stats = {}
            for msg in meaningful_messages:
                sender_id = msg.sender_id
                if sender_id:
                    user_stats[sender_id] = user_stats.get(sender_id, 0) + 1

            async def _get_user_details(user_id: int):
                try:
                    user = await client.get_entity(user_id)
                    return {
                        'name': user.username or user.first_name or 'Unknown',
                        'messages': user_stats.get(user_id, 0),
                        'link': f'tg://user?id={user_id}'
                    }
                except Exception:
                    return None

            top_users = await asyncio.gather(*[
                _get_user_details(uid) 
                for uid in sorted(user_stats, key=user_stats.get, reverse=True)[:5]
            ])
            top_users = [user for user in top_users if user]

            return {
                'title': getattr(chat, 'title', 'Unknown'),
                'chat_id': chat.id if hasattr(chat, 'id') else chat,
                'total_messages': len(meaningful_messages),
                'active_members': len({msg.sender_id for msg in meaningful_messages}),
                'bots': len({p.id for p in participants if getattr(p, 'bot', False)}),
                'top_users': top_users,
                'pattern_matches': len(meaningful_messages) if pattern else 0
            }
        except Exception as e:
            logging.error(f"Chat analysis error: {e}")
            return {}

class WebStatsCreator:
    def __init__(self, stats: Dict[str, Any]):
        self.stats = stats
        self.app = web.Application()
        self.app.router.add_get("/", self.index)
        self.url = None
        self.port = None
        self.runner = None
        self.site = None
        self.ssh_process = None

    async def index(self, request):
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Chat Statistics</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-gray-900 text-white">
    <div class="container mx-auto p-6">
        <h1 class="text-3xl font-bold mb-6 text-center">Chat Statistics</h1>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="bg-gray-800 p-6 rounded-lg">
                <h2 class="text-xl font-semibold mb-4">Basic Information</h2>
                <ul class="space-y-2">
                    <li><strong>Chat Title:</strong> {self.stats.get('title', 'Unknown')}</li>
                    <li><strong>Chat ID:</strong> <code>{self.stats.get('chat_id', 'N/A')}</code></li>
                    <li><strong>Total Messages:</strong> {self.stats.get('total_messages', 0)}</li>
                    <li><strong>Active Members:</strong> {self.stats.get('active_members', 0)}</li>
                    <li><strong>Bots:</strong> {self.stats.get('bots', 0)}</li>
                </ul>
            </div>

            <div class="bg-gray-800 p-6 rounded-lg">
                <h2 class="text-xl font-semibold mb-4">Top Users</h2>
                <canvas id="topUsersChart"></canvas>
            </div>
        </div>
    </div>

    <script>
    document.addEventListener('DOMContentLoaded', () => {{
        const topUsers = {json.dumps([
            user['name'] for user in self.stats.get('top_users', [])
        ])};
        const topUserMessages = {json.dumps([
            user['messages'] for user in self.stats.get('top_users', [])
        ])};

        new Chart(document.getElementById('topUsersChart'), {{
            type: 'bar',
            data: {{
                labels: topUsers,
                datasets: [{{
                    label: 'Messages',
                    data: topUserMessages,
                    backgroundColor: 'rgba(75, 192, 192, 0.6)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Number of Messages'
                        }}
                    }}
                }}
            }}
        }});
    }});
    </script>
</body>
</html>
"""
        return web.Response(text=html_content, content_type="text/html")

    async def start_server(self, port: Optional[int] = None):
        """Запуск локального веб-сервера"""
        self.port = port or random.randint(10000, 60000)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "127.0.0.1", self.port)
        await self.site.start()
        return self.port

    async def open_tunnel(self):
        """Открытие SSH-туннеля"""
        if not self.port:
            raise ValueError("Сервер не запущен. Сначала вызовите start_server().")

        ssh_command = f"ssh -o StrictHostKeyChecking=no -R 80:localhost:{self.port} nokey@localhost.run"
        self.ssh_process = await asyncio.create_subprocess_shell(
            ssh_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        url = await self._extract_tunnel_url(self.ssh_process.stdout)
        self.url = url or f"http://localhost:{self.port}"
        return self.url

    async def _extract_tunnel_url(self, stdout):
        """Извлечение URL туннеля из SSH-вывода"""
        url, event = None, asyncio.Event()

        async def read_output():
            nonlocal url
            while True:
                line = await stdout.readline()
                if not line:
                    break
                decoded_line = line.decode()
                match = re.search(r"tunneled.*?(https:\/\/.+)", decoded_line)
                if match:
                    url = match[1]
                    break
            event.set()

        await read_output()
        await event.wait()
        return url

    async def cleanup(self):
        """Очистка всех ресурсов"""
        if self.ssh_process:
            self.ssh_process.terminate()
            await self.ssh_process.wait()
        
        if self.site:
            await self.site.stop()
        
        if self.runner:
            await self.runner.cleanup()

@loader.tds
class AdvancedChatAnalyzer(loader.Module):
    """High-performance Telegram chat analyzer with network diagnostics"""
    
    strings = {
        "name": "AdvancedChatAnalyzer",
        "network_stats": (
            "🌐 <b>Network Performance</b>\n"
            "• Telethon Latency: {telethon:.2f} ms\n"
            "• RTT Latency: {rtt:.2f} ms\n"
            "• Comprehensive Latency: {comprehensive:.2f} ms\n"
        ),
        "chat_stats": (
            "\n<b>📊 Chat Statistics</b>\n"
            "🏷️ Title: {title}\n"
            "🆔 ID: <code>{chat_id}</code>\n"
            "💬 Total Messages: {total_messages}\n"
            "👥 Active Members: {active_members}\n"
            "🤖 Bots: {bots}\n"
            "{pattern_section}"
            "\n<b>🏆 Top Active Users</b>\n"
            "{top_users_section}"
        ),
        "web_link_message": "🌐 <b>Statistics Web Link</b>: {}",
        "web_url": "🌐 <b>Stats URL:</b> {} <b>Expires in</b> <code>{}</code> seconds",
        "expired": "⏰ <b>Web statistics link expired</b>"
    }

    def __init__(self):
        self.network_utils = NetworkUtils()
        self.chat_stats = ChatStatistics()
        self.active_web_servers = {}

    async def pstatcmd(self, message):
        """
        Расширенная статистика чата:
        - Без аргументов: статистика текущего чата
        - [chat_id]: статистика указанного чата
        - r'pattern': фильтрация сообщений по регулярному выражению
        - web: создание веб-ссылки на статистику
        - network: только сетевая статистика
        """
        try:
            args = utils.get_args_raw(message).split()
            chat_id = None
            pattern = None
            generate_web = False
            network_only = False

            # Парсинг аргументов
            for arg in args[:]:
                if arg.startswith("r'") and arg.endswith("'"):
                    pattern = arg[2:-1]
                    args.remove(arg)
                elif arg == "web":
                    generate_web = True
                    args.remove(arg)
                elif arg == "network":
                    network_only = True
                    args.remove(arg)

            chat_id = args[0] if args else None
            chat = await (
                message.client.get_entity(int(chat_id)) if chat_id 
                else message.get_chat()
            )

            # Сетевая производительность
            network_metrics = await self.network_utils.measure_network_performance(message.client)
            
            # Если требуется только сетевая статистика
            if network_only:
                return await message.edit(
                    self.strings["network_stats"].format(**network_metrics)
                )

            # Статистика чата
            stats = await self.chat_stats.analyze_chat(
                message.client, chat, pattern=pattern
            )

            # Секция топ-пользователей
            top_users_section = "\n".join(
                f"• [{user['name']}]({user['link']}): {user['messages']} messages" 
                for user in stats.get('top_users', [])
            ) or "No active users found"

            # Секция совпадений паттерна
            pattern_section = (
                f"🔍 Pattern Matches: {stats.get('pattern_matches', 0)}\n" 
                if pattern else ""
            )

            # Создание веб-ссылки, если указан флаг
            web_link = None
            if generate_web:
                web_stats_creator = WebStatsCreator(stats)
                await web_stats_creator.start_server()
                web_link = await web_stats_creator.open_tunnel()
                
                # Сохраняем ссылку для последующей очистки
                self.active_web_servers[web_link] = web_stats_creator

                # Планируем автоматическую очистку через 5 минут
                asyncio.create_task(self._cleanup_web_server(web_link, 300))

            # Формирование финального сообщения
            final_message = (
                self.strings["network_stats"].format(**network_metrics) +
                self.strings["chat_stats"].format(
                    **stats,
                    pattern_section=pattern_section,
                    top_users_section=top_users_section
                ) +
                (f"\n{self.strings['web_link_message'].format(web_link)}" if web_link else "")
            )

            await message.edit(final_message)

        except Exception as e:
            await message.edit(f"❌ Error: {e}")

    async def _cleanup_web_server(self, web_link: str, timeout: int):
        """Автоматическая очистка веб-сервера"""
        await asyncio.sleep(timeout)
        
        if web_link in self.active_web_servers:
            web_stats_creator = self.active_web_servers.pop(web_link)
            await web_stats_creator.cleanup()
