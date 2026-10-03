"""Runner script for Popularity Baseline (Model 0) evaluation on VALIDATION split.

Evaluates:
- Rating-prediction baselines (global_mean, movie_mean, damped_movie_mean) -> RMSE/MAE
- Ranking popularity variants:
  1. most_rated
  2. most_liked
  3. damped_mean tuned over m in [0, 5, 10, 25, 50, 100, 250, 500]
- Sampled user comparison vs full validation run with bootstrap CI comparison
- Generates JSON and CSV artifacts in recommender/results/
"""

import datetime
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List

# Ensure project root is on sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import numpy as np
import pandas as pd
import scipy
import pyarrow
import pytest


from recommender.baselines.popularity import (
    PopularityRecommender,
    PopularityVariant,
)
from recommender.evaluation.evaluator import (
    EvaluationResult,
    Evaluator,
    evaluate_rating_prediction,
)
from recommender.evaluation.protocol import (
    EvaluationConfig,
    build_evaluation_context,
)
from recommender.preprocessing.utils import (
    compute_dataframe_content_hash,
    load_dataset_config,
)


def get_git_commit_hash(root_dir: Path) -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "git-unavailable"


def get_git_dirty_flag(root_dir: Path) -> bool:
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        return len(res.stdout.strip()) > 0
    except Exception:
        return True


def format_summary(s) -> Dict[str, float]:
    return {
        "mean": round(float(s.mean), 6),
        "ci_lower": round(float(s.ci_lower), 6),
        "ci_upper": round(float(s.ci_upper), 6),
    }


def main():
    start_total_time = time.time()
    root_dir = Path(__file__).resolve().parent.parent.parent
    dataset_name = "ml-25m"
    splits_dir = root_dir / "data" / "processed" / dataset_name / "splits"
    results_dir = root_dir / "recommender" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"MOIEREC POPULARITY BASELINE (MODEL 0) VALIDATION RUN — {dataset_name}")
    print("=" * 70)

    # 1. Config and metadata
    cfg = load_dataset_config(dataset_name)
    pos_thresh = float(cfg.get("positive_threshold", 4.0))
    git_hash = get_git_commit_hash(root_dir)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    pkg_versions = {
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "pyarrow": pyarrow.__version__,
        "pytest": pytest.__version__,
    }

    print(f"Timestamp: {timestamp}")
    print(f"Git commit: {git_hash}")
    print(f"Positive threshold: {pos_thresh}")
    print(f"Packages: {pkg_versions}")

    # 2. Load TRAIN and VALIDATION splits only (GUARD: NEVER load test.parquet)
    print("\nLoading TRAIN and VALIDATION splits...")
    train_path = splits_dir / "train.parquet"
    val_path = splits_dir / "validation.parquet"

    t0 = time.time()
    train_df = pd.read_parquet(train_path)
    val_df = pd.read_parquet(val_path)
    print(f"Loaded train ({len(train_df):,} rows) and validation ({len(val_df):,} rows) in {time.time() - t0:.2f}s")

    train_hash = compute_dataframe_content_hash(train_df)
    val_hash = compute_dataframe_content_hash(val_df)
    print(f"Train content hash:      {train_hash}")
    print(f"Validation content hash: {val_hash}")

    # 3. Rating prediction baselines on VALIDATION (anchor RMSE/MAE)
    print("\n" + "-" * 70)
    print("PART B5: RATING-PREDICTION BASELINES (VALIDATION RMSE / MAE)")
    print("-" * 70)
    rating_pred_results = []
    for method in ["global_mean", "movie_mean"]:
        res_rp = evaluate_rating_prediction(train_df, val_df, method=method)
        rating_pred_results.append(res_rp)
        print(f"  {method:<16}: RMSE={res_rp['rmse']:.4f}, MAE={res_rp['mae']:.4f}")

    for damping_val in [10.0, 25.0, 50.0]:
        res_rp = evaluate_rating_prediction(train_df, val_df, method="damped_movie_mean", damping=damping_val)
        rating_pred_results.append(res_rp)
        print(f"  damped_mean(m={int(damping_val)}): RMSE={res_rp['rmse']:.4f}, MAE={res_rp['mae']:.4f}")

    # 4. Build Evaluation Context on full validation set
    print("\n" + "-" * 70)
    print("BUILDING FULL VALIDATION EVALUATION CONTEXT...")
    print("-" * 70)
    bench_ratings_path = root_dir / "data" / "processed" / dataset_name / "benchmark" / "ratings.parquet"
    if bench_ratings_path.exists():
        print("Loading benchmark rating timestamps for exact session-span calculation...")
        b_df = pd.read_parquet(bench_ratings_path, columns=["user_id", "timestamp"])
        b_spans = b_df.groupby("user_id")["timestamp"].agg(["min", "max"])
        spans_dict = ((b_spans["max"] - b_spans["min"]) / 86400.0).to_dict()
    else:
        spans_dict = None

    t_ctx = time.time()
    ctx_full = build_evaluation_context(
        train_df,
        val_df,
        mode="validation",
        positive_threshold=pos_thresh,
        user_history_spans=spans_dict,
    )
    print(f"Context constructed in {time.time() - t_ctx:.2f}s:")
    print(f"  Candidate catalog items (train rated >= 1): {ctx_full.n_candidates:,}")
    print(f"  Total validation users:                      {ctx_full.total_split_users:,}")
    print(f"  Evaluated validation users (reachables >= 1): {ctx_full.n_evaluated_users:,}")
    print(f"  Excluded validation users (zero reachables): {ctx_full.excluded_zero_pos_users_count:,}")
    print(f"  Total validation positives:                  {ctx_full.total_split_positives:,}")
    print(f"  Unreachable validation positives (dropped):  {ctx_full.unreachable_positives_count:,} ({ctx_full.unreachable_positives_pct:.4f}%)")

    # 5. Grid search over popularity variants on full validation set
    print("\n" + "-" * 70)
    print("RUNNING POPULARITY VARIANTS GRID SEARCH (FULL VALIDATION)...")
    print("-" * 70)
    eval_cfg = EvaluationConfig(positive_threshold=pos_thresh, k=10, batch_size=2000, seed=42, n_bootstrap=1000)
    evaluator_full = Evaluator(ctx_full, eval_cfg)

    # Grid specification (including extended damping grid: 1000, 2500, 5000, 10000)
    variants_to_eval = [
        {"name": "most_rated", "variant": PopularityVariant.MOST_RATED, "damping": 0.0},
        {"name": "most_liked", "variant": PopularityVariant.MOST_LIKED, "damping": 0.0},
    ]
    damping_grid = [0, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
    for m in damping_grid:
        variants_to_eval.append({
            "name": f"damped_mean_m{m}",
            "variant": PopularityVariant.DAMPED_MEAN,
            "damping": float(m),
        })

    grid_results = []
    best_variant_record = None
    best_ndcg = -1.0
    saved_per_user_runs = {}

    print(f"{'Variant':<20} | {'P@10':<8} | {'R@10':<8} | {'NDCG@10':<8} | {'HR@10':<8} | {'MRR@10':<8} | {'Coverage':<8} | {'Mean Pop':<8}")
    print("-" * 95)

    for item in variants_to_eval:
        v_name = item["name"]
        variant_enum = item["variant"]
        m_val = item["damping"]

        model = PopularityRecommender(variant=variant_enum, damping=m_val, positive_threshold=pos_thresh)
        model.fit(train_df, context={"candidate_movie_ids": ctx_full.candidate_movie_ids})

        t_eval = time.time()
        res = evaluator_full.evaluate(model, store_per_user_metrics=True)
        eval_time = time.time() - t_eval

        if v_name in ("most_rated", "most_liked"):
            saved_per_user_runs[v_name] = res.per_user_metrics

        record = {
            "variant_name": v_name,
            "variant_type": variant_enum.value,
            "damping_m": m_val,
            "precision": format_summary(res.precision),
            "recall": format_summary(res.recall),
            "ndcg": format_summary(res.ndcg),
            "hit_rate": format_summary(res.hit_rate),
            "mrr": format_summary(res.mrr),
            "catalog_coverage": round(float(res.catalog_coverage), 6),
            "mean_recommended_popularity": format_summary(res.mean_recommended_popularity),
            "activity_breakdown": res.activity_breakdown,
            "session_strata_breakdown": res.session_strata_breakdown,
            "eval_runtime_seconds": round(eval_time, 2),
        }
        grid_results.append(record)

        print(
            f"{v_name:<20} | "
            f"{res.precision.mean:<8.4f} | "
            f"{res.recall.mean:<8.4f} | "
            f"{res.ndcg.mean:<8.4f} | "
            f"{res.hit_rate.mean:<8.4f} | "
            f"{res.mrr.mean:<8.4f} | "
            f"{res.catalog_coverage:<8.4f} | "
            f"{res.mean_recommended_popularity.mean:<8.1f}"
        )

        if res.ndcg.mean > best_ndcg:
            best_ndcg = res.ndcg.mean
            best_variant_record = record

    print("-" * 95)
    print(f"BEST VARIANT: {best_variant_record['variant_name']} with NDCG@10 = {best_ndcg:.6f}")

    # 6. Paired Statistical Comparison: most_liked vs most_rated (Part A7)
    print("\n" + "-" * 70)
    print("PAIRED COMPARISON: most_liked vs most_rated (ALL VALIDATION USERS)")
    print("-" * 70)
    paired_comparisons = {}
    for m_col in ["ndcg", "hit_rate", "recall"]:
        comp_res = Evaluator.compare(
            saved_per_user_runs["most_liked"][m_col],
            saved_per_user_runs["most_rated"][m_col],
            metric=f"{m_col.upper()}@10",
        )
        dist_str = "YES (p < 0.05)" if comp_res.is_distinguishable_from_zero else "NO (p >= 0.05)"
        print(f"  {comp_res.metric:<12}: Diff={comp_res.mean_diff:+.6f} [95% CI: {comp_res.ci_lower:+.6f}, {comp_res.ci_upper:+.6f}] | Lift={comp_res.relative_lift:+.2%} | Distinguishable={dist_str}")
        print(f"               Liked>Rated: {comp_res.pct_a_better:.2f}% | Equal: {comp_res.pct_equal:.2f}% | Liked<Rated: {comp_res.pct_b_better:.2f}%")
        paired_comparisons[m_col] = {
            "metric": comp_res.metric,
            "mean_diff": round(comp_res.mean_diff, 6),
            "ci_lower": round(comp_res.ci_lower, 6),
            "ci_upper": round(comp_res.ci_upper, 6),
            "relative_lift": round(comp_res.relative_lift, 4),
            "pct_liked_better": round(comp_res.pct_a_better, 2),
            "pct_equal": round(comp_res.pct_equal, 2),
            "pct_rated_better": round(comp_res.pct_b_better, 2),
            "is_distinguishable_from_zero": comp_res.is_distinguishable_from_zero,
        }


    # 6. Sampled user validation comparison & reproducibility check
    print("\n" + "-" * 70)
    print("SAMPLED USER EVALUATION (REPRODUCIBILITY & ABSOLUTE DIFFERENCE)...")
    print("-" * 70)
    sample_size = 5000
    sample_seed = 42

    ctx_sample = build_evaluation_context(
        train_df,
        val_df,
        mode="validation",
        positive_threshold=pos_thresh,
        sample_users=sample_size,
        seed=sample_seed,
    )
    evaluator_sample = Evaluator(ctx_sample, eval_cfg)

    best_model = PopularityRecommender(
        variant=best_variant_record["variant_type"],
        damping=best_variant_record["damping_m"],
        positive_threshold=pos_thresh,
    )
    best_model.fit(train_df, context={"candidate_movie_ids": ctx_sample.candidate_movie_ids})

    # Run 1 on sample
    res_s1 = evaluator_sample.evaluate(best_model)
    # Run 2 on sample to assert exact reproducibility
    res_s2 = evaluator_sample.evaluate(best_model)

    assert res_s1.ndcg.mean == res_s2.ndcg.mean, "Sampled user evaluation non-deterministic!"
    assert res_s1.precision.mean == res_s2.precision.mean, "Sampled user evaluation non-deterministic!"
    print(f"Sampled-user mode verified: identical results across repeated runs with seed={sample_seed}.")

    # Compute absolute differences between sample and full run
    sample_metrics = {
        "precision": format_summary(res_s1.precision),
        "recall": format_summary(res_s1.recall),
        "ndcg": format_summary(res_s1.ndcg),
        "hit_rate": format_summary(res_s1.hit_rate),
        "mrr": format_summary(res_s1.mrr),
        "mean_recommended_popularity": format_summary(res_s1.mean_recommended_popularity),
    }

    sample_vs_full_diff = {}
    print(f"{'Metric':<15} | {'Full Mean':<10} | {'Sample Mean':<12} | {'Abs Diff':<10} | {'Sample 95% CI':<20}")
    print("-" * 75)
    for m_key in ["precision", "recall", "ndcg", "hit_rate", "mrr", "mean_recommended_popularity"]:
        full_val = best_variant_record[m_key]["mean"]
        samp_val = sample_metrics[m_key]["mean"]
        diff = abs(samp_val - full_val)
        ci_str = f"[{sample_metrics[m_key]['ci_lower']:.4f}, {sample_metrics[m_key]['ci_upper']:.4f}]"
        sample_vs_full_diff[m_key] = {
            "full_mean": full_val,
            "sample_mean": samp_val,
            "abs_difference": round(diff, 6),
            "sample_ci": [sample_metrics[m_key]["ci_lower"], sample_metrics[m_key]["ci_upper"]],
        }
        print(f"{m_key:<15} | {full_val:<10.4f} | {samp_val:<12.4f} | {diff:<10.6f} | {ci_str:<20}")

    # 7. Save outputs
    total_elapsed = time.time() - start_total_time
    output_data = {
        "metadata": {
            "dataset": dataset_name,
            "timestamp": timestamp,
            "git_commit": git_hash,
            "dirty_working_tree": get_git_dirty_flag(root_dir),
            "positive_threshold": pos_thresh,
            "tie_break": eval_cfg.tie_break,
            "train_content_hash": train_hash,
            "validation_content_hash": val_hash,
            "packages": pkg_versions,
            "total_runtime_seconds": round(total_elapsed, 2),
        },
        "catalog_and_split_stats": {
            "n_candidate_items": ctx_full.n_candidates,
            "total_validation_users": ctx_full.total_split_users,
            "evaluated_validation_users": ctx_full.n_evaluated_users,
            "excluded_zero_pos_users": ctx_full.excluded_zero_pos_users_count,
            "total_validation_positives": ctx_full.total_split_positives,
            "unreachable_validation_positives": ctx_full.unreachable_positives_count,
            "unreachable_validation_positives_pct": round(ctx_full.unreachable_positives_pct, 4),
        },
        "rating_prediction_baselines": rating_pred_results,
        "popularity_tuning_grid": grid_results,
        "best_variant": best_variant_record,
        "paired_comparison_most_liked_vs_most_rated": paired_comparisons,
        "sample_vs_full_comparison": {

            "sample_users": sample_size,
            "seed": sample_seed,
            "differences": sample_vs_full_diff,
        },
    }

    json_path = results_dir / "popularity_validation.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    print(f"\nSaved complete results JSON to: {json_path}")

    # CSV summary table
    csv_rows = []
    for item in grid_results:
        csv_rows.append({
            "variant": item["variant_name"],
            "type": item["variant_type"],
            "damping_m": item["damping_m"],
            "ndcg_10": item["ndcg"]["mean"],
            "ndcg_10_ci_lower": item["ndcg"]["ci_lower"],
            "ndcg_10_ci_upper": item["ndcg"]["ci_upper"],
            "precision_10": item["precision"]["mean"],
            "recall_10": item["recall"]["mean"],
            "hit_rate_10": item["hit_rate"]["mean"],
            "mrr_10": item["mrr"]["mean"],
            "catalog_coverage": item["catalog_coverage"],
            "mean_recommended_popularity": item["mean_recommended_popularity"]["mean"],
            "eval_runtime_seconds": item["eval_runtime_seconds"],
        })
    csv_df = pd.DataFrame(csv_rows)
    csv_path = results_dir / "popularity_validation.csv"
    csv_df.to_csv(csv_path, index=False)
    print(f"Saved CSV summary to: {csv_path}")


if __name__ == "__main__":
    main()
