"""
backend/app/db/tmdb_cache.py
=============================
SQLite cache for TMDB API responses.
TTL: 30 days for ok, 24h for error/not_found.
No pandas/pyarrow — stdlib sqlite3 only.
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings

TTL_OK_SECONDS = 30 * 24 * 3600
TTL_ERR_SECONDS = 24 * 3600

_conn: Optional[sqlite3.Connection] = None
_conn_path: Optional[str] = None


def _get_db_path() -> str:
    db_path = Path(settings.TMDB_CACHE_DB_PATH)
    if not db_path.is_absolute():
        db_path = Path(__file__).resolve().parent.parent.parent.parent / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)


def get_cache_conn() -> sqlite3.Connection:
    global _conn, _conn_path
    path = _get_db_path()
    if _conn is None or _conn_path != path:
        _conn = sqlite3.connect(path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS tmdb_cache (
                tmdb_id    INTEGER PRIMARY KEY,
                payload    TEXT,
                fetched_at INTEGER NOT NULL,
                status     TEXT    NOT NULL
            )
        """)
        _conn.commit()
        _conn_path = path
    return _conn


def _set_test_conn(conn: sqlite3.Connection) -> None:
    """Override the cache connection for testing."""
    global _conn, _conn_path
    _conn = conn
    _conn_path = "__test__"


def cache_get(tmdb_id: int) -> Optional[dict]:
    conn = get_cache_conn()
    cur = conn.execute(
        "SELECT payload, fetched_at, status FROM tmdb_cache WHERE tmdb_id = ?",
        (tmdb_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None

    status = row["status"]
    fetched_at = row["fetched_at"]
    now = int(time.time())
    ttl = TTL_OK_SECONDS if status == "ok" else TTL_ERR_SECONDS

    if now - fetched_at > ttl:
        return None

    if status != "ok":
        return {"_status": status}

    try:
        payload = json.loads(row["payload"])
    except (json.JSONDecodeError, TypeError):
        return None

    if payload.get("adult", False):
        return {"_status": "adult_filtered"}

    return payload


def cache_put(tmdb_id: int, payload: Optional[dict], status: str) -> None:
    conn = get_cache_conn()
    payload_str = json.dumps(payload) if payload is not None else None
    conn.execute(
        """
        INSERT INTO tmdb_cache (tmdb_id, payload, fetched_at, status)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(tmdb_id) DO UPDATE SET
            payload    = excluded.payload,
            fetched_at = excluded.fetched_at,
            status     = excluded.status
        """,
        (tmdb_id, payload_str, int(time.time()), status),
    )
    conn.commit()


def cache_stats() -> dict:
    conn = get_cache_conn()
    cur = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM tmdb_cache GROUP BY status"
    )
    return {r["status"]: r["cnt"] for r in cur.fetchall()}
