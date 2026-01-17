"""
Минимальный скрипт для теста отправки кода в Telegram
"""
import sys
import codecs
# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

import asyncio
from pyrogram import Client

async def test_send_code():
    # ВСТАВЬТЕ ВАШИ ДАННЫЕ ЗДЕСЬ
    api_id = "28175657"  # Замените на реальный
    api_hash = "0bba767d56632e4cc6e3831c3e7d3ef6"  # Замените на реальный
    phone = "+79996472302"  # Замените на реальный номер
    
    print(f"\n{'='*60}")
    print(f"Testing Telegram code sending")
    print(f"Phone: {phone}")
    print(f"API ID: {api_id}")
    print(f"{'='*60}\n")
    
    client = Client(
        f"test_{phone}",
        api_id=int(api_id),
        api_hash=api_hash,
        phone_number=phone
    )
    
    try:
        await client.connect()
        print("✅ Connected to Telegram")
        
        # Проверяем авторизацию
        try:
            me = await client.get_me()
            print(f"✅ Already authorized as: {me.first_name}")
            await client.disconnect()
            return
        except Exception as e:
            print(f"❌ Not authorized: {e}")
        
        # Отправляем код
        print("\n🔄 Sending code...")
        sent_code = await client.send_code(phone)
        
        print(f"\n{'='*60}")
        print(f"✅ CODE REQUEST SENT!")
        print(f"Phone code hash: {sent_code.phone_code_hash}")
        print(f"Type: {sent_code.type}")
        
        # Проверяем тип отправки
        if hasattr(sent_code, 'type'):
            print(f"Send type: {sent_code.type}")
            if sent_code.type == 'app':
                print("📱 Code will be sent to Telegram app")
            elif sent_code.type == 'sms':
                print("📱 Code will be sent via SMS")
            elif sent_code.type == 'call':
                print("📞 Code will be sent via phone call")
            elif sent_code.type == 'flash_call':
                print("📞 Code will be sent via flash call")
        
        print(f"{'='*60}\n")
        
        print("⏳ Check your Telegram app NOW!")
        print("   Look for message from 'Telegram' (blue-white icon)")
        print("   Code format: 5 digits like '12345'")
        print("\nDid you receive the code? (yes/no)")
        
        await client.disconnect()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        if client.is_connected:
            await client.disconnect()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TELEGRAM CODE TEST SCRIPT")
    print("="*60)
    print("\nRunning test...")
    print("="*60 + "\n")
    
    asyncio.run(test_send_code())
