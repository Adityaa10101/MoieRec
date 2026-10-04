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

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CastMember(BaseModel):
    name: str
    character: Optional[str] = None


class NearestPickExplanation(BaseModel):
    movie_id: int
    title: str
    similarity: float


class SharedFeatureExplanation(BaseModel):
    feature: str
    raw_name: str
    contribution: float
    feature_type: str


class ComponentsExplanation(BaseModel):
    content: float
    popularity: float
    cf: Optional[float] = None


class CfPickExplanation(BaseModel):
    movie_id: int
    title: str
    similarity: float
    cooccurrence: int


class ExplanationOut(BaseModel):
    nearest_pick: NearestPickExplanation
    top_shared_features: List[SharedFeatureExplanation] = Field(default_factory=list)
    components: ComponentsExplanation
    match_percent: int
    similarity_threshold: Optional[float] = None
    alpha: Optional[float] = None
    weights: Optional[Dict[str, float]] = None
    cf_pick: Optional[CfPickExplanation] = None
    reason_labels: Optional[dict[str, str]] = None


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

    # Ranking & personalization fields
    rank: Optional[int] = None                   # position in this response's list
    score: Optional[float] = None                # personalized score or cosine
    match_percent: Optional[int] = None          # relative rank among candidate pool (0-100), NOT a probability
    reason_codes: List[str] = Field(default_factory=list)   # reason codes derived from evidence
    explanation: Optional[ExplanationOut] = None # structured explainability evidence
    source: str = "popularity"                   # "hybrid_v1", "content_similarity", or "popularity"

    model_config = {"from_attributes": True}


class RecommendationRow(BaseModel):
    id: str
    title: str
    subtitle: str
    movies: List[MovieOut]


class HomeResponse(BaseModel):
    hero: Optional[MovieOut] = None
    rows: List[RecommendationRow] = Field(default_factory=list)


class PersonalizedHomeRequest(BaseModel):
    liked_movie_ids: List[int] = Field(..., max_length=50, description="Max 50 liked MovieLens movie_ids")
    exclude_movie_ids: Optional[List[int]] = Field(default_factory=list, description="MovieLens movie_ids to exclude (disliked, etc.)")


class PersonalizedHomeResponse(BaseModel):
    personalized: bool
    k: int
    config_version: str
    alpha_used: Optional[float] = None
    weights_used: Optional[Dict[str, float]] = None
    ignored_ids: List[int] = Field(default_factory=list)
    message: Optional[str] = None
    rows: List[RecommendationRow] = Field(default_factory=list)
