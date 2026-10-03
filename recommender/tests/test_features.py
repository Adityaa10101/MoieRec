"""Tests for stable ID mappings, Tier 1 baseline features, and Tier 2 snapshot matrices."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from scipy import sparse


def test_id_mappings_round_trip():
    """Verify that ID mappings round-trip without loss or corruption."""
    root = Path(__file__).resolve().parent.parent.parent
    id_dir = root / "data" / "processed" / "ml-latest-small" / "id_mappings"
    if not id_dir.exists():
        id_dir = root / "data" / "processed" / "ml-25m" / "id_mappings"
    if not id_dir.exists():
        pytest.skip("ID mappings not found. Run pipeline first.")

    # 1. Full catalog movie mappings
    m2i = pd.read_parquet(id_dir / "movie_id_to_full_idx.parquet")
    i2m = pd.read_parquet(id_dir / "full_idx_to_movie_id.parquet")
    assert len(m2i) == len(i2m)
    # Check round-trip
    m_dict = dict(zip(m2i["movie_id"], m2i["full_idx"]))
    i_dict = dict(zip(i2m["internal_idx"], i2m["original_id"]))
    for m_id, idx in list(m_dict.items())[:100]:
        assert i_dict[idx] == m_id, f"Round-trip failed for movie_id {m_id}"

    # 2. Benchmark movie mappings
    bm2i = pd.read_parquet(id_dir / "movie_id_to_benchmark_idx.parquet")
    bi2m = pd.read_parquet(id_dir / "benchmark_idx_to_movie_id.parquet")
    assert len(bm2i) == len(bi2m)
    bm_dict = dict(zip(bm2i["movie_id"], bm2i["benchmark_idx"]))
    bi_dict = dict(zip(bi2m["internal_idx"], bi2m["original_id"]))
    for m_id, idx in list(bm_dict.items())[:100]:
        assert bi_dict[idx] == m_id, f"Round-trip failed for benchmark movie_id {m_id}"

    # 3. Benchmark user mappings
    bu2i = pd.read_parquet(id_dir / "user_id_to_benchmark_idx.parquet")
    bi2u = pd.read_parquet(id_dir / "benchmark_idx_to_user_id.parquet")
    assert len(bu2i) == len(bi2u)
    bu_dict = dict(zip(bu2i["user_id"], bu2i["benchmark_idx"]))
    bi_u_dict = dict(zip(bi2u["internal_idx"], bi2u["original_id"]))
    for u_id, idx in list(bu_dict.items())[:100]:
        assert bi_u_dict[idx] == u_id, f"Round-trip failed for user_id {u_id}"


def test_tier1_features_properties():
    """Verify Tier 1 baseline feature matrix dimensionality and non-negativity."""
    root = Path(__file__).resolve().parent.parent.parent
    feat_dir = root / "data" / "processed" / "ml-latest-small" / "features"
    if not feat_dir.exists():
        feat_dir = root / "data" / "processed" / "ml-25m" / "features"
    if not feat_dir.exists():
        pytest.skip("Features not found. Run pipeline first.")

    tier1_path = feat_dir / "tier1_baseline_features.npz"
    assert tier1_path.exists(), "tier1_baseline_features.npz missing!"

    mat = sparse.load_npz(tier1_path)
    assert isinstance(mat, sparse.csr_matrix)
    assert mat.shape[0] > 0
    assert mat.shape[1] > 0
    # Values should be non-negative (normalized [0, 1])
    assert (mat.data >= 0.0).all(), "Found negative feature values in Tier 1 matrix!"
    assert (mat.data <= 1.0).all(), "Found feature values exceeding 1.0 in Tier 1 matrix!"
