"""
Создание сессии Telegram локально
После запуска файл сессии можно загрузить на сервер
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

import asyncio
from pyrogram import Client

async def create_session():
    print("\n" + "="*60)
    print("СОЗДАНИЕ СЕССИИ TELEGRAM")
    print("="*60 + "\n")
    
    # ВСТАВЬТЕ ВАШИ ДАННЫЕ
    api_id = input("Введите API ID: ")
    api_hash = input("Введите API Hash: ")
    phone = input("Введите номер телефона (например, +79991234567): ")
    
    print(f"\n{'='*60}")
    print(f"Создаём сессию для {phone}")
    print(f"{'='*60}\n")
    
    # Создаём клиент с именем файла сессии
    session_name = phone.replace("+", "").replace(" ", "").replace("-", "")
    
    client = Client(
        f"sessions/{session_name}",
        api_id=int(api_id),
        api_hash=api_hash,
        phone_number=phone
    )
    
    try:
        await client.start()
        
        me = await client.get_me()
        
        print(f"\n{'='*60}")
        print(f"✅ УСПЕШНО АВТОРИЗОВАНЫ!")
        print(f"Имя: {me.first_name} {me.last_name or ''}")
        print(f"Username: @{me.username or 'нет'}")
        print(f"ID: {me.id}")
        print(f"{'='*60}\n")
        
        print(f"📁 Файл сессии создан:")
        print(f"   sessions/{session_name}.session")
        print(f"\n✅ Теперь вы можете:")
        print(f"   1. Скопировать этот файл на сервер в папку sessions/")
        print(f"   2. Использовать аккаунт в парсере без кода!")
        print(f"\n{'='*60}\n")
        
        await client.stop()
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n⚠️  ВАЖНО:")
    print("   1. Этот скрипт создаст файл сессии локально")
    print("   2. Telegram может запросить код через APP (не API)")
    print("   3. Если код не приходит - попробуйте через несколько часов")
    print("   4. Или используйте номер, который не пробовали сегодня\n")
    
    asyncio.run(create_session())
