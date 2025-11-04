from typing import List
from backend.services.telegram_service import TelegramService
from backend.database.account_storage import AccountStorage
from backend.database.supabase_client import SupabaseClient

class ParserService:
    def __init__(self, supabase_client: SupabaseClient):
        self.telegram_service = TelegramService()
        self.account_storage = AccountStorage()
        self.supabase_client = supabase_client
    
    async def parse_all_accounts(self):
        """Парсит сообщения для всех подключенных аккаунтов"""
        print(f"\n>>> Starting parse_all_accounts", flush=True)
        
        accounts = self.account_storage.get_all_connected_accounts()
        print(f">>> Found {len(accounts)} connected accounts", flush=True)
        
        if not accounts:
            print(">>> WARNING: No connected accounts found!", flush=True)
            return
        
        for account in accounts:
            print(f">>> Processing account: {account.get('phone_number')}", flush=True)
            try:
                selected_chats = self.account_storage.get_selected_chats(account["id"])
                print(f">>> Selected chats for account {account['id']}: {selected_chats}", flush=True)
                
                if not selected_chats:
                    print(f">>> WARNING: No selected chats for account {account['id']}", flush=True)
                    continue
                
                print(f">>> Parsing messages from {len(selected_chats)} chats...", flush=True)
                messages = await self.telegram_service.parse_messages(
                    account["api_id"],
                    account["api_hash"],
                    account["phone_number"],
                    selected_chats,
                    hours_back=1
                )
                print(f">>> Found {len(messages)} messages", flush=True)
                
                if messages:
                    # Преобразуем datetime строки в формат для Supabase
                    formatted_messages = []
                    for msg in messages:
                        formatted_messages.append({
                            "message_time": msg["message_time"],
                            "chat_name": msg["chat_name"],
                            "user_id": msg.get("user_id"),  # ← ДОБАВЛЕНО!
                            "first_name": msg["first_name"],
                            "last_name": msg["last_name"],
                            "username": msg["username"],
                            "bio": msg["bio"],
                            "profile_link": msg.get("profile_link"),  # ← ДОБАВЛЕНО!
                            "message": msg["message"]
                        })
                    
                    self.supabase_client.insert_messages_batch(formatted_messages)
                    print(f"Parsed {len(messages)} messages for account {account['phone_number']}")
            
            except Exception as e:
                print(f"Error parsing account {account.get('phone_number', 'unknown')}: {e}")
                continue

