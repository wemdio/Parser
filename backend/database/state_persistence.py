"""
Persist accounts.json + Telegram session files to Supabase so they survive
container rebuilds.

Timeweb Apps build a bare Dockerfile with NO persistent volume, so the
ephemeral `accounts.json` and `sessions/*.session` are wiped on every
rebuild/redeploy. Without this the parser loses its account + session and
message ingestion silently stops ("No connected accounts").

Design goal: zero risk to the working login/parsing code. We do NOT change
how sessions are created or how clients connect — we only MIRROR the
ephemeral files into a `parser_state` table and RESTORE them on boot.

Requires a one-time table (run in Supabase SQL editor):

    CREATE TABLE IF NOT EXISTS parser_state (
        key        text PRIMARY KEY,
        content    text NOT NULL,
        updated_at timestamptz NOT NULL DEFAULT now()
    );
    ALTER TABLE parser_state DISABLE ROW LEVEL SECURITY;

Everything here is best-effort: if the table is missing or Supabase is
unreachable, calls log and return without raising, so the parser keeps
running (just without persistence).
"""
import os
import sys
import base64
import glob
import sqlite3
import tempfile
from datetime import datetime, timezone

from supabase import create_client

SESSIONS_DIR = "sessions"
ACCOUNTS_FILE = "accounts.json"
TABLE = "parser_state"

_client = None


def _log(msg: str) -> None:
    print(f">>> [persist] {msg}", file=sys.stderr, flush=True)


def _get_client():
    global _client
    if _client is not None:
        return _client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        _log("SUPABASE_URL/KEY missing — persistence disabled")
        return None
    try:
        _client = create_client(url, key)
    except Exception as e:  # noqa: BLE001
        _log(f"client init failed: {e}")
        _client = None
    return _client


def _safe_phone(phone: str) -> str:
    return phone.replace("+", "").replace("-", "").replace(" ", "")


def _upsert(key: str, content: str) -> bool:
    c = _get_client()
    if not c:
        return False
    try:
        c.table(TABLE).upsert({
            "key": key,
            "content": content,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        return True
    except Exception as e:  # noqa: BLE001
        _log(f"upsert {key} failed: {e}")
        return False


def _sqlite_snapshot_bytes(path: str) -> bytes:
    """Consistent snapshot of a (possibly in-use) SQLite session file via the
    SQLite online-backup API, so we never capture a torn read."""
    fd, tmp = tempfile.mkstemp(suffix=".session")
    os.close(fd)
    try:
        src = sqlite3.connect(path)
        dst = sqlite3.connect(tmp)
        with dst:
            src.backup(dst)
        dst.close()
        src.close()
        with open(tmp, "rb") as f:
            return f.read()
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


# ── backup ───────────────────────────────────────────────────────────────

def backup_accounts() -> None:
    if not os.path.exists(ACCOUNTS_FILE):
        return
    try:
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            data = f.read()
    except Exception as e:  # noqa: BLE001
        _log(f"read {ACCOUNTS_FILE} failed: {e}")
        return
    if _upsert("accounts.json", data):
        _log("accounts.json backed up")


def backup_session(phone: str) -> None:
    safe = _safe_phone(phone)
    path = os.path.join(SESSIONS_DIR, f"{safe}.session")
    if not os.path.exists(path):
        return
    try:
        raw = _sqlite_snapshot_bytes(path)
        b64 = base64.b64encode(raw).decode("ascii")
    except Exception as e:  # noqa: BLE001
        _log(f"snapshot {safe} failed: {e}")
        return
    if _upsert(f"session:{safe}", b64):
        _log(f"session {safe} backed up ({len(raw)} bytes)")


def backup_all() -> None:
    backup_accounts()
    for path in glob.glob(os.path.join(SESSIONS_DIR, "*.session")):
        safe = os.path.basename(path)[: -len(".session")]
        backup_session(safe)


# ── restore ──────────────────────────────────────────────────────────────

def restore_all() -> None:
    """Restore accounts.json + every session file from Supabase. Call this on
    boot BEFORE the realtime service reads accounts / opens sessions."""
    c = _get_client()
    if not c:
        return
    try:
        rows = c.table(TABLE).select("key,content").execute().data or []
    except Exception as e:  # noqa: BLE001
        _log(f"restore query failed (table missing?): {e}")
        return
    if not rows:
        _log("no saved state in DB yet (first run)")
        return
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    restored = 0
    for row in rows:
        key = row.get("key") or ""
        content = row.get("content")
        if content is None:
            continue
        try:
            if key == "accounts.json":
                with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                    f.write(content)
                restored += 1
            elif key.startswith("session:"):
                safe = key.split(":", 1)[1]
                with open(os.path.join(SESSIONS_DIR, f"{safe}.session"), "wb") as f:
                    f.write(base64.b64decode(content))
                restored += 1
        except Exception as e:  # noqa: BLE001
            _log(f"restore {key} failed: {e}")
    _log(f"restored {restored} item(s) from DB")
