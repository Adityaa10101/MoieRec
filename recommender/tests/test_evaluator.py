"""Evaluator self-validation suite (Part C).

Validates the evaluator engine BEFORE running any baseline models:
- C1: Hand-computed tiny cases with known exact values for precision/recall/ndcg/hit_rate/mrr
- C2: ORACLE recommender on real validation split (ndcg=1.0, hr=1.0, mrr=1.0, recall=mean(min(R,k)/R), prec=mean(min(R,k)/k))
- C3: RANDOM recommender compared to analytic hypergeometric expectations within 4 SE + seed determinism
- C4: SEEN-ITEM MASKING on synthetic fixture (train masked in both modes, train+val masked in test mode, train-bias recommender gets 0)
- C5: Tie-breaking determinism on constant-score recommender
- C6: Batch-size invariance (500 vs 5000 on a sample)
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from scipy.stats import hypergeom

from recommender.evaluation.evaluator import Evaluator
from recommender.evaluation.metrics import (
    compute_hits,
    hit_rate_at_k,
    mrr_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from recommender.evaluation.protocol import (
    EvaluationConfig,
    Recommender,
    build_evaluation_context,
)


# ==============================================================================
# C1. Hand-computed tiny cases with known exact values
# ==============================================================================

def test_c1_hand_computed_tiny_cases():
    """Verify ranking metrics against exact hand-computed values across diverse edge cases."""
    # Case 1: k=4, |R|=2, hit at rank 1 only
    # Recommended: [item 0, item 1, item 2, item 3], Relevant: {0, 9}
    # Hits: [True, False, False, False]
    hits_c1 = np.array([[True, False, False, False]])
    reachables_c1 = np.array([2])
    k = 4

    p = precision_at_k(hits_c1, k)[0]
    r = recall_at_k(hits_c1, reachables_c1, k)[0]
    hr = hit_rate_at_k(hits_c1, k)[0]
    mrr = mrr_at_k(hits_c1, k)[0]
    ndcg = ndcg_at_k(hits_c1, reachables_c1, k)[0]

    assert np.isclose(p, 1.0 / 4.0), f"P@4 expected 0.25, got {p}"
    assert np.isclose(r, 1.0 / 2.0), f"R@4 expected 0.5, got {r}"
    assert np.isclose(hr, 1.0), f"HR@4 expected 1.0, got {hr}"
    assert np.isclose(mrr, 1.0), f"MRR@4 expected 1.0, got {mrr}"

    # DCG: 1 / log2(2) = 1.0
    # IDCG: min(2, 4)=2 items -> 1/log2(2) + 1/log2(3) = 1.0 + 1.0 / 1.584962500721156 = 1.6309297535714573
    expected_ndcg_c1 = 1.0 / (1.0 + 1.0 / np.log2(3.0))
    assert np.isclose(ndcg, expected_ndcg_c1, atol=1e-6), f"NDCG@4 expected {expected_ndcg_c1}, got {ndcg}"

    # Case 2: k=4, |R|=3, no hits at all
    hits_c2 = np.array([[False, False, False, False]])
    reachables_c2 = np.array([3])

    assert np.isclose(precision_at_k(hits_c2, k)[0], 0.0)
    assert np.isclose(recall_at_k(hits_c2, reachables_c2, k)[0], 0.0)
    assert np.isclose(hit_rate_at_k(hits_c2, k)[0], 0.0)
    assert np.isclose(mrr_at_k(hits_c2, k)[0], 0.0)
    assert np.isclose(ndcg_at_k(hits_c2, reachables_c2, k)[0], 0.0)

    # Case 3: k=4, |R|=1, hit at rank k (rank 4)
    hits_c3 = np.array([[False, False, False, True]])
    reachables_c3 = np.array([1])

    assert np.isclose(precision_at_k(hits_c3, k)[0], 1.0 / 4.0)
    assert np.isclose(recall_at_k(hits_c3, reachables_c3, k)[0], 1.0)
    assert np.isclose(hit_rate_at_k(hits_c3, k)[0], 1.0)
    assert np.isclose(mrr_at_k(hits_c3, k)[0], 1.0 / 4.0)

    # DCG: 1 / log2(5) = 1.0 / 2.321928094887362
    # IDCG: min(1, 4)=1 item -> 1 / log2(2) = 1.0
    expected_ndcg_c3 = (1.0 / np.log2(5.0)) / 1.0
    assert np.isclose(ndcg_at_k(hits_c3, reachables_c3, k)[0], expected_ndcg_c3, atol=1e-6)

    # Case 4: k=4, |R|=5 (more relevant items than k), hits at rank 1 and rank 3
    hits_c4 = np.array([[True, False, True, False]])
    reachables_c4 = np.array([5])

    assert np.isclose(precision_at_k(hits_c4, k)[0], 2.0 / 4.0)
    assert np.isclose(recall_at_k(hits_c4, reachables_c4, k)[0], 2.0 / 5.0)
    assert np.isclose(hit_rate_at_k(hits_c4, k)[0], 1.0)
    assert np.isclose(mrr_at_k(hits_c4, k)[0], 1.0)

    # DCG: 1/log2(2) + 1/log2(4) = 1.0 + 0.5 = 1.5
    # IDCG: min(5, 4)=4 items -> 1/log2(2) + 1/log2(3) + 1/log2(4) + 1/log2(5)
    idcg_c4 = 1.0 / np.log2(2.0) + 1.0 / np.log2(3.0) + 1.0 / np.log2(4.0) + 1.0 / np.log2(5.0)
    expected_ndcg_c4 = 1.5 / idcg_c4
    assert np.isclose(ndcg_at_k(hits_c4, reachables_c4, k)[0], expected_ndcg_c4, atol=1e-6)


# ==============================================================================
# Helper to load dataset splits
# ==============================================================================

def load_dataset_splits(dataset_name: str = "ml-latest-small"):
    root = Path(__file__).resolve().parent.parent.parent
    splits_dir = root / "data" / "processed" / dataset_name / "splits"
    if not splits_dir.exists():
        pytest.skip(f"Processed splits not found for {dataset_name}. Run preprocessing first.")
    train = pd.read_parquet(splits_dir / "train.parquet")
    val = pd.read_parquet(splits_dir / "validation.parquet")
    return train, val


# ==============================================================================
# C2. ORACLE recommender on real validation split
# ==============================================================================

class OracleRecommender(Recommender):
    """Assigns large score to reachable positives for each user, 0 to others."""

    def __init__(self, reachables, n_candidates: int):
        self.reachables = reachables
        self.n_candidates = n_candidates

    def fit(self, train_df: pd.DataFrame, context=None) -> "OracleRecommender":
        return self

    def score(self, user_indices: np.ndarray) -> np.ndarray:
        scores = np.zeros((len(user_indices), self.n_candidates), dtype=np.float32)
        for i, u_idx in enumerate(user_indices):
            rel = list(self.reachables[u_idx])
            if rel:
                scores[i, rel] = 1000.0
        return scores


@pytest.mark.parametrize("dataset_name", ["ml-latest-small", "ml-25m"])
def test_c2_oracle_recommender(dataset_name: str):
    """Assert exact theoretical values for Oracle recommender on validation split."""
    train, val = load_dataset_splits(dataset_name)
    sample_users = 2000 if dataset_name == "ml-25m" else None
    ctx = build_evaluation_context(train, val, mode="validation", sample_users=sample_users, seed=42)
    k = 10
    cfg = EvaluationConfig(k=k, batch_size=2000)

    model = OracleRecommender(ctx.reachables, ctx.n_candidates)
    evaluator = Evaluator(ctx, cfg)
    res = evaluator.evaluate(model)



    R = ctx.reachable_counts
    expected_recall = float(np.mean(np.minimum(R, k) / R))
    expected_precision = float(np.mean(np.minimum(R, k) / k))

    assert np.isclose(res.ndcg.mean, 1.0, atol=1e-5), f"Oracle NDCG expected 1.0, got {res.ndcg.mean}"
    assert np.isclose(res.hit_rate.mean, 1.0, atol=1e-5), f"Oracle HitRate expected 1.0, got {res.hit_rate.mean}"
    assert np.isclose(res.mrr.mean, 1.0, atol=1e-5), f"Oracle MRR expected 1.0, got {res.mrr.mean}"
    assert np.isclose(res.recall.mean, expected_recall, atol=1e-5), f"Oracle Recall mismatch: {res.recall.mean} vs {expected_recall}"
    assert np.isclose(res.precision.mean, expected_precision, atol=1e-5), f"Oracle Precision mismatch: {res.precision.mean} vs {expected_precision}"


# ==============================================================================
# C3. RANDOM recommender: comparison to analytic expectations within 4 SE
# ==============================================================================

class RandomRecommender(Recommender):
    """Generates seeded random scores."""

    def __init__(self, seed: int = 42, n_candidates: int = 0):
        self.seed = seed
        self.n_candidates = n_candidates
        self.rng = np.random.default_rng(seed)

    def fit(self, train_df: pd.DataFrame, context=None) -> "RandomRecommender":
        if context and "n_candidates" in context:
            self.n_candidates = context["n_candidates"]
        return self

    def score(self, user_indices: np.ndarray) -> np.ndarray:
        return self.rng.random((len(user_indices), self.n_candidates), dtype=np.float32)


@pytest.mark.parametrize("dataset_name", ["ml-latest-small", "ml-25m"])
def test_c3_random_recommender(dataset_name: str):
    """Verify measured Random recommender metrics against hypergeometric analytic expectations."""
    train, val = load_dataset_splits(dataset_name)
    sample_users = 3000 if dataset_name == "ml-25m" else None
    ctx = build_evaluation_context(train, val, mode="validation", sample_users=sample_users, seed=42)
    k = 10
    cfg = EvaluationConfig(k=k, seed=42)


    evaluator = Evaluator(ctx, cfg)

    # Run 1
    model1 = RandomRecommender(seed=42, n_candidates=ctx.n_candidates)
    res1 = evaluator.evaluate(model1, store_per_user_metrics=True)

    # Repeat run with identical seed: verify exact determinism
    model2 = RandomRecommender(seed=42, n_candidates=ctx.n_candidates)
    res2 = evaluator.evaluate(model2, store_per_user_metrics=True)

    for metric_name in ["precision", "recall", "hit_rate", "ndcg", "mrr"]:
        np.testing.assert_array_equal(
            res1.per_user_metrics[metric_name],
            res2.per_user_metrics[metric_name],
            err_msg=f"Random recommender repeat run was not deterministic on {metric_name}!",
        )

    # Analytic expectations per user
    # Number of unseen candidates C_u = n_candidates - seen_count_u
    seen_counts = np.diff(ctx.seen_matrix.indptr)
    C = ctx.n_candidates - seen_counts
    R = ctx.reachable_counts
    k_prime = np.minimum(k, C)

    expected_hits = k_prime * (R / C)
    expected_prec = expected_hits / float(k)
    expected_rec = expected_hits / R
    # Numerically stable hit-rate via hypergeometric survival / PMF
    expected_hr = 1.0 - hypergeom.pmf(0, C, R, k_prime)

    metrics_to_test = [
        ("Precision@10", res1.per_user_metrics["precision"], expected_prec),
        ("Recall@10", res1.per_user_metrics["recall"], expected_rec),
        ("HitRate@10", res1.per_user_metrics["hit_rate"], expected_hr),
    ]

    for name, measured, expected in metrics_to_test:
        meas_mean = float(np.mean(measured))
        exp_mean = float(np.mean(expected))
        diff = abs(meas_mean - exp_mean)
        se = float(np.std(measured, ddof=1) / np.sqrt(len(measured)))
        tol = 4.0 * se

        assert diff <= tol, (
            f"Random recommender {name} mismatch beyond 4 SE! "
            f"Measured={meas_mean:.6f}, Expected={exp_mean:.6f}, Diff={diff:.6f}, 4*SE={tol:.6f}"
        )


# ==============================================================================
# C4. SEEN-ITEM MASKING on synthetic fixture
# ==============================================================================

def test_c4_seen_item_masking():
    """Verify seen-item masking across validation and test modes on a synthetic fixture."""
    # Synthetic fixture with 8 candidate movies: 10, 20, 30, 40, 50, 60, 70, 80
    train_df = pd.DataFrame({
        "user_id": [1, 2, 3, 4, 4, 4, 4, 4, 4],
        "movie_id": [10, 10, 20, 20, 30, 40, 50, 60, 70],
        "rating": [4.0, 5.0, 3.5, 4.0, 4.0, 4.5, 4.0, 4.0, 4.0],
        "timestamp": list(range(9)),
    })

    # Validation interactions: user 1, 2, 3 have positive on movie 70
    val_df = pd.DataFrame({
        "user_id": [1, 2, 3],
        "movie_id": [70, 70, 70],
        "rating": [4.5, 4.0, 4.5],
        "timestamp": [20, 21, 22],
    })

    # Synthetic "test" interactions (never real test file!)
    synth_test_df = pd.DataFrame({
        "user_id": [1, 2, 3],
        "movie_id": [70, 70, 70],
        "rating": [5.0, 4.0, 4.0],
        "timestamp": [30, 31, 32],
    })

    # Combined train + val for test-mode seen masking
    train_plus_val = pd.concat([train_df, val_df], ignore_index=True)

    # 1. Validation mode context
    ctx_val = build_evaluation_context(train_df, val_df, mode="validation", positive_threshold=4.0)

    # Verify items seen in TRAIN are marked 1 in seen_matrix for validation mode
    user1_idx = ctx_val.user_id_to_eval_idx[1]
    movie10_idx = ctx_val.movie_id_to_cand_idx[10]
    movie70_idx = ctx_val.movie_id_to_cand_idx[70]
    assert ctx_val.seen_matrix[user1_idx, movie10_idx] == 1.0
    assert ctx_val.seen_matrix[user1_idx, movie70_idx] == 0.0

    # 2. Test mode context requires final=True and frozen_config_id
    with pytest.raises(PermissionError):
        build_evaluation_context(
            train_df, synth_test_df, mode="test", final=False, frozen_config_id="unit-test-1"
        )

    with pytest.raises(PermissionError):
        build_evaluation_context(
            train_df, synth_test_df, mode="test", final=True, frozen_config_id=""
        )

    ctx_test = build_evaluation_context(
        train_df,
        synth_test_df,
        mode="test",
        final=True,
        frozen_config_id="unit-test-frozen-1",
        train_plus_val_df_for_test=train_plus_val,
    )

    # In test mode, items seen in TRAIN + VALIDATION must be masked
    user1_idx_t = ctx_test.user_id_to_eval_idx[1]
    assert ctx_test.seen_matrix[user1_idx_t, movie10_idx] == 1.0  # from train
    assert ctx_test.seen_matrix[user1_idx_t, movie70_idx] == 1.0  # from validation (masked in test)

    # 3. Train-bias Recommender: gives highest score ONLY to user's train items
    class TrainBiasRecommender(Recommender):
        def fit(self, train_df, context=None):
            return self

        def score(self, user_indices):
            scores = np.full((len(user_indices), ctx_val.n_candidates), 0.0, dtype=np.float32)
            for i, u_idx in enumerate(user_indices):
                seen_items = ctx_val.seen_matrix[u_idx].indices
                scores[i, seen_items] = 100.0
            return scores

    evaluator = Evaluator(ctx_val, EvaluationConfig(k=2))
    res = evaluator.evaluate(TrainBiasRecommender())
    # Because train items are masked to -inf, they can never be recommended.
    # The remaining items (which are not relevant) fill the top-k, yielding 0 hits.
    assert res.precision.mean == 0.0
    assert res.recall.mean == 0.0
    assert res.hit_rate.mean == 0.0
    assert res.mrr.mean == 0.0
    assert res.ndcg.mean == 0.0



# ==============================================================================
# C5. Tie-breaking determinism on constant-score recommender
# ==============================================================================

class ConstantScoreRecommender(Recommender):
    """Returns identical score 1.0 for all candidate items."""

    def __init__(self, n_candidates: int):
        self.n_candidates = n_candidates

    def fit(self, train_df, context=None):
        return self

    def score(self, user_indices):
        return np.ones((len(user_indices), self.n_candidates), dtype=np.float32)


@pytest.mark.parametrize("dataset_name", ["ml-latest-small", "ml-25m"])
def test_c5_tie_breaking_determinism(dataset_name: str):
    """Verify that constant score recommender produces bitwise identical rankings across independent runs."""
    train, val = load_dataset_splits(dataset_name)
    sample_users = 2000 if dataset_name == "ml-25m" else None
    ctx = build_evaluation_context(train, val, mode="validation", sample_users=sample_users, seed=42)
    cfg = EvaluationConfig(k=10)
    evaluator = Evaluator(ctx, cfg)

    model1 = ConstantScoreRecommender(ctx.n_candidates)
    res1 = evaluator.evaluate(model1, store_topk=True)

    model2 = ConstantScoreRecommender(ctx.n_candidates)
    res2 = evaluator.evaluate(model2, store_topk=True)

    np.testing.assert_array_equal(res1.predicted_topk, res2.predicted_topk)
    assert res1.ndcg.mean == res2.ndcg.mean
    assert res1.catalog_coverage == res2.catalog_coverage


# ==============================================================================
# C6. Batch-size invariance
# ==============================================================================

@pytest.mark.parametrize("dataset_name", ["ml-latest-small", "ml-25m"])
def test_c6_batch_size_invariance(dataset_name: str):
    """Verify that evaluation results are strictly identical across batch_size=500 vs 5000."""
    train, val = load_dataset_splits(dataset_name)
    ctx = build_evaluation_context(train, val, mode="validation", sample_users=1000, seed=42)

    model = ConstantScoreRecommender(ctx.n_candidates)

    evaluator_b500 = Evaluator(ctx, EvaluationConfig(k=10, batch_size=500, seed=42))
    res_b500 = evaluator_b500.evaluate(model, store_topk=True)

    evaluator_b5000 = Evaluator(ctx, EvaluationConfig(k=10, batch_size=5000, seed=42))
    res_b5000 = evaluator_b5000.evaluate(model, store_topk=True)

    np.testing.assert_array_equal(res_b500.predicted_topk, res_b5000.predicted_topk)
    assert np.isclose(res_b500.precision.mean, res_b5000.precision.mean)
    assert np.isclose(res_b500.recall.mean, res_b5000.recall.mean)
    assert np.isclose(res_b500.ndcg.mean, res_b5000.ndcg.mean)
    assert np.isclose(res_b500.hit_rate.mean, res_b5000.hit_rate.mean)
    assert np.isclose(res_b500.mrr.mean, res_b5000.mrr.mean)


# ==============================================================================
# A6. Exact Tie-Breaking & Precision Property Tests
# ==============================================================================

def test_a6_tie_breaking_lower_index_ranks_first():
    """Verify that among tied scores the LOWER internal item index always ranks first,
    including across the top-k boundary."""
    from recommender.evaluation.evaluator import select_topk_exact

    # 1. Constant scores across all 50 items for 3 users: top-5 must be [0, 1, 2, 3, 4]
    scores_all_tied = np.full((3, 50), 42.0, dtype=np.float32)
    topk_const = select_topk_exact(scores_all_tied, k=5)
    for u in range(3):
        assert np.array_equal(topk_const[u], np.arange(5)), f"Expected [0..4], got {topk_const[u]}"

    # 2. Boundary tie: 3 items with score 10.0 at indices [35, 12, 4],
    # and all remaining 47 items tied with score 5.0.
    # With k=7, top-7 must be [4, 12, 35] followed by the first 4 lowest available indices [0, 1, 2, 3]!
    scores_boundary = np.full((1, 50), 5.0, dtype=np.float32)
    scores_boundary[0, [35, 12, 4]] = 10.0
    topk_b = select_topk_exact(scores_boundary, k=7)
    expected_top7 = np.array([4, 12, 35, 0, 1, 2, 3])
    assert np.array_equal(topk_b[0], expected_top7), f"Expected {expected_top7}, got {topk_b[0]}"


def test_a6_float32_distinct_scores_not_reordered_and_high_magnitude():
    """Verify that exact tie-breaking cannot reorder float32-distinct scores and is immune
    to float64 rounding at popularity magnitudes (counts up to ~50,000)."""
    from recommender.evaluation.evaluator import select_topk_exact

    rng = np.random.default_rng(12345)
    n_users = 10
    n_items = 100
    k = 10

    # 1. Float32 scores that are nearly equal: e.g. base = 0.85, differences of 1e-6
    # Exact tie handling operates without perturbation, so strict inequalities are preserved!
    base_scores = 0.85 + rng.uniform(-1e-4, 1e-4, size=(n_users, n_items)).astype(np.float32)
    topk_fine = select_topk_exact(base_scores, k=k)

    for u in range(n_users):
        u_topk = topk_fine[u]
        u_scores = base_scores[u, u_topk]
        # Must be non-increasing
        assert np.all(np.diff(u_scores) <= 0.0), f"Scores in top-k not sorted descending: {u_scores}"

    # 2. High magnitude popularity counts up to ~50,000 with exact ties
    pop_scores = np.full((2, 100), 50000.0, dtype=np.float32)
    # Give higher count 51,000 to items 70 and 20
    pop_scores[:, [70, 20]] = 51000.0
    topk_pop = select_topk_exact(pop_scores, k=5)
    # Higher counts [20, 70] first, followed by lowest available indices [0, 1, 2]
    expected_pop = np.array([20, 70, 0, 1, 2])
    assert np.array_equal(topk_pop[0], expected_pop), f"Expected {expected_pop}, got {topk_pop[0]}"


# ==============================================================================
# A7. Paired Comparison Statistical Tests
# ==============================================================================

def test_a7_paired_comparison_identical_and_shift():
    """Verify evaluator.compare: identical inputs yield diff=0 and CI containing 0;
    constructed constant shift yields the exact shift."""
    from recommender.evaluation.evaluator import Evaluator

    rng = np.random.default_rng(42)
    n = 1000
    arr_a = rng.uniform(0.1, 0.9, size=n)

    # 1. Identical inputs
    comp_ident = Evaluator.compare(arr_a, arr_a.copy(), metric="test_metric")
    assert np.isclose(comp_ident.mean_diff, 0.0)
    assert comp_ident.ci_lower <= 0.0 <= comp_ident.ci_upper
    assert np.isclose(comp_ident.relative_lift, 0.0)
    assert np.isclose(comp_ident.pct_equal, 100.0)
    assert not comp_ident.is_distinguishable_from_zero

    # 2. Constructed constant shift of +0.05
    shift = 0.05
    arr_b = arr_a + shift
    comp_shift = Evaluator.compare(arr_b, arr_a, metric="test_metric")
    assert np.isclose(comp_shift.mean_diff, shift, atol=1e-6)
    assert np.isclose(comp_shift.ci_lower, shift, atol=1e-6)
    assert np.isclose(comp_shift.ci_upper, shift, atol=1e-6)
    assert comp_shift.is_distinguishable_from_zero
    assert np.isclose(comp_shift.pct_a_better, 100.0)


# ==============================================================================
# B1. Neutral Random Permutation Tie-Breaking Tests
# ==============================================================================

def test_b1_random_perm_tie_break_reproducible_and_neutral():
    """Verify B1: random permutation tie-break is reproducible across runs,
    and Spearman correlation with movie_id and train rating_count is ~0."""
    from scipy import sparse, stats
    from recommender.evaluation.protocol import EvaluationConfig, EvaluationContext
    from recommender.evaluation.evaluator import Evaluator

    n_cands = 18275
    # Synthetic candidate movie IDs roughly following ML-25M
    mids = np.arange(1, n_cands + 1)
    # Synthetic train counts strongly correlated with early movie IDs
    counts = np.maximum(1, (100000.0 / (np.sqrt(mids) + 1.0))).astype(int)

    # Context stub
    ctx = EvaluationContext(
        mode="validation",
        positive_threshold=4.0,
        candidate_movie_ids=mids,
        n_candidates=n_cands,
        movie_id_to_cand_idx={mid: idx for idx, mid in enumerate(mids)},
        eval_user_ids=np.array([1, 2]),
        user_id_to_eval_idx={1: 0, 2: 1},
        user_train_counts=np.array([50, 60]),
        user_history_spans_days=np.array([10.0, 20.0]),
        candidate_train_counts=counts,
        candidate_train_pos_counts=counts // 2,
        candidate_train_mean_ratings=np.full(n_cands, 3.5),
        global_train_mean=3.5,
        reachables=[{1, 2}, {3, 4}],
        reachable_counts=np.array([2, 2]),
        seen_matrix=sparse.csr_matrix((2, n_cands), dtype=np.float32),
        total_split_positives=4,
        unreachable_positives_count=0,
        unreachable_positives_pct=0.0,
        total_split_users=2,
        excluded_zero_pos_users_count=0,
        n_evaluated_users=2,
    )

    cfg1 = EvaluationConfig(seed=42, tie_break="random_perm")
    evaluator1 = Evaluator(ctx, cfg1)

    cfg2 = EvaluationConfig(seed=42, tie_break="random_perm")
    evaluator2 = Evaluator(ctx, cfg2)

    # 1. Exact reproducibility across runs with same seed
    assert np.array_equal(evaluator1.tie_ranks, evaluator2.tie_ranks)

    # 2. Spearman correlation with movie_id ~ 0 (|r| < 0.03)
    # Tolerance documentation: for N=18,275, SE = 1/sqrt(N) ≈ 0.0074. 4 * SE ≈ 0.03.
    corr_mid, p_mid = stats.spearmanr(evaluator1.tie_ranks, mids)
    assert abs(corr_mid) < 0.03, f"Spearman with movie_id was {corr_mid:.4f}, expected |r| < 0.03"

    # 3. Spearman correlation with train counts ~ 0 (|r| < 0.03)
    corr_count, p_count = stats.spearmanr(evaluator1.tie_ranks, counts)
    assert abs(corr_count) < 0.03, f"Spearman with train counts was {corr_count:.4f}, expected |r| < 0.03"


def test_b1_constant_score_recommender_yields_same_lists():
    """Verify B1: constant-score recommender yields the same recommendations across runs."""
    from scipy import sparse
    from recommender.evaluation.protocol import EvaluationConfig, EvaluationContext, Recommender
    from recommender.evaluation.evaluator import Evaluator

    n_cands = 500
    mids = np.arange(1, n_cands + 1)
    counts = np.ones(n_cands, dtype=int)

    ctx = EvaluationContext(
        mode="validation",
        positive_threshold=4.0,
        candidate_movie_ids=mids,
        n_candidates=n_cands,
        movie_id_to_cand_idx={mid: idx for idx, mid in enumerate(mids)},
        eval_user_ids=np.array([1, 2, 3]),
        user_id_to_eval_idx={1: 0, 2: 1, 3: 2},
        user_train_counts=np.array([10, 10, 10]),
        user_history_spans_days=np.array([5.0, 5.0, 5.0]),
        candidate_train_counts=counts,
        candidate_train_pos_counts=counts,
        candidate_train_mean_ratings=np.full(n_cands, 3.5),
        global_train_mean=3.5,
        reachables=[{1, 2}, {3, 4}, {5, 6}],
        reachable_counts=np.array([2, 2, 2]),
        seen_matrix=sparse.csr_matrix((3, n_cands), dtype=np.float32),
        total_split_positives=6,
        unreachable_positives_count=0,
        unreachable_positives_pct=0.0,
        total_split_users=3,
        excluded_zero_pos_users_count=0,
        n_evaluated_users=3,
    )

    class ConstantScoreRecommender(Recommender):
        def fit(self, train_df, context=None):
            return self

        def score(self, user_indices):
            # All items have uniform constant score 1.0
            return np.ones((len(user_indices), n_cands), dtype=np.float32)

    model = ConstantScoreRecommender()

    cfg1 = EvaluationConfig(k=10, seed=42, tie_break="random_perm")
    res1 = Evaluator(ctx, cfg1).evaluate(model, store_topk=True)

    cfg2 = EvaluationConfig(k=10, seed=42, tie_break="random_perm")
    res2 = Evaluator(ctx, cfg2).evaluate(model, store_topk=True)

    assert np.array_equal(res1.predicted_topk, res2.predicted_topk)



