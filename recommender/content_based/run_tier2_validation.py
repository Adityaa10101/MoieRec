"""Runner script for Tier 2 Snapshot Experiment (Part C).

CRITICAL NOTICE: Tag TF-IDF and Tag Genome features were aggregated over historical data
up to November 2019, leaking future user tagging and semantic signals across the split boundary.
Evaluated as a separate exploratory experiment labeled snapshot_features=true.

Evaluates:
- Tier 2 block combinations: T1+tags, T1+genome, T1+tags+genome over block weights in {0.5, 1.0, 2.0}
  on a fixed sample of 20,000 validation users.
- Reuses the chosen Part B profile variant (centered, IDF=False, w_yr=0.0).
- Evaluates the best Tier 2 config across all 94,312 validation users with 95% bootstrap CIs.
- Computes genome coverage among recommended items.
- Paired statistical comparisons vs Tier 1 and vs Popularity (most_liked).
- Saves results to recommender/results/content_tier2_snapshot_validation.json and .csv.
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


def compute_user_weights(df: pd.DataFrame, p_var: str, pos_thresh: float) -> Tuple[pd.DataFrame, np.ndarray]:
    if p_var == "centered":
        user_means = df.groupby("user_id")["rating"].mean()
        df = df.copy()
        df["mean_r"] = df["user_id"].map(user_means)
        weights = (df["rating"] - df["mean_r"]).to_numpy(dtype=np.float32)
        return df, weights
    elif p_var == "pos_mean":
        sub = df[df["rating"] >= pos_thresh].copy()
        user_pos_cnt = sub.groupby("user_id")["movie_id"].transform("count")
        weights = (1.0 / user_pos_cnt).to_numpy(dtype=np.float32)
        return sub, weights
    elif p_var == "pos_rating_weighted":
        sub = df[df["rating"] >= pos_thresh].copy()
        weights = sub["rating"].to_numpy(dtype=np.float32)
        return sub, weights
    elif p_var == "rating_weighted":
        weights = df["rating"].to_numpy(dtype=np.float32)
        return df, weights
    else:
        raise ValueError(f"Unknown profile variant: {p_var}")


def format_summary(summary: MetricSummary) -> Dict[str, float]:
    return {
        "mean": round(float(summary.mean), 6),
        "ci_lower": round(float(summary.ci_lower), 6),
        "ci_upper": round(float(summary.ci_upper), 6),
    }


def main() -> None:
    start_total_time = time.time()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    git_hash = get_git_commit_hash(root_dir)

    print("=" * 70)
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
    print(f"\nTimestamp:  {timestamp}")
    print(f"Git commit: {git_hash}")

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

    # 1. Load Tier 1 chosen config
    t1_json_path = results_dir / "content_tier1_validation.json"
    with open(t1_json_path, "r", encoding="utf-8") as f:
        t1_data = json.load(f)
    t1_chosen = t1_data["chosen_config"]
    p_var = t1_chosen["profile_variant"]
    use_idf = t1_chosen["use_genre_idf"]
    w_yr = t1_chosen["year_weight"]
    print(f"\nReusing Best Part B Profile Config: {p_var}, use_genre_idf={use_idf}, year_weight={w_yr}")

    # 2. Load Train and Validation splits
    print("Loading TRAIN and VALIDATION splits...")
    train_df = pd.read_parquet(splits_dir / "train.parquet")
    val_df = pd.read_parquet(splits_dir / "validation.parquet")
    train_hash = t1_data["metadata"]["train_content_hash"]
    val_hash = t1_data["metadata"]["validation_content_hash"]

    # History spans
    bench_ratings_path = data_dir / "benchmark" / "ratings.parquet"
    if bench_ratings_path.exists():
        ratings_bench = pd.read_parquet(bench_ratings_path, columns=["user_id", "timestamp"])
        user_min_max = ratings_bench.groupby("user_id")["timestamp"].agg(["min", "max"])
        spans_series = (user_min_max["max"] - user_min_max["min"]) / 86400.0
        spans_dict = spans_series.to_dict()
    else:
        spans_dict = None

    pos_thresh = 4.0

    # 3. Build Evaluation Contexts
    ctx_full = build_evaluation_context(
        train_df,
        val_df,
        mode="validation",
        positive_threshold=pos_thresh,
        user_history_spans=spans_dict,
    )
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

    eval_cfg_sample = EvaluationConfig(positive_threshold=pos_thresh, k=10, batch_size=2000, seed=sample_seed, n_bootstrap=50)
    evaluator_sample = Evaluator(ctx_sample, eval_cfg_sample)

    eval_cfg_full = EvaluationConfig(positive_threshold=pos_thresh, k=10, batch_size=2000, seed=42, n_bootstrap=1000)
    evaluator_full = Evaluator(ctx_full, eval_cfg_full)

    # 4. Preload and Normalize Candidate Feature Blocks ONCE
    print("\nPreloading candidate feature blocks into memory...")
    t_load = time.time()
    id_map_path = data_dir / "id_mappings" / "movie_id_to_benchmark_idx.parquet"
    m2b = pd.read_parquet(id_map_path).set_index("movie_id")["benchmark_idx"].to_dict()
    cand_bench_indices = [m2b[mid] for mid in ctx_full.candidate_movie_ids]
    n_candidates = len(cand_bench_indices)

    # (a) Tier 1 Block
    t1_csr = sparse.load_npz(feat_dir / "tier1_baseline_features.npz")
    cand_t1 = t1_csr[cand_bench_indices].toarray().astype(np.float32)
    # Apply Tier 1 weights (chosen config)
    if use_idf:
        genre_matrix = cand_t1[:, :19]
        doc_freq = np.sum(genre_matrix > 0, axis=0)
        idf = np.log((float(n_candidates) / (doc_freq + 1.0))) + 1.0
        cand_t1[:, :19] *= idf
    cand_t1[:, 19] *= w_yr  # norm_year
    cand_t1[:, 20] *= 0.0   # missing_year_flag
    t1_norms = np.linalg.norm(cand_t1, axis=1, keepdims=True)
    t1_norms = np.where(t1_norms > 0, t1_norms, 1.0)
    cand_t1 = cand_t1 / t1_norms

    # (b) Tags TF-IDF Block
    tags_csr = sparse.load_npz(feat_dir / "tier2_tag_tfidf.npz")[cand_bench_indices]
    tag_norms = sparse.linalg.norm(tags_csr, axis=1)
    tag_norms = np.where(tag_norms > 0, tag_norms, 1.0)[:, None]
    cand_tags_dense = (tags_csr / tag_norms).astype(np.float32).toarray()

    # (c) Genome Block
    genome_mat = np.load(feat_dir / "tier2_genome_matrix.npy")[cand_bench_indices].astype(np.float32)
    genome_mask = np.load(feat_dir / "tier2_genome_mask.npy")[cand_bench_indices].astype(np.float32)[:, None]
    masked_genome = genome_mat * genome_mask
    gen_norms = np.linalg.norm(masked_genome, axis=1, keepdims=True)
    gen_norms = np.where(gen_norms > 0, gen_norms, 1.0)
    cand_genome_dense = (masked_genome / gen_norms).astype(np.float32)
    print(f"Preloaded and normalized feature blocks in {time.time() - t_load:.2f}s")

    # 5. Precompute Interaction Weight Matrix W on 20,000 user sample
    print("Precomputing user interaction profiles W on 20,000 user sample...")
    t_w = time.time()
    user_to_cand_idx = {mid: idx for idx, mid in enumerate(ctx_full.candidate_movie_ids)}
    valid_mask_samp = train_df["user_id"].isin(ctx_sample.user_id_to_eval_idx) & train_df["movie_id"].isin(user_to_cand_idx)
    sub_train_samp = train_df[valid_mask_samp].copy()

    sub_train_samp, weights_samp = compute_user_weights(sub_train_samp, p_var, pos_thresh)

    u_indices_samp = sub_train_samp["user_id"].map(ctx_sample.user_id_to_eval_idx).to_numpy(dtype=np.int32)
    i_indices_samp = sub_train_samp["movie_id"].map(user_to_cand_idx).to_numpy(dtype=np.int32)

    W_samp = sparse.csr_matrix(
        (weights_samp, (u_indices_samp, i_indices_samp)),
        shape=(ctx_sample.n_evaluated_users, n_candidates),
        dtype=np.float32,
    )

    # Pre-multiply W with each block ONCE
    P_t1_samp = W_samp.dot(cand_t1)
    P_tags_samp = W_samp.dot(cand_tags_dense)
    P_gen_samp = W_samp.dot(cand_genome_dense)
    print(f"Precomputed block profiles for 20k users in {time.time() - t_w:.2f}s")

    # 6. Grid Search over Tier 2 block combinations on 20k sample
    print("\n" + "-" * 70)
    print("RUNNING TIER 2 GRID SEARCH ON 20,000 USER SAMPLE...")
    print("-" * 70)

    tier2_configs = []
    for w_tag in [1.0, 2.0, 4.0, 8.0]:
        for w_gen in [0.5, 1.0, 2.0, 4.0]:
            tier2_configs.append({
                "name": f"t1_1.0_tags_{w_tag:g}_gen_{w_gen:g}",
                "weights": {"tier1": 1.0, "tags": float(w_tag), "genome": float(w_gen)},
            })

    grid_results = []
    best_t2_record = None
    best_t2_ndcg = -1.0

    print(f"{'Config Name':<26} | {'Weights (T1, Tags, Gen)':<24} | {'NDCG@10':<8} | {'P@10':<8} | {'R@10':<8} | {'HR@10':<8}")
    print("-" * 88)

    for cfg in tier2_configs:
        w_dict = cfg["weights"]
        w1, w2, w3 = w_dict["tier1"], w_dict["tags"], w_dict["genome"]

        # Concatenate item blocks
        blocks_x = []
        blocks_p = []
        if w1 > 0:
            blocks_x.append(cand_t1 * w1)
            blocks_p.append(P_t1_samp * w1)
        if w2 > 0:
            blocks_x.append(cand_tags_dense * w2)
            blocks_p.append(P_tags_samp * w2)
        if w3 > 0:
            blocks_x.append(cand_genome_dense * w3)
            blocks_p.append(P_gen_samp * w3)

        concat_x = np.hstack(blocks_x)
        x_norms = np.linalg.norm(concat_x, axis=1, keepdims=True)
        x_norms = np.where(x_norms > 0, x_norms, 1.0)
        item_feats = concat_x / x_norms

        concat_p = np.hstack(blocks_p)
        p_norms = np.linalg.norm(concat_p, axis=1, keepdims=True)
        zero_cnt = int(np.sum(p_norms.squeeze() == 0.0))
        p_norms = np.where(p_norms > 0, p_norms, 1.0)
        user_profiles = concat_p / p_norms

        # Instantiate model wrapper
        model = ContentBasedRecommender(
            profile_variant=p_var,
            use_genre_idf=use_idf,
            year_weight=w_yr,
            tier=2,
            tier2_block_weights=w_dict,
        )
        model.candidate_movie_ids = ctx_sample.candidate_movie_ids
        model.movie_id_to_cand_idx = user_to_cand_idx
        model.n_candidates = n_candidates
        model.item_features = item_feats
        model.user_profiles = user_profiles
        model.n_zero_profile_users = zero_cnt

        res = evaluator_sample.evaluate(model, store_per_user_metrics=False)

        w_str = f"({w1}, {w2}, {w3})"
        rec = {
            "snapshot_features": True,
            "name": cfg["name"],
            "tier2_block_weights": w_dict,
            "ndcg": round(res.ndcg.mean, 6),
            "precision": round(res.precision.mean, 6),
            "recall": round(res.recall.mean, 6),
            "hit_rate": round(res.hit_rate.mean, 6),
            "mrr": round(res.mrr.mean, 6),
            "catalog_coverage": round(res.catalog_coverage, 6),
            "zero_profile_users": zero_cnt,
        }
        grid_results.append(rec)

        print(
            f"{cfg['name']:<26} | {w_str:<24} | "
            f"{res.ndcg.mean:<8.4f} | {res.precision.mean:<8.4f} | "
            f"{res.recall.mean:<8.4f} | {res.hit_rate.mean:<8.4f}"
        )

        if res.ndcg.mean > best_t2_ndcg:
            best_t2_ndcg = res.ndcg.mean
            best_t2_record = rec

    print("-" * 88)
    print(f"BEST TIER 2 SNAPSHOT CONFIG: {best_t2_record['name']} with weights {best_t2_record['tier2_block_weights']} (NDCG@10 = {best_t2_ndcg:.6f})")

    # 7. Evaluate Best Tier 2 on ALL 94,312 Validation Users
    print("\n" + "=" * 70)
    print("EVALUATING BEST TIER 2 ON ALL VALIDATION USERS (94,312 USERS)...")
    print("=" * 70)

    best_w = best_t2_record["tier2_block_weights"]
    w1, w2, w3 = best_w["tier1"], best_w["tags"], best_w["genome"]

    # Precompute full W
    t_w_full = time.time()
    valid_mask_full = train_df["user_id"].isin(ctx_full.user_id_to_eval_idx) & train_df["movie_id"].isin(user_to_cand_idx)
    sub_train_full = train_df[valid_mask_full].copy()

    sub_train_full, weights_full = compute_user_weights(sub_train_full, p_var, pos_thresh)

    u_indices_full = sub_train_full["user_id"].map(ctx_full.user_id_to_eval_idx).to_numpy(dtype=np.int32)
    i_indices_full = sub_train_full["movie_id"].map(user_to_cand_idx).to_numpy(dtype=np.int32)

    W_full = sparse.csr_matrix(
        (weights_full, (u_indices_full, i_indices_full)),
        shape=(ctx_full.n_evaluated_users, n_candidates),
        dtype=np.float32,
    )
    print(f"Built full W in {time.time() - t_w_full:.2f}s")

    # Combine blocks for best config
    blocks_x_full = []
    blocks_p_full = []
    if w1 > 0:
        blocks_x_full.append(cand_t1 * w1)
        blocks_p_full.append(W_full.dot(cand_t1) * w1)
    if w2 > 0:
        blocks_x_full.append(cand_tags_dense * w2)
        blocks_p_full.append(W_full.dot(cand_tags_dense) * w2)
    if w3 > 0:
        blocks_x_full.append(cand_genome_dense * w3)
        blocks_p_full.append(W_full.dot(cand_genome_dense) * w3)

    concat_x_full = np.hstack(blocks_x_full)
    x_norms_full = np.linalg.norm(concat_x_full, axis=1, keepdims=True)
    x_norms_full = np.where(x_norms_full > 0, x_norms_full, 1.0)
    full_item_feats = concat_x_full / x_norms_full

    concat_p_full = np.hstack(blocks_p_full)
    p_norms_full = np.linalg.norm(concat_p_full, axis=1, keepdims=True)
    full_zero_cnt = int(np.sum(p_norms_full.squeeze() == 0.0))
    p_norms_full = np.where(p_norms_full > 0, p_norms_full, 1.0)
    full_user_profiles = concat_p_full / p_norms_full

    best_model_full = ContentBasedRecommender(
        profile_variant=p_var,
        use_genre_idf=use_idf,
        year_weight=w_yr,
        tier=2,
        tier2_block_weights=best_w,
    )
    best_model_full.candidate_movie_ids = ctx_full.candidate_movie_ids
    best_model_full.movie_id_to_cand_idx = user_to_cand_idx
    best_model_full.n_candidates = n_candidates
    best_model_full.item_features = full_item_feats
    best_model_full.user_profiles = full_user_profiles
    best_model_full.n_zero_profile_users = full_zero_cnt

    t_eval_full = time.time()
    best_t2_res = evaluator_full.evaluate(best_model_full, store_per_user_metrics=True, store_topk=True)
    print(f"Evaluated Best Tier 2 on all validation users in {time.time() - t_eval_full:.2f}s")

    # Genome coverage among top-10 recommended items
    cand_has_genome = genome_mask.squeeze().astype(bool)
    recs_has_genome = cand_has_genome[best_t2_res.predicted_topk]
    genome_rec_cov = float(np.mean(recs_has_genome))
    print(f"Genome coverage among recommended items: {genome_rec_cov:.4%}")

    print("\nTIER 2 SNAPSHOT VALIDATION PERFORMANCE (WITH 95% BOOTSTRAP CIs):")
    print(f"  Precision@10: {best_t2_res.precision.mean:.4f} [{best_t2_res.precision.ci_lower:.4f}, {best_t2_res.precision.ci_upper:.4f}]")
    print(f"  Recall@10:    {best_t2_res.recall.mean:.4f} [{best_t2_res.recall.ci_lower:.4f}, {best_t2_res.recall.ci_upper:.4f}]")
    print(f"  NDCG@10:      {best_t2_res.ndcg.mean:.4f} [{best_t2_res.ndcg.ci_lower:.4f}, {best_t2_res.ndcg.ci_upper:.4f}]")
    print(f"  HitRate@10:   {best_t2_res.hit_rate.mean:.4f} [{best_t2_res.hit_rate.ci_lower:.4f}, {best_t2_res.hit_rate.ci_upper:.4f}]")
    print(f"  MRR@10:       {best_t2_res.mrr.mean:.4f} [{best_t2_res.mrr.ci_lower:.4f}, {best_t2_res.mrr.ci_upper:.4f}]")
    print(f"  Coverage:     {best_t2_res.catalog_coverage:.4f}")
    print(f"  Mean Pop:     {best_t2_res.mean_recommended_popularity.mean:.1f}")

    # 8. Paired comparisons vs Tier 1 and vs Popularity
    print("\nPAIRED STATISTICAL COMPARISON: TIER 2 SNAPSHOT vs TIER 1")
    # Load Tier 1 model to extract per-user metrics
    t1_model = ContentBasedRecommender(
        profile_variant=p_var,
        use_genre_idf=use_idf,
        year_weight=w_yr,
        tier=1,
    )
    t1_model.candidate_movie_ids = ctx_full.candidate_movie_ids
    t1_model.movie_id_to_cand_idx = user_to_cand_idx
    t1_model.n_candidates = n_candidates
    t1_model.item_features = cand_t1
    t1_p_norms = np.linalg.norm(P_t1_full := W_full.dot(cand_t1), axis=1, keepdims=True)
    t1_model.user_profiles = P_t1_full / np.where(t1_p_norms > 0, t1_p_norms, 1.0)
    t1_res = evaluator_full.evaluate(t1_model, store_per_user_metrics=True)

    t2_vs_t1 = {}
    for m_col in ["ndcg", "hit_rate", "recall"]:
        comp = Evaluator.compare(
            best_t2_res.per_user_metrics[m_col],
            t1_res.per_user_metrics[m_col],
            metric=f"{m_col.upper()}@10",
        )
        dist_str = "YES (p < 0.05)" if comp.is_distinguishable_from_zero else "NO (p >= 0.05)"
        print(f"  {comp.metric:<12}: Diff={comp.mean_diff:+.6f} [95% CI: {comp.ci_lower:+.6f}, {comp.ci_upper:+.6f}] | Lift={comp.relative_lift:+.2%} | Distinguishable={dist_str}")
        print(f"               T2>T1: {comp.pct_a_better:.2f}% | Equal: {comp.pct_equal:.2f}% | T2<T1: {comp.pct_b_better:.2f}%")
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
    pop_model = PopularityRecommender(variant=PopularityVariant.MOST_LIKED, positive_threshold=pos_thresh)
    pop_model.fit(train_df, context={"candidate_movie_ids": ctx_full.candidate_movie_ids})
    pop_res = evaluator_full.evaluate(pop_model, store_per_user_metrics=True)

    t2_vs_pop = {}
    for m_col in ["ndcg", "hit_rate", "recall"]:
        comp = Evaluator.compare(
            best_t2_res.per_user_metrics[m_col],
            pop_res.per_user_metrics[m_col],
            metric=f"{m_col.upper()}@10",
        )
        dist_str = "YES (p < 0.05)" if comp.is_distinguishable_from_zero else "NO (p >= 0.05)"
        print(f"  {comp.metric:<12}: Diff={comp.mean_diff:+.6f} [95% CI: {comp.ci_lower:+.6f}, {comp.ci_upper:+.6f}] | Lift={comp.relative_lift:+.2%} | Distinguishable={dist_str}")
        print(f"               T2>Pop: {comp.pct_a_better:.2f}% | Equal: {comp.pct_equal:.2f}% | T2<Pop: {comp.pct_b_better:.2f}%")
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

    # 9. Save Results
    total_elapsed = time.time() - start_total_time
    t2_output = {
        "snapshot_features": True,
        "snapshot_leakage_warning": leakage_warning,
        "metadata": {
            "snapshot_features": True,
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
            "total_runtime_seconds": round(total_elapsed, 2),
        },
        "chosen_config": best_t2_record,
        "tuning_grid_results": grid_results,
        "full_validation_metrics": {
            "snapshot_features": True,
            "precision": format_summary(best_t2_res.precision),
            "recall": format_summary(best_t2_res.recall),
            "ndcg": format_summary(best_t2_res.ndcg),
            "hit_rate": format_summary(best_t2_res.hit_rate),
            "mrr": format_summary(best_t2_res.mrr),
            "catalog_coverage": round(float(best_t2_res.catalog_coverage), 6),
            "genome_coverage_among_recommendations": round(genome_rec_cov, 6),
            "mean_recommended_popularity": format_summary(best_t2_res.mean_recommended_popularity),
            "zero_profile_users": full_zero_cnt,
            "activity_breakdown": best_t2_res.activity_breakdown,
            "session_strata_breakdown": best_t2_res.session_strata_breakdown,
        },
        "paired_comparison_vs_tier1": t2_vs_t1,
        "paired_comparison_vs_popularity_most_liked": t2_vs_pop,
    }

    t2_json_path = results_dir / "content_tier2_snapshot_validation.json"
    with open(t2_json_path, "w", encoding="utf-8") as f:
        json.dump(t2_output, f, indent=2)
    print(f"\nSaved Tier 2 snapshot results JSON to: {t2_json_path}")

    # CSV summary
    t2_csv_df = pd.DataFrame(grid_results)
    t2_csv_path = results_dir / "content_tier2_snapshot_validation.csv"
    t2_csv_df.to_csv(t2_csv_path, index=False)
    print(f"Saved Tier 2 snapshot CSV summary to: {t2_csv_path}")

    print("\n" + "=" * 70)
    print(f"PART C TIER 2 SNAPSHOT COMPLETED IN {total_elapsed:.2f}s ({total_elapsed/60.0:.2f}m)")
    print("=" * 70)


if __name__ == "__main__":
    main()
