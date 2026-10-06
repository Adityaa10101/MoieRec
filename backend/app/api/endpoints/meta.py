"""
backend/app/api/endpoints/meta.py
==================================
Catalog metadata endpoints: /meta/filters
Returns real genres and decades from MovieLens catalog (movies with TMDB ID).
"""

from fastapi import APIRouter
from app.db.catalog import fetch_catalog_meta_filters
from app.schemas.movies import MetaFiltersResponse

router = APIRouter()


@router.get("/filters", response_model=MetaFiltersResponse, summary="Catalog metadata filters")
async def get_catalog_filters():
    """
    Returns available genre chips and decade chips with movie counts from the catalog.
    Only includes movies with valid TMDB IDs.
    """
    data = fetch_catalog_meta_filters()
    return MetaFiltersResponse(**data)
