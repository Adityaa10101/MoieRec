"""
backend/tests/test_personalized_api.py
======================================
Comprehensive backend tests for Phase 2F:
- POST /api/personalized/home
- GET /api/movies/{id}/similar
- Mocked TMDB (no network calls)
- Testing: shapes, <3 likes path, ignored IDs, excludes honored,
  reason codes strictly backed by evidence, match_percent range,
  no fabrication, determinism, and backend scorer parity.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from app.main import app
from app.services.hybrid_service import get_hybrid_scorer

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = _PROJECT_ROOT / "data" / "serving" / "model_v1"

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


@pytest.fixture()
def client():
    """TestClient with mocked TMDB network calls."""
    with patch("app.services.tmdb.get_tmdb_data", new_callable=AsyncMock) as mock_tmdb:
        mock_tmdb.return_value = MOCK_TMDB_PAYLOAD
        with TestClient(app) as c:
            yield c


@pytest.fixture(scope="module")
def scorer():
    return get_hybrid_scorer()


# ---------------------------------------------------------------------------
# C1 / C4: < 3 Likes Path
# ---------------------------------------------------------------------------

def test_personalized_less_than_3_likes(client):
    """When fewer than 3 valid likes are provided, personalized=False and rows=[] are returned."""
    # 0 likes
    resp0 = client.post("/api/personalized/home", json={"liked_movie_ids": []})
    assert resp0.status_code == 200
    data0 = resp0.json()
    assert data0["personalized"] is False
    assert data0["k"] == 0
    assert data0["rows"] == []
    assert data0["message"] is not None

    # 1 like
    resp1 = client.post("/api/personalized/home", json={"liked_movie_ids": [1]})
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["personalized"] is False
    assert data1["k"] == 1
    assert data1["rows"] == []

    # 2 likes
    resp2 = client.post("/api/personalized/home", json={"liked_movie_ids": [1, 2]})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["personalized"] is False
    assert data2["k"] == 2
    assert data2["rows"] == []


# ---------------------------------------------------------------------------
# C1 / C4: Ignored / Unknown IDs
# ---------------------------------------------------------------------------

def test_ignored_ids(client, scorer):
    """Invalid or nonexistent movie IDs are ignored and listed in ignored_ids."""
    unknown_ids = [9999991, 9999992]
    valid_ids = [int(scorer.item_movie_ids[0]), int(scorer.item_movie_ids[1])]

    # 2 valid + 2 unknown = 2 valid -> < 3 -> personalized=False
    resp = client.post(
        "/api/personalized/home",
        json={"liked_movie_ids": valid_ids + unknown_ids},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["personalized"] is False
    assert data["k"] == 2
    assert set(data["ignored_ids"]) == set(unknown_ids)

    # 3 valid + 2 unknown = 3 valid -> >= 3 -> personalized=True
    valid_3 = valid_ids + [int(scorer.item_movie_ids[2])]
    resp_valid = client.post(
        "/api/personalized/home",
        json={"liked_movie_ids": valid_3 + unknown_ids},
    )
    assert resp_valid.status_code == 200
    data_valid = resp_valid.json()
    assert data_valid["personalized"] is True
    assert data_valid["k"] == 3
    assert set(data_valid["ignored_ids"]) == set(unknown_ids)


# ---------------------------------------------------------------------------
# C1 / C4: Happy Path Shapes and Row Structures
# ---------------------------------------------------------------------------

def test_personalized_home_happy_path(client, scorer):
    """With >= 3 valid likes, returns Picked for You row + up to 2 Because you liked rows."""
    liked_ids = [int(scorer.item_movie_ids[0]), int(scorer.item_movie_ids[1]), int(scorer.item_movie_ids[2])]

    resp = client.post("/api/personalized/home", json={"liked_movie_ids": liked_ids})
    assert resp.status_code == 200
    data = resp.json()

    assert data["personalized"] is True
    assert data["k"] == 3
    assert data["config_version"] == scorer.version
    assert len(data["rows"]) >= 1

    # First row is 'Picked for You'
    picked_row = data["rows"][0]
    assert picked_row["id"] == "row-personalized-picked"
    assert picked_row["title"] == "Picked for You"
    assert len(picked_row["movies"]) > 0

    # Check movie properties
    for m in picked_row["movies"]:
        assert m["movie_id"] not in liked_ids  # Liked movies excluded
        assert m["source"] in ("hybrid_v1", "hybrid_v1.1", "hybrid_v2")
        assert data.get("alpha_used") is not None
        assert m["score"] is not None
        assert m["match_percent"] is not None
        assert 0 <= m["match_percent"] <= 100
        assert m["poster_url"] is not None  # Only movies with posters included

        # Explanation object exists
        expl = m["explanation"]
        assert expl is not None
        assert expl["match_percent"] == m["match_percent"]
        assert "content" in expl["components"]
        assert "popularity" in expl["components"]
        if scorer.is_v2:
            # At K=3, w_c=0, so nearest_pick is None and content codes gated
            assert expl["nearest_pick"] is None
            assert "SIMILAR_TO_PICK" not in m["reason_codes"]
            assert "SHARED_GENRES" not in m["reason_codes"]
            assert "SHARED_TAGS" not in m["reason_codes"]
            assert "POPULAR_WITH_VIEWERS" not in m["reason_codes"]
        else:
            assert expl["nearest_pick"]["movie_id"] in liked_ids

        # No fabricated meters
        assert "directorAffinity" not in m
        assert "thematicFit" not in m

    # Up to 2 'Because you liked <title>' rows
    if len(data["rows"]) > 1:
        for row in data["rows"][1:]:
            assert row["title"].startswith("Because you liked")
            for m in row["movies"]:
                assert m["movie_id"] not in liked_ids
                assert m["source"] == "content_similarity"
                assert m["score"] is not None


# ---------------------------------------------------------------------------
# C1 / C4: Excludes Honored
# ---------------------------------------------------------------------------

def test_excludes_honored(client, scorer):
    """Liked items and exclude_movie_ids are never in recommended rows."""
    liked_ids = [int(scorer.item_movie_ids[i]) for i in range(5)]
    exclude_ids = [int(scorer.item_movie_ids[i]) for i in range(5, 10)]

    resp = client.post(
        "/api/personalized/home",
        json={"liked_movie_ids": liked_ids, "exclude_movie_ids": exclude_ids},
    )
    assert resp.status_code == 200
    data = resp.json()

    forbidden_ids = set(liked_ids) | set(exclude_ids)
    for row in data["rows"]:
        for m in row["movies"]:
            assert m["movie_id"] not in forbidden_ids, f"Excluded movie {m['movie_id']} found in {row['id']}"


# ---------------------------------------------------------------------------
# C1 / C4 / B4: Reason Codes Backed Strictly by Evidence
# ---------------------------------------------------------------------------

def test_reason_codes_evidence_contract(client, scorer):
    """Reason codes are only emitted when concrete mathematical evidence holds."""
    liked_ids = [int(scorer.item_movie_ids[i]) for i in range(5)]

    resp = client.post("/api/personalized/home", json={"liked_movie_ids": liked_ids})
    assert resp.status_code == 200
    picked_row = resp.json()["rows"][0]

    for m in picked_row["movies"]:
        codes = m["reason_codes"]
        expl = m["explanation"]
        assert expl is not None

        if scorer.is_v2:
            # At K=5, w_c=0, w_p=0, w_f=1.0: no content or popularity codes allowed
            assert "SIMILAR_TO_PICK" not in codes
            assert "SHARED_GENRES" not in codes
            assert "SHARED_TAGS" not in codes
            assert "POPULAR_WITH_VIEWERS" not in codes
            if "CO_LIKED_BY_USERS" in codes:
                assert expl.get("cf_pick") is not None
                assert expl["cf_pick"]["cooccurrence"] >= scorer.cf_min_support
        else:
            if "SIMILAR_TO_PICK" in codes:
                assert expl["nearest_pick"]["similarity"] >= scorer.similarity_threshold
            if "SHARED_GENRES" in codes:
                genre_contribs = [f for f in expl["top_shared_features"] if f["feature_type"] == "genre"]
                assert any(f["contribution"] > 0 for f in genre_contribs)
            if "SHARED_TAGS" in codes:
                tag_contribs = [f for f in expl["top_shared_features"] if f["feature_type"] in ("tag", "genome_tag")]
                assert any(f["contribution"] > 0 for f in tag_contribs)
            if "POPULAR_WITH_VIEWERS" in codes:
                assert expl["components"]["popularity"] >= expl["components"]["content"]


def test_reason_codes_gating_k_ge_15(client, scorer):
    """At K >= 15, w_c=0.1 > 0, so content evidence is extracted, but w_p=0 so popularity is never emitted."""
    liked_ids = [int(scorer.item_movie_ids[i]) for i in range(16)]

    resp = client.post("/api/personalized/home", json={"liked_movie_ids": liked_ids})
    assert resp.status_code == 200
    picked_row = resp.json()["rows"][0]

    for m in picked_row["movies"]:
        codes = m["reason_codes"]
        expl = m["explanation"]
        assert expl is not None

        if scorer.is_v2:
            # w_c=0.1 > 0: nearest_pick exists
            assert expl["nearest_pick"] is not None
            assert expl["nearest_pick"]["movie_id"] in liked_ids
            # w_p is still 0.0: popularity reason code strictly forbidden
            assert "POPULAR_WITH_VIEWERS" not in codes
            if "SIMILAR_TO_PICK" in codes:
                assert expl["nearest_pick"]["similarity"] >= scorer.similarity_threshold
            if "CO_LIKED_BY_USERS" in codes:
                assert expl.get("cf_pick") is not None
                assert expl["cf_pick"]["cooccurrence"] >= scorer.cf_min_support



# ---------------------------------------------------------------------------
# C1 / C4: Determinism
# ---------------------------------------------------------------------------

def test_personalized_feed_determinism(client, scorer):
    """Calling the endpoint twice with identical input returns identical results."""
    liked_ids = [int(scorer.item_movie_ids[i]) for i in (10, 20, 30, 40)]

    resp1 = client.post("/api/personalized/home", json={"liked_movie_ids": liked_ids})
    resp2 = client.post("/api/personalized/home", json={"liked_movie_ids": liked_ids})

    assert resp1.status_code == 200
    assert resp2.status_code == 200

    row1 = resp1.json()["rows"][0]["movies"]
    row2 = resp2.json()["rows"][0]["movies"]

    mids1 = [m["movie_id"] for m in row1]
    mids2 = [m["movie_id"] for m in row2]
    assert mids1 == mids2

    scores1 = [m["score"] for m in row1]
    scores2 = [m["score"] for m in row2]
    assert scores1 == scores2


# ---------------------------------------------------------------------------
# C2 / C4: GET /api/movies/{id}/similar
# ---------------------------------------------------------------------------

def test_similar_movies_endpoint(client, scorer):
    """GET /api/movies/{id}/similar returns content-only neighbors with source='content_similarity'."""
    mid = int(scorer.item_movie_ids[0])

    resp = client.get(f"/api/movies/{mid}/similar?limit=10")
    assert resp.status_code == 200
    movies = resp.json()

    assert len(movies) <= 10
    assert all(m["source"] == "content_similarity" for m in movies)
    assert all(m["movie_id"] != mid for m in movies)  # Excludes self
    assert all(m["score"] is not None for m in movies)

    # 404 for invalid movie
    resp_404 = client.get("/api/movies/9999999/similar")
    assert resp_404.status_code == 404


# ---------------------------------------------------------------------------
# Personalized limit parameter tests
# ---------------------------------------------------------------------------

def test_personalized_limit_param(client, scorer):
    """
    Test limit param on POST /api/personalized/home:
    - Default (no limit) is identical to limit=20.
    - First 20 items of limit=30 equal (same IDs, same order) the limit=20 response.
    - limit=1 returns 1 item matching the top item.
    - limit=50 returns 50 items.
    - Out of range limits (0, 51) are rejected with HTTP 422.
    """
    liked_ids = [int(scorer.item_movie_ids[i]) for i in (10, 20, 30, 40, 50)]

    # 1. Default (no limit sent) vs limit=20
    resp_default = client.post("/api/personalized/home", json={"liked_movie_ids": liked_ids})
    assert resp_default.status_code == 200
    movies_default = resp_default.json()["rows"][0]["movies"]
    assert len(movies_default) == 20

    resp_20 = client.post("/api/personalized/home", json={"liked_movie_ids": liked_ids, "limit": 20})
    assert resp_20.status_code == 200
    movies_20 = resp_20.json()["rows"][0]["movies"]
    assert len(movies_20) == 20

    # Byte-for-byte / value identical
    assert [m["movie_id"] for m in movies_default] == [m["movie_id"] for m in movies_20]
    assert [m["score"] for m in movies_default] == [m["score"] for m in movies_20]

    # 2. limit=30: first 20 items equal limit=20 (same IDs, same order)
    resp_30 = client.post("/api/personalized/home", json={"liked_movie_ids": liked_ids, "limit": 30})
    assert resp_30.status_code == 200
    movies_30 = resp_30.json()["rows"][0]["movies"]
    assert len(movies_30) == 30
    assert [m["movie_id"] for m in movies_30[:20]] == [m["movie_id"] for m in movies_20]
    assert [m["score"] for m in movies_30[:20]] == [m["score"] for m in movies_20]

    # 3. limit=1
    resp_1 = client.post("/api/personalized/home", json={"liked_movie_ids": liked_ids, "limit": 1})
    assert resp_1.status_code == 200
    movies_1 = resp_1.json()["rows"][0]["movies"]
    assert len(movies_1) == 1
    assert movies_1[0]["movie_id"] == movies_20[0]["movie_id"]

    # 4. limit=50
    resp_50 = client.post("/api/personalized/home", json={"liked_movie_ids": liked_ids, "limit": 50})
    assert resp_50.status_code == 200
    movies_50 = resp_50.json()["rows"][0]["movies"]
    assert len(movies_50) == 50
    assert [m["movie_id"] for m in movies_50[:20]] == [m["movie_id"] for m in movies_20]

    # 5. Out of range values rejected with 422
    resp_low = client.post("/api/personalized/home", json={"liked_movie_ids": liked_ids, "limit": 0})
    assert resp_low.status_code == 422

    resp_high = client.post("/api/personalized/home", json={"liked_movie_ids": liked_ids, "limit": 51})
    assert resp_high.status_code == 422

