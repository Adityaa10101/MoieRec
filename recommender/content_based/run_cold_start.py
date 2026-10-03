"""Runner script for Simulated Cold-Start Onboarding Evaluation (Protocol v2).

Tests the product claim:
"A brand-new user picks a few movies they like and gets personalized recommendations immediately."

Protocol v2 (PHASE 2E.1):
- Evaluates strictly on cold_dev (50% of cold_start_users, 2,560 users).
- cold_final (2,559 users) is strictly guarded and remains untouched for the final frozen report.
- For K in {3, 5, 10}:
  - ONBOARDING = first K positives chronologically by (timestamp, seeded hash tie-break).
  - RELEVANT = the NEXT W=20 positives chronologically after onboarding picks in candidate catalog.
  - User inclusion threshold: user must have >= K + W positives in candidate catalog.
  - CANDIDATES = catalog minus the K revealed items.
  - Two variants:
    (i) All candidates: candidate catalog minus K revealed items.
    (ii) Long-tail: candidate catalog minus K revealed items AND minus top-200 most-rated TRAIN movies.
         Top-200 most-rated TRAIN movies are ALSO excluded from the relevant set.
  - Plus reference comparison:
    (iii) Old reference: all remaining positives protocol.
- Models:
  1. Popularity (most_liked; ignores onboarding picks, masks revealed/long-tail items)
  2. Content-Based Tier 1 (profile built ONLY from K revealed items with chosen config)
  3. Content-Based Tier 2 Snapshot (profile built ONLY from K revealed items with snapshot config)
- Metrics: Precision@10, Recall@10, NDCG@10, HitRate@10, MRR@10 with 95% bootstrap CIs,
  plus paired statistical comparisons (content vs popularity).
"""

import datetime
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Set

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

from recommender.content_based.model import ContentBasedRecommender
from recommender.evaluation.cold_start import (
    ColdStartEvaluationResult,
    ColdStartEvaluator,
    load_cold_start_split,
    partition_cold_start_users,
)
from recommender.evaluation.evaluator import (
    Evaluator,
    MetricSummary,
    PairedComparisonResult,
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


def main() -> None:
    start_time = time.time()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    git_hash = get_git_commit_hash(root_dir)
    dirty_flag = get_git_dirty_flag(root_dir)

    print("=" * 70)
    print("SIMULATED COLD-START ONBOARDING EVALUATION — PROTOCOL v2 (COLD_DEV)")
    print("=" * 70)
    print(f"Timestamp:  {timestamp}")
    print(f"Git commit: {git_hash} (dirty: {dirty_flag})")

    pkg_versions = {
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "pyarrow": pyarrow.__version__,
        "pytest": pytest.__version__,
    }

    dataset_name = "ml-25m"
    data_dir = root_dir / "data" / "processed" / dataset_name
    splits_dir = data_dir / "splits"
    feat_dir = data_dir / "features"
    results_dir = root_dir / "recommender" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # 1. Partition cold start users 50/50 deterministically if not already present
    partition_path = splits_dir / "cold_start_partition.json"
    cold_parquet_path = splits_dir / "cold_start_users.parquet"
    if not partition_path.exists():
        print("Partitioning cold-start users 50/50 into cold_dev and cold_final...")
        part_meta = partition_cold_start_users(cold_parquet_path, partition_path, seed=42)
    else:
        with open(partition_path, "r", encoding="utf-8") as f:
            part_meta = json.load(f)

    print(f"Cold-start population: {part_meta['n_total']:,} users")
    print(f"  cold_dev:   {part_meta['n_cold_dev']:,} users (USED IN THIS PHASE)")
    print(f"  cold_final: {part_meta['n_cold_final']:,} users (UNTOUCHED / GUARDED)")

    # 2. Load cold_dev split interactions (strictly guarded)
    print("\nLoading cold_dev interactions...")
    cold_dev_df = load_cold_start_split(split="cold_dev", final=False, splits_dir=splits_dir)
    print(f"Loaded cold_dev interactions: {len(cold_dev_df):,} ratings across {cold_dev_df['user_id'].nunique():,} users")

    # 3. Load TRAIN candidate catalog and popularity scores
    print("Loading TRAIN candidate catalog...")
    train_df = pd.read_parquet(splits_dir / "train.parquet")
    pos_thresh = 4.0

    train_movie_stats = train_df.groupby("movie_id").agg(
        count=("rating", "count"),
        pos_count=("rating", lambda s: (s >= pos_thresh).sum()),
    ).reset_index().sort_values(by="movie_id").reset_index(drop=True)

    candidate_movie_ids = train_movie_stats["movie_id"].to_numpy()
    candidate_pos_counts = train_movie_stats["pos_count"].to_numpy(dtype=np.float64)
    n_candidates = len(candidate_movie_ids)
    print(f"Candidate catalog: {n_candidates:,} benchmark movies with >=1 train rating")

    # Identify top-200 most-rated TRAIN movies for long-tail variant
    top200_train_mids = set(train_movie_stats.nlargest(200, "count")["movie_id"].tolist())
    print(f"Identified top-200 most-rated TRAIN movies for long-tail candidate/relevant filtering.")

    # 4. Load best Tier 1 and Tier 2 item features
    t1_res_path = results_dir / "content_tier1_validation.json"
    if t1_res_path.exists():
        with open(t1_res_path, "r", encoding="utf-8") as f:
            t1_meta = json.load(f)
        t1_chosen = t1_meta.get("chosen_config", {})
        t1_idf = t1_chosen.get("use_genre_idf", False)
        t1_wyr = t1_chosen.get("year_weight", 0.0)
    else:
        t1_idf = False
        t1_wyr = 0.0

    t2_res_path = results_dir / "content_tier2_snapshot_validation.json"
    if t2_res_path.exists():
        with open(t2_res_path, "r", encoding="utf-8") as f:
            t2_meta = json.load(f)
        t2_chosen = t2_meta.get("chosen_config", {})
        t2_weights = t2_chosen.get("tier2_block_weights", {"tier1": 1.0, "tags": 1.0, "genome": 1.0})
    else:
        t2_weights = {"tier1": 1.0, "tags": 1.0, "genome": 1.0}

    print(f"\nBuilding candidate item representations:")
    print(f"  Tier 1 config: use_genre_idf={t1_idf}, year_weight={t1_wyr}")
    t1_model = ContentBasedRecommender(
        profile_variant="pos_mean",
        use_genre_idf=t1_idf,
        year_weight=t1_wyr,
        missing_year_weight=0.0,
        tier=1,
        feature_dir=feat_dir,
    )
    t1_model.fit(train_df, context={"candidate_movie_ids": candidate_movie_ids, "build_user_profiles": False})
    t1_features = t1_model.item_features  # [n_candidates, D1]

    print(f"  Tier 2 Snapshot config: block_weights={t2_weights}")
    t2_model = ContentBasedRecommender(
        profile_variant="pos_mean",
        use_genre_idf=t1_idf,
        year_weight=t1_wyr,
        missing_year_weight=0.0,
        tier=2,
        tier2_block_weights=t2_weights,
        feature_dir=feat_dir,
    )
    t2_model.fit(train_df, context={"candidate_movie_ids": candidate_movie_ids, "build_user_profiles": False})
    t2_features = t2_model.item_features  # [n_candidates, D2]

    # 5. Run Cold-Start Onboarding Evaluation across K in {3, 5, 10}
    cold_evaluator = ColdStartEvaluator(
        cold_df=cold_dev_df,
        candidate_movie_ids=candidate_movie_ids,
        positive_threshold=pos_thresh,
        k_eval=10,
        n_bootstrap=1000,
        seed=42,
    )

    k_values = [3, 5, 10]
    all_results = []
    paired_comparisons = {}

    eval_protocols = [
        {"protocol": "v2", "variant": "all_candidates", "desc": "Protocol v2 (All Candidates, W=20)"},
        {"protocol": "v2", "variant": "long_tail", "desc": "Protocol v2 (Long-Tail: Excl Top-200, W=20)"},
        {"protocol": "old_reference", "variant": "all_remaining", "desc": "Old Reference (All Remaining Positives, >=K+5)"},
    ]

    for K in k_values:
        print("\n" + "=" * 80)
        print(f"EVALUATING ONBOARDING SET SIZE K = {K} (COLD_DEV)")
        print("=" * 80)

        for p_cfg in eval_protocols:
            p_name = p_cfg["protocol"]
            v_name = p_cfg["variant"]
            p_desc = p_cfg["desc"]

            print(f"\n--- {p_desc} (K={K}) ---")

            if p_name == "v2" and v_name == "all_candidates":
                eval_users, rev_list, gt_list, mask_list, n_excl = cold_evaluator.prepare_data_v2(
                    K, window_w=20, long_tail=False
                )
            elif p_name == "v2" and v_name == "long_tail":
                eval_users, rev_list, gt_list, mask_list, n_excl = cold_evaluator.prepare_data_v2(
                    K, window_w=20, long_tail=True, top200_train_mids=top200_train_mids
                )
            else:  # old_reference
                eval_users, rev_list, gt_list, mask_list, n_excl = cold_evaluator.prepare_data_old(K)

            n_eval = len(eval_users)
            print(f"Users evaluated: {n_eval:,} ({n_eval/cold_evaluator.total_cold_users*100:.2f}%) | Excluded: {n_excl:,} ({n_excl/cold_evaluator.total_cold_users*100:.2f}%)")

            # 1. Popularity (most_liked)
            pop_res = cold_evaluator.evaluate_popularity(
                k_onboarding=K,
                popularity_scores=candidate_pos_counts,
                eval_users=eval_users,
                revealed_list=rev_list,
                ground_truth_list=gt_list,
                mask_indices_list=mask_list,
                n_excluded=n_excl,
                model_name="popularity_most_liked",
                protocol=p_name,
                variant=v_name,
            )

            # 2. Content-Based Tier 1
            t1_res = cold_evaluator.evaluate_content_model(
                k_onboarding=K,
                item_features=t1_features,
                eval_users=eval_users,
                revealed_list=rev_list,
                ground_truth_list=gt_list,
                mask_indices_list=mask_list,
                n_excluded=n_excl,
                model_name="content_tier1",
                protocol=p_name,
                variant=v_name,
            )

            # 3. Content-Based Tier 2 Snapshot
            t2_res = cold_evaluator.evaluate_content_model(
                k_onboarding=K,
                item_features=t2_features,
                eval_users=eval_users,
                revealed_list=rev_list,
                ground_truth_list=gt_list,
                mask_indices_list=mask_list,
                n_excluded=n_excl,
                model_name="content_tier2_snapshot",
                protocol=p_name,
                variant=v_name,
            )

            # Summary Table
            print(f"{'Model':<25} | {'NDCG@10':<8} | {'P@10':<8} | {'R@10':<8} | {'HR@10':<8} | {'MRR@10':<8}")
            print("-" * 75)
            for r in [pop_res, t1_res, t2_res]:
                print(
                    f"{r.model_name:<25} | "
                    f"{r.ndcg.mean:<8.4f} | "
                    f"{r.precision.mean:<8.4f} | "
                    f"{r.recall.mean:<8.4f} | "
                    f"{r.hit_rate.mean:<8.4f} | "
                    f"{r.mrr.mean:<8.4f}"
                )
                all_results.append({
                    "k_onboarding": K,
                    "protocol": p_name,
                    "variant": v_name,
                    "model": r.model_name,
                    "n_evaluated_users": n_eval,
                    "n_excluded_users": n_excl,
                    "ndcg": format_summary(r.ndcg),
                    "precision": format_summary(r.precision),
                    "recall": format_summary(r.recall),
                    "hit_rate": format_summary(r.hit_rate),
                    "mrr": format_summary(r.mrr),
                })

            # Paired Comparisons: Content Tier 1 vs Popularity
            t1_vs_pop = {}
            for m_col in ["ndcg", "hit_rate", "recall"]:
                comp = Evaluator.compare(
                    t1_res.per_user_metrics[m_col],
                    pop_res.per_user_metrics[m_col],
                    metric=f"{m_col.upper()}@10",
                )
                t1_vs_pop[m_col] = {
                    "mean_diff": round(comp.mean_diff, 6),
                    "ci_lower": round(comp.ci_lower, 6),
                    "ci_upper": round(comp.ci_upper, 6),
                    "relative_lift": round(comp.relative_lift, 4),
                    "pct_content_better": round(comp.pct_a_better, 2),
                    "pct_equal": round(comp.pct_equal, 2),
                    "pct_pop_better": round(comp.pct_b_better, 2),
                    "distinguishable_from_zero": comp.is_distinguishable_from_zero,
                }

            # Paired Comparisons: Content Tier 2 Snapshot vs Popularity
            t2_vs_pop = {}
            for m_col in ["ndcg", "hit_rate", "recall"]:
                comp = Evaluator.compare(
                    t2_res.per_user_metrics[m_col],
                    pop_res.per_user_metrics[m_col],
                    metric=f"{m_col.upper()}@10",
                )
                t2_vs_pop[m_col] = {
                    "mean_diff": round(comp.mean_diff, 6),
                    "ci_lower": round(comp.ci_lower, 6),
                    "ci_upper": round(comp.ci_upper, 6),
                    "relative_lift": round(comp.relative_lift, 4),
                    "pct_content_better": round(comp.pct_a_better, 2),
                    "pct_equal": round(comp.pct_equal, 2),
                    "pct_pop_better": round(comp.pct_b_better, 2),
                    "distinguishable_from_zero": comp.is_distinguishable_from_zero,
                }

            pair_key = f"K_{K}_{p_name}_{v_name}"
            paired_comparisons[pair_key] = {
                "tier1_vs_popularity": t1_vs_pop,
                "tier2_snapshot_vs_popularity": t2_vs_pop,
            }

    # 6. Save Results JSON and CSV
    total_elapsed = round(time.time() - start_time, 2)
    output_data = {
        "metadata": {
            "dataset": dataset_name,
            "split_evaluated": "cold_dev",
            "cold_final_guarded": True,
            "timestamp": timestamp,
            "git_commit": git_hash,
            "dirty_working_tree": dirty_flag,
            "positive_threshold": pos_thresh,
            "packages": pkg_versions,
            "n_cold_dev_users": part_meta["n_cold_dev"],
            "n_cold_final_users_untouched": part_meta["n_cold_final"],
            "total_runtime_seconds": total_elapsed,
        },
        "k_evaluations": all_results,
        "paired_comparisons": paired_comparisons,
    }

    json_path = results_dir / "cold_start_dev.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    print(f"\nSaved cold start dev JSON to: {json_path}")

    csv_rows = []
    for item in all_results:
        csv_rows.append({
            "k_onboarding": item["k_onboarding"],
            "protocol": item["protocol"],
            "variant": item["variant"],
            "model": item["model"],
            "n_evaluated_users": item["n_evaluated_users"],
            "n_excluded_users": item["n_excluded_users"],
            "ndcg_10": item["ndcg"]["mean"],
            "ndcg_10_ci_lower": item["ndcg"]["ci_lower"],
            "ndcg_10_ci_upper": item["ndcg"]["ci_upper"],
            "precision_10": item["precision"]["mean"],
            "recall_10": item["recall"]["mean"],
            "hit_rate_10": item["hit_rate"]["mean"],
            "mrr_10": item["mrr"]["mean"],
        })
    csv_df = pd.DataFrame(csv_rows)
    csv_path = results_dir / "cold_start_dev.csv"
    csv_df.to_csv(csv_path, index=False)
    print(f"Saved cold start dev CSV to: {csv_path}")


if __name__ == "__main__":
    main()
