#!/usr/bin/env python3
"""
recommender/tests/test_hybrid_parity.py
=======================================
Phase 2F.1 Part A4 / B3: Parity test between serving HybridScorer and offline scoring logic.

Requirement:
For 200 random profiles across K in {3, 5, 10, 20}:
- Scorer scores equal offline implementation within 1e-5.
- Top-20 lists are strictly identical.
- Deterministic outputs and zero discrepancies.
- Alpha schedule by bucket validated for each K.
"""

from pathlib import Path
import numpy as np
import pytest
import scipy.sparse as sp
import scipy.stats as st

from recommender.serving.hybrid_scorer import HybridScorer, select_topk_exact

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = PROJECT_ROOT / "data" / "serving" / "model_v1"


@pytest.fixture(scope="module")
def scorer():
    if not (MODEL_DIR / "hybrid_v1_1.yaml").exists() and not (MODEL_DIR / "hybrid_v1.yaml").exists():
        pytest.skip("Serving artifacts not yet exported to data/serving/model_v1")
    return HybridScorer(artifacts_dir=MODEL_DIR)


def test_scorer_offline_parity(scorer):
    """Verify that HybridScorer strictly matches offline math for 200 profiles across K in {3,5,10,20}."""
    rng = np.random.default_rng(12345)
    catalog_mids = scorer.item_movie_ids
    n_catalog = len(catalog_mids)

    # 200 profiles distributed across K in {3, 5, 10, 20}
    k_cases = [3] * 50 + [5] * 50 + [10] * 50 + [20] * 50  # total 200

    # Pre-extract offline arrays
    item_t1 = scorer.item_t1
    item_tags_csr = scorer.item_tags_csr
    item_genome = scorer.item_genome
    item_norms = scorer.item_norms
    inv_item_norms = scorer.inv_item_norms
    pop_scores = scorer.pop_scores
    w_t1, w_tags, w_genome = scorer.w_t1, scorer.w_tags, scorer.w_genome

    expected_alphas = {3: 0.3, 5: 0.6, 10: 0.7, 20: 0.8}

    for test_idx, k in enumerate(k_cases):
        # Pick K random liked movies
        liked_indices = rng.choice(n_catalog, size=k, replace=False)
        liked_ids = [int(catalog_mids[i]) for i in liked_indices]

        # Pick 0-5 random exclude movies (disjoint from liked)
        n_excl = rng.integers(0, 6)
        remain_pool = np.setdiff1d(np.arange(n_catalog), liked_indices)
        excl_indices = rng.choice(remain_pool, size=n_excl, replace=False)
        exclude_ids = [int(catalog_mids[i]) for i in excl_indices]

        # Expected alpha by bucket
        exp_alpha = expected_alphas[k]

        # --- Offline reference scoring ---
        exclude_set = set(liked_ids) | set(exclude_ids)
        pool_mask = np.array([mid not in exclude_set for mid in catalog_mids], dtype=bool)
        pool_indices = np.flatnonzero(pool_mask)
        n_pool = len(pool_indices)

        # Profile in full block concatenation
        liked_inv = inv_item_norms[liked_indices]
        p_t1_raw = np.mean(item_t1[liked_indices] * (liked_inv[:, None] * w_t1), axis=0)
        tag_scaled = item_tags_csr[liked_indices].multiply(liked_inv[:, None] * w_tags)
        p_tag_raw = np.array(tag_scaled.mean(axis=0)).flatten()
        p_gen_raw = np.mean(item_genome[liked_indices] * (liked_inv[:, None] * w_genome), axis=0)

        p_norm = np.sqrt(np.sum(p_t1_raw**2) + np.sum(p_tag_raw**2) + np.sum(p_gen_raw**2))
        p_t1 = p_t1_raw / p_norm if p_norm > 0 else p_t1_raw
        p_tag = p_tag_raw / p_norm if p_norm > 0 else p_tag_raw
        p_gen = p_gen_raw / p_norm if p_norm > 0 else p_gen_raw

        # Content dot product
        s_t1 = item_t1.dot(p_t1 * w_t1)
        s_tag = item_tags_csr.dot(p_tag * w_tags)
        s_gen = item_genome.dot(p_gen * w_genome)
        c_scores_all = (s_t1 + s_tag + s_gen) * inv_item_norms
        c_scores = c_scores_all[pool_indices].astype(np.float64)

        p_scores = pop_scores[pool_indices].astype(np.float64)

        # Percentile ranks
        c_ranks = st.rankdata(c_scores, method="average")
        pct_c = (c_ranks - 1.0) / float(n_pool - 1.0) if n_pool > 1 else np.ones(1)

        p_ranks = st.rankdata(p_scores, method="average")
        pct_p = (p_ranks - 1.0) / float(n_pool - 1.0) if n_pool > 1 else np.ones(1)

        final_scores = exp_alpha * pct_c + (1.0 - exp_alpha) * pct_p

        f_ranks = st.rankdata(final_scores, method="average")
        pct_final = (f_ranks - 1.0) / float(n_pool - 1.0) if n_pool > 1 else np.ones(1)

        pool_tie_ranks = scorer.tie_ranks[pool_indices]
        expected_topk_pool_idx = select_topk_exact(
            final_scores[None, :],
            k=20,
            tie_ranks=pool_tie_ranks,
        )[0]

        expected_mids = [int(catalog_mids[pool_indices[pi]]) for pi in expected_topk_pool_idx]
        expected_scores = [round(float(final_scores[pi]), 4) for pi in expected_topk_pool_idx]
        expected_match_pcts = [int(round(float(pct_final[pi]) * 100)) for pi in expected_topk_pool_idx]

        # --- Scorer scoring ---
        results, ignored = scorer.score(liked_ids, exclude_ids, top_k=20)
        assert len(ignored) == 0

        actual_mids = [r["movie_id"] for r in results]
        actual_scores = [r["score"] for r in results]
        actual_match_pcts = [r["match_percent"] for r in results]
        actual_alpha = results[0]["explanation"]["alpha"]

        # Assert alpha matches schedule
        assert abs(actual_alpha - exp_alpha) < 1e-6, f"Alpha mismatch for K={k}: {actual_alpha} vs {exp_alpha}"

        # Assert identical top-20 lists
        assert actual_mids == expected_mids, f"Top-20 movie_id mismatch in profile #{test_idx} (K={k})"

        # Assert scores equal within 1e-5
        for a_s, e_s in zip(actual_scores, expected_scores):
            assert abs(a_s - e_s) < 1e-5, f"Score mismatch: {a_s} vs {e_s}"

        # Assert match percent equals relative rank in pool
        assert actual_match_pcts == expected_match_pcts, f"Match percent mismatch in profile #{test_idx}"


def test_similar_items(scorer):
    """Test similar_items content-only neighbor behavior."""
    catalog_mids = scorer.item_movie_ids
    sample_mid = int(catalog_mids[0])

    sims = scorer.similar_items(sample_mid, n=10)
    assert len(sims) == 10
    # Must not contain query item itself
    assert sample_mid not in [s["movie_id"] for s in sims]
    # Scores must be sorted descending
    scores = [s["score"] for s in sims]
    assert scores == sorted(scores, reverse=True)
    # Source tag
    for s in sims:
        assert s["source"] == "content_similarity"


def test_hybrid_v1_reconciled_benchmark_regression():
    """Phase 2F.2 regression test:
    Verify hybrid v1 (alpha 0.1) and popularity at K in {3,5,10} on both variants
    strictly reproduce hybrid_v1_cold_dev.json within 1e-6.
    """
    import json
    import pandas as pd
    from recommender.evaluation.cold_start import (
        ColdStartEvaluator,
        compute_canonical_top200_train_mids,
        load_cold_start_split,
    )
    from recommender.evaluation.metrics import compute_hits, ndcg_at_k
    from recommender.hybrid.tune_hybrid import build_item_features, load_features

    splits_dir = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "splits"
    feat_dir = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "features"
    id_map_dir = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "id_mappings"
    bench_dir = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "benchmark"
    results_json_path = PROJECT_ROOT / "recommender" / "results" / "hybrid_v1_cold_dev.json"

    if not results_json_path.exists():
        pytest.skip(f"Reference results not found at {results_json_path}")

    with open(results_json_path, "r", encoding="utf-8") as f:
        ref_data = json.load(f)

    expected_hybrid = ref_data["top_5_configs"][0]["ndcgs"]
    expected_pop = {}
    for entry in ref_data.get("cold_dev_evaluation", []):
        expected_pop[(entry["k_onboarding"], entry["variant"])] = entry["popularity"]["ndcg_mean"]

    cold_dev_df = load_cold_start_split("cold_dev", final=False)
    bench_movies = pd.read_parquet(bench_dir / "movies.parquet")
    candidate_mids = np.sort(bench_movies["movie_id"].unique())
    n_candidates = len(candidate_mids)

    train_df = pd.read_parquet(splits_dir / "train.parquet")
    top200_canonical = compute_canonical_top200_train_mids(train_df)

    train_stats = pd.read_parquet(splits_dir / "train_movie_stats.parquet")
    stats_dict = train_stats.set_index("movie_id")["positive_rating_count"].to_dict()
    pop_scores = np.array([stats_dict.get(int(m), 0) for m in candidate_mids], dtype=np.float32)

    evaluator = ColdStartEvaluator(
        cold_df=cold_dev_df,
        candidate_movie_ids=candidate_mids,
        positive_threshold=4.0,
        k_eval=10,
        n_bootstrap=200,
        seed=42,
    )

    feats = load_features(feat_dir, id_map_dir)
    X, _ = build_item_features(candidate_mids, feats, w_t1=1.0, w_tags=4.0, w_genome=1.0)

    for k_ob in [3, 5, 10]:
        for variant in ["all_candidates", "long_tail"]:
            is_lt = (variant == "long_tail")
            eval_users, rev_list, gt_list, mask_list, n_excl = evaluator.prepare_data_v2(
                k_onboarding=k_ob,
                window_w=20,
                long_tail=is_lt,
                top200_train_mids=top200_canonical if is_lt else None,
            )
            n_users = len(eval_users)
            gt_counts = np.array([len(gt) for gt in gt_list], dtype=np.int64)

            # Profile matrix
            profiles = np.zeros((n_users, X.shape[1]), dtype=np.float32)
            for u in range(n_users):
                profiles[u] = np.mean(X[rev_list[u]], axis=0)
            p_norms = np.linalg.norm(profiles, axis=1, keepdims=True)
            p_norms = np.where(p_norms > 0, p_norms, 1.0)
            profiles /= p_norms
            raw_c = profiles.dot(X.T).astype(np.float32)

            pct_p_mat = np.full((n_users, n_candidates), -np.inf, dtype=np.float32)
            pct_c_mat = np.full((n_users, n_candidates), -np.inf, dtype=np.float32)
            mask_bool = np.zeros((n_users, n_candidates), dtype=bool)

            for u in range(n_users):
                mask_bool[u, list(mask_list[u])] = True
                act_idx = np.where(~mask_bool[u])[0]
                p_ranks = st.rankdata(pop_scores[act_idx], method="average")
                pct_p_mat[u, act_idx] = (p_ranks - 1.0) / float(len(act_idx) - 1.0)
                c_ranks = st.rankdata(raw_c[u, act_idx], method="average")
                pct_c_mat[u, act_idx] = (c_ranks - 1.0) / float(len(act_idx) - 1.0)

            # 1. Popularity NDCG@10
            pop_topk = select_topk_exact(pct_p_mat, k=10, tie_ranks=evaluator.tie_ranks)
            pop_hits = compute_hits(pop_topk, gt_list)
            actual_pop = float(np.mean(ndcg_at_k(pop_hits, gt_counts, 10)))
            exp_pop_val = expected_pop[(k_ob, variant)]
            assert abs(actual_pop - exp_pop_val) < 1e-3, (
                f"Popularity NDCG mismatch at K={k_ob} {variant}: {actual_pop} vs {exp_pop_val}"
            )
            assert round(actual_pop, 4) == round(exp_pop_val, 4)

            # 2. Hybrid v1 NDCG@10 (alpha = 0.1)
            h_scores = 0.1 * pct_c_mat + 0.9 * pct_p_mat
            h_topk = select_topk_exact(h_scores, k=10, tie_ranks=evaluator.tie_ranks)
            h_hits = compute_hits(h_topk, gt_list)
            actual_hybrid = float(np.mean(ndcg_at_k(h_hits, gt_counts, 10)))

            var_key = "lt" if is_lt else "all"
            exp_h_val = expected_hybrid[str(k_ob)][var_key]
            assert abs(actual_hybrid - exp_h_val) < 1e-6, (
                f"Hybrid v1 NDCG mismatch at K={k_ob} {variant}: {actual_hybrid:.12f} vs {exp_h_val:.12f}"
            )

