import asyncio
from pyrogram import Client
from pyrogram.errors import FloodWait

accounts = [
    {
        "api_id": 28175657,
        "api_hash": "0bba767d56632e4cc6e3831c3e7d3ef6",
        "phone": "+79996472302",
        "name": "test_sms_1"
    },
    {
        "api_id": 27151971,
        "api_hash": "769f1d8d9f15a4cd75819fce4a32699f",
        "phone": "+79959982523",
        "name": "test_sms_2"
    },
    {
        "api_id": 27399397,
        "api_hash": "ea8395bc60c486bb433e1da84862e5d8",
        "phone": "+79861760834",
        "name": "test_sms_3"
    }
]

async def test_sms(account):
    print(f"\n{'='*60}")
    print(f"Testing SMS: {account['phone']}")
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
        print(f"[{account['phone']}] Connected!")
        
        # Сначала обычный запрос
        sent_code = await app.send_code(account['phone'])
        print(f"[{account['phone']}] Code type: {sent_code.type}")
        
        await asyncio.sleep(3)
        
        # Теперь запрашиваем ПОВТОРНУЮ отправку через SMS
        print(f"[{account['phone']}] Requesting RESEND via SMS...")
        await app.resend_code(account['phone'], sent_code.phone_code_hash)
        print(f"[{account['phone']}] SMS CODE REQUESTED! Check SMS!")
        
    except FloodWait as e:
        print(f"[{account['phone']}] FLOOD WAIT: {e.value} seconds")
    except Exception as e:
        print(f"[{account['phone']}] ERROR: {e}")
    finally:
        await app.disconnect()
        print(f"[{account['phone']}] Done\n")

async def main():
    print("\n" + "="*60)
    print("TESTING SMS CODE SENDING")
    print("="*60)
    
    for account in accounts:
        await test_sms(account)
        await asyncio.sleep(3)
    
    print("\n" + "="*60)
    print("CHECK YOUR SMS!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
