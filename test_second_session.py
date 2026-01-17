"""Test second session using copy"""
import asyncio
from pyrogram import Client

async def test():
    print("\n" + "="*60)
    print("Testing: +79861760834 (copy)")
    print("="*60 + "\n")
    
    app = Client(
        "79861760834_copy.session",
        api_id=27399397,
        api_hash="ea8395bc60c486bb433e1da84862e5d8",
        workdir="sessions"
    )
    
    try:
        print("[*] Connecting...")
        await app.start()
        
        me = await app.get_me()
        
        print("[OK] SESSION WORKS!")
        print(f"    ID: {me.id}")
        print(f"    Phone: {me.phone_number}")
        
        try:
            if me.username:
                print(f"    Username: @{me.username}")
        except:
            pass
        
        dialog_count = 0
        async for dialog in app.get_dialogs(limit=5):
            dialog_count += 1
        
        print(f"    Chats access: OK ({dialog_count}+ chats)")
        
        await app.stop()
        
        print("\n[SUCCESS] This session is ready to use!")
        
    except Exception as e:
        print(f"[X] ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test())
