"""
backend/app/db/catalog.py
==========================
Thin wrapper around data/serving/catalog.sqlite using stdlib sqlite3.
No pandas/pyarrow in the backend.
"""

import json
import sqlite3
import unicodedata
from pathlib import Path
from typing import Optional

from app.core.config import settings

# Module-level connection (recreated if DB path changes)
_conn: Optional[sqlite3.Connection] = None
_conn_path: Optional[str] = None


def _get_db_path() -> str:
    db_path = Path(settings.CATALOG_DB_PATH)
    if not db_path.is_absolute():
        # Resolve relative to project root (parent of the backend/ dir)
        db_path = Path(__file__).resolve().parent.parent.parent.parent / db_path
    return str(db_path)


def get_catalog_conn() -> sqlite3.Connection:
    """Return a cached connection to the catalog DB (check_same_thread=False)."""
    global _conn, _conn_path
    path = _get_db_path()
    if _conn is None or _conn_path != path:
        _conn = sqlite3.connect(path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn_path = path
    return _conn


def _set_test_conn(conn: sqlite3.Connection) -> None:
    """Override the connection for testing (no network, in-memory DB)."""
    global _conn, _conn_path
    _conn = conn
    _conn_path = "__test__"


def movie_row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row from the movies table to a plain dict."""
    d = dict(row)
    d["genres"] = json.loads(d.get("genres") or "[]")
    return d


def fetch_movie(movie_id: int) -> Optional[dict]:
    conn = get_catalog_conn()
    cur = conn.execute(
        "SELECT * FROM movies WHERE movie_id = ? AND tmdb_id IS NOT NULL",
        (movie_id,),
    )
    row = cur.fetchone()
    return movie_row_to_dict(row) if row else None


def fetch_movies_by_ids(movie_ids: list[int]) -> list[dict]:
    """Fetch multiple movies by their movie_id in one query. Only movies WITH a tmdb_id are returned."""
    if not movie_ids:
        return []
    conn = get_catalog_conn()
    placeholders = ",".join("?" for _ in movie_ids)
    cur = conn.execute(
        f"SELECT * FROM movies WHERE movie_id IN ({placeholders}) AND tmdb_id IS NOT NULL",
        movie_ids,
    )
    return [movie_row_to_dict(r) for r in cur.fetchall()]


def fetch_popular(
    limit: int = 20,
    offset: int = 0,
    genre: Optional[str] = None,
    decade: Optional[int] = None,
    year: Optional[int] = None,
    sort: Optional[str] = "popular",
) -> list[dict]:
    """
    Return movies ordered by train_positive_count DESC (or year DESC/ASC), with optional
    genre/decade/year filters. Only movies WITH a tmdb_id are returned.
    """
    where_clauses = ["tmdb_id IS NOT NULL"]
    params: list = []

    if genre:
        genre_list = [g.strip() for g in genre.split(",") if g.strip()]
        if genre_list:
            placeholders = ", ".join(["?"] * len(genre_list))
            where_clauses.append(
                f"EXISTS (SELECT 1 FROM json_each(genres) WHERE json_each.value IN ({placeholders}))"
            )
            params.extend(genre_list)

    if year is not None:
        where_clauses.append("year = ?")
        params.append(year)
    elif decade is not None:
        where_clauses.append("year >= ? AND year < ?")
        params.extend([decade, decade + 10])

    where_sql = " AND ".join(where_clauses)

    if sort == "newest":
        order_by_sql = """
            COALESCE(year, 0) DESC,
            COALESCE(train_positive_count, 0) DESC,
            (movie_id * 2654435761) & 0xFFFFFFFF ASC
        """
    elif sort == "oldest":
        order_by_sql = """
            COALESCE(year, 9999) ASC,
            COALESCE(train_positive_count, 0) DESC,
            (movie_id * 2654435761) & 0xFFFFFFFF ASC
        """
    else:
        order_by_sql = """
            COALESCE(train_positive_count, 0) DESC,
            (movie_id * 2654435761) & 0xFFFFFFFF ASC
        """

    params.extend([limit, offset])

    conn = get_catalog_conn()
    cur = conn.execute(
        f"""
        SELECT * FROM movies
        WHERE {where_sql}
        ORDER BY {order_by_sql}
        LIMIT ? OFFSET ?
        """,
        params,
    )
    return [movie_row_to_dict(r) for r in cur.fetchall()]


def fetch_catalog_meta_filters() -> dict:
    """Return genres and decades with movie counts from the catalog (only movies with a tmdb_id)."""
    conn = get_catalog_conn()
    cur = conn.execute(
        "SELECT genres FROM movies WHERE tmdb_id IS NOT NULL"
    )
    genre_counts: dict[str, int] = {}
    for (g_json,) in cur.fetchall():
        try:
            for g in json.loads(g_json or "[]"):
                if g and g not in ("IMAX", "(no genres listed)"):
                    genre_counts[g] = genre_counts.get(g, 0) + 1
        except Exception:
            continue

    sorted_genres = [
        {"name": g, "count": count}
        for g, count in sorted(genre_counts.items(), key=lambda x: -x[1])
    ]

    cur = conn.execute(
        """
        SELECT (year / 10) * 10 AS decade, COUNT(*) AS count
        FROM movies
        WHERE tmdb_id IS NOT NULL AND year IS NOT NULL AND year >= 1920
        GROUP BY decade
        ORDER BY decade DESC
        """
    )
    decades = [
        {"decade": int(r["decade"]), "label": f"{int(r['decade'])}s", "count": int(r["count"])}
        for r in cur.fetchall()
    ]

    return {
        "genres": sorted_genres,
        "decades": decades,
    }


def fetch_hero() -> Optional[dict]:
    """Top popular movie that has a tmdb_id."""
    conn = get_catalog_conn()
    cur = conn.execute(
        """
        SELECT * FROM movies
        WHERE tmdb_id IS NOT NULL
        ORDER BY COALESCE(train_positive_count, 0) DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    return movie_row_to_dict(row) if row else None


def search_movies(q: str, limit: int = 10) -> list[dict]:
    """Normalized prefix/substring title match ranked by popularity."""
    if len(q.strip()) < 2:
        return []

    nfkd = unicodedata.normalize("NFKD", q.lower())
    q_norm = "".join(c for c in nfkd if not unicodedata.combining(c))

    conn = get_catalog_conn()
    cur = conn.execute(
        """
        SELECT * FROM movies
        WHERE tmdb_id IS NOT NULL
          AND title_search LIKE ?
        ORDER BY
            CASE WHEN title_search LIKE ? THEN 0 ELSE 1 END,
            COALESCE(train_positive_count, 0) DESC
        LIMIT ?
        """,
        (f"%{q_norm}%", f"{q_norm}%", limit),
    )
    return [movie_row_to_dict(r) for r in cur.fetchall()]


def fetch_top_n_tmdb_ids(n: int) -> list[int]:
    """Return the top-N tmdb_ids by train_positive_count for cache warm-up."""
    conn = get_catalog_conn()
    cur = conn.execute(
        """
        SELECT tmdb_id FROM movies
        WHERE tmdb_id IS NOT NULL
        ORDER BY COALESCE(train_positive_count, 0) DESC
        LIMIT ?
        """,
        (n,),
    )
    return [r[0] for r in cur.fetchall()]
