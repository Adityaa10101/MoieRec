"""
backend/app/api/endpoints/personalized.py
=========================================
Personalized home feed endpoint: POST /api/personalized/home
Stateless guest flow based on liked movie_ids in request body.
"""

import asyncio
import logging
from typing import List

from fastapi import APIRouter, HTTPException

from app.db.catalog import fetch_movie
from app.schemas.movies import (
    ExplanationOut,
    MovieOut,
    PersonalizedHomeRequest,
    PersonalizedHomeResponse,
    RecommendationRow,
)
from app.services.hybrid_service import get_hybrid_scorer
from app.api.endpoints.movies import _enrich

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/home", response_model=PersonalizedHomeResponse, summary="Personalized home feed")
async def get_personalized_home(request: PersonalizedHomeRequest):
    """
    Stateless personalized recommendation feed based on picked movies.
    - Requires at least 3 valid liked movie_ids.
    - If < 3 valid likes: returns personalized=False with explanatory message and empty rows.
    - If >= 3 valid likes:
        - Row 1: 'Picked for You' (hybrid content + popularity, 20 items with TMDB posters)
        - Up to 2 rows: 'Because you liked <Title>' (content-only neighbors for recent picks)
    - Excluded items (disliked, etc.) and liked items are never recommended.
    - Strict input validation; logs only counts of picks.
    """
    # Strict privacy: log only counts, never user picks
    n_liked = len(request.liked_movie_ids)
    n_excl = len(request.exclude_movie_ids) if request.exclude_movie_ids else 0
    logger.info(f"Personalized feed requested: {n_liked} liked IDs, {n_excl} excluded IDs")

    scorer = get_hybrid_scorer()

    # Identify valid vs unknown/ignored IDs
    valid_liked: List[int] = []
    ignored_ids: List[int] = []
    for mid in request.liked_movie_ids:
        if scorer.is_valid_movie_id(mid):
            if mid not in valid_liked:
                valid_liked.append(mid)
        else:
            ignored_ids.append(mid)

    # If fewer than 3 valid liked items, do not personalize
    if len(valid_liked) < 3:
        return PersonalizedHomeResponse(
            personalized=False,
            k=len(valid_liked),
            config_version=scorer.version,
            ignored_ids=ignored_ids,
            message="At least 3 valid liked movies are required for personalized recommendations.",
            rows=[],
        )

    # 1. Row 'Picked for You' (Hybrid Model)
    TARGET_COUNT = 20
    k_liked = len(valid_liked)
    if scorer.is_v2:
        w_c, w_f, w_p = scorer.get_weights(k_liked)
        weights_used = {"w_c": round(w_c, 2), "w_f": round(w_f, 2), "w_p": round(w_p, 2)}
        alpha_used = w_c
    else:
        alpha_used = scorer.get_alpha(k_liked)
        weights_used = None

    # Request a generous candidate pool from scorer to ensure backfill has 20 items with TMDB posters
    scored_candidates, _ = scorer.score(
        liked_movie_ids=valid_liked,
        exclude_movie_ids=request.exclude_movie_ids,
        top_k=100,
    )

    picked_movies: List[MovieOut] = []
    for cand in scored_candidates:
        mid = cand["movie_id"]
        catalog_row = fetch_movie(mid)
        if not catalog_row:
            continue

        enriched = await _enrich(catalog_row, rank=len(picked_movies) + 1)
        # Include only movies that have a TMDB poster
        if enriched.poster_url:
            m_dict = enriched.model_dump()
            m_dict["score"] = cand["score"]
            m_dict["match_percent"] = cand["match_percent"]
            m_dict["reason_codes"] = cand["reason_codes"]
            m_dict["explanation"] = cand["explanation"]
            m_dict["source"] = cand.get("source", "hybrid_v2" if scorer.is_v2 else "hybrid_v1.1")
            picked_movies.append(MovieOut(**m_dict))
            if len(picked_movies) == TARGET_COUNT:
                break

    rows: List[RecommendationRow] = [
        RecommendationRow(
            id="row-personalized-picked",
            title="Picked for You",
            subtitle=f"Scored from your picks using collaborative filtering{' and content similarity' if len(valid_liked) >= 15 else ''}",
            movies=picked_movies,
        )
    ]

    # 2. Up to 2 rows: 'Because you liked <title>' for most recent liked IDs by request order
    # Most recent picks are at the end of the request order
    recent_liked_mids: List[int] = []
    for mid in reversed(valid_liked):
        if mid not in recent_liked_mids:
            recent_liked_mids.append(mid)
        if len(recent_liked_mids) == 2:
            break

    for ref_mid in recent_liked_mids:
        ref_title = scorer.get_title(ref_mid)
        sim_cands = scorer.similar_items(ref_mid, n=80)

        sim_movies: List[MovieOut] = []
        for c in sim_cands:
            # Do not recommend items the user already liked or excluded
            c_mid = c["movie_id"]
            if c_mid in valid_liked or (request.exclude_movie_ids and c_mid in request.exclude_movie_ids):
                continue

            catalog_row = fetch_movie(c_mid)
            if not catalog_row:
                continue

            enriched = await _enrich(catalog_row, rank=len(sim_movies) + 1)
            if enriched.poster_url:
                m_dict = enriched.model_dump()
                m_dict["score"] = c["score"]
                m_dict["source"] = "content_similarity"
                sim_movies.append(MovieOut(**m_dict))
                if len(sim_movies) == TARGET_COUNT:
                    break

        if sim_movies:
            rows.append(
                RecommendationRow(
                    id=f"row-because-liked-{ref_mid}",
                    title=f"Because you liked {ref_title}",
                    subtitle="Similar by genres and tags",
                    movies=sim_movies,
                )
            )

    return PersonalizedHomeResponse(
        personalized=True,
        k=len(valid_liked),
        config_version=scorer.version,
        alpha_used=alpha_used,
        weights_used=weights_used,
        ignored_ids=ignored_ids,
        rows=rows,
    )
