"""Build activity-filtered benchmark subset using iterative k-core filtering.

1. Evaluates a 3x3 grid of (min_user_ratings, min_movie_ratings) thresholds.
2. Applies iterative k-core filtering (repeating until convergence, since 1-pass filtering is not stable).
3. Applies optional deterministic user sampling (benchmark_max_users + seed).
4. Saves filtered benchmark tables to data/processed/<dataset>/benchmark/:
   - ratings.parquet
   - movies.parquet
   - tags.parquet (optional)
   - links.parquet (optional)
   - dataset_summary.json (Benchmark descriptive statistics)
   - grid_analysis.json (Threshold sensitivity matrix)
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from recommender.preprocessing.parse_movielens import compute_catalog_statistics
from recommender.preprocessing.utils import load_dataset_config


def iterative_k_core(
    ratings: pd.DataFrame, min_user_ratings: int, min_movie_ratings: int
) -> Tuple[pd.DataFrame, int]:
    """Iteratively filter ratings until all users and movies meet minimum thresholds.
    
    A single pass is not stable because removing movies can drop user rating counts
    below the threshold, and vice-versa.
    
    Returns:
        Tuple of (filtered_ratings_df, num_iterations)
    """
    df = ratings[["user_id", "movie_id", "rating", "timestamp"]].copy()
    iterations = 0

    while True:
        iterations += 1
        initial_count = len(df)

        # 1. Filter users
        user_counts = df["user_id"].value_counts()
        valid_users = user_counts[user_counts >= min_user_ratings].index
        df = df[df["user_id"].isin(valid_users)]

        # 2. Filter movies
        movie_counts = df["movie_id"].value_counts()
        valid_movies = movie_counts[movie_counts >= min_movie_ratings].index
        df = df[df["movie_id"].isin(valid_movies)]

        final_count = len(df)
        if final_count == initial_count:
            break

    return df.reset_index(drop=True), iterations


def compute_threshold_grid(
    ratings: pd.DataFrame,
    user_thresholds: List[int] = [20, 50, 100],
    movie_thresholds: List[int] = [5, 20, 50],
) -> List[Dict[str, Any]]:
    """Compute benchmark metrics for a grid of user and movie activity thresholds."""
    grid_results = []
    print("\nComputing threshold sensitivity grid (iterative k-core):")

    for u_min in user_thresholds:
        for m_min in movie_thresholds:
            t0 = time.time()
            filtered_df, iters = iterative_k_core(ratings, u_min, m_min)
            elapsed = time.time() - t0

            n_users = int(filtered_df["user_id"].nunique())
            n_movies = int(filtered_df["movie_id"].nunique())
            n_ratings = int(len(filtered_df))
            matrix_size = n_users * n_movies
            density = float(n_ratings / matrix_size) if matrix_size > 0 else 0.0
            sparsity = float(1.0 - density)

            row = {
                "min_user_ratings": u_min,
                "min_movie_ratings": m_min,
                "iterations_to_converge": iters,
                "users": n_users,
                "movies": n_movies,
                "ratings": n_ratings,
                "density": round(density, 6),
                "sparsity": round(sparsity, 6),
                "runtime_seconds": round(elapsed, 2),
            }
            grid_results.append(row)
            print(
                f"  -> Threshold ({u_min:>3} user, {m_min:>2} movie): "
                f"Users={n_users:,} | Movies={n_movies:,} | Ratings={n_ratings:,} | "
                f"Density={density:.6f} ({iters} iters, {elapsed:.2f}s)"
            )

    return grid_results


def print_grid_table(grid_results: List[Dict[str, Any]], provisional_u: int, provisional_m: int) -> None:
    """Print formatted markdown table of the threshold grid."""
    print("\n" + "=" * 80)
    print("THRESHOLD SENSITIVITY GRID TABLE (ITERATIVE K-CORE FILTERING)")
    print("=" * 80)
    print(f"| {'Min User':>8} | {'Min Movie':>9} | {'Users':>10} | {'Movies':>8} | {'Ratings':>12} | {'Density':>10} | {'Status':>12} |")
    print(f"|{'-'*10}|{'-'*11}|{'-'*12}|{'-'*10}|{'-'*14}|{'-'*12}|{'-'*14}|")
    for r in grid_results:
        is_prov = (r["min_user_ratings"] == provisional_u and r["min_movie_ratings"] == provisional_m)
        status = "PROVISIONAL *" if is_prov else "Evaluated"
        print(
            f"| {r['min_user_ratings']:>8} | {r['min_movie_ratings']:>9} | {r['users']:>10,} | "
            f"{r['movies']:>8,} | {r['ratings']:>12,} | {r['density']:>10.6f} | {status:>12} |"
        )
    print("=" * 80)
    print("* Configured provisional baseline threshold for model benchmarking.\n")


def build_benchmark_subset(
    dataset_name: str,
    override_min_user: int = None,
    override_min_movie: int = None,
) -> None:
    """Filter full catalog into benchmark subset and write Parquet tables."""
    cfg = load_dataset_config(dataset_name)
    processed_dir = cfg["processed_dir_abs"]
    full_dir = processed_dir / "full"
    benchmark_dir = processed_dir / "benchmark"
    benchmark_dir.mkdir(parents=True, exist_ok=True)

    ratings_path = full_dir / "ratings.parquet"
    movies_path = full_dir / "movies.parquet"
    if not ratings_path.exists() or not movies_path.exists():
        raise FileNotFoundError(
            f"Full catalog tables missing in {full_dir}. Run parse_movielens.py first."
        )

    print(f"Loading full catalog from {full_dir} ...")
    ratings = pd.read_parquet(ratings_path)
    movies = pd.read_parquet(movies_path)

    # 1. Evaluate sensitivity grid
    grid = compute_threshold_grid(ratings, user_thresholds=[20, 50, 100], movie_thresholds=[5, 20, 50])
    u_thresh = override_min_user if override_min_user is not None else cfg["min_user_ratings"]
    m_thresh = override_min_movie if override_min_movie is not None else cfg["min_movie_ratings"]
    print_grid_table(grid, u_thresh, m_thresh)

    # Save grid analysis
    with open(benchmark_dir / "grid_analysis.json", "w", encoding="utf-8") as f:
        json.dump(grid, f, indent=2)

    # 2. Build benchmark with selected threshold
    print(f"Filtering benchmark with iterative k-core (min_user={u_thresh}, min_movie={m_thresh}) ...")
    bench_ratings, iters = iterative_k_core(ratings, u_thresh, m_thresh)
    print(f"Converged in {iters} iterations.")

    # 3. Optional deterministic user subsampling (if benchmark_max_users is configured)
    max_users = cfg.get("benchmark_max_users")
    seed = cfg.get("seed", 42)
    if max_users is not None and bench_ratings["user_id"].nunique() > max_users:
        print(f"Subsampling {max_users} users deterministically (seed={seed}) ...")
        all_bench_users = np.array(sorted(bench_ratings["user_id"].unique()))
        rng = np.random.default_rng(seed)
        sampled_users = set(rng.choice(all_bench_users, size=max_users, replace=False))
        bench_ratings = bench_ratings[bench_ratings["user_id"].isin(sampled_users)].reset_index(drop=True)
        # Re-verify movie threshold after sampling
        bench_ratings, _ = iterative_k_core(bench_ratings, u_thresh, m_thresh)

    # 4. Filter movies to match benchmark movies
    bench_movie_ids = set(bench_ratings["movie_id"].unique())
    bench_movies = movies[movies["movie_id"].isin(bench_movie_ids)].copy().reset_index(drop=True)

    # 5. Filter tags and links if present
    bench_user_ids = set(bench_ratings["user_id"].unique())
    tags_path = full_dir / "tags.parquet"
    if tags_path.exists():
        tags = pd.read_parquet(tags_path)
        bench_tags = tags[tags["movie_id"].isin(bench_movie_ids) & tags["user_id"].isin(bench_user_ids)].reset_index(drop=True)
        bench_tags.to_parquet(benchmark_dir / "tags.parquet", index=False, engine="pyarrow", compression="snappy")
        print(f"  [+] Saved benchmark tags.parquet ({len(bench_tags):,} rows)")

    links_path = full_dir / "links.parquet"
    if links_path.exists():
        links = pd.read_parquet(links_path)
        bench_links = links[links["movie_id"].isin(bench_movie_ids)].reset_index(drop=True)
        bench_links.to_parquet(benchmark_dir / "links.parquet", index=False, engine="pyarrow", compression="snappy")
        print(f"  [+] Saved benchmark links.parquet ({len(bench_links):,} rows)")

    # 6. Save benchmark ratings & movies
    bench_ratings.to_parquet(benchmark_dir / "ratings.parquet", index=False, engine="pyarrow", compression="snappy")
    print(f"  [+] Saved benchmark ratings.parquet ({len(bench_ratings):,} rows)")
    bench_movies.to_parquet(benchmark_dir / "movies.parquet", index=False, engine="pyarrow", compression="snappy")
    print(f"  [+] Saved benchmark movies.parquet ({len(bench_movies):,} rows)")

    # 7. Compute & save benchmark summary statistics
    bench_stats = compute_catalog_statistics(bench_ratings, bench_movies, level_name="benchmark")
    bench_stats["filter_parameters"] = {
        "min_user_ratings": u_thresh,
        "min_movie_ratings": m_thresh,
        "benchmark_max_users": max_users,
        "seed": seed,
        "iterations_to_converge": iters,
        "is_provisional": True,
        "note": "Provisional threshold. Changing thresholds requires only editing datasets.yaml and rerunning build_benchmark.py.",
    }
    with open(benchmark_dir / "dataset_summary.json", "w", encoding="utf-8") as f:
        json.dump(bench_stats, f, indent=2)
    print(f"  [+] Saved benchmark dataset_summary.json")

    print(f"\nBenchmark successfully built under {benchmark_dir}:")
    print(f"  - Users:   {bench_stats['unique_users']:,}")
    print(f"  - Movies:  {bench_stats['total_movies']:,}")
    print(f"  - Ratings: {bench_stats['total_ratings']:,}")
    print(f"  - Density: {bench_stats['density']:.6f} | Sparsity: {bench_stats['sparsity']:.6f}")


def main():
    parser = argparse.ArgumentParser(description="Build activity-filtered benchmark subset using iterative k-core.")
    parser.add_argument(
        "--dataset",
        type=str,
        default="ml-25m",
        choices=["ml-25m", "ml-latest-small"],
        help="Dataset name configured in datasets.yaml (default: ml-25m)",
    )
    parser.add_argument(
        "--min-user-ratings",
        type=int,
        default=None,
        help="Override min_user_ratings from datasets.yaml",
    )
    parser.add_argument(
        "--min-movie-ratings",
        type=int,
        default=None,
        help="Override min_movie_ratings from datasets.yaml",
    )
    args = parser.parse_args()

    try:
        build_benchmark_subset(
            args.dataset,
            override_min_user=args.min_user_ratings,
            override_min_movie=args.min_movie_ratings,
        )
    except Exception as e:
        print(f"BUILD BENCHMARK ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
