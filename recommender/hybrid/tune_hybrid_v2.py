"""Hybrid Recommender v2 Tuning on cold_dev (Phase 2G-Lite Part B).

Three-component hybrid blend on the simplex:
    final = w_c * pct_content + w_f * pct_cf + w_p * pct_pop
    w_c, w_f, w_p >= 0, w_c + w_f + w_p = 1.0 (step 0.1, 66 combinations).

Tuned on cold_dev ONLY across K in {3, 5, 10, 20} using the SAME objective and constraint as v1.1:
    Objective: mean(NDCG_all / NDCG_pop_all, NDCG_lt / NDCG_pop_lt)
    Constraint: NDCG_all >= NDCG_pop_all

Adoption Rule:
    Adopt v2 as served default only if:
    (a) on long-tail variants its paired difference vs v1.1 is positive with CI excluding 0
        for at least K=5 and K=10, AND
    (b) on all-candidates it is not significantly worse than v1.1 at any K.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
import scipy.sparse as sp
import scipy.stats as st
import yaml

from recommender.collaborative.item_cf import ItemItemCollaborativeRecommender
from recommender.evaluation.cold_start import (
    ColdStartEvaluator,
    compute_canonical_top200_train_mids,
    load_cold_start_split,
)
from recommender.evaluation.evaluator import (
    compute_bootstrap_ci,
    compute_hits,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    hit_rate_at_k,
    mrr_at_k,
    select_topk_exact,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SPLITS_DIR = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "splits"
FEAT_DIR = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "features"
ID_MAP_DIR = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "id_mappings"
CONFIG_DIR = PROJECT_ROOT / "recommender" / "config"
RESULTS_DIR = PROJECT_ROOT / "recommender" / "results"


def get_git_commit_hash() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def get_git_dirty_flag() -> bool:
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        return len(res.stdout.strip()) > 0
    except Exception:
        return True


def generate_simplex_grid(step: float = 0.1) -> List[Tuple[float, float, float]]:
    """Generate all non-negative triples (w_c, w_f, w_p) summing to 1.0 with given step."""
    n_steps = int(round(1.0 / step))
    combos = []
    for i in range(n_steps + 1):
        for j in range(n_steps + 1 - i):
            k = n_steps - i - j
            w_c = round(i * step, 2)
            w_f = round(j * step, 2)
            w_p = round(k * step, 2)
            combos.append((w_c, w_f, w_p))
    return combos


def compute_paired_bootstrap(
    a: np.ndarray,
    b: np.ndarray,
    n_resamples: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> Dict[str, Any]:
    """Compute paired bootstrap difference (a - b) and statistics."""
    diff = a - b
    mean_diff = float(np.mean(diff))
    rng = np.random.default_rng(seed)
    n = len(diff)
    if n == 0:
        return {"mean_diff": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "p_val": 1.0, "excludes_zero": False}
    indices = rng.integers(0, n, size=(n_resamples, n))
    boot_means = np.mean(diff[indices], axis=1)
    alpha_ci = (1.0 - ci) / 2.0
    lo = float(np.percentile(boot_means, 100.0 * alpha_ci))
    hi = float(np.percentile(boot_means, 100.0 * (1.0 - alpha_ci)))
    excludes_zero = bool(lo > 0.0 or hi < 0.0)
    p_better = float(np.mean(a > b) * 100.0)
    p_equal = float(np.mean(a == b) * 100.0)
    p_worse = float(np.mean(a < b) * 100.0)
    return {
        "mean_diff": round(mean_diff, 6),
        "ci_lower": round(lo, 6),
        "ci_upper": round(hi, 6),
        "excludes_zero": excludes_zero,
        "pct_a_better": round(p_better, 2),
        "pct_equal": round(p_equal, 2),
        "pct_b_better": round(p_worse, 2),
    }


def load_feature_blocks() -> Dict[str, Any]:
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

    return {
        "m2b": m2b,
        "t1_csr": t1_csr,
        "tag_csr": tag_csr,
        "genome_mat": genome_mat,
        "genome_mask": genome_mask,
        "feature_names_t1": feature_names_t1,
        "n_genres": n_genres,
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

    cand_t1 = t1_csr[safe_indices].toarray().astype(np.float32)
    cand_t1[~valid_mask] = 0.0

    cand_tags_csr = tag_csr[safe_indices]
    tag_norms = sp.linalg.norm(cand_tags_csr, axis=1)
    tag_norms = np.where(tag_norms > 0, tag_norms, 1.0)[:, None]
    cand_tags = (cand_tags_csr / tag_norms).astype(np.float32)
    if sp.issparse(cand_tags):
        cand_tags = cand_tags.toarray()
    cand_tags[~valid_mask] = 0.0

    cand_genome = genome_mat[safe_indices].astype(np.float32)
    cand_mask = genome_mask[safe_indices].astype(np.float32)[:, None]
    masked_genome = cand_genome * cand_mask
    gen_norms = np.linalg.norm(masked_genome, axis=1, keepdims=True)
    gen_norms = np.where(gen_norms > 0, gen_norms, 1.0)
    cand_genome_norm = masked_genome / gen_norms
    cand_genome_norm[~valid_mask] = 0.0

    concat_X = np.hstack([cand_t1 * w_t1, cand_tags * w_tags, cand_genome_norm * w_genome])
    tot_norms = np.linalg.norm(concat_X, axis=1, keepdims=True)
    tot_norms = np.where(tot_norms > 0, tot_norms, 1.0)
    return (concat_X / tot_norms).astype(np.float32)


def main():
    start_time = time.time()
    git_hash = get_git_commit_hash()
    is_dirty = get_git_dirty_flag()
    timestamp = datetime.now(timezone.utc).isoformat()

    print("=" * 80)
    print("PHASE 2G-LITE: HYBRID v2 CANDIDATE TUNING (cold_dev ONLY)")
    print(f"Timestamp: {timestamp} | Commit: {git_hash[:8]} | Dirty: {is_dirty}")
    print("=" * 80)

    # 1. Load configs & components
    v1_cfg_path = CONFIG_DIR / "hybrid_v1.yaml"
    with open(v1_cfg_path, "r", encoding="utf-8") as f:
        v1_cfg = yaml.safe_load(f)
    bw = v1_cfg.get("block_weights", {})
    w_t1 = float(bw.get("w_t1", 1.0))
    w_tags = float(bw.get("w_tags", 4.0))
    w_genome = float(bw.get("w_genome", 1.0))

    # Load CF chosen config from validation tuning
    cf_val_path = RESULTS_DIR / "cf_validation.json"
    if cf_val_path.exists():
        with open(cf_val_path, "r", encoding="utf-8") as f:
            cf_val_json = json.load(f)
        cf_chosen = cf_val_json["chosen_config"]
    else:
        cf_chosen = {"a": 0.5, "shrinkage": 0.0, "k": 200}
    print(f"CF Model Config: a={cf_chosen['a']}, lambda={cf_chosen['shrinkage']}, k={cf_chosen['k']}")

    # Load cold_dev
    cold_dev_df = load_cold_start_split("cold_dev", final=False)
    bench_movies = pd.read_parquet(PROJECT_ROOT / "data" / "processed" / "ml-25m" / "benchmark" / "movies.parquet")
    candidate_mids = np.sort(bench_movies["movie_id"].unique())
    n_candidates = len(candidate_mids)

    evaluator = ColdStartEvaluator(
        cold_df=cold_dev_df,
        candidate_movie_ids=candidate_mids,
        positive_threshold=4.0,
        k_eval=10,
        n_bootstrap=1000,
        seed=42,
    )

    # Popularity scores
    train_stats = pd.read_parquet(SPLITS_DIR / "train_movie_stats.parquet")
    stats_dict = train_stats.set_index("movie_id")["positive_rating_count"].to_dict()
    pop_scores = np.array([stats_dict.get(int(m), 0) for m in candidate_mids], dtype=np.float32)

    # Canonical top-200 train movies
    top200_mids = compute_canonical_top200_train_mids(SPLITS_DIR / "train.parquet")

    # Fit CF Model
    print("Fitting CF model on train data...")
    cf_model = ItemItemCollaborativeRecommender(
        a=cf_chosen["a"],
        shrinkage=cf_chosen["shrinkage"],
        k=cf_chosen["k"],
        positive_threshold=4.0,
    )
    cf_model.fit(None, context={"candidate_movie_ids": candidate_mids})

    # Build Content item features
    print("Building Content item features...")
    feats = load_feature_blocks()
    X = build_item_features(candidate_mids, feats, w_t1=w_t1, w_tags=w_tags, w_genome=w_genome)

    # Load Hybrid v1.1 reconciled baseline for comparison
    v1_1_path = RESULTS_DIR / "hybrid_v1_1_cold_dev_reconciled.json"
    with open(v1_1_path, "r", encoding="utf-8") as f:
        v1_1_data = json.load(f)
    v1_1_schedule = v1_1_data["metadata"]["tuned_alphas_per_k"]

    k_values = [3, 5, 10, 20]
    variants = ["all_candidates", "long_tail"]

    print("\nPrecomputing component percentile ranks per (user, K, variant)...")
    cohort_data = {}

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

            pct_p_mat = np.full((n_users, n_candidates), -np.inf, dtype=np.float32)
            pct_c_mat = np.full((n_users, n_candidates), -np.inf, dtype=np.float32)
            pct_f_mat = np.full((n_users, n_candidates), -np.inf, dtype=np.float32)
            active_indices_list = []

            # Vectorized content profiles
            profiles = np.zeros((n_users, X.shape[1]), dtype=np.float32)
            for u in range(n_users):
                rev = revealed_list[u]
                profiles[u] = np.mean(X[rev], axis=0)
            prof_norms = np.linalg.norm(profiles, axis=1, keepdims=True)
            prof_norms = np.where(prof_norms > 0, prof_norms, 1.0)
            profiles /= prof_norms
            raw_c_mat = profiles.dot(X.T).astype(np.float32)

            for u in range(n_users):
                mask_set = mask_idx_list[u]
                mask_arr = np.fromiter(mask_set, dtype=np.int32, count=len(mask_set))
                bool_mask = np.zeros(n_candidates, dtype=bool)
                bool_mask[mask_arr] = True
                act_idx = np.where(~bool_mask)[0]
                active_indices_list.append(act_idx)
                n_act = len(act_idx)
                denom = float(n_act - 1.0) if n_act > 1 else 1.0

                # 1. Popularity percentile
                p_ranks = st.rankdata(pop_scores[act_idx], method="average")
                pct_p_mat[u, act_idx] = (p_ranks - 1.0) / denom

                # 2. Content percentile
                c_ranks = st.rankdata(raw_c_mat[u, act_idx], method="average")
                pct_c_mat[u, act_idx] = (c_ranks - 1.0) / denom

                # 3. CF percentile
                # Revealed candidate indices -> movie IDs
                rev_cand = revealed_list[u]
                rev_mids = [candidate_mids[idx] for idx in rev_cand]
                raw_cf = cf_model.score_picks(rev_mids)
                # Average ranks for ties gives defined, documented percentile for zero-score items
                f_ranks = st.rankdata(raw_cf[act_idx], method="average")
                pct_f_mat[u, act_idx] = (f_ranks - 1.0) / denom

            cohort_data[(k_val, variant)] = {
                "eval_users": eval_users,
                "revealed_list": revealed_list,
                "ground_truth_list": ground_truth_list,
                "mask_idx_list": mask_idx_list,
                "n_excluded": n_excl,
                "n_users": n_users,
                "gt_counts": gt_counts,
                "active_indices_list": active_indices_list,
                "pct_p": pct_p_mat,
                "pct_c": pct_c_mat,
                "pct_f": pct_f_mat,
            }

    # Evaluate individual baselines per (K, variant)
    print("\nEvaluating individual baselines (Pop, Content-only, CF-only, Hybrid v1.1)...")
    baseline_ndcgs = {}
    baseline_results = {}

    for k_val in k_values:
        for variant in variants:
            c = cohort_data[(k_val, variant)]
            gt_counts = c["gt_counts"]
            gt_list = c["ground_truth_list"]

            # Popularity
            pop_topk = select_topk_exact(c["pct_p"], k=10, tie_ranks=evaluator.tie_ranks)
            pop_ndcg = ndcg_at_k(compute_hits(pop_topk, gt_list), gt_counts, 10)
            baseline_ndcgs[("pop", k_val, variant)] = pop_ndcg

            # Content-only (w_c=1.0)
            cnt_topk = select_topk_exact(c["pct_c"], k=10, tie_ranks=evaluator.tie_ranks)
            cnt_ndcg = ndcg_at_k(compute_hits(cnt_topk, gt_list), gt_counts, 10)
            baseline_ndcgs[("content", k_val, variant)] = cnt_ndcg

            # CF-only (w_f=1.0)
            cf_topk = select_topk_exact(c["pct_f"], k=10, tie_ranks=evaluator.tie_ranks)
            cf_ndcg = ndcg_at_k(compute_hits(cf_topk, gt_list), gt_counts, 10)
            baseline_ndcgs[("cf", k_val, variant)] = cf_ndcg

            # Hybrid v1.1 (w_c=alpha, w_p=1-alpha, w_f=0.0)
            v1_1_alpha = float(v1_1_schedule[str(k_val)])
            v1_1_blend = v1_1_alpha * c["pct_c"] + (1.0 - v1_1_alpha) * c["pct_p"]
            v1_1_topk = select_topk_exact(v1_1_blend, k=10, tie_ranks=evaluator.tie_ranks)
            v1_1_ndcg = ndcg_at_k(compute_hits(v1_1_topk, gt_list), gt_counts, 10)
            baseline_ndcgs[("v1_1", k_val, variant)] = v1_1_ndcg

    # Simplex grid tuning (66 combinations)
    print("\nSweeping 66 simplex weights (w_c, w_f, w_p) per K...")
    simplex_combos = generate_simplex_grid(step=0.1)

    tuning_results_per_k = {}
    best_weights_per_k = {}
    top3_weights_per_k = {}

    for k_val in k_values:
        pop_mean_all = float(np.mean(baseline_ndcgs[("pop", k_val, "all_candidates")]))
        pop_mean_lt = float(np.mean(baseline_ndcgs[("pop", k_val, "long_tail")]))

        c_all = cohort_data[(k_val, "all_candidates")]
        c_lt = cohort_data[(k_val, "long_tail")]

        combo_records = []
        for w_c, w_f, w_p in simplex_combos:
            # Score all candidates
            blend_all = w_c * c_all["pct_c"] + w_f * c_all["pct_f"] + w_p * c_all["pct_p"]
            topk_all = select_topk_exact(blend_all, k=10, tie_ranks=evaluator.tie_ranks)
            ndcgs_all = ndcg_at_k(compute_hits(topk_all, c_all["ground_truth_list"]), c_all["gt_counts"], 10)
            mean_ndcg_all = float(np.mean(ndcgs_all))

            # Score long tail
            blend_lt = w_c * c_lt["pct_c"] + w_f * c_lt["pct_f"] + w_p * c_lt["pct_p"]
            topk_lt = select_topk_exact(blend_lt, k=10, tie_ranks=evaluator.tie_ranks)
            ndcgs_lt = ndcg_at_k(compute_hits(topk_lt, c_lt["ground_truth_list"]), c_lt["gt_counts"], 10)
            mean_ndcg_lt = float(np.mean(ndcgs_lt))

            lift_all = mean_ndcg_all / pop_mean_all
            lift_lt = mean_ndcg_lt / pop_mean_lt
            objective = 0.5 * ((lift_all - 1.0) + (lift_lt - 1.0))
            constraint_met = bool(mean_ndcg_all >= pop_mean_all)

            combo_records.append({
                "w_c": w_c,
                "w_f": w_f,
                "w_p": w_p,
                "ndcg_all": mean_ndcg_all,
                "ndcg_lt": mean_ndcg_lt,
                "lift_all": lift_all,
                "lift_lt": lift_lt,
                "objective": objective,
                "constraint_met": constraint_met,
            })

        # Filter valid and sort
        valid_records = [r for r in combo_records if r["constraint_met"]]
        valid_records.sort(key=lambda r: r["objective"], reverse=True)
        combo_records.sort(key=lambda r: r["objective"], reverse=True)

        best_weights_per_k[k_val] = valid_records[0]
        top3_weights_per_k[k_val] = valid_records[:3]
        tuning_results_per_k[k_val] = combo_records

        b = valid_records[0]
        print(
            f"K={k_val:<2}: Best weights (w_c={b['w_c']}, w_f={b['w_f']}, w_p={b['w_p']}) | "
            f"NDCG_all={b['ndcg_all']:.4f} (Lift {b['lift_all']:+.1%}) | "
            f"NDCG_lt={b['ndcg_lt']:.4f} (Lift {b['lift_lt']:+.1%}) | Obj={b['objective']:+.4f}"
        )

    # Full Bootstrap Evaluation (1000 resamples) for Best Hybrid v2 vs Baselines
    print("\nRunning full 1000-bootstrap evaluation for final tables & paired comparisons...")
    final_table_rows = []
    paired_comparisons = {}

    for k_val in k_values:
        best_w = best_weights_per_k[k_val]
        w_c, w_f, w_p = best_w["w_c"], best_w["w_f"], best_w["w_p"]

        for variant in variants:
            c = cohort_data[(k_val, variant)]
            blend_v2 = w_c * c["pct_c"] + w_f * c["pct_f"] + w_p * c["pct_p"]
            topk_v2 = select_topk_exact(blend_v2, k=10, tie_ranks=evaluator.tie_ranks)
            hits_v2 = compute_hits(topk_v2, c["ground_truth_list"])
            ndcgs_v2 = ndcg_at_k(hits_v2, c["gt_counts"], 10)
            p_v2 = precision_at_k(hits_v2, 10)
            r_v2 = recall_at_k(hits_v2, c["gt_counts"], 10)
            hr_v2 = hit_rate_at_k(hits_v2, 10)
            mrr_v2 = mrr_at_k(hits_v2, 10)

            # CIs
            v2_mn, v2_lo, v2_hi = compute_bootstrap_ci(ndcgs_v2, n_resamples=1000, seed=42)
            pop_mn, pop_lo, pop_hi = compute_bootstrap_ci(baseline_ndcgs[("pop", k_val, variant)], n_resamples=1000, seed=42)
            cnt_mn, cnt_lo, cnt_hi = compute_bootstrap_ci(baseline_ndcgs[("content", k_val, variant)], n_resamples=1000, seed=42)
            cf_mn, cf_lo, cf_hi = compute_bootstrap_ci(baseline_ndcgs[("cf", k_val, variant)], n_resamples=1000, seed=42)
            v1_1_mn, v1_1_lo, v1_1_hi = compute_bootstrap_ci(baseline_ndcgs[("v1_1", k_val, variant)], n_resamples=1000, seed=42)

            # Paired comparisons
            v2_vs_v1_1 = compute_paired_bootstrap(ndcgs_v2, baseline_ndcgs[("v1_1", k_val, variant)], n_resamples=1000, seed=42)
            v2_vs_pop = compute_paired_bootstrap(ndcgs_v2, baseline_ndcgs[("pop", k_val, variant)], n_resamples=1000, seed=42)

            paired_comparisons[(k_val, variant)] = {
                "v2_vs_v1_1": v2_vs_v1_1,
                "v2_vs_pop": v2_vs_pop,
            }

            final_table_rows.append({
                "K": k_val,
                "variant": variant,
                "n_users": c["n_users"],
                "n_excluded": c["n_excluded"],
                "v2_weights": f"({w_c}, {w_f}, {w_p})",
                "pop_ndcg": pop_mn,
                "pop_ci": f"[{pop_lo:.4f}, {pop_hi:.4f}]",
                "content_ndcg": cnt_mn,
                "content_ci": f"[{cnt_lo:.4f}, {cnt_hi:.4f}]",
                "cf_ndcg": cf_mn,
                "cf_ci": f"[{cf_lo:.4f}, {cf_hi:.4f}]",
                "v1_1_ndcg": v1_1_mn,
                "v1_1_ci": f"[{v1_1_lo:.4f}, {v1_1_hi:.4f}]",
                "v2_ndcg": v2_mn,
                "v2_ci": f"[{v2_lo:.4f}, {v2_hi:.4f}]",
                "diff_vs_v1_1": v2_vs_v1_1["mean_diff"],
                "diff_vs_v1_1_ci": f"[{v2_vs_v1_1['ci_lower']:+.4f}, {v2_vs_v1_1['ci_upper']:+.4f}]",
                "diff_vs_pop": v2_vs_pop["mean_diff"],
                "diff_vs_pop_ci": f"[{v2_vs_pop['ci_lower']:+.4f}, {v2_vs_pop['ci_upper']:+.4f}]",
            })

    # Adoption Rule Check
    print("\n" + "=" * 80)
    print("ADOPTION RULE VERIFICATION (B3)")
    print("=" * 80)
    # Rule (a): on long-tail variants its paired difference vs v1.1 is positive with CI excluding 0 for at least K=5 and K=10
    lt_5 = paired_comparisons[(5, "long_tail")]["v2_vs_v1_1"]
    lt_10 = paired_comparisons[(10, "long_tail")]["v2_vs_v1_1"]
    rule_a_k5 = (lt_5["mean_diff"] > 0 and lt_5["ci_lower"] > 0)
    rule_a_k10 = (lt_10["mean_diff"] > 0 and lt_10["ci_lower"] > 0)
    rule_a_met = rule_a_k5 and rule_a_k10

    # Rule (b): on all-candidates it is not significantly worse than v1.1 at any K
    all_cand_worse = []
    for k_val in k_values:
        comp = paired_comparisons[(k_val, "all_candidates")]["v2_vs_v1_1"]
        # Significantly worse means mean_diff < 0 and ci_upper < 0
        if comp["mean_diff"] < 0 and comp["ci_upper"] < 0:
            all_cand_worse.append(k_val)
    rule_b_met = len(all_cand_worse) == 0

    adopted = rule_a_met and rule_b_met
    print(f"Rule (a) Long-tail paired diff vs v1.1 > 0 with CI excluding 0 for K=5 and K=10:")
    print(f"  K=5  long-tail diff: {lt_5['mean_diff']:+.6f} [95% CI: {lt_5['ci_lower']:+.6f}, {lt_5['ci_upper']:+.6f}] -> Met: {rule_a_k5}")
    print(f"  K=10 long-tail diff: {lt_10['mean_diff']:+.6f} [95% CI: {lt_10['ci_lower']:+.6f}, {lt_10['ci_upper']:+.6f}] -> Met: {rule_a_k10}")
    print(f"  Overall Rule (a) Met: {rule_a_met}")
    print(f"\nRule (b) Not significantly worse than v1.1 on all-candidates at any K:")
    for k_val in k_values:
        comp = paired_comparisons[(k_val, "all_candidates")]["v2_vs_v1_1"]
        sig_worse = (comp["mean_diff"] < 0 and comp["ci_upper"] < 0)
        print(f"  K={k_val:<2} diff vs v1.1: {comp['mean_diff']:+.6f} [95% CI: {comp['ci_lower']:+.6f}, {comp['ci_upper']:+.6f}] -> Sig Worse: {sig_worse}")
    print(f"  Overall Rule (b) Met: {rule_b_met}")
    print(f"\nFINAL ADOPTION DECISION: {'ADOPT HYBRID v2' if adopted else 'REJECT HYBRID v2 (KEEP v1.1 AS SERVED DEFAULT)'}")

    # Build bucket schedule for hybrid_v2
    # Buckets: K in [3, 4], K in [5, 7], K in [8, 14], K >= 15
    bucket_schedule = {
        "K_3_4": {"w_c": best_weights_per_k[3]["w_c"], "w_f": best_weights_per_k[3]["w_f"], "w_p": best_weights_per_k[3]["w_p"]},
        "K_5_7": {"w_c": best_weights_per_k[5]["w_c"], "w_f": best_weights_per_k[5]["w_f"], "w_p": best_weights_per_k[5]["w_p"]},
        "K_8_14": {"w_c": best_weights_per_k[10]["w_c"], "w_f": best_weights_per_k[10]["w_f"], "w_p": best_weights_per_k[10]["w_p"]},
        "K_15_plus": {"w_c": best_weights_per_k[20]["w_c"], "w_f": best_weights_per_k[20]["w_f"], "w_p": best_weights_per_k[20]["w_p"]},
    }

    # Save hybrid_v2.yaml
    v2_config = {
        "version": "hybrid_v2",
        "adopted_as_served_default": adopted,
        "bucket_schedule": bucket_schedule,
        "tuned_weights_per_k": {
            str(k): {"w_c": best_weights_per_k[k]["w_c"], "w_f": best_weights_per_k[k]["w_f"], "w_p": best_weights_per_k[k]["w_p"]}
            for k in k_values
        },
        "top3_weights_per_k": {
            str(k): [
                {"w_c": r["w_c"], "w_f": r["w_f"], "w_p": r["w_p"], "objective": round(r["objective"], 4)}
                for r in top3_weights_per_k[k]
            ]
            for k in k_values
        },
        "content_block_weights": {"w_t1": w_t1, "w_tags": w_tags, "w_genome": w_genome},
        "collaborative_config": cf_chosen,
        "normalization": "percentile",
        "zero_cf_percentile": "average_rank_of_tied_zeros",
        "selection_objective": "mean(NDCG_all/NDCG_pop_all, NDCG_lt/NDCG_pop_lt)",
        "selection_constraint": "NDCG_all >= NDCG_pop_all",
        "provenance": {
            "git_commit": git_hash,
            "git_dirty": is_dirty,
            "timestamp": timestamp,
            "runtime_seconds": round(time.time() - start_time, 2),
        },
        "tuning_note": "Tuned on cold_dev only. Confidence intervals are optimistic because weights were selected on cold_dev.",
    }
    with open(CONFIG_DIR / "hybrid_v2.yaml", "w", encoding="utf-8") as f:
        yaml.dump(v2_config, f, sort_keys=False)
    print(f"\nSaved {CONFIG_DIR / 'hybrid_v2.yaml'}")

    # Save results JSON & CSV
    results_json = {
        "metadata": v2_config,
        "final_tables": final_table_rows,
        "paired_comparisons": {
            f"K_{k}_{v}": paired_comparisons[(k, v)]
            for k in k_values for v in variants
        },
        "tuning_curves": {
            str(k): tuning_results_per_k[k]
            for k in k_values
        },
    }
    with open(RESULTS_DIR / "hybrid_v2_cold_dev.json", "w", encoding="utf-8") as f:
        json.dump(results_json, f, indent=2)
    print(f"Saved {RESULTS_DIR / 'hybrid_v2_cold_dev.json'}")

    df_csv = pd.DataFrame(final_table_rows)
    df_csv.to_csv(RESULTS_DIR / "hybrid_v2_cold_dev.csv", index=False)
    print(f"Saved {RESULTS_DIR / 'hybrid_v2_cold_dev.csv'}")


if __name__ == "__main__":
    main()
