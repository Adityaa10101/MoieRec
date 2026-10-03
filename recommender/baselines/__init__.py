"""Baseline recommender models for MoieRec."""

from recommender.baselines.popularity import (
    PopularityRecommender,
    PopularityVariant,
)

__all__ = [
    "PopularityRecommender",
    "PopularityVariant",
]
