"""
Тест отправки кода через SMS
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

import asyncio
from pyrogram import Client
import time

async def test_send_code_sms():
    api_id = "28175657"
    api_hash = "0bba767d56632e4cc6e3831c3e7d3ef6"
    phone = "+79996472302"
    
    print(f"\n{'='*60}")
    print(f"Testing Telegram code sending (will try SMS)")
    print(f"Phone: {phone}")
    print(f"{'='*60}\n")
    
    client = Client(
        f"test_sms_{phone}",
        api_id=int(api_id),
        api_hash=api_hash,
        phone_number=phone
    )
    
    try:
        await client.connect()
        print("✅ Connected to Telegram\n")
        
        # Отправляем код
        print("🔄 Sending code request...")
        sent_code = await client.send_code(phone)
        
        print(f"\n{'='*60}")
        print(f"✅ CODE REQUEST SENT!")
        print(f"Phone code hash: {sent_code.phone_code_hash}")
        print(f"Type: {sent_code.type}")
        print(f"{'='*60}\n")
        
        # Ждём 10 секунд
        print("⏳ Waiting 10 seconds...")
        await asyncio.sleep(10)
        
        # Пробуем запросить повторно через SMS
        print("\n🔄 Requesting code resend via SMS/Call...")
        try:
            resend = await client.resend_code(phone, sent_code.phone_code_hash)
            print(f"✅ Resend requested!")
            print(f"New type: {resend.type}")
            print(f"{'='*60}\n")
        except Exception as e:
            print(f"❌ Resend failed: {e}\n")
        
        print("📱 Check your phone NOW!")
        print("   - Telegram app message")
        print("   - SMS message")
        print("   - Phone call (last 5 digits of number)")
        
        await client.disconnect()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        if client.is_connected:
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_send_code_sms())
