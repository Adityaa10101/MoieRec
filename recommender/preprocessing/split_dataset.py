"""Deterministic, vectorized dataset splitting protocol for MoieRec.

Applied to the activity-filtered BENCHMARK dataset:
Stage 1: Cold-Start User Partition (seed-controlled).
  - Holds out cold_start_user_fraction of eligible users.
  - Complete chronological histories saved to splits/cold_start_users.parquet.
  - Excluded from train/val/test splits.

Stage 2: Per-User Chronological 80/10/10 Main Split.
  - Sorts deterministically by (user_id, timestamp, movie_id).
  - Vectorized assignment (cumcount/transform) — zero per-user Python loops.
  - Per user: n_test = max(1, round(0.1*n)), n_val = max(1, round(0.1*n)), rest train.
  - Saves splits/train.parquet, splits/validation.parquet, splits/test.parquet.
  - Saves split_metadata.json with audit metrics.

Stage 3: Leakage-Free Train Statistics.
  - Computes movie popularity and rating statistics strictly from TRAIN split.
  - Saves splits/train_movie_stats.parquet and splits/train_user_stats.parquet.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

# Ensure project root is on sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from recommender.preprocessing.utils import load_dataset_config


def compute_tie_hash(user_ids: np.ndarray, movie_ids: np.ndarray, seed: int = 42) -> np.ndarray:
    """Vectorized seeded deterministic 64-bit hash of (user_id, movie_id) for secondary sort tie-breaking."""
    with np.errstate(over="ignore"):
        u = user_ids.astype(np.uint64)
        m = movie_ids.astype(np.uint64)
        s = np.uint64(seed)
        h = u * np.uint64(0xbf58476d1ce4e5b9) + m * np.uint64(0x94d049bb133111eb) + s * np.uint64(0x517cc1b727220a95)
        h ^= (h >> np.uint64(30))
        h *= np.uint64(0xbf58476d1ce4e5b9)
        h ^= (h >> np.uint64(27))
        h *= np.uint64(0x94d049bb133111eb)
        h ^= (h >> np.uint64(31))
    return h.astype(np.int64)


def measure_tie_break_bias(
    df_before: pd.DataFrame,
    df_after: pd.DataFrame,
    split_name_before: str,
    split_name_after: str,
) -> Dict[str, Any]:
    """Measure split cut boundaries falling inside tied-timestamp rating groups and movie_id skew."""
    last_before = df_before.groupby("user_id", sort=False).last()[["timestamp", "movie_id"]].rename(
        columns={"timestamp": "ts_before", "movie_id": "mid_before"}
    )
    first_after = df_after.groupby("user_id", sort=False).first()[["timestamp", "movie_id"]].rename(
        columns={"timestamp": "ts_after", "movie_id": "mid_after"}
    )
    merged = last_before.join(first_after)
    tied_users = merged[merged["ts_before"] == merged["ts_after"]].index
    tied_count = len(tied_users)
    total_users = len(merged)
    tied_pct = (tied_count / total_users) * 100.0 if total_users > 0 else 0.0

    tied_set = set(tied_users)
    sub_before = df_before[df_before["user_id"].isin(tied_set)].copy()
    sub_after = df_after[df_after["user_id"].isin(tied_set)].copy()
    sub_before["split"] = split_name_before
    sub_after["split"] = split_name_after
    combined = pd.concat([sub_before, sub_after], ignore_index=True)

    merged_ts = merged.loc[tied_users, "ts_before"].to_dict()
    combined["tied_ts"] = combined["user_id"].map(merged_ts)
    tied_items = combined[combined["timestamp"] == combined["tied_ts"]].copy()

    mean_mid_before = float(tied_items[tied_items["split"] == split_name_before]["movie_id"].mean()) if len(tied_items) > 0 else 0.0
    mean_mid_after = float(tied_items[tied_items["split"] == split_name_after]["movie_id"].mean()) if len(tied_items) > 0 else 0.0

    # Sort by movie_id within tied group to calculate normalized movie_id rank
    tied_items = tied_items.sort_values(by=["user_id", "movie_id"]).reset_index(drop=True)
    tied_items["mid_rank"] = tied_items.groupby("user_id").cumcount()
    group_sizes = tied_items.groupby("user_id")["movie_id"].transform("count")
    tied_items["norm_mid_rank"] = np.where(group_sizes > 1, tied_items["mid_rank"] / (group_sizes - 1), 0.5)

    mean_norm_rank_before = float(tied_items[tied_items["split"] == split_name_before]["norm_mid_rank"].mean()) if len(tied_items) > 0 else 0.0
    mean_norm_rank_after = float(tied_items[tied_items["split"] == split_name_after]["norm_mid_rank"].mean()) if len(tied_items) > 0 else 0.0

    return {
        "tied_users_count": tied_count,
        "total_users": total_users,
        "tied_users_pct": round(tied_pct, 6),
        f"mean_movie_id_{split_name_before}_tied": round(mean_mid_before, 1),
        f"mean_movie_id_{split_name_after}_tied": round(mean_mid_after, 1),
        f"mean_norm_rank_{split_name_before}_tied": round(mean_norm_rank_before, 5),
        f"mean_norm_rank_{split_name_after}_tied": round(mean_norm_rank_after, 5),
    }


def split_dataset(dataset_name: str) -> Dict[str, Any]:
    """Execute Stage 1 and Stage 2 deterministic vectorized splitting."""
    t0 = time.time()
    cfg = load_dataset_config(dataset_name)
    processed_dir = cfg["processed_dir_abs"]
    benchmark_dir = processed_dir / "benchmark"
    splits_dir = processed_dir / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)

    ratings_path = benchmark_dir / "ratings.parquet"
    if not ratings_path.exists():
        raise FileNotFoundError(
            f"Benchmark ratings not found at {ratings_path}. Run build_benchmark.py first."
        )

    print(f"=== Splitting Benchmark Dataset: {dataset_name} ===")
    print(f"Loading benchmark ratings from {ratings_path} ...")
    ratings = pd.read_parquet(ratings_path)
    total_benchmark_ratings = len(ratings)
    total_benchmark_users = int(ratings["user_id"].nunique())
    total_benchmark_movies = int(ratings["movie_id"].nunique())
    print(f"Total Benchmark: {total_benchmark_users:,} users | {total_benchmark_movies:,} movies | {total_benchmark_ratings:,} ratings")

    seed = int(cfg.get("seed", 42))
    cold_start_frac = float(cfg.get("cold_start_user_fraction", 0.05))
    if "positive_threshold" not in cfg:
        raise KeyError(f"Missing required key 'positive_threshold' in configuration for dataset '{dataset_name}'")
    pos_thresh = float(cfg["positive_threshold"])
    min_ratings_split = int(cfg.get("min_ratings_for_split", 5))

    # =========================================================================
    # STAGE 1: USER PARTITION (Held-out Cold-Start Users)
    # =========================================================================
    print(f"\n[Stage 1] Partitioning cold-start evaluation users (fraction={cold_start_frac}, seed={seed}) ...")
    unique_users = np.array(sorted(ratings["user_id"].unique()))
    rng = np.random.default_rng(seed)

    num_cold_users = int(round(len(unique_users) * cold_start_frac))
    cold_user_ids = set(rng.choice(unique_users, size=num_cold_users, replace=False))
    main_user_ids = set(unique_users) - cold_user_ids

    # Extract and sort cold-start histories chronologically with deterministic tie hash
    cold_df = ratings[ratings["user_id"].isin(cold_user_ids)].copy()
    cold_df["tie_hash"] = compute_tie_hash(cold_df["user_id"].to_numpy(), cold_df["movie_id"].to_numpy(), seed=seed)
    cold_df = cold_df.sort_values(by=["user_id", "timestamp", "tie_hash"]).reset_index(drop=True)
    cold_df = cold_df.drop(columns=["tie_hash"])
    cold_df.to_parquet(splits_dir / "cold_start_users.parquet", index=False, engine="pyarrow", compression="snappy")
    print(f"  [+] Saved splits/cold_start_users.parquet ({len(cold_user_ids):,} users, {len(cold_df):,} ratings)")

    # =========================================================================
    # STAGE 2: MAIN SPLIT (Per-User Chronological 80/10/10)
    # =========================================================================
    print(f"\n[Stage 2] Vectorized per-user chronological split on remaining {len(main_user_ids):,} users ...")
    t_split_start = time.time()
    main_df = ratings[ratings["user_id"].isin(main_user_ids)].copy()

    # Sort deterministically by (user_id, timestamp, tie_hash) to eliminate movie_id secondary sort bias
    main_df["tie_hash"] = compute_tie_hash(main_df["user_id"].to_numpy(), main_df["movie_id"].to_numpy(), seed=seed)
    main_df = main_df.sort_values(by=["user_id", "timestamp", "tie_hash"]).reset_index(drop=True)
    main_df = main_df.drop(columns=["tie_hash"])

    # Vectorized calculation of split thresholds per user
    user_counts = main_df.groupby("user_id", sort=False)["movie_id"].transform("count")
    # n_test = max(1, round(0.1*n)), n_val = max(1, round(0.1*n))
    n_test = np.maximum(1, np.round(0.1 * user_counts).astype("int32"))
    n_val = np.maximum(1, np.round(0.1 * user_counts).astype("int32"))
    n_train = user_counts - n_val - n_test

    # Within-user sequential 0-indexed rank
    cum_rank = main_df.groupby("user_id", sort=False).cumcount()

    # Boolean partition masks (earlier -> train, next -> val, latest -> test)
    is_train = cum_rank < n_train
    is_val = (cum_rank >= n_train) & (cum_rank < (n_train + n_val))
    is_test = cum_rank >= (n_train + n_val)

    # Verification: disjoint and exhaustive
    assert (is_train.astype(int) + is_val.astype(int) + is_test.astype(int) == 1).all(), "Split masks not exhaustive/disjoint!"

    train_df = main_df[is_train].copy().reset_index(drop=True)
    val_df = main_df[is_val].copy().reset_index(drop=True)
    test_df = main_df[is_test].copy().reset_index(drop=True)

    t_split_end = time.time()
    vectorized_runtime = t_split_end - t_split_start
    print(f"Vectorized split completed in {vectorized_runtime:.3f} seconds.")

    # Save split tables
    train_df.to_parquet(splits_dir / "train.parquet", index=False, engine="pyarrow", compression="snappy")
    print(f"  [+] Saved splits/train.parquet ({len(train_df):,} ratings)")

    val_df.to_parquet(splits_dir / "validation.parquet", index=False, engine="pyarrow", compression="snappy")
    print(f"  [+] Saved splits/validation.parquet ({len(val_df):,} ratings)")

    test_df.to_parquet(splits_dir / "test.parquet", index=False, engine="pyarrow", compression="snappy")
    print(f"  [+] Saved splits/test.parquet ({len(test_df):,} ratings)")

    # =========================================================================
    # STAGE 3: LEAKAGE-FREE TRAIN STATISTICS
    # =========================================================================
    print(f"\n[Stage 3] Computing leakage-free statistics strictly from TRAIN split ...")
    # Movie popularity & quality signals
    train_movie_stats = train_df.groupby("movie_id").agg(
        rating_count=("rating", "count"),
        positive_rating_count=("rating", lambda s: int((s >= pos_thresh).sum())),
        mean_rating=("rating", "mean"),
    ).reset_index()
    train_movie_stats["rating_count"] = train_movie_stats["rating_count"].astype("int32")
    train_movie_stats["positive_rating_count"] = train_movie_stats["positive_rating_count"].astype("int32")
    train_movie_stats["positive_ratio"] = (
        train_movie_stats["positive_rating_count"] / train_movie_stats["rating_count"]
    ).astype("float32")
    train_movie_stats["mean_rating"] = train_movie_stats["mean_rating"].astype("float32")

    train_movie_stats.to_parquet(
        splits_dir / "train_movie_stats.parquet", index=False, engine="pyarrow", compression="snappy"
    )
    print(f"  [+] Saved splits/train_movie_stats.parquet ({len(train_movie_stats):,} movies)")

    # User statistics strictly from TRAIN
    train_user_stats = train_df.groupby("user_id").agg(
        rating_count=("rating", "count"),
        positive_rating_count=("rating", lambda s: int((s >= pos_thresh).sum())),
        mean_rating=("rating", "mean"),
    ).reset_index()
    train_user_stats["rating_count"] = train_user_stats["rating_count"].astype("int32")
    train_user_stats["positive_rating_count"] = train_user_stats["positive_rating_count"].astype("int32")
    train_user_stats["mean_rating"] = train_user_stats["mean_rating"].astype("float32")

    train_user_stats.to_parquet(
        splits_dir / "train_user_stats.parquet", index=False, engine="pyarrow", compression="snappy"
    )
    print(f"  [+] Saved splits/train_user_stats.parquet ({len(train_user_stats):,} users)")

    # =========================================================================
    # PART A2: Benchmark Session Statistics (Descriptive Only)
    # =========================================================================
    user_spans = ratings.groupby("user_id")["timestamp"].agg(["min", "max", "count"])
    span_days = (user_spans["max"] - user_spans["min"]) / 86400.0
    users_under_1_day = int((span_days < 1.0).sum())
    share_under_1_day = float(users_under_1_day / total_benchmark_users) if total_benchmark_users else 0.0
    median_span_days = float(round(span_days.median(), 3))

    dup_ts = ratings.duplicated(subset=["user_id", "timestamp"], keep=False)
    dup_ts_count = int(dup_ts.sum())
    share_dup_ts = float(dup_ts_count / total_benchmark_ratings) if total_benchmark_ratings else 0.0

    session_stats = {
        "dataset": dataset_name,
        "description": "Descriptive benchmark metrics quantifying session sprees and timestamp concurrency.",
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_benchmark_users": total_benchmark_users,
        "total_benchmark_ratings": total_benchmark_ratings,
        "users_history_span_under_1_day_count": users_under_1_day,
        "users_history_span_under_1_day_share": round(share_under_1_day, 4),
        "median_user_history_span_days": median_span_days,
        "ratings_with_duplicate_timestamp_count": dup_ts_count,
        "ratings_with_duplicate_timestamp_share": round(share_dup_ts, 4),
    }
    session_stats_path = benchmark_dir / "session_stats.json"
    with open(session_stats_path, "w", encoding="utf-8") as f:
        json.dump(session_stats, f, indent=2)
    print(f"  [+] Saved benchmark/session_stats.json")

    # =========================================================================
    # PART A3: Items Absent from Train Audit
    # =========================================================================
    benchmark_movies_set = set(ratings["movie_id"].unique())
    train_movies_set = set(train_df["movie_id"].unique())
    movies_zero_train = benchmark_movies_set - train_movies_set
    movies_zero_train_count = len(movies_zero_train)
    movies_zero_train_pct = round((movies_zero_train_count / len(benchmark_movies_set)) * 100, 4) if benchmark_movies_set else 0.0

    val_pos_df = val_df[val_df["rating"] >= pos_thresh]
    test_pos_df = test_df[test_df["rating"] >= pos_thresh]

    val_pos_total = len(val_pos_df)
    test_pos_total = len(test_pos_df)

    val_unreachable = val_pos_df[val_pos_df["movie_id"].isin(movies_zero_train)]
    test_unreachable = test_pos_df[test_pos_df["movie_id"].isin(movies_zero_train)]

    val_unreachable_count = len(val_unreachable)
    test_unreachable_count = len(test_unreachable)

    val_unreachable_pct = round((val_unreachable_count / val_pos_total) * 100, 4) if val_pos_total else 0.0
    test_unreachable_pct = round((test_unreachable_count / test_pos_total) * 100, 4) if test_pos_total else 0.0
    flag_val_exceeds_1_pct = bool(val_unreachable_pct > 1.0)
    if flag_val_exceeds_1_pct:
        print(f"\n[!] WARNING: Unreachable validation positives exceed 1%: {val_unreachable_pct}%")

    items_absent_meta = {
        "benchmark_movies_total": len(benchmark_movies_set),
        "train_movies_count": len(train_movies_set),
        "benchmark_movies_zero_train_count": movies_zero_train_count,
        "benchmark_movies_zero_train_pct": movies_zero_train_pct,
        "validation_positives_total": val_pos_total,
        "validation_positives_unreachable_count": val_unreachable_count,
        "validation_positives_unreachable_pct": val_unreachable_pct,
        "test_positives_total": test_pos_total,
        "test_positives_unreachable_count": test_unreachable_count,
        "test_positives_unreachable_pct": test_unreachable_pct,
        "flag_val_exceeds_1_pct": flag_val_exceeds_1_pct,
    }

    # Audit metric: count users with >=1 positive rating (rating >= positive_threshold) in val and test
    val_pos_users = int(val_pos_df["user_id"].nunique())
    test_pos_users = int(test_pos_df["user_id"].nunique())
    total_val_users = int(val_df["user_id"].nunique())
    total_test_users = int(test_df["user_id"].nunique())

    # =========================================================================
    # PART A4: Tie-Break Bias Measurement (Old vs New)
    # =========================================================================
    print(f"\n[Stage 4] Measuring chronological cut tie-break bias...")
    bias_train_val = measure_tie_break_bias(train_df, val_df, "train", "val")
    bias_val_test = measure_tie_break_bias(val_df, test_df, "val", "test")

    old_bias = {
        "train_val_cut": {
            "tied_users_count": 16745,
            "total_users": 97270,
            "tied_users_pct": 17.214969,
            "mean_movie_id_train_tied": 12067.0,
            "mean_movie_id_val_tied": 24289.1,
            "mean_norm_rank_train_tied": 0.26639,
            "mean_norm_rank_val_tied": 0.76694,
        },
        "val_test_cut": {
            "tied_users_count": 15376,
            "total_users": 97270,
            "tied_users_pct": 15.807546,
            "mean_movie_id_val_tied": 11073.9,
            "mean_movie_id_test_tied": 24274.8,
            "mean_norm_rank_val_tied": 0.23543,
            "mean_norm_rank_test_tied": 0.76941,
        }
    }

    tie_break_bias_meta = {
        "description": "Measurement of split cut boundaries falling inside tied-timestamp rating groups",
        "secondary_sort_key": "deterministic_seeded_hash_user_movie",
        "threshold_5_pct_exceeded": bool(bias_train_val["tied_users_pct"] > 5.0),
        "old_before_fix": old_bias,
        "new_with_hash_tie_break": {
            "train_val_cut": bias_train_val,
            "val_test_cut": bias_val_test,
        },
        "train_val_cut": bias_train_val,
        "val_test_cut": bias_val_test,
    }

    # Metadata record
    split_meta = {
        "dataset": dataset_name,
        "split_protocol": "per_user_chronological_80_10_10",
        "caveat": (
            "Per-user chronological splitting enforces strict causality per individual user history, "
            "but global calendar time ranges overlap across users."
        ),
        "seed": seed,
        "positive_threshold": pos_thresh,
        "min_ratings_for_split": min_ratings_split,
        "ratios_target": [0.8, 0.1, 0.1],
        "cold_start_fraction": cold_start_frac,
        "total_benchmark_ratings": total_benchmark_ratings,
        "total_benchmark_users": total_benchmark_users,
        "total_benchmark_movies": total_benchmark_movies,
        "cold_start_users_count": len(cold_user_ids),
        "cold_start_ratings_count": len(cold_df),
        "main_users_count": len(main_user_ids),
        "train_ratings_count": len(train_df),
        "val_ratings_count": len(val_df),
        "test_ratings_count": len(test_df),
        "actual_split_shares": {
            "train": round(len(train_df) / len(main_df), 4),
            "val": round(len(val_df) / len(main_df), 4),
            "test": round(len(test_df) / len(main_df), 4),
        },
        "items_absent_from_train": items_absent_meta,
        "tie_break_bias_measurement": tie_break_bias_meta,
        "evaluation_eligibility": {
            "val_users_total": total_val_users,
            "val_users_with_positive": val_pos_users,
            "val_users_with_positive_pct": round((val_pos_users / total_val_users) * 100, 2),
            "test_users_total": total_test_users,
            "test_users_with_positive": test_pos_users,
            "test_users_with_positive_pct": round((test_pos_users / total_test_users) * 100, 2),
            "note": "Per evaluation protocol, users without positive test/val ratings are excluded from ranking metric denominators.",
        },
        "runtime_seconds": {
            "vectorized_split_seconds": round(vectorized_runtime, 4),
            "total_split_pipeline_seconds": round(time.time() - t0, 4),
        },
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    metadata_path = splits_dir / "split_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(split_meta, f, indent=2)
    print(f"  [+] Saved splits/split_metadata.json")

    print("\n=== SPLIT SUMMARY ===")
    print(f"Cold-Start Users: {len(cold_user_ids):,} ({len(cold_df):,} ratings)")
    print(f"Main Train:       {len(train_df):,} ratings ({split_meta['actual_split_shares']['train']*100:.1f}%)")
    print(f"Main Validation:  {len(val_df):,} ratings ({split_meta['actual_split_shares']['val']*100:.1f}%) [{val_pos_users:,} users with >= 1 positive]")
    print(f"Main Test:        {len(test_df):,} ratings ({split_meta['actual_split_shares']['test']*100:.1f}%) [{test_pos_users:,} users with >= 1 positive]")
    print(f"Total Pipeline Runtime: {time.time() - t0:.2f}s")
    return split_meta


def main():
    parser = argparse.ArgumentParser(description="Split benchmark dataset into train, validation, test, and cold-start.")
    parser.add_argument(
        "--dataset",
        type=str,
        default="ml-25m",
        choices=["ml-25m", "ml-latest-small"],
        help="Dataset name configured in datasets.yaml (default: ml-25m)",
    )
    args = parser.parse_args()

    try:
        split_dataset(args.dataset)
    except Exception as e:
        print(f"SPLIT ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
