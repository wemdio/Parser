from pyrogram import Client, filters
from pyrogram.errors import FloodWait, AuthKeyUnregistered
from pyrogram.handlers import MessageHandler
from backend.database.account_storage import AccountStorage
from backend.database.supabase_client import SupabaseClient
from datetime import datetime, timezone
import asyncio
import os
import sys


class RealtimeService:
    """Persistent Telegram clients that receive messages in real-time via event handlers."""

    def __init__(self, supabase_client: SupabaseClient):
        self.supabase_client = supabase_client
        self.account_storage = AccountStorage()
        self.sessions_dir = "sessions"

        self._clients: dict[str, Client] = {}
        self._running = False
        self._msg_count = 0
        self._errors: list[str] = []
        self._started_at: datetime | None = None

        self._bio_cache: dict[int, str | None] = {}
        self._chat_title_cache: dict[int, tuple[str, str | None]] = {}

        self._save_queue: list[dict] = []
        self._flush_task: asyncio.Task | None = None

    # ── public status ────────────────────────────────────────────────

    def is_running(self) -> bool:
        return self._running

    def status(self) -> dict:
        return {
            "running": self._running,
            "accounts": len(self._clients),
            "messages_received": self._msg_count,
            "queue_size": len(self._save_queue),
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "recent_errors": self._errors[-5:],
        }

    # ── lifecycle ────────────────────────────────────────────────────

    async def start(self):
        if self._running:
            return

        print("\n" + "=" * 60, flush=True)
        print(">>> REALTIME SERVICE STARTING <<<", flush=True)
        print("=" * 60, flush=True)

        accounts = self.account_storage.get_all_connected_accounts()
        if not accounts:
            print(">>> No connected accounts, realtime not started", flush=True)
            return

        self._running = True
        self._started_at = datetime.now(timezone.utc)
        self._flush_task = asyncio.create_task(self._flush_loop())

        for account in accounts:
            try:
                await self._start_client(account)
            except Exception as e:
                err = f"Failed to start client {account.get('phone_number')}: {e}"
                print(f">>> {err}", flush=True)
                self._errors.append(err)

        total = len(self._clients)
        print(f">>> REALTIME SERVICE STARTED — {total} client(s) connected", flush=True)

    async def stop(self):
        if not self._running:
            return

        print("\n>>> REALTIME SERVICE STOPPING...", flush=True)
        self._running = False

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        await self._flush_queue()

        for phone, client in list(self._clients.items()):
            try:
                await client.stop()
                print(f">>> Disconnected {phone}", flush=True)
            except Exception as e:
                print(f">>> Error disconnecting {phone}: {e}", flush=True)

        self._clients.clear()
        print(">>> REALTIME SERVICE STOPPED", flush=True)

    async def restart(self):
        await self.stop()
        await asyncio.sleep(1)
        await self.start()

    # ── client management ────────────────────────────────────────────

    async def _start_client(self, account: dict):
        phone = account["phone_number"]
        api_id = int(account["api_id"])
        api_hash = account["api_hash"]
        account_id = account["id"]

        safe_phone = phone.replace("+", "").replace("-", "").replace(" ", "")
        session_path = os.path.join(self.sessions_dir, safe_phone)

        if not os.path.exists(f"{session_path}.session"):
            raise FileNotFoundError(f"Session file not found: {session_path}.session")

        selected_chats = self.account_storage.get_selected_chats(account_id)
        if not selected_chats:
            print(f">>> No selected chats for {phone}, skipping realtime", flush=True)
            return

        client = Client(
            session_path,
            api_id=api_id,
            api_hash=api_hash,
        )

        chat_filter = filters.chat(selected_chats) & (filters.text | filters.caption)

        async def on_message(c: Client, message):
            await self._handle_message(c, message, phone)

        client.add_handler(MessageHandler(on_message, chat_filter))

        await client.start()
        self._clients[phone] = client

        chat_count = len(selected_chats)
        print(f">>> Client {phone} connected, listening to {chat_count} chats", flush=True)

    # ── message handler ──────────────────────────────────────────────

    async def _handle_message(self, client: Client, message, phone: str):
        try:
            msg_date = message.date
            if hasattr(msg_date, 'timestamp'):
                from datetime import datetime as dt
                msg_date = dt.fromtimestamp(msg_date.timestamp(), tz=timezone.utc)

            chat = message.chat
            chat_id = chat.id
            if chat_id not in self._chat_title_cache:
                self._chat_title_cache[chat_id] = (
                    getattr(chat, 'title', None) or f"Chat {chat_id}",
                    getattr(chat, 'username', None),
                )
            chat_title, chat_username = self._chat_title_cache[chat_id]

            user_info = await self._extract_user_info(client, message)
            if user_info is None:
                return

            message_text = message.text or message.caption or ""
            if not message_text:
                return

            profile_link = self._build_profile_link(
                user_info, chat_title, chat_username, message.id
            )

            msg_data = {
                "message_time": msg_date.isoformat(),
                "chat_name": chat_title,
                "user_id": user_info.get("user_id"),
                "first_name": user_info.get("first_name"),
                "last_name": user_info.get("last_name"),
                "username": user_info.get("username"),
                "bio": user_info.get("bio"),
                "profile_link": profile_link,
                "message": message_text,
            }

            self._save_queue.append(msg_data)
            self._msg_count += 1

        except Exception as e:
            err = f"handle_message error: {e}"
            print(f">>> RT: {err}", file=sys.stderr, flush=True)
            self._errors.append(err)

    async def _extract_user_info(self, client: Client, message) -> dict | None:
        if message.from_user:
            uid = message.from_user.id
            info = {
                "user_id": uid,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
                "username": message.from_user.username,
            }
            info["bio"] = await self._get_bio(client, uid, is_channel=False)
            return info

        if hasattr(message, 'sender_chat') and message.sender_chat:
            sid = message.sender_chat.id
            info = {
                "user_id": sid,
                "first_name": getattr(message.sender_chat, 'title', None),
                "last_name": None,
                "username": getattr(message.sender_chat, 'username', None),
            }
            info["bio"] = await self._get_bio(client, sid, is_channel=True)
            return info

        return None

    async def _get_bio(self, client: Client, uid: int, is_channel: bool) -> str | None:
        if uid in self._bio_cache:
            return self._bio_cache[uid]

        try:
            full = await client.get_chat(uid)
            if is_channel:
                bio = getattr(full, 'description', None)
            else:
                bio = getattr(full, 'bio', None) or getattr(full, 'about', None)
            self._bio_cache[uid] = bio
            return bio
        except FloodWait:
            self._bio_cache[uid] = None
            return None
        except Exception:
            self._bio_cache[uid] = None
            return None

    @staticmethod
    def _build_profile_link(user_info: dict, chat_title: str,
                            chat_username: str | None, msg_id: int) -> str:
        uname = user_info.get("username")
        if uname:
            return f"https://t.me/{uname}"
        if chat_username:
            link = f"https://t.me/{chat_username}/{msg_id}"
            return f'Профиль скрыт. Сообщение в чате "{chat_title}": {link}'
        return f'Профиль скрыт. Сообщение в приватном чате "{chat_title}" (ID сообщения: {msg_id})'

    # ── queue flush ──────────────────────────────────────────────────

    async def _flush_loop(self):
        """Flush accumulated messages every 3 seconds."""
        while self._running:
            await asyncio.sleep(3)
            await self._flush_queue()

    async def _flush_queue(self):
        if not self._save_queue:
            return

        batch = self._save_queue[:]
        self._save_queue.clear()

        try:
            success = self.supabase_client.insert_messages_batch(batch)
            if success:
                print(f">>> RT: Saved {len(batch)} messages in real-time", flush=True)
            else:
                self._errors.append(f"Failed to save batch of {len(batch)} messages")
        except Exception as e:
            err = f"flush error: {e}"
            print(f">>> RT: {err}", file=sys.stderr, flush=True)
            self._errors.append(err)
