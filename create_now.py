"""
Create Telegram session
"""
import asyncio
from pyrogram import Client

async def create_session():
    print("\n" + "="*60)
    print("CREATING TELEGRAM SESSION")
    print("="*60 + "\n")
    
    api_id = 27399397
    api_hash = "ea8395bc60c486bb433e1da84862e5d8"
    phone = "+79861760834"
    
    print(f"API ID: {api_id}")
    print(f"Phone: {phone}")
    print(f"{'='*60}\n")
    
    session_name = phone.replace("+", "").replace(" ", "").replace("-", "")
    
    client = Client(
        f"sessions/{session_name}",
        api_id=api_id,
        api_hash=api_hash,
        phone_number=phone
    )
    
    try:
        print("Connecting to Telegram...")
        print("Code will arrive in Telegram app!")
        print("="*60)
        
        await client.start()
        
        me = await client.get_me()
        
        print(f"\n{'='*60}")
        print(f"SUCCESS!")
        print(f"Name: {me.first_name} {me.last_name or ''}")
        print(f"Username: @{me.username or 'none'}")
        print(f"ID: {me.id}")
        print(f"{'='*60}\n")
        
        print(f"Session file created: sessions/{session_name}.session")
        
        await client.stop()
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(create_session())
