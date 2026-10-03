"""Runner script for Content-Based Recommender (Model 1) validation and Tier 2 snapshot experiments.

Evaluates:
- Part B: Tier 1 tuning grid (32 configurations: 4 profile variants x 2 genre IDF x 4 year weights)
  on a fixed sample of 20,000 validation users.
- Full validation evaluation of the selected best Tier 1 config across all 94,312 validation users
  with 95% bootstrap CIs, activity breakdowns, session strata breakdowns, and paired comparison
  vs Popularity baseline (most_liked).
- Part C: Tier 2 snapshot experiments (T1+tags, T1+genome, T1+tags+genome) tuned on 20,000 users,
  then evaluated on all validation users with snapshot_features=true labeling, genome recommendation
  coverage, and paired comparisons vs Tier 1 and vs Popularity.
"""

import datetime
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure project root is on sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import numpy as np
import pandas as pd
import scipy
from scipy import sparse
import pyarrow
import pytest

from recommender.content_based.model import (
    ContentBasedRecommender,
    ProfileVariant,
)
from recommender.baselines.popularity import (
    PopularityRecommender,
    PopularityVariant,
)
from recommender.evaluation.evaluator import (
    EvaluationResult,
    Evaluator,
    MetricSummary,
    PairedComparisonResult,
)
from recommender.evaluation.protocol import (
    EvaluationConfig,
    build_evaluation_context,
)
from recommender.preprocessing.utils import (
    compute_dataframe_content_hash,
    load_dataset_config,
)


def get_git_commit_hash(repo_dir: Path) -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def get_git_dirty_flag(repo_dir: Path) -> bool:
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        return len(res.stdout.strip()) > 0
    except Exception:
        return True


def format_summary(summary: MetricSummary) -> Dict[str, float]:
    return {
        "mean": round(float(summary.mean), 6),
        "ci_lower": round(float(summary.ci_lower), 6),
        "ci_upper": round(float(summary.ci_upper), 6),
    }


def compute_genome_recommendation_coverage(
    evaluator: Evaluator,
    model: ContentBasedRecommender,
    feat_dir: Path,
) -> float:
    """Compute the fraction of recommended items across all users that have genome features."""
    mask_path = feat_dir / "tier2_genome_mask.npy"
    if not mask_path.exists():
        return 0.0

    # Load benchmark mask
    id_map_path = feat_dir.parent / "id_mappings" / "movie_id_to_benchmark_idx.parquet"
    m2b = pd.read_parquet(id_map_path).set_index("movie_id")["benchmark_idx"].to_dict()
    cand_bench_indices = [m2b[mid] for mid in model.candidate_movie_ids]
    cand_has_genome = np.load(mask_path)[cand_bench_indices].astype(bool)

    # Evaluate model storing top-k recommendations
    res = evaluator.evaluate(model, store_per_user_metrics=False, store_topk=True)
    all_topk = res.topk_item_indices  # [n_users, k]
    if all_topk is None:
        return 0.0

    recs_have_genome = cand_has_genome[all_topk]
    return float(np.mean(recs_have_genome))


def main() -> None:
    start_total_time = time.time()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    git_hash = get_git_commit_hash(root_dir)

    print("=" * 70)
    print("MOIEREC CONTENT-BASED RECOMMENDER (MODEL 1) VALIDATION RUN")
    print("=" * 70)
    print(f"Timestamp: {timestamp}")
    print(f"Git commit: {git_hash}")

    pkg_versions = {
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "pyarrow": pyarrow.__version__,
        "pytest": pytest.__version__,
    }
    print(f"Packages: {pkg_versions}")

    dataset_name = "ml-25m"
    data_dir = root_dir / "data" / "processed" / dataset_name
    splits_dir = data_dir / "splits"
    feat_dir = data_dir / "features"
    results_dir = root_dir / "recommender" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load Data
    print("\nLoading TRAIN and VALIDATION splits...")
    t0 = time.time()
    train_df = pd.read_parquet(splits_dir / "train.parquet")
    val_df = pd.read_parquet(splits_dir / "validation.parquet")
    print(f"Loaded train ({len(train_df):,} rows) and validation ({len(val_df):,} rows) in {time.time() - t0:.2f}s")

    train_hash = compute_dataframe_content_hash(train_df)
    val_hash = compute_dataframe_content_hash(val_df)
    print(f"Train content hash:      {train_hash}")
    print(f"Validation content hash: {val_hash}")

    # 2. History spans for session strata
    print("Loading benchmark rating timestamps for session spans...")
    bench_ratings_path = data_dir / "benchmark" / "ratings.parquet"
    if bench_ratings_path.exists():
        ratings_bench = pd.read_parquet(bench_ratings_path, columns=["user_id", "timestamp"])
        user_min_max = ratings_bench.groupby("user_id")["timestamp"].agg(["min", "max"])
        spans_series = (user_min_max["max"] - user_min_max["min"]) / 86400.0
        spans_dict = spans_series.to_dict()
    else:
        spans_dict = None

    pos_thresh = 4.0

    # 3. Build Full Context and 20k Sampled Context
    print("\nBuilding validation evaluation contexts...")
    ctx_full = build_evaluation_context(
        train_df,
        val_df,
        mode="validation",
        positive_threshold=pos_thresh,
        user_history_spans=spans_dict,
    )
    print(f"Full Context: {ctx_full.n_evaluated_users:,} evaluated users, {ctx_full.n_candidates:,} candidates")

    sample_size = 20000
    sample_seed = 42
    ctx_sample = build_evaluation_context(
        train_df,
        val_df,
        mode="validation",
        positive_threshold=pos_thresh,
        sample_users=sample_size,
        seed=sample_seed,
        user_history_spans=spans_dict,
    )
    print(f"Sample Context: {ctx_sample.n_evaluated_users:,} users (seed={sample_seed})")

    eval_cfg_sample = EvaluationConfig(positive_threshold=pos_thresh, k=10, batch_size=2000, seed=sample_seed, n_bootstrap=100)
    evaluator_sample = Evaluator(ctx_sample, eval_cfg_sample)

    eval_cfg_full = EvaluationConfig(positive_threshold=pos_thresh, k=10, batch_size=2000, seed=42, n_bootstrap=1000)
    evaluator_full = Evaluator(ctx_full, eval_cfg_full)

    # Context dict for model fitting
    sample_fit_context = {
        "candidate_movie_ids": ctx_sample.candidate_movie_ids,
        "user_id_to_eval_idx": ctx_sample.user_id_to_eval_idx,
        "eval_user_ids": ctx_sample.eval_user_ids,
        "feature_dir": feat_dir,
    }

    full_fit_context = {
        "candidate_movie_ids": ctx_full.candidate_movie_ids,
        "user_id_to_eval_idx": ctx_full.user_id_to_eval_idx,
        "eval_user_ids": ctx_full.eval_user_ids,
        "feature_dir": feat_dir,
    }

    # =========================================================================
    # PART B: CONTENT-BASED TIER 1 TUNING (20,000 SAMPLES)
    # =========================================================================
    print("\n" + "=" * 70)
    print("PART B: TIER 1 GRID SEARCH (20,000 VALIDATION USERS)")
    print("=" * 70)

    profile_variants = [
        ProfileVariant.POS_MEAN,
        ProfileVariant.RATING_WEIGHTED,
        ProfileVariant.CENTERED,
        ProfileVariant.POS_RATING_WEIGHTED,
    ]
    genre_idf_options = [False, True]
    year_weights = [0.0, 0.25, 0.5, 1.0]

    tier1_grid_results = []
    best_t1_record = None
    best_t1_ndcg = -1.0

    print(f"{'Variant':<20} | {'IDF':<5} | {'w_yr':<5} | {'NDCG@10':<8} | {'P@10':<8} | {'R@10':<8} | {'HR@10':<8} | {'Zero Prof':<9}")
    print("-" * 88)

    for p_var in profile_variants:
        for use_idf in genre_idf_options:
            for w_yr in year_weights:
                model = ContentBasedRecommender(
                    profile_variant=p_var,
                    use_genre_idf=use_idf,
                    year_weight=w_yr,
                    missing_year_weight=0.0,
                    positive_threshold=pos_thresh,
                    tier=1,
                    feature_dir=feat_dir,
                )
                model.fit(train_df, context=sample_fit_context)
                res = evaluator_sample.evaluate(model, store_per_user_metrics=False)

                rec = {
                    "profile_variant": p_var.value,
                    "use_genre_idf": use_idf,
                    "year_weight": w_yr,
                    "ndcg": round(res.ndcg.mean, 6),
                    "precision": round(res.precision.mean, 6),
                    "recall": round(res.recall.mean, 6),
                    "hit_rate": round(res.hit_rate.mean, 6),
                    "mrr": round(res.mrr.mean, 6),
                    "catalog_coverage": round(res.catalog_coverage, 6),
                    "zero_profile_users": model.n_zero_profile_users,
                }
                tier1_grid_results.append(rec)

                print(
                    f"{p_var.value:<20} | {str(use_idf):<5} | {w_yr:<5.2f} | "
                    f"{res.ndcg.mean:<8.4f} | {res.precision.mean:<8.4f} | "
                    f"{res.recall.mean:<8.4f} | {res.hit_rate.mean:<8.4f} | "
                    f"{model.n_zero_profile_users:<9}"
                )

                if res.ndcg.mean > best_t1_ndcg:
                    best_t1_ndcg = res.ndcg.mean
                    best_t1_record = rec

    print("-" * 88)
    print(f"BEST TIER 1 CONFIG: {best_t1_record['profile_variant']}, IDF={best_t1_record['use_genre_idf']}, w_yr={best_t1_record['year_weight']} (NDCG@10 = {best_t1_ndcg:.6f})")

    # =========================================================================
    # PART B: EVALUATE BEST TIER 1 ON ALL VALIDATION USERS
    # =========================================================================
    print("\n" + "=" * 70)
    print("EVALUATING BEST TIER 1 ON ALL VALIDATION USERS (94,312 USERS)...")
    print("=" * 70)

    best_t1_model = ContentBasedRecommender(
        profile_variant=best_t1_record["profile_variant"],
        use_genre_idf=best_t1_record["use_genre_idf"],
        year_weight=best_t1_record["year_weight"],
        missing_year_weight=0.0,
        positive_threshold=pos_thresh,
        tier=1,
        feature_dir=feat_dir,
    )
    t_fit_t1 = time.time()
    best_t1_model.fit(train_df, context=full_fit_context)
    print(f"Fitted Best Tier 1 model on train interactions in {time.time() - t_fit_t1:.2f}s")
    print(f"Zero-profile users on full validation: {best_t1_model.n_zero_profile_users:,}")

    t_eval_t1 = time.time()
    best_t1_res = evaluator_full.evaluate(best_t1_model, store_per_user_metrics=True)
    print(f"Evaluated Best Tier 1 on all validation users in {time.time() - t_eval_t1:.2f}s")

    print("\nTIER 1 VALIDATION PERFORMANCE (WITH 95% BOOTSTRAP CIs):")
    print(f"  Precision@10: {best_t1_res.precision.mean:.4f} [{best_t1_res.precision.ci_lower:.4f}, {best_t1_res.precision.ci_upper:.4f}]")
    print(f"  Recall@10:    {best_t1_res.recall.mean:.4f} [{best_t1_res.recall.ci_lower:.4f}, {best_t1_res.recall.ci_upper:.4f}]")
    print(f"  NDCG@10:      {best_t1_res.ndcg.mean:.4f} [{best_t1_res.ndcg.ci_lower:.4f}, {best_t1_res.ndcg.ci_upper:.4f}]")
    print(f"  HitRate@10:   {best_t1_res.hit_rate.mean:.4f} [{best_t1_res.hit_rate.ci_lower:.4f}, {best_t1_res.hit_rate.ci_upper:.4f}]")
    print(f"  MRR@10:       {best_t1_res.mrr.mean:.4f} [{best_t1_res.mrr.ci_lower:.4f}, {best_t1_res.mrr.ci_upper:.4f}]")
    print(f"  Coverage:     {best_t1_res.catalog_coverage:.4f}")
    print(f"  Mean Pop:     {best_t1_res.mean_recommended_popularity.mean:.1f}")

    # Paired comparison vs Popularity (most_liked)
    pop_model = PopularityRecommender(variant=PopularityVariant.MOST_LIKED, positive_threshold=pos_thresh)
    pop_model.fit(train_df, context={"candidate_movie_ids": ctx_full.candidate_movie_ids})
    pop_res = evaluator_full.evaluate(pop_model, store_per_user_metrics=True)

    print("\nPAIRED STATISTICAL COMPARISON: TIER 1 vs POPULARITY (MOST_LIKED)")
    t1_vs_pop = {}
    for m_col in ["ndcg", "hit_rate", "recall"]:
        comp = Evaluator.compare(
            best_t1_res.per_user_metrics[m_col],
            pop_res.per_user_metrics[m_col],
            metric=f"{m_col.upper()}@10",
        )
        dist_str = "YES (p < 0.05)" if comp.is_distinguishable_from_zero else "NO (p >= 0.05)"
        print(f"  {comp.metric:<12}: Diff={comp.mean_diff:+.6f} [95% CI: {comp.ci_lower:+.6f}, {comp.ci_upper:+.6f}] | Lift={comp.relative_lift:+.2%} | Distinguishable={dist_str}")
        print(f"               CB>Pop: {comp.pct_a_better:.2f}% | Equal: {comp.pct_equal:.2f}% | CB<Pop: {comp.pct_b_better:.2f}%")
        t1_vs_pop[m_col] = {
            "metric": comp.metric,
            "mean_diff": round(comp.mean_diff, 6),
            "ci_lower": round(comp.ci_lower, 6),
            "ci_upper": round(comp.ci_upper, 6),
            "relative_lift": round(comp.relative_lift, 4),
            "pct_tier1_better": round(comp.pct_a_better, 2),
            "pct_equal": round(comp.pct_equal, 2),
            "pct_pop_better": round(comp.pct_b_better, 2),
            "distinguishable_from_zero": comp.is_distinguishable_from_zero,
        }

    # Save Tier 1 results JSON and CSV
    t1_output = {
        "metadata": {
            "dataset": dataset_name,
            "timestamp": timestamp,
            "git_commit": git_hash,
            "dirty_working_tree": get_git_dirty_flag(root_dir),
            "positive_threshold": pos_thresh,
            "tie_break": eval_cfg_full.tie_break,
            "train_content_hash": train_hash,
            "validation_content_hash": val_hash,
            "packages": pkg_versions,
            "tuning_sample_size": sample_size,
            "tuning_seed": sample_seed,
            "total_runtime_seconds": round(time.time() - start_total_time, 2),
        },
        "chosen_config": best_t1_record,
        "tuning_grid_results": tier1_grid_results,
        "full_validation_metrics": {
            "precision": format_summary(best_t1_res.precision),
            "recall": format_summary(best_t1_res.recall),
            "ndcg": format_summary(best_t1_res.ndcg),
            "hit_rate": format_summary(best_t1_res.hit_rate),
            "mrr": format_summary(best_t1_res.mrr),
            "catalog_coverage": round(float(best_t1_res.catalog_coverage), 6),
            "mean_recommended_popularity": format_summary(best_t1_res.mean_recommended_popularity),
            "zero_profile_users": best_t1_model.n_zero_profile_users,
            "activity_breakdown": best_t1_res.activity_breakdown,
            "session_strata_breakdown": best_t1_res.session_strata_breakdown,
        },
        "paired_comparison_vs_popularity_most_liked": t1_vs_pop,
    }

    t1_json_path = results_dir / "content_tier1_validation.json"
    with open(t1_json_path, "w", encoding="utf-8") as f:
        json.dump(t1_output, f, indent=2)
    print(f"\nSaved Tier 1 results JSON to: {t1_json_path}")

    # CSV summary for Tier 1
    t1_csv_df = pd.DataFrame(tier1_grid_results)
    t1_csv_path = results_dir / "content_tier1_validation.csv"
    t1_csv_df.to_csv(t1_csv_path, index=False)
    print(f"Saved Tier 1 CSV summary to: {t1_csv_path}")

    total_time = time.time() - start_total_time
    print("\n" + "=" * 70)
    print(f"TIER 1 CONTENT-BASED EVALUATION COMPLETED IN {total_time:.2f}s ({total_time/60.0:.2f}m)")
    print("=" * 70)
    return
    print("\n" + "=" * 70)
    print("PART C: TIER 2 SNAPSHOT EXPERIMENT (EXPLICIT TEMPORAL LEAKAGE NOTICE)")
    print("=" * 70)
    leakage_warning = (
        "CRITICAL TEMPORAL LEAKAGE NOTICE: Tier 2 features (Tags and Tag Genome) were aggregated over "
        "the entire MovieLens history up to November 2019. Because user tags and genome scores encapsulate "
        "future post-release information, Tier 2 features leak semantic signals across chronological splits. "
        "These results are reported in a separate experiment labeled snapshot_features=true and must never "
        "be mixed into Tier 1 clean temporal results."
    )
    print(leakage_warning)

    chosen_p_var = best_t1_record["profile_variant"]
    chosen_idf = best_t1_record["use_genre_idf"]
    chosen_wyr = best_t1_record["year_weight"]

    tier2_configs = [
        # T1 + tags
        {"name": "t1_plus_tags_w0.5", "weights": {"tier1": 1.0, "tags": 0.5, "genome": 0.0}},
        {"name": "t1_plus_tags_w1.0", "weights": {"tier1": 1.0, "tags": 1.0, "genome": 0.0}},
        {"name": "t1_plus_tags_w2.0", "weights": {"tier1": 1.0, "tags": 2.0, "genome": 0.0}},
        {"name": "t1_0.5_plus_tags_1.0", "weights": {"tier1": 0.5, "tags": 1.0, "genome": 0.0}},
        # T1 + genome
        {"name": "t1_plus_genome_w0.5", "weights": {"tier1": 1.0, "tags": 0.0, "genome": 0.5}},
        {"name": "t1_plus_genome_w1.0", "weights": {"tier1": 1.0, "tags": 0.0, "genome": 1.0}},
        {"name": "t1_plus_genome_w2.0", "weights": {"tier1": 1.0, "tags": 0.0, "genome": 2.0}},
        {"name": "t1_0.5_plus_genome_1.0", "weights": {"tier1": 0.5, "tags": 0.0, "genome": 1.0}},
        # T1 + tags + genome
        {"name": "t1_tags_genome_all1.0", "weights": {"tier1": 1.0, "tags": 1.0, "genome": 1.0}},
        {"name": "t1_tags1.0_genome2.0", "weights": {"tier1": 1.0, "tags": 1.0, "genome": 2.0}},
        {"name": "t1_tags2.0_genome1.0", "weights": {"tier1": 1.0, "tags": 2.0, "genome": 1.0}},
        {"name": "t1_tags0.5_genome1.0", "weights": {"tier1": 1.0, "tags": 0.5, "genome": 1.0}},
        {"name": "t1_0.5_tags1.0_genome2.0", "weights": {"tier1": 0.5, "tags": 1.0, "genome": 2.0}},
    ]

    tier2_grid_results = []
    best_t2_record = None
    best_t2_ndcg = -1.0

    print(f"\n{'Config Name':<26} | {'Weights (T1, Tags, Gen)':<24} | {'NDCG@10':<8} | {'P@10':<8} | {'R@10':<8} | {'HR@10':<8}")
    print("-" * 88)

    for cfg in tier2_configs:
        t2_model = ContentBasedRecommender(
            profile_variant=chosen_p_var,
            use_genre_idf=chosen_idf,
            year_weight=chosen_wyr,
            missing_year_weight=0.0,
            positive_threshold=pos_thresh,
            tier=2,
            tier2_block_weights=cfg["weights"],
            feature_dir=feat_dir,
        )
        t2_model.fit(train_df, context=sample_fit_context)
        res = evaluator_sample.evaluate(t2_model, store_per_user_metrics=False)

        w_str = f"({cfg['weights']['tier1']}, {cfg['weights']['tags']}, {cfg['weights']['genome']})"
        rec = {
            "snapshot_features": True,
            "name": cfg["name"],
            "tier2_block_weights": cfg["weights"],
            "ndcg": round(res.ndcg.mean, 6),
            "precision": round(res.precision.mean, 6),
            "recall": round(res.recall.mean, 6),
            "hit_rate": round(res.hit_rate.mean, 6),
            "mrr": round(res.mrr.mean, 6),
            "catalog_coverage": round(res.catalog_coverage, 6),
            "zero_profile_users": t2_model.n_zero_profile_users,
        }
        tier2_grid_results.append(rec)

        print(
            f"{cfg['name']:<26} | {w_str:<24} | "
            f"{res.ndcg.mean:<8.4f} | {res.precision.mean:<8.4f} | "
            f"{res.recall.mean:<8.4f} | {res.hit_rate.mean:<8.4f}"
        )

        if res.ndcg.mean > best_t2_ndcg:
            best_t2_ndcg = res.ndcg.mean
            best_t2_record = rec

    print("-" * 88)
    print(f"BEST TIER 2 SNAPSHOT CONFIG: {best_t2_record['name']} (NDCG@10 = {best_t2_ndcg:.6f})")

    # Evaluate Best Tier 2 on all validation users
    print("\nEVALUATING BEST TIER 2 ON ALL VALIDATION USERS (94,312 USERS)...")
    best_t2_model = ContentBasedRecommender(
        profile_variant=chosen_p_var,
        use_genre_idf=chosen_idf,
        year_weight=chosen_wyr,
        missing_year_weight=0.0,
        positive_threshold=pos_thresh,
        tier=2,
        tier2_block_weights=best_t2_record["tier2_block_weights"],
        feature_dir=feat_dir,
    )
    t_fit_t2 = time.time()
    best_t2_model.fit(train_df, context=full_fit_context)
    print(f"Fitted Best Tier 2 model in {time.time() - t_fit_t2:.2f}s")

    t_eval_t2 = time.time()
    best_t2_res = evaluator_full.evaluate(best_t2_model, store_per_user_metrics=True)
    print(f"Evaluated Best Tier 2 on full validation in {time.time() - t_eval_t2:.2f}s")

    # Genome recommendation coverage
    genome_cov = compute_genome_recommendation_coverage(evaluator_full, best_t2_model, feat_dir)
    print(f"Genome coverage among recommendations: {genome_cov:.4%}")

    print("\nTIER 2 SNAPSHOT VALIDATION PERFORMANCE (WITH 95% BOOTSTRAP CIs):")
    print(f"  Precision@10: {best_t2_res.precision.mean:.4f} [{best_t2_res.precision.ci_lower:.4f}, {best_t2_res.precision.ci_upper:.4f}]")
    print(f"  Recall@10:    {best_t2_res.recall.mean:.4f} [{best_t2_res.recall.ci_lower:.4f}, {best_t2_res.recall.ci_upper:.4f}]")
    print(f"  NDCG@10:      {best_t2_res.ndcg.mean:.4f} [{best_t2_res.ndcg.ci_lower:.4f}, {best_t2_res.ndcg.ci_upper:.4f}]")
    print(f"  HitRate@10:   {best_t2_res.hit_rate.mean:.4f} [{best_t2_res.hit_rate.ci_lower:.4f}, {best_t2_res.hit_rate.ci_upper:.4f}]")
    print(f"  MRR@10:       {best_t2_res.mrr.mean:.4f} [{best_t2_res.mrr.ci_lower:.4f}, {best_t2_res.mrr.ci_upper:.4f}]")
    print(f"  Coverage:     {best_t2_res.catalog_coverage:.4f}")
    print(f"  Mean Pop:     {best_t2_res.mean_recommended_popularity.mean:.1f}")

    # Paired comparisons: Tier 2 vs Tier 1, and Tier 2 vs Popularity
    print("\nPAIRED STATISTICAL COMPARISON: TIER 2 SNAPSHOT vs TIER 1")
    t2_vs_t1 = {}
    for m_col in ["ndcg", "hit_rate", "recall"]:
        comp = Evaluator.compare(
            best_t2_res.per_user_metrics[m_col],
            best_t1_res.per_user_metrics[m_col],
            metric=f"{m_col.upper()}@10",
        )
        dist_str = "YES (p < 0.05)" if comp.is_distinguishable_from_zero else "NO (p >= 0.05)"
        print(f"  {comp.metric:<12}: Diff={comp.mean_diff:+.6f} [95% CI: {comp.ci_lower:+.6f}, {comp.ci_upper:+.6f}] | Lift={comp.relative_lift:+.2%} | Distinguishable={dist_str}")
        t2_vs_t1[m_col] = {
            "metric": comp.metric,
            "mean_diff": round(comp.mean_diff, 6),
            "ci_lower": round(comp.ci_lower, 6),
            "ci_upper": round(comp.ci_upper, 6),
            "relative_lift": round(comp.relative_lift, 4),
            "pct_tier2_better": round(comp.pct_a_better, 2),
            "pct_equal": round(comp.pct_equal, 2),
            "pct_tier1_better": round(comp.pct_b_better, 2),
            "distinguishable_from_zero": comp.is_distinguishable_from_zero,
        }

    print("\nPAIRED STATISTICAL COMPARISON: TIER 2 SNAPSHOT vs POPULARITY (MOST_LIKED)")
    t2_vs_pop = {}
    for m_col in ["ndcg", "hit_rate", "recall"]:
        comp = Evaluator.compare(
            best_t2_res.per_user_metrics[m_col],
            pop_res.per_user_metrics[m_col],
            metric=f"{m_col.upper()}@10",
        )
        dist_str = "YES (p < 0.05)" if comp.is_distinguishable_from_zero else "NO (p >= 0.05)"
        print(f"  {comp.metric:<12}: Diff={comp.mean_diff:+.6f} [95% CI: {comp.ci_lower:+.6f}, {comp.ci_upper:+.6f}] | Lift={comp.relative_lift:+.2%} | Distinguishable={dist_str}")
        t2_vs_pop[m_col] = {
            "metric": comp.metric,
            "mean_diff": round(comp.mean_diff, 6),
            "ci_lower": round(comp.ci_lower, 6),
            "ci_upper": round(comp.ci_upper, 6),
            "relative_lift": round(comp.relative_lift, 4),
            "pct_tier2_better": round(comp.pct_a_better, 2),
            "pct_equal": round(comp.pct_equal, 2),
            "pct_pop_better": round(comp.pct_b_better, 2),
            "distinguishable_from_zero": comp.is_distinguishable_from_zero,
        }

    # Save Tier 2 results
    t2_output = {
        "snapshot_features": True,
        "snapshot_leakage_warning": leakage_warning,
        "metadata": {
            "dataset": dataset_name,
            "timestamp": timestamp,
            "git_commit": git_hash,
            "positive_threshold": pos_thresh,
            "train_content_hash": train_hash,
            "validation_content_hash": val_hash,
            "packages": pkg_versions,
            "tuning_sample_size": sample_size,
            "tuning_seed": sample_seed,
            "total_runtime_seconds": round(time.time() - start_total_time, 2),
        },
        "chosen_config": best_t2_record,
        "tuning_grid_results": tier2_grid_results,
        "full_validation_metrics": {
            "snapshot_features": True,
            "precision": format_summary(best_t2_res.precision),
            "recall": format_summary(best_t2_res.recall),
            "ndcg": format_summary(best_t2_res.ndcg),
            "hit_rate": format_summary(best_t2_res.hit_rate),
            "mrr": format_summary(best_t2_res.mrr),
            "catalog_coverage": round(float(best_t2_res.catalog_coverage), 6),
            "genome_coverage_among_recommendations": round(genome_cov, 6),
            "mean_recommended_popularity": format_summary(best_t2_res.mean_recommended_popularity),
            "zero_profile_users": best_t2_model.n_zero_profile_users,
            "activity_breakdown": best_t2_res.activity_breakdown,
            "session_strata_breakdown": best_t2_res.session_strata_breakdown,
        },
        "paired_comparison_vs_tier1": t2_vs_t1,
        "paired_comparison_vs_popularity_most_liked": t2_vs_pop,
    }

    t2_json_path = results_dir / "content_tier2_snapshot_validation.json"
    with open(t2_json_path, "w", encoding="utf-8") as f:
        json.dump(t2_output, f, indent=2)
    print(f"\nSaved Tier 2 results JSON to: {t2_json_path}")

    # CSV summary for Tier 2
    t2_csv_df = pd.DataFrame(tier2_grid_results)
    t2_csv_path = results_dir / "content_tier2_snapshot_validation.csv"
    t2_csv_df.to_csv(t2_csv_path, index=False)
    print(f"Saved Tier 2 CSV summary to: {t2_csv_path}")

    total_time = time.time() - start_total_time
    print("\n" + "=" * 70)
    print(f"CONTENT-BASED EVALUATION COMPLETED IN {total_time:.2f}s ({total_time/60.0:.2f}m)")
    print("=" * 70)


if __name__ == "__main__":
    main()
