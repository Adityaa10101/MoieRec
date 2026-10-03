"""
backend/app/scripts/warm_tmdb_cache.py
========================================
Warm the TMDB cache with the top-N movies by train_positive_count.

Features:
- Concurrency 4 with asyncio.Semaphore(4)
- Reuses ONE httpx.AsyncClient with keep-alive
- Exponential backoff with random jitter on 429/5xx and network errors
- Resumable (skips entries already 'ok' or 'not_found')
- Optional --retry-errors flag to re-attempt 'error' entries regardless of TTL
- Summary counting failures by type (connect error, TLS reset, timeout, 429, 5xx)
- Circuit-breaker / early stopping if error rate persists above 5% (avoids infinite loops)

Usage:
    python -m app.scripts.warm_tmdb_cache --top 3000 --retry-errors
    python -m app.scripts.warm_tmdb_cache --top 6000
"""

import argparse
import asyncio
import random
import ssl
import sys
import time
from pathlib import Path
from typing import Optional

# Ensure backend package is importable when run from project root
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import httpx

from app.core.config import settings
from app.db.catalog import fetch_top_n_tmdb_ids
from app.db.tmdb_cache import cache_put, cache_stats, get_cache_conn
from app.services.tmdb import (
    DEFAULT_IMAGE_BASE_URL,
    _extract_payload,
)

BASE_URL = "https://api.themoviedb.org/3"
CONCURRENCY = 4
MAX_RETRIES = 3
BASE_DELAY = 0.5
MAX_JITTER = 0.3
ERROR_RATE_THRESHOLD = 0.05
MIN_ATTEMPTS_BEFORE_CHECK = 30


async def fetch_configuration(client: httpx.AsyncClient) -> Optional[dict]:
    """Fetch TMDB /configuration to get image base URLs."""
    try:
        resp = await client.get("/configuration")
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def classify_failure(exc: Exception, failure_counts: dict) -> str:
    """Classify exception into failure category."""
    exc_str = str(exc).lower()
    if isinstance(exc, (ConnectionResetError, ssl.SSLError)) or "reset" in exc_str or "10054" in exc_str:
        failure_counts["tls_reset"] += 1
        return "tls_reset"
    elif isinstance(exc, httpx.TimeoutException):
        failure_counts["timeout"] += 1
        return "timeout"
    elif isinstance(exc, httpx.ConnectError) or isinstance(exc, OSError):
        failure_counts["connect_error"] += 1
        return "connect_error"
    else:
        failure_counts["connect_error"] += 1
        return "connect_error"


async def fetch_movie(
    client: httpx.AsyncClient,
    tmdb_id: int,
    config: Optional[dict],
    semaphore: asyncio.Semaphore,
    failure_counts: dict,
) -> tuple[int, str]:
    """
    Fetch movie metadata with backoff and jitter.
    Returns (tmdb_id, status) where status is 'ok', 'not_found', or 'error'.
    """
    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                resp = await client.get(
                    f"/movie/{tmdb_id}",
                    params={"append_to_response": "credits"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("adult", False):
                        cache_put(tmdb_id, None, "not_found")
                        return tmdb_id, "not_found"
                    payload = _extract_payload(data, config)
                    cache_put(tmdb_id, payload, "ok")
                    return tmdb_id, "ok"
                elif resp.status_code == 404:
                    cache_put(tmdb_id, None, "not_found")
                    return tmdb_id, "not_found"
                elif resp.status_code == 429:
                    failure_counts["429"] += 1
                    retry_header = resp.headers.get("Retry-After")
                    delay = float(retry_header) if retry_header else (BASE_DELAY * (2 ** attempt) + random.uniform(0, MAX_JITTER))
                    await asyncio.sleep(delay)
                    continue
                elif resp.status_code >= 500:
                    failure_counts["5xx"] += 1
                    delay = BASE_DELAY * (2 ** attempt) + random.uniform(0, MAX_JITTER)
                    await asyncio.sleep(delay)
                    continue
                else:
                    cache_put(tmdb_id, None, "error")
                    failure_counts["other"] += 1
                    return tmdb_id, "error"
            except Exception as exc:
                classify_failure(exc, failure_counts)
                delay = BASE_DELAY * (2 ** attempt) + random.uniform(0, MAX_JITTER)
                await asyncio.sleep(delay)

        # Retries exhausted
        cache_put(tmdb_id, None, "error")
        return tmdb_id, "error"


async def warm(top_n: int, retry_errors: bool = False) -> None:
    print(f"=== Starting TMDB Cache Warm-Up ===")
    print(f"  Target: top {top_n} movies by popularity")
    print(f"  Retry errors: {retry_errors}")
    print(f"  Concurrency: {CONCURRENCY}")

    all_tmdb_ids = fetch_top_n_tmdb_ids(top_n)
    total_candidates = len(all_tmdb_ids)
    print(f"  Found {total_candidates} candidate tmdb_ids in catalog")

    # Read current cache state
    cache_conn = get_cache_conn()
    existing_cache = {
        r["tmdb_id"]: r["status"]
        for r in cache_conn.execute("SELECT tmdb_id, status FROM tmdb_cache").fetchall()
    }

    # Determine which tmdb_ids to fetch
    to_fetch: list[int] = []
    already_ok = 0
    already_not_found = 0
    already_error = 0

    for tid in all_tmdb_ids:
        status = existing_cache.get(tid)
        if status == "ok":
            already_ok += 1
        elif status == "not_found":
            already_not_found += 1
        elif status == "error":
            already_error += 1
            if retry_errors:
                to_fetch.append(tid)
        else:
            to_fetch.append(tid)

    print(f"  Current cache for top {top_n}:")
    print(f"    Already OK:        {already_ok}")
    print(f"    Already Not Found: {already_not_found}")
    print(f"    Already Error:     {already_error}")
    print(f"  Pending fetch:       {len(to_fetch)} movies")

    if not to_fetch:
        print("\nAll target entries are already satisfied in cache. Nothing to fetch.")
        stats = cache_stats()
        print(f"Cache totals: {stats}")
        return

    # Client setup: reuse ONE httpx.AsyncClient with keep-alive
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=10, keepalive_expiry=30.0)
    timeout = httpx.Timeout(10.0, connect=5.0)

    failure_counts = {
        "connect_error": 0,
        "tls_reset": 0,
        "timeout": 0,
        "429": 0,
        "5xx": 0,
        "other": 0,
    }

    start_time = time.time()
    ok_count = 0
    not_found_count = 0
    error_count = 0
    halted_early = False

    semaphore = asyncio.Semaphore(CONCURRENCY)

    async with httpx.AsyncClient(
        base_url=BASE_URL,
        params={"api_key": settings.TMDB_API_KEY},
        headers=headers,
        limits=limits,
        timeout=timeout,
    ) as client:
        config = await fetch_configuration(client)

        batch_size = 20
        total_to_fetch = len(to_fetch)

        for i in range(0, total_to_fetch, batch_size):
            batch = to_fetch[i : i + batch_size]
            results = await asyncio.gather(
                *[fetch_movie(client, tid, config, semaphore, failure_counts) for tid in batch]
            )

            for tid, status in results:
                if status == "ok":
                    ok_count += 1
                elif status == "not_found":
                    not_found_count += 1
                else:
                    error_count += 1

            done = min(i + batch_size, total_to_fetch)
            elapsed = time.time() - start_time
            rate = done / elapsed if elapsed > 0 else 0.0
            pct = done / total_to_fetch * 100.0

            print(
                f"\r  [{done:>5}/{total_to_fetch}] {pct:5.1f}%  "
                f"ok={ok_count} not_found={not_found_count} error={error_count}  "
                f"{rate:.1f} req/s",
                end="",
                flush=True,
            )

            # Check early termination condition if errors persist above ~5%
            attempted = ok_count + not_found_count + error_count
            if attempted >= MIN_ATTEMPTS_BEFORE_CHECK:
                err_ratio = error_count / attempted
                if err_ratio > ERROR_RATE_THRESHOLD and error_count >= 25:
                    print(f"\n\n[NOTICE] Error rate is {err_ratio*100:.1f}% (above {ERROR_RATE_THRESHOLD*100:.0f}% threshold).")
                    print("Stopping early to avoid infinite retry loops as requested.")
                    halted_early = True
                    break

    elapsed = time.time() - start_time
    print()
    print()
    print("=== Warm-Up Execution Summary ===")
    print(f"  Runtime:         {elapsed:.1f}s")
    print(f"  Processed:       {ok_count + not_found_count + error_count} of {total_to_fetch}")
    print(f"  OK (success):    {ok_count}")
    print(f"  Not Found (404): {not_found_count}")
    print(f"  Errors:          {error_count}")
    print(f"  Halted early:    {halted_early}")
    print()
    print("=== Failures by Type ===")
    print(f"  Connect Errors:  {failure_counts['connect_error']}")
    print(f"  TLS Resets:      {failure_counts['tls_reset']}")
    print(f"  Timeouts:        {failure_counts['timeout']}")
    print(f"  HTTP 429:        {failure_counts['429']}")
    print(f"  HTTP 5xx:        {failure_counts['5xx']}")
    print(f"  Other:           {failure_counts['other']}")
    print()
    stats = cache_stats()
    print(f"=== Total Cache DB Contents ===")
    print(f"  {stats}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Warm TMDB cache")
    parser.add_argument("--top", type=int, default=3000,
                        help="Number of top-popular movies to process (default: 3000)")
    parser.add_argument("--retry-errors", action="store_true", default=False,
                        help="Retry entries with status='error' regardless of TTL")
    args = parser.parse_args()
    asyncio.run(warm(args.top, retry_errors=args.retry_errors))


if __name__ == "__main__":
    main()
