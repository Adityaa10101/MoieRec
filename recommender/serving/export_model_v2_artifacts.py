#!/usr/bin/env python3
"""
recommender/serving/export_model_v2_artifacts.py
================================================
Phase 2G-Lite Part C1: Export compact serving artifacts for Hybrid v2 model.

Outputs (to data/serving/model_v2/ — git-ignored):
  - item_t1.npy             [18259, D_t1] float32 L2-normed
  - item_tags_csr.npz       [18259, D_tags] float32 CSR L2-normed
  - item_genome.npy         [18259, D_genome] float32 L2-normed
  - item_norms.npy          [18259] float32 pre-norm norms
  - item_movie_ids.npy      [18259] int32 serving movie IDs
  - pop_scores.npy          [18259] float32 train positive counts
  - cf_topk_indices.npy     [18259, 200] int32 serving neighbor indices (-1 for empty)
  - cf_topk_sims.npy        [18259, 200] float32 neighbor similarities
  - cf_topk_cooc.npy        [18259, 200] int32 neighbor co-occurrence counts n_ij
  - feature_names.json      Feature display strings
  - genre_names.json        Genre vocabulary
  - genome_tag_names.json   Genome tag names
  - movie_titles.json       Dict of movie_id -> title_display
  - release_era_names.json  Release era strings
  - tag_vocab.json          Tag vocabulary
  - hybrid_v2.yaml          Model v2 configuration

NEVER reads test.parquet or cold_final.
"""

import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np
import scipy.sparse as sp
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_V1_DIR = PROJECT_ROOT / "data" / "serving" / "model_v1"
MODEL_V2_DIR = PROJECT_ROOT / "data" / "serving" / "model_v2"
CF_CACHE_DIR = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "collaborative"
CONFIG_PATH = PROJECT_ROOT / "recommender" / "config" / "hybrid_v2.yaml"


def export_model_v2_artifacts() -> None:
    t0 = time.time()
    print("=" * 70)
    print("Phase 2G-Lite Part C1: Exporting Model v2 Serving Artifacts")
    print("=" * 70)

    MODEL_V2_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Base serving content & popularity artifacts from model_v1
    base_files = [
        "item_t1.npy",
        "item_tags_csr.npz",
        "item_genome.npy",
        "item_norms.npy",
        "item_movie_ids.npy",
        "pop_scores.npy",
        "feature_names.json",
        "genre_names.json",
        "genome_tag_names.json",
        "movie_titles.json",
        "release_era_names.json",
        "tag_vocab.json",
    ]
    print("[1/4] Copying base content & catalog artifacts from model_v1...")
    for fname in base_files:
        src = MODEL_V1_DIR / fname
        dst = MODEL_V2_DIR / fname
        if not src.exists():
            raise FileNotFoundError(f"Source file {src} does not exist.")
        shutil.copy2(str(src), str(dst))

    # Copy config
    shutil.copy2(str(CONFIG_PATH), str(MODEL_V2_DIR / "hybrid_v2.yaml"))
    print("  Copied 12 base artifact files + hybrid_v2.yaml")

    # 2. Load CF neighbor cache and map to serving items
    print("[2/4] Loading offline top-200 CF neighbor tables...")
    top200_path = CF_CACHE_DIR / "top200_a5_lam0.npz"
    cand_mids_path = CF_CACHE_DIR / "candidate_movie_ids.npy"

    if not top200_path.exists() or not cand_mids_path.exists():
        raise FileNotFoundError(f"CF precomputed tables not found in {CF_CACHE_DIR}")

    top200_data = np.load(top200_path)
    cand_mids_cache = np.load(cand_mids_path)
    serving_mids = np.load(MODEL_V2_DIR / "item_movie_ids.npy")

    n_serving = len(serving_mids)
    n_cand_cache = len(cand_mids_cache)
    print(f"  Serving catalog size: {n_serving}, Benchmark candidate size: {n_cand_cache}")

    # Map candidate_idx -> serving_idx
    serving_mid_to_idx = {int(mid): idx for idx, mid in enumerate(serving_mids)}
    cand_idx_to_serving_idx = np.full(n_cand_cache, -1, dtype=np.int32)
    for c_idx, mid in enumerate(cand_mids_cache):
        if int(mid) in serving_mid_to_idx:
            cand_idx_to_serving_idx[c_idx] = serving_mid_to_idx[int(mid)]

    # Map serving_mid -> raw cand index in cache
    cand_mid_to_cidx = {int(mid): c_idx for c_idx, mid in enumerate(cand_mids_cache)}

    # 3. Create compact serving arrays
    print("[3/4] Aligning CF neighbor arrays to serving indices...")
    k_neighbors = 200
    cf_indices = np.full((n_serving, k_neighbors), -1, dtype=np.int32)
    cf_sims = np.zeros((n_serving, k_neighbors), dtype=np.float32)
    cf_cooc = np.zeros((n_serving, k_neighbors), dtype=np.int32)

    raw_indices = top200_data["indices"]
    raw_sims = top200_data["similarities"]
    raw_cooc = top200_data["cooccurrences"]

    mapped_count = 0
    for s_idx, mid in enumerate(serving_mids):
        raw_cidx = cand_mid_to_cidx.get(int(mid), -1)
        if raw_cidx < 0:
            continue
        mapped_count += 1

        row_raw_neigh = raw_indices[raw_cidx]
        row_raw_sim = raw_sims[raw_cidx]
        row_raw_cooc = raw_cooc[raw_cidx]

        # Valid neighbor filter
        valid_raw = (row_raw_neigh >= 0) & (row_raw_sim > 0)
        valid_neigh_cindices = row_raw_neigh[valid_raw]
        mapped_serving_neigh = cand_idx_to_serving_idx[valid_neigh_cindices]

        # Keep only neighbors present in serving catalog
        valid_serving = mapped_serving_neigh >= 0
        n_valid = np.sum(valid_serving)
        if n_valid > 0:
            cf_indices[s_idx, :n_valid] = mapped_serving_neigh[valid_serving]
            cf_sims[s_idx, :n_valid] = row_raw_sim[valid_raw][valid_serving]
            cf_cooc[s_idx, :n_valid] = row_raw_cooc[valid_raw][valid_serving]

    print(f"  Mapped {mapped_count}/{n_serving} serving items to CF neighbor tables.")

    # 4. Save compact arrays
    print(f"[4/4] Saving compact CF arrays to {MODEL_V2_DIR}...")
    np.save(MODEL_V2_DIR / "cf_topk_indices.npy", cf_indices)
    np.save(MODEL_V2_DIR / "cf_topk_sims.npy", cf_sims)
    np.save(MODEL_V2_DIR / "cf_topk_cooc.npy", cf_cooc)

    elapsed = time.time() - t0
    print(f"Done in {elapsed:.2f}s!")
    print(f"cf_topk_indices: shape={cf_indices.shape}, dtype={cf_indices.dtype} (size: {cf_indices.nbytes / (1024*1024):.1f} MB)")
    print(f"cf_topk_sims:    shape={cf_sims.shape}, dtype={cf_sims.dtype} (size: {cf_sims.nbytes / (1024*1024):.1f} MB)")
    print(f"cf_topk_cooc:    shape={cf_cooc.shape}, dtype={cf_cooc.dtype} (size: {cf_cooc.nbytes / (1024*1024):.1f} MB)")
    print(f"Total CF footprint: {(cf_indices.nbytes + cf_sims.nbytes + cf_cooc.nbytes) / (1024*1024):.1f} MB")


if __name__ == "__main__":
    export_model_v2_artifacts()
