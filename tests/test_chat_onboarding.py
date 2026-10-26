import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import FastAPI
from pyrogram import filters
from pyrogram.enums import ChatType, ChatMemberStatus
from pyrogram.errors import FloodWait, InviteRequestSent, UserNotParticipant, UserAlreadyParticipant

stub = types.ModuleType("backend.database.supabase_client")
stub.SupabaseClient = object
sys.modules.setdefault("backend.database.supabase_client", stub)

from backend.database.account_storage import AccountStorage
from backend.routers import chat_onboarding as routes
from backend.services import realtime_service as rt
from backend.services.session_clients import SessionClients, SessionBusyError


TOKEN = "test-only-token-not-valid-in-production-123456789"


class OnboardingRoutesTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.service = Mock()
        self.service.join_selected_chat = AsyncMock(return_value={"selected": True})
        self.service.onboarding_status.return_value = {"running": True}
        app = FastAPI()
        app.state.realtime_service = self.service
        app.include_router(routes.router, prefix="/onboarding")
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)
        env = patch.dict(os.environ, {
            "PARSER_CHAT_ADMIN_TOKEN": TOKEN,
            "PARSER_JOIN_ALLOWED_USERNAMES": "ozon_fbs,PDN152FZ",
        })
        env.start()
        self.addCleanup(env.stop)

    async def join(self, username="ozon_fbs", token=TOKEN):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return await self.client.post("/onboarding/join", json={"account_id": 3, "username": username}, headers=headers)

    async def test_missing_or_wrong_token_cannot_call_telegram(self):
        for token in (None, "wrong", "Bearer "+TOKEN):
            response = await self.join(token=token)
            self.assertEqual(401, response.status_code)
        self.service.join_selected_chat.assert_not_awaited()

    async def test_disabled_without_long_server_secret(self):
        for token in ("", "short"):
            with patch.dict(os.environ, {"PARSER_CHAT_ADMIN_TOKEN": token}):
                self.assertEqual(503, (await self.join()).status_code)
        self.service.join_selected_chat.assert_not_awaited()

    async def test_allowlist_and_public_username_validation(self):
        for name in ("https://t.me/ozon_fbs", "+privateinvite", "@ozon_fbs", "12345", "a/bcd"):
            self.assertEqual(422, (await self.join(name)).status_code)
        self.assertEqual(403, (await self.join("not_approved")).status_code)
        with patch.dict(os.environ, {"PARSER_JOIN_ALLOWED_USERNAMES": ""}):
            self.assertEqual(403, (await self.join()).status_code)
        self.service.join_selected_chat.assert_not_awaited()

    async def test_normalizes_approved_username(self):
        self.assertEqual(200, (await self.join("PDN152FZ")).status_code)
        self.service.join_selected_chat.assert_awaited_once_with(3, "pdn152fz")

    async def test_status_requires_token(self):
        self.assertEqual(401, (await self.client.get("/onboarding/status")).status_code)
        self.service.onboarding_status.assert_not_called()
        response = await self.client.get("/onboarding/status", headers={"Authorization": f"Bearer {TOKEN}"})
        self.assertEqual({"running": True}, response.json())

    async def test_floodwait_busy_and_timeout_are_not_success(self):
        for error, status in ((FloodWait(90), 429), (SessionBusyError(), 409), (asyncio.TimeoutError(), 504)):
            self.service.join_selected_chat.side_effect = error
            response = await self.join()
            self.assertEqual(status, response.status_code)
            if status == 429:
                self.assertEqual("90", response.headers["retry-after"])

    async def test_unexpected_errors_do_not_leak_secrets(self):
        self.service.join_selected_chat.side_effect = RuntimeError("secret-session-api-hash")
        response = await self.join()
        self.assertEqual(500, response.status_code)
        self.assertNotIn("secret-session-api-hash", response.text)


class OnboardingServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = SessionClients()
        patcher = patch.object(rt, "session_clients", self.pool)
        patcher.start()
        self.addCleanup(patcher.stop)
        with patch.object(AccountStorage, "_ensure_file_exists"):
            self.service = rt.RealtimeService(object())
        self.account = {"id": 3, "phone_number": "+70000000003", "is_connected": True}
        self.storage = Mock()
        self.storage.get_account.return_value = self.account
        self.storage.get_all_connected_accounts.return_value = [self.account]
        self.storage.selected_chat_owner.return_value = None
        self.storage.append_selected_chat.return_value = {"chat_ids": [-1001, -1002], "added": True, "persisted": True}
        self.service.account_storage = self.storage
        self.chat = SimpleNamespace(id=-1002, type=ChatType.SUPERGROUP, username="ozon_fbs", title="Test group")
        self.member = SimpleNamespace(status=ChatMemberStatus.MEMBER)
        self.client = SimpleNamespace(
            is_connected=True, start=AsyncMock(), stop=AsyncMock(), disconnect=AsyncMock(),
            get_chat=AsyncMock(return_value=self.chat),
            get_chat_member=AsyncMock(return_value=self.member),
            join_chat=AsyncMock(return_value=self.chat),
        )
        self.path = self.service._session_path(self.account["phone_number"])
        await self.pool.start(self.path, lambda: self.client)
        self.service._running = True
        self.service._clients[self.account["phone_number"]] = self.client
        self.live_filter = filters.chat([-1001])
        self.service._chat_filters[self.account["phone_number"]] = self.live_filter

    async def test_join_reuses_owner_preserves_old_filter_and_enables_new_messages(self):
        self.client.get_chat_member.side_effect = [UserNotParticipant(), self.member]
        result = await self.service.join_selected_chat(3, "ozon_fbs")
        self.assertEqual("joined", result["status"])
        self.assertTrue(result["persisted"])
        self.client.join_chat.assert_awaited_once_with(-1002)
        self.storage.append_selected_chat.assert_called_once_with(3, -1002)
        self.assertEqual({-1001, -1002}, self.live_filter)
        for chat_id in (-1001, -1002):
            msg = SimpleNamespace(chat=SimpleNamespace(id=chat_id, username=None, usernames=None))
            self.assertTrue(await self.live_filter(None, msg))
        self.assertIs(self.client, self.pool.state(self.path).client)
        self.client.stop.assert_not_awaited()
        self.client.disconnect.assert_not_awaited()

    async def test_existing_member_is_selected_without_joining_again(self):
        result = await self.service.join_selected_chat(3, "ozon_fbs")
        self.assertEqual("already_member", result["status"])
        self.client.join_chat.assert_not_awaited()

    async def test_already_participant_error_is_reconciled(self):
        self.client.get_chat_member.side_effect = [UserNotParticipant(), self.member]
        self.client.join_chat.side_effect = UserAlreadyParticipant()
        result = await self.service.join_selected_chat(3, "ozon_fbs")
        self.assertTrue(result["selected"])

    async def test_pending_approval_is_not_selected_or_repeated_then_recovers(self):
        self.client.get_chat_member.side_effect = UserNotParticipant()
        self.client.join_chat.side_effect = InviteRequestSent()
        first = await self.service.join_selected_chat(3, "ozon_fbs")
        self.assertEqual("pending_approval", first["status"])
        self.service._next_join_at = 0
        second = await self.service.join_selected_chat(3, "ozon_fbs")
        self.assertFalse(second["selected"])
        self.client.join_chat.assert_awaited_once()
        self.storage.append_selected_chat.assert_not_called()
        self.assertEqual({-1001}, self.live_filter)
        self.client.get_chat_member.side_effect = None
        self.service._next_join_at = 0
        third = await self.service.join_selected_chat(3, "ozon_fbs")
        self.assertTrue(third["selected"])

    async def test_floodwait_blocks_subsequent_join_attempts(self):
        self.client.get_chat.side_effect = FloodWait(90)
        with self.assertRaises(FloodWait):
            await self.service.join_selected_chat(3, "ozon_fbs")
        with self.assertRaises(FloodWait):
            await self.service.join_selected_chat(4, "pdn152fz")
        self.client.get_chat.assert_awaited_once()
        self.storage.append_selected_chat.assert_not_called()

    async def test_cross_account_duplicate_does_not_join(self):
        self.storage.selected_chat_owner.return_value = 4
        result = await self.service.join_selected_chat(3, "ozon_fbs")
        self.assertEqual("selected_on_other_account", result["status"])
        self.client.join_chat.assert_not_awaited()
        self.storage.append_selected_chat.assert_not_called()

    async def test_no_owner_does_not_create_or_authorize_a_client(self):
        self.pool.state(self.path).client = None
        with self.assertRaises(SessionBusyError):
            await self.service.join_selected_chat(3, "ozon_fbs")
        self.client.get_chat.assert_not_awaited()

    async def test_banned_or_unconfirmed_membership_does_not_select(self):
        self.client.get_chat_member.return_value = SimpleNamespace(status=ChatMemberStatus.BANNED)
        with self.assertRaises(PermissionError):
            await self.service.join_selected_chat(3, "ozon_fbs")
        self.client.join_chat.assert_not_awaited()
        self.service._next_join_at = 0
        self.client.get_chat_member.side_effect = UserNotParticipant()
        with self.assertRaises(PermissionError):
            await self.service.join_selected_chat(3, "ozon_fbs")
        self.storage.append_selected_chat.assert_not_called()

    async def test_private_chat_or_broadcast_is_not_joined(self):
        for chat_type in (ChatType.PRIVATE, ChatType.BOT, ChatType.CHANNEL):
            self.chat.type = chat_type
            self.service._next_join_at = 0
            with self.assertRaises(ValueError):
                await self.service.join_selected_chat(3, "ozon_fbs")
        self.client.join_chat.assert_not_awaited()

    async def test_cancellation_keeps_realtime_client_and_selections(self):
        started = asyncio.Event()

        async def hung(_):
            started.set()
            await asyncio.Event().wait()

        self.client.get_chat.side_effect = hung
        task = asyncio.create_task(self.service.join_selected_chat(3, "ozon_fbs"))
        await started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual({-1001}, self.live_filter)
        self.assertIs(self.client, self.pool.state(self.path).client)
        self.assertFalse(self.pool.state(self.path).lock.locked())
        self.client.stop.assert_not_awaited()
        self.client.disconnect.assert_not_awaited()

    async def test_storage_failure_does_not_enable_chat_in_memory(self):
        self.storage.append_selected_chat.side_effect = OSError("disk full")
        with self.assertRaises(OSError):
            await self.service.join_selected_chat(3, "ozon_fbs")
        self.assertEqual({-1001}, self.live_filter)

    async def test_disconnected_owner_and_unknown_account_cannot_join(self):
        self.client.is_connected = False
        with self.assertRaises(SessionBusyError):
            await self.service.join_selected_chat(3, "ozon_fbs")
        self.storage.get_account.return_value = None
        with self.assertRaises(ValueError):
            await self.service.join_selected_chat(99, "ozon_fbs")
        self.client.join_chat.assert_not_awaited()

    async def test_backup_failure_is_reported_not_hidden(self):
        self.storage.append_selected_chat.return_value["persisted"] = False
        result = await self.service.join_selected_chat(3, "ozon_fbs")
        self.assertTrue(result["listening"])
        self.assertFalse(result["persisted"])

    async def test_status_has_no_account_credentials(self):
        self.account.update(api_hash="SECRET", api_id="SECRET")
        status = self.service.onboarding_status()
        encoded = json.dumps(status)
        self.assertNotIn("SECRET", encoded)
        self.assertNotIn(self.account["phone_number"], encoded)
        self.assertEqual([-1001], status["accounts"][0]["listening_chat_ids"])

    async def test_http_join_to_storage_live_filter_and_message_save(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(AccountStorage, "_ensure_file_exists"):
                storage = AccountStorage()
            storage.storage_file = str(Path(directory) / "accounts.json")
            old = {"accounts": [self.account, {"id": 4}], "selected_chats": {"3": [-1001], "4": [-1003]}}
            Path(storage.storage_file).write_text(json.dumps(old))
            self.service.account_storage = storage
            self.client.get_chat_member.side_effect = [UserNotParticipant(), self.member]
            persistence = types.ModuleType("backend.database.state_persistence")
            persistence.backup_accounts = Mock(return_value=True)
            app = FastAPI()
            app.state.realtime_service = self.service
            app.include_router(routes.router, prefix="/onboarding")
            with (
                patch.dict(sys.modules, {"backend.database.state_persistence": persistence}),
                patch.dict(os.environ, {"PARSER_CHAT_ADMIN_TOKEN": TOKEN, "PARSER_JOIN_ALLOWED_USERNAMES": "ozon_fbs"}),
            ):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http:
                    response = await http.post("/onboarding/join", json={"account_id": 3, "username": "ozon_fbs"}, headers={"Authorization": f"Bearer {TOKEN}"})
            self.assertEqual(200, response.status_code)
            self.assertTrue(response.json()["persisted"])
            self.assertEqual([-1001, -1002], storage.get_selected_chats(3))
            self.assertEqual([-1003], storage.get_selected_chats(4))
            self.assertEqual(old["accounts"], storage.get_all_accounts())
            self.chat.usernames = None
            message = SimpleNamespace(chat=self.chat, text="synthetic test message", caption=None, date=datetime.now(timezone.utc), id=1)
            self.assertTrue(await self.live_filter(None, message))
            self.service._extract_user_info = AsyncMock(return_value={"user_id": 1, "username": "test_author"})
            self.service.supabase_client = Mock()
            self.service.supabase_client.insert_messages_batch.return_value = True
            await self.service._handle_message(self.client, message, self.account["phone_number"])
            await self.service._flush_queue()
            saved = self.service.supabase_client.insert_messages_batch.call_args.args[0]
            self.assertEqual("synthetic test message", saved[0]["message"])
            self.assertEqual(1, self.service.onboarding_status()["received_by_chat"][-1002])
            self.assertEqual([], self.service._errors)


class OnboardingStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        with patch.object(AccountStorage, "_ensure_file_exists"):
            self.storage = AccountStorage()
        self.storage.storage_file = str(Path(self.temp.name) / "accounts.json")
        self.data = {"accounts": [{"id": 3, "name": "first"}, {"id": 4, "name": "second"}], "selected_chats": {"3": [-1001], "4": [-1003]}, "untouched": True}
        Path(self.storage.storage_file).write_text(json.dumps(self.data))
        persistence = types.ModuleType("backend.database.state_persistence")
        persistence.backup_accounts = Mock(return_value=True)
        self.backup = persistence.backup_accounts
        patcher = patch.dict(sys.modules, {"backend.database.state_persistence": persistence})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_append_preserves_everything_else_and_is_idempotent(self):
        first = self.storage.append_selected_chat(3, -1002)
        second = self.storage.append_selected_chat(3, -1002)
        self.assertTrue(first["added"])
        self.assertFalse(second["added"])
        expected = self.data
        expected["selected_chats"]["3"].append(-1002)
        self.assertEqual(expected, json.loads(Path(self.storage.storage_file).read_text()))
        self.assertTrue(first["persisted"])
        self.assertEqual(3, self.storage.selected_chat_owner(-1002))

    def test_corrupt_storage_is_never_replaced_with_empty_state(self):
        path = Path(self.storage.storage_file)
        path.write_text("broken json")
        with self.assertRaises(json.JSONDecodeError):
            self.storage.append_selected_chat(3, -1002)
        with self.assertRaises(json.JSONDecodeError):
            self.storage.selected_chat_owner(-1002)
        self.assertEqual("broken json", path.read_text())

    def test_missing_account_and_duplicate_on_other_account_do_not_write(self):
        before = Path(self.storage.storage_file).read_bytes()
        for account_id, chat_id in ((99, -1002), (3, -1003)):
            with self.assertRaises(ValueError):
                self.storage.append_selected_chat(account_id, chat_id)
        self.assertEqual(before, Path(self.storage.storage_file).read_bytes())

    def test_atomic_write_failure_preserves_original_file(self):
        before = Path(self.storage.storage_file).read_bytes()
        with patch("backend.database.account_storage.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.storage.append_selected_chat(3, -1002)
        self.assertEqual(before, Path(self.storage.storage_file).read_bytes())
        self.assertEqual(1, len(list(Path(self.temp.name).iterdir())))

    def test_backup_failure_is_explicit_and_retry_can_persist(self):
        self.backup.return_value = False
        self.assertFalse(self.storage.append_selected_chat(3, -1002)["persisted"])
        self.backup.return_value = True
        self.assertTrue(self.storage.append_selected_chat(3, -1002)["persisted"])


if __name__ == "__main__":
    unittest.main()
