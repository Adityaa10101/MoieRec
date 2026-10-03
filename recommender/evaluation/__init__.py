"""Evaluation engine and metrics for MoieRec recommender systems."""

from recommender.evaluation.metrics import (
    precision_at_k,
    recall_at_k,
    ndcg_at_k,
    hit_rate_at_k,
    mrr_at_k,
    catalog_coverage_at_k,
    mean_recommended_popularity_at_k,
    rmse,
    mae,
    compute_hits,
)
from recommender.evaluation.protocol import (
    Recommender,
    EvaluationConfig,
    EvaluationContext,
    build_evaluation_context,
)
from recommender.evaluation.evaluator import (
    Evaluator,
    EvaluationResult,
    MetricSummary,
    PairedComparisonResult,
    compute_bootstrap_ci,
    evaluate_rating_prediction,
    select_topk_exact,
)

__all__ = [
    "Recommender",
    "EvaluationConfig",
    "EvaluationContext",
    "build_evaluation_context",
    "Evaluator",
    "EvaluationResult",
    "MetricSummary",
    "PairedComparisonResult",
    "compute_bootstrap_ci",
    "evaluate_rating_prediction",
    "select_topk_exact",
    "precision_at_k",
    "recall_at_k",
    "ndcg_at_k",
    "hit_rate_at_k",
    "mrr_at_k",
    "catalog_coverage_at_k",
    "mean_recommended_popularity_at_k",
    "rmse",
    "mae",
    "compute_hits",
]

