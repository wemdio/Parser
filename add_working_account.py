"""
Add working account to the system
This account already has a valid session file
"""
import json

# Рабочий аккаунт
ACCOUNT = {
    "api_id": "27151971",
    "api_hash": "769f1d8d9f15a4cd75819fce4a32699f",
    "phone_number": "+79959982523",
    "name": "Andruninkek"
}

def add_account():
    # Read current accounts
    try:
        with open("accounts.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = {"accounts": [], "selected_chats": {}}
    
    # Check if already exists
    for acc in data["accounts"]:
        if acc["phone_number"] == ACCOUNT["phone_number"]:
            print(f"[!] Account {ACCOUNT['phone_number']} already exists!")
            print(f"    Setting is_connected = True...")
            acc["is_connected"] = True
            with open("accounts.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[OK] Account updated!")
            return
    
    # Get new ID
    new_id = max([acc.get("id", 0) for acc in data["accounts"]], default=0) + 1
    
    # Add account
    new_account = {
        "id": new_id,
        "api_id": ACCOUNT["api_id"],
        "api_hash": ACCOUNT["api_hash"],
        "phone_number": ACCOUNT["phone_number"],
        "name": ACCOUNT["name"],
        "is_connected": True,  # Already connected via session file!
        "created_at": "2026-01-15T19:00:00.000000"
    }
    
    data["accounts"].append(new_account)
    
    # Save
    with open("accounts.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"ACCOUNT ADDED SUCCESSFULLY!")
    print(f"{'='*60}")
    print(f"ID: {new_id}")
    print(f"Phone: {ACCOUNT['phone_number']}")
    print(f"Name: {ACCOUNT['name']}")
    print(f"Status: CONNECTED (session file exists)")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    add_account()
