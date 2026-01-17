"""
Простой скрипт для создания сессии Telegram
Использование:
    python create_session_easy.py

ВАЖНО: Код будет запрошен через ОФИЦИАЛЬНОЕ приложение Telegram
       (не через API), поэтому блокировка не действует!
"""
import asyncio
import sys
from pyrogram import Client

# Используем один из ваших аккаунтов
API_ID = 27151971
API_HASH = "769f1d8d9f15a4cd75819fce4a32699f"
PHONE = "+79959982523"
SESSION_NAME = "79959982523.session"

print("="*60)
print("СОЗДАНИЕ TELEGRAM СЕССИИ")
print("="*60)
print(f"\nАккаунт: {PHONE}")
print(f"API ID: {API_ID}")
print("\n⚠️  Telegram запросит код через ОФИЦИАЛЬНОЕ приложение")
print("   (не через API - блокировка не действует!)\n")

async def create_session():
    app = Client(
        SESSION_NAME,
        api_id=API_ID,
        api_hash=API_HASH,
        phone_number=PHONE,
        workdir="sessions"
    )
    
    try:
        print("🔄 Подключение к Telegram...\n")
        await app.start()
        
        print("✅ СЕССИЯ СОЗДАНА УСПЕШНО!")
        print(f"📁 Файл: sessions/{SESSION_NAME}.session")
        
        me = await app.get_me()
        print(f"\n👤 Аккаунт: {me.first_name} (@{me.username})")
        print(f"📱 ID: {me.id}")
        
        await app.stop()
        
        print("\n" + "="*60)
        print("ГОТОВО! Теперь загрузите этот файл на сервер:")
        print(f"sessions/{SESSION_NAME}.session")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        print("\n💡 Попробуйте:")
        print("   1. Подождать 24 часа")
        print("   2. Использовать другой номер")
        print("   3. Или экспортировать сессию из Telegram Desktop")

if __name__ == "__main__":
    asyncio.run(create_session())
