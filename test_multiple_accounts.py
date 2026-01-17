import asyncio
from pyrogram import Client

# Тестируем 3 аккаунта
accounts = [
    {
        "api_id": 28175657,
        "api_hash": "0bba767d56632e4cc6e3831c3e7d3ef6",
        "phone": "+79996472302",
        "name": "test_account_1"
    },
    {
        "api_id": 27151971,
        "api_hash": "769f1d8d9f15a4cd75819fce4a32699f",
        "phone": "+79959982523",
        "name": "test_account_2"
    },
    {
        "api_id": 27399397,
        "api_hash": "ea8395bc60c486bb433e1da84862e5d8",
        "phone": "+79861760834",
        "name": "test_account_3"
    }
]

async def test_account(account):
    print(f"\n{'='*60}")
    print(f"Testing: {account['phone']}")
    print(f"API ID: {account['api_id']}")
    print(f"{'='*60}\n")
    
    app = Client(
        account['name'],
        api_id=account['api_id'],
        api_hash=account['api_hash'],
        phone_number=account['phone'],
        workdir="."
    )
    
    try:
        await app.connect()
        print(f"[{account['phone']}] Connected to Telegram!")
        
        sent_code = await app.send_code(account['phone'])
        print(f"[{account['phone']}] CODE REQUEST SENT!")
        print(f"[{account['phone']}] Phone code hash: {sent_code.phone_code_hash[:20]}...")
        print(f"[{account['phone']}] SUCCESS - Check your Telegram app for code!")
        
    except Exception as e:
        print(f"[{account['phone']}] ERROR: {e}")
    finally:
        await app.disconnect()
        print(f"[{account['phone']}] Disconnected\n")

async def main():
    print("\n" + "="*60)
    print("TESTING TELEGRAM CODE SENDING FOR 3 ACCOUNTS")
    print("="*60)
    
    for account in accounts:
        await test_account(account)
        await asyncio.sleep(2)  # Небольшая пауза между аккаунтами
    
    print("\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
