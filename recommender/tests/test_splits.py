"""Tests for chronological dataset splitting, tie-breaking, and cold-start user isolation."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from recommender.preprocessing.utils import load_dataset_config


def test_split_integrity_on_processed_data():
    """Verify split invariants across train, validation, test, and cold_start_users."""
    # Look for any available processed dataset (ml-latest-small or ml-25m)
    root = Path(__file__).resolve().parent.parent.parent
    splits_dir = root / "data" / "processed" / "ml-latest-small" / "splits"
    if not splits_dir.exists():
        splits_dir = root / "data" / "processed" / "ml-25m" / "splits"
    if not splits_dir.exists():
        pytest.skip("Processed splits not found. Run pipeline first.")

    train = pd.read_parquet(splits_dir / "train.parquet")
    val = pd.read_parquet(splits_dir / "validation.parquet")
    test = pd.read_parquet(splits_dir / "test.parquet")
    cold = pd.read_parquet(splits_dir / "cold_start_users.parquet")

    # 1. No (user_id, movie_id) overlap across train, val, test
    train_pairs = set(zip(train["user_id"], train["movie_id"]))
    val_pairs = set(zip(val["user_id"], val["movie_id"]))
    test_pairs = set(zip(test["user_id"], test["movie_id"]))

    assert len(train_pairs.intersection(val_pairs)) == 0, "Overlap found between train and validation!"
    assert len(train_pairs.intersection(test_pairs)) == 0, "Overlap found between train and test!"
    assert len(val_pairs.intersection(test_pairs)) == 0, "Overlap found between validation and test!"

    # 2. Cold-start users are 100% disjoint from train, val, and test users
    cold_users = set(cold["user_id"].unique())
    main_users = set(train["user_id"].unique()).union(set(val["user_id"].unique())).union(set(test["user_id"].unique()))
    assert len(cold_users.intersection(main_users)) == 0, "Cold-start users leaked into main split!"

    dataset_name = "ml-latest-small" if "ml-latest-small" in str(splits_dir) else "ml-25m"
    cfg = load_dataset_config(dataset_name)

    # 3. Per-user chronological order: train_max <= val_min <= test_min under tie-breaking rule
    # In Phase 2E.1, tie rule sorts by (timestamp, hash(user_id, movie_id, seed))
    from recommender.preprocessing.split_dataset import compute_tie_hash
    seed = int(cfg.get("seed", 42))

    sample_users = list(train["user_id"].unique()[:50])
    for uid in sample_users:
        u_train = train[train["user_id"] == uid].copy()
        u_val = val[val["user_id"] == uid].copy()
        u_test = test[test["user_id"] == uid].copy()

        u_train["tie_key"] = compute_tie_hash(u_train["user_id"].values, u_train["movie_id"].values, seed=seed)
        u_val["tie_key"] = compute_tie_hash(u_val["user_id"].values, u_val["movie_id"].values, seed=seed)
        u_test["tie_key"] = compute_tie_hash(u_test["user_id"].values, u_test["movie_id"].values, seed=seed)

        u_train = u_train.sort_values(by=["timestamp", "tie_key"])
        u_val = u_val.sort_values(by=["timestamp", "tie_key"])
        u_test = u_test.sort_values(by=["timestamp", "tie_key"])

        if len(u_train) > 0 and len(u_val) > 0:
            last_train = (u_train.iloc[-1]["timestamp"], u_train.iloc[-1]["tie_key"])
            first_val = (u_val.iloc[0]["timestamp"], u_val.iloc[0]["tie_key"])
            assert last_train <= first_val, f"Chronological leak between train and val for user {uid}"

        if len(u_val) > 0 and len(u_test) > 0:
            last_val = (u_val.iloc[-1]["timestamp"], u_val.iloc[-1]["tie_key"])
            first_test = (u_test.iloc[0]["timestamp"], u_test.iloc[0]["tie_key"])
            assert last_val <= first_test, f"Chronological leak between val and test for user {uid}"

    # 4. Check exact split size formula: n_test = max(1, round(0.1n)), n_val = max(1, round(0.1n))
    train_counts = train.groupby("user_id")["movie_id"].count()
    val_counts = val.groupby("user_id")["movie_id"].count()
    test_counts = test.groupby("user_id")["movie_id"].count()

    total_counts = train_counts.add(val_counts, fill_value=0).add(test_counts, fill_value=0)
    for uid, n in list(total_counts.items())[:100]:
        expected_test = max(1, int(round(0.1 * n)))
        expected_val = max(1, int(round(0.1 * n)))
        expected_train = n - expected_test - expected_val
        assert test_counts[uid] == expected_test, f"Test count mismatch for user {uid}: expected {expected_test}, got {test_counts[uid]}"
        assert val_counts[uid] == expected_val, f"Val count mismatch for user {uid}: expected {expected_val}, got {val_counts[uid]}"
        assert train_counts[uid] == expected_train, f"Train count mismatch for user {uid}: expected {expected_train}, got {train_counts[uid]}"

    # 5. Check no duplicate (user_id, movie_id) within any single split
    assert train.duplicated(subset=["user_id", "movie_id"]).sum() == 0, "Duplicates found within train!"
    assert val.duplicated(subset=["user_id", "movie_id"]).sum() == 0, "Duplicates found within validation!"
    assert test.duplicated(subset=["user_id", "movie_id"]).sum() == 0, "Duplicates found within test!"
    assert cold.duplicated(subset=["user_id", "movie_id"]).sum() == 0, "Duplicates found within cold_start_users!"

    # 6. Check that all movie_ids and user_ids exist in benchmark catalog
    bench_dir = splits_dir.parent / "benchmark"
    bench_movies = pd.read_parquet(bench_dir / "movies.parquet")
    bench_movie_ids = set(bench_movies["movie_id"].unique())
    bench_ratings = pd.read_parquet(bench_dir / "ratings.parquet")
    bench_user_ids = set(bench_ratings["user_id"].unique())

    for split_df, name in [(train, "train"), (val, "val"), (test, "test"), (cold, "cold")]:
        invalid_movies = set(split_df["movie_id"].unique()) - bench_movie_ids
        invalid_users = set(split_df["user_id"].unique()) - bench_user_ids
        assert len(invalid_movies) == 0, f"Found {len(invalid_movies)} invalid movie IDs in {name}!"
        assert len(invalid_users) == 0, f"Found {len(invalid_users)} invalid user IDs in {name}!"

    # 7. Positive threshold is dynamically read from config
    dataset_name = "ml-latest-small" if "ml-latest-small" in str(splits_dir) else "ml-25m"
    cfg = load_dataset_config(dataset_name)
    assert "positive_threshold" in cfg, "Config missing positive_threshold key"
    cfg_pos = float(cfg["positive_threshold"])

    # Modifying threshold changes the positive set
    higher_thresh = cfg_pos + 0.5
    count_at_cfg = (train["rating"] >= cfg_pos).sum()
    count_at_higher = (train["rating"] >= higher_thresh).sum()
    assert count_at_cfg > count_at_higher, "Positive threshold not altering positive set count!"
