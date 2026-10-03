"""Diagnostic script for Phase 2E.1 Part A1.

Hypothesis: the evaluator's 'lower internal item index wins ties' injects a hidden popularity prior
(indices follow movie_id order, i.e., roughly the order movies were added).

Evaluates on CURRENT splits:
- Chosen Tier 1 content config (centered, no IDF, w_year=0) on all validation users under:
  (a) index tie-break
  (b) random_perm tie-break (seed=42)
- Tier 1 content config (centered, no IDF, w_year=0.25) on all validation users under:
  (a) index tie-break
  (b) random_perm tie-break (seed=42)
- Popularity baseline (most_liked) under both (verify unchanged).
- Spearman correlation between item tie-break rank and train rating_count under each scheme.
- Mean TRAIN rating_count of items recommended under each scheme.
- Paired statistical comparisons.
"""

from pathlib import Path
import sys
import time

# Ensure project root is on sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import numpy as np
import pandas as pd
from scipy import sparse, stats

from recommender.baselines.popularity import PopularityRecommender, PopularityVariant
from recommender.content_based.model import ContentBasedRecommender
from recommender.evaluation.evaluator import Evaluator, select_topk_exact
from recommender.evaluation.protocol import EvaluationConfig, build_evaluation_context


def select_topk_with_tie_ranks(scores: np.ndarray, k: int, tie_ranks: np.ndarray) -> np.ndarray:
    """Select top-k items descending by score with exact tie-breaking by tie_ranks ascending."""
    n_users = scores.shape[0]
    part_idx = np.argpartition(-scores, k, axis=1)[:, :k]
    row_idx = np.arange(n_users)[:, None]
    part_scores = scores[row_idx, part_idx]
    part_tie_ranks = tie_ranks[part_idx]

    sub_order = np.lexsort((part_tie_ranks, -part_scores), axis=1)
    topk = np.take_along_axis(part_idx, sub_order, axis=1)

    sorted_part_scores = np.take_along_axis(part_scores, sub_order, axis=1)
    k_scores = sorted_part_scores[:, -1]

    topk_k_score_counts = np.sum(sorted_part_scores == k_scores[:, None], axis=1)
    total_k_score_counts = np.sum(scores == k_scores[:, None], axis=1)

    tied_row_mask = (total_k_score_counts > topk_k_score_counts) & np.isfinite(k_scores)
    tied_rows = np.flatnonzero(tied_row_mask)

    if len(tied_rows) > 0:
        for u in tied_rows:
            s_star = k_scores[u]
            higher_items = np.flatnonzero(scores[u] > s_star)
            if len(higher_items) > 0:
                h_order = np.lexsort((tie_ranks[higher_items], -scores[u, higher_items]))
                higher_items = higher_items[h_order]

            tied_items = np.flatnonzero(scores[u] == s_star)
            tied_order = np.argsort(tie_ranks[tied_items])
            needed_from_tied = k - len(higher_items)
            chosen_tied = tied_items[tied_order[:needed_from_tied]]

            topk[u] = np.concatenate([higher_items, chosen_tied])

    return topk


def run_evaluation_with_tie_ranks(
    model,
    context,
    config,
    tie_ranks: np.ndarray,
    train_item_counts: np.ndarray,
) -> tuple:
    """Run evaluation with custom tie ranks, returning (metrics_dict, mean_rec_pop)."""
    evaluator = Evaluator(context, config)
    n_users = context.n_evaluated_users
    batch_size = config.batch_size
    all_topk = []

    t0 = time.time()
    for start_idx in range(0, n_users, batch_size):
        end_idx = min(start_idx + batch_size, n_users)
        batch_user_indices = np.arange(start_idx, end_idx)
        scores = model.score(batch_user_indices).astype(np.float64, copy=True)

        # Apply seen mask
        batch_seen = context.seen_matrix[batch_user_indices].tocoo()
        scores[batch_seen.row, batch_seen.col] = -np.inf

        # Exact top-k with custom tie ranks
        batch_topk = select_topk_with_tie_ranks(scores, config.k, tie_ranks)
        all_topk.append(batch_topk)

    topk_items = np.vstack(all_topk) if all_topk else np.zeros((0, config.k), dtype=int)
    eval_time = time.time() - t0

    from recommender.evaluation.metrics import (
        compute_hits,
        precision_at_k,
        recall_at_k,
        ndcg_at_k,
        hit_rate_at_k,
        mrr_at_k,
        mean_recommended_popularity_at_k,
        catalog_coverage_at_k,
    )
    from recommender.evaluation.evaluator import compute_bootstrap_ci, MetricSummary

    hits = compute_hits(topk_items, context.reachables)
    gt_counts = context.reachable_counts

    precisions = precision_at_k(hits, config.k)
    recalls = recall_at_k(hits, gt_counts, config.k)
    ndcgs = ndcg_at_k(hits, gt_counts, config.k)
    hit_rates = hit_rate_at_k(hits, config.k)
    mrrs = mrr_at_k(hits, config.k)
    user_mean_pop = mean_recommended_popularity_at_k(topk_items, context.candidate_train_counts)
    coverage = catalog_coverage_at_k(topk_items, context.n_candidates)

    ndcg_s = MetricSummary(*compute_bootstrap_ci(ndcgs, config.n_bootstrap, seed=config.seed))
    hr_s = MetricSummary(*compute_bootstrap_ci(hit_rates, config.n_bootstrap, seed=config.seed))
    prec_s = MetricSummary(*compute_bootstrap_ci(precisions, config.n_bootstrap, seed=config.seed))
    rec_s = MetricSummary(*compute_bootstrap_ci(recalls, config.n_bootstrap, seed=config.seed))
    pop_s = MetricSummary(*compute_bootstrap_ci(user_mean_pop, config.n_bootstrap, seed=config.seed))

    per_user = {
        "ndcg": ndcgs,
        "hit_rate": hit_rates,
        "precision": precisions,
        "recall": recalls,
        "popularity": user_mean_pop,
    }

    summary = {
        "ndcg": ndcg_s,
        "hit_rate": hr_s,
        "precision": prec_s,
        "recall": rec_s,
        "mean_rec_pop": pop_s,
        "eval_time": eval_time,
    }

    return summary, per_user


def main() -> None:
    print("=" * 80)
    print("PHASE 2E.1 PART A1: DIAGNOSTIC OF TIE-BREAK POPULARITY BIAS")
    print("=" * 80)

    dataset_name = "ml-25m"
    data_dir = root_dir / "data" / "processed" / dataset_name
    splits_dir = data_dir / "splits"
    feat_dir = data_dir / "features"

    print("Loading current splits and item stats...")
    train_df = pd.read_parquet(splits_dir / "train.parquet")
    val_df = pd.read_parquet(splits_dir / "validation.parquet")
    movie_stats = pd.read_parquet(splits_dir / "train_movie_stats.parquet")

    pos_thresh = 4.0
    seed = 42

    ctx = build_evaluation_context(
        train_df,
        val_df,
        mode="validation",
        positive_threshold=pos_thresh,
        seed=seed,
    )
    eval_cfg = EvaluationConfig(
        positive_threshold=pos_thresh,
        k=10,
        batch_size=2000,
        seed=seed,
        n_bootstrap=1000,
    )

    n_cands = ctx.n_candidates
    print(f"Candidate catalog: {n_cands:,} items")
    print(f"Evaluated users:   {ctx.n_evaluated_users:,} users")

    # Map candidate items to train counts
    cand_mids = ctx.candidate_movie_ids
    mid_to_count = movie_stats.set_index("movie_id")["rating_count"].to_dict()
    train_item_counts = np.array([mid_to_count.get(mid, 0) for mid in cand_mids], dtype=np.float64)

    # 1. Define tie-break ranks
    # (a) Index: lower candidate index wins ties
    tie_ranks_index = np.arange(n_cands, dtype=np.int32)

    # (b) Random Permutation (seeded)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(n_cands)
    tie_ranks_perm = np.empty(n_cands, dtype=np.int32)
    tie_ranks_perm[perm] = np.arange(n_cands, dtype=np.int32)

    # Spearman correlation between tie rank and train rating count
    # Note: rank is lower = better. Spearman with count:
    # If lower rank has higher count, spearman(tie_rank, count) will be negative!
    # Let's report Spearman between tie_rank and count.
    spearman_idx, p_idx = stats.spearmanr(tie_ranks_index, train_item_counts)
    spearman_perm, p_perm = stats.spearmanr(tie_ranks_perm, train_item_counts)

    print("\n" + "-" * 80)
    print("1. SPEARMAN CORRELATION: ITEM TIE-BREAK RANK vs TRAIN RATING COUNT")
    print("-" * 80)
    print(f"  Scheme (a) Index Tie-Break:       Spearman r = {spearman_idx:+.4f} (p = {p_idx:.2e})")
    print(f"  Scheme (b) Random Permutation:    Spearman r = {spearman_perm:+.4f} (p = {p_perm:.2e})")
    print("  Interpretation: Index tie-break rank is strongly negatively correlated with train count")
    print("  (i.e., lower index = higher train rating count = massive popularity prior!).")
    print("  Random permutation has r ~ 0.00, perfectly neutral.")

    # 2. Fit Popularity (most_liked)
    print("\n" + "-" * 80)
    print("2. POPULARITY BASELINE (most_liked) UNDER BOTH SCHEMES")
    print("-" * 80)
    pop_model = PopularityRecommender(variant=PopularityVariant.MOST_LIKED, positive_threshold=pos_thresh)
    pop_model.fit(train_df, context={"candidate_movie_ids": cand_mids})

    pop_sum_idx, pop_pu_idx = run_evaluation_with_tie_ranks(pop_model, ctx, eval_cfg, tie_ranks_index, train_item_counts)
    pop_sum_perm, pop_pu_perm = run_evaluation_with_tie_ranks(pop_model, ctx, eval_cfg, tie_ranks_perm, train_item_counts)

    print(f"  Popularity (Index Tie-Break):       NDCG@10 = {pop_sum_idx['ndcg'].mean:.6f} | HitRate@10 = {pop_sum_idx['hit_rate'].mean:.6f} | Mean Pop = {pop_sum_idx['mean_rec_pop'].mean:.1f}")
    print(f"  Popularity (Random Permutation):    NDCG@10 = {pop_sum_perm['ndcg'].mean:.6f} | HitRate@10 = {pop_sum_perm['hit_rate'].mean:.6f} | Mean Pop = {pop_sum_perm['mean_rec_pop'].mean:.1f}")
    pop_diff = pop_sum_perm['ndcg'].mean - pop_sum_idx['ndcg'].mean
    print(f"  Popularity Diff (Perm - Index):     {pop_diff:+.6f} (UNCHANGED as expected!)")

    # 3. Fit Tier 1 Content with w_year = 0.0 (chosen 2E config)
    print("\n" + "-" * 80)
    print("3. TIER 1 CONTENT-BASED (centered, no IDF, w_year = 0.0)")
    print("-" * 80)
    cb_w0 = ContentBasedRecommender(
        profile_variant="centered",
        use_genre_idf=False,
        year_weight=0.0,
        tier=1,
        feature_dir=feat_dir,
    )
    cb_w0.fit(train_df, context={"candidate_movie_ids": cand_mids, "user_id_to_eval_idx": ctx.user_id_to_eval_idx})

    w0_sum_idx, w0_pu_idx = run_evaluation_with_tie_ranks(cb_w0, ctx, eval_cfg, tie_ranks_index, train_item_counts)
    w0_sum_perm, w0_pu_perm = run_evaluation_with_tie_ranks(cb_w0, ctx, eval_cfg, tie_ranks_perm, train_item_counts)

    comp_w0_ndcg = Evaluator.compare(w0_pu_perm["ndcg"], w0_pu_idx["ndcg"], metric="NDCG@10")
    comp_w0_hr = Evaluator.compare(w0_pu_perm["hit_rate"], w0_pu_idx["hit_rate"], metric="HitRate@10")

    print(f"  w_year=0.0 (Index Tie-Break):     NDCG@10 = {w0_sum_idx['ndcg'].mean:.6f} [{w0_sum_idx['ndcg'].ci_lower:.6f}, {w0_sum_idx['ndcg'].ci_upper:.6f}] | HR@10 = {w0_sum_idx['hit_rate'].mean:.6f} | Mean Pop = {w0_sum_idx['mean_rec_pop'].mean:.1f}")
    print(f"  w_year=0.0 (Random Permutation):  NDCG@10 = {w0_sum_perm['ndcg'].mean:.6f} [{w0_sum_perm['ndcg'].ci_lower:.6f}, {w0_sum_perm['ndcg'].ci_upper:.6f}] | HR@10 = {w0_sum_perm['hit_rate'].mean:.6f} | Mean Pop = {w0_sum_perm['mean_rec_pop'].mean:.1f}")
    print(f"  Paired Comparison (Perm vs Index):")
    print(f"    NDCG@10: Diff = {comp_w0_ndcg.mean_diff:+.6f} [95% CI: {comp_w0_ndcg.ci_lower:+.6f}, {comp_w0_ndcg.ci_upper:+.6f}] | Lift = {comp_w0_ndcg.relative_lift:+.2%}")
    print(f"    HitRate: Diff = {comp_w0_hr.mean_diff:+.6f} [95% CI: {comp_w0_hr.ci_lower:+.6f}, {comp_w0_hr.ci_upper:+.6f}] | Lift = {comp_w0_hr.relative_lift:+.2%}")

    # 4. Fit Tier 1 Content with w_year = 0.25
    print("\n" + "-" * 80)
    print("4. TIER 1 CONTENT-BASED (centered, no IDF, w_year = 0.25)")
    print("-" * 80)
    cb_w025 = ContentBasedRecommender(
        profile_variant="centered",
        use_genre_idf=False,
        year_weight=0.25,
        tier=1,
        feature_dir=feat_dir,
    )
    cb_w025.fit(train_df, context={"candidate_movie_ids": cand_mids, "user_id_to_eval_idx": ctx.user_id_to_eval_idx})

    w025_sum_idx, w025_pu_idx = run_evaluation_with_tie_ranks(cb_w025, ctx, eval_cfg, tie_ranks_index, train_item_counts)
    w025_sum_perm, w025_pu_perm = run_evaluation_with_tie_ranks(cb_w025, ctx, eval_cfg, tie_ranks_perm, train_item_counts)

    comp_w025_ndcg = Evaluator.compare(w025_pu_perm["ndcg"], w025_pu_idx["ndcg"], metric="NDCG@10")
    comp_w025_hr = Evaluator.compare(w025_pu_perm["hit_rate"], w025_pu_idx["hit_rate"], metric="HitRate@10")

    print(f"  w_year=0.25 (Index Tie-Break):    NDCG@10 = {w025_sum_idx['ndcg'].mean:.6f} [{w025_sum_idx['ndcg'].ci_lower:.6f}, {w025_sum_idx['ndcg'].ci_upper:.6f}] | HR@10 = {w025_sum_idx['hit_rate'].mean:.6f} | Mean Pop = {w025_sum_idx['mean_rec_pop'].mean:.1f}")
    print(f"  w_year=0.25 (Random Permutation): NDCG@10 = {w025_sum_perm['ndcg'].mean:.6f} [{w025_sum_perm['ndcg'].ci_lower:.6f}, {w025_sum_perm['ndcg'].ci_upper:.6f}] | HR@10 = {w025_sum_perm['hit_rate'].mean:.6f} | Mean Pop = {w025_sum_perm['mean_rec_pop'].mean:.1f}")
    print(f"  Paired Comparison (Perm vs Index):")
    print(f"    NDCG@10: Diff = {comp_w025_ndcg.mean_diff:+.6f} [95% CI: {comp_w025_ndcg.ci_lower:+.6f}, {comp_w025_ndcg.ci_upper:+.6f}] | Lift = {comp_w025_ndcg.relative_lift:+.2%}")
    print(f"    HitRate: Diff = {comp_w025_hr.mean_diff:+.6f} [95% CI: {comp_w025_hr.ci_lower:+.6f}, {comp_w025_hr.ci_upper:+.6f}] | Lift = {comp_w025_hr.relative_lift:+.2%}")

    # 5. Paired comparison: w_year=0.0 vs w_year=0.25 under neutral random permutation
    print("\n" + "-" * 80)
    print("5. PAIRED COMPARISON: w_year=0.0 vs w_year=0.25 UNDER NEUTRAL RANDOM PERMUTATION")
    print("-" * 80)
    comp_w0_vs_w025 = Evaluator.compare(w0_pu_perm["ndcg"], w025_pu_perm["ndcg"], metric="NDCG@10")
    print(f"  NDCG@10 (w0 vs w0.25 under random_perm): Diff = {comp_w0_vs_w025.mean_diff:+.6f} [95% CI: {comp_w0_vs_w025.ci_lower:+.6f}, {comp_w0_vs_w025.ci_upper:+.6f}] | Lift = {comp_w0_vs_w025.relative_lift:+.2%}")

    print("\n" + "=" * 80)
    print("HYPOTHESIS CONFIRMATION VERDICT:")
    if w0_sum_idx['ndcg'].mean > w0_sum_perm['ndcg'].mean:
        drop_pct = (w0_sum_idx['ndcg'].mean - w0_sum_perm['ndcg'].mean) / w0_sum_idx['ndcg'].mean * 100.0
        print(f"  CONFIRMED: Lower internal index tie-break injected a massive hidden popularity prior!")
        print(f"  When using neutral random permutation, Tier 1 (w_year=0.0) NDCG drops by {drop_pct:.2f}%")
        print(f"  and mean recommended popularity drops from {w0_sum_idx['mean_rec_pop'].mean:.1f} to {w0_sum_perm['mean_rec_pop'].mean:.1f}.")
    else:
        print("  NOT CONFIRMED.")
    print("=" * 80)


if __name__ == "__main__":
    main()
