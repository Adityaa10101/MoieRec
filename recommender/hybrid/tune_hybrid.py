#!/usr/bin/env python3
"""
recommender/hybrid/tune_hybrid.py
===================================
Phase 2F Part A: Offline grid search for the hybrid content + popularity model.

Protocol:
- cold_dev only (cold_final is strictly guarded and never touched)
- Cold-Start Protocol v2: K in {3, 5, 10}, W=20
- Variants: (i) all_candidates, (ii) long_tail (excluding top-200 train movies)
- Grid: alpha in {0, 0.1, ..., 1.0} x (w_tags in {2,4,8,16}) x (w_genome in {0.25,0.5,1.0})
  with w_t1=1 fixed
- Selection objective: mean NDCG@10 over K in {3,5,10} on variant (i)
- Reject configs where variant (ii) NDCG < popularity baseline NDCG
- Fast dev mode: cached component scores, 200 bootstrap resamples for grid search,
  1000 for final chosen config

Sanity checks:
- alpha=0 reproduces popularity NDCG (assert within 1e-3)
- alpha=1 reproduces content-only NDCG (assert within 1e-3)

Outputs:
- recommender/config/hybrid_v1.yaml
- recommender/results/hybrid_v1_cold_dev.json
- recommender/results/hybrid_v1_cold_dev.csv
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
import scipy.sparse as sp
import scipy.stats as st

# Guard: never touch cold_final or test.parquet
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SPLITS_DIR = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "splits"
FEAT_DIR = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "features"
ID_MAP_DIR = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "id_mappings"
RESULTS_DIR = PROJECT_ROOT / "recommender" / "results"
CONFIG_DIR = PROJECT_ROOT / "recommender" / "config"

_FORBIDDEN = {"test.parquet", "cold_final"}
for _f in _FORBIDDEN:
    for _p in [SPLITS_DIR, FEAT_DIR]:
        assert _f not in str(_p), f"Forbidden path: {_f}"

from recommender.evaluation.cold_start import ColdStartEvaluator, load_cold_start_split
from recommender.evaluation.evaluator import compute_bootstrap_ci, select_topk_exact
from recommender.evaluation.metrics import ndcg_at_k, compute_hits


# ---------------------------------------------------------------------------
# Feature loading and construction
# ---------------------------------------------------------------------------

def load_features(feat_dir: Path, id_map_dir: Path) -> Dict[str, Any]:
    """Load all Tier 2 feature blocks + metadata needed for hybrid model."""
    meta = json.loads((feat_dir / "feature_metadata.json").read_text(encoding="utf-8"))
    t1_info = meta["tier1_baseline"]
    feature_names_t1 = list(t1_info["feature_names"])
    n_genres = int(t1_info["n_genres"])

    # ID mapping: movie_id -> benchmark_idx
    m2b_df = pd.read_parquet(id_map_dir / "movie_id_to_benchmark_idx.parquet")
    m2b = m2b_df.set_index("movie_id")["benchmark_idx"].to_dict()

    # Tier 1 sparse
    t1_csr = sp.load_npz(feat_dir / "tier1_baseline_features.npz")
    n_total = t1_csr.shape[0]

    # Tag TF-IDF sparse
    tag_csr = sp.load_npz(feat_dir / "tier2_tag_tfidf.npz")

    # Genome matrix + mask
    genome_mat = np.load(feat_dir / "tier2_genome_matrix.npy", mmap_mode="r")
    genome_mask = np.load(feat_dir / "tier2_genome_mask.npy", mmap_mode="r")

    # Genome tag names
    full_genome_tags = pd.read_parquet(PROJECT_ROOT / "data" / "processed" / "ml-25m" / "full" / "genome_tags.parquet")
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
        "n_total": n_total,
    }


def build_item_features(
    candidate_movie_ids: np.ndarray,
    feats: Dict[str, Any],
    w_t1: float = 1.0,
    w_tags: float = 1.0,
    w_genome: float = 1.0,
) -> Tuple[np.ndarray, List[str]]:
    """Build L2-normalized Tier 2 item feature matrix for candidates with given block weights."""
    m2b = feats["m2b"]
    t1_csr = feats["t1_csr"]
    tag_csr = feats["tag_csr"]
    genome_mat = feats["genome_mat"]
    genome_mask = feats["genome_mask"]
    feature_names_t1 = feats["feature_names_t1"]

    bench_indices = np.array([m2b.get(mid, -1) for mid in candidate_movie_ids], dtype=np.int32)
    valid_mask = bench_indices >= 0
    safe_indices = np.where(valid_mask, bench_indices, 0)

    # 1. Tier 1 block
    cand_t1 = t1_csr[safe_indices].toarray().astype(np.float32)
    cand_t1[~valid_mask] = 0.0
    t1_norms = np.linalg.norm(cand_t1, axis=1, keepdims=True)
    t1_norms = np.where(t1_norms > 0, t1_norms, 1.0)
    cand_t1_normed = cand_t1 / t1_norms

    blocks = [cand_t1_normed * w_t1]
    all_names = [f"t1:{n}" for n in feature_names_t1]

    # 2. Tag TF-IDF block
    if w_tags > 0:
        tags_raw = tag_csr[safe_indices]
        tag_norms_arr = np.array(tags_raw.power(2).sum(axis=1)).flatten() ** 0.5
        tag_norms_arr = np.where(tag_norms_arr > 0, tag_norms_arr, 1.0)
        tags_dense = tags_raw.toarray().astype(np.float32)
        tags_dense /= tag_norms_arr[:, None]
        tags_dense[~valid_mask] = 0.0
        blocks.append(tags_dense * w_tags)
        all_names.extend([f"tag_tfidf_{i}" for i in range(tags_dense.shape[1])])
        del tags_raw, tags_dense

    # 3. Genome block
    if w_genome > 0:
        gm = genome_mat[safe_indices].astype(np.float32)
        gm_mask = genome_mask[safe_indices].astype(np.float32)[:, None]
        masked_gm = gm * gm_mask
        masked_gm[~valid_mask] = 0.0
        gen_norms = np.linalg.norm(masked_gm, axis=1, keepdims=True)
        gen_norms = np.where(gen_norms > 0, gen_norms, 1.0)
        genome_block = (masked_gm / gen_norms) * w_genome
        blocks.append(genome_block)
        all_names.extend([f"genome_dim_{i}" for i in range(gm.shape[1])])

    concat_X = np.hstack(blocks).astype(np.float32)
    total_norms = np.linalg.norm(concat_X, axis=1, keepdims=True)
    total_norms = np.where(total_norms > 0, total_norms, 1.0)
    X = (concat_X / total_norms).astype(np.float32)

    return X, all_names


def build_cold_start_profiles(
    revealed_list: List[List[int]],
    item_features: np.ndarray,
    n_candidates: int,
) -> np.ndarray:
    """Build L2-normalized user taste profile vectors as mean of revealed items' feature vectors."""
    n_users = len(revealed_list)
    row_indices, col_indices, data_vals = [], [], []
    for u_idx, rev in enumerate(revealed_list):
        k = max(len(rev), 1)
        w = 1.0 / float(k)
        for cand_i in rev:
            row_indices.append(u_idx)
            col_indices.append(cand_i)
            data_vals.append(w)

    W = sp.csr_matrix(
        (data_vals, (row_indices, col_indices)),
        shape=(n_users, n_candidates),
        dtype=np.float32,
    )
    raw = W.dot(item_features).astype(np.float32)
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    safe_norms = np.where(norms > 0, norms, 1.0)
    return raw / safe_norms


from recommender.evaluation.cold_start import compute_canonical_top200_train_mids

compute_top200_train_movies = compute_canonical_top200_train_mids


def percentile_rank(scores: np.ndarray) -> np.ndarray:
    """Convert raw scores to percentile ranks in [0, 1] (ties get average rank).
    Higher score -> higher rank -> closer to 1.0.
    """
    n = len(scores)
    if n <= 1:
        return np.ones(n, dtype=np.float64) if n == 1 else scores.copy()
    ranks = st.rankdata(scores, method="average")
    return (ranks - 1.0) / float(n - 1.0)


# ---------------------------------------------------------------------------
# Grid Search Execution
# ---------------------------------------------------------------------------

def run_grid_search() -> None:
    t0 = time.time()
    print("=" * 70, flush=True)
    print("Phase 2F Part A — Hybrid Content+Popularity Grid Search", flush=True)
    print("=" * 70, flush=True)

    # 1. Load cold_dev
    print("\n[1/6] Loading cold_dev interactions...", flush=True)
    cold_df = load_cold_start_split(split="cold_dev", final=False)
    print(f"  cold_dev: {cold_df['user_id'].nunique():,} users, {len(cold_df):,} rows", flush=True)

    # 2. Load train for popularity + top200
    print("[2/6] Loading train data...", flush=True)
    train_df = pd.read_parquet(SPLITS_DIR / "train.parquet")
    train_stats = pd.read_parquet(SPLITS_DIR / "train_movie_stats.parquet")
    print(f"  train: {len(train_df):,} rows, {train_df['movie_id'].nunique():,} movies", flush=True)

    top200_mids = compute_top200_train_movies(train_df)

    # Candidate catalog from benchmark movies
    bench_movies = pd.read_parquet(
        PROJECT_ROOT / "data" / "processed" / "ml-25m" / "benchmark" / "movies.parquet"
    )
    candidate_movie_ids = np.sort(bench_movies["movie_id"].unique())
    n_candidates = len(candidate_movie_ids)
    print(f"  Candidate catalog: {n_candidates:,} movies", flush=True)

    # Popularity scores aligned to candidate_movie_ids
    stats_dict = train_stats.set_index("movie_id")["positive_rating_count"].to_dict()
    pop_scores = np.array(
        [stats_dict.get(mid, 0) for mid in candidate_movie_ids], dtype=np.float32
    )

    # Create ColdStartEvaluator
    evaluator = ColdStartEvaluator(
        cold_df=cold_df,
        candidate_movie_ids=candidate_movie_ids,
        positive_threshold=4.0,
        k_eval=10,
        n_bootstrap=200,  # fast dev mode
        seed=42,
    )

    # 3. Load feature matrices
    print("[3/6] Loading feature matrices...", flush=True)
    feats = load_features(FEAT_DIR, ID_MAP_DIR)
    print(f"  T1 shape: {feats['t1_csr'].shape}", flush=True)
    print(f"  Tags shape: {feats['tag_csr'].shape}", flush=True)
    print(f"  Genome shape: {feats['genome_mat'].shape}", flush=True)

    # 4. Precompute cold_start data and popularity percentile ranks for all 6 settings
    print("\n[4/6] Precomputing evaluation cohorts and popularity baseline...", flush=True)
    k_values = [3, 5, 10]
    variants = ["all_candidates", "long_tail"]

    cohort_data = {}  # (k_ob, variant) -> dict
    pop_ndcgs_ref = {}

    for k_ob in k_values:
        for variant in variants:
            long_tail = (variant == "long_tail")
            eval_users, revealed_list, ground_truth_list, mask_idx_list, n_excl = (
                evaluator.prepare_data_v2(
                    k_onboarding=k_ob, window_w=20, long_tail=long_tail,
                    top200_train_mids=top200_mids if long_tail else None,
                )
            )
            n_users = len(eval_users)
            gt_counts = np.array([len(gt) for gt in ground_truth_list], dtype=np.int64)

            # Build precomputed boolean masks and popularity percentile matrix [n_users, n_candidates]
            pct_p_mat = np.full((n_users, n_candidates), -np.inf, dtype=np.float32)
            active_indices_list = []
            mask_bool_mat = np.zeros((n_users, n_candidates), dtype=bool)

            for u_idx in range(n_users):
                mask_set = mask_idx_list[u_idx]
                mask_arr = np.fromiter(mask_set, dtype=np.int32, count=len(mask_set))
                mask_bool_mat[u_idx, mask_arr] = True
                active_idx = np.where(~mask_bool_mat[u_idx])[0]
                active_indices_list.append(active_idx)
                # Percentile rank of pop_scores over active pool
                ranks = st.rankdata(pop_scores[active_idx], method="average")
                pct_p_mat[u_idx, active_idx] = (ranks - 1.0) / float(len(active_idx) - 1.0)

            # Evaluate Popularity baseline (alpha=0)
            pop_topk = select_topk_exact(pct_p_mat, k=10, tie_ranks=evaluator.tie_ranks)
            pop_hits = compute_hits(pop_topk, ground_truth_list)
            pop_ndcgs = ndcg_at_k(pop_hits, gt_counts, 10)
            pop_mn, pop_lo, pop_hi = compute_bootstrap_ci(pop_ndcgs, n_resamples=200, seed=42)
            pop_ndcgs_ref[(k_ob, variant)] = pop_mn
            print(f"  Pop K={k_ob:<2} {variant:<15}: n_users={n_users:<5} NDCG@10={pop_mn:.4f} [{pop_lo:.4f}, {pop_hi:.4f}]", flush=True)

            cohort_data[(k_ob, variant)] = {
                "eval_users": eval_users,
                "revealed_list": revealed_list,
                "ground_truth_list": ground_truth_list,
                "gt_counts": gt_counts,
                "mask_bool_mat": mask_bool_mat,
                "active_indices_list": active_indices_list,
                "pct_p_mat": pct_p_mat,
                "n_users": n_users,
                "n_excluded": n_excl,
            }

    # 5. Grid Search
    alphas = [round(a * 0.1, 1) for a in range(0, 11)]  # 0.0 to 1.0
    w_tags_grid = [2, 4, 8, 16]
    w_genome_grid = [0.25, 0.5, 1.0]
    w_t1 = 1.0

    n_weight_combos = len(w_tags_grid) * len(w_genome_grid)
    n_configs = n_weight_combos * len(alphas)
    print(f"\n[5/6] Running grid search: {len(alphas)} alphas x {len(w_tags_grid)} w_tags x {len(w_genome_grid)} w_genome = {n_configs} configs", flush=True)
    print("  (Component scores cached per weight combo; fast vectorized alpha sweep)", flush=True)

    grid_results = []
    combo_idx = 0

    for w_tags in w_tags_grid:
        for w_genome in w_genome_grid:
            combo_idx += 1
            t_combo = time.time()
            print(f"\n  Weight combo {combo_idx}/{n_weight_combos}: w_t1={w_t1} w_tags={w_tags} w_genome={w_genome}", flush=True)

            # Build item feature matrix X
            X, feat_names = build_item_features(
                candidate_movie_ids=candidate_movie_ids,
                feats=feats,
                w_t1=w_t1,
                w_tags=w_tags,
                w_genome=w_genome,
            )

            # Precompute content percentile matrices for all 6 settings
            content_pct_cache = {}
            for k_ob in k_values:
                for variant in variants:
                    cohort = cohort_data[(k_ob, variant)]
                    n_u = cohort["n_users"]
                    if n_u == 0:
                        content_pct_cache[(k_ob, variant)] = None
                        continue

                    profiles = build_cold_start_profiles(cohort["revealed_list"], X, n_candidates)
                    c_scores = (X @ profiles.T).T.astype(np.float64)  # [n_u, n_candidates]

                    pct_c_mat = np.full((n_u, n_candidates), -np.inf, dtype=np.float32)
                    for u_idx in range(n_u):
                        active_idx = cohort["active_indices_list"][u_idx]
                        ranks = st.rankdata(c_scores[u_idx, active_idx], method="average")
                        pct_c_mat[u_idx, active_idx] = (ranks - 1.0) / float(len(active_idx) - 1.0)

                    content_pct_cache[(k_ob, variant)] = pct_c_mat

            # Sweep over alpha
            for alpha in alphas:
                ndcgs_by_setting = {}
                objective_parts = []

                for k_ob in k_values:
                    for variant in variants:
                        cohort = cohort_data[(k_ob, variant)]
                        n_u = cohort["n_users"]
                        pct_c_mat = content_pct_cache[(k_ob, variant)]

                        if n_u == 0 or pct_c_mat is None:
                            ndcgs_by_setting[(k_ob, variant)] = 0.0
                            continue

                        pct_p_mat = cohort["pct_p_mat"]
                        mask_bool = cohort["mask_bool_mat"]

                        # Hybrid blend on active items; masked items remain -np.inf
                        final_scores = np.where(
                            mask_bool,
                            -np.inf,
                            alpha * pct_c_mat + (1.0 - alpha) * pct_p_mat,
                        )

                        topk = select_topk_exact(final_scores, k=10, tie_ranks=evaluator.tie_ranks)
                        hits = compute_hits(topk, cohort["ground_truth_list"])
                        ndcgs = ndcg_at_k(hits, cohort["gt_counts"], 10)
                        mn, _, _ = compute_bootstrap_ci(ndcgs, n_resamples=200, seed=42)
                        ndcgs_by_setting[(k_ob, variant)] = mn

                        if variant == "all_candidates":
                            objective_parts.append(mn)

                # Objective: mean NDCG@10 over K in {3,5,10} on variant (i)
                obj = float(np.mean(objective_parts)) if objective_parts else 0.0

                # Reject check: variant (ii) NDCG must be >= popularity baseline for all K
                rejected = False
                for k_ob in k_values:
                    lt_ndcg = ndcgs_by_setting.get((k_ob, "long_tail"), 0.0)
                    pop_lt = pop_ndcgs_ref.get((k_ob, "long_tail"), 0.0)
                    if lt_ndcg < pop_lt - 1e-6:
                        rejected = True
                        break

                grid_results.append({
                    "alpha": alpha,
                    "w_t1": w_t1,
                    "w_tags": w_tags,
                    "w_genome": w_genome,
                    "objective": obj,
                    "rejected": rejected,
                    "ndcgs": {
                        str(k): {
                            "all": ndcgs_by_setting.get((k, "all_candidates"), 0.0),
                            "lt": ndcgs_by_setting.get((k, "long_tail"), 0.0),
                        }
                        for k in k_values
                    },
                })

            print(f"    Alpha sweep finished in {time.time()-t_combo:.1f}s", flush=True)

    # Sort valid results by objective descending
    valid_results = [r for r in grid_results if not r["rejected"]]
    valid_results.sort(key=lambda x: x["objective"], reverse=True)

    if not valid_results:
        print("\nWARNING: All configs rejected! Using best overall config.", flush=True)
        valid_results = sorted(grid_results, key=lambda x: x["objective"], reverse=True)

    top5 = valid_results[:5]
    best = top5[0]

    print("\n" + "=" * 70, flush=True)
    print("TOP 5 CONFIGS (by mean NDCG@10 over K in {3,5,10}, variant (i)):", flush=True)
    print("=" * 70, flush=True)
    for i, cfg in enumerate(top5):
        rej_flag = " [REJECTED]" if cfg["rejected"] else ""
        print(f"  #{i+1}: alpha={cfg['alpha']} w_t1={cfg['w_t1']} w_tags={cfg['w_tags']} w_genome={cfg['w_genome']}", flush=True)
        print(f"       obj={cfg['objective']:.4f}{rej_flag}", flush=True)
        for k_ob in k_values:
            k_str = str(k_ob)
            print(f"       K={k_ob}: all={cfg['ndcgs'][k_str]['all']:.4f} lt={cfg['ndcgs'][k_str]['lt']:.4f}", flush=True)

    # Check grid edges
    edge_notes = []
    if best["alpha"] in [0.0, 1.0]:
        edge_notes.append(f"alpha={best['alpha']} is at alpha grid edge")
    if best["w_tags"] in [min(w_tags_grid), max(w_tags_grid)]:
        edge_notes.append(f"w_tags={best['w_tags']} is at grid edge ({min(w_tags_grid)}-{max(w_tags_grid)})")
    if best["w_genome"] in [min(w_genome_grid), max(w_genome_grid)]:
        edge_notes.append(f"w_genome={best['w_genome']} is at grid edge ({min(w_genome_grid)}-{max(w_genome_grid)})")

    if edge_notes:
        print("\nGRID EDGE NOTE: Best config touches grid boundaries:", flush=True)
        for note in edge_notes:
            print(f"  - {note}", flush=True)
    else:
        print("\n  Best config is interior (not on grid edge).", flush=True)

    # NDCG vs alpha curves for best weight combo
    best_w_tags = best["w_tags"]
    best_w_genome = best["w_genome"]

    alpha_curve_data = {}
    for k_ob in k_values:
        for variant in variants:
            alpha_curve_data[(k_ob, variant)] = []
            for r in grid_results:
                if r["w_tags"] == best_w_tags and r["w_genome"] == best_w_genome:
                    k_str = str(k_ob)
                    v_key = "all" if variant == "all_candidates" else "lt"
                    alpha_curve_data[(k_ob, variant)].append({
                        "alpha": r["alpha"],
                        "ndcg": round(r["ndcgs"][k_str][v_key], 4),
                    })
            alpha_curve_data[(k_ob, variant)].sort(key=lambda x: x["alpha"])

    print("\nNDCG-VS-ALPHA CURVES (for chosen weights w_tags={}, w_genome={}):".format(best_w_tags, best_w_genome), flush=True)
    for (k_ob, variant), curve in sorted(alpha_curve_data.items()):
        vals_str = " ".join(f"{c['alpha']}:{c['ndcg']:.4f}" for c in curve)
        print(f"  K={k_ob:<2} {variant:<15}: {vals_str}", flush=True)

    # 6. Final Evaluation with 1000 resamples
    print("\n[6/6] Final evaluation with 1000 resamples on chosen config...", flush=True)
    X_final, feat_names_final = build_item_features(
        candidate_movie_ids=candidate_movie_ids,
        feats=feats,
        w_t1=w_t1,
        w_tags=best_w_tags,
        w_genome=best_w_genome,
    )

    # Compute similarity threshold for Reason Code SIMILAR_TO_PICK:
    # 95th percentile of cosine over 50,000 random item pairs
    print("  Computing data-derived similarity threshold (95th pct of pairwise item cosines)...", flush=True)
    rng_sim = np.random.default_rng(42)
    n_sample_pairs = 50000
    idx_a = rng_sim.integers(0, n_candidates, size=n_sample_pairs)
    idx_b = rng_sim.integers(0, n_candidates, size=n_sample_pairs)
    pair_cosines = np.sum(X_final[idx_a] * X_final[idx_b], axis=1)
    sim_threshold = float(np.percentile(pair_cosines, 95.0))
    print(f"  Similarity threshold (95th pct, 50k pairs): {sim_threshold:.4f}", flush=True)

    final_results = []
    alpha_chosen = best["alpha"]

    for k_ob in k_values:
        for variant in variants:
            cohort = cohort_data[(k_ob, variant)]
            n_u = cohort["n_users"]
            gt_counts = cohort["gt_counts"]
            gt_list = cohort["ground_truth_list"]
            mask_bool = cohort["mask_bool_mat"]
            pct_p_mat = cohort["pct_p_mat"]

            profiles = build_cold_start_profiles(cohort["revealed_list"], X_final, n_candidates)
            c_scores = (X_final @ profiles.T).T.astype(np.float64)

            pct_c_mat = np.full((n_u, n_candidates), -np.inf, dtype=np.float32)
            for u_idx in range(n_u):
                active_idx = cohort["active_indices_list"][u_idx]
                ranks = st.rankdata(c_scores[u_idx, active_idx], method="average")
                pct_c_mat[u_idx, active_idx] = (ranks - 1.0) / float(len(active_idx) - 1.0)

            # Popularity (alpha=0)
            pop_scores_final = np.where(mask_bool, -np.inf, pct_p_mat)
            pop_topk = select_topk_exact(pop_scores_final, k=10, tie_ranks=evaluator.tie_ranks)
            pop_hits = compute_hits(pop_topk, gt_list)
            pop_ndcgs = ndcg_at_k(pop_hits, gt_counts, 10)
            pop_mn, pop_lo, pop_hi = compute_bootstrap_ci(pop_ndcgs, n_resamples=1000, seed=42)

            # Content-only (alpha=1)
            cont_scores_final = np.where(mask_bool, -np.inf, pct_c_mat)
            cont_topk = select_topk_exact(cont_scores_final, k=10, tie_ranks=evaluator.tie_ranks)
            cont_hits = compute_hits(cont_topk, gt_list)
            cont_ndcgs = ndcg_at_k(cont_hits, gt_counts, 10)
            cont_mn, cont_lo, cont_hi = compute_bootstrap_ci(cont_ndcgs, n_resamples=1000, seed=42)

            # Hybrid
            hyb_scores_final = np.where(
                mask_bool,
                -np.inf,
                alpha_chosen * pct_c_mat + (1.0 - alpha_chosen) * pct_p_mat,
            )
            hyb_topk = select_topk_exact(hyb_scores_final, k=10, tie_ranks=evaluator.tie_ranks)
            hyb_hits = compute_hits(hyb_topk, gt_list)
            hyb_ndcgs = ndcg_at_k(hyb_hits, gt_counts, 10)
            hyb_mn, hyb_lo, hyb_hi = compute_bootstrap_ci(hyb_ndcgs, n_resamples=1000, seed=42)

            # Paired comparisons (with 95% bootstrap CI on differences)
            diff_hyb_pop = hyb_ndcgs - pop_ndcgs
            mn_diff_hp, lo_diff_hp, hi_diff_hp = compute_bootstrap_ci(diff_hyb_pop, n_resamples=1000, seed=42)
            better_hp = bool(lo_diff_hp > 0)  # CI strictly excludes zero

            diff_hyb_cont = hyb_ndcgs - cont_ndcgs
            mn_diff_hc, lo_diff_hc, hi_diff_hc = compute_bootstrap_ci(diff_hyb_cont, n_resamples=1000, seed=42)
            better_hc = bool(lo_diff_hc > 0)  # CI strictly excludes zero

            final_results.append({
                "k_onboarding": k_ob,
                "variant": variant,
                "n_users": n_u,
                "n_excluded": cohort["n_excluded"],
                "popularity": {
                    "ndcg_mean": round(pop_mn, 4),
                    "ci_lower": round(pop_lo, 4),
                    "ci_upper": round(pop_hi, 4),
                },
                "content_only": {
                    "ndcg_mean": round(cont_mn, 4),
                    "ci_lower": round(cont_lo, 4),
                    "ci_upper": round(cont_hi, 4),
                },
                "hybrid": {
                    "ndcg_mean": round(hyb_mn, 4),
                    "ci_lower": round(hyb_lo, 4),
                    "ci_upper": round(hyb_hi, 4),
                },
                "hybrid_vs_popularity": {
                    "mean_diff": round(mn_diff_hp, 4),
                    "ci_lower": round(lo_diff_hp, 4),
                    "ci_upper": round(hi_diff_hp, 4),
                    "hybrid_better": better_hp,
                    "honest_claim": "hybrid better than popularity" if better_hp else "not distinguishable from popularity",
                },
                "hybrid_vs_content": {
                    "mean_diff": round(mn_diff_hc, 4),
                    "ci_lower": round(lo_diff_hc, 4),
                    "ci_upper": round(hi_diff_hc, 4),
                    "hybrid_better": better_hc,
                    "honest_claim": "hybrid better than content" if better_hc else "not distinguishable from content",
                },
            })

            print(
                f"  K={k_ob:<2} {variant:<15}: pop={pop_mn:.4f} [{pop_lo:.4f},{pop_hi:.4f}] "
                f"content={cont_mn:.4f} [{cont_lo:.4f},{cont_hi:.4f}] "
                f"hybrid={hyb_mn:.4f} [{hyb_lo:.4f},{hyb_hi:.4f}] "
                f"(diff_pop={mn_diff_hp:+.4f} [{lo_diff_hp:+.4f},{hi_diff_hp:+.4f}], better={better_hp}; "
                f"diff_cont={mn_diff_hc:+.4f} [{lo_diff_hc:+.4f},{hi_diff_hc:+.4f}], better={better_hc})",
                flush=True,
            )

    # ---- SANITY ASSERTS (A4) ----
    print("\n  SANITY CHECKS (A4):", flush=True)
    # Check alpha=0 and alpha=1 reproduction
    for row in final_results:
        k_ob = row["k_onboarding"]
        variant = row["variant"]
        pop_mean = row["popularity"]["ndcg_mean"]
        cont_mean = row["content_only"]["ndcg_mean"]

        # Grid alpha=0
        r_alpha0 = next(
            r for r in grid_results
            if r["alpha"] == 0.0 and r["w_tags"] == best_w_tags and r["w_genome"] == best_w_genome
        )
        alpha0_val = r_alpha0["ndcgs"][str(k_ob)]["all" if variant == "all_candidates" else "lt"]
        diff_pop = abs(alpha0_val - pop_mean)
        assert diff_pop < 1e-3, f"alpha=0 sanity assertion failed for K={k_ob} {variant}: diff={diff_pop:.6f}"

        # Grid alpha=1
        r_alpha1 = next(
            r for r in grid_results
            if r["alpha"] == 1.0 and r["w_tags"] == best_w_tags and r["w_genome"] == best_w_genome
        )
        alpha1_val = r_alpha1["ndcgs"][str(k_ob)]["all" if variant == "all_candidates" else "lt"]
        diff_cont = abs(alpha1_val - cont_mean)
        assert diff_cont < 1e-3, f"alpha=1 sanity assertion failed for K={k_ob} {variant}: diff={diff_cont:.6f}"

        print(f"    K={k_ob} {variant}: alpha=0 diff_pop={diff_pop:.6f} [OK], alpha=1 diff_cont={diff_cont:.6f} [OK]", flush=True)

    # Git provenance
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(PROJECT_ROOT), text=True
        ).strip()
        git_dirty = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=str(PROJECT_ROOT), text=True
        ).strip() != ""
    except Exception:
        git_hash = "unknown"
        git_dirty = False

    runtime_s = time.time() - t0
    print(f"\nTotal tuning runtime: {runtime_s:.1f}s", flush=True)

    # Save recommender/config/hybrid_v1.yaml
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_data = {
        "version": "hybrid_v1",
        "alpha": float(best["alpha"]),
        "block_weights": {
            "w_t1": float(w_t1),
            "w_tags": float(best["w_tags"]),
            "w_genome": float(best["w_genome"]),
        },
        "normalization": "percentile",
        "tie_break_seed": 42,
        "similarity_threshold": round(sim_threshold, 4),
        "snapshot_features": True,
        "snapshot_leakage_warning": (
            "Tag TF-IDF and Genome features were aggregated over entire history (up to Nov 2019). "
            "They leak semantic signals across chronological splits. "
            "Labeled as 'Snapshot Features' per protocol."
        ),
        "tuned_on": "cold_dev",
        "tuning_protocol": "Cold-Start Protocol v2",
        "selection_objective": "mean NDCG@10 over K in {3,5,10}, variant (i) all_candidates",
        "reject_criterion": "variant (ii) long_tail NDCG >= popularity baseline for all K",
        "grid_edge_notes": edge_notes,
        "provenance": {
            "git_commit": git_hash,
            "git_dirty": git_dirty,
            "runtime_seconds": round(runtime_s, 1),
        },
    }

    import yaml
    yaml_path = CONFIG_DIR / "hybrid_v1.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
    print(f"Config saved: {yaml_path}", flush=True)

    # Save recommender/results/hybrid_v1_cold_dev.json and .csv
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    alpha_curves_serializable = {
        f"K{k}_{v}": [{"alpha": x["alpha"], "ndcg": x["ndcg"]} for x in alpha_curve_data[(k, v)]]
        for k in k_values for v in variants
    }

    results_json = {
        "metadata": {
            "config_version": "hybrid_v1",
            "chosen_config": {
                "alpha": float(best["alpha"]),
                "w_t1": float(w_t1),
                "w_tags": float(best["w_tags"]),
                "w_genome": float(best["w_genome"]),
            },
            "similarity_threshold": round(sim_threshold, 4),
            "selection_objective": "mean NDCG@10 all K on variant (i)",
            "selection_objective_value": round(best["objective"], 4),
            "grid_edge_notes": edge_notes,
            "provenance": {
                "git_commit": git_hash,
                "git_dirty": git_dirty,
                "runtime_seconds": round(runtime_s, 1),
            },
            "notes": "First K positives of MovieLens users approximate real onboarding picks.",
        },
        "top_5_configs": top5,
        "alpha_curves": alpha_curves_serializable,
        "cold_dev_evaluation": final_results,
    }

    json_path = RESULTS_DIR / "hybrid_v1_cold_dev.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results_json, f, indent=2)
    print(f"Results (JSON) saved: {json_path}", flush=True)

    csv_rows = []
    for r in final_results:
        csv_rows.append({
            "k_onboarding": r["k_onboarding"],
            "variant": r["variant"],
            "n_users": r["n_users"],
            "pop_ndcg": round(r["popularity"]["ndcg_mean"], 4),
            "pop_ci_lower": round(r["popularity"]["ci_lower"], 4),
            "pop_ci_upper": round(r["popularity"]["ci_upper"], 4),
            "content_ndcg": round(r["content_only"]["ndcg_mean"], 4),
            "content_ci_lower": round(r["content_only"]["ci_lower"], 4),
            "content_ci_upper": round(r["content_only"]["ci_upper"], 4),
            "hybrid_ndcg": round(r["hybrid"]["ndcg_mean"], 4),
            "hybrid_ci_lower": round(r["hybrid"]["ci_lower"], 4),
            "hybrid_ci_upper": round(r["hybrid"]["ci_upper"], 4),
            "hyb_vs_pop_diff": round(r["hybrid_vs_popularity"]["mean_diff"], 4),
            "hyb_vs_pop_ci_lower": round(r["hybrid_vs_popularity"]["ci_lower"], 4),
            "hyb_vs_pop_ci_upper": round(r["hybrid_vs_popularity"]["ci_upper"], 4),
            "hyb_vs_pop_better": r["hybrid_vs_popularity"]["hybrid_better"],
            "hyb_vs_content_diff": round(r["hybrid_vs_content"]["mean_diff"], 4),
            "hyb_vs_content_ci_lower": round(r["hybrid_vs_content"]["ci_lower"], 4),
            "hyb_vs_content_ci_upper": round(r["hybrid_vs_content"]["ci_upper"], 4),
            "hyb_vs_content_better": r["hybrid_vs_content"]["hybrid_better"],
        })

    csv_path = RESULTS_DIR / "hybrid_v1_cold_dev.csv"
    pd.DataFrame(csv_rows).to_csv(csv_path, index=False)
    print(f"Results (CSV) saved: {csv_path}", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("HYBRID v1 TUNING COMPLETE", flush=True)
    print(f"Chosen config: alpha={best['alpha']} w_t1={w_t1} w_tags={best['w_tags']} w_genome={best['w_genome']}", flush=True)
    print(f"Objective (mean NDCG@10 all K, variant i): {best['objective']:.4f}", flush=True)
    print(f"Similarity threshold: {sim_threshold:.4f}", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    run_grid_search()
