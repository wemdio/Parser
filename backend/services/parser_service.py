import asyncio
from typing import List
from backend.services.telegram_service import TelegramService
from backend.database.account_storage import AccountStorage
from backend.database.supabase_client import SupabaseClient
import uuid
from datetime import datetime, timezone

# Hard cap per account scan. Defense-in-depth on top of the per-chat timeout
# in telegram_service.parse_messages — if every single chat hits its 25s
# timeout, 93 chats × 25s ≈ 39 min, so a generous outer cap is needed.
PARSE_ACCOUNT_TIMEOUT_SECONDS = 1800  # 30 minutes

class ParserService:
    def __init__(self, supabase_client: SupabaseClient):
        self.telegram_service = TelegramService()
        self.account_storage = AccountStorage()
        self.supabase_client = supabase_client
        self._is_running = False
        self._should_stop = False
        # Optional realtime service. Wired from main.py after construction
        # so the batch scheduler can recover the realtime listener when
        # accounts appear after the initial RealtimeService.start() call
        # (which silently exits if no accounts are connected yet).
        self._realtime_service = None

    def set_realtime_service(self, realtime_service):
        """Inject the RealtimeService so parse_all_accounts can revive it
        if accounts appeared after startup."""
        self._realtime_service = realtime_service
    
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

            # If realtime wasn't able to start at boot (no accounts at the time)
            # but accounts exist now, try to bring it up so we don't depend on
            # the slow 30-min batch scan as the only data source.
            if self._realtime_service is not None and not self._realtime_service.is_running():
                print(">>> Realtime is not running but accounts exist — starting it", flush=True)
                try:
                    await self._realtime_service.start()
                except Exception as rt_err:
                    print(f">>> ⚠️ Could not start realtime: {rt_err}", flush=True)
            
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
                    try:
                        result = await asyncio.wait_for(
                            self.telegram_service.parse_messages(
                                account["api_id"],
                                account["api_hash"],
                                account["phone_number"],
                                selected_chats,
                                hours_back=1
                            ),
                            timeout=PARSE_ACCOUNT_TIMEOUT_SECONDS
                        )
                    except asyncio.TimeoutError:
                        print(
                            f"⏱️ Account {account['phone_number']} exceeded "
                            f"{PARSE_ACCOUNT_TIMEOUT_SECONDS}s — aborted, will retry next cycle",
                            flush=True
                        )
                        continue
                    
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
                        
                        save_success = self.supabase_client.insert_messages_batch(formatted_messages)
                        if save_success:
                            print(f"✅ Saved {len(messages)} messages for account {account['phone_number']}")
                        else:
                            print(f"⚠️ WARNING: Failed to save {len(messages)} messages for account {account['phone_number']}! Check Supabase connection.")
                    
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
                        
                        logs_success = self.supabase_client.insert_parsing_logs_batch(formatted_logs)
                        if logs_success:
                            print(f"📊 Saved statistics for {len(stats)} chats")
                        else:
                            print(f"⚠️ WARNING: Failed to save parsing statistics for {len(stats)} chats!")
                
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

