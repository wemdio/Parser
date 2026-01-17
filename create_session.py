from pyrogram import Client

API_ID = "27399397"
API_HASH = "ea8395bc60c486bb433e1da84862e5d8"
PHONE = "+79861760834"

session_name = PHONE.replace("+", "")

print(f"Creating session for {PHONE}...")
print("Code will arrive in Telegram!")

app = Client(session_name, api_id=API_ID, api_hash=API_HASH, phone_number=PHONE)

with app:
    me = app.get_me()
    print(f"\nSession created for: {me.first_name}")
    print(f"File: {session_name}.session")
