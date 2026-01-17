"""
Проверка существующих сессий Telegram
"""
import asyncio
from pyrogram import Client
import os

# API credentials для проверки
# Имя сессии БЕЗ последнего .session (Pyrogram добавит автоматически)
ACCOUNTS = [
    {
        "session": "79959982523.session",
        "api_id": 27151971,
        "api_hash": "769f1d8d9f15a4cd75819fce4a32699f",
        "phone": "+79959982523"
    },
    {
        "session": "79861760834.session",
        "api_id": 27399397,
        "api_hash": "ea8395bc60c486bb433e1da84862e5d8",
        "phone": "+79861760834"
    }
]

async def check_session(account):
    print(f"\n{'='*60}")
    print(f"Checking: {account['phone']}")
    print(f"{'='*60}")
    
    # Pyrogram добавляет .session автоматически
    session_path = f"sessions/{account['session']}.session"
    
    if not os.path.exists(session_path):
        print(f"[X] File not found: {session_path}")
        return False
    
    file_size = os.path.getsize(session_path)
    print(f"[+] File found: {session_path} ({file_size} bytes)")
    
    app = Client(
        account['session'],
        api_id=account['api_id'],
        api_hash=account['api_hash'],
        workdir="sessions"
    )
    
    try:
        print(f"[*] Connecting...")
        await app.start()
        
        me = await app.get_me()
        
        print(f"[OK] SESSION WORKS!")
        print(f"    ID: {me.id}")
        print(f"    Phone: {me.phone_number}")
        
        # Безопасный вывод имени/username (могут содержать кириллицу)
        try:
            if me.username:
                print(f"    Username: @{me.username}")
            print(f"    Name: {me.first_name or ''} {me.last_name or ''}")
        except:
            print(f"    Name: [contains non-ASCII characters]")
        
        dialog_count = 0
        async for dialog in app.get_dialogs(limit=5):
            dialog_count += 1
        
        print(f"    Chats access: OK ({dialog_count}+ chats)")
        
        await app.stop()
        return True
        
    except Exception as e:
        error_msg = str(e)
        # Безопасный вывод ошибки
        try:
            print(f"[X] ERROR: {error_msg}")
        except:
            print(f"[X] ERROR: [contains non-ASCII characters]")
        print(f"    Session invalid or expired")
        return False

async def main():
    print("\n" + "="*60)
    print("CHECKING EXISTING TELEGRAM SESSIONS")
    print("="*60)
    
    results = []
    for account in ACCOUNTS:
        result = await check_session(account)
        results.append({
            'phone': account['phone'],
            'working': result
        })
        await asyncio.sleep(2)
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print("="*60)
    
    working = [r for r in results if r['working']]
    not_working = [r for r in results if not r['working']]
    
    if working:
        print(f"\n[OK] Working sessions ({len(working)}):")
        for r in working:
            print(f"   - {r['phone']}")
    
    if not_working:
        print(f"\n[X] Not working ({len(not_working)}):")
        for r in not_working:
            print(f"   - {r['phone']}")
    
    if len(working) == len(results):
        print("\n[SUCCESS] ALL SESSIONS WORK!")
        print("          Ready for parsing!")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(main())
