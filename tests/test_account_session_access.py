import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException
from backend.database.account_storage import AccountStorage
from backend.services.session_clients import SessionClients


# These route tests must not initialize a Supabase client or write account data.
persistence = types.ModuleType("backend.database.state_persistence")
persistence.backup_session = Mock()
persistence.backup_accounts = Mock()
with (
    patch.dict(sys.modules, {"backend.database.state_persistence": persistence}),
    patch.object(AccountStorage, "_ensure_file_exists"),
):
    from backend.routers import accounts


class AccountSessionAccessTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = SessionClients()
        self.storage = Mock()
        self.storage.get_account.return_value = {
            "id": 1, "phone_number": "+70000000001", "api_id": "1", "api_hash": "test"
        }
        self.path = accounts.telegram_service.get_session_path("+70000000001")
        self.client = SimpleNamespace(
            is_connected=True,
            start=AsyncMock(),
            stop=AsyncMock(),
            disconnect=AsyncMock(),
            get_me=AsyncMock(return_value=SimpleNamespace(first_name="Test")),
        )
        for patcher in (
            patch.object(accounts, "session_clients", self.pool),
            patch.object(accounts, "account_storage", self.storage),
            patch.object(accounts.os.path, "exists", return_value=True),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    async def test_status_borrows_live_owner_without_reconnect(self):
        await self.pool.start(self.path, lambda: self.client)
        with patch.object(accounts.telegram_service, "create_client", new_callable=AsyncMock) as factory:
            result = await accounts.check_account_status(1)
        self.assertEqual(result["status"], "connected")
        factory.assert_not_awaited()
        self.client.disconnect.assert_not_awaited()
        self.client.stop.assert_not_awaited()

    async def test_status_does_not_mark_pending_authorization_invalid(self):
        self.pool.state(self.path).auth_client = self.client
        with self.assertRaises(HTTPException) as exc:
            await accounts.check_account_status(1)
        self.assertEqual(exc.exception.status_code, 409)
        self.storage.update_account_connection.assert_not_called()

    async def test_upload_cannot_replace_live_owner(self):
        await self.pool.start(self.path, lambda: self.client)
        with patch.object(accounts, "_upload_session", new_callable=AsyncMock) as upload:
            with self.assertRaises(HTTPException) as exc:
                await accounts.upload_session(object(), "1", "test", "+7 (000) 000-00-01", None)
        self.assertEqual(exc.exception.status_code, 409)
        upload.assert_not_awaited()

    async def test_upload_cannot_replace_pending_authorization(self):
        self.pool.state(self.path).auth_client = self.client
        with patch.object(accounts, "_upload_session", new_callable=AsyncMock) as upload:
            with self.assertRaises(HTTPException) as exc:
                await accounts.upload_session(object(), "1", "test", "+70000000001", None)
        self.assertEqual(exc.exception.status_code, 409)
        upload.assert_not_awaited()
        self.client.disconnect.assert_not_awaited()

    async def test_delete_cannot_remove_live_session(self):
        await self.pool.start(self.path, lambda: self.client)
        with patch.object(accounts.os, "remove") as remove:
            with self.assertRaises(HTTPException) as exc:
                await accounts.delete_account(1)
        self.assertEqual(exc.exception.status_code, 409)
        remove.assert_not_called()
        self.storage.delete_account.assert_not_called()


if __name__ == "__main__":
    unittest.main()
