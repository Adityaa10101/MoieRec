"""Validation suite for MovieLens datasets.

Verifies structural integrity, schema conformity, data boundaries, and foreign key relationships:
1. File existence and schema parsing.
2. Ratings range constraint [0.5, 5.0].
3. Timestamp validity (>= Jan 09, 1995 and not in future).
4. Uniqueness of (user_id, movie_id) rating pairs.
5. Referential integrity: all rated movie_ids exist in movies catalog.
6. Unique movie_ids in movies catalog.
7. Foreign keys for links, tags, and genome tables.
8. Genome catalog coverage (count and percentage of catalog).
9. Missing TMDB IDs count and percentage.
10. Year extraction failures.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from recommender.preprocessing.adapters.csv_adapter import MovieLensCSVAdapter
from recommender.preprocessing.utils import load_dataset_config


def validate_dataset(dataset_name: str) -> Dict[str, Any]:
    """Execute complete validation suite on normalized dataset tables."""
    cfg = load_dataset_config(dataset_name)
    extracted_dir = cfg["extracted_dir_abs"]

    if not extracted_dir.exists():
        raise FileNotFoundError(
            f"Extracted dataset directory not found at {extracted_dir}. "
            f"Run download_movielens.py --dataset {dataset_name} first."
        )

    print(f"Loading and validating dataset '{dataset_name}' from {extracted_dir} ...")
    adapter = MovieLensCSVAdapter(cfg)
    norm_data = adapter.load_normalized(extracted_dir)

    ratings = norm_data.ratings
    movies = norm_data.movies
    tags = norm_data.tags
    links = norm_data.links
    genome_scores = norm_data.genome_scores
    genome_tags = norm_data.genome_tags
    meta = norm_data.parsing_metadata or {}

    checks: Dict[str, Any] = {}
    errors: List[str] = []

    # 1. Row counts
    total_ratings = len(ratings)
    total_movies = len(movies)
    unique_users = ratings["user_id"].nunique()
    unique_rated_movies = ratings["movie_id"].nunique()

    checks["counts"] = {
        "ratings": total_ratings,
        "movies": total_movies,
        "users": unique_users,
        "unique_rated_movies": unique_rated_movies,
        "tags": len(tags) if tags is not None else 0,
        "links": len(links) if links is not None else 0,
        "genome_scores": len(genome_scores) if genome_scores is not None else 0,
        "genome_tags": len(genome_tags) if genome_tags is not None else 0,
    }

    # 2. Ratings range constraint
    min_rating = float(ratings["rating"].min())
    max_rating = float(ratings["rating"].max())
    valid_range = (min_rating >= 0.5) and (max_rating <= 5.0)
    checks["rating_range"] = {
        "min": min_rating,
        "max": max_rating,
        "valid": valid_range,
    }
    if not valid_range:
        errors.append(f"Ratings out of range [0.5, 5.0]: min={min_rating}, max={max_rating}")

    # 3. Timestamps validation
    min_ts = int(ratings["timestamp"].min())
    max_ts = int(ratings["timestamp"].max())
    # MovieLens ratings began Jan 09, 1995 (ts ~ 789148800)
    min_dt = datetime.fromtimestamp(min_ts, timezone.utc).isoformat()
    max_dt = datetime.fromtimestamp(max_ts, timezone.utc).isoformat()
    now_ts = int(datetime.now(timezone.utc).timestamp())
    valid_timestamps = (min_ts >= 780000000) and (max_ts <= now_ts)
    checks["timestamp_range"] = {
        "min_timestamp": min_ts,
        "max_timestamp": max_ts,
        "min_datetime_utc": min_dt,
        "max_datetime_utc": max_dt,
        "valid": valid_timestamps,
    }
    if not valid_timestamps:
        errors.append(f"Invalid timestamp range: {min_dt} to {max_dt}")

    # 4. Duplicate (user_id, movie_id) checks
    dup_count = int(ratings.duplicated(subset=["user_id", "movie_id"]).sum())
    checks["duplicate_ratings"] = {
        "count": dup_count,
        "valid": dup_count == 0,
    }
    if dup_count > 0:
        errors.append(f"Found {dup_count} duplicate (user_id, movie_id) rating records.")

    # 5. Movies uniqueness
    movie_id_dups = int(movies.duplicated(subset=["movie_id"]).sum())
    checks["movie_id_uniqueness"] = {
        "duplicate_movie_ids": movie_id_dups,
        "valid": movie_id_dups == 0,
    }
    if movie_id_dups > 0:
        errors.append(f"Found {movie_id_dups} duplicate movie_ids in movies catalog.")

    # 6. Referential integrity: all rated movie_ids must exist in movies catalog
    catalog_movie_ids = set(movies["movie_id"].unique())
    rated_movie_ids = set(ratings["movie_id"].unique())
    orphan_rated_movies = len(rated_movie_ids - catalog_movie_ids)
    checks["referential_integrity"] = {
        "orphan_rated_movies": orphan_rated_movies,
        "valid": orphan_rated_movies == 0,
    }
    if orphan_rated_movies > 0:
        errors.append(f"Found {orphan_rated_movies} rated movies missing from movies catalog.")

    # 7. Links foreign keys & TMDB ID coverage
    if links is not None:
        orphan_links = len(set(links["movie_id"].unique()) - catalog_movie_ids)
        missing_tmdb = int(links["tmdb_missing"].sum())
        tmdb_pct = round((missing_tmdb / len(links)) * 100, 2) if len(links) else 0.0
        checks["links_validation"] = {
            "orphan_link_movies": orphan_links,
            "missing_tmdb_ids": missing_tmdb,
            "missing_tmdb_pct": tmdb_pct,
            "valid": orphan_links == 0,
        }
        if orphan_links > 0:
            errors.append(f"Found {orphan_links} links with movie_ids not in catalog.")

    # 8. Tags foreign keys
    if tags is not None:
        orphan_tag_movies = len(set(tags["movie_id"].unique()) - catalog_movie_ids)
        checks["tags_validation"] = {
            "orphan_tag_movies": orphan_tag_movies,
            "unique_tags": int(tags["tag"].nunique()),
            "valid": orphan_tag_movies == 0,
        }
        if orphan_tag_movies > 0:
            errors.append(f"Found {orphan_tag_movies} tags referencing non-existent movie_ids.")

    # 9. Genome coverage
    if genome_scores is not None:
        genome_movies = set(genome_scores["movie_id"].unique())
        orphan_genome_movies = len(genome_movies - catalog_movie_ids)
        genome_coverage_count = len(genome_movies)
        genome_coverage_pct = round((genome_coverage_count / total_movies) * 100, 2) if total_movies else 0.0

        tag_ids_in_scores = set(genome_scores["tag_id"].unique())
        tag_ids_in_catalog = set(genome_tags["tag_id"].unique()) if genome_tags is not None else set()
        orphan_genome_tags = len(tag_ids_in_scores - tag_ids_in_catalog)

        checks["genome_coverage"] = {
            "movies_with_genome": genome_coverage_count,
            "total_movies": total_movies,
            "coverage_pct": genome_coverage_pct,
            "orphan_genome_movies": orphan_genome_movies,
            "orphan_genome_tags": orphan_genome_tags,
            "valid": orphan_genome_movies == 0 and orphan_genome_tags == 0,
        }
        if orphan_genome_movies > 0 or orphan_genome_tags > 0:
            errors.append(f"Genome foreign key mismatch: orphan_movies={orphan_genome_movies}, orphan_tags={orphan_genome_tags}")
    else:
        checks["genome_coverage"] = {
            "available": False,
            "note": "Genome not present in this dataset",
        }

    # 10. Year parsing failures & no-genres
    checks["metadata_parsing"] = {
        "year_extraction_failures": meta.get("year_extraction_failures_count", 0),
        "year_extraction_failures_pct": round(
            (meta.get("year_extraction_failures_count", 0) / total_movies) * 100, 2
        ) if total_movies else 0.0,
        "no_genres_count": meta.get("no_genres_count", 0),
        "no_genres_pct": round((meta.get("no_genres_count", 0) / total_movies) * 100, 2) if total_movies else 0.0,
    }

    report = {
        "dataset": dataset_name,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "passed": len(errors) == 0,
        "errors": errors,
        "checks": checks,
    }

    # Save validation report
    processed_dir = cfg["processed_dir_abs"]
    processed_dir.mkdir(parents=True, exist_ok=True)
    report_file = processed_dir / "validation_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


def print_report(report: Dict[str, Any]) -> None:
    """Print a clean formatted validation report."""
    print("=" * 60)
    print(f"MOIEREC VALIDATION REPORT — {report['dataset'].upper()}")
    print("=" * 60)
    print(f"Overall Status: {'PASSED' if report['passed'] else 'FAILED'}")
    if report["errors"]:
        print("\nERRORS ENCOUNTERED:")
        for err in report["errors"]:
            print(f"  [X] {err}")

    c = report["checks"]["counts"]
    print("\n[Record Counts]")
    print(f"  - Ratings:        {c['ratings']:,}")
    print(f"  - Movies:         {c['movies']:,}")
    print(f"  - Users:          {c['users']:,}")
    print(f"  - Rated Movies:   {c['unique_rated_movies']:,}")
    print(f"  - Tags:           {c['tags']:,}")
    print(f"  - Links:          {c['links']:,}")
    print(f"  - Genome Scores:  {c['genome_scores']:,}")
    print(f"  - Genome Tags:    {c['genome_tags']:,}")

    r = report["checks"]["rating_range"]
    print("\n[Ratings Range Integrity]")
    print(f"  - Min: {r['min']}, Max: {r['max']} (Valid [0.5, 5.0]: {r['valid']})")

    t = report["checks"]["timestamp_range"]
    print("\n[Timestamp Range]")
    print(f"  - Start: {t['min_datetime_utc']}")
    print(f"  - End:   {t['max_datetime_utc']}")
    print(f"  - Valid: {t['valid']}")

    dup = report["checks"]["duplicate_ratings"]
    print(f"\n[Duplicate Ratings]: {dup['count']} duplicates (Valid: {dup['valid']})")

    ref = report["checks"]["referential_integrity"]
    print(f"[Referential Integrity]: {ref['orphan_rated_movies']} orphan ratings (Valid: {ref['valid']})")

    if "links_validation" in report["checks"]:
        lk = report["checks"]["links_validation"]
        print(f"[Links Integrity]: Missing TMDB IDs = {lk['missing_tmdb_ids']:,} ({lk['missing_tmdb_pct']}%)")

    gc = report["checks"]["genome_coverage"]
    if gc.get("available") is not False:
        print(f"[Genome Coverage]: {gc['movies_with_genome']:,} of {gc['total_movies']:,} movies ({gc['coverage_pct']}%)")
    else:
        print(f"[Genome Coverage]: Not applicable ({gc.get('note')})")

    mp = report["checks"]["metadata_parsing"]
    print(f"[Metadata Parsing]: Year extraction failures = {mp['year_extraction_failures']} ({mp['year_extraction_failures_pct']}%)")
    print(f"                    No-genres listed = {mp['no_genres_count']} ({mp['no_genres_pct']}%)")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Validate normalized MovieLens dataset tables.")
    parser.add_argument(
        "--dataset",
        type=str,
        default="ml-25m",
        choices=["ml-25m", "ml-latest-small"],
        help="Dataset name configured in datasets.yaml (default: ml-25m)",
    )
    args = parser.parse_args()

    try:
        report = validate_dataset(args.dataset)
        print_report(report)
        if not report["passed"]:
            sys.exit(1)
    except Exception as e:
        print(f"VALIDATION CRITICAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
