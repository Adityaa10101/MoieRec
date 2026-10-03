"""Tests verifying deterministic reproducibility across pipeline executions."""

import pandas as pd
import pytest

from recommender.preprocessing.build_benchmark import iterative_k_core
from recommender.preprocessing.split_dataset import split_dataset
from recommender.preprocessing.utils import compute_dataframe_content_hash


def test_iterative_k_core_determinism():
    """Verify that iterative k-core produces identical output across independent runs."""
    # Synthetic dataset
    ratings_data = {
        "user_id": [1, 1, 1, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5],
        "movie_id": [10, 20, 30, 10, 20, 10, 30, 40, 10, 20, 30, 10, 50],
        "rating": [4.0, 5.0, 3.0, 4.5, 2.0, 3.5, 4.0, 5.0, 4.0, 3.5, 4.5, 2.0, 1.0],
        "timestamp": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112],
    }
    df = pd.DataFrame(ratings_data)

    res1, iters1 = iterative_k_core(df, min_user_ratings=3, min_movie_ratings=3)
    res2, iters2 = iterative_k_core(df, min_user_ratings=3, min_movie_ratings=3)

    assert iters1 == iters2
    hash1 = compute_dataframe_content_hash(res1)
    hash2 = compute_dataframe_content_hash(res2)
    assert hash1 == hash2, f"K-core filtering is non-deterministic! Hash1={hash1}, Hash2={hash2}"
    pd.testing.assert_frame_equal(res1, res2)


@pytest.mark.slow
def test_end_to_end_pipeline_determinism():
    """Verify end-to-end split determinism across repeated executions on ml-latest-small."""
    from pathlib import Path
    from recommender.preprocessing.build_benchmark import build_benchmark_subset
    from recommender.preprocessing.split_dataset import split_dataset
    from recommender.preprocessing.build_content_features import build_features

    root = Path(__file__).resolve().parent.parent.parent
    dataset = "ml-latest-small"
    splits_dir = root / "data" / "processed" / dataset / "splits"

    # Ensure raw or processed data exists for ml-latest-small
    if not (root / "data" / "raw" / dataset).exists() and not splits_dir.exists():
        pytest.skip(f"Dataset {dataset} not found. Skipping slow end-to-end determinism test.")

    def get_hashes():
        train = pd.read_parquet(splits_dir / "train.parquet")
        val = pd.read_parquet(splits_dir / "validation.parquet")
        test = pd.read_parquet(splits_dir / "test.parquet")
        cold = pd.read_parquet(splits_dir / "cold_start_users.parquet")
        return {
            "train": compute_dataframe_content_hash(train),
            "val": compute_dataframe_content_hash(val),
            "test": compute_dataframe_content_hash(test),
            "cold": compute_dataframe_content_hash(cold),
        }

    # Run 1: execute pipeline
    build_benchmark_subset(dataset)
    split_dataset(dataset)
    build_features(dataset)
    hashes_run1 = get_hashes()

    # Run 2: re-execute pipeline
    build_benchmark_subset(dataset)
    split_dataset(dataset)
    build_features(dataset)
    hashes_run2 = get_hashes()

    assert hashes_run1 == hashes_run2, f"Pipeline determinism mismatch: {hashes_run1} vs {hashes_run2}"

