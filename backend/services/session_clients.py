"""Serialize access to each on-disk Telegram session within the API process."""

import asyncio
import os
from contextlib import asynccontextmanager


CLOSE_TIMEOUT_SECONDS = 10


class SessionBusyError(RuntimeError):
    pass


class SessionState:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.client = None
        self.auth_client = None
        self.unavailable = False
        self.closing = False
        self.borrowers = set()


class SessionClients:
    def __init__(self):
        self._states = {}

    def state(self, path):
        return self._states.setdefault(os.path.realpath(path), SessionState())

    @staticmethod
    def _check(state):
        if state.unavailable or state.closing:
            raise SessionBusyError("Session is closing or requires process recovery")
        if state.auth_client is not None:
            raise SessionBusyError("Session authorization is in progress")

    async def _close(self, state, client, stop=False):
        async def close():
            if stop:
                await client.stop()
            elif getattr(client, "is_connected", False):
                await client.disconnect()
            else:
                # connect() can be cancelled after opening SQLite but before
                # setting is_connected. disconnect() rejects this state.
                session = getattr(client, "session", None)
                if session is not None:
                    await session.stop()
                storage = getattr(client, "storage", None)
                if getattr(storage, "conn", None) is not None:
                    await storage.close()
        try:
            await asyncio.wait_for(close(), CLOSE_TIMEOUT_SECONDS)
        except BaseException:
            # Do not open a second connection if cleanup did not finish.
            state.unavailable = True
            raise

    @asynccontextmanager
    async def read(self, path, factory):
        state = self.state(path)
        async with state.lock:
            self._check(state)
            if state.client is not None:
                if not state.client.is_connected:
                    raise SessionBusyError("Realtime client is disconnected; restart it first")
                task = asyncio.current_task()
                state.borrowers.add(task)
                try:
                    yield state.client
                finally:
                    state.borrowers.discard(task)
                return
            client = await factory()
            if client is None:
                raise RuntimeError("Failed to create Telegram client")
            try:
                task = asyncio.current_task()
                state.borrowers.add(task)
                await client.connect()
                if not client.is_connected:
                    raise RuntimeError("Telegram client did not connect")
                yield client
            finally:
                try:
                    await self._close(state, client)
                finally:
                    state.borrowers.discard(task)

    async def start(self, path, factory):
        state = self.state(path)
        async with state.lock:
            self._check(state)
            if state.client is not None:
                raise SessionBusyError("Realtime session already has an owner")
            client = factory()
            try:
                await client.start()
            except BaseException:
                # start() may have opened storage before initialization failed.
                try:
                    if getattr(client, "is_initialized", False):
                        await self._close(state, client, stop=True)
                    else:
                        await self._close(state, client)
                except BaseException:
                    state.unavailable = True
                raise
            state.client = client
            return client

    async def stop(self, path, client):
        state = self.state(path)
        if state.client is not None and state.client is not client:
            raise SessionBusyError("Cannot stop another session owner")
        state.closing = True
        borrowers = list(state.borrowers)
        for task in borrowers:
            task.cancel()
        if borrowers:
            await asyncio.gather(*borrowers, return_exceptions=True)
        async with state.lock:
            if state.client is not None and state.client is not client:
                raise SessionBusyError("Cannot stop another session owner")
            await self._close(state, client, stop=True)
            state.client = None
            state.closing = False
            state.unavailable = False

    async def close_authorization(self, path, client):
        """Close an auth client while the caller holds authorize()."""
        state = self.state(path)
        if state.auth_client is not client:
            raise SessionBusyError("Cannot close another authorization owner")
        await self._close(state, client)
        state.auth_client = None

    @asynccontextmanager
    async def authorize(self, path, allow_pending=False):
        state = self.state(path)
        async with state.lock:
            if state.client is not None or state.unavailable or state.closing:
                raise SessionBusyError("Stop the active Telegram client before reauthorizing")
            if state.auth_client is not None and not allow_pending:
                raise SessionBusyError("Session authorization is already in progress")
            try:
                yield state
            except BaseException:
                if state.auth_client is not None:
                    try:
                        await self._close(state, state.auth_client)
                    finally:
                        if not state.unavailable:
                            state.auth_client = None
                raise
            finally:
                if state.auth_client is not None and not state.auth_client.is_connected:
                    state.auth_client = None


session_clients = SessionClients()
