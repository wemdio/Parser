from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

    # Restore accounts.json + session files from Supabase BEFORE anything reads
    # them. Timeweb Apps wipe these on every rebuild; this makes the account +
    # session survive redeploys so the parser reconnects automatically.
    try:
        from backend.database import state_persistence
        state_persistence.restore_all()
    except Exception as e:
        print(f"⚠️ State restore failed (continuing): {e}", flush=True)

    # Инициализация сервисов
    parser_service = ParserService(supabase_client)
    realtime_service = RealtimeService(supabase_client)

    # Wire realtime into parser so the scheduled batch can revive realtime
    # if it failed to start at boot (typical when no accounts were connected
    # yet at lifespan startup).
    parser_service.set_realtime_service(realtime_service)

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
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300
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
    # Clients are stopped now, so session files are consistent — back them up.
    try:
        from backend.database import state_persistence
        state_persistence.backup_all()
    except Exception as e:
        print(f"⚠️ State backup on shutdown failed: {e}", flush=True)
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

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0-with-logging",
        "logging": "enabled"
    }

# ── Serve the built React frontend (merged single-app deploy) ─────────────
# Dockerfile.fullstack builds frontend/ and copies the result to ./frontend_build.
# Static assets are served from /static; any other path falls back to index.html
# so React Router client-side routes resolve. /api/* and /health are matched by
# their own routes above (registered before this catch-all).
FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend_build"
)
_FRONTEND_INDEX = os.path.join(FRONTEND_DIR, "index.html")

if os.path.isdir(FRONTEND_DIR):
    _static_dir = os.path.join(FRONTEND_DIR, "static")
    if os.path.isdir(_static_dir):
        app.mount("/static", StaticFiles(directory=_static_dir), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(_FRONTEND_INDEX)

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        # If an /api or /health path reaches here it didn't match a real route → 404.
        if full_path.startswith("api/") or full_path == "health":
            raise HTTPException(status_code=404, detail="Not found")
        # Serve real root-level files (favicon.ico, manifest.json, ...),
        # guarding against path traversal.
        candidate = os.path.normpath(os.path.join(FRONTEND_DIR, full_path))
        if (candidate == FRONTEND_DIR or candidate.startswith(FRONTEND_DIR + os.sep)) \
                and os.path.isfile(candidate):
            return FileResponse(candidate)
        # Otherwise hand back the SPA entry point.
        return FileResponse(_FRONTEND_INDEX)
else:
    @app.get("/")
    async def root():
        return {
            "message": "Telegram Parser API",
            "version": "2.0-with-logging",
            "status": "Backend is running (frontend not bundled)",
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

