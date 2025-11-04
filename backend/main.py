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

from backend.routers import accounts, chats, parser
from backend.services.parser_service import ParserService
from backend.database.supabase_client import SupabaseClient

# Инициализация Supabase
supabase_client = SupabaseClient()

# Инициализация планировщика
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "="*70, flush=True)
    print(">>> BACKEND STARTED <<<", flush=True)
    print(">>> Listening on http://localhost:8000", flush=True)
    print(">>> LOGS WILL APPEAR BELOW", flush=True)
    print("="*70 + "\n", flush=True)
    
    # Инициализация сервиса парсинга
    parser_service = ParserService(supabase_client)
    
    # Запуск планировщика при старте
    scheduler.start()
    
    # Добавляем задачу на каждый час
    scheduler.add_job(
        parser_service.parse_all_accounts,
        'interval',
        hours=1,
        id='hourly_parse',
        replace_existing=True
    )
    
    print("Scheduler started - will parse messages every hour\n", flush=True)
    
    yield
    
    # Остановка планировщика при завершении
    print("\nShutting down backend...", flush=True)
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(chats.router, prefix="/api/chats", tags=["chats"])
app.include_router(parser.router, prefix="/api/parser", tags=["parser"])

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

