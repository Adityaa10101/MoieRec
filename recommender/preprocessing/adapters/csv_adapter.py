"""CSV Adapter for GroupLens MovieLens datasets (ml-25m, ml-latest-small).

Ingests MovieLens CSV files with explicit compact dtypes (int32/float32) for memory efficiency.
Normalizes schemas, extracts release years with failure tracking, parses pipe-separated genres,
and handles nullable TMDB IDs.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from .base import BaseDatasetAdapter, NormalizedDataset

# Regular expression to extract trailing 4-digit release year in parentheses
# Handles optional trailing whitespace, e.g. "Toy Story (1995)" or "Film Title (2001) "
YEAR_REGEX = re.compile(r"^(.*?)\s*\((\d{4})\)\s*$")


class MovieLensCSVAdapter(BaseDatasetAdapter):
    """Adapter for parsing official GroupLens MovieLens CSV dumps."""

    def load_normalized(self, raw_data_dir: Path) -> NormalizedDataset:
        """Parse raw MovieLens CSV files into standardized NormalizedDataset."""
        files = self.config["files"]
        parsing_meta: Dict[str, Any] = {
            "dataset": self.dataset_name,
            "year_extraction_failures_count": 0,
            "year_extraction_failures_sample": [],
            "tmdb_id_missing_count": 0,
            "tmdb_id_missing_pct": 0.0,
            "no_genres_count": 0,
        }

        # 1. Parse ratings
        ratings_path = raw_data_dir / files["ratings"]
        if not ratings_path.exists():
            raise FileNotFoundError(f"Missing ratings file at: {ratings_path}")

        ratings_df = pd.read_csv(
            ratings_path,
            dtype={
                "userId": "int32",
                "movieId": "int32",
                "rating": "float32",
                "timestamp": "int64",
            },
            engine="c",
        ).rename(
            columns={
                "userId": "user_id",
                "movieId": "movie_id",
                "rating": "rating",
                "timestamp": "timestamp",
            }
        )

        # 2. Parse movies
        movies_path = raw_data_dir / files["movies"]
        if not movies_path.exists():
            raise FileNotFoundError(f"Missing movies file at: {movies_path}")

        raw_movies = pd.read_csv(
            movies_path,
            dtype={"movieId": "int32", "title": "string", "genres": "string"},
            engine="c",
        )

        movie_ids: List[int] = []
        titles: List[str] = []
        years: List[Optional[int]] = []
        genres_list: List[List[str]] = []
        no_genres_flags: List[bool] = []
        failures: List[Dict[str, Any]] = []

        for row in raw_movies.itertuples(index=False):
            m_id = int(row.movieId)
            raw_title = str(row.title) if pd.notna(row.title) else ""
            raw_gen = str(row.genres) if pd.notna(row.genres) else ""

            # Extract year from title
            match = YEAR_REGEX.match(raw_title)
            if match:
                clean_title = match.group(1).strip()
                extracted_year = int(match.group(2))
            else:
                clean_title = raw_title.strip()
                extracted_year = None
                failures.append({"movie_id": m_id, "raw_title": raw_title})

            # Extract genres
            if not raw_gen or raw_gen == "(no genres listed)":
                parsed_genres: List[str] = []
                no_gen = True
            else:
                parsed_genres = [g.strip() for g in raw_gen.split("|") if g.strip()]
                no_gen = len(parsed_genres) == 0

            movie_ids.append(m_id)
            titles.append(clean_title)
            years.append(extracted_year)
            genres_list.append(parsed_genres)
            no_genres_flags.append(no_gen)

        movies_df = pd.DataFrame({
            "movie_id": pd.Series(movie_ids, dtype="int32"),
            "title": pd.Series(titles, dtype="string"),
            "genres": pd.Series(genres_list, dtype="object"),
            "year": pd.Series(years, dtype="Int32"),
            "no_genres_flag": pd.Series(no_genres_flags, dtype="bool"),
            "raw_title": raw_movies["title"].astype("string"),
        })

        parsing_meta["year_extraction_failures_count"] = len(failures)
        parsing_meta["year_extraction_failures_sample"] = failures[:15]
        parsing_meta["no_genres_count"] = int(movies_df["no_genres_flag"].sum())

        # 3. Parse tags (if configured)
        tags_df = None
        if self.config.get("has_tags") and files.get("tags"):
            tags_path = raw_data_dir / files["tags"]
            if tags_path.exists():
                tags_df = pd.read_csv(
                    tags_path,
                    dtype={
                        "userId": "int32",
                        "movieId": "int32",
                        "tag": "string",
                        "timestamp": "int64",
                    },
                    engine="c",
                ).rename(
                    columns={
                        "userId": "user_id",
                        "movieId": "movie_id",
                        "tag": "tag",
                        "timestamp": "timestamp",
                    }
                )
                # Clean tag text: fill na, strip whitespace
                tags_df["tag"] = tags_df["tag"].fillna("").astype("string").str.strip()
                # Exclude completely empty tags
                tags_df = tags_df[tags_df["tag"].str.len() > 0].reset_index(drop=True)

        # 4. Parse links (if configured)
        links_df = None
        if self.config.get("has_links") and files.get("links"):
            links_path = raw_data_dir / files["links"]
            if links_path.exists():
                links_raw = pd.read_csv(
                    links_path,
                    dtype={"movieId": "int32", "imdbId": "string", "tmdbId": "float64"},
                    engine="c",
                )
                # Cast tmdbId to nullable Int32
                tmdb_missing = links_raw["tmdbId"].isna()
                missing_count = int(tmdb_missing.sum())
                total_links = len(links_raw)
                parsing_meta["tmdb_id_missing_count"] = missing_count
                parsing_meta["tmdb_id_missing_pct"] = (
                    round((missing_count / total_links) * 100, 2) if total_links else 0.0
                )

                links_df = pd.DataFrame({
                    "movie_id": links_raw["movieId"].astype("int32"),
                    "imdb_id": links_raw["imdbId"].astype("string"),
                    "tmdb_id": links_raw["tmdbId"].astype("Int32"),
                    "tmdb_missing": tmdb_missing.astype("bool"),
                })

        # 5. Parse genome (if configured)
        genome_scores_df = None
        genome_tags_df = None
        if self.config.get("has_genome"):
            g_scores_file = files.get("genome_scores")
            g_tags_file = files.get("genome_tags")
            if g_scores_file and (raw_data_dir / g_scores_file).exists():
                genome_scores_df = pd.read_csv(
                    raw_data_dir / g_scores_file,
                    dtype={
                        "movieId": "int32",
                        "tagId": "int32",
                        "relevance": "float32",
                    },
                    engine="c",
                ).rename(
                    columns={
                        "movieId": "movie_id",
                        "tagId": "tag_id",
                        "relevance": "relevance",
                    }
                )

            if g_tags_file and (raw_data_dir / g_tags_file).exists():
                genome_tags_df = pd.read_csv(
                    raw_data_dir / g_tags_file,
                    dtype={"tagId": "int32", "tag": "string"},
                    engine="c",
                ).rename(columns={"tagId": "tag_id", "tag": "tag"})

        return NormalizedDataset(
            dataset_name=self.dataset_name,
            ratings=ratings_df,
            movies=movies_df,
            tags=tags_df,
            links=links_df,
            genome_scores=genome_scores_df,
            genome_tags=genome_tags_df,
            parsing_metadata=parsing_meta,
        )
