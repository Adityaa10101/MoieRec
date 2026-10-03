"""Parse raw MovieLens CSV files into normalized Parquet tables and compute full catalog statistics.

Outputs saved under data/processed/<dataset>/full/:
- ratings.parquet
- movies.parquet
- tags.parquet (optional)
- links.parquet (optional)
- genome_scores.parquet (optional)
- genome_tags.parquet (optional)
- dataset_summary.json (Full descriptive statistics with explicit leakage disclaimer)
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

from recommender.preprocessing.adapters.csv_adapter import MovieLensCSVAdapter
from recommender.preprocessing.utils import load_dataset_config


def compute_catalog_statistics(
    ratings: pd.DataFrame, movies: pd.DataFrame, level_name: str = "full"
) -> Dict[str, Any]:
    """Compute comprehensive descriptive dataset statistics.
    
    Adheres strictly to the LEAKAGE RULE: Full catalog statistics are marked
    as descriptive only and never utilized in modeling or evaluation.
    """
    total_ratings = int(len(ratings))
    total_movies = int(len(movies))
    unique_rated_movies = int(ratings["movie_id"].nunique())
    unique_users = int(ratings["user_id"].nunique())

    # Density & sparsity on two distinct bases:
    # 1. Rated movies basis: only movies with >= 1 interaction
    matrix_cells_rated = unique_users * unique_rated_movies
    density_rated = float(total_ratings / matrix_cells_rated) if matrix_cells_rated > 0 else 0.0
    sparsity_rated = float(1.0 - density_rated)

    # 2. Full catalog basis: all movies in catalog (including unrated)
    matrix_cells_full = unique_users * total_movies
    density_full = float(total_ratings / matrix_cells_full) if matrix_cells_full > 0 else 0.0
    sparsity_full = float(1.0 - density_full)

    # Rating distribution
    rating_counts = ratings["rating"].value_counts().sort_index()
    rating_distribution = {str(k): int(v) for k, v in rating_counts.items()}

    # Rating summary metrics
    r_series = ratings["rating"]
    r_stats = {
        "min": float(r_series.min()),
        "max": float(r_series.max()),
        "mean": float(round(r_series.mean(), 4)),
        "median": float(r_series.median()),
        "std": float(round(r_series.std(), 4)),
    }

    # Timestamp range
    min_ts = int(ratings["timestamp"].min())
    max_ts = int(ratings["timestamp"].max())
    ts_range = {
        "min_timestamp": min_ts,
        "max_timestamp": max_ts,
        "min_datetime_utc": datetime.fromtimestamp(min_ts, timezone.utc).isoformat(),
        "max_datetime_utc": datetime.fromtimestamp(max_ts, timezone.utc).isoformat(),
    }

    # Ratings per user
    user_counts = ratings["user_id"].value_counts()
    user_stats = {
        "mean": float(round(user_counts.mean(), 2)),
        "median": float(user_counts.median()),
        "min": int(user_counts.min()),
        "max": int(user_counts.max()),
        "p10": float(user_counts.quantile(0.10)),
        "p25": float(user_counts.quantile(0.25)),
        "p50": float(user_counts.quantile(0.50)),
        "p75": float(user_counts.quantile(0.75)),
        "p90": float(user_counts.quantile(0.90)),
        "p99": float(user_counts.quantile(0.99)),
    }

    # Ratings per movie
    movie_counts = ratings["movie_id"].value_counts()
    movie_stats = {
        "mean": float(round(movie_counts.mean(), 2)),
        "median": float(movie_counts.median()),
        "min": int(movie_counts.min()),
        "max": int(movie_counts.max()),
        "p10": float(movie_counts.quantile(0.10)),
        "p25": float(movie_counts.quantile(0.25)),
        "p50": float(movie_counts.quantile(0.50)),
        "p75": float(movie_counts.quantile(0.75)),
        "p90": float(movie_counts.quantile(0.90)),
        "p99": float(movie_counts.quantile(0.99)),
    }

    # Low activity counts
    low_activity = {
        "users_under_10_ratings": int((user_counts < 10).sum()),
        "users_under_20_ratings": int((user_counts < 20).sum()),
        "movies_under_5_ratings": int((movie_counts < 5).sum()),
        "movies_under_10_ratings": int((movie_counts < 10).sum()),
        "movies_under_20_ratings": int((movie_counts < 20).sum()),
    }

    # Genres count
    all_genres = set()
    for g_list in movies["genres"]:
        if isinstance(g_list, list):
            all_genres.update(g_list)
        elif isinstance(g_list, np.ndarray):
            all_genres.update(list(g_list))
    genres_count = len(all_genres)

    summary = {
        "level": level_name,
        "leakage_disclaimer": (
            "Descriptive catalog statistics only, strictly prohibited from modeling, "
            "feature engineering, or evaluation candidate pools to prevent data leakage."
        ),
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_ratings": total_ratings,
        "total_movies": total_movies,
        "unique_rated_movies": unique_rated_movies,
        "unique_users": unique_users,
        "density_rated_movies_basis": density_rated,
        "sparsity_rated_movies_basis": sparsity_rated,
        "density_full_catalog_basis": density_full,
        "sparsity_full_catalog_basis": sparsity_full,
        "density_basis_description": {
            "rated_movies_basis": "total_ratings / (unique_users * unique_rated_movies)",
            "full_catalog_basis": "total_ratings / (unique_users * total_movies)",
        },
        "density": density_rated,
        "sparsity": sparsity_rated,
        "rating_distribution": rating_distribution,
        "rating_stats": r_stats,
        "timestamp_range": ts_range,
        "ratings_per_user": user_stats,
        "ratings_per_movie": movie_stats,
        "low_activity_counts": low_activity,
        "genres_count": genres_count,
        "genres_list": sorted(list(all_genres)),
    }
    return summary


def parse_and_save_full_dataset(dataset_name: str) -> None:
    """Parse raw files and serialize normalized Parquet tables for the full catalog."""
    cfg = load_dataset_config(dataset_name)
    extracted_dir = cfg["extracted_dir_abs"]
    processed_dir = cfg["processed_dir_abs"]
    full_dir = processed_dir / "full"
    full_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    print(f"=== Parsing Full Catalog: {dataset_name} ===")
    print(f"Source: {extracted_dir}")
    print(f"Destination: {full_dir}")

    adapter = MovieLensCSVAdapter(cfg)
    norm = adapter.load_normalized(extracted_dir)

    # Save to Parquet
    print("\nWriting normalized Parquet tables...")
    norm.ratings.to_parquet(full_dir / "ratings.parquet", index=False, engine="pyarrow", compression="snappy")
    print(f"  [+] ratings.parquet ({len(norm.ratings):,} rows)")

    norm.movies.to_parquet(full_dir / "movies.parquet", index=False, engine="pyarrow", compression="snappy")
    print(f"  [+] movies.parquet ({len(norm.movies):,} rows)")

    if norm.tags is not None:
        norm.tags.to_parquet(full_dir / "tags.parquet", index=False, engine="pyarrow", compression="snappy")
        print(f"  [+] tags.parquet ({len(norm.tags):,} rows)")

    if norm.links is not None:
        norm.links.to_parquet(full_dir / "links.parquet", index=False, engine="pyarrow", compression="snappy")
        print(f"  [+] links.parquet ({len(norm.links):,} rows)")

    if norm.genome_scores is not None:
        norm.genome_scores.to_parquet(full_dir / "genome_scores.parquet", index=False, engine="pyarrow", compression="snappy")
        print(f"  [+] genome_scores.parquet ({len(norm.genome_scores):,} rows)")

    if norm.genome_tags is not None:
        norm.genome_tags.to_parquet(full_dir / "genome_tags.parquet", index=False, engine="pyarrow", compression="snappy")
        print(f"  [+] genome_tags.parquet ({len(norm.genome_tags):,} rows)")

    # Compute & save summary statistics
    print("\nComputing full catalog descriptive statistics...")
    stats = compute_catalog_statistics(norm.ratings, norm.movies, level_name="full")
    summary_path = full_dir / "dataset_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"  [+] dataset_summary.json saved at: {summary_path}")

    elapsed = time.time() - start_time
    print(f"\nParsing completed in {elapsed:.2f} seconds.")
    print(f"Users: {stats['unique_users']:,} | Movies: {stats['total_movies']:,} | Ratings: {stats['total_ratings']:,}")
    print(f"Density: {stats['density']:.6f} | Sparsity: {stats['sparsity']:.6f}")


def main():
    parser = argparse.ArgumentParser(description="Parse raw MovieLens CSV files into normalized Parquet tables.")
    parser.add_argument(
        "--dataset",
        type=str,
        default="ml-25m",
        choices=["ml-25m", "ml-latest-small"],
        help="Dataset name configured in datasets.yaml (default: ml-25m)",
    )
    args = parser.parse_args()

    try:
        parse_and_save_full_dataset(args.dataset)
    except Exception as e:
        print(f"PARSING ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
