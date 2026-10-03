"""
backend/app/schemas/movies.py
==============================
Pydantic response models for all movie endpoints.
Honesty contract:
  - score: always null (no personalization yet)
  - match_percent: always null
  - reason_codes: always []
  - explanation: always null
  - source: always "popularity"
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class CastMember(BaseModel):
    name: str
    character: Optional[str] = None


class MovieOut(BaseModel):
    """Single movie in any API response."""
    movie_id: int
    tmdb_id: Optional[int] = None
    title: str
    year: Optional[int] = None
    genres: List[str] = Field(default_factory=list)

    # TMDB-enriched fields (null when TMDB unavailable)
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    runtime: Optional[int] = None                # minutes
    vote_average: Optional[float] = None         # TMDB score, labelled as such
    tagline: Optional[str] = None
    cast: List[CastMember] = Field(default_factory=list)
    directors: List[str] = Field(default_factory=list)

    # Popularity signal (from training data)
    train_positive_count: Optional[int] = None

    # Future-contract fields — honest null values now
    rank: Optional[int] = None                   # position in this response's list
    score: None = None                           # no personalized score
    match_percent: None = None                   # null — no personalization
    reason_codes: List[str] = Field(default_factory=list)   # empty — no explanation
    explanation: None = None                     # null — no explanation
    source: str = "popularity"                   # Model 0: popularity only

    model_config = {"from_attributes": True}


class RecommendationRow(BaseModel):
    id: str
    title: str
    subtitle: str
    movies: List[MovieOut]


class HomeResponse(BaseModel):
    hero: Optional[MovieOut] = None
    rows: List[RecommendationRow] = Field(default_factory=list)
