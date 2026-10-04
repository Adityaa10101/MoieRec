#!/usr/bin/env python3
"""
recommender/hybrid/tune_hybrid_v1_1.py
======================================
Phase 2F.1 Part A: Alpha Schedule Tuning by K on cold_dev.

Tuning protocol:
- Extended K in {3, 5, 10, 20} (W=20; K=20 requires >= 40 positive interactions).
- Fixed Tier 2 block weights from hybrid_v1.yaml: w_t1=1.0, w_tags=4.0, w_genome=1.0.
- Alpha grid: {0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8} (+ 0.0 popularity, 1.0 content-only).
- Selection objective per K:
    maximize average of the two RELATIVE lifts over popularity:
    mean(NDCG_all / NDCG_pop_all, NDCG_lt / NDCG_pop_lt)
    Constraint: variant (i) NDCG >= popularity NDCG.
- Serving buckets:
    K 3-4   -> tuned K=3
    K 5-7   -> tuned K=5
    K 8-14  -> tuned K=10
    K >= 15 -> tuned K=20
- Final evaluation: 1000 bootstrap resamples on cold_dev comparing:
    popularity, content-only, hybrid v1 (alpha=0.1), and hybrid v1.1 (alpha by K).
- Outputs:
    recommender/config/hybrid_v1_1.yaml
    recommender/results/hybrid_v1_1_cold_dev.json
    recommender/results/hybrid_v1_1_cold_dev.csv
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
import scipy.sparse as sp
import scipy.stats as st
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
SPLITS_DIR = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "splits"
FEAT_DIR = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "features"
ID_MAP_DIR = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "id_mappings"
V1_CONFIG_PATH = PROJECT_ROOT / "recommender" / "config" / "hybrid_v1.yaml"
OUTPUT_CONFIG_PATH = PROJECT_ROOT / "recommender" / "config" / "hybrid_v1_1.yaml"
OUTPUT_JSON_PATH = PROJECT_ROOT / "recommender" / "results" / "hybrid_v1_1_cold_dev.json"
OUTPUT_CSV_PATH = PROJECT_ROOT / "recommender" / "results" / "hybrid_v1_1_cold_dev.csv"

# Safety guard: never touch forbidden files
_FORBIDDEN = {"test.parquet", "cold_final"}
for _p in [SPLITS_DIR, FEAT_DIR]:
    for _f in _FORBIDDEN:
        assert _f not in str(_p), f"Forbidden path: {_f}"


def get_git_info() -> Dict[str, Any]:
    try:
        rev = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
        status = subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.DEVNULL).decode().strip()
        return {"git_commit": rev, "git_dirty": bool(len(status) > 0)}
    except Exception:
        return {"git_commit": "unknown", "git_dirty": True}


def select_topk_exact(
    scores: np.ndarray,
    k: int = 10,
    tie_ranks: Optional[np.ndarray] = None,
) -> np.ndarray:
    n_rows, n_cols = scores.shape
    if tie_ranks is not None:
        eps = 1e-9 * (1.0 / float(n_cols))
        adj_scores = scores - eps * tie_ranks[None, :]
    else:
        adj_scores = scores

    if k >= n_cols:
        return np.argsort(-adj_scores, axis=1)

    part_idx = np.argpartition(-adj_scores, k, axis=1)[:, :k]
    row_indices = np.arange(n_rows)[:, None]
    part_scores = adj_scores[row_indices, part_idx]
    sorted_order = np.argsort(-part_scores, axis=1)
    return np.take_along_axis(part_idx, sorted_order, axis=1)


def compute_hits(topk_matrix: np.ndarray, ground_truth_list: List[Set[int]]) -> np.ndarray:
    n_users, k = topk_matrix.shape
    hits = np.zeros((n_users, k), dtype=np.int32)
    for u in range(n_users):
        gt = ground_truth_list[u]
        row = topk_matrix[u]
        for rank_idx in range(k):
            if row[rank_idx] in gt:
                hits[u, rank_idx] = 1
    return hits


def ndcg_at_k(hits_matrix: np.ndarray, gt_counts: np.ndarray, k: int = 10) -> np.ndarray:
    discounts = 1.0 / np.log2(np.arange(2, k + 2))
    dcg = np.sum(hits_matrix[:, :k] * discounts[None, :], axis=1)
    idcg = np.zeros(len(gt_counts), dtype=np.float64)
    for i, c in enumerate(gt_counts):
        n_ideal = min(int(c), k)
        if n_ideal > 0:
            idcg[i] = np.sum(discounts[:n_ideal])
        else:
            idcg[i] = 1.0
    ndcg = dcg / idcg
    ndcg = np.nan_to_num(ndcg, nan=0.0, posinf=0.0, neginf=0.0)
    return ndcg


def compute_bootstrap_ci(
    values: np.ndarray,
    n_resamples: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    mean_val = float(np.mean(values))
    n = len(values)
    if n == 0:
        return 0.0, 0.0, 0.0
    indices = rng.integers(0, n, size=(n_resamples, n))
    sample_means = np.mean(values[indices], axis=1)
    alpha_ci = (1.0 - ci) / 2.0
    lo = float(np.percentile(sample_means, 100.0 * alpha_ci))
    hi = float(np.percentile(sample_means, 100.0 * (1.0 - alpha_ci)))
    return mean_val, lo, hi


def compute_paired_bootstrap(
    a: np.ndarray,
    b: np.ndarray,
    n_resamples: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float, float, bool]:
    diff = a - b
    mean_diff, lo, hi = compute_bootstrap_ci(diff, n_resamples=n_resamples, ci=ci, seed=seed)
    strictly_better = lo > 0.0
    return mean_diff, lo, hi, strictly_better


def load_feature_blocks() -> Dict[str, Any]:
    print("Loading feature matrices...")
    meta = json.loads((FEAT_DIR / "feature_metadata.json").read_text(encoding="utf-8"))
    t1_info = meta["tier1_baseline"]
    feature_names_t1 = list(t1_info["feature_names"])
    n_genres = int(t1_info["n_genres"])

    m2b_df = pd.read_parquet(ID_MAP_DIR / "movie_id_to_benchmark_idx.parquet")
    m2b = m2b_df.set_index("movie_id")["benchmark_idx"].to_dict()

    t1_csr = sp.load_npz(FEAT_DIR / "tier1_baseline_features.npz")
    tag_csr = sp.load_npz(FEAT_DIR / "tier2_tag_tfidf.npz")
    genome_mat = np.load(FEAT_DIR / "tier2_genome_matrix.npy")
    genome_mask = np.load(FEAT_DIR / "tier2_genome_mask.npy")

    full_genome_tags = pd.read_parquet(
        PROJECT_ROOT / "data" / "processed" / "ml-25m" / "full" / "genome_tags.parquet"
    )
    genome_tag_names = full_genome_tags.sort_values("tag_id")["tag"].tolist()

    return {
        "m2b": m2b,
        "t1_csr": t1_csr,
        "tag_csr": tag_csr,
        "genome_mat": genome_mat,
        "genome_mask": genome_mask,
        "feature_names_t1": feature_names_t1,
        "n_genres": n_genres,
        "genome_tag_names": genome_tag_names,
    }


def build_item_features(
    candidate_movie_ids: np.ndarray,
    feats: Dict[str, Any],
    w_t1: float = 1.0,
    w_tags: float = 4.0,
    w_genome: float = 1.0,
) -> np.ndarray:
    m2b = feats["m2b"]
    t1_csr = feats["t1_csr"]
    tag_csr = feats["tag_csr"]
    genome_mat = feats["genome_mat"]
    genome_mask = feats["genome_mask"]

    bench_indices = np.array([m2b.get(mid, -1) for mid in candidate_movie_ids], dtype=np.int32)
    valid_mask = bench_indices >= 0
    safe_indices = np.where(valid_mask, bench_indices, 0)

    # 1. Tier 1
    cand_t1 = t1_csr[safe_indices].toarray().astype(np.float32)
    cand_t1[~valid_mask] = 0.0
    t1_norms = np.linalg.norm(cand_t1, axis=1, keepdims=True)
    t1_norms = np.where(t1_norms > 0, t1_norms, 1.0)
    blocks = [cand_t1 / t1_norms * w_t1]

    # 2. Tag TF-IDF
    if w_tags > 0:
        tags_raw = tag_csr[safe_indices]
        tag_norms_arr = np.array(tags_raw.power(2).sum(axis=1)).flatten() ** 0.5
        tag_norms_arr = np.where(tag_norms_arr > 0, tag_norms_arr, 1.0)
        tags_dense = tags_raw.toarray().astype(np.float32)
        tags_dense /= tag_norms_arr[:, None]
        tags_dense[~valid_mask] = 0.0
        blocks.append(tags_dense * w_tags)
        del tags_raw, tags_dense

    # 3. Genome
    if w_genome > 0:
        gm = genome_mat[safe_indices].astype(np.float32)
        gm_mask = genome_mask[safe_indices].astype(np.float32)[:, None]
        masked_gm = gm * gm_mask
        masked_gm[~valid_mask] = 0.0
        gen_norms = np.linalg.norm(masked_gm, axis=1, keepdims=True)
        gen_norms = np.where(gen_norms > 0, gen_norms, 1.0)
        blocks.append((masked_gm / gen_norms) * w_genome)

    concat_X = np.hstack(blocks).astype(np.float32)
    row_norms = np.linalg.norm(concat_X, axis=1, keepdims=True)
    row_norms = np.where(row_norms > 0, row_norms, 1.0)
    X = concat_X / row_norms
    return X


def main() -> None:
    t_start = time.time()
    print("=" * 70)
    print("Phase 2F.1 Part A — Alpha Schedule Tuning by K on cold_dev")
    print("=" * 70)

    # Verify V1 config exists and read fixed block weights
    if not V1_CONFIG_PATH.exists():
        print(f"ERROR: {V1_CONFIG_PATH} does not exist.")
        sys.exit(1)

    with open(V1_CONFIG_PATH, "r", encoding="utf-8") as f:
        v1_cfg = yaml.safe_load(f)

    w_t1 = float(v1_cfg["block_weights"]["w_t1"])
    w_tags = float(v1_cfg["block_weights"]["w_tags"])
    w_genome = float(v1_cfg["block_weights"]["w_genome"])
    sim_threshold = float(v1_cfg.get("similarity_threshold", 0.1278))

    print(f"Fixed Tier 2 block weights from v1: w_t1={w_t1}, w_tags={w_tags}, w_genome={w_genome}")

    from recommender.evaluation.cold_start import ColdStartEvaluator, load_cold_start_split
    cold_dev_df = load_cold_start_split("cold_dev", final=False)

    bench_movies = pd.read_parquet(
        PROJECT_ROOT / "data" / "processed" / "ml-25m" / "benchmark" / "movies.parquet"
    )
    candidate_mids = np.sort(bench_movies["movie_id"].unique())
    n_candidates = len(candidate_mids)
    print(f"Catalog candidate movies: {n_candidates:,}")

    evaluator = ColdStartEvaluator(
        cold_df=cold_dev_df,
        candidate_movie_ids=candidate_mids,
        positive_threshold=4.0,
        k_eval=10,
        n_bootstrap=200,
        seed=42,
    )

    # Popularity scores
    train_stats = pd.read_parquet(SPLITS_DIR / "train_movie_stats.parquet")
    stats_dict = train_stats.set_index("movie_id")["positive_rating_count"].to_dict()
    pop_scores = np.array([stats_dict.get(int(m), 0) for m in candidate_mids], dtype=np.float32)

    top200_train = (
        train_stats.sort_values("positive_rating_count", ascending=False)
        .head(200)["movie_id"]
        .tolist()
    )
    top200_mids = set(top200_train)

    k_values = [3, 5, 10, 20]
    variants = ["all_candidates", "long_tail"]

    print("\n[1/4] Preparing cohorts for K in {3, 5, 10, 20} (W=20)...")
    cohort_data = {}
    pop_ndcg_baseline = {}

    for k_val in k_values:
        for variant in variants:
            long_tail = (variant == "long_tail")
            eval_users, revealed_list, ground_truth_list, mask_idx_list, n_excl = evaluator.prepare_data_v2(
                k_onboarding=k_val,
                window_w=20,
                long_tail=long_tail,
                top200_train_mids=top200_mids if long_tail else None,
            )
            n_users = len(eval_users)
            gt_counts = np.array([len(gt) for gt in ground_truth_list], dtype=np.int64)

            # Build precomputed boolean masks and popularity percentile matrix
            pct_p_mat = np.full((n_users, n_candidates), -np.inf, dtype=np.float32)
            active_indices_list = []
            mask_bool_mat = np.zeros((n_users, n_candidates), dtype=bool)

            for u_idx in range(n_users):
                mask_set = mask_idx_list[u_idx]
                mask_arr = np.fromiter(mask_set, dtype=np.int32, count=len(mask_set))
                mask_bool_mat[u_idx, mask_arr] = True
                active_idx = np.where(~mask_bool_mat[u_idx])[0]
                active_indices_list.append(active_idx)
                ranks = st.rankdata(pop_scores[active_idx], method="average")
                pct_p_mat[u_idx, active_idx] = (ranks - 1.0) / float(len(active_idx) - 1.0)

            # Evaluate Popularity baseline
            pop_topk = select_topk_exact(pct_p_mat, k=10, tie_ranks=evaluator.tie_ranks)
            pop_hits = compute_hits(pop_topk, ground_truth_list)
            pop_ndcgs = ndcg_at_k(pop_hits, gt_counts, 10)
            pop_mn, pop_lo, pop_hi = compute_bootstrap_ci(pop_ndcgs, n_resamples=200, seed=42)
            pop_ndcg_baseline[(k_val, variant)] = pop_mn

            print(
                f"  K={k_val:<2} {variant:<15}: Users={n_users:<5} (Excluded={n_excl:<5}) "
                f"Pop NDCG@10={pop_mn:.4f} [{pop_lo:.4f}, {pop_hi:.4f}]"
            )

            cohort_data[(k_val, variant)] = {
                "eval_users": eval_users,
                "revealed_list": revealed_list,
                "ground_truth_list": ground_truth_list,
                "gt_counts": gt_counts,
                "mask_bool_mat": mask_bool_mat,
                "active_indices_list": active_indices_list,
                "pct_p_mat": pct_p_mat,
                "n_users": n_users,
                "n_excluded": n_excl,
                "pop_ndcgs": pop_ndcgs,
            }

    # 2. Build feature matrix and precompute content percentiles
    print("\n[2/4] Building Tier 2 features and caching component scores...")
    feats = load_feature_blocks()
    X = build_item_features(candidate_mids, feats, w_t1=w_t1, w_tags=w_tags, w_genome=w_genome)

    pct_c_cache = {}
    content_only_ndcgs = {}

    for k_val in k_values:
        for variant in variants:
            cohort = cohort_data[(k_val, variant)]
            n_users = cohort["n_users"]
            revealed_list = cohort["revealed_list"]
            active_indices_list = cohort["active_indices_list"]
            gt_counts = cohort["gt_counts"]
            ground_truth_list = cohort["ground_truth_list"]

            # Compute user profiles: mean of revealed item vectors, L2-normalized
            profiles = np.zeros((n_users, X.shape[1]), dtype=np.float32)
            for u in range(n_users):
                rev = revealed_list[u]
                profiles[u] = np.mean(X[rev], axis=0)

            prof_norms = np.linalg.norm(profiles, axis=1, keepdims=True)
            prof_norms = np.where(prof_norms > 0, prof_norms, 1.0)
            profiles /= prof_norms

            # Dot products [n_users, n_candidates]
            raw_c_mat = profiles.dot(X.T).astype(np.float32)

            pct_c_mat = np.full((n_users, n_candidates), -np.inf, dtype=np.float32)
            for u in range(n_users):
                act_idx = active_indices_list[u]
                ranks = st.rankdata(raw_c_mat[u, act_idx], method="average")
                pct_c_mat[u, act_idx] = (ranks - 1.0) / float(len(act_idx) - 1.0)

            pct_c_cache[(k_val, variant)] = pct_c_mat

            # Content-only baseline (alpha=1.0)
            c_topk = select_topk_exact(pct_c_mat, k=10, tie_ranks=evaluator.tie_ranks)
            c_hits = compute_hits(c_topk, ground_truth_list)
            c_ndcgs = ndcg_at_k(c_hits, gt_counts, 10)
            c_mn, _, _ = compute_bootstrap_ci(c_ndcgs, n_resamples=200, seed=42)
            content_only_ndcgs[(k_val, variant)] = c_ndcgs

    # 3. Alpha Sweep per K
    print("\n[3/4] Evaluating alpha in {0.1, ..., 0.8} per K...")
    alphas = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]

    # Structure to hold tuning curves
    sweep_results = {k_val: [] for k_val in k_values}

    for k_val in k_values:
        pop_all = pop_ndcg_baseline[(k_val, "all_candidates")]
        pop_lt = pop_ndcg_baseline[(k_val, "long_tail")]

        pct_c_all = pct_c_cache[(k_val, "all_candidates")]
        pct_p_all = cohort_data[(k_val, "all_candidates")]["pct_p_mat"]
        gt_list_all = cohort_data[(k_val, "all_candidates")]["ground_truth_list"]
        gt_counts_all = cohort_data[(k_val, "all_candidates")]["gt_counts"]

        pct_c_lt = pct_c_cache[(k_val, "long_tail")]
        pct_p_lt = cohort_data[(k_val, "long_tail")]["pct_p_mat"]
        gt_list_lt = cohort_data[(k_val, "long_tail")]["ground_truth_list"]
        gt_counts_lt = cohort_data[(k_val, "long_tail")]["gt_counts"]

        for alpha in alphas:
            # (i) all_candidates
            blend_all = alpha * pct_c_all + (1.0 - alpha) * pct_p_all
            topk_all = select_topk_exact(blend_all, k=10, tie_ranks=evaluator.tie_ranks)
            ndcg_all = float(np.mean(ndcg_at_k(compute_hits(topk_all, gt_list_all), gt_counts_all, 10)))

            # (ii) long_tail
            blend_lt = alpha * pct_c_lt + (1.0 - alpha) * pct_p_lt
            topk_lt = select_topk_exact(blend_lt, k=10, tie_ranks=evaluator.tie_ranks)
            ndcg_lt = float(np.mean(ndcg_at_k(compute_hits(topk_lt, gt_list_lt), gt_counts_lt, 10)))

            lift_all = ndcg_all / pop_all
            lift_lt = ndcg_lt / pop_lt
            rel_obj = 0.5 * (lift_all + lift_lt)
            constraint_met = (ndcg_all >= pop_all)

            sweep_results[k_val].append({
                "alpha": alpha,
                "ndcg_all": ndcg_all,
                "ndcg_lt": ndcg_lt,
                "lift_all": lift_all,
                "lift_lt": lift_lt,
                "rel_obj": rel_obj,
                "constraint_met": constraint_met,
            })

    print("\nALPHA SWEEP TABLE PER K:")
    print(f"{'K':<3} {'Alpha':<6} {'NDCG_all':<10} {'NDCG_lt':<10} {'Lift_all':<10} {'Lift_lt':<10} {'AvgRelLift':<12} {'Constraint':<10}")
    print("-" * 75)
    optimal_raw = {}
    for k_val in k_values:
        for r in sweep_results[k_val]:
            print(
                f"{k_val:<3} {r['alpha']:<6.1f} {r['ndcg_all']:<10.4f} {r['ndcg_lt']:<10.4f} "
                f"{r['lift_all']:<10.4f} {r['lift_lt']:<10.4f} {r['rel_obj']:<12.4f} {'MET' if r['constraint_met'] else 'FAIL':<10}"
            )
        # Select best under constraint
        valid_candidates = [r for r in sweep_results[k_val] if r["constraint_met"]]
        best_r = max(valid_candidates, key=lambda x: x["rel_obj"])
        optimal_raw[k_val] = best_r["alpha"]

    print("\nRAW OPTIMAL ALPHA PER K:")
    for k_val in k_values:
        print(f"  K={k_val}: raw optimal alpha = {optimal_raw[k_val]}")

    # Monotone smoothing check
    # As K increases, user profile contains more information, so alpha should be non-decreasing: alpha(K_i) <= alpha(K_{i+1})
    smoothed_alpha = {}
    cur_alpha = 0.0
    for k_val in k_values:
        a = optimal_raw[k_val]
        if a < cur_alpha:
            print(f"  Note: Smoothing K={k_val} from {a} to {cur_alpha} for monotonicity.")
            smoothed_alpha[k_val] = cur_alpha
        else:
            smoothed_alpha[k_val] = a
            cur_alpha = a

    print("\nFINAL CHOSEN ALPHA SCHEDULE (by K):")
    for k_val in k_values:
        print(f"  K={k_val}: alpha = {smoothed_alpha[k_val]}")

    # Bucket mapping:
    # K 3-4 -> tuned K=3
    # K 5-7 -> tuned K=5
    # K 8-14 -> tuned K=10
    # K >= 15 -> tuned K=20
    alpha_buckets = {
        "K_3_4": float(smoothed_alpha[3]),
        "K_5_7": float(smoothed_alpha[5]),
        "K_8_14": float(smoothed_alpha[10]),
        "K_15_plus": float(smoothed_alpha[20]),
    }

    # 4. Final Evaluation with 1000 Bootstrap Resamples
    print("\n[4/4] Final Evaluation with 1000 bootstrap resamples...")
    final_rows = []

    for k_val in k_values:
        opt_alpha = smoothed_alpha[k_val]
        v1_alpha = 0.1

        for variant in variants:
            cohort = cohort_data[(k_val, variant)]
            n_users = cohort["n_users"]
            n_excl = cohort["n_excluded"]
            gt_counts = cohort["gt_counts"]
            gt_list = cohort["ground_truth_list"]
            pct_p = cohort["pct_p_mat"]
            pct_c = pct_c_cache[(k_val, variant)]
            pop_ndcgs = cohort["pop_ndcgs"]
            c_ndcgs = content_only_ndcgs[(k_val, variant)]

            # Hybrid v1 (alpha = 0.1)
            blend_v1 = v1_alpha * pct_c + (1.0 - v1_alpha) * pct_p
            topk_v1 = select_topk_exact(blend_v1, k=10, tie_ranks=evaluator.tie_ranks)
            v1_ndcgs = ndcg_at_k(compute_hits(topk_v1, gt_list), gt_counts, 10)

            # Hybrid v1.1 (opt_alpha)
            blend_v11 = opt_alpha * pct_c + (1.0 - opt_alpha) * pct_p
            topk_v11 = select_topk_exact(blend_v11, k=10, tie_ranks=evaluator.tie_ranks)
            v11_ndcgs = ndcg_at_k(compute_hits(topk_v11, gt_list), gt_counts, 10)

            # Bootstrap CIs (1000 resamples)
            pop_mean, pop_lo, pop_hi = compute_bootstrap_ci(pop_ndcgs, n_resamples=1000, seed=42)
            c_mean, c_lo, c_hi = compute_bootstrap_ci(c_ndcgs, n_resamples=1000, seed=42)
            v1_mean, v1_lo, v1_hi = compute_bootstrap_ci(v1_ndcgs, n_resamples=1000, seed=42)
            v11_mean, v11_lo, v11_hi = compute_bootstrap_ci(v11_ndcgs, n_resamples=1000, seed=42)

            # Paired comparisons
            d_v1_pop, d_v1_pop_lo, d_v1_pop_hi, better_v1_pop = compute_paired_bootstrap(v11_ndcgs, pop_ndcgs, n_resamples=1000, seed=42)
            d_v1_v1, d_v1_v1_lo, d_v1_v1_hi, better_v1_v1 = compute_paired_bootstrap(v11_ndcgs, v1_ndcgs, n_resamples=1000, seed=42)

            final_rows.append({
                "k": k_val,
                "variant": variant,
                "n_users": n_users,
                "n_excluded": n_excl,
                "alpha_v1": v1_alpha,
                "alpha_v1_1": opt_alpha,
                "pop_ndcg": round(pop_mean, 4),
                "pop_ci": [round(pop_lo, 4), round(pop_hi, 4)],
                "content_ndcg": round(c_mean, 4),
                "content_ci": [round(c_lo, 4), round(c_hi, 4)],
                "v1_ndcg": round(v1_mean, 4),
                "v1_ci": [round(v1_lo, 4), round(v1_hi, 4)],
                "v1_1_ndcg": round(v11_mean, 4),
                "v1_1_ci": [round(v11_lo, 4), round(v11_hi, 4)],
                "diff_vs_pop": round(d_v1_pop, 4),
                "diff_vs_pop_ci": [round(d_v1_pop_lo, 4), round(d_v1_pop_hi, 4)],
                "v1_1_better_than_pop": better_v1_pop,
                "diff_vs_v1": round(d_v1_v1, 4),
                "diff_vs_v1_ci": [round(d_v1_v1_lo, 4), round(d_v1_v1_hi, 4)],
                "v1_1_better_than_v1": better_v1_v1,
            })

    print("\nFINAL RESULTS TABLE (1000 Bootstrap Resamples):")
    print(f"{'K':<3} {'Variant':<15} {'Users':<6} {'Pop NDCG':<12} {'V1 (a=0.1)':<12} {'V1.1 (Sched)':<14} {'Diff vs Pop':<16} {'Diff vs V1':<16}")
    print("-" * 95)
    for r in final_rows:
        print(
            f"{r['k']:<3} {r['variant']:<15} {r['n_users']:<6} "
            f"{r['pop_ndcg']:.4f} {r['pop_ci']} "
            f"{r['v1_ndcg']:.4f} {r['v1_ci']} "
            f"{r['v1_1_ndcg']:.4f} {r['v1_1_ci']} "
            f"{r['diff_vs_pop']:+.4f} {r['diff_vs_pop_ci']} "
            f"{r['diff_vs_v1']:+.4f} {r['diff_vs_v1_ci']}"
        )

    # Write hybrid_v1_1.yaml
    git_info = get_git_info()
    v1_1_config = {
        "version": "hybrid_v1.1",
        "alpha_by_bucket": alpha_buckets,
        "alpha_by_k": {int(k): float(v) for k, v in smoothed_alpha.items()},
        "block_weights": {
            "w_t1": w_t1,
            "w_tags": w_tags,
            "w_genome": w_genome,
        },
        "normalization": "percentile",
        "tie_break_seed": 42,
        "similarity_threshold": sim_threshold,
        "snapshot_features": True,
        "snapshot_leakage_warning": (
            "Tag TF-IDF and Genome features were aggregated over entire history (up to Nov 2019). "
            "They leak semantic signals across chronological splits. Labeled as 'Snapshot Features' per protocol."
        ),
        "tuned_on": "cold_dev",
        "tuning_protocol": "Cold-Start Protocol v2 (K in {3,5,10,20}, W=20)",
        "selection_objective": "mean(NDCG_all/NDCG_pop_all, NDCG_lt/NDCG_pop_lt) subject to NDCG_all >= NDCG_pop_all",
        "serving_buckets": {
            "K_3_4": {"min_k": 3, "max_k": 4, "tuned_k": 3, "alpha": alpha_buckets["K_3_4"]},
            "K_5_7": {"min_k": 5, "max_k": 7, "tuned_k": 5, "alpha": alpha_buckets["K_5_7"]},
            "K_8_14": {"min_k": 8, "max_k": 14, "tuned_k": 10, "alpha": alpha_buckets["K_8_14"]},
            "K_15_plus": {"min_k": 15, "max_k": 50, "tuned_k": 20, "alpha": alpha_buckets["K_15_plus"]},
        },
        "provenance": {
            "git_commit": git_info["git_commit"],
            "git_dirty": git_info["git_dirty"],
            "runtime_seconds": round(time.time() - t_start, 1),
        },
        "notes": (
            "Tuned strictly on cold_dev interactions; bootstrap CIs are optimistic. "
            "The final evaluation on cold_final is reserved for the final benchmark phase."
        ),
    }

    OUTPUT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(v1_1_config, f, sort_keys=False)
    print(f"\nConfig written to {OUTPUT_CONFIG_PATH}")

    # Write JSON results
    json_output = {
        "metadata": {
            "config_version": "hybrid_v1.1",
            "alpha_schedule": alpha_buckets,
            "tuned_alphas_per_k": smoothed_alpha,
            "raw_optimal_alphas": optimal_raw,
            "selection_objective": "mean(NDCG_all/NDCG_pop_all, NDCG_lt/NDCG_pop_lt)",
            "selection_constraint": "NDCG_all >= NDCG_pop_all",
            "provenance": git_info,
            "tuning_note": "Tuned on cold_dev. One-shot cold_final run reserved for final phase.",
        },
        "sweep_curves": sweep_results,
        "evaluation_results": final_rows,
    }

    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2)
    print(f"Results JSON written to {OUTPUT_JSON_PATH}")

    # Write CSV results
    csv_rows = []
    for r in final_rows:
        csv_rows.append({
            "k": r["k"],
            "variant": r["variant"],
            "n_users": r["n_users"],
            "n_excluded": r["n_excluded"],
            "alpha_v1": r["alpha_v1"],
            "alpha_v1_1": r["alpha_v1_1"],
            "popularity_ndcg": r["pop_ndcg"],
            "popularity_ci_lower": r["pop_ci"][0],
            "popularity_ci_upper": r["pop_ci"][1],
            "content_only_ndcg": r["content_ndcg"],
            "content_only_ci_lower": r["content_ci"][0],
            "content_only_ci_upper": r["content_ci"][1],
            "hybrid_v1_ndcg": r["v1_ndcg"],
            "hybrid_v1_ci_lower": r["v1_ci"][0],
            "hybrid_v1_ci_upper": r["v1_ci"][1],
            "hybrid_v1_1_ndcg": r["v1_1_ndcg"],
            "hybrid_v1_1_ci_lower": r["v1_1_ci"][0],
            "hybrid_v1_1_ci_upper": r["v1_1_ci"][1],
            "diff_vs_pop": r["diff_vs_pop"],
            "diff_vs_pop_ci_lower": r["diff_vs_pop_ci"][0],
            "diff_vs_pop_ci_upper": r["diff_vs_pop_ci"][1],
            "v1_1_better_than_pop": r["v1_1_better_than_pop"],
            "diff_vs_v1": r["diff_vs_v1"],
            "diff_vs_v1_ci_lower": r["diff_vs_v1_ci"][0],
            "diff_vs_v1_ci_upper": r["diff_vs_v1_ci"][1],
            "v1_1_better_than_v1": r["v1_1_better_than_v1"],
        })
    pd.DataFrame(csv_rows).to_csv(OUTPUT_CSV_PATH, index=False)
    print(f"Results CSV written to {OUTPUT_CSV_PATH}")

    print(f"\nDone in {time.time() - t_start:.1f}s")


if __name__ == "__main__":
    main()
