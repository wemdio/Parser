from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from dotenv import load_dotenv
import os
import sys

# Настройка кодировки для Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ВАЖНО: Загружаем .env ПЕРЕД импортом модулей
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)
print(f"\n>>> Loading .env from: {env_path}", flush=True)
print(f">>> .env exists: {os.path.exists(env_path)}", flush=True)
print(f">>> SUPABASE_URL set: {bool(os.getenv('SUPABASE_URL'))}", flush=True)
print(f">>> SUPABASE_KEY set: {bool(os.getenv('SUPABASE_KEY'))}", flush=True)
if os.getenv('SUPABASE_URL'):
    print(f">>> SUPABASE_URL: {os.getenv('SUPABASE_URL')[:50]}...", flush=True)

from backend.routers import accounts, chats, parser, stats
from backend.services.parser_service import ParserService
from backend.services.realtime_service import RealtimeService
from backend.database.supabase_client import SupabaseClient

# Инициализация Supabase
supabase_client = SupabaseClient()

# Передаём Supabase client в роутер статистики
stats.set_supabase_client(supabase_client)

# Инициализация планировщика
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "="*70, flush=True)
    print(">>> BACKEND STARTED <<<", flush=True)
    print(">>> Listening on http://localhost:8000", flush=True)
    print(">>> LOGS WILL APPEAR BELOW", flush=True)
    print("="*70 + "\n", flush=True)
    
    # Инициализация сервисов
    parser_service = ParserService(supabase_client)
    realtime_service = RealtimeService(supabase_client)
    
    # Сохраняем в app.state для доступа из роутеров
    app.state.scheduler = scheduler
    app.state.auto_parsing_enabled = True
    app.state.realtime_service = realtime_service
    
    # Запуск планировщика (batch-парсинг как fallback каждые 30 мин)
    scheduler.start()
    scheduler.add_job(
        parser_service.parse_all_accounts,
        'interval',
        minutes=30,
        id='hourly_parse',
        replace_existing=True
    )
    print("✅ Scheduler started — batch fallback every 30 min", flush=True)
    
    # Запуск real-time сервиса
    try:
        await realtime_service.start()
        print("✅ Realtime service started — messages arrive instantly\n", flush=True)
    except Exception as e:
        print(f"⚠️ Realtime service failed to start: {e}", flush=True)
        print("   Batch parsing will still work as fallback\n", flush=True)
    
    yield
    
    # Остановка при завершении
    print("\nShutting down backend...", flush=True)
    await realtime_service.stop()
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# Настройка CORS - разрешаем все origin для упрощения деплоя
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем все домены
    allow_credentials=False,  # Отключаем credentials для работы с wildcard
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(chats.router, prefix="/api/chats", tags=["chats"])
app.include_router(parser.router, prefix="/api/parser", tags=["parser"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])

@app.get("/")
async def root():
    return {
        "message": "Telegram Parser API",
        "version": "2.0-with-logging",
        "status": "Backend is running with enhanced logging"
    }

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0-with-logging",
        "logging": "enabled"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

