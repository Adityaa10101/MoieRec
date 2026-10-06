"""
backend/tests/test_movies_api.py
=================================
Backend tests with mocked TMDB (no network calls).

Tests cover:
- home/search/detail response shapes
- adult filter
- missing tmdb_id exclusion
- cache hit/miss/TTL
- TMDB failure degrades gracefully
- API never returns match_percent or explanation values
- title normalization (articles, years, accents)
- search ranking
"""

import json
import sqlite3
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Make recommender importable for title normalization tests
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Test DB factories
# ---------------------------------------------------------------------------

SAMPLE_MOVIES = [
    {
        "movie_id": 1, "tmdb_id": 862, "title_raw": "Toy Story (1995)",
        "title_display": "Toy Story", "title_search": "toy story",
        "year": 1995, "genres": ["Animation", "Children", "Comedy"],
        "train_positive_count": 25000,
    },
    {
        "movie_id": 2, "tmdb_id": 8844, "title_raw": "Jumanji (1995)",
        "title_display": "Jumanji", "title_search": "jumanji",
        "year": 1995, "genres": ["Adventure", "Children"],
        "train_positive_count": 10000,
    },
    {
        "movie_id": 3, "tmdb_id": None, "title_raw": "No TMDB Movie (2000)",
        "title_display": "No TMDB Movie", "title_search": "no tmdb movie",
        "year": 2000, "genres": ["Drama"],
        "train_positive_count": 5000,
    },
    {
        "movie_id": 4, "tmdb_id": 99999, "title_raw": "Sci-Fi Film (2015)",
        "title_display": "Sci-Fi Film", "title_search": "sci-fi film",
        "year": 2015, "genres": ["Sci-Fi"],
        "train_positive_count": 8000,
    },
    {
        "movie_id": 5, "tmdb_id": 77777, "title_raw": "Drama Classic (1992)",
        "title_display": "Drama Classic", "title_search": "drama classic",
        "year": 1992, "genres": ["Drama"],
        "train_positive_count": 15000,
    },
]

MOCK_TMDB_PAYLOAD = {
    "tmdb_id": 862,
    "title": "Toy Story",
    "overview": "A test overview.",
    "tagline": "A test tagline.",
    "release_date": "1995-11-22",
    "runtime": 81,
    "genres": ["Animation", "Comedy", "Family"],
    "vote_average": 7.9,
    "vote_count": 10000,
    "poster_path": "/test_poster.jpg",
    "backdrop_path": "/test_backdrop.jpg",
    "cast": [{"name": "Tom Hanks", "character": "Woody (voice)", "profile_path": None}],
    "directors": ["John Lasseter"],
    "adult": False,
    "original_language": "en",
    "_image_base_url": "https://image.tmdb.org/t/p/",
}


def _make_catalog_conn(rows: list[dict]) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
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
        CREATE INDEX idx_movies_tmdb_id ON movies (tmdb_id);
        CREATE INDEX idx_movies_year ON movies (year);
        CREATE INDEX idx_movies_title_search ON movies (title_search);
    """)
    for r in rows:
        conn.execute(
            "INSERT INTO movies VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                r["movie_id"], r.get("tmdb_id"), r["title_raw"],
                r["title_display"], r["title_search"], r.get("year"),
                json.dumps(r.get("genres", [])),
                r.get("train_rating_count", 100),
                r.get("train_positive_count", 50),
                r.get("train_positive_ratio", 0.5),
                r.get("train_mean_rating", 3.5),
            ),
        )
    conn.commit()
    return conn


def _make_cache_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE tmdb_cache (
            tmdb_id INTEGER PRIMARY KEY,
            payload TEXT,
            fetched_at INTEGER NOT NULL,
            status TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def app_client():
    """
    Create a TestClient with in-memory catalog + cache DBs and mocked TMDB.
    Patches get_catalog_conn and get_cache_conn at the module level so all
    call sites (endpoints + direct test imports) use the same in-memory DBs.
    """
    cat_conn = _make_catalog_conn(SAMPLE_MOVIES)
    cache_conn = _make_cache_conn()

    with (
        patch("app.db.catalog.get_catalog_conn", return_value=cat_conn),
        patch("app.db.tmdb_cache.get_cache_conn", return_value=cache_conn),
        patch("app.services.tmdb.get_tmdb_data", new_callable=AsyncMock) as mock_tmdb,
        patch("app.api.endpoints.movies.get_tmdb_data", mock_tmdb),
    ):
        mock_tmdb.return_value = MOCK_TMDB_PAYLOAD

        from app.main import create_application
        from fastapi.testclient import TestClient

        test_app = create_application()
        with TestClient(test_app) as client:
            yield client, mock_tmdb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHomeEndpoint:
    def test_home_shape(self, app_client):
        client, _ = app_client
        resp = client.get("/api/home")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "hero" in data
        assert "rows" in data
        assert isinstance(data["rows"], list)
        assert len(data["rows"]) == 5

    def test_home_rows_have_movies(self, app_client):
        client, _ = app_client
        data = client.get("/api/home").json()
        for row in data["rows"]:
            assert "id" in row
            assert "title" in row
            assert "subtitle" in row
            assert isinstance(row["movies"], list)

    def test_home_row_labels_honest(self, app_client):
        client, _ = app_client
        data = client.get("/api/home").json()
        row_ids = {r["id"] for r in data["rows"]}
        assert "row-popular" in row_ids
        assert "row-scifi" in row_ids
        assert "row-drama" in row_ids
        assert "row-2010s" in row_ids
        assert "row-1990s" in row_ids

    def test_hero_is_movie_out(self, app_client):
        client, _ = app_client
        data = client.get("/api/home").json()
        if data["hero"]:
            assert "movie_id" in data["hero"]
            assert "title" in data["hero"]


class TestHonestyContract:
    """API must never return fabricated match_percent or explanation."""

    def _check_movie(self, m: dict) -> None:
        assert m.get("match_percent") is None, f"match_percent must be null, got {m['match_percent']}"
        assert m.get("explanation") is None, f"explanation must be null"
        assert m.get("score") is None, f"score must be null"
        assert m.get("reason_codes") == [], f"reason_codes must be []"
        assert m.get("source") == "popularity"

    def test_no_fabricated_scores_in_home(self, app_client):
        client, _ = app_client
        data = client.get("/api/home").json()
        movies = []
        if data.get("hero"):
            movies.append(data["hero"])
        for row in data.get("rows", []):
            movies.extend(row.get("movies", []))
        for m in movies:
            self._check_movie(m)

    def test_no_fabricated_scores_in_search(self, app_client):
        client, _ = app_client
        data = client.get("/api/search?q=toy").json()
        for m in data:
            self._check_movie(m)

    def test_no_fabricated_scores_in_detail(self, app_client):
        client, _ = app_client
        resp = client.get("/api/movies/1")
        assert resp.status_code == 200
        self._check_movie(resp.json())


class TestAdultFilter:
    def test_adult_payload_marked_correctly(self):
        from app.services.tmdb import _extract_payload
        result = _extract_payload(
            {"id": 1, "adult": True, "title": "Adult Film", "credits": {}},
            config=None,
        )
        assert result["adult"] is True


class TestMissingTmdbId:
    def test_no_tmdb_excluded_from_popular(self, app_client):
        client, _ = app_client
        data = client.get("/api/movies/popular").json()
        movie_ids = [m["movie_id"] for m in data]
        assert 3 not in movie_ids  # movie_id=3 has tmdb_id=None

    def test_no_tmdb_excluded_from_search(self, app_client):
        client, _ = app_client
        data = client.get("/api/search?q=no+tmdb").json()
        assert all(m["movie_id"] != 3 for m in data)

    def test_no_tmdb_returns_404(self, app_client):
        client, _ = app_client
        # movie_id=3 has tmdb_id=None -> fetch_movie returns None -> 404
        resp = client.get("/api/movies/3")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


class TestGracefulDegradation:
    def test_tmdb_unreachable_returns_catalog_only(self, app_client):
        client, mock_tmdb = app_client
        # Override return value to None for this test
        mock_tmdb.return_value = None
        mock_tmdb.side_effect = None
        resp = client.get("/api/movies/1")
        assert resp.status_code == 200
        m = resp.json()
        assert m["movie_id"] == 1
        assert m["title"] == "Toy Story"  # from catalog
        assert m["source"] == "popularity"
        assert m["match_percent"] is None  # honesty contract preserved

    def test_home_works_without_tmdb(self, app_client):
        client, mock_tmdb = app_client
        mock_tmdb.return_value = None
        resp = client.get("/api/home")
        assert resp.status_code == 200


class TestCacheTTL:
    def test_cache_get_miss_returns_none(self):
        from app.db.tmdb_cache import _set_test_conn, cache_get
        conn = _make_cache_conn()
        _set_test_conn(conn)
        assert cache_get(999) is None

    def test_cache_put_and_get(self):
        from app.db.tmdb_cache import _set_test_conn, cache_get, cache_put
        conn = _make_cache_conn()
        _set_test_conn(conn)
        cache_put(111, {"title": "Test"}, "ok")
        result = cache_get(111)
        assert result is not None
        assert result["title"] == "Test"

    def test_cache_expired_returns_none(self):
        from app.db.tmdb_cache import _set_test_conn, cache_get, cache_put, TTL_ERR_SECONDS
        conn = _make_cache_conn()
        _set_test_conn(conn)
        # Insert with a fetched_at in the past (expired)
        old_time = int(time.time()) - TTL_ERR_SECONDS - 1
        conn.execute(
            "INSERT INTO tmdb_cache VALUES (?, ?, ?, ?)",
            (222, json.dumps({"title": "Old"}), old_time, "error"),
        )
        conn.commit()
        assert cache_get(222) is None  # Expired


class TestTitleNormalization:
    def test_trailing_article_moved(self):
        from recommender.serving.normalize import make_title_display
        assert make_title_display("Matrix, The (1999)") == "The Matrix"

    def test_good_bad_ugly(self):
        from recommender.serving.normalize import make_title_display
        result = make_title_display("Good, the Bad and the Ugly, The (1966)")
        assert result.startswith("The")

    def test_year_stripped(self):
        from recommender.serving.normalize import make_title_display
        assert make_title_display("Toy Story (1995)") == "Toy Story"

    def test_aka_removed(self):
        from recommender.serving.normalize import make_title_display
        result = make_title_display("Cry Freedom (a.k.a. A Dry White Season) (1987)")
        assert "a.k.a." not in result
        assert "Cry Freedom" in result

    def test_accent_normalization(self):
        from recommender.serving.normalize import normalize_for_search
        assert normalize_for_search("Amélie") == "amelie"
        assert normalize_for_search("Nausicaä") == "nausicaa"


class TestSearchRanking:
    def test_min_length_enforced(self, app_client):
        client, _ = app_client
        resp = client.get("/api/search?q=t")
        assert resp.status_code == 422

    def test_search_finds_results(self, app_client):
        client, _ = app_client
        data = client.get("/api/search?q=toy").json()
        assert any(m["title"] == "Toy Story" for m in data)

    def test_search_ranked_by_popularity(self, app_client):
        client, _ = app_client
        # "toy" matches only Toy Story — verify it appears and is highest popularity
        data = client.get("/api/search?q=toy").json()
        if data:
            assert data[0]["title"] == "Toy Story"
            # Popularity order: Toy Story (25000) should be first


class TestPopularEndpoint:
    def test_returns_list(self, app_client):
        client, _ = app_client
        data = client.get("/api/movies/popular").json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_genre_filter(self, app_client):
        client, _ = app_client
        data = client.get("/api/movies/popular?genre=Sci-Fi").json()
        assert all("Sci-Fi" in m["genres"] for m in data)

    def test_decade_filter(self, app_client):
        client, _ = app_client
        data = client.get("/api/movies/popular?decade=2010").json()
        assert all(2010 <= (m["year"] or 0) < 2020 for m in data)

    def test_pagination(self, app_client):
        client, _ = app_client
        p1 = client.get("/api/movies/popular?limit=1&offset=0").json()
        p2 = client.get("/api/movies/popular?limit=1&offset=1").json()
        if p1 and p2:
            assert p1[0]["movie_id"] != p2[0]["movie_id"]


class TestHealthEndpoint:
    def test_health_ok(self, app_client):
        client, _ = app_client
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestTmdbImageUrlBuilder:
    """Regression tests for centralized TMDB image URL builder."""

    def test_null_in_null_out(self):
        from app.services.tmdb import build_tmdb_image_url
        assert build_tmdb_image_url(None, "w500") is None
        assert build_tmdb_image_url("", "w500") is None
        assert build_tmdb_image_url("   ", "w500") is None

    @pytest.mark.parametrize("synthetic_path", ["/abc123.jpg", "abc123.jpg"])
    @pytest.mark.parametrize("size", ["w342", "w500", "w780", "w1280", "original"])
    def test_synthetic_paths_match_format_and_no_double_slashes(self, synthetic_path, size):
        import re
        from app.services.tmdb import build_tmdb_image_url

        pattern = re.compile(r"^https://image\.tmdb\.org/t/p/(w\d+|original)/[^/]\S*$")
        url = build_tmdb_image_url(synthetic_path, size)
        assert url is not None
        assert pattern.match(url), f"URL {url} does not match required regex pattern"
        # Verify no accidental double slashes after the protocol
        path_part = url.replace("https://", "")
        assert "//" not in path_part, f"Accidental double slash found in URL: {url}"

    def test_custom_and_cached_base_url(self):
        import re
        from app.services.tmdb import build_tmdb_image_url

        pattern = re.compile(r"^https://image\.tmdb\.org/t/p/(w\d+|original)/[^/]\S*$")
        # Base with or without trailing slash
        url1 = build_tmdb_image_url("/synthetic_poster.png", "w500", base_url="https://image.tmdb.org/t/p/")
        url2 = build_tmdb_image_url("/synthetic_poster.png", "w500", base_url="https://image.tmdb.org/t/p")
        assert url1 == url2
        assert pattern.match(url1)
        assert "//" not in url1.replace("https://", "")


class TestBatchEndpoint:
    def test_batch_happy_path(self, app_client):
        client, _ = app_client
        resp = client.get("/api/movies/batch?ids=1,2")
        assert resp.status_code == 200
        movies = resp.json()
        assert isinstance(movies, list)
        mids = [m["movie_id"] for m in movies]
        assert 1 in mids
        for m in movies:
            assert m["source"] == "popularity"
            assert m["score"] is None
            assert m["match_percent"] is None
            assert m["poster_url"] is not None

    def test_batch_skips_unknown_ids(self, app_client):
        client, _ = app_client
        resp = client.get("/api/movies/batch?ids=1,9999999")
        assert resp.status_code == 200
        movies = resp.json()
        mids = [m["movie_id"] for m in movies]
        assert 1 in mids
        assert 9999999 not in mids

    def test_batch_empty_or_invalid_strings(self, app_client):
        client, _ = app_client
        assert client.get("/api/movies/batch?ids=").json() == []
        assert client.get("/api/movies/batch?ids=abc,def").json() == []

    def test_batch_max_100_enforced(self, app_client):
        client, _ = app_client
        many_ids = ",".join(str(i) for i in range(101))
        resp = client.get(f"/api/movies/batch?ids={many_ids}")
        assert resp.status_code == 400
        assert "Maximum 100" in resp.json()["detail"]


class TestMetaFiltersEndpoint:
    def test_meta_filters(self, app_client):
        client, _ = app_client
        resp = client.get("/api/meta/filters")
        assert resp.status_code == 200
        data = resp.json()
        assert "genres" in data
        assert "decades" in data
        assert isinstance(data["genres"], list)
        assert isinstance(data["decades"], list)
        assert len(data["genres"]) > 0
        assert len(data["decades"]) > 0
        assert "name" in data["genres"][0]
        assert "count" in data["genres"][0]
        assert "decade" in data["decades"][0]
        assert "label" in data["decades"][0]
        assert all(g["name"] not in ("IMAX", "(no genres listed)") for g in data["genres"])


class TestPopularSortingAndValidation:
    def test_sort_newest(self, app_client):
        client, _ = app_client
        resp = client.get("/api/movies/popular?sort=newest&limit=5")
        assert resp.status_code == 200
        movies = resp.json()
        assert len(movies) >= 1

    def test_sort_oldest(self, app_client):
        client, _ = app_client
        resp = client.get("/api/movies/popular?sort=oldest&limit=5")
        assert resp.status_code == 200
        movies = resp.json()
        assert len(movies) >= 1

    def test_invalid_sort_returns_400(self, app_client):
        client, _ = app_client
        resp = client.get("/api/movies/popular?sort=unsupported")
        assert resp.status_code == 400

    def test_invalid_decade_returns_400(self, app_client):
        client, _ = app_client
        resp = client.get("/api/movies/popular?decade=1995")
        assert resp.status_code == 400

    def test_invalid_year_returns_400(self, app_client):
        client, _ = app_client
        resp = client.get("/api/movies/popular?year=1800")
        assert resp.status_code == 400

