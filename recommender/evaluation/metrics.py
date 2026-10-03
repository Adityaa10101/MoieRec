"""Evaluation metrics for MoieRec recommender systems.

All ranking metrics are pure, vectorized functions operating on binary relevance.
Each ranking metric is available per user so that means, standard errors,
and bootstrap confidence intervals can be computed.
"""

from typing import Dict, List, Optional, Set, Union
import numpy as np


def compute_hits(
    predicted_topk: np.ndarray,
    reachable_items: Union[List[Set[int]], List[np.ndarray]],
) -> np.ndarray:
    """Compute boolean hit matrix [n_users, k] for recommended items.

    Args:
        predicted_topk: Array of shape [n_users, k] containing recommended item indices.
        reachable_items: List of sets or arrays of reachable positive item indices per user.

    Returns:
        Boolean array of shape [n_users, k] where True indicates a relevant hit.
    """
    n_users, k = predicted_topk.shape
    hits = np.zeros((n_users, k), dtype=bool)
    for u in range(n_users):
        rel = reachable_items[u]
        if not isinstance(rel, set):
            rel = set(rel)
        for j in range(k):
            if predicted_topk[u, j] in rel:
                hits[u, j] = True
    return hits


def precision_at_k(
    hits: np.ndarray,
    k: Optional[int] = None,
) -> np.ndarray:
    """Compute Precision@K per user: hits_in_topk / k.

    Args:
        hits: Boolean array of shape [n_users, k].
        k: Optional cut-off. If None, inferred from hits.shape[1].

    Returns:
        Array of shape [n_users] with float values in [0.0, 1.0].
    """
    if k is None:
        k = hits.shape[1]
    effective_k = min(k, hits.shape[1])
    hits_cut = hits[:, :effective_k]
    return hits_cut.sum(axis=1) / float(k)


def recall_at_k(
    hits: np.ndarray,
    reachable_counts: np.ndarray,
    k: Optional[int] = None,
) -> np.ndarray:
    """Compute Recall@K per user: hits_in_topk / |relevant|.

    Args:
        hits: Boolean array of shape [n_users, k].
        reachable_counts: Array of shape [n_users] with count of reachable positive items.
        k: Optional cut-off. If None, inferred from hits.shape[1].

    Returns:
        Array of shape [n_users] with float values in [0.0, 1.0].
    """
    if k is None:
        k = hits.shape[1]
    effective_k = min(k, hits.shape[1])
    hits_cut = hits[:, :effective_k]
    # Guard against division by zero if an empty user slipped through
    safe_counts = np.where(reachable_counts > 0, reachable_counts, 1.0)
    recalls = hits_cut.sum(axis=1) / safe_counts
    return np.where(reachable_counts > 0, recalls, 0.0)


def ndcg_at_k(
    hits: np.ndarray,
    reachable_counts: np.ndarray,
    k: Optional[int] = None,
) -> np.ndarray:
    """Compute NDCG@K per user with log2(rank + 1) discount.

    Ideal DCG (IDCG) places min(|relevant|, k) hits at ranks 1 .. min(|relevant|, k).

    Args:
        hits: Boolean array of shape [n_users, k].
        reachable_counts: Array of shape [n_users] with count of reachable positive items.
        k: Optional cut-off. If None, inferred from hits.shape[1].

    Returns:
        Array of shape [n_users] with float values in [0.0, 1.0].
    """
    if k is None:
        k = hits.shape[1]
    effective_k = min(k, hits.shape[1])
    hits_cut = hits[:, :effective_k]

    # Discounts: log2(rank + 1) for rank in 1..effective_k -> log2(2..effective_k + 1)
    ranks = np.arange(1, effective_k + 1, dtype=np.float64)
    discounts = 1.0 / np.log2(ranks + 1.0)

    # Actual DCG: sum of discount for hits
    dcg = (hits_cut * discounts).sum(axis=1)

    # IDCG: cumulative discounts for min(|relevant|, k)
    cum_discounts = np.cumsum(discounts)
    ideal_counts = np.clip(reachable_counts, 0, effective_k).astype(int)

    # idcg lookup
    idcg = np.zeros(len(reachable_counts), dtype=np.float64)
    mask = ideal_counts > 0
    idcg[mask] = cum_discounts[ideal_counts[mask] - 1]

    ndcg = np.zeros_like(dcg)
    valid_idcg = idcg > 0
    ndcg[valid_idcg] = dcg[valid_idcg] / idcg[valid_idcg]
    return ndcg


def hit_rate_at_k(
    hits: np.ndarray,
    k: Optional[int] = None,
) -> np.ndarray:
    """Compute HitRate@K per user: 1.0 if any relevant item in top-k else 0.0.

    Args:
        hits: Boolean array of shape [n_users, k].
        k: Optional cut-off. If None, inferred from hits.shape[1].

    Returns:
        Array of shape [n_users] with values 0.0 or 1.0.
    """
    if k is None:
        k = hits.shape[1]
    effective_k = min(k, hits.shape[1])
    return (hits[:, :effective_k].sum(axis=1) > 0).astype(np.float64)


def mrr_at_k(
    hits: np.ndarray,
    k: Optional[int] = None,
) -> np.ndarray:
    """Compute Mean Reciprocal Rank (MRR@K) per user: 1 / rank of first relevant item in top-k, else 0.0.

    Args:
        hits: Boolean array of shape [n_users, k].
        k: Optional cut-off. If None, inferred from hits.shape[1].

    Returns:
        Array of shape [n_users] with float values in [0.0, 1.0].
    """
    if k is None:
        k = hits.shape[1]
    effective_k = min(k, hits.shape[1])
    hits_cut = hits[:, :effective_k]

    has_hit = hits_cut.any(axis=1)
    # argmax along axis=1 returns the first True index
    first_hit_idx = np.argmax(hits_cut, axis=1)  # 0-indexed
    # Rank is 1-indexed: 1 / (first_hit_idx + 1)
    reciprocal_rank = np.where(has_hit, 1.0 / (first_hit_idx + 1.0), 0.0)
    return reciprocal_rank


def catalog_coverage_at_k(
    predicted_topk: np.ndarray,
    n_candidate_items: int,
) -> float:
    """Compute catalog coverage: distinct items recommended across all users / candidate items.

    Args:
        predicted_topk: Array of shape [n_users, k] of recommended candidate item indices.
        n_candidate_items: Total number of candidate items in the catalog.

    Returns:
        Float coverage ratio in [0.0, 1.0].
    """
    if n_candidate_items <= 0:
        return 0.0
    unique_items = np.unique(predicted_topk)
    return float(len(unique_items)) / float(n_candidate_items)


def mean_recommended_popularity_at_k(
    predicted_topk: np.ndarray,
    item_train_counts: np.ndarray,
) -> np.ndarray:
    """Compute mean TRAIN rating_count of recommended items per user (popularity-bias indicator).

    Args:
        predicted_topk: Array of shape [n_users, k] containing candidate item indices.
        item_train_counts: 1D array of shape [n_candidate_items] with train rating counts.

    Returns:
        Array of shape [n_users] containing the mean popularity of recommended items for each user.
    """
    pop_scores = item_train_counts[predicted_topk]
    return pop_scores.mean(axis=1)


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute Root Mean Squared Error (RMSE) for rating predictions."""
    diff = y_true - y_pred
    return float(np.sqrt(np.mean(diff ** 2)))


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute Mean Absolute Error (MAE) for rating predictions."""
    return float(np.mean(np.abs(y_true - y_pred)))
