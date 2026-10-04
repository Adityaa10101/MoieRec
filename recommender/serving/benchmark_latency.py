#!/usr/bin/env python3
"""
recommender/serving/benchmark_latency.py
========================================
Phase 2G-Lite Part C3: Latency, Memory Footprint, and cProfile Benchmark.

Measures:
- RSS memory after loading HybridScorer(model_v2).
- Latency (p50, p95, p99) over 100 requests across K in {3, 5, 10, 20}.
- cProfile summary of hot paths.
- Target: p50 < 150 ms.
"""

import cProfile
import ctypes
from ctypes import wintypes
from pathlib import Path
import pstats
import time
from typing import List, Tuple

import numpy as np


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
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
    ]


def get_rss_mb() -> float:
    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    h = kernel32.OpenProcess(0x0400 | 0x0010, False, os.getpid())
    if h:
        psapi.GetProcessMemoryInfo(h, ctypes.byref(counters), counters.cb)
        kernel32.CloseHandle(h)
        return counters.WorkingSetSize / (1024 * 1024)
    return 0.0

from recommender.serving.hybrid_scorer import HybridScorer

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_V2_DIR = PROJECT_ROOT / "data" / "serving" / "model_v2"


def run_benchmark():
    print("=" * 70)
    print("Phase 2G-Lite Part C3: Latency & Footprint Benchmark (Model v2)")
    print("=" * 70)

    rss_before = get_rss_mb()

    t_load_start = time.time()
    scorer = HybridScorer(artifacts_dir=MODEL_V2_DIR)
    t_load = time.time() - t_load_start

    rss_after = get_rss_mb()
    rss_delta = rss_after - rss_before

    print(f"Artifacts loaded in: {t_load:.2f}s")
    print(f"Process RSS after load: {rss_after:.1f} MB (Delta: {rss_delta:+.1f} MB)")
    print(f"Scorer version: {scorer.version}, items: {scorer.n_items}")

    # Generate 100 synthetic profiles distributed across K in {3, 5, 10, 20}
    rng = np.random.default_rng(9999)
    catalog_mids = scorer.item_movie_ids
    n_catalog = len(catalog_mids)

    k_distribution = [3] * 25 + [5] * 25 + [10] * 25 + [20] * 25  # 100 requests
    requests: List[Tuple[List[int], List[int]]] = []

    for k in k_distribution:
        liked_indices = rng.choice(n_catalog, size=k, replace=False)
        liked_ids = [int(catalog_mids[i]) for i in liked_indices]
        n_excl = rng.integers(0, 5)
        remain = np.setdiff1d(np.arange(n_catalog), liked_indices)
        excl_indices = rng.choice(remain, size=n_excl, replace=False)
        exclude_ids = [int(catalog_mids[i]) for i in excl_indices]
        requests.append((liked_ids, exclude_ids))

    # Warmup
    print("\nWarming up (5 requests)...")
    for liked_ids, exclude_ids in requests[:5]:
        _ = scorer.score(liked_movie_ids=liked_ids, exclude_movie_ids=exclude_ids, top_k=20)

    # 100 timed requests
    print("Running 100 timed requests...")
    latencies_ms: List[float] = []

    # Also capture with cProfile
    profiler = cProfile.Profile()
    profiler.enable()

    for liked_ids, exclude_ids in requests:
        t0 = time.perf_counter()
        results, ignored = scorer.score(liked_movie_ids=liked_ids, exclude_movie_ids=exclude_ids, top_k=20)
        t_elapsed = (time.perf_counter() - t0) * 1000.0  # ms
        latencies_ms.append(t_elapsed)
        assert len(results) == 20
        assert len(ignored) == 0

    profiler.disable()

    # Latency stats
    arr = np.array(latencies_ms)
    p50 = float(np.percentile(arr, 50))
    p90 = float(np.percentile(arr, 90))
    p95 = float(np.percentile(arr, 95))
    p99 = float(np.percentile(arr, 99))
    mean_val = float(np.mean(arr))
    min_val = float(np.min(arr))
    max_val = float(np.max(arr))

    print("\n" + "=" * 70)
    print("LATENCY RESULTS (100 REQUESTS):")
    print(f"  Min:  {min_val:6.2f} ms")
    print(f"  Mean: {mean_val:6.2f} ms")
    print(f"  p50:  {p50:6.2f} ms  (Target: < 150 ms) -> {'PASS' if p50 < 150 else 'FAIL'}")
    print(f"  p90:  {p90:6.2f} ms")
    print(f"  p95:  {p95:6.2f} ms")
    print(f"  p99:  {p99:6.2f} ms")
    print(f"  Max:  {max_val:6.2f} ms")
    print("=" * 70)

    # cProfile Top 20 cumulative time
    print("\nTOP 20 FUNCTIONS BY CUMULATIVE TIME (cProfile):")
    stats = pstats.Stats(profiler)
    stats.strip_dirs()
    stats.sort_stats("cumulative")
    stats.print_stats(20)


if __name__ == "__main__":
    run_benchmark()
