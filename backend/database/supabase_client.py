from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

class SupabaseClient:
    def __init__(self):
        print("\n" + "="*70, flush=True)
        print("🔧 INITIALIZING SUPABASE CLIENT", flush=True)
        print("="*70, flush=True)
        
        # Проверяем ВСЕ переменные окружения, связанные с Supabase
        print(f"📋 Checking environment variables:", flush=True)
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        print(f"   SUPABASE_URL exists: {supabase_url is not None}", flush=True)
        print(f"   SUPABASE_KEY exists: {supabase_key is not None}", flush=True)
        
        if supabase_url:
            print(f"   SUPABASE_URL value: {supabase_url[:30]}...", flush=True)
        else:
            print(f"   ❌ SUPABASE_URL is empty/None!", flush=True)
            
        if supabase_key:
            print(f"   SUPABASE_KEY length: {len(supabase_key)} characters", flush=True)
        else:
            print(f"   ❌ SUPABASE_KEY is empty/None!", flush=True)
        
        if not supabase_url or not supabase_key:
            print("\n❌ ERROR: SUPABASE_URL and/or SUPABASE_KEY not set!", flush=True)
            print("   Please set them in Timeweb Cloud environment variables", flush=True)
            print("   Then RESTART the backend application", flush=True)
            print("="*70 + "\n", flush=True)
            self.client = None
            return
        
        try:
            print(f"Initializing Supabase client...", flush=True)
            print(f"URL: {supabase_url}", flush=True)
            
            self.client: Client = create_client(supabase_url, supabase_key)
            print("Supabase client initialized successfully!", flush=True)
            
            # Проверяем подключение
            try:
                # Простой запрос для проверки
                self.client.table('messages').select("id").limit(1).execute()
                print("Supabase connection verified!", flush=True)
            except Exception as test_error:
                print(f"Warning: Could not verify Supabase connection: {test_error}", flush=True)
                print("Table might not exist yet - will be created on first insert", flush=True)
                
        except Exception as e:
            print(f"ERROR: Could not initialize Supabase client: {e}", flush=True)
            import traceback
            traceback.print_exc()
            self.client = None
    
    def _ensure_table_exists(self):
        """Проверяет что таблица messages существует"""
        if not self.client:
            return
        
        try:
            # Проверяем существование таблицы
            self.client.table('messages').select("id").limit(1).execute()
            print("Table 'messages' exists", flush=True)
        except Exception as e:
            print(f"Warning: Could not verify table 'messages': {e}", flush=True)
            print("Please create table in Supabase dashboard", flush=True)
    
    def insert_message(self, message_data: dict):
        """Вставляет сообщение в базу данных"""
        if not self.client:
            print("Warning: Supabase client not initialized. Message not saved.")
            return None
        try:
            response = self.client.table("messages").insert(message_data).execute()
            return response.data
        except Exception as e:
            print(f"Error inserting message: {e}")
            raise
    
    def insert_messages_batch(self, messages: list) -> bool:
        """Вставляет пакет сообщений"""
        if not self.client:
            print("\n" + "="*70, flush=True)
            print("❌ ERROR: Supabase client not initialized. Messages not saved!", flush=True)
            print("   Possible reasons:", flush=True)
            print("   1. SUPABASE_URL or SUPABASE_KEY not set in environment", flush=True)
            print("   2. Backend not restarted after adding variables", flush=True)
            print("   3. Invalid Supabase credentials", flush=True)
            print("="*70 + "\n", flush=True)
            return False
        
        if not messages:
            print("No messages to insert", flush=True)
            return True
            
        try:
            print(f"Inserting {len(messages)} messages to Supabase...", flush=True)
            
            # Логируем первые 2 сообщения для отладки
            if len(messages) > 0:
                print(f"\n🔍 DEBUG: First message to insert:", flush=True)
                first_msg = messages[0]
                print(f"   user_id: {first_msg.get('user_id')} (type: {type(first_msg.get('user_id'))})", flush=True)
                print(f"   profile_link: {first_msg.get('profile_link')}", flush=True)
                print(f"   first_name: {first_msg.get('first_name')}", flush=True)
                print(f"   chat_name: {first_msg.get('chat_name')}", flush=True)
            
            result = self.client.table('messages').insert(messages).execute()
            print(f"Successfully inserted {len(messages)} messages!", flush=True)
            return True
        except Exception as e:
            print(f"ERROR inserting messages batch: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False

