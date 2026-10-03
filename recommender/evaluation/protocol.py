"""Evaluation protocol, dataset context builder, and abstract model interface for MoieRec.

Enforces:
- Candidate catalog = benchmark movies with >= 1 TRAIN rating.
- Reachable positives = user's positives (rating >= positive_threshold) in the evaluated split
  that belong to the candidate catalog.
- Zero-positive users excluded from ranking metrics with counts reported.
- Seen-item masking via sparse CSR matrix (TRAIN items for validation; TRAIN+VAL for test).
- Test-split access guard (raises PermissionError unless final=True and frozen_config_id provided).
- Deterministic tie-breaking by lower internal item index.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
import numpy as np
import pandas as pd
from scipy import sparse


class Recommender(ABC):
    """Abstract base class for all MoieRec recommender models."""

    @abstractmethod
    def fit(self, train_df: pd.DataFrame, context: Optional[dict] = None) -> "Recommender":
        """Fit model on training split only.

        Args:
            train_df: Training interactions DataFrame with [user_id, movie_id, rating, timestamp].
            context: Optional dictionary with catalog metadata, feature matrices, etc.
        """
        pass

    @abstractmethod
    def score(self, user_indices: np.ndarray) -> np.ndarray:
        """Compute recommendation scores for candidate catalog items for a batch of users.

        Args:
            user_indices: 1D array of internal user indices in [0, n_evaluated_users - 1].

        Returns:
            2D float32 array of shape [len(user_indices), n_candidate_items].
        """
        pass


@dataclass
class EvaluationConfig:
    """Configuration container for evaluation runs."""
    positive_threshold: float = 4.0
    k: int = 10
    batch_size: int = 2000
    sample_users: Optional[int] = None
    seed: int = 42
    n_bootstrap: int = 1000
    tie_break: str = "random_perm"  # "random_perm" (default neutral) or "index"


@dataclass
class EvaluationContext:
    """Precomputed evaluation context containing catalog, seen masks, and reachable positives."""
    mode: str
    positive_threshold: float
    candidate_movie_ids: np.ndarray
    n_candidates: int
    movie_id_to_cand_idx: Dict[int, int]

    # Evaluated users
    eval_user_ids: np.ndarray
    user_id_to_eval_idx: Dict[int, int]
    user_train_counts: np.ndarray  # train ratings per evaluated user
    user_history_spans_days: np.ndarray  # full history span in days per evaluated user


    # Catalog train stats
    candidate_train_counts: np.ndarray  # v
    candidate_train_pos_counts: np.ndarray  # positive count in train
    candidate_train_mean_ratings: np.ndarray  # R
    global_train_mean: float  # C

    # Reachable positives per evaluated user
    reachables: List[Set[int]]
    reachable_counts: np.ndarray

    # Sparse seen matrix [n_eval_users, n_candidates]
    seen_matrix: sparse.csr_matrix

    # Audit statistics
    total_split_positives: int
    unreachable_positives_count: int
    unreachable_positives_pct: float
    total_split_users: int
    excluded_zero_pos_users_count: int
    n_evaluated_users: int


def build_evaluation_context(
    train_df: pd.DataFrame,
    eval_df: pd.DataFrame,
    mode: str = "validation",
    positive_threshold: float = 4.0,
    sample_users: Optional[int] = None,
    seed: int = 42,
    final: bool = False,
    frozen_config_id: Optional[str] = None,
    train_plus_val_df_for_test: Optional[pd.DataFrame] = None,
    user_history_spans: Optional[Dict[int, float]] = None,
) -> EvaluationContext:

    """Build evaluation context and sparse masks.

    Args:
        train_df: Training interactions.
        eval_df: Evaluation interactions (validation or test).
        mode: 'validation' or 'test'.
        positive_threshold: Rating threshold defining a positive interaction.
        sample_users: Optional count of users to subsample for evaluation.
        seed: Random seed for sampling.
        final: Must be True to evaluate on test mode.
        frozen_config_id: Unique frozen config identifier required for test mode.
        train_plus_val_df_for_test: Combined train + validation df used only for test-mode seen masking.

    Raises:
        PermissionError: If mode is test and final=False or frozen_config_id is missing.
    """
    mode_normalized = mode.lower().strip()
    if mode_normalized in ("test", "test_split"):
        if not final or not frozen_config_id:
            raise PermissionError(
                "TEST split evaluation is strictly guarded and forbidden during model development. "
                "The test split is reserved for the final frozen run and requires final=True and a valid frozen_config_id."
            )

    # 1. Candidate catalog: benchmark movies with >= 1 TRAIN rating
    train_movie_stats = train_df.groupby("movie_id").agg(
        count=("rating", "count"),
        pos_count=("rating", lambda s: (s >= positive_threshold).sum()),
        mean_rating=("rating", "mean"),
    ).reset_index()

    # Sort candidate movie IDs for deterministic internal indexing
    train_movie_stats = train_movie_stats.sort_values(by="movie_id").reset_index(drop=True)
    candidate_movie_ids = train_movie_stats["movie_id"].to_numpy()
    n_candidates = len(candidate_movie_ids)
    movie_id_to_cand_idx = {mid: idx for idx, mid in enumerate(candidate_movie_ids)}

    candidate_train_counts = train_movie_stats["count"].to_numpy(dtype=np.int64)
    candidate_train_pos_counts = train_movie_stats["pos_count"].to_numpy(dtype=np.int64)
    candidate_train_mean_ratings = train_movie_stats["mean_rating"].to_numpy(dtype=np.float64)
    global_train_mean = float(train_df["rating"].mean())

    # 2. Reachable positives in eval split
    eval_positives = eval_df[eval_df["rating"] >= positive_threshold]
    total_split_positives = len(eval_positives)

    # Identify positives whose movie has no TRAIN ratings (unreachable)
    is_reachable = eval_positives["movie_id"].isin(movie_id_to_cand_idx)
    reachable_eval_pos = eval_positives[is_reachable]
    unreachable_count = total_split_positives - len(reachable_eval_pos)
    unreachable_pct = (unreachable_count / total_split_positives * 100.0) if total_split_positives > 0 else 0.0

    # Group reachable positives by user
    reachable_by_user: Dict[int, Set[int]] = {}
    for uid, mid in zip(reachable_eval_pos["user_id"], reachable_eval_pos["movie_id"]):
        cand_idx = movie_id_to_cand_idx[mid]
        if uid not in reachable_by_user:
            reachable_by_user[uid] = set()
        reachable_by_user[uid].add(cand_idx)

    # All users present in eval_df
    all_eval_users = eval_df["user_id"].unique()
    total_split_users = len(all_eval_users)

    # Filter to users with >= 1 reachable positive (users with 0 reachable positives excluded from ranking)
    users_with_positives = np.array([uid for uid in all_eval_users if uid in reachable_by_user])
    excluded_zero_pos_users_count = total_split_users - len(users_with_positives)

    # Sort user IDs for determinism
    users_with_positives = np.sort(users_with_positives)

    # Optional fixed user sample
    if sample_users is not None and sample_users < len(users_with_positives):
        rng = np.random.default_rng(seed)
        sampled_indices = rng.choice(len(users_with_positives), size=sample_users, replace=False)
        eval_user_ids = np.sort(users_with_positives[sampled_indices])
    else:
        eval_user_ids = users_with_positives

    n_eval_users = len(eval_user_ids)
    user_id_to_eval_idx = {uid: idx for idx, uid in enumerate(eval_user_ids)}

    # Build reachables list and counts for evaluated users
    reachables = [reachable_by_user[uid] for uid in eval_user_ids]
    reachable_counts = np.array([len(r) for r in reachables], dtype=np.int64)

    # Precompute train rating count per evaluated user
    train_user_counts = train_df.groupby("user_id")["movie_id"].count()
    user_train_counts = np.array([train_user_counts.get(uid, 0) for uid in eval_user_ids], dtype=np.int64)

    # Compute history span in days per evaluated user
    if user_history_spans is not None:
        user_history_spans_days = np.array([user_history_spans.get(uid, 0.0) for uid in eval_user_ids], dtype=np.float64)
    else:
        # Fallback: compute from train_df and eval_df
        t_min_train = train_df.groupby("user_id")["timestamp"].min()
        t_max_train = train_df.groupby("user_id")["timestamp"].max()
        t_min_eval = eval_df.groupby("user_id")["timestamp"].min()
        t_max_eval = eval_df.groupby("user_id")["timestamp"].max()

        mins = np.minimum(
            [t_min_train.get(uid, np.inf) for uid in eval_user_ids],
            [t_min_eval.get(uid, np.inf) for uid in eval_user_ids],
        )
        maxs = np.maximum(
            [t_max_train.get(uid, -np.inf) for uid in eval_user_ids],
            [t_max_eval.get(uid, -np.inf) for uid in eval_user_ids],
        )
        user_history_spans_days = np.maximum(0.0, (maxs - mins) / 86400.0)

    # 3. Seen-item masking via sparse CSR matrix [n_eval_users, n_candidates]
    # In validation mode: items seen in train_df
    # In test mode: items seen in train_df + validation_df
    if mode_normalized in ("test", "test_split"):
        mask_source_df = train_plus_val_df_for_test if train_plus_val_df_for_test is not None else train_df
    else:
        mask_source_df = train_df

    # Filter mask_source_df to evaluated users and candidate movies
    mask_rows = mask_source_df[
        mask_source_df["user_id"].isin(user_id_to_eval_idx) &
        mask_source_df["movie_id"].isin(movie_id_to_cand_idx)
    ]

    seen_user_indices = np.array([user_id_to_eval_idx[uid] for uid in mask_rows["user_id"]], dtype=np.int32)
    seen_item_indices = np.array([movie_id_to_cand_idx[mid] for mid in mask_rows["movie_id"]], dtype=np.int32)

    seen_matrix = sparse.csr_matrix(
        (np.ones(len(seen_user_indices), dtype=np.float32), (seen_user_indices, seen_item_indices)),
        shape=(n_eval_users, n_candidates),
    )

    return EvaluationContext(
        mode=mode_normalized,
        positive_threshold=positive_threshold,
        candidate_movie_ids=candidate_movie_ids,
        n_candidates=n_candidates,
        movie_id_to_cand_idx=movie_id_to_cand_idx,
        eval_user_ids=eval_user_ids,
        user_id_to_eval_idx=user_id_to_eval_idx,
        user_train_counts=user_train_counts,
        user_history_spans_days=user_history_spans_days,

        candidate_train_counts=candidate_train_counts,
        candidate_train_pos_counts=candidate_train_pos_counts,
        candidate_train_mean_ratings=candidate_train_mean_ratings,
        global_train_mean=global_train_mean,
        reachables=reachables,
        reachable_counts=reachable_counts,
        seen_matrix=seen_matrix,
        total_split_positives=total_split_positives,
        unreachable_positives_count=unreachable_count,
        unreachable_positives_pct=unreachable_pct,
        total_split_users=total_split_users,
        excluded_zero_pos_users_count=excluded_zero_pos_users_count,
        n_evaluated_users=n_eval_users,
    )
