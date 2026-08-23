import asyncio
import sys
import types
import unittest
from unittest.mock import patch


# Keep this lifecycle test independent from the external Supabase SDK.
supabase_client_module = types.ModuleType("backend.database.supabase_client")
supabase_client_module.SupabaseClient = object
sys.modules.setdefault("backend.database.supabase_client", supabase_client_module)

from backend.services import realtime_service as realtime_module


def account(account_id: int, phone: str) -> dict:
    return {
        "id": account_id,
        "phone_number": phone,
        "api_id": 1000 + account_id,
        "api_hash": f"hash-{account_id}",
    }


class FakeAccountStorage:
    def __init__(self, accounts: list[dict]):
        self.accounts = accounts

    def get_all_connected_accounts(self) -> list[dict]:
        return self.accounts


class FakeClient:
    def __init__(self):
        self.stopped = False

    async def stop(self):
        self.stopped = True


class RealtimeServiceStartTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        service = getattr(self, "service", None)
        if service and service.is_running():
            await service.stop()

    async def test_hung_client_does_not_block_other_accounts(self):
        hung = account(1, "+70000000001")
        healthy = account(2, "+70000000002")
        self.service = realtime_module.RealtimeService(object())
        self.service.account_storage = FakeAccountStorage([hung, healthy])
        hung_cancelled = asyncio.Event()

        async def start_client(current: dict):
            if current["id"] == hung["id"]:
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    hung_cancelled.set()
                    raise
            self.service._clients[current["phone_number"]] = FakeClient()

        with (
            patch.object(self.service, "_start_client", side_effect=start_client),
            patch.object(
                realtime_module,
                "CLIENT_START_TIMEOUT_SECONDS",
                0.01,
                create=True,
            ),
        ):
            await asyncio.wait_for(self.service.start(), timeout=0.2)

        self.assertIn(healthy["phone_number"], self.service._clients)
        self.assertNotIn(hung["phone_number"], self.service._clients)
        self.assertTrue(hung_cancelled.is_set())
        self.assertTrue(
            any(
                hung["phone_number"] in error and "timed out" in error.lower()
                for error in self.service._errors
            )
        )

    async def test_all_hung_clients_leave_service_retryable(self):
        hung = account(1, "+70000000001")
        self.service = realtime_module.RealtimeService(object())
        self.service.account_storage = FakeAccountStorage([hung])

        async def never_starts(_current: dict):
            await asyncio.Event().wait()

        with (
            patch.object(self.service, "_start_client", side_effect=never_starts),
            patch.object(
                realtime_module,
                "CLIENT_START_TIMEOUT_SECONDS",
                0.01,
                create=True,
            ),
        ):
            await asyncio.wait_for(self.service.start(), timeout=0.2)

        self.assertFalse(self.service.is_running())

        async def starts_on_retry(current: dict):
            self.service._clients[current["phone_number"]] = FakeClient()

        with patch.object(self.service, "_start_client", side_effect=starts_on_retry):
            await asyncio.wait_for(self.service.start(), timeout=0.2)

        self.assertTrue(self.service.is_running())
        self.assertIn(hung["phone_number"], self.service._clients)

    async def test_hung_client_does_not_block_shutdown(self):
        self.service = realtime_module.RealtimeService(object())
        healthy_client = FakeClient()
        hung_cancelled = asyncio.Event()

        class HungClient:
            async def stop(self):
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    hung_cancelled.set()
                    raise

        hung_phone = "+70000000001"
        healthy_phone = "+70000000002"
        self.service._clients = {
            hung_phone: HungClient(),
            healthy_phone: healthy_client,
        }
        self.service._running = True
        self.service._flush_task = asyncio.create_task(self.service._flush_loop())

        with patch.object(
            realtime_module,
            "CLIENT_STOP_TIMEOUT_SECONDS",
            0.01,
            create=True,
        ):
            await asyncio.wait_for(self.service.stop(), timeout=0.2)

        self.assertFalse(self.service.is_running())
        self.assertEqual({}, self.service._clients)
        self.assertTrue(healthy_client.stopped)
        self.assertTrue(hung_cancelled.is_set())
        self.assertTrue(
            any(
                hung_phone in error and "timed out" in error.lower()
                for error in self.service._errors
            )
        )


if __name__ == "__main__":
    unittest.main()
