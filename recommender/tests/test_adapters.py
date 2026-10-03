"""Unit tests for dataset adapters, year extraction, genres normalization, and schema casting."""

import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from recommender.preprocessing.adapters.csv_adapter import MovieLensCSVAdapter, YEAR_REGEX


def test_year_regex_patterns():
    """Verify year extraction across standard, noisy, and missing-year titles."""
    test_cases = [
        ("Toy Story (1995)", "Toy Story", 1995),
        ("Blade Runner 2049 (2017)", "Blade Runner 2049", 2017),
        ("One False Move (1992) ", "One False Move", 1992),
        ("Babylon 5: The Gathering (1993) (1998)", "Babylon 5: The Gathering (1993)", 1998),
        ("No Year Title", "No Year Title", None),
        ("Film Title (Unknown)", "Film Title (Unknown)", None),
        ("2001: A Space Odyssey (1968)", "2001: A Space Odyssey", 1968),
    ]

    for raw, expected_title, expected_year in test_cases:
        m = YEAR_REGEX.match(raw)
        if expected_year is not None:
            assert m is not None, f"Failed to match valid year in '{raw}'"
            assert m.group(1).strip() == expected_title
            assert int(m.group(2)) == expected_year
        else:
            assert m is None, f"Incorrectly matched year in '{raw}'"


def test_csv_adapter_parsing_with_mock_data():
    """Test MovieLensCSVAdapter against a mock MovieLens CSV directory structure."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_path = Path(tmp_dir)

        # Mock movies.csv
        movies_csv = (
            "movieId,title,genres\n"
            "1,Toy Story (1995),Adventure|Animation|Children\n"
            "2,Jumanji (1995),Adventure|Children|Fantasy\n"
            "3,Grumpier Old Men (1995),Comedy|Romance\n"
            "4,Waiting to Exhale (1995),Comedy|Drama|Romance\n"
            "5,Unknown Movie,(no genres listed)\n"
        )
        (raw_path / "movies.csv").write_text(movies_csv, encoding="utf-8")

        # Mock ratings.csv
        ratings_csv = (
            "userId,movieId,rating,timestamp\n"
            "1,1,4.0,964982703\n"
            "1,2,3.5,964982710\n"
            "2,1,5.0,964982720\n"
            "2,3,2.0,964982730\n"
            "3,4,4.5,964982740\n"
        )
        (raw_path / "ratings.csv").write_text(ratings_csv, encoding="utf-8")

        # Mock links.csv (with missing tmdbId)
        links_csv = (
            "movieId,imdbId,tmdbId\n"
            "1,0114709,862.0\n"
            "2,0113497,8844.0\n"
            "3,0113228,15602.0\n"
            "4,0114885,31357.0\n"
            "5,0114886,\n"
        )
        (raw_path / "links.csv").write_text(links_csv, encoding="utf-8")

        cfg = {
            "name": "test-mock",
            "files": {
                "ratings": "ratings.csv",
                "movies": "movies.csv",
                "tags": None,
                "links": "links.csv",
                "genome_scores": None,
                "genome_tags": None,
            },
            "has_tags": False,
            "has_links": True,
            "has_genome": False,
        }

        adapter = MovieLensCSVAdapter(cfg)
        norm = adapter.load_normalized(raw_path)

        # 1. Ratings dtypes & values
        assert norm.ratings["user_id"].dtype == "int32"
        assert norm.ratings["movie_id"].dtype == "int32"
        assert norm.ratings["rating"].dtype == "float32"
        assert norm.ratings["timestamp"].dtype == "int64"
        assert len(norm.ratings) == 5

        # 2. Movies normalization
        assert len(norm.movies) == 5
        m5 = norm.movies[norm.movies["movie_id"] == 5].iloc[0]
        assert m5["no_genres_flag"] == True
        assert m5["genres"] == []
        assert pd.isna(m5["year"])

        m1 = norm.movies[norm.movies["movie_id"] == 1].iloc[0]
        assert m1["title"] == "Toy Story"
        assert m1["year"] == 1995
        assert m1["genres"] == ["Adventure", "Animation", "Children"]
        assert m1["no_genres_flag"] == False

        # 3. Links nullable tmdb_id
        assert norm.links is not None
        assert norm.links["tmdb_id"].dtype == "Int32"
        l5 = norm.links[norm.links["movie_id"] == 5].iloc[0]
        assert pd.isna(l5["tmdb_id"])
        assert l5["tmdb_missing"] == True

        # 4. Check parsing metadata
        assert norm.parsing_metadata["tmdb_id_missing_count"] == 1
        assert norm.parsing_metadata["year_extraction_failures_count"] == 1
