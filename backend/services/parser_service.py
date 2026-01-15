from typing import List
from backend.services.telegram_service import TelegramService
from backend.database.account_storage import AccountStorage
from backend.database.supabase_client import SupabaseClient
import uuid
from datetime import datetime, timezone

class ParserService:
    def __init__(self, supabase_client: SupabaseClient):
        self.telegram_service = TelegramService()
        self.account_storage = AccountStorage()
        self.supabase_client = supabase_client
        self._is_running = False
        self._should_stop = False
    
    async def parse_all_accounts(self):
        """Парсит сообщения для всех подключенных аккаунтов"""
        print(f"\n>>> Starting parse_all_accounts", flush=True)
        
        self._is_running = True
        self._should_stop = False
        
        # 🆔 Создаём уникальный ID сессии парсинга
        parsing_session_id = str(uuid.uuid4())
        session_start_time = datetime.now(timezone.utc)
        print(f">>> 📊 Parsing Session ID: {parsing_session_id}", flush=True)
        
        try:
            accounts = self.account_storage.get_all_connected_accounts()
            print(f">>> Found {len(accounts)} connected accounts", flush=True)
            
            if not accounts:
                print(">>> WARNING: No connected accounts found!", flush=True)
                return
            
            for account in accounts:
                # Проверяем флаг остановки
                if self._should_stop:
                    print(f">>> PARSING STOPPED BY USER", flush=True)
                    break
                
                print(f">>> Processing account: {account.get('phone_number')}", flush=True)
                try:
                    selected_chats = self.account_storage.get_selected_chats(account["id"])
                    print(f">>> Selected chats for account {account['id']}: {selected_chats}", flush=True)
                    
                    if not selected_chats:
                        print(f">>> WARNING: No selected chats for account {account['id']}", flush=True)
                        continue
                    
                    print(f">>> Parsing messages from {len(selected_chats)} chats...", flush=True)
                    
                    # 📊 Парсим сообщения (теперь возвращает Dict с messages и stats)
                    result = await self.telegram_service.parse_messages(
                        account["api_id"],
                        account["api_hash"],
                        account["phone_number"],
                        selected_chats,
                        hours_back=1
                    )
                    
                    messages = result.get("messages", [])
                    stats = result.get("stats", [])
                    
                    print(f">>> Found {len(messages)} messages from {len(stats)} chats", flush=True)
                    
                    # Проверяем флаг остановки перед сохранением
                    if self._should_stop:
                        print(f">>> PARSING STOPPED BY USER (before saving)", flush=True)
                        break
                    
                    # 💾 Сохраняем сообщения
                    if messages:
                        # Преобразуем datetime строки в формат для Supabase
                        formatted_messages = []
                        for msg in messages:
                            formatted_messages.append({
                                "message_time": msg["message_time"],
                                "chat_name": msg["chat_name"],
                                "user_id": msg.get("user_id"),
                                "first_name": msg["first_name"],
                                "last_name": msg["last_name"],
                                "username": msg["username"],
                                "bio": msg["bio"],
                                "profile_link": msg.get("profile_link"),
                                "message": msg["message"]
                            })
                        
                        self.supabase_client.insert_messages_batch(formatted_messages)
                        print(f"✅ Saved {len(messages)} messages for account {account['phone_number']}")
                    
                    # 📊 Сохраняем статистику парсинга
                    if stats:
                        formatted_logs = []
                        for stat in stats:
                            formatted_logs.append({
                                "parsing_session_id": parsing_session_id,
                                "started_at": stat["started_at"].isoformat() if stat.get("started_at") else session_start_time.isoformat(),
                                "finished_at": stat["finished_at"].isoformat() if stat.get("finished_at") else None,
                                "phone_number": account["phone_number"],
                                "chat_id": stat["chat_id"],
                                "chat_name": stat["chat_name"],
                                "messages_found": stat["messages_found"],
                                "messages_saved": stat["messages_saved"],
                                "messages_skipped": stat["messages_skipped"],
                                "status": stat["status"],
                                "error_type": stat.get("error_type"),
                                "error_message": stat.get("error_message"),
                                "hours_back": 1,
                                "execution_time_seconds": stat.get("execution_time_seconds", 0)
                            })
                        
                        self.supabase_client.insert_parsing_logs_batch(formatted_logs)
                        print(f"📊 Saved statistics for {len(stats)} chats")
                
                except Exception as e:
                    print(f"Error parsing account {account.get('phone_number', 'unknown')}: {e}")
                    continue
        finally:
            self._is_running = False
            self._should_stop = False
    
    def stop_parsing(self):
        """Останавливает текущий парсинг"""
        if self._is_running:
            print(">>> STOP SIGNAL RECEIVED", flush=True)
            self._should_stop = True
            return True
        return False
    
    def is_running(self):
        """Возвращает статус парсера"""
        return self._is_running

