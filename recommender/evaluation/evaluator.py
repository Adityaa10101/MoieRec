"""Evaluator engine for MoieRec recommender systems.

Implements batched user evaluation, deterministic tie-breaking, seen-item masking,
per-user metric extraction, 95% bootstrap confidence intervals, and activity-bucket analysis.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from recommender.evaluation.metrics import (
    catalog_coverage_at_k,
    compute_hits,
    hit_rate_at_k,
    mae,
    mean_recommended_popularity_at_k,
    mrr_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    rmse,
)
from recommender.evaluation.protocol import (
    EvaluationConfig,
    EvaluationContext,
    Recommender,
)


def compute_bootstrap_ci(
    values: np.ndarray,
    n_resamples: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 42,
    chunk_size: int = 100,
) -> Tuple[float, float, float]:
    """Compute mean and 95% bootstrap confidence interval over users.

    Args:
        values: 1D array of per-user metric values.
        n_resamples: Number of bootstrap resamples (default: 1000).
        confidence_level: Desired coverage (default: 0.95).
        seed: Random seed for reproducibility.
        chunk_size: Block size for vectorized resampling.

    Returns:
        Tuple of (mean, ci_lower, ci_upper).
    """
    n = len(values)
    if n == 0:
        return 0.0, 0.0, 0.0
    mean_val = float(np.mean(values))
    if n == 1:
        return mean_val, mean_val, mean_val

    rng = np.random.default_rng(seed)
    alpha = (1.0 - confidence_level) / 2.0
    boot_means = []

    remaining = n_resamples
    while remaining > 0:
        b = min(remaining, chunk_size)
        idx = rng.integers(0, n, size=(b, n))
        chunk_means = values[idx].mean(axis=1)
        boot_means.extend(chunk_means)
        remaining -= b

    boot_means = np.array(boot_means)
    ci_lower = float(np.percentile(boot_means, alpha * 100.0))
    ci_upper = float(np.percentile(boot_means, (1.0 - alpha) * 100.0))
    return mean_val, ci_lower, ci_upper


@dataclass
class MetricSummary:
    mean: float
    ci_lower: float
    ci_upper: float


@dataclass
class PairedComparisonResult:
    """Paired statistical comparison between two models over identical evaluated users."""
    metric: str
    n_users: int
    mean_a: float
    mean_b: float
    mean_diff: float
    ci_lower: float
    ci_upper: float
    relative_lift: float
    pct_a_better: float
    pct_equal: float
    pct_b_better: float
    is_distinguishable_from_zero: bool


@dataclass
class EvaluationResult:
    """Complete evaluation report for a model."""
    k: int
    n_evaluated_users: int
    n_excluded_zero_pos_users: int
    n_candidates: int
    unreachable_positives_count: int
    unreachable_positives_pct: float

    # Ranking metrics (mean + 95% CI)
    precision: MetricSummary
    recall: MetricSummary
    ndcg: MetricSummary
    hit_rate: MetricSummary
    mrr: MetricSummary

    # Beyond-accuracy metrics
    catalog_coverage: float
    mean_recommended_popularity: MetricSummary

    # User activity breakdown (quartiles of train ratings count)
    activity_breakdown: List[Dict[str, Any]]

    # Session span breakdown (<1 day, 1-30 days, >=30 days)
    session_strata_breakdown: List[Dict[str, Any]] = field(default_factory=list)

    # Detailed arrays (optional, for custom analysis or tests)
    per_user_metrics: Optional[Dict[str, np.ndarray]] = None
    predicted_topk: Optional[np.ndarray] = None
    runtime_seconds: float = 0.0



def select_topk_exact(
    scores: np.ndarray,
    k: int,
    tie_ranks: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Select top-k items descending by score with exact tie-breaking.

    Guarantees:
    - Items with higher score strictly rank before items with lower score.
    - Items with identical scores strictly rank by tie_ranks ascending (lower tie rank wins).
    - Zero floating-point perturbation artifacts or ULP precision loss at high magnitudes.
    """
    n_users = scores.shape[0]
    n_items = scores.shape[1]
    if tie_ranks is None:
        tie_ranks = np.arange(n_items, dtype=np.int32)

    # 1. Fast introselect partition at k
    part_idx = np.argpartition(-scores, k, axis=1)[:, :k]
    row_idx = np.arange(n_users)[:, None]
    part_scores = scores[row_idx, part_idx]
    part_tie_ranks = tie_ranks[part_idx]

    # 2. Sort the k items by (-score, tie_ranks) using lexsort
    sub_order = np.lexsort((part_tie_ranks, -part_scores), axis=1)
    topk = np.take_along_axis(part_idx, sub_order, axis=1)

    # 3. Cutoff score at rank k (last column)
    sorted_part_scores = np.take_along_axis(part_scores, sub_order, axis=1)
    k_scores = sorted_part_scores[:, -1]

    # Boundary tie check: count of items with score == k_score in entire row vs inside top-k
    topk_k_score_counts = np.sum(sorted_part_scores == k_scores[:, None], axis=1)
    total_k_score_counts = np.sum(scores == k_scores[:, None], axis=1)

    tied_row_mask = (total_k_score_counts > topk_k_score_counts) & np.isfinite(k_scores)
    tied_rows = np.flatnonzero(tied_row_mask)

    if len(tied_rows) > 0:
        for u in tied_rows:
            s_star = k_scores[u]
            higher_items = np.flatnonzero(scores[u] > s_star)
            tied_items = np.flatnonzero(scores[u] == s_star)

            needed_from_tied = k - len(higher_items)
            tied_order = np.argsort(tie_ranks[tied_items])
            chosen_tied = tied_items[tied_order[:needed_from_tied]]

            combined = np.concatenate([higher_items, chosen_tied])
            comb_scores = scores[u, combined]
            comb_tie_ranks = tie_ranks[combined]
            comb_order = np.lexsort((comb_tie_ranks, -comb_scores))
            topk[u] = combined[comb_order]

    return topk


class Evaluator:
    """Evaluates Recommender models under the strict MoieRec evaluation protocol."""

    def __init__(self, context: EvaluationContext, config: Optional[EvaluationConfig] = None):
        self.context = context
        self.config = config or EvaluationConfig()

        # Build item tie-breaking ranks
        if self.config.tie_break == "random_perm":
            rng = np.random.default_rng(self.config.seed)
            perm = rng.permutation(self.context.n_candidates)
            self.tie_ranks = np.empty(self.context.n_candidates, dtype=np.int32)
            self.tie_ranks[perm] = np.arange(self.context.n_candidates, dtype=np.int32)
        elif self.config.tie_break == "index":
            self.tie_ranks = np.arange(self.context.n_candidates, dtype=np.int32)
        else:
            raise ValueError(f"Unknown tie_break: {self.config.tie_break}. Expected 'random_perm' or 'index'.")

    def evaluate(
        self,
        model: Recommender,
        store_per_user_metrics: bool = True,
        store_topk: bool = False,
    ) -> EvaluationResult:
        """Run batched ranking evaluation for the model.

        Args:
            model: Fitted Recommender instance.
            store_per_user_metrics: Whether to attach raw per-user metric arrays.
            store_topk: Whether to attach full [n_users, k] recommended indices array.

        Returns:
            EvaluationResult dataclass.
        """
        start_time = time.time()
        n_users = self.context.n_evaluated_users
        n_candidates = self.context.n_candidates
        k = self.config.k
        batch_size = self.config.batch_size

        all_topk = []

        for start_idx in range(0, n_users, batch_size):
            end_idx = min(start_idx + batch_size, n_users)
            batch_user_indices = np.arange(start_idx, end_idx)

            # 1. Model scores for batch [batch_len, n_candidates]
            scores = model.score(batch_user_indices).astype(np.float64, copy=True)

            # 2. Seen-item masking via sparse CSR matrix
            batch_seen = self.context.seen_matrix[batch_user_indices].tocoo()
            scores[batch_seen.row, batch_seen.col] = -np.inf

            # 3. Exact top-k partition and deterministic tie-breaking
            batch_topk = select_topk_exact(scores, k, self.tie_ranks)
            all_topk.append(batch_topk)

        predicted_topk = np.vstack(all_topk) if all_topk else np.zeros((0, k), dtype=int)

        # 4. Compute hits against reachable positives
        hits = compute_hits(predicted_topk, self.context.reachables)

        # 5. Extract per-user ranking metrics
        precisions = precision_at_k(hits, k)
        recalls = recall_at_k(hits, self.context.reachable_counts, k)
        ndcgs = ndcg_at_k(hits, self.context.reachable_counts, k)
        hit_rates = hit_rate_at_k(hits, k)
        mrrs = mrr_at_k(hits, k)
        mrps = mean_recommended_popularity_at_k(predicted_topk, self.context.candidate_train_counts)
        coverage = catalog_coverage_at_k(predicted_topk, n_candidates)

        # 6. Compute bootstrap confidence intervals
        seed = self.config.seed
        n_boot = self.config.n_bootstrap

        prec_summary = MetricSummary(*compute_bootstrap_ci(precisions, n_boot, seed=seed))
        rec_summary = MetricSummary(*compute_bootstrap_ci(recalls, n_boot, seed=seed))
        ndcg_summary = MetricSummary(*compute_bootstrap_ci(ndcgs, n_boot, seed=seed))
        hr_summary = MetricSummary(*compute_bootstrap_ci(hit_rates, n_boot, seed=seed))
        mrr_summary = MetricSummary(*compute_bootstrap_ci(mrrs, n_boot, seed=seed))
        mrp_summary = MetricSummary(*compute_bootstrap_ci(mrps, n_boot, seed=seed))

        # 7. User activity breakdown (quartiles of train ratings count)
        activity_breakdown = self._compute_activity_breakdown(
            precisions, recalls, ndcgs, hit_rates, mrrs, self.context.user_train_counts
        )

        # 8. Session span breakdown (< 1 day, 1-30 days, >= 30 days)
        session_strata = self._compute_session_strata_breakdown(
            precisions, recalls, ndcgs, hit_rates, mrrs, self.context.user_history_spans_days
        )

        elapsed = time.time() - start_time

        per_user_dict = {
            "precision": precisions,
            "recall": recalls,
            "ndcg": ndcgs,
            "hit_rate": hit_rates,
            "mrr": mrrs,
            "mean_popularity": mrps,
        } if store_per_user_metrics else None

        return EvaluationResult(
            k=k,
            n_evaluated_users=n_users,
            n_excluded_zero_pos_users=self.context.excluded_zero_pos_users_count,
            n_candidates=n_candidates,
            unreachable_positives_count=self.context.unreachable_positives_count,
            unreachable_positives_pct=self.context.unreachable_positives_pct,
            precision=prec_summary,
            recall=rec_summary,
            ndcg=ndcg_summary,
            hit_rate=hr_summary,
            mrr=mrr_summary,
            catalog_coverage=coverage,
            mean_recommended_popularity=mrp_summary,
            activity_breakdown=activity_breakdown,
            session_strata_breakdown=session_strata,
            per_user_metrics=per_user_dict,
            predicted_topk=predicted_topk if store_topk else None,
            runtime_seconds=elapsed,
        )

    def _compute_session_strata_breakdown(
        self,
        precisions: np.ndarray,
        recalls: np.ndarray,
        ndcgs: np.ndarray,
        hit_rates: np.ndarray,
        mrrs: np.ndarray,
        spans_days: np.ndarray,
    ) -> List[Dict[str, Any]]:
        """Stratify evaluated users by full rating history duration."""
        n_users = len(spans_days)
        if n_users == 0:
            return []

        masks = [
            ("< 1 day (Onboarding Spree)", spans_days < 1.0),
            ("1-30 days (Short-term / Casual)", (spans_days >= 1.0) & (spans_days < 30.0)),
            (">= 30 days (Multi-session / Longitudinal)", spans_days >= 30.0),
        ]

        breakdown = []
        for label, m in masks:
            count = int(m.sum())
            if count == 0:
                continue
            breakdown.append({
                "strata": label,
                "n_users": count,
                "pct_of_evaluated": float(count / n_users * 100.0),
                "min_span_days": float(spans_days[m].min()),
                "max_span_days": float(spans_days[m].max()),
                "precision": float(precisions[m].mean()),
                "recall": float(recalls[m].mean()),
                "ndcg": float(ndcgs[m].mean()),
                "hit_rate": float(hit_rates[m].mean()),
                "mrr": float(mrrs[m].mean()),
            })
        return breakdown

    @staticmethod
    def compare(
        per_user_a: np.ndarray,
        per_user_b: np.ndarray,
        metric: str = "metric",
        n_resamples: int = 1000,
        confidence_level: float = 0.95,
        seed: int = 42,
    ) -> PairedComparisonResult:
        """Compute paired statistical comparison with 95% bootstrap confidence interval."""
        assert len(per_user_a) == len(per_user_b), "User arrays must have identical length"
        n = len(per_user_a)
        if n == 0:
            return PairedComparisonResult(metric, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 100.0, 0.0, False)

        diff = per_user_a - per_user_b
        mean_a = float(np.mean(per_user_a))
        mean_b = float(np.mean(per_user_b))
        mean_diff = float(np.mean(diff))

        # Vectorized paired bootstrap over differences
        rng = np.random.default_rng(seed)
        alpha = (1.0 - confidence_level) / 2.0
        boot_diff_means = []
        chunk_size = 100
        rem = n_resamples
        while rem > 0:
            b = min(rem, chunk_size)
            idx = rng.integers(0, n, size=(b, n))
            chunk_means = diff[idx].mean(axis=1)
            boot_diff_means.extend(chunk_means)
            rem -= b

        boot_diff_means = np.array(boot_diff_means)
        ci_lower = float(np.percentile(boot_diff_means, alpha * 100.0))
        ci_upper = float(np.percentile(boot_diff_means, (1.0 - alpha) * 100.0))

        relative_lift = float(mean_diff / mean_b) if abs(mean_b) > 1e-12 else 0.0

        tol = 1e-9
        is_eq = np.abs(diff) < tol
        is_a_better = diff >= tol
        is_b_better = diff <= -tol

        pct_a = float(np.mean(is_a_better) * 100.0)
        pct_eq = float(np.mean(is_eq) * 100.0)
        pct_b = float(np.mean(is_b_better) * 100.0)

        is_distinguishable = bool((ci_lower > 0.0) or (ci_upper < 0.0))

        return PairedComparisonResult(
            metric=metric,
            n_users=n,
            mean_a=mean_a,
            mean_b=mean_b,
            mean_diff=mean_diff,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            relative_lift=relative_lift,
            pct_a_better=pct_a,
            pct_equal=pct_eq,
            pct_b_better=pct_b,
            is_distinguishable_from_zero=is_distinguishable,
        )


    def _compute_activity_breakdown(
        self,
        precisions: np.ndarray,
        recalls: np.ndarray,
        ndcgs: np.ndarray,
        hit_rates: np.ndarray,
        mrrs: np.ndarray,
        train_counts: np.ndarray,
    ) -> List[Dict[str, Any]]:
        """Group users by train interaction count quartiles."""
        n_users = len(train_counts)
        if n_users == 0:
            return []

        # If too few users or zero variance, return single bucket
        q25, q50, q75 = np.percentile(train_counts, [25, 50, 75])

        masks = [
            ("Q1 (Low)", train_counts <= q25),
            ("Q2 (Med-Low)", (train_counts > q25) & (train_counts <= q50)),
            ("Q3 (Med-High)", (train_counts > q50) & (train_counts <= q75)),
            ("Q4 (High)", train_counts > q75),
        ]

        breakdown = []
        for label, m in masks:
            count = int(m.sum())
            if count == 0:
                continue
            breakdown.append({
                "bucket": label,
                "n_users": count,
                "min_train_ratings": int(train_counts[m].min()),
                "max_train_ratings": int(train_counts[m].max()),
                "precision": float(precisions[m].mean()),
                "recall": float(recalls[m].mean()),
                "ndcg": float(ndcgs[m].mean()),
                "hit_rate": float(hit_rates[m].mean()),
                "mrr": float(mrrs[m].mean()),
            })
        return breakdown


def evaluate_rating_prediction(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    method: str = "global_mean",
    damping: float = 25.0,
) -> Dict[str, float]:
    """Evaluate non-personalized rating prediction baselines on VALIDATION split.

    Anchors RMSE and MAE. Labeled strictly as rating prediction, not ranking quality.

    Args:
        train_df: Train interactions [user_id, movie_id, rating].
        val_df: Validation interactions [user_id, movie_id, rating].
        method: 'global_mean', 'movie_mean', or 'damped_movie_mean'.
        damping: Hyperparameter m for damped movie mean.

    Returns:
        Dict with 'rmse', 'mae', 'method', and 'n_ratings'.
    """
    global_mean = float(train_df["rating"].mean())
    y_true = val_df["rating"].to_numpy(dtype=np.float64)

    if method == "global_mean":
        y_pred = np.full_like(y_true, global_mean)

    elif method == "movie_mean":
        movie_means = train_df.groupby("movie_id")["rating"].mean().to_dict()
        y_pred = val_df["movie_id"].map(movie_means).fillna(global_mean).to_numpy(dtype=np.float64)

    elif method == "damped_movie_mean":
        stats = train_df.groupby("movie_id").agg(
            v=("rating", "count"),
            R=("rating", "mean"),
        )
        # formula: (v / (v + m)) * R + (m / (v + m)) * C
        stats["damped"] = (stats["v"] / (stats["v"] + damping)) * stats["R"] + (damping / (stats["v"] + damping)) * global_mean
        damped_map = stats["damped"].to_dict()
        y_pred = val_df["movie_id"].map(damped_map).fillna(global_mean).to_numpy(dtype=np.float64)

    else:
        raise ValueError(f"Unknown rating prediction method: {method}")

    val_rmse = rmse(y_true, y_pred)
    val_mae = mae(y_true, y_pred)

    return {
        "method": method,
        "rmse": val_rmse,
        "mae": val_mae,
        "n_ratings": len(y_true),
        "damping": damping if method == "damped_movie_mean" else None,
    }
