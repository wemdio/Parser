"""
Create sessions for multiple accounts
Run this script and enter verification codes when they arrive in Telegram
"""
import asyncio
from pyrogram import Client
import os

# Your accounts
ACCOUNTS = [
    {
        "api_id": 28969523,
        "api_hash": "688076c4ccbd479f0719de0bba1b29d5",
        "phone": "+79957884802"
    },
    {
        "api_id": 28175657,
        "api_hash": "0bba767d56632e4cc6e3831c3e7d3ef6",
        "phone": "+79996472302"
    },
    {
        "api_id": 27399397,
        "api_hash": "ea8395bc60c486bb433e1da84862e5d8",
        "phone": "+79861760834"
    },
    {
        "api_id": 27151971,
        "api_hash": "769f1d8d9f15a4cd75819fce4a32699f",
        "phone": "+79959982523"
    }
]

async def create_session(account):
    phone = account["phone"]
    phone_clean = phone.replace("+", "").replace(" ", "")
    session_path = f"sessions/{phone_clean}"
    
    print(f"\n{'='*60}")
    print(f"Creating session for {phone}")
    print(f"API ID: {account['api_id']}")
    print(f"{'='*60}")
    
    # Check if session already exists
    if os.path.exists(f"{session_path}.session"):
        print(f"Session file already exists: {session_path}.session")
        
        # Try to use existing session
        client = Client(
            session_path,
            api_id=account["api_id"],
            api_hash=account["api_hash"]
        )
        
        try:
            await client.start()
            me = await client.get_me()
            print(f"Existing session VALID!")
            print(f"User: {me.first_name} (@{me.username or 'no username'})")
            await client.stop()
            return True
        except Exception as e:
            print(f"Existing session invalid: {e}")
            print("Will create new session...")
    
    # Create new session
    client = Client(
        session_path,
        api_id=account["api_id"],
        api_hash=account["api_hash"],
        phone_number=phone
    )
    
    try:
        await client.start()
        me = await client.get_me()
        print(f"\nSUCCESS!")
        print(f"User: {me.first_name} {me.last_name or ''}")
        print(f"Username: @{me.username or 'none'}")
        print(f"ID: {me.id}")
        print(f"Session saved: {session_path}.session")
        await client.stop()
        return True
    except Exception as e:
        print(f"\nERROR: {e}")
        return False

async def main():
    print("\n" + "="*60)
    print("SESSION CREATOR FOR MULTIPLE ACCOUNTS")
    print("="*60)
    print("\nThis script will create sessions for 4 accounts.")
    print("When Telegram sends a code, enter it in the terminal.")
    print("\nPress Enter to start...")
    input()
    
    os.makedirs("sessions", exist_ok=True)
    
    results = []
    for account in ACCOUNTS:
        try:
            success = await create_session(account)
            results.append((account["phone"], success))
        except Exception as e:
            print(f"Failed for {account['phone']}: {e}")
            results.append((account["phone"], False))
    
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    for phone, success in results:
        status = "OK" if success else "FAILED"
        print(f"  {phone}: {status}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
