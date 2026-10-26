import asyncio
import os
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from backend.services.session_clients import SessionBusyError, SessionClients
from backend.services import telegram_service as telegram_module


class Client:
    def __init__(self):
        self.is_connected = False
        self.is_initialized = False
        self.connects = self.disconnects = self.stops = 0

    async def connect(self):
        self.connects += 1
        self.is_connected = True

    async def start(self):
        await self.connect()
        self.is_initialized = True

    async def disconnect(self):
        self.disconnects += 1
        self.is_connected = False

    async def stop(self):
        self.stops += 1
        self.is_initialized = False
        self.is_connected = False


class SessionClientsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = SessionClients()
        self.path = "/tmp/session-unit-test"
        self.client = Client()

    async def test_read_reuses_realtime_without_disconnect(self):
        await self.pool.start(self.path, lambda: self.client)
        factory = AsyncMock(side_effect=AssertionError("second connection"))
        async with self.pool.read(self.path, factory) as borrowed:
            self.assertIs(borrowed, self.client)
        self.assertTrue(self.client.is_connected)
        self.assertEqual(self.client.disconnects, 0)
        factory.assert_not_awaited()
        await self.pool.stop(self.path, self.client)

    async def test_fallback_connects_and_closes(self):
        async with self.pool.read(self.path, AsyncMock(return_value=self.client)):
            self.assertTrue(self.client.is_connected)
        self.assertEqual((self.client.connects, self.client.disconnects), (1, 1))

    async def test_fallback_closes_on_cancellation(self):
        entered = asyncio.Event()

        async def read():
            async with self.pool.read(self.path, AsyncMock(return_value=self.client)):
                entered.set()
                await asyncio.Event().wait()

        task = asyncio.create_task(read())
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.client.disconnects, 1)
        self.assertFalse(self.pool.state(self.path).lock.locked())

    async def test_cancelled_borrower_does_not_close_realtime(self):
        await self.pool.start(self.path, lambda: self.client)
        with self.assertRaises(asyncio.CancelledError):
            async with self.pool.read(self.path, AsyncMock()):
                raise asyncio.CancelledError()
        self.assertTrue(self.client.is_connected)
        self.assertEqual(self.client.disconnects, 0)

    async def test_start_waits_for_fallback_cleanup(self):
        entered, release = asyncio.Event(), asyncio.Event()
        persistent = Client()

        async def read():
            async with self.pool.read(self.path, AsyncMock(return_value=self.client)):
                entered.set()
                await release.wait()

        reader = asyncio.create_task(read())
        await entered.wait()
        starter = asyncio.create_task(self.pool.start(self.path, lambda: persistent))
        await asyncio.sleep(0)
        self.assertEqual(persistent.connects, 0)
        release.set()
        await reader
        await starter
        self.assertEqual(self.client.disconnects, 1)

    async def test_stop_cancels_borrower_then_closes_owner(self):
        await self.pool.start(self.path, lambda: self.client)
        entered = asyncio.Event()

        async def read():
            async with self.pool.read(self.path, AsyncMock()):
                entered.set()
                await asyncio.Event().wait()

        reader = asyncio.create_task(read())
        await entered.wait()
        await asyncio.wait_for(self.pool.stop(self.path, self.client), 0.2)
        self.assertTrue(reader.cancelled())
        self.assertEqual(self.client.stops, 1)
        await self.pool.start(self.path, lambda: Client())

    async def test_failed_close_blocks_second_connection(self):
        self.client.disconnect = AsyncMock(side_effect=RuntimeError("close failed"))
        with self.assertRaisesRegex(RuntimeError, "close failed"):
            async with self.pool.read(self.path, AsyncMock(return_value=self.client)):
                pass
        factory = AsyncMock()
        with self.assertRaises(SessionBusyError):
            async with self.pool.read(self.path, factory):
                pass
        factory.assert_not_awaited()

    async def test_cancelled_connect_closes_partial_storage(self):
        close = AsyncMock()
        self.client.storage = SimpleNamespace(conn=object(), close=close)
        self.client.session = SimpleNamespace(stop=AsyncMock())
        entered = asyncio.Event()

        async def connect():
            entered.set()
            await asyncio.Event().wait()

        self.client.connect = connect

        async def read():
            async with self.pool.read(self.path, AsyncMock(return_value=self.client)):
                pass

        reader = asyncio.create_task(read())
        await entered.wait()
        reader.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await reader
        close.assert_awaited_once()
        self.assertFalse(self.pool.state(self.path).unavailable)

    async def test_pending_auth_blocks_runtime(self):
        self.pool.state(self.path).auth_client = self.client
        with self.assertRaises(SessionBusyError):
            await self.pool.start(self.path, lambda: Client())

    async def test_auth_cannot_replace_live_session(self):
        await self.pool.start(self.path, lambda: self.client)
        with self.assertRaises(SessionBusyError):
            async with self.pool.authorize(self.path):
                self.fail("authorization must not reach file deletion")

    async def test_upload_cannot_interrupt_pending_authorization(self):
        await self.client.connect()
        self.pool.state(self.path).auth_client = self.client
        with self.assertRaises(SessionBusyError):
            async with self.pool.authorize(self.path):
                self.fail("upload must not replace a pending login")
        self.assertTrue(self.client.is_connected)
        self.assertEqual(self.client.disconnects, 0)
        self.assertIs(self.pool.state(self.path).auth_client, self.client)

    async def test_pending_authorization_can_continue_verification(self):
        await self.client.connect()
        self.pool.state(self.path).auth_client = self.client
        async with self.pool.authorize(self.path, allow_pending=True):
            await self.pool.close_authorization(self.path, self.client)
        self.assertIsNone(self.pool.state(self.path).auth_client)
        await self.pool.start(self.path, lambda: Client())

    async def test_cancelled_authorization_closes_partial_storage(self):
        close = AsyncMock()
        self.client.storage = SimpleNamespace(conn=object(), close=close)
        with self.assertRaises(asyncio.CancelledError):
            async with self.pool.authorize(self.path) as state:
                state.auth_client = self.client
                raise asyncio.CancelledError()
        close.assert_awaited_once()
        self.assertIsNone(self.pool.state(self.path).auth_client)

    async def test_failed_authorization_cleanup_blocks_restart(self):
        await self.client.connect()
        self.client.disconnect = AsyncMock(side_effect=RuntimeError("close failed"))
        with self.assertRaisesRegex(RuntimeError, "close failed"):
            async with self.pool.authorize(self.path) as state:
                state.auth_client = self.client
                raise ValueError("sign-in failed")
        with self.assertRaises(SessionBusyError):
            await self.pool.start(self.path, lambda: Client())

    async def test_partial_start_failure_releases_storage_before_retry(self):
        close = AsyncMock()
        self.client.storage = SimpleNamespace(conn=object(), close=close)
        self.client.start = AsyncMock(side_effect=RuntimeError("init failed"))
        with self.assertRaisesRegex(RuntimeError, "init failed"):
            await self.pool.start(self.path, lambda: self.client)
        close.assert_awaited_once()
        self.assertIsNone(self.pool.state(self.path).client)
        await self.pool.start(self.path, lambda: Client())

    async def test_failed_stop_retains_owner_and_allows_cleanup_retry(self):
        await self.pool.start(self.path, lambda: self.client)
        stop = self.client.stop
        self.client.stop = AsyncMock(side_effect=RuntimeError("stop failed"))
        with self.assertRaisesRegex(RuntimeError, "stop failed"):
            await self.pool.stop(self.path, self.client)
        self.assertIs(self.pool.state(self.path).client, self.client)
        with self.assertRaises(SessionBusyError):
            async with self.pool.read(self.path, AsyncMock()):
                pass
        self.client.stop = stop
        await self.pool.stop(self.path, self.client)
        await self.pool.start(self.path, lambda: Client())

    async def test_wrong_owner_cannot_poison_working_session(self):
        await self.pool.start(self.path, lambda: self.client)
        with self.assertRaises(SessionBusyError):
            await self.pool.stop(self.path, Client())
        self.assertFalse(self.pool.state(self.path).closing)
        async with self.pool.read(self.path, AsyncMock()) as borrowed:
            self.assertIs(borrowed, self.client)

    async def test_different_accounts_do_not_block_each_other(self):
        async with self.pool.read(self.path, AsyncMock(return_value=self.client)):
            async with self.pool.read(self.path + "-other", AsyncMock(return_value=Client())):
                pass

    async def test_equivalent_paths_have_same_lock(self):
        self.assertIs(self.pool.state(self.path), self.pool.state("/tmp/./session-unit-test"))

    async def test_real_sqlite_write_transaction_reuses_one_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "client")
            conn = sqlite3.connect(path + ".session", timeout=0)
            self.addCleanup(conn.close)
            conn.execute("create table peers(id integer)")
            conn.execute("insert into peers values (1)")
            other = sqlite3.connect(path + ".session", timeout=0)
            try:
                with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                    other.execute("insert into peers values (99)")
            finally:
                other.close()
            await self.pool.start(path, lambda: self.client)
            async with self.pool.read(path, AsyncMock(side_effect=AssertionError("second SQLite owner"))):
                conn.execute("insert into peers values (2)")
                conn.commit()
            self.assertEqual(conn.execute("select count(*) from peers").fetchone()[0], 2)


class TelegramConsumersTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = SessionClients()
        patcher = patch.object(telegram_module, "session_clients", self.pool)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.service = telegram_module.TelegramService()
        self.path = self.service.get_session_path("+70000000001")
        self.client = Client()

    async def test_batch_and_chat_listing_borrow_same_client(self):
        await self.pool.start(self.path, lambda: self.client)
        self.service.create_client = AsyncMock(side_effect=AssertionError("second client"))
        self.service._get_chats_raw = AsyncMock(return_value=[])
        self.service._parse_with_client = AsyncMock(return_value={"messages": [], "stats": []})
        await self.service.get_chats("1", "test", "+70000000001")
        await self.service.parse_messages("1", "test", "+70000000001", [123], hours_back=1)
        self.service._get_chats_raw.assert_awaited_once_with(self.client)
        self.service._parse_with_client.assert_awaited_once_with(self.client, [123], 1)
        self.service.create_client.assert_not_awaited()
        self.assertTrue(self.client.is_connected)

    async def test_reauthorization_refuses_live_file_before_deletion(self):
        await self.pool.start(self.path, lambda: self.client)
        with patch.object(telegram_module.os, "remove") as remove:
            with self.assertRaises(SessionBusyError):
                await self.service.connect_account("1", "test", "+70000000001")
            remove.assert_not_called()

    async def test_parse_failure_does_not_disconnect_shared_client(self):
        await self.pool.start(self.path, lambda: self.client)
        self.service._parse_with_client = AsyncMock(side_effect=RuntimeError("history failed"))
        with self.assertRaisesRegex(RuntimeError, "history failed"):
            await self.service.parse_messages("1", "test", "+70000000001", [123])
        self.assertTrue(self.client.is_connected)

    async def test_cancelled_verification_removes_disconnected_cached_client(self):
        await self.client.connect()
        self.pool.state(self.path).auth_client = self.client
        self.service._verify_code = AsyncMock(side_effect=asyncio.CancelledError())
        with self.assertRaises(asyncio.CancelledError):
            await self.service.verify_code("1", "test", "+70000000001", "00000", "test")
        self.assertFalse(self.client.is_connected)
        self.assertIsNone(self.pool.state(self.path).auth_client)
        self.assertNotIn("+70000000001", self.service._active_clients)

    async def test_verification_uses_pending_owner_across_service_instances(self):
        await self.client.connect()
        self.pool.state(self.path).auth_client = self.client

        async def verify(*args):
            self.assertIs(self.service._active_clients["+70000000001"], self.client)
            await self.client.disconnect()
            return True

        self.service._verify_code = verify
        self.assertTrue(await self.service.verify_code("1", "test", "+70000000001", "00000", "test"))
        self.assertIsNone(self.pool.state(self.path).auth_client)


if __name__ == "__main__":
    unittest.main()
