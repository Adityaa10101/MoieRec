#!/usr/bin/env python3
"""
recommender/serving/benchmark_footprint.py
=========================================
Phase 2F.1 Part B2: Measure process RSS after loading artifacts, load time,
and p50/p95 latency over 100 /api/personalized/home requests with mocked TMDB.
"""

import ctypes
from ctypes import wintypes
import os
import time
from unittest.mock import AsyncMock, patch
import numpy as np
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from starlette.testclient import TestClient
from app.main import app
from app.services.hybrid_service import get_hybrid_scorer

class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]

_GetProcessMemoryInfo = ctypes.windll.kernel32.K32GetProcessMemoryInfo
_GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]
_GetProcessMemoryInfo.restype = wintypes.BOOL

def get_process_rss_mb() -> float:
    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    if _GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
        return counters.WorkingSetSize / (1024 * 1024)
    return 0.0

MOCK_TMDB_PAYLOAD = {
    "tmdb_id": 862,
    "title": "Mock Title",
    "overview": "A test overview.",
    "tagline": "A test tagline.",
    "release_date": "1995-11-22",
    "runtime": 100,
    "genres": ["Action", "Drama"],
    "vote_average": 7.5,
    "vote_count": 5000,
    "poster_path": "/test_poster.jpg",
    "backdrop_path": "/test_backdrop.jpg",
    "cast": [],
    "directors": ["Mock Director"],
    "adult": False,
    "original_language": "en",
    "_image_base_url": "https://image.tmdb.org/t/p/",
}

def main():
    rss_before_mb = get_process_rss_mb()

    # 1. Measure load time
    t0 = time.perf_counter()
    scorer = get_hybrid_scorer()
    load_time_sec = time.perf_counter() - t0

    rss_after_load_mb = get_process_rss_mb()
    rss_delta_mb = rss_after_load_mb - rss_before_mb

    print(f"=== Serving Footprint & Load Time (B2) ===")
    print(f"Process RSS before load: {rss_before_mb:.2f} MB")
    print(f"Artifact load time:      {load_time_sec:.3f} s ({load_time_sec*1000:.1f} ms)")
    print(f"Process RSS after load:  {rss_after_load_mb:.2f} MB (Delta: +{rss_delta_mb:.2f} MB)")
    print(f"Target RSS ceiling:      < 500 MB (Achieved: {'YES' if rss_after_load_mb < 500 else 'NO'})")

    # Inspect largest arrays in scorer
    csr_bytes = (scorer.item_tags_csr.data.nbytes + scorer.item_tags_csr.indices.nbytes + scorer.item_tags_csr.indptr.nbytes)
    arrays = [
        ("item_genome", scorer.item_genome.nbytes / (1024 * 1024)),
        ("item_tags_csr (data+indptr+indices)", csr_bytes / (1024 * 1024)),
        ("item_t1", scorer.item_t1.nbytes / (1024 * 1024)),
        ("item_norms", scorer.item_norms.nbytes / (1024 * 1024)),
        ("pop_scores", scorer.pop_scores.nbytes / (1024 * 1024)),
        ("item_movie_ids", scorer.item_movie_ids.nbytes / (1024 * 1024)),
    ]
    print("\nLargest model arrays in memory:")
    for name, sz in sorted(arrays, key=lambda x: -x[1]):
        print(f"  - {name}: {sz:.2f} MB")

    # 2. Measure latency over 100 requests with mocked TMDB
    print("\n=== Latency Benchmark: 100 /api/personalized/home Requests ===")
    rng = np.random.default_rng(42)
    catalog_mids = scorer.item_movie_ids

    # Generate 100 profile requests across K in {3, 5, 10, 20}
    test_profiles = []
    k_choices = [3, 5, 10, 20]
    for i in range(100):
        k = k_choices[i % 4]
        picks = [int(mid) for mid in rng.choice(catalog_mids, size=k, replace=False)]
        test_profiles.append(picks)

    latencies_ms = []

    with patch("app.api.endpoints.movies.get_tmdb_data", new_callable=AsyncMock) as mock_tmdb:
        mock_tmdb.return_value = MOCK_TMDB_PAYLOAD
        with patch("app.services.tmdb.get_tmdb_data", mock_tmdb):
            with TestClient(app) as client:
                # Warm-up request
                client.post("/api/personalized/home", json={"liked_movie_ids": test_profiles[0]})

                for idx, picks in enumerate(test_profiles):
                    t_req_start = time.perf_counter()
                    resp = client.post("/api/personalized/home", json={"liked_movie_ids": picks})
                    dur_ms = (time.perf_counter() - t_req_start) * 1000.0
                    assert resp.status_code == 200, f"Request failed: {resp.text}"
                    data = resp.json()
                    assert data["personalized"] is True
                    assert len(data["rows"]) >= 1
                    latencies_ms.append(dur_ms)

    latencies_ms = np.array(latencies_ms)
    p50 = np.percentile(latencies_ms, 50)
    p90 = np.percentile(latencies_ms, 90)
    p95 = np.percentile(latencies_ms, 95)
    p99 = np.percentile(latencies_ms, 99)
    mean_lat = np.mean(latencies_ms)
    min_lat = np.min(latencies_ms)
    max_lat = np.max(latencies_ms)

    rss_final_mb = get_process_rss_mb()

    print(f"Requests completed: {len(latencies_ms)}")
    print(f"Mean latency:       {mean_lat:.2f} ms")
    print(f"p50 (median):       {p50:.2f} ms")
    print(f"p90:                {p90:.2f} ms")
    print(f"p95:                {p95:.2f} ms")
    print(f"p99:                {p99:.2f} ms")
    print(f"Min / Max latency:  {min_lat:.2f} ms / {max_lat:.2f} ms")
    print(f"Process RSS after 100 requests: {rss_final_mb:.2f} MB")

if __name__ == "__main__":
    main()
