#!/usr/bin/env python3
"""
Скрипт для запуска backend сервера
"""
import sys
import os

# Настройка кодировки для Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

if __name__ == "__main__":
    if "--serve" not in sys.argv:
        from backend.process_supervisor import supervise
        supervise(__file__)
        sys.exit(0)

    import faulthandler
    import signal
    import uvicorn

    faulthandler.enable()
    if hasattr(signal, "SIGUSR1"):
        faulthandler.register(signal.SIGUSR1, all_threads=True)

    print("\n" + "="*70)
    print("STARTING BACKEND - Version 2.1")
    print("="*70 + "\n")
    
    # Отладочный вывод переменных окружения
    print("🔍 Environment variables check:")
    print(f"   SUPABASE_URL set: {bool(os.getenv('SUPABASE_URL'))}")
    print(f"   SUPABASE_KEY set: {bool(os.getenv('SUPABASE_KEY'))}")
    if os.getenv('SUPABASE_URL'):
        print(f"   SUPABASE_URL: {os.getenv('SUPABASE_URL')[:50]}...")
    else:
        print("   ⚠️  WARNING: SUPABASE_URL not set!")
    if not os.getenv('SUPABASE_KEY'):
        print("   ⚠️  WARNING: SUPABASE_KEY not set!")
    print()
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        # Session ownership is process-local; WEB_CONCURRENCY must not fork it.
        workers=1,
        reload=False,  # Отключаем auto-reload - он не работает корректно
        log_level="info",
        access_log=True
    )

