"""
backend/app/services/tmdb.py
==============================
TMDB v3 API client with:
- Lazy fetch on cache miss
- Exponential backoff on 429/5xx (honours Retry-After)
- Concurrency limit of 8
- Image URLs built at response time (paths stored, not full URLs)
- Adult content filtered
- Graceful degradation: returns None if TMDB is unreachable
"""

import asyncio
import logging
import time
from typing import Optional

import httpx

from app.core.config import settings
from app.db.tmdb_cache import cache_get, cache_put

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.themoviedb.org/3"
_SEMAPHORE: Optional[asyncio.Semaphore] = None
_TMDB_CONFIG: Optional[dict] = None  # cached /configuration response

# Image sizes per spec
_POSTER_CARD_SIZE = "w342"
_POSTER_DETAIL_SIZE = "w500"
_BACKDROP_CARD_SIZE = "w780"
_BACKDROP_HERO_SIZE = "w1280"

_MAX_RETRIES = 4
_BACKOFF_BASE = 1.0  # seconds


def _get_semaphore() -> asyncio.Semaphore:
    global _SEMAPHORE
    if _SEMAPHORE is None:
        _SEMAPHORE = asyncio.Semaphore(8)
    return _SEMAPHORE


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=_BASE_URL,
        params={"api_key": settings.TMDB_API_KEY},
        timeout=httpx.Timeout(10.0),
        headers={"Accept": "application/json"},
    )


async def _fetch_with_retry(client: httpx.AsyncClient, path: str, params: dict = None) -> Optional[dict]:
    """Fetch a TMDB endpoint with exponential back-off on 429/5xx."""
    for attempt in range(_MAX_RETRIES):
        try:
            resp = await client.get(path, params=params or {})
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                return None  # caller treats as not_found
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", _BACKOFF_BASE * (2 ** attempt)))
                logger.warning("TMDB 429 on %s, waiting %.1fs", path, retry_after)
                await asyncio.sleep(retry_after)
                continue
            if resp.status_code >= 500:
                delay = _BACKOFF_BASE * (2 ** attempt)
                logger.warning("TMDB %d on %s, retry in %.1fs", resp.status_code, path, delay)
                await asyncio.sleep(delay)
                continue
            # Other 4xx: don't retry
            logger.warning("TMDB %d on %s", resp.status_code, path)
            return None
        except httpx.TimeoutException:
            delay = _BACKOFF_BASE * (2 ** attempt)
            logger.warning("TMDB timeout on %s (attempt %d), retry in %.1fs", path, attempt + 1, delay)
            await asyncio.sleep(delay)
        except httpx.RequestError as exc:
            logger.warning("TMDB request error on %s: %s", path, exc)
            raise
    return None


async def _get_tmdb_config(client: httpx.AsyncClient) -> Optional[dict]:
    global _TMDB_CONFIG
    if _TMDB_CONFIG is not None:
        return _TMDB_CONFIG
    data = await _fetch_with_retry(client, "/configuration")
    if data:
        _TMDB_CONFIG = data
    return _TMDB_CONFIG


DEFAULT_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"


def get_cached_image_base_url() -> str:
    """Return secure_base_url from cached TMDB /configuration, or fallback constant."""
    global _TMDB_CONFIG
    if _TMDB_CONFIG and "images" in _TMDB_CONFIG:
        return _TMDB_CONFIG["images"].get("secure_base_url") or DEFAULT_IMAGE_BASE_URL
    return DEFAULT_IMAGE_BASE_URL


def build_tmdb_image_url(
    file_path: Optional[str],
    size: str,
    base_url: Optional[str] = None,
) -> Optional[str]:
    """
    Build a full TMDB image URL from file_path and size.

    - Resolves base URL from provided base_url, cached /configuration, or DEFAULT_IMAGE_BASE_URL fallback.
    - Handles file_path with or without leading '/'.
    - Handles size with or without leading/trailing '/'.
    - Avoids accidental double slashes.
    - Returns None if file_path is None or empty.
    """
    if not file_path or not str(file_path).strip():
        return None

    resolved_base = (base_url or get_cached_image_base_url() or DEFAULT_IMAGE_BASE_URL).strip()
    if not resolved_base:
        resolved_base = DEFAULT_IMAGE_BASE_URL

    # Ensure base ends with a single slash, e.g. "https://image.tmdb.org/t/p/"
    resolved_base = resolved_base.rstrip("/") + "/"

    clean_size = str(size).strip().strip("/")
    clean_path = str(file_path).strip().lstrip("/")

    if not clean_path:
        return None

    return f"{resolved_base}{clean_size}/{clean_path}"


# Backward compatibility alias
_build_image_url = build_tmdb_image_url


def _extract_payload(data: dict, config: Optional[dict]) -> dict:
    """
    Extract only the fields we store/return from a full TMDB movie response.
    Never stores adult=True movies.
    """
    base_url = ""
    if config and "images" in config:
        base_url = config["images"].get("secure_base_url", "")

    # Cast: top 8 billed
    cast_raw = (data.get("credits") or {}).get("cast") or []
    cast = [
        {"name": c.get("name"), "character": c.get("character"),
         "profile_path": c.get("profile_path")}
        for c in sorted(cast_raw, key=lambda x: x.get("order", 999))[:8]
    ]

    # Director(s)
    crew_raw = (data.get("credits") or {}).get("crew") or []
    directors = [c.get("name") for c in crew_raw if c.get("job") == "Director"]

    poster_path = data.get("poster_path")
    backdrop_path = data.get("backdrop_path")

    return {
        "tmdb_id": data.get("id"),
        "title": data.get("title"),
        "overview": data.get("overview"),
        "tagline": data.get("tagline"),
        "release_date": data.get("release_date"),
        "runtime": data.get("runtime"),
        "genres": [g["name"] for g in (data.get("genres") or [])],
        "vote_average": data.get("vote_average"),
        "vote_count": data.get("vote_count"),
        "poster_path": poster_path,
        "backdrop_path": backdrop_path,
        "cast": cast,
        "directors": directors,
        "adult": data.get("adult", False),
        "original_language": data.get("original_language"),
        # Image URLs built at storage time from config (stored as paths above,
        # re-built from paths at response time — see build_image_urls)
        "_image_base_url": base_url,
    }


def build_image_urls(payload: dict, size_poster: str = _POSTER_CARD_SIZE,
                     size_backdrop: str = _BACKDROP_CARD_SIZE) -> dict:
    """Build full image URLs from stored paths + base_url."""
    base_url = payload.get("_image_base_url") or get_cached_image_base_url()
    result = dict(payload)
    result["poster_url"] = build_tmdb_image_url(payload.get("poster_path"), size_poster, base_url=base_url)
    result["backdrop_url"] = build_tmdb_image_url(payload.get("backdrop_path"), size_backdrop, base_url=base_url)
    return result


async def get_tmdb_data(tmdb_id: int) -> Optional[dict]:
    """
    Return TMDB metadata for a movie. Uses cache; fetches on miss.
    Returns None if TMDB is unreachable (graceful degradation).
    Returns the cached sentinel dict for known not_found/error.
    Adult content is filtered.
    """
    # Check cache first (sync)
    cached = cache_get(tmdb_id)
    if cached is not None:
        if cached.get("_status") in ("not_found", "error", "adult_filtered"):
            return None
        return cached

    # Cache miss — fetch from TMDB
    sem = _get_semaphore()
    async with sem:
        # Double-check under semaphore (another coroutine may have fetched it)
        cached = cache_get(tmdb_id)
        if cached is not None:
            if cached.get("_status") in ("not_found", "error", "adult_filtered"):
                return None
            return cached

        try:
            async with _build_client() as client:
                config = await _get_tmdb_config(client)
                data = await _fetch_with_retry(
                    client,
                    f"/movie/{tmdb_id}",
                    params={"append_to_response": "credits"},
                )

                if data is None:
                    cache_put(tmdb_id, None, "not_found")
                    return None

                # Filter adult
                if data.get("adult", False):
                    cache_put(tmdb_id, None, "not_found")
                    logger.info("Filtered adult movie tmdb_id=%d", tmdb_id)
                    return None

                payload = _extract_payload(data, config)
                cache_put(tmdb_id, payload, "ok")
                return payload

        except Exception as exc:
            logger.error("TMDB fetch error for tmdb_id=%d: %s", tmdb_id, exc)
            cache_put(tmdb_id, None, "error")
            return None  # Graceful degradation
