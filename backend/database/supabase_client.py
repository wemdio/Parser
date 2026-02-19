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
        """Вставляет пакет сообщений с устойчивостью к дубликатам.
        
        Unique index messages_unique_hash_idx использует выражения
        (md5(message), COALESCE(username,''), chat_name, message_time),
        поэтому PostgREST upsert не может разрешить конфликт автоматически.
        Вставляем чанками; при ошибке дубликата — fallback на поштучную вставку.
        """
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
            
        print(f"Inserting {len(messages)} messages to Supabase...", flush=True)
        
        if len(messages) > 0:
            first_msg = messages[0]
            print(f"\n🔍 DEBUG: First message to insert:", flush=True)
            print(f"   user_id: {first_msg.get('user_id')} (type: {type(first_msg.get('user_id'))})", flush=True)
            print(f"   profile_link: {first_msg.get('profile_link')}", flush=True)
            print(f"   first_name: {first_msg.get('first_name')}", flush=True)
            print(f"   chat_name: {first_msg.get('chat_name')}", flush=True)

        CHUNK_SIZE = 50
        total_inserted = 0
        total_duplicates = 0
        total_errors = 0

        for i in range(0, len(messages), CHUNK_SIZE):
            chunk = messages[i:i + CHUNK_SIZE]
            try:
                result = self.client.table('messages').upsert(chunk, ignore_duplicates=True).execute()
                inserted = len(result.data) if result.data else 0
                total_inserted += inserted
                total_duplicates += len(chunk) - inserted
            except Exception as chunk_err:
                err_code = getattr(chunk_err, 'code', '') or ''
                err_msg = str(chunk_err)
                is_duplicate = '23505' in err_msg or '23505' in str(err_code)

                if is_duplicate:
                    ins, dup, errs = self._insert_individually(chunk)
                    total_inserted += ins
                    total_duplicates += dup
                    total_errors += errs
                else:
                    print(f"❌ Chunk insert error (non-duplicate): {chunk_err}", flush=True)
                    total_errors += len(chunk)

        if total_duplicates > 0 or total_errors > 0:
            print(f"✅ Inserted {total_inserted}, ⏩ duplicates skipped {total_duplicates}, ❌ errors {total_errors} (total {len(messages)})", flush=True)
        else:
            print(f"✅ Successfully inserted all {total_inserted} messages!", flush=True)

        return total_errors == 0 or total_inserted > 0

    def _insert_individually(self, messages: list):
        """Fallback: вставляет сообщения по одному, пропуская дубликаты."""
        inserted = 0
        duplicates = 0
        errors = 0
        for msg in messages:
            try:
                result = self.client.table('messages').upsert([msg], ignore_duplicates=True).execute()
                if result.data:
                    inserted += 1
                else:
                    duplicates += 1
            except Exception as e:
                err_msg = str(e)
                if '23505' in err_msg:
                    duplicates += 1
                else:
                    errors += 1
                    if errors <= 3:
                        print(f"⚠️ Individual insert error: {err_msg[:150]}", flush=True)
        return inserted, duplicates, errors
    
    def insert_parsing_logs_batch(self, logs: list) -> bool:
        """Вставляет пакет логов парсинга"""
        if not self.client:
            print("⚠️ WARNING: Supabase client not initialized. Parsing logs not saved!", flush=True)
            return False
        
        if not logs:
            return True
            
        try:
            print(f"📊 Inserting {len(logs)} parsing logs to Supabase...", flush=True)
            result = self.client.table('parsing_logs').insert(logs).execute()
            print(f"✅ Successfully inserted {len(logs)} parsing logs!", flush=True)
            return True
        except Exception as e:
            print(f"❌ ERROR inserting parsing logs: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False

