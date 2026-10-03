"""Content feature extraction and index mapping generator.

Creates:
1. Stable, non-contiguous ID mappings under id_mappings/:
   - movie_id <-> full_idx
   - movie_id <-> benchmark_idx
   - user_id <-> benchmark_idx
2. Tier 1 Baseline Features (Main Evaluation):
   - Multi-hot genres + normalized release year / missing flag.
   - Sparse scipy csr_matrix (tier1_baseline_features.npz).
3. Tier 2 Enhanced Snapshot Features (Separate Experiment):
   - (a) Tag TF-IDF from tags.csv (tier2_tag_tfidf.npz).
   - (b) Tag Genome matrix with explicit coverage mask (tier2_genome_matrix.npy, tier2_genome_mask.npy).
   - Documented snapshot temporal leakage caveat.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

from recommender.preprocessing.utils import load_dataset_config


def build_id_mappings(
    full_movies: pd.DataFrame,
    benchmark_movies: pd.DataFrame,
    benchmark_ratings: pd.DataFrame,
    output_dir: Path,
) -> Dict[str, Any]:
    """Create and persist stable two-way index mappings."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Full catalog movie mappings
    full_movie_ids = np.sort(full_movies["movie_id"].unique())
    full_m2i = pd.DataFrame({"movie_id": full_movie_ids, "full_idx": np.arange(len(full_movie_ids), dtype="int32")})
    full_m2i.to_parquet(output_dir / "movie_id_to_full_idx.parquet", index=False)
    full_m2i.rename(columns={"movie_id": "original_id", "full_idx": "internal_idx"}).to_parquet(
        output_dir / "full_idx_to_movie_id.parquet", index=False
    )

    # 2. Benchmark movie mappings
    bench_movie_ids = np.sort(benchmark_movies["movie_id"].unique())
    bench_m2i = pd.DataFrame({"movie_id": bench_movie_ids, "benchmark_idx": np.arange(len(bench_movie_ids), dtype="int32")})
    bench_m2i.to_parquet(output_dir / "movie_id_to_benchmark_idx.parquet", index=False)
    bench_m2i.rename(columns={"movie_id": "original_id", "benchmark_idx": "internal_idx"}).to_parquet(
        output_dir / "benchmark_idx_to_movie_id.parquet", index=False
    )

    # 3. Benchmark user mappings
    bench_user_ids = np.sort(benchmark_ratings["user_id"].unique())
    bench_u2i = pd.DataFrame({"user_id": bench_user_ids, "benchmark_idx": np.arange(len(bench_user_ids), dtype="int32")})
    bench_u2i.to_parquet(output_dir / "user_id_to_benchmark_idx.parquet", index=False)
    bench_u2i.rename(columns={"user_id": "original_id", "benchmark_idx": "internal_idx"}).to_parquet(
        output_dir / "benchmark_idx_to_user_id.parquet", index=False
    )

    meta = {
        "full_catalog_movies": len(full_movie_ids),
        "benchmark_movies": len(bench_movie_ids),
        "benchmark_users": len(bench_user_ids),
    }
    return meta


def build_tier1_baseline(
    benchmark_movies: pd.DataFrame, output_dir: Path
) -> Tuple[sparse.csr_matrix, List[str], Dict[str, Any]]:
    """Build Tier 1 sparse baseline features: Multi-hot genres + normalized release year."""
    # Ensure ordered by benchmark_idx (sorted movie_id)
    sorted_movies = benchmark_movies.sort_values(by="movie_id").reset_index(drop=True)
    n_movies = len(sorted_movies)

    # 1. Multi-hot genres
    all_genres = set()
    for g_list in sorted_movies["genres"]:
        if isinstance(g_list, (list, np.ndarray)):
            all_genres.update(g_list)
    genre_vocab = sorted(list(all_genres))
    genre_to_idx = {g: i for i, g in enumerate(genre_vocab)}

    row_ind, col_ind = [], []
    for row_i, g_list in enumerate(sorted_movies["genres"]):
        if isinstance(g_list, (list, np.ndarray)):
            for g in g_list:
                if g in genre_to_idx:
                    row_ind.append(row_i)
                    col_ind.append(genre_to_idx[g])

    genres_data = np.ones(len(row_ind), dtype="float32")
    genres_sparse = sparse.csr_matrix((genres_data, (row_ind, col_ind)), shape=(n_movies, len(genre_vocab)), dtype="float32")

    # 2. Normalized year & missing indicator
    years = sorted_movies["year"].to_numpy(dtype="float32", na_value=np.nan)
    has_year = ~np.isnan(years)
    valid_years = years[has_year]

    if len(valid_years) > 0:
        min_y = float(valid_years.min())
        max_y = float(valid_years.max())
        y_range = max_y - min_y if max_y > min_y else 1.0
        norm_years = np.where(has_year, (years - min_y) / y_range, 0.0).astype("float32")
    else:
        min_y, max_y = 1900.0, 2020.0
        norm_years = np.zeros(n_movies, dtype="float32")

    missing_year_flag = (~has_year).astype("float32")

    year_features = np.column_stack([norm_years, missing_year_flag])
    year_sparse = sparse.csr_matrix(year_features, dtype="float32")

    # Combine into unified Tier 1 matrix
    tier1_matrix = sparse.hstack([genres_sparse, year_sparse], format="csr", dtype="float32")

    feature_names = [f"genre:{g}" for g in genre_vocab] + ["norm_year", "missing_year_flag"]

    # Save to disk
    sparse.save_npz(output_dir / "tier1_baseline_features.npz", tier1_matrix)

    meta = {
        "n_samples": tier1_matrix.shape[0],
        "n_features": tier1_matrix.shape[1],
        "n_genres": len(genre_vocab),
        "genres": genre_vocab,
        "year_min": min_y,
        "year_max": max_y,
        "movies_missing_year": int((~has_year).sum()),
        "sparsity": round(1.0 - (tier1_matrix.nnz / (tier1_matrix.shape[0] * tier1_matrix.shape[1])), 6),
    }
    return tier1_matrix, feature_names, meta


def build_tier2_enhanced(
    benchmark_movies: pd.DataFrame,
    benchmark_tags: pd.DataFrame,
    full_genome_scores: pd.DataFrame,
    full_genome_tags: pd.DataFrame,
    output_dir: Path,
) -> Dict[str, Any]:
    """Build Tier 2 Enhanced Snapshot features: Tag TF-IDF & Tag Genome with coverage mask."""
    sorted_movies = benchmark_movies.sort_values(by="movie_id").reset_index(drop=True)
    n_movies = len(sorted_movies)
    movie_id_list = sorted_movies["movie_id"].to_numpy()
    m2idx = {mid: i for i, mid in enumerate(movie_id_list)}

    tier2_meta: Dict[str, Any] = {
        "tag_tfidf_available": False,
        "genome_available": False,
        "snapshot_leakage_warning": (
            "CRITICAL TEMPORAL LEAKAGE NOTICE: Tier 2 features (Tags and Tag Genome) were aggregated "
            "over the entire history up to November 2019. Because user tags and genome scores encapsulate "
            "future post-release information, Tier 2 features leak semantic signals across chronological splits. "
            "They must be evaluated in a separate experiment labeled 'Snapshot Features' with this limitation stated."
        ),
    }

    # 1. Cleaned Tag TF-IDF
    if benchmark_tags is not None and len(benchmark_tags) > 0:
        print("  -> Computing Tag TF-IDF from tags.csv (min_df=2, sublinear_tf=True) ...")
        # Aggregate tags per movie into a single document
        clean_tags = benchmark_tags.dropna(subset=["tag"]).copy()
        clean_tags["clean_tag"] = clean_tags["tag"].astype(str).str.lower().str.replace(r"[^\w\s-]", "", regex=True).str.strip()
        tags_per_movie = clean_tags.groupby("movie_id")["clean_tag"].apply(lambda s: " ".join(s)).to_dict()

        documents = [tags_per_movie.get(mid, "") for mid in movie_id_list]
        movies_with_tags = sum(1 for d in documents if len(d) > 0)

        vectorizer = TfidfVectorizer(
            lowercase=True,
            min_df=2,
            max_df=0.7,
            sublinear_tf=True,
            token_pattern=r"(?u)\b\w[\w-]+\b",
        )
        tfidf_matrix = vectorizer.fit_transform(documents)
        sparse.save_npz(output_dir / "tier2_tag_tfidf.npz", tfidf_matrix)

        tier2_meta["tag_tfidf_available"] = True
        tier2_meta["tag_tfidf"] = {
            "n_samples": tfidf_matrix.shape[0],
            "n_features": tfidf_matrix.shape[1],
            "movies_with_tags": movies_with_tags,
            "movies_with_tags_pct": round((movies_with_tags / n_movies) * 100, 2),
            "vocabulary_size": len(vectorizer.vocabulary_),
        }
        print(f"     [+] Tag TF-IDF Matrix: {tfidf_matrix.shape} ({movies_with_tags:,} movies with tags)")

    # 2. Tag Genome Matrix + Explicit Coverage Mask
    if full_genome_scores is not None and full_genome_tags is not None:
        print("  -> Compiling Tag Genome matrix with explicit coverage mask ...")
        tag_ids = np.sort(full_genome_tags["tag_id"].unique())
        n_tags = len(tag_ids)
        t2idx = {tid: i for i, tid in enumerate(tag_ids)}

        # Filter genome scores to benchmark movies
        bench_scores = full_genome_scores[full_genome_scores["movie_id"].isin(set(movie_id_list))].copy()
        movies_with_genome = set(bench_scores["movie_id"].unique())

        genome_matrix = np.zeros((n_movies, n_tags), dtype="float32")
        coverage_mask = np.zeros(n_movies, dtype=bool)

        for row in bench_scores.itertuples(index=False):
            m_idx = m2idx.get(row.movie_id)
            t_idx = t2idx.get(row.tag_id)
            if m_idx is not None and t_idx is not None:
                genome_matrix[m_idx, t_idx] = float(row.relevance)
                coverage_mask[m_idx] = True

        # Save dense numpy array & coverage mask
        np.save(output_dir / "tier2_genome_matrix.npy", genome_matrix)
        np.save(output_dir / "tier2_genome_mask.npy", coverage_mask)

        tier2_meta["genome_available"] = True
        tier2_meta["genome"] = {
            "n_samples": n_movies,
            "n_genome_tags": n_tags,
            "movies_with_genome": int(coverage_mask.sum()),
            "genome_coverage_pct": round((int(coverage_mask.sum()) / n_movies) * 100, 2),
            "no_imputation_rule": "Missing movies flagged via tier2_genome_mask.npy without synthetic value imputation.",
        }
        print(f"     [+] Tag Genome Matrix: {genome_matrix.shape} (Coverage: {coverage_mask.sum():,}/{n_movies:,} = {tier2_meta['genome']['genome_coverage_pct']}%)")
    else:
        tier2_meta["genome_available"] = False
        print("  -> Genome data not available in this dataset. Skipping Tier 2 Genome.")

    return tier2_meta


def build_features(dataset_name: str) -> None:
    """Build index mappings, Tier 1 baseline, and Tier 2 enhanced features."""
    t0 = time.time()
    cfg = load_dataset_config(dataset_name)
    processed_dir = cfg["processed_dir_abs"]
    full_dir = processed_dir / "full"
    benchmark_dir = processed_dir / "benchmark"
    id_dir = processed_dir / "id_mappings"
    feat_dir = processed_dir / "features"
    id_dir.mkdir(parents=True, exist_ok=True)
    feat_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Building Content Features: {dataset_name} ===")

    full_movies = pd.read_parquet(full_dir / "movies.parquet")
    bench_movies = pd.read_parquet(benchmark_dir / "movies.parquet")
    bench_ratings = pd.read_parquet(benchmark_dir / "ratings.parquet")

    # 1. ID Mappings
    print("\n1. Generating stable ID mappings under id_mappings/ ...")
    id_meta = build_id_mappings(full_movies, bench_movies, bench_ratings, id_dir)
    print(f"  [+] ID Mappings: {id_meta['full_catalog_movies']:,} full movies, {id_meta['benchmark_movies']:,} benchmark movies, {id_meta['benchmark_users']:,} benchmark users")

    # 2. Tier 1 Baseline
    print("\n2. Building Tier 1 Baseline Features (Genres + Normalized Year) ...")
    tier1_mat, feat_names, tier1_meta = build_tier1_baseline(bench_movies, feat_dir)
    print(f"  [+] Tier 1 Baseline Matrix: {tier1_mat.shape} (Sparse CSR, {tier1_mat.nnz:,} non-zeros)")

    # 3. Tier 2 Enhanced (Snapshot)
    print("\n3. Building Tier 2 Enhanced Features (Snapshot Tag TF-IDF & Genome) ...")
    tags_path = benchmark_dir / "tags.parquet"
    bench_tags = pd.read_parquet(tags_path) if tags_path.exists() else None

    g_scores_path = full_dir / "genome_scores.parquet"
    g_tags_path = full_dir / "genome_tags.parquet"
    full_genome_scores = pd.read_parquet(g_scores_path) if g_scores_path.exists() else None
    full_genome_tags = pd.read_parquet(g_tags_path) if g_tags_path.exists() else None

    tier2_meta = build_tier2_enhanced(bench_movies, bench_tags, full_genome_scores, full_genome_tags, feat_dir)

    # Save feature metadata
    metadata = {
        "dataset": dataset_name,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "id_mappings": id_meta,
        "tier1_baseline": {
            **tier1_meta,
            "feature_names": feat_names,
        },
        "tier2_enhanced": tier2_meta,
    }

    meta_file = feat_dir / "feature_metadata.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"\n[+] Feature metadata saved at: {meta_file}")

    print("\n" + "=" * 60)
    print("FEATURE DIMENSIONALITIES SUMMARY")
    print("=" * 60)
    print(f"Tier 1 Baseline Sparse Matrix:  {tier1_mat.shape[0]:,} movies x {tier1_mat.shape[1]:,} features")
    if tier2_meta["tag_tfidf_available"]:
        t_meta = tier2_meta["tag_tfidf"]
        print(f"Tier 2 Tag TF-IDF Sparse Matrix: {t_meta['n_samples']:,} movies x {t_meta['n_features']:,} terms")
    if tier2_meta["genome_available"]:
        g_meta = tier2_meta["genome"]
        print(f"Tier 2 Genome Dense Matrix:     {g_meta['n_samples']:,} movies x {g_meta['n_genome_tags']:,} tag dimensions")
    print("=" * 60)
    print(f"Pipeline completed in {time.time() - t0:.2f} seconds.")


def main():
    parser = argparse.ArgumentParser(description="Build stable ID mappings and content features.")
    parser.add_argument(
        "--dataset",
        type=str,
        default="ml-25m",
        choices=["ml-25m", "ml-latest-small"],
        help="Dataset name configured in datasets.yaml (default: ml-25m)",
    )
    args = parser.parse_args()

    try:
        build_features(args.dataset)
    except Exception as e:
        print(f"FEATURE EXTRACTION ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
