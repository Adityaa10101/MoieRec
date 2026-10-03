"""Popularity-based non-personalized baseline recommenders (Model 0).

Computed entirely from TRAIN data.
Implements three variants:
1. most_rated: score = train rating_count (v)
2. most_liked: score = train positive_rating_count (count of train ratings >= positive_threshold)
3. damped_mean: score = (v / (v + m)) * R + (m / (v + m)) * C
   where:
     v = movie train rating_count
     R = movie train mean rating
     C = global train mean rating
     m = damping hyperparameter
"""

from enum import Enum
from typing import Dict, Optional, Union
import numpy as np
import pandas as pd

from recommender.evaluation.protocol import Recommender


class PopularityVariant(str, Enum):
    MOST_RATED = "most_rated"
    MOST_LIKED = "most_liked"
    DAMPED_MEAN = "damped_mean"


class PopularityRecommender(Recommender):
    """Non-personalized popularity baseline recommender."""

    def __init__(
        self,
        variant: Union[str, PopularityVariant] = PopularityVariant.MOST_RATED,
        damping: float = 25.0,
        positive_threshold: float = 4.0,
    ):
        """Initialize popularity recommender.

        Args:
            variant: One of 'most_rated', 'most_liked', or 'damped_mean'.
            damping: Hyperparameter m for damped_mean variant.
            positive_threshold: Rating threshold defining positive feedback (used in most_liked).
        """
        self.variant = PopularityVariant(variant)
        self.damping = float(damping)
        self.positive_threshold = float(positive_threshold)
        self.item_scores: Optional[np.ndarray] = None
        self.candidate_movie_ids: Optional[np.ndarray] = None
        self.n_candidates: int = 0

    def fit(self, train_df: pd.DataFrame, context: Optional[dict] = None) -> "PopularityRecommender":
        """Compute popularity scores on training interactions only.

        Args:
            train_df: Train interactions [user_id, movie_id, rating, timestamp].
            context: Context containing 'candidate_movie_ids' array. If omitted,
                     inferred from unique movie_ids in train_df.
        """
        if context is not None and "candidate_movie_ids" in context:
            self.candidate_movie_ids = np.asarray(context["candidate_movie_ids"])
        else:
            # Deterministic ascending order of candidate movies
            self.candidate_movie_ids = np.sort(train_df["movie_id"].unique())

        self.n_candidates = len(self.candidate_movie_ids)
        cand_map = {mid: idx for idx, mid in enumerate(self.candidate_movie_ids)}

        # Aggregate train stats
        global_mean = float(train_df["rating"].mean())

        # Group train interactions by movie_id
        stats = train_df.groupby("movie_id").agg(
            v=("rating", "count"),
            pos_v=("rating", lambda s: (s >= self.positive_threshold).sum()),
            R=("rating", "mean"),
        ).reset_index()

        # Align with candidate_movie_ids
        scores_arr = np.zeros(self.n_candidates, dtype=np.float32)

        # Vectorized mapping using merge
        stats_df = pd.DataFrame({"movie_id": self.candidate_movie_ids})
        stats_df = stats_df.merge(stats, on="movie_id", how="left").fillna(
            {"v": 0, "pos_v": 0, "R": global_mean}
        )

        v = stats_df["v"].to_numpy(dtype=np.float64)
        pos_v = stats_df["pos_v"].to_numpy(dtype=np.float64)
        R = stats_df["R"].to_numpy(dtype=np.float64)
        m = self.damping

        if self.variant == PopularityVariant.MOST_RATED:
            scores_arr = v.astype(np.float32)

        elif self.variant == PopularityVariant.MOST_LIKED:
            scores_arr = pos_v.astype(np.float32)

        elif self.variant == PopularityVariant.DAMPED_MEAN:
            # Formula: (v / (v + m)) * R + (m / (v + m)) * C
            denom = v + m
            safe_denom = np.where(denom > 0, denom, 1.0)
            damped = (v / safe_denom) * R + (m / safe_denom) * global_mean
            scores_arr = damped.astype(np.float32)

        else:
            raise ValueError(f"Unknown variant: {self.variant}")

        self.item_scores = scores_arr
        return self

    def score(self, user_indices: np.ndarray) -> np.ndarray:
        """Return candidate scores broadcasted for the batch of users.

        Args:
            user_indices: 1D array of user internal indices.

        Returns:
            2D float32 array of shape [len(user_indices), n_candidates].
        """
        if self.item_scores is None:
            raise RuntimeError("Model must be fitted before calling score().")

        batch_size = len(user_indices)
        # Broadcast the 1D item_scores across the batch
        return np.tile(self.item_scores, (batch_size, 1))
