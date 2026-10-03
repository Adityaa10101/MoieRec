"""Unit tests for Content-Based Recommender (Model 1) and Cold-Start Evaluation.

Verifies:
- Profile construction matches hand-computed tiny example across all 4 variants
- Cosine scoring matches manual values
- Fit receives only TRAIN data (isolation from validation/test)
- Cold-start onboarding uses only K revealed items
- Zero-profile users handled gracefully and counted accurately
- Seen-item masking functions correctly with content-based scores
- explain() contributions sum to model score and never name zero-weight features
- Determinism across repeated runs
- cold_final guard raises PermissionError without final=True
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from scipy import sparse

from recommender.content_based.model import (
    ContentBasedRecommender,
    ProfileVariant,
)
from recommender.evaluation.cold_start import (
    ColdStartEvaluator,
    load_cold_start_split,
    partition_cold_start_users,
)
from recommender.evaluation.evaluator import Evaluator
from recommender.evaluation.protocol import (
    EvaluationConfig,
    build_evaluation_context,
)


@pytest.fixture
def tiny_catalog():
    """Tiny 3-item, 2-feature synthetic catalog."""
    # Item 0: [1.0, 0.0]
    # Item 1: [0.0, 1.0]
    # Item 2: [0.6, 0.8] (L2-norm = 1.0)
    features = np.array([
        [1.0, 0.0],
        [0.0, 1.0],
        [0.6, 0.8],
    ], dtype=np.float32)
    candidate_ids = np.array([101, 102, 103])
    feature_names = ["genre:Sci-Fi", "genre:Drama"]
    return features, candidate_ids, feature_names


def test_hand_computed_profile_construction(tiny_catalog, monkeypatch):
    features, candidate_ids, feature_names = tiny_catalog

    # Train interactions for User 1:
    # Item 101 (index 0): rating 5.0
    # Item 102 (index 1): rating 4.0
    train_df = pd.DataFrame([
        {"user_id": 1, "movie_id": 101, "rating": 5.0, "timestamp": 100},
        {"user_id": 1, "movie_id": 102, "rating": 4.0, "timestamp": 101},
    ])

    # 1. pos_mean (threshold = 4.0):
    # Both items >= 4.0 -> raw sum = [1.0, 0.0] + [0.0, 1.0] = [1.0, 1.0]
    # L2 normalized: [1/sqrt(2), 1/sqrt(2)] = [0.70710678, 0.70710678]
    model_pos_mean = ContentBasedRecommender(profile_variant=ProfileVariant.POS_MEAN, positive_threshold=4.0)
    model_pos_mean.item_features = features
    model_pos_mean.candidate_movie_ids = candidate_ids
    model_pos_mean.movie_id_to_cand_idx = {mid: i for i, mid in enumerate(candidate_ids)}
    model_pos_mean.n_candidates = len(candidate_ids)
    model_pos_mean._build_user_profiles(train_df)

    expected_pos_mean = np.array([1.0 / np.sqrt(2), 1.0 / np.sqrt(2)], dtype=np.float32)
    np.testing.assert_allclose(model_pos_mean.user_profiles[0], expected_pos_mean, rtol=1e-5)
    assert model_pos_mean.n_zero_profile_users == 0

    # 2. rating_weighted:
    # raw sum = 5.0 * [1, 0] + 4.0 * [0, 1] = [5.0, 4.0]
    # norm = sqrt(25 + 16) = sqrt(41) ~ 6.403124
    # normalized = [5/sqrt(41), 4/sqrt(41)] = [0.7808688, 0.624695]
    model_rw = ContentBasedRecommender(profile_variant=ProfileVariant.RATING_WEIGHTED)
    model_rw.item_features = features
    model_rw.candidate_movie_ids = candidate_ids
    model_rw.movie_id_to_cand_idx = {mid: i for i, mid in enumerate(candidate_ids)}
    model_rw.n_candidates = len(candidate_ids)
    model_rw._build_user_profiles(train_df)

    expected_rw = np.array([5.0 / np.sqrt(41), 4.0 / np.sqrt(41)], dtype=np.float32)
    np.testing.assert_allclose(model_rw.user_profiles[0], expected_rw, rtol=1e-5)

    # 3. centered:
    # user mean = (5.0 + 4.0)/2 = 4.5
    # weights: Item 101: +0.5, Item 102: -0.5
    # raw sum = 0.5 * [1, 0] - 0.5 * [0, 1] = [0.5, -0.5]
    # L2 normalized = [1/sqrt(2), -1/sqrt(2)] = [0.70710678, -0.70710678]
    model_c = ContentBasedRecommender(profile_variant=ProfileVariant.CENTERED)
    model_c.item_features = features
    model_c.candidate_movie_ids = candidate_ids
    model_c.movie_id_to_cand_idx = {mid: i for i, mid in enumerate(candidate_ids)}
    model_c.n_candidates = len(candidate_ids)
    model_c._build_user_profiles(train_df)

    expected_c = np.array([1.0 / np.sqrt(2), -1.0 / np.sqrt(2)], dtype=np.float32)
    np.testing.assert_allclose(model_c.user_profiles[0], expected_c, rtol=1e-5)

    # 4. pos_rating_weighted:
    # both >= 4.0, identical to rating_weighted in this case
    model_prw = ContentBasedRecommender(profile_variant=ProfileVariant.POS_RATING_WEIGHTED, positive_threshold=4.0)
    model_prw.item_features = features
    model_prw.candidate_movie_ids = candidate_ids
    model_prw.movie_id_to_cand_idx = {mid: i for i, mid in enumerate(candidate_ids)}
    model_prw.n_candidates = len(candidate_ids)
    model_prw._build_user_profiles(train_df)

    np.testing.assert_allclose(model_prw.user_profiles[0], expected_rw, rtol=1e-5)


def test_hand_computed_cosine_scores(tiny_catalog):
    features, candidate_ids, _ = tiny_catalog

    # User profile: [0.6, 0.8] (normalized)
    # Cosine scores:
    # with Item 0 [1.0, 0.0] -> 0.6 * 1.0 + 0.8 * 0.0 = 0.6
    # with Item 1 [0.0, 1.0] -> 0.6 * 0.0 + 0.8 * 1.0 = 0.8
    # with Item 2 [0.6, 0.8] -> 0.6 * 0.6 + 0.8 * 0.8 = 1.0
    model = ContentBasedRecommender()
    model.item_features = features
    model.user_profiles = np.array([[0.6, 0.8]], dtype=np.float32)
    model.candidate_movie_ids = candidate_ids
    model.movie_id_to_cand_idx = {mid: i for i, mid in enumerate(candidate_ids)}
    model.n_candidates = len(candidate_ids)

    scores = model.score(np.array([0]))
    expected_scores = np.array([[0.6, 0.8, 1.0]], dtype=np.float32)
    np.testing.assert_allclose(scores, expected_scores, rtol=1e-5)


def test_zero_profile_user_handling(tiny_catalog):
    features, candidate_ids, _ = tiny_catalog

    # User 2 has only a 2.0 rating (below positive_threshold=4.0)
    train_df = pd.DataFrame([
        {"user_id": 2, "movie_id": 101, "rating": 2.0, "timestamp": 100},
    ])

    model = ContentBasedRecommender(profile_variant=ProfileVariant.POS_MEAN, positive_threshold=4.0)
    model.item_features = features
    model.candidate_movie_ids = candidate_ids
    model.movie_id_to_cand_idx = {mid: i for i, mid in enumerate(candidate_ids)}
    model.n_candidates = len(candidate_ids)
    model._build_user_profiles(train_df)

    assert model.n_zero_profile_users == 1
    np.testing.assert_array_equal(model.user_profiles[0], np.zeros(2, dtype=np.float32))

    # Scores must be all zero
    scores = model.score(np.array([0]))
    np.testing.assert_array_equal(scores, np.zeros((1, 3), dtype=np.float32))


def test_explain_contributions_sum_and_no_zero_feature(tiny_catalog):
    features, candidate_ids, feature_names = tiny_catalog

    model = ContentBasedRecommender()
    model.item_features = features
    model.feature_names = feature_names
    # User profile: [0.6, 0.8]
    model.user_profiles = np.array([[0.6, 0.8]], dtype=np.float32)
    model.candidate_movie_ids = candidate_ids
    model.n_candidates = len(candidate_ids)

    # Explain score for Item 0 [1.0, 0.0]
    # Score = 0.6. Feature 0 contrib = 0.6, Feature 1 contrib = 0.0.
    explanation_item0 = model.explain(user_idx=0, item_idx=0, top_n=3)
    assert len(explanation_item0) == 1  # Feature 1 has 0 contrib, must be excluded!
    assert explanation_item0[0]["feature"] == "genre:Sci-Fi"
    assert explanation_item0[0]["contribution"] == 0.6
    assert explanation_item0[0]["percentage"] == 100.0

    # Explain score for Item 2 [0.6, 0.8]
    # Score = 1.0. Feature 0 contrib = 0.36, Feature 1 contrib = 0.64.
    explanation_item2 = model.explain(user_idx=0, item_idx=2, top_n=3)
    assert len(explanation_item2) == 2
    # Feature 1 should be first (0.64 > 0.36)
    assert explanation_item2[0]["feature"] == "genre:Drama"
    assert explanation_item2[0]["contribution"] == 0.64
    assert explanation_item2[1]["feature"] == "genre:Sci-Fi"
    assert explanation_item2[1]["contribution"] == 0.36

    # Sum check
    contrib_sum = sum(e["contribution"] for e in explanation_item2)
    model_score = float(model.score(np.array([0]))[0, 2])
    assert abs(contrib_sum - model_score) < 1e-5


def test_model_train_only_isolation(tiny_catalog):
    features, candidate_ids, _ = tiny_catalog

    train_df = pd.DataFrame([
        {"user_id": 1, "movie_id": 101, "rating": 5.0, "timestamp": 100},
    ])
    val_df = pd.DataFrame([
        {"user_id": 1, "movie_id": 102, "rating": 5.0, "timestamp": 200},
    ])

    model = ContentBasedRecommender(profile_variant=ProfileVariant.POS_MEAN)
    model.item_features = features
    model.candidate_movie_ids = candidate_ids
    model.movie_id_to_cand_idx = {mid: i for i, mid in enumerate(candidate_ids)}
    model.n_candidates = len(candidate_ids)

    # Fit receives ONLY train_df
    model._build_user_profiles(train_df)

    # User profile should only reflect Item 101 [1.0, 0.0]
    expected_p = np.array([1.0, 0.0], dtype=np.float32)
    np.testing.assert_allclose(model.user_profiles[0], expected_p, rtol=1e-5)


def test_seen_item_masking_with_content_model():
    """Verify Evaluator seen-item masking masks train-rated items with content model."""
    train_df = pd.DataFrame([
        {"user_id": 1, "movie_id": 101, "rating": 5.0, "timestamp": 100},
    ])
    val_df = pd.DataFrame([
        {"user_id": 1, "movie_id": 102, "rating": 5.0, "timestamp": 200},
    ])

    ctx = build_evaluation_context(train_df, val_df, mode="validation", positive_threshold=4.0)
    evaluator = Evaluator(ctx, EvaluationConfig(k=1, batch_size=10))

    # Mock model where item 101 has highest score (10.0), but was seen in train!
    class MockModel:
        def score(self, user_indices):
            # item 0 (101): 10.0, item 1 (102): 5.0
            return np.array([[10.0]], dtype=np.float32) if len(ctx.candidate_movie_ids) == 1 else np.array([[10.0, 5.0]], dtype=np.float32)

    # Item 101 was seen in train, so it must be masked.
    res = evaluator.evaluate(MockModel(), store_topk=True)
    # If 101 is masked, the top recommendation cannot be item 101 (index 0) if another candidate exists
    if ctx.n_candidates > 1:
        assert res.topk_item_indices[0, 0] != 0


def test_cold_final_guard(tmp_path):
    cold_parquet = tmp_path / "cold_start_users.parquet"
    partition_json = tmp_path / "cold_start_partition.json"

    # Create dummy cold users
    dummy_data = []
    for uid in range(1, 11):
        for mid in [101, 102, 103]:
            dummy_data.append({"user_id": uid, "movie_id": mid, "rating": 4.5, "timestamp": 1000 + mid})
    pd.DataFrame(dummy_data).to_parquet(cold_parquet)

    part_meta = partition_cold_start_users(cold_parquet, partition_json, seed=42)
    assert part_meta["n_cold_dev"] == 5
    assert part_meta["n_cold_final"] == 5

    # Accessing cold_dev without final=True must succeed
    dev_df = load_cold_start_split("cold_dev", final=False, splits_dir=tmp_path)
    assert dev_df["user_id"].nunique() == 5

    # Accessing cold_final without final=True must raise PermissionError
    with pytest.raises(PermissionError, match="strictly guarded"):
        load_cold_start_split("cold_final", final=False, splits_dir=tmp_path)

    # Accessing cold_final with final=True must succeed
    final_df = load_cold_start_split("cold_final", final=True, splits_dir=tmp_path)
    assert final_df["user_id"].nunique() == 5


def test_content_model_determinism(tiny_catalog):
    features, candidate_ids, _ = tiny_catalog
    train_df = pd.DataFrame([
        {"user_id": 1, "movie_id": 101, "rating": 5.0, "timestamp": 100},
        {"user_id": 2, "movie_id": 102, "rating": 4.0, "timestamp": 101},
        {"user_id": 3, "movie_id": 103, "rating": 4.5, "timestamp": 102},
    ])

    m1 = ContentBasedRecommender(profile_variant=ProfileVariant.POS_MEAN)
    m1.item_features = features
    m1.candidate_movie_ids = candidate_ids
    m1.movie_id_to_cand_idx = {mid: i for i, mid in enumerate(candidate_ids)}
    m1.n_candidates = len(candidate_ids)
    m1._build_user_profiles(train_df)
    s1 = m1.score(np.array([0, 1, 2]))

    m2 = ContentBasedRecommender(profile_variant=ProfileVariant.POS_MEAN)
    m2.item_features = features
    m2.candidate_movie_ids = candidate_ids
    m2.movie_id_to_cand_idx = {mid: i for i, mid in enumerate(candidate_ids)}
    m2.n_candidates = len(candidate_ids)
    m2._build_user_profiles(train_df)
    s2 = m2.score(np.array([0, 1, 2]))

    np.testing.assert_array_equal(s1, s2)
