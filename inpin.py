from __future__ import annotations

import asyncio
import logging
import re
from typing import Dict, List, Optional, Union

import socket
import time
import threading

import webview
import json

from telethon import TelegramClient
from telethon.tl.types import Chat, Message

from .. import loader, utils

class NetworkAnalyzer:
    @staticmethod
    async def measure_latency(client: TelegramClient, attempts: int = 3) -> Dict[str, float]:
        """Измерение сетевой задержки различными методами"""
        results = {"telethon": -1.0, "rtt": -1.0, "comprehensive": -1.0}
        
        try:
            # Telethon latency
            telethon_times = []
            for _ in range(attempts):
                start = time.time()
                try:
                    await asyncio.wait_for(client.get_me(), timeout=2)
                    telethon_times.append((time.time() - start) * 1000)
                except Exception:
                    pass
            
            if telethon_times:
                results["telethon"] = sum(telethon_times) / len(telethon_times)
            
            # RTT latency
            try:
                start = time.time()
                with socket.create_connection(('8.8.8.8', 53), timeout=2) as sock:
                    results["rtt"] = (time.time() - start) * 1000
            except Exception:
                pass
            
            # Comprehensive latency
            try:
                start = time.time()
                await asyncio.wait_for(client.get_dialogs(limit=1), timeout=2)
                results["comprehensive"] = (time.time() - start) * 1000
            except Exception:
                pass
        
        except Exception as e:
            logging.error(f"Ошибка измерения пинга: {e}")
        
        return results

class ChatAnalyzer:
    @staticmethod
    async def analyze_chat(
        client: TelegramClient, 
        chat: Union[Chat, int], 
        message_limit: int = 5000, 
        pattern: Optional[str] = None
    ) -> Dict[str, Union[str, int, List[Dict]]]:
        """Комплексный анализ чата"""
        try:
            # Параллельная загрузка участников и сообщений
            participants, messages = await asyncio.gather(
                client.get_participants(chat, limit=message_limit),
                client.get_messages(chat, limit=message_limit)
            )
            
            # Фильтрация сообщений
            def is_meaningful_message(msg: Message) -> bool:
                return (
                    hasattr(msg, 'text') and 
                    msg.text and 
                    msg.text.strip() and 
                    not getattr(msg, 'service', False)
                )
            
            meaningful_messages = list(filter(is_meaningful_message, messages))
            
            # Фильтрация по регулярному выражению
            if pattern:
                meaningful_messages = [
                    msg for msg in meaningful_messages 
                    if re.search(pattern, msg.text or '', re.IGNORECASE)
                ]
            
            # Подсчет сообщений пользователей
            user_message_count = {}
            for msg in meaningful_messages:
                if msg.sender_id:
                    user_message_count[msg.sender_id] = user_message_count.get(msg.sender_id, 0) + 1
            
            # Определение топ-пользователей
            async def get_user_info(user_id: int) -> Optional[Dict]:
                try:
                    user = await client.get_entity(user_id)
                    return {
                        'name': f"[{user.username or user.first_name or 'Unknown'}](tg://user?id={user_id})",
                        'id': user_id,
                        'messages': user_message_count.get(user_id, 0)
                    }
                except Exception:
                    return None
            
            top_users = await asyncio.gather(*[
                get_user_info(user_id) 
                for user_id in sorted(user_message_count, key=user_message_count.get, reverse=True)[:3]
            ])
            top_users = [user for user in top_users if user is not None]
            
            # Идентификация ботов и активных пользователей
            bot_ids = {p.id for p in participants if getattr(p, 'bot', False)}
            active_user_ids = {
                msg.sender_id for msg in meaningful_messages 
                if msg.sender_id and msg.sender_id not in bot_ids
            }
            
            return {
                'title': getattr(chat, 'title', 'Неизвестно'),
                'chat_id': chat.id if hasattr(chat, 'id') else chat,
                'total_messages': len(meaningful_messages),
                'active_members': len(active_user_ids),
                'bots': len(bot_ids),
                'top_users': top_users,
                'pattern_count': len(meaningful_messages) if pattern else 0,
            }
        
        except Exception as e:
            logging.error(f"Ошибка анализа чата: {e}")
            return {}

class HikkaWebApp:
    def __init__(self, module):
        self.module = module
    
    async def measure_latency(self):
        return await self.module.measure_latency()
    
    async def analyze_chat(self, chat_id):
        return await self.module.analyze_chat(chat_id)

def start_webview(module):
    """Запуск веб-интерфейса с React-компонентом"""
    web_app = HikkaWebApp(module)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hikka Chat Stats</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/react/17.0.2/umd/react.development.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/17.0.2/umd/react-dom.development.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/babel-standalone/6.26.0/babel.min.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; }}
        </style>
    </head>
    <body>
        <div id="root"></div>
        
        <script type="text/babel">
        {module.react_component}
        
        const App = () => {{
            return <ChatStatistics 
                client={{{{ /* mock client data */ }}}} 
                chatId={2396215373} 
            />;
        }};
        
        ReactDOM.render(<App />, document.getElementById('root'));
        </script>
    </body>
    </html>
    """
    
    webview.create_window('Hikka Chat Stats', html=html)
    webview.start()

@loader.tds
class AnalyzerModule(loader.Module):
    """Расширенный анализатор чата с React-компонентом"""
    
    strings = {
        "name": "ChatAnalyzer",
        "error": "❌ <b>Ошибка:</b> {}",
    }

    # React компонент в виде строки
    react_component = """
import React, { useState, useEffect } from 'react';
import { RefreshCcw } from 'lucide-react';

const ChatStatistics = ({ client, chatId }) => {
  const [stats, setStats] = useState({
    ping: null,
    telethonPing: null,
    rttPing: null,
    chatName: null,
    chatId: null,
    totalMessages: null,
    activeMembers: null,
    bots: null,
    topUsers: []
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchChatStats = async () => {
    try {
      setLoading(true);
      
      const pingResults = await window.pywebview.api.measure_latency();
      const chatStats = await window.pywebview.api.analyze_chat(chatId);

      setStats({
        ping: pingResults.comprehensive,
        telethonPing: pingResults.telethon,
        rttPing: pingResults.rtt,
        chatName: chatStats.title,
        chatId: chatStats.chat_id,
        totalMessages: chatStats.total_messages,
        activeMembers: chatStats.active_members,
        bots: chatStats.bots,
        topUsers: chatStats.top_users || []
      });

      setError(null);
    } catch (err) {
      setError("Ошибка получения статистики: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (chatId) {
      fetchChatStats();
    }
  }, [chatId]);

  const handleRefresh = () => {
    fetchChatStats();
  };

  if (loading) return <div>Загрузка...</div>;
  if (error) return <div className="text-red-500">{error}</div>;

  return (
    <div className="p-4 bg-gray-100 rounded-lg shadow-md">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Статистика чата</h2>
        <button 
          onClick={handleRefresh}
          className="p-2 bg-blue-500 text-white rounded-full hover:bg-blue-600 transition"
        >
          <RefreshCcw size={20} />
        </button>
      </div>

      <div className="mb-4">
        <h3 className="font-semibold">🌐 Ping</h3>
        <p>Общий: {stats.ping?.toFixed(2) || 'N/A'} мс</p>
        <p>• Telethon: {stats.telethonPing?.toFixed(2) || 'N/A'} мс</p>
        <p>• RTT: {stats.rttPing?.toFixed(2) || 'N/A'} мс</p>
      </div>

      <div className="mb-4">
        <h3 className="font-semibold">Статистика чата</h3>
        <p>🏷️ Название: {stats.chatName || 'Неизвестно'}</p>
        <p>🆔 ID: {stats.chatId || 'Неизвестен'}</p>
        <p>💬 Сообщений: {stats.totalMessages || 0}</p>
        <p>👥 Активные участники: {stats.activeMembers || 0}</p>
        <p>🤖 Боты: {stats.bots || 0}</p>
      </div>

      <div>
        <h3 className="font-семибольшой">Топ-3 активных пользователей</h3>
        {stats.topUsers.length > 0 ? (
          stats.topUsers.map((user) => (
            <p key={user.id}>
              • <a 
                href={`tg://user?id=${user.id}`} 
                className="text-blue-600 hover:underline"
              >
                {user.name}
              </a>: {user.messages} сообщений
            </p>
          ))
        ) : (
          <p>Нет данных о пользователях</p>
        )}
      </div>
    </div>
  );
};

export default ChatStatistics;
"""

    async def client_ready(self, client, db):
        """Инициализация модуля"""
        self._client = client
        self._network_analyzer = NetworkAnalyzer()
        self._chat_analyzer = ChatAnalyzer()

    @loader.command()
    async def chatstat(self, message):
        """Получение статистики чата"""
        try:
            chat = await message.get_chat()
            
            # Измерение пинга
            ping_results = await self._network_analyzer.measure_latency(self._client)
            
            # Анализ чата
            stats = await self._chat_analyzer.analyze_chat(self._client, chat)
            
            # Форматирование результатов
            top_users_text = "\n".join([
                f"• {user['name']}: {user['messages']} сообщений" 
                for user in stats.get('top_users', [])
            ])
            
            response = (
                f"🌐 Ping: {ping_results['comprehensive']:.2f} мс\n"
                f"• Telethon: {ping_results['telethon']:.2f} мс\n"
                f"• RTT: {ping_results['rtt']:.2f} мс\n\n"
                f"Статистика чата '{stats.get('title', 'Неизвестно')}':\n"
                f"🆔 ID: {stats.get('chat_id', 'Н/Д')}\n"
                f"💬 Сообщений: {stats.get('total_messages', 0)}\n"
                f"👥 Активные участники: {stats.get('active_members', 0)}\n"
                f"🤖 Боты: {stats.get('bots', 0)}\n\n"
                "Топ-3 активных пользователей:\n"
                f"{top_users_text}"
            )
            
            await message.reply(response)
            
        except Exception as e:
            await message.reply(f"❌ Ошибка: {str(e)}")

    @loader.command()
    async def openchatstats(self, message):
        """Открыть статистику чата в веб-интерфейсе"""
        # Запуск в отдельном потоке, чтобы не блокировать основной
        threading.Thread(target=start_webview, args=(self,)).start()
        await message.reply("🌐 Открываю веб-интерфейс статистики...")

    async def measure_latency(self):
        """API-метод для React-компонента"""
        return await self._network_analyzer.measure_latency(self._client)

    async def analyze_chat(self, chat_id):
        """API-метод для React-компонента"""
        return await self._chat_analyzer.analyze_chat(self._client, chat_id)
