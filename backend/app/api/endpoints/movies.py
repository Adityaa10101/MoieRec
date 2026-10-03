"""
backend/app/api/endpoints/movies.py
=====================================
Movie API endpoints: /home, /movies/popular, /movies/{id}, /search
All responses use MovieOut schema with honesty contract.
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.db.catalog import (
    fetch_hero,
    fetch_movie,
    fetch_popular,
    search_movies,
)
from app.schemas.movies import CastMember, HomeResponse, MovieOut, RecommendationRow
from app.services.tmdb import (
    _BACKDROP_HERO_SIZE,
    _POSTER_CARD_SIZE,
    _POSTER_DETAIL_SIZE,
    _BACKDROP_CARD_SIZE,
    build_image_urls,
    get_tmdb_data,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _enrich(catalog_row: dict, rank: int = None,
                  poster_size: str = _POSTER_CARD_SIZE,
                  backdrop_size: str = _BACKDROP_CARD_SIZE) -> MovieOut:
    """
    Merge catalog row with TMDB data (if available) into MovieOut.
    Gracefully handles missing TMDB data.
    """
    tmdb_id = catalog_row.get("tmdb_id")
    tmdb = None
    if tmdb_id:
        tmdb = await get_tmdb_data(int(tmdb_id))

    if tmdb:
        enriched = build_image_urls(tmdb, size_poster=poster_size, size_backdrop=backdrop_size)
        cast = [CastMember(name=c.get("name", ""), character=c.get("character"))
                for c in enriched.get("cast", [])]
        return MovieOut(
            movie_id=catalog_row["movie_id"],
            tmdb_id=tmdb_id,
            title=catalog_row["title_display"],
            year=catalog_row.get("year"),
            genres=catalog_row["genres"] or enriched.get("genres", []),
            overview=enriched.get("overview") or None,
            poster_url=enriched.get("poster_url"),
            backdrop_url=enriched.get("backdrop_url"),
            runtime=enriched.get("runtime"),
            vote_average=enriched.get("vote_average"),
            tagline=enriched.get("tagline"),
            cast=cast,
            directors=enriched.get("directors", []),
            train_positive_count=catalog_row.get("train_positive_count"),
            rank=rank,
        )
    else:
        # TMDB unavailable — return catalog-only data
        return MovieOut(
            movie_id=catalog_row["movie_id"],
            tmdb_id=tmdb_id,
            title=catalog_row["title_display"],
            year=catalog_row.get("year"),
            genres=catalog_row["genres"],
            train_positive_count=catalog_row.get("train_positive_count"),
            rank=rank,
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/home", response_model=HomeResponse, summary="Home page data")
async def get_home():
    """
    Returns hero movie and curated rows.
    All rows are ordered by popularity (train_positive_count) — Model 0.
    No personalization.
    """
    # Hero: top popular movie that has a valid backdrop (and poster)
    hero_movie = None
    hero_candidates = fetch_popular(limit=50)
    for candidate in hero_candidates:
        enriched = await _enrich(
            candidate,
            rank=1,
            poster_size=_POSTER_DETAIL_SIZE,
            backdrop_size=_BACKDROP_HERO_SIZE,
        )
        if enriched.backdrop_url:
            hero_movie = enriched
            break

    # Rows config — honest labels per spec
    row_configs = [
        {
            "id": "row-popular",
            "title": "Popular with MovieLens Viewers",
            "subtitle": "Most-liked films among MovieLens viewers",
            "genre": None,
            "decade": None,
        },
        {
            "id": "row-scifi",
            "title": "Top in Sci-Fi",
            "subtitle": "Highest-rated science fiction films by MovieLens audience",
            "genre": "Sci-Fi",
            "decade": None,
        },
        {
            "id": "row-drama",
            "title": "Top in Drama",
            "subtitle": "Most-liked drama films among MovieLens viewers",
            "genre": "Drama",
            "decade": None,
        },
        {
            "id": "row-2010s",
            "title": "Top of the 2010s",
            "subtitle": "Most-liked films from the 2010s decade on MovieLens",
            "genre": None,
            "decade": 2010,
        },
        {
            "id": "row-1990s",
            "title": "Top of the 1990s",
            "subtitle": "Most-liked films from the 1990s decade on MovieLens",
            "genre": None,
            "decade": 1990,
        },
    ]

    TARGET_ROW_COUNT = 20
    CHUNK_SIZE = 40
    MAX_SCAN = 500

    rows = []
    for cfg in row_configs:
        selected_movies: list[MovieOut] = []
        offset = 0
        while len(selected_movies) < TARGET_ROW_COUNT and offset < MAX_SCAN:
            catalog_rows = fetch_popular(
                limit=CHUNK_SIZE,
                offset=offset,
                genre=cfg.get("genre"),
                decade=cfg.get("decade"),
            )
            if not catalog_rows:
                break

            enriched_batch = await asyncio.gather(
                *[_enrich(r) for r in catalog_rows]
            )

            for m in enriched_batch:
                # Include only movies that have a TMDB poster_path (poster_url)
                if m.poster_url:
                    m_dict = m.model_dump()
                    m_dict["rank"] = len(selected_movies) + 1
                    selected_movies.append(MovieOut(**m_dict))
                    if len(selected_movies) == TARGET_ROW_COUNT:
                        break

            offset += CHUNK_SIZE

        rows.append(RecommendationRow(
            id=cfg["id"],
            title=cfg["title"],
            subtitle=cfg["subtitle"],
            movies=selected_movies,
        ))

    return HomeResponse(hero=hero_movie, rows=rows)


@router.get("/movies/popular", response_model=list[MovieOut], summary="Popular movies")
async def get_popular(
    genre: Optional[str] = Query(None, description="Filter by genre name"),
    decade: Optional[int] = Query(None, description="Filter by decade start year (e.g. 2010)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Returns movies ordered by popularity (train_positive_count). No personalization."""
    import asyncio
    catalog_rows = fetch_popular(limit=limit, offset=offset, genre=genre, decade=decade)
    movies = await asyncio.gather(
        *[_enrich(r, rank=offset + i + 1) for i, r in enumerate(catalog_rows)]
    )
    return list(movies)


@router.get("/movies/{movie_id}", response_model=MovieOut, summary="Movie detail")
async def get_movie_detail(movie_id: int):
    """Full movie detail with TMDB enrichment. No taste-match numbers."""
    catalog_row = fetch_movie(movie_id)
    if catalog_row is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return await _enrich(
        catalog_row,
        poster_size=_POSTER_DETAIL_SIZE,
        backdrop_size=_BACKDROP_HERO_SIZE,
    )


@router.get("/search", response_model=list[MovieOut], summary="Search movies by title")
async def search(
    q: str = Query(..., min_length=2, description="Search query (min 2 chars)"),
    limit: int = Query(10, ge=1, le=50),
):
    """
    Normalized prefix/substring title match ranked by popularity.
    Minimum 2 characters. No fake match scores.
    """
    import asyncio
    catalog_rows = search_movies(q=q, limit=limit)
    movies = await asyncio.gather(
        *[_enrich(r, rank=i + 1) for i, r in enumerate(catalog_rows)]
    )
    return list(movies)
