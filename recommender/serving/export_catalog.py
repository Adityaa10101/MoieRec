#!/usr/bin/env python3
"""
recommender/serving/export_catalog.py
======================================
Exports a SQLite catalog (data/serving/catalog.sqlite) from existing
processed Parquet files. Uses ONLY:
  - data/processed/ml-25m/benchmark/movies.parquet
  - data/processed/ml-25m/benchmark/links.parquet
  - data/processed/ml-25m/splits/train_movie_stats.parquet

NEVER reads test.parquet or cold_final.

Run from the project root with the recommender venv:
    python -m recommender.serving.export_catalog
  or
    python recommender/serving/export_catalog.py
"""

import json
import re
import sqlite3
import unicodedata
from pathlib import Path
import argparse

import pandas as pd

from recommender.serving.normalize import make_title_display, normalize_for_search

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_BASE = PROJECT_ROOT / "data" / "processed" / "ml-25m"
BENCHMARK_DIR = DATA_BASE / "benchmark"
SPLITS_DIR = DATA_BASE / "splits"

MOVIES_PARQUET = BENCHMARK_DIR / "movies.parquet"
LINKS_PARQUET = BENCHMARK_DIR / "links.parquet"
STATS_PARQUET = SPLITS_DIR / "train_movie_stats.parquet"

OUTPUT_DIR = PROJECT_ROOT / "data" / "serving"
OUTPUT_DB = OUTPUT_DIR / "catalog.sqlite"

# Safety guard: never even import test.parquet
_FORBIDDEN = {"test.parquet", "cold_final"}


def _guard_forbidden() -> None:
    """Assert that none of the forbidden paths are referenced."""
    for f in _FORBIDDEN:
        assert f not in str(MOVIES_PARQUET), f"Forbidden: {f}"
        assert f not in str(LINKS_PARQUET), f"Forbidden: {f}"
        assert f not in str(STATS_PARQUET), f"Forbidden: {f}"


# ---------------------------------------------------------------------------
# Title display normalization
# ---------------------------------------------------------------------------
_TRAILING_ARTICLE_RE = re.compile(
    r"^(.+),\s+(The|A|An|Les|Le|La|Los|Las|Der|Die|Das|De|El|Il|L\')\s*(\(\d{4}\))?\s*$",
    re.IGNORECASE,
)
_AKA_RE = re.compile(r"\s*\(a\.k\.a\..+?\)", re.IGNORECASE)
_YEAR_SUFFIX_RE = re.compile(r"\s*\(\d{4}\)\s*$")


def make_title_display(raw_title: str) -> str:
    """
    Convert MovieLens raw title to display form:
      'Matrix, The (1999)'   -> 'The Matrix'
      'Grumpier Old Men (1995)' -> 'Grumpier Old Men'
      'Cry Freedom (a.k.a. A Dry White Season) (1987)' -> 'Cry Freedom'
    """
    title = str(raw_title).strip()
    # Remove (a.k.a. ...) parts first
    title = _AKA_RE.sub("", title).strip()
    # Move trailing article back to front
    m = _TRAILING_ARTICLE_RE.match(title)
    if m:
        base, article, year_part = m.group(1).strip(), m.group(2), m.group(3)
        title = f"{article} {base}"
    # Strip trailing year "(YYYY)"
    title = _YEAR_SUFFIX_RE.sub("", title).strip()
    return title


def normalize_for_search(title: str) -> str:
    """Lowercase + ASCII-fold (remove diacritics) for search index."""
    nfkd = unicodedata.normalize("NFKD", title.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# ---------------------------------------------------------------------------
# Main export
# ---------------------------------------------------------------------------

def export_catalog(output_db: Path = OUTPUT_DB) -> None:
    _guard_forbidden()

    output_db.parent.mkdir(parents=True, exist_ok=True)

    # --- Load Parquets ---
    print("Loading Parquets…")
    movies_df = pd.read_parquet(MOVIES_PARQUET)
    links_df = pd.read_parquet(LINKS_PARQUET)
    stats_df = pd.read_parquet(STATS_PARQUET)

    # Normalise column names from stats
    stats_df = stats_df.rename(columns={
        "rating_count": "train_rating_count",
        "positive_rating_count": "train_positive_count",
        "mean_rating": "train_mean_rating",
        "positive_ratio": "train_positive_ratio",
    })

    # --- Merge ---
    # movies LEFT JOIN links on movie_id
    df = movies_df.merge(links_df[["movie_id", "tmdb_id", "tmdb_missing"]], on="movie_id", how="left")
    # LEFT JOIN stats
    df = df.merge(stats_df[["movie_id", "train_rating_count", "train_positive_count",
                             "train_mean_rating", "train_positive_ratio"]],
                  on="movie_id", how="left")

    total_movies = len(df)

    # --- Year parse report ---
    year_failures = df["year"].isna().sum()
    print(f"  Total movies: {total_movies}")
    print(f"  Year parse failures: {year_failures}")

    # --- TMDB coverage ---
    no_tmdb = df["tmdb_id"].isna() | df["tmdb_missing"].fillna(False)
    no_tmdb_count = no_tmdb.sum()
    print(f"  Movies without tmdb_id: {no_tmdb_count} ({no_tmdb_count/total_movies*100:.2f}%)")

    # Impact on top-1000 by train_positive_count
    df_sorted = df.sort_values("train_positive_count", ascending=False, na_position="last")
    top1000 = df_sorted.head(1000)
    top1000_no_tmdb = (top1000["tmdb_id"].isna() | top1000["tmdb_missing"].fillna(False)).sum()
    print(f"  Top-1000 movies without tmdb_id: {top1000_no_tmdb}")

    # --- Exclude movies without tmdb_id from search/rows (per spec) ---
    # We still store them in the table (tmdb_id NULL) but note the exclusion
    df_export = df.copy()

    # --- Build display columns ---
    df_export["title_display"] = df_export["raw_title"].apply(make_title_display)
    df_export["title_search"] = df_export["title_display"].apply(normalize_for_search)

    # --- genres JSON ---
    def genres_to_json(g) -> str:
        if hasattr(g, "tolist"):
            return json.dumps(list(g.tolist()))
        if isinstance(g, (list, tuple)):
            return json.dumps(list(g))
        if isinstance(g, str):
            # pipe-separated fallback
            return json.dumps([x.strip() for x in g.split("|") if x.strip()])
        return "[]"

    df_export["genres_json"] = df_export["genres"].apply(genres_to_json)

    # --- tmdb_id: nullable int ---
    df_export["tmdb_id_int"] = pd.to_numeric(df_export["tmdb_id"], errors="coerce").astype("Int64")

    # --- Write SQLite ---
    print(f"Writing to {output_db}…")
    if output_db.exists():
        output_db.unlink()

    con = sqlite3.connect(output_db)
    cur = con.cursor()

    cur.executescript("""
        CREATE TABLE movies (
            movie_id             INTEGER PRIMARY KEY,
            tmdb_id              INTEGER,
            title_raw            TEXT    NOT NULL,
            title_display        TEXT    NOT NULL,
            title_search         TEXT    NOT NULL,
            year                 INTEGER,
            genres               TEXT    NOT NULL DEFAULT '[]',
            train_rating_count   INTEGER,
            train_positive_count INTEGER,
            train_positive_ratio REAL,
            train_mean_rating    REAL
        );

        CREATE INDEX idx_movies_tmdb_id     ON movies (tmdb_id);
        CREATE INDEX idx_movies_year        ON movies (year);
        CREATE INDEX idx_movies_title_search ON movies (title_search);
    """)

    rows = []
    for _, row in df_export.iterrows():
        tmdb_id_val = None if pd.isna(row["tmdb_id_int"]) else int(row["tmdb_id_int"])
        year_val = None if pd.isna(row["year"]) else int(row["year"])
        rows.append((
            int(row["movie_id"]),
            tmdb_id_val,
            str(row["raw_title"]),
            str(row["title_display"]),
            str(row["title_search"]),
            year_val,
            str(row["genres_json"]),
            int(row["train_rating_count"]) if pd.notna(row.get("train_rating_count")) else None,
            int(row["train_positive_count"]) if pd.notna(row.get("train_positive_count")) else None,
            float(row["train_positive_ratio"]) if pd.notna(row.get("train_positive_ratio")) else None,
            float(row["train_mean_rating"]) if pd.notna(row.get("train_mean_rating")) else None,
        ))

    cur.executemany(
        "INSERT INTO movies VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    con.commit()
    con.close()

    exported = len(rows)
    print("")
    print("[OK] Catalog export complete.")
    print(f"  Movies exported:           {exported}")
    print(f"  Movies without tmdb_id:    {no_tmdb_count} ({no_tmdb_count/total_movies*100:.2f}%)")
    print(f"  Year parse failures:        {year_failures}")
    print(f"  Top-1000 without tmdb_id:  {top1000_no_tmdb}")
    print(f"  Output:                    {output_db}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export MoieRec catalog to SQLite")
    parser.add_argument("--output", type=Path, default=OUTPUT_DB,
                        help="Path for output catalog.sqlite")
    args = parser.parse_args()
    export_catalog(args.output)
