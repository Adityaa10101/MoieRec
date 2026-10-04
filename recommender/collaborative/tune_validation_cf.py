"""Warm validation grid search and evaluation for Item-Item Collaborative Filtering.

Phase 2G-Lite (Part A2):
- Tuning on 20,000-user validation sample over 18 options:
    a in {0.5, 0.7}, lambda in {0, 20, 100}, k in {50, 100, 200}.
- Chosen config evaluated on ALL validation users (94,312 users) with 1000 bootstrap resamples.
- Strata: activity quartiles, session span.
- Paired statistical comparisons vs:
    (1) Popularity (most_liked)
    (2) Tier 2 content-only model on the same split.
- Catalog coverage and mean recommended popularity.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from recommender.baselines.popularity import PopularityRecommender, PopularityVariant
from recommender.collaborative.item_cf import ItemItemCollaborativeRecommender
from recommender.content_based.model import ContentBasedRecommender, ProfileVariant
from recommender.evaluation import (
    EvaluationConfig,
    Evaluator,
    MetricSummary,
    build_evaluation_context,
)
from recommender.preprocessing.utils import compute_dataframe_content_hash


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


def run_tuning_and_evaluation() -> None:
    start_total_time = time.time()
    root_dir = Path(__file__).resolve().parent.parent.parent
    data_dir = root_dir / "data" / "processed" / "ml-25m"
    splits_dir = data_dir / "splits"
    feat_dir = data_dir / "features"
    results_dir = root_dir / "recommender" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    git_hash = get_git_commit_hash(root_dir)
    is_dirty = get_git_dirty_flag(root_dir)
    timestamp = datetime.now(timezone.utc).isoformat()

    print("=" * 80)
    print("PHASE 2G-LITE: ITEM-ITEM COLLABORATIVE FILTERING VALIDATION TUNING")
    print(f"Timestamp: {timestamp} | Commit: {git_hash[:8]} | Dirty: {is_dirty}")
    print("=" * 80)

    # 1. Load splits
    print("\nLoading datasets...")
    train_df = pd.read_parquet(splits_dir / "train.parquet")
    val_df = pd.read_parquet(splits_dir / "validation.parquet")
    train_hash = compute_dataframe_content_hash(train_df)
    val_hash = compute_dataframe_content_hash(val_df)
    print(f"Train: {len(train_df):,} rows (hash: {train_hash[:12]})")
    print(f"Val:   {len(val_df):,} rows (hash: {val_hash[:12]})")

    # History spans for session strata
    bench_ratings_path = data_dir / "benchmark" / "ratings.parquet"
    if bench_ratings_path.exists():
        ratings_bench = pd.read_parquet(bench_ratings_path, columns=["user_id", "timestamp"])
        user_min_max = ratings_bench.groupby("user_id")["timestamp"].agg(["min", "max"])
        spans_series = (user_min_max["max"] - user_min_max["min"]) / 86400.0
        spans_dict = spans_series.to_dict()
    else:
        spans_dict = None

    pos_thresh = 4.0
    sample_size = 20000
    sample_seed = 42

    # 2. Build 20k Sample Context
    print(f"\nBuilding 20k validation evaluation context (seed={sample_seed})...")
    ctx_sample = build_evaluation_context(
        train_df,
        val_df,
        mode="validation",
        positive_threshold=pos_thresh,
        sample_users=sample_size,
        seed=sample_seed,
        user_history_spans=spans_dict,
    )
    eval_cfg_sample = EvaluationConfig(
        positive_threshold=pos_thresh,
        k=10,
        batch_size=2000,
        seed=sample_seed,
        n_bootstrap=200,
    )
    evaluator_sample = Evaluator(ctx_sample, eval_cfg_sample)

    sample_context_dict = {
        "candidate_movie_ids": ctx_sample.candidate_movie_ids,
        "user_id_to_eval_idx": ctx_sample.user_id_to_eval_idx,
        "eval_user_ids": ctx_sample.eval_user_ids,
    }

    # 3. Grid Search over 18 options
    print("\n" + "=" * 80)
    print("GRID SEARCH (20,000 VALIDATION USERS, 18 COMBINATIONS)")
    print("=" * 80)
    print(f"{'a':<5} | {'lambda':<6} | {'k':<5} | {'NDCG@10':<9} | {'P@10':<8} | {'R@10':<8} | {'HR@10':<8} | {'Cov':<7} | {'Mean Pop':<9}")
    print("-" * 88)

    grid_cache_path = data_dir / "collaborative" / "cf_tuning_grid.json"
    grid_results = []
    best_config = None
    best_ndcg = -1.0

    if grid_cache_path.exists():
        print(f"Loading cached grid search results from {grid_cache_path}...")
        with open(grid_cache_path, "r", encoding="utf-8") as f:
            grid_results = json.load(f)
        for entry in grid_results:
            print(
                f"{entry['a']:<5.1f} | {entry['shrinkage']:<6.0f} | {entry['k']:<5} | {entry['ndcg']:<9.6f} | "
                f"{entry['precision']:<8.4f} | {entry['recall']:<8.4f} | "
                f"{entry['hit_rate']:<8.4f} | {entry['catalog_coverage']:<7.4f} | "
                f"{entry['mean_recommended_popularity']:<9.1f}"
            )
            if entry["ndcg"] > best_ndcg:
                best_ndcg = entry["ndcg"]
                best_config = entry
    else:
        a_options = [0.5, 0.7]
        lam_options = [0.0, 20.0, 100.0]
        k_options = [50, 100, 200]

        for a in a_options:
            for lam in lam_options:
                for k in k_options:
                    t0 = time.time()
                    cf_model = ItemItemCollaborativeRecommender(
                        a=a,
                        shrinkage=lam,
                        k=k,
                        positive_threshold=pos_thresh,
                    )
                    cf_model.fit(train_df, context=sample_context_dict)
                    res = evaluator_sample.evaluate(cf_model, store_per_user_metrics=False)
                    elapsed = time.time() - t0

                    entry = {
                        "a": a,
                        "shrinkage": lam,
                        "k": k,
                        "ndcg": round(float(res.ndcg.mean), 6),
                        "precision": round(float(res.precision.mean), 6),
                        "recall": round(float(res.recall.mean), 6),
                        "hit_rate": round(float(res.hit_rate.mean), 6),
                        "mrr": round(float(res.mrr.mean), 6),
                        "catalog_coverage": round(float(res.catalog_coverage), 6),
                        "mean_recommended_popularity": round(float(res.mean_recommended_popularity.mean), 2),
                        "elapsed_seconds": round(elapsed, 2),
                    }
                    grid_results.append(entry)

                    print(
                        f"{a:<5.1f} | {lam:<6.0f} | {k:<5} | {entry['ndcg']:<9.6f} | "
                        f"{entry['precision']:<8.4f} | {entry['recall']:<8.4f} | "
                        f"{entry['hit_rate']:<8.4f} | {entry['catalog_coverage']:<7.4f} | "
                        f"{entry['mean_recommended_popularity']:<9.1f}"
                    )

                    if entry["ndcg"] > best_ndcg:
                        best_ndcg = entry["ndcg"]
                        best_config = entry

        with open(grid_cache_path, "w", encoding="utf-8") as f:
            json.dump(grid_results, f, indent=2)

    print("-" * 88)
    print(f"CHOSEN CONFIG: a={best_config['a']}, lambda={best_config['shrinkage']}, k={best_config['k']} (NDCG@10 = {best_ndcg:.6f})")

    # 4. Evaluate Chosen Config on ALL Validation Users
    print("\n" + "=" * 80)
    print("EVALUATING CHOSEN CONFIG ON ALL VALIDATION USERS (94,312 USERS, 1000 BOOTSTRAP)...")
    print("=" * 80)

    ctx_full = build_evaluation_context(
        train_df,
        val_df,
        mode="validation",
        positive_threshold=pos_thresh,
        user_history_spans=spans_dict,
    )
    eval_cfg_full = EvaluationConfig(
        positive_threshold=pos_thresh,
        k=10,
        batch_size=2000,
        seed=42,
        n_bootstrap=1000,
    )
    evaluator_full = Evaluator(ctx_full, eval_cfg_full)

    full_context_dict = {
        "candidate_movie_ids": ctx_full.candidate_movie_ids,
        "user_id_to_eval_idx": ctx_full.user_id_to_eval_idx,
        "eval_user_ids": ctx_full.eval_user_ids,
    }

    best_cf_model = ItemItemCollaborativeRecommender(
        a=best_config["a"],
        shrinkage=best_config["shrinkage"],
        k=best_config["k"],
        positive_threshold=pos_thresh,
    )
    t_fit = time.time()
    best_cf_model.fit(train_df, context=full_context_dict)
    print(f"Fitted Best CF model on full train in {time.time() - t_fit:.2f}s")

    t_eval = time.time()
    cf_res = evaluator_full.evaluate(best_cf_model, store_per_user_metrics=True)
    print(f"Evaluated Best CF on full validation in {time.time() - t_eval:.2f}s")

    print("\nCHOSEN CF MODEL FULL VALIDATION PERFORMANCE (95% BOOTSTRAP CIs):")
    print(f"  Precision@10: {cf_res.precision.mean:.4f} [{cf_res.precision.ci_lower:.4f}, {cf_res.precision.ci_upper:.4f}]")
    print(f"  Recall@10:    {cf_res.recall.mean:.4f} [{cf_res.recall.ci_lower:.4f}, {cf_res.recall.ci_upper:.4f}]")
    print(f"  NDCG@10:      {cf_res.ndcg.mean:.4f} [{cf_res.ndcg.ci_lower:.4f}, {cf_res.ndcg.ci_upper:.4f}]")
    print(f"  HitRate@10:   {cf_res.hit_rate.mean:.4f} [{cf_res.hit_rate.ci_lower:.4f}, {cf_res.hit_rate.ci_upper:.4f}]")
    print(f"  MRR@10:       {cf_res.mrr.mean:.4f} [{cf_res.mrr.ci_lower:.4f}, {cf_res.mrr.ci_upper:.4f}]")
    print(f"  Coverage:     {cf_res.catalog_coverage:.4f}")
    print(f"  Mean Pop:     {cf_res.mean_recommended_popularity.mean:.1f} [{cf_res.mean_recommended_popularity.ci_lower:.1f}, {cf_res.mean_recommended_popularity.ci_upper:.1f}]")

    # 5. Popularity baseline on same split
    print("\nEvaluating Popularity baseline (most_liked) on full validation...")
    pop_model = PopularityRecommender(variant=PopularityVariant.MOST_LIKED, positive_threshold=pos_thresh)
    pop_model.fit(train_df, context={"candidate_movie_ids": ctx_full.candidate_movie_ids})
    pop_res = evaluator_full.evaluate(pop_model, store_per_user_metrics=True)

    print("\nPOPULARITY (MOST_LIKED) FULL VALIDATION PERFORMANCE:")
    print(f"  NDCG@10:      {pop_res.ndcg.mean:.4f} [{pop_res.ndcg.ci_lower:.4f}, {pop_res.ndcg.ci_upper:.4f}]")
    print(f"  HitRate@10:   {pop_res.hit_rate.mean:.4f} [{pop_res.hit_rate.ci_lower:.4f}, {pop_res.hit_rate.ci_upper:.4f}]")
    print(f"  Recall@10:    {pop_res.recall.mean:.4f} [{pop_res.recall.ci_lower:.4f}, {pop_res.recall.ci_upper:.4f}]")
    print(f"  Coverage:     {pop_res.catalog_coverage:.4f}")

    # 6. Tier 2 content model on same split
    print("\nEvaluating Content-Only Tier 2 model on full validation...")
    # Load Tier 2 block weights from canonical validation results
    tier2_res_path = results_dir / "content_tier2_snapshot_validation.json"
    if tier2_res_path.exists():
        with open(tier2_res_path, "r", encoding="utf-8") as f:
            t2_data = json.load(f)
        block_weights = t2_data["chosen_config"]["tier2_block_weights"]
    else:
        block_weights = {"tier1": 1.0, "tags": 8.0, "genome": 0.5}
    print(f"Tier 2 block weights: {block_weights}")

    content_model = ContentBasedRecommender(
        profile_variant=ProfileVariant.POS_MEAN,
        positive_threshold=pos_thresh,
        tier=2,
        tier2_block_weights=block_weights,
        feature_dir=feat_dir,
    )
    content_model.fit(train_df, context=full_context_dict)
    content_res = evaluator_full.evaluate(content_model, store_per_user_metrics=True)

    print("\nTIER 2 CONTENT-ONLY FULL VALIDATION PERFORMANCE:")
    print(f"  NDCG@10:      {content_res.ndcg.mean:.4f} [{content_res.ndcg.ci_lower:.4f}, {content_res.ndcg.ci_upper:.4f}]")
    print(f"  HitRate@10:   {content_res.hit_rate.mean:.4f} [{content_res.hit_rate.ci_lower:.4f}, {content_res.hit_rate.ci_upper:.4f}]")
    print(f"  Recall@10:    {content_res.recall.mean:.4f} [{content_res.recall.ci_lower:.4f}, {content_res.recall.ci_upper:.4f}]")
    print(f"  Coverage:     {content_res.catalog_coverage:.4f}")

    # 7. Paired comparisons
    print("\nPAIRED STATISTICAL COMPARISON: CF vs POPULARITY (MOST_LIKED)")
    cf_vs_pop = {}
    for m_col in ["ndcg", "hit_rate", "recall"]:
        comp = Evaluator.compare(
            cf_res.per_user_metrics[m_col],
            pop_res.per_user_metrics[m_col],
            metric=f"{m_col.upper()}@10",
        )
        dist_str = "YES (p < 0.05)" if comp.is_distinguishable_from_zero else "NO (p >= 0.05)"
        print(f"  {comp.metric:<12}: Diff={comp.mean_diff:+.6f} [95% CI: {comp.ci_lower:+.6f}, {comp.ci_upper:+.6f}] | Lift={comp.relative_lift:+.2%} | Dist={dist_str}")
        print(f"               CF>Pop: {comp.pct_a_better:.2f}% | Equal: {comp.pct_equal:.2f}% | CF<Pop: {comp.pct_b_better:.2f}%")
        cf_vs_pop[m_col] = {
            "metric": comp.metric,
            "mean_diff": round(comp.mean_diff, 6),
            "ci_lower": round(comp.ci_lower, 6),
            "ci_upper": round(comp.ci_upper, 6),
            "relative_lift": round(comp.relative_lift, 4),
            "pct_cf_better": round(comp.pct_a_better, 2),
            "pct_equal": round(comp.pct_equal, 2),
            "pct_pop_better": round(comp.pct_b_better, 2),
            "distinguishable_from_zero": comp.is_distinguishable_from_zero,
        }

    print("\nPAIRED STATISTICAL COMPARISON: CF vs CONTENT-ONLY (TIER 2)")
    cf_vs_content = {}
    for m_col in ["ndcg", "hit_rate", "recall"]:
        comp = Evaluator.compare(
            cf_res.per_user_metrics[m_col],
            content_res.per_user_metrics[m_col],
            metric=f"{m_col.upper()}@10",
        )
        dist_str = "YES (p < 0.05)" if comp.is_distinguishable_from_zero else "NO (p >= 0.05)"
        print(f"  {comp.metric:<12}: Diff={comp.mean_diff:+.6f} [95% CI: {comp.ci_lower:+.6f}, {comp.ci_upper:+.6f}] | Lift={comp.relative_lift:+.2%} | Dist={dist_str}")
        print(f"               CF>Content: {comp.pct_a_better:.2f}% | Equal: {comp.pct_equal:.2f}% | CF<Content: {comp.pct_b_better:.2f}%")
        cf_vs_content[m_col] = {
            "metric": comp.metric,
            "mean_diff": round(comp.mean_diff, 6),
            "ci_lower": round(comp.ci_lower, 6),
            "ci_upper": round(comp.ci_upper, 6),
            "relative_lift": round(comp.relative_lift, 4),
            "pct_cf_better": round(comp.pct_a_better, 2),
            "pct_equal": round(comp.pct_equal, 2),
            "pct_content_better": round(comp.pct_b_better, 2),
            "distinguishable_from_zero": comp.is_distinguishable_from_zero,
        }

    # 8. Strata breakdowns
    activity_strata = cf_res.activity_breakdown
    session_strata = cf_res.session_strata_breakdown

    # Save results JSON
    cf_results_json = {
        "metadata": {
            "model_family": "item_item_collaborative_filtering",
            "timestamp": timestamp,
            "git_commit": git_hash,
            "dirty_working_tree": is_dirty,
            "positive_threshold": pos_thresh,
            "tuning_sample_size": sample_size,
            "tuning_seed": sample_seed,
            "total_runtime_seconds": round(time.time() - start_total_time, 2),
        },
        "chosen_config": best_config,
        "tuning_grid_results": grid_results,
        "full_validation_metrics": {
            "precision": format_summary(cf_res.precision),
            "recall": format_summary(cf_res.recall),
            "ndcg": format_summary(cf_res.ndcg),
            "hit_rate": format_summary(cf_res.hit_rate),
            "mrr": format_summary(cf_res.mrr),
            "catalog_coverage": round(float(cf_res.catalog_coverage), 6),
            "mean_recommended_popularity": format_summary(cf_res.mean_recommended_popularity),
            "activity_breakdown": activity_strata,
            "session_strata_breakdown": session_strata,
        },
        "popularity_validation_metrics": {
            "precision": format_summary(pop_res.precision),
            "recall": format_summary(pop_res.recall),
            "ndcg": format_summary(pop_res.ndcg),
            "hit_rate": format_summary(pop_res.hit_rate),
            "mrr": format_summary(pop_res.mrr),
            "catalog_coverage": round(float(pop_res.catalog_coverage), 6),
            "mean_recommended_popularity": format_summary(pop_res.mean_recommended_popularity),
        },
        "content_tier2_validation_metrics": {
            "precision": format_summary(content_res.precision),
            "recall": format_summary(content_res.recall),
            "ndcg": format_summary(content_res.ndcg),
            "hit_rate": format_summary(content_res.hit_rate),
            "mrr": format_summary(content_res.mrr),
            "catalog_coverage": round(float(content_res.catalog_coverage), 6),
            "mean_recommended_popularity": format_summary(content_res.mean_recommended_popularity),
        },
        "paired_comparison_vs_popularity": cf_vs_pop,
        "paired_comparison_vs_content_tier2": cf_vs_content,
    }

    json_path = results_dir / "cf_validation.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(cf_results_json, f, indent=2)
    print(f"\nSaved CF validation results to {json_path}")

    # Save summary CSV
    csv_rows = []
    # Grid search rows
    for r in grid_results:
        csv_rows.append({
            "stage": "tuning_grid",
            "model": f"cf_a{r['a']}_lam{r['shrinkage']}_k{r['k']}",
            "a": r["a"],
            "lambda": r["shrinkage"],
            "k": r["k"],
            "ndcg": r["ndcg"],
            "precision": r["precision"],
            "recall": r["recall"],
            "hit_rate": r["hit_rate"],
            "coverage": r["catalog_coverage"],
            "mean_pop": r["mean_recommended_popularity"],
        })
    # Full validation rows
    csv_rows.append({
        "stage": "full_validation",
        "model": f"cf_chosen_a{best_config['a']}_lam{best_config['shrinkage']}_k{best_config['k']}",
        "a": best_config["a"],
        "lambda": best_config["shrinkage"],
        "k": best_config["k"],
        "ndcg": cf_res.ndcg.mean,
        "precision": cf_res.precision.mean,
        "recall": cf_res.recall.mean,
        "hit_rate": cf_res.hit_rate.mean,
        "coverage": cf_res.catalog_coverage,
        "mean_pop": cf_res.mean_recommended_popularity.mean,
    })
    csv_rows.append({
        "stage": "full_validation",
        "model": "popularity_most_liked",
        "a": None,
        "lambda": None,
        "k": None,
        "ndcg": pop_res.ndcg.mean,
        "precision": pop_res.precision.mean,
        "recall": pop_res.recall.mean,
        "hit_rate": pop_res.hit_rate.mean,
        "coverage": pop_res.catalog_coverage,
        "mean_pop": pop_res.mean_recommended_popularity.mean,
    })
    csv_rows.append({
        "stage": "full_validation",
        "model": "content_tier2",
        "a": None,
        "lambda": None,
        "k": None,
        "ndcg": content_res.ndcg.mean,
        "precision": content_res.precision.mean,
        "recall": content_res.recall.mean,
        "hit_rate": content_res.hit_rate.mean,
        "coverage": content_res.catalog_coverage,
        "mean_pop": content_res.mean_recommended_popularity.mean,
    })
    csv_path = results_dir / "cf_validation.csv"
    pd.DataFrame(csv_rows).to_csv(csv_path, index=False)
    print(f"Saved CF validation summary CSV to {csv_path}")


if __name__ == "__main__":
    run_tuning_and_evaluation()
