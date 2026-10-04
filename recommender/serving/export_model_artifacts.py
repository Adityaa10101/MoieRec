#!/usr/bin/env python3
"""
recommender/serving/export_model_artifacts.py
===============================================
Phase 2F Part B1: Export serving artifacts for hybrid_v1 model.

Outputs (to data/serving/model_v1/ — git-ignored):
  - item_features.npy       [n_serving_items, D] float32 L2-normalized
  - item_movie_ids.npy      [n_serving_items] int32 — movie_ids in feature row order
  - item_norms.npy          [n_serving_items] float32 (pre-norm norms, for diagnostics)
  - pop_scores.npy          [n_serving_items] float32 train_positive_count
  - feature_names.json      feature name strings [D]
  - genre_names.json        list of genre name strings
  - genome_tag_names.json   list of genome tag strings [1128]
  - hybrid_v1.yaml          copy of the chosen config

NEVER reads test.parquet or cold_final.
Run from project root with the recommender venv.
"""

import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FEAT_DIR = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "features"
ID_MAP_DIR = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "id_mappings"
SPLITS_DIR = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "splits"
BENCHMARK_DIR = PROJECT_ROOT / "data" / "processed" / "ml-25m" / "benchmark"
CATALOG_DB = PROJECT_ROOT / "data" / "serving" / "catalog.sqlite"
CONFIG_PATH = PROJECT_ROOT / "recommender" / "config" / "hybrid_v1.yaml"
OUTPUT_DIR = PROJECT_ROOT / "data" / "serving" / "model_v1"

# Safety guard: never touch forbidden paths
_FORBIDDEN = {"test.parquet", "cold_final"}
for _f in _FORBIDDEN:
    for _p in [SPLITS_DIR, FEAT_DIR]:
        assert _f not in str(_p), f"Forbidden path: {_f}"


def main() -> None:
    import yaml

    t0 = time.time()
    print("=" * 60)
    print("Phase 2F Part B1 — Export Model Artifacts")
    print("=" * 60)

    if not CONFIG_PATH.exists():
        print(f"ERROR: hybrid_v1.yaml not found at {CONFIG_PATH}")
        print("Run recommender/hybrid/tune_hybrid.py first.")
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    alpha = float(config["alpha"])
    w_t1 = float(config["block_weights"]["w_t1"])
    w_tags = float(config["block_weights"]["w_tags"])
    w_genome = float(config["block_weights"]["w_genome"])

    print(f"Config: alpha={alpha} w_t1={w_t1} w_tags={w_tags} w_genome={w_genome}")

    # Serving catalog: movie_ids that have tmdb_id (from catalog.sqlite)
    print("\n[1/5] Loading serving catalog (movies with tmdb_id)...")
    import sqlite3
    conn = sqlite3.connect(str(CATALOG_DB))
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT movie_id, title_display FROM movies WHERE tmdb_id IS NOT NULL ORDER BY movie_id ASC"
    )
    rows = cur.fetchall()
    serving_movie_ids = np.array([r["movie_id"] for r in rows], dtype=np.int32)
    movie_titles = {int(r["movie_id"]): r["title_display"] for r in rows}
    conn.close()
    n_serving = len(serving_movie_ids)
    print(f"  Serving catalog: {n_serving} movies with tmdb_id")

    # Feature metadata
    meta = json.loads((FEAT_DIR / "feature_metadata.json").read_text(encoding="utf-8"))
    t1_info = meta["tier1_baseline"]
    feature_names_t1 = list(t1_info["feature_names"])
    n_genres = int(t1_info["n_genres"])

    # ID mapping: movie_id -> benchmark_idx
    m2b_df = pd.read_parquet(ID_MAP_DIR / "movie_id_to_benchmark_idx.parquet")
    m2b = m2b_df.set_index("movie_id")["benchmark_idx"].to_dict()

    # Feature matrices
    print("\n[2/5] Loading feature matrices...")
    t1_csr = sp.load_npz(FEAT_DIR / "tier1_baseline_features.npz")
    tag_csr = sp.load_npz(FEAT_DIR / "tier2_tag_tfidf.npz")
    genome_mat = np.load(FEAT_DIR / "tier2_genome_matrix.npy")
    genome_mask = np.load(FEAT_DIR / "tier2_genome_mask.npy")

    # Genome tag names
    full_genome_tags = pd.read_parquet(
        PROJECT_ROOT / "data" / "processed" / "ml-25m" / "full" / "genome_tags.parquet"
    )
    genome_tag_names = full_genome_tags.sort_values("tag_id")["tag"].tolist()

    # Tag vocabulary reconstruction
    from sklearn.feature_extraction.text import TfidfVectorizer
    bench_movies = pd.read_parquet(BENCHMARK_DIR / "movies.parquet")
    benchmark_tags = pd.read_parquet(BENCHMARK_DIR / "tags.parquet")
    clean_tags = benchmark_tags.dropna(subset=["tag"]).copy()
    clean_tags["clean_tag"] = clean_tags["tag"].astype(str).str.lower().str.replace(r"[^\w\s-]", "", regex=True).str.strip()
    tags_per_movie = clean_tags.groupby("movie_id")["clean_tag"].apply(lambda s: " ".join(s)).to_dict()
    sorted_bm_movies = bench_movies.sort_values("movie_id").reset_index(drop=True)
    documents = [tags_per_movie.get(mid, "") for mid in sorted_bm_movies["movie_id"]]
    vec = TfidfVectorizer(
        lowercase=True,
        min_df=2,
        max_df=0.7,
        sublinear_tf=True,
        token_pattern=r"(?u)\b\w[\w-]+\b",
    )
    vec.fit(documents)
    tag_vocab = list(vec.get_feature_names_out())

    # Benchmark movie metadata (genres)
    genre_set = set()
    for genres_str in bench_movies["genres"].dropna():
        for g in str(genres_str).split("|"):
            g = g.strip()
            if g and g != "(no genres listed)":
                genre_set.add(g)
    genre_names = sorted(genre_set)
    release_era_names = ["norm_year", "missing_year_flag"]

    # Popularity scores (from train_movie_stats)
    print("\n[3/5] Building popularity scores...")
    train_stats = pd.read_parquet(SPLITS_DIR / "train_movie_stats.parquet")
    stats_dict = train_stats.set_index("movie_id")["positive_rating_count"].to_dict()

    # ---- Build block item features for serving movie_ids ----
    print(f"\n[4/5] Building block item features for {n_serving} serving movies...")
    bench_indices = np.array([m2b.get(int(mid), -1) for mid in serving_movie_ids], dtype=np.int32)
    valid = bench_indices >= 0
    safe_idx = np.where(valid, bench_indices, 0)

    # 1. T1 block (dense, unit-normed)
    cand_t1 = t1_csr[safe_idx].toarray().astype(np.float32)
    cand_t1[~valid] = 0.0
    t1_norms = np.linalg.norm(cand_t1, axis=1, keepdims=True)
    t1_norms = np.where(t1_norms > 0, t1_norms, 1.0)
    cand_t1_normed = (cand_t1 / t1_norms).astype(np.float32)
    t1_names = [f"t1:{n}" for n in feature_names_t1]

    # 2. Tag block (sparse CSR, unit-normed)
    tags_raw = tag_csr[safe_idx].astype(np.float32)
    tag_row_norms = np.array(tags_raw.power(2).sum(axis=1)).flatten() ** 0.5
    tag_row_norms = np.where(tag_row_norms > 0, tag_row_norms, 1.0)
    tag_row_norms[~valid] = 1.0
    # Unit-normalize CSR rows
    inv_tag_norms = (1.0 / tag_row_norms).astype(np.float32)
    # Multiply CSR rows by diagonal matrix
    diag_inv = sp.diags(inv_tag_norms)
    tags_csr_normed = diag_inv.dot(tags_raw).tocsr().astype(np.float32)
    # Zero out invalid entries
    if not np.all(valid):
        # invalid rows set to 0
        invalid_rows = np.flatnonzero(~valid)
        for r in invalid_rows:
            tags_csr_normed.data[tags_csr_normed.indptr[r]:tags_csr_normed.indptr[r+1]] = 0.0
        tags_csr_normed.eliminate_zeros()
    tag_names = [f"tag:{t}" for t in tag_vocab]

    # 3. Genome block (dense, unit-normed)
    gm = genome_mat[safe_idx].astype(np.float32)
    gm_mask = genome_mask[safe_idx].astype(np.float32)[:, None]
    masked_gm = gm * gm_mask
    masked_gm[~valid] = 0.0
    gen_norms = np.linalg.norm(masked_gm, axis=1, keepdims=True)
    gen_norms = np.where(gen_norms > 0, gen_norms, 1.0)
    genome_normed = (masked_gm / gen_norms).astype(np.float32)
    genome_names = [f"genome:{t}" for t in genome_tag_names]

    all_names = t1_names + tag_names + genome_names

    # Compute item pre-normalization norms using block weights from config
    # Norm of [w_t1 * v_t1, w_tags * v_tags, w_genome * v_genome]
    # Since each block is unit-normalized (or 0), ||v_b||^2 is 1.0 (if non-zero) or 0.0
    t1_has_val = (np.linalg.norm(cand_t1_normed, axis=1) > 0).astype(np.float32)
    tags_has_val = (np.array(tags_csr_normed.power(2).sum(axis=1)).flatten() > 0).astype(np.float32)
    gen_has_val = (np.linalg.norm(genome_normed, axis=1) > 0).astype(np.float32)

    item_norms = np.sqrt(
        (w_t1 ** 2) * t1_has_val +
        (w_tags ** 2) * tags_has_val +
        (w_genome ** 2) * gen_has_val
    ).astype(np.float32)
    item_norms = np.where(item_norms > 0, item_norms, 1.0)

    print(f"  Item T1 dense shape: {cand_t1_normed.shape}, dtype={cand_t1_normed.dtype}")
    print(f"  Item Tags CSR shape: {tags_csr_normed.shape}, nnz={tags_csr_normed.nnz}")
    print(f"  Item Genome dense shape: {genome_normed.shape}, dtype={genome_normed.dtype}")
    print(f"  Feature dimension total: {len(all_names)}")

    # Popularity scores aligned to serving_movie_ids
    pop_scores = np.array(
        [stats_dict.get(int(mid), 0) for mid in serving_movie_ids], dtype=np.float32
    )

    # ---- Save artifacts ----
    print(f"\n[5/5] Saving artifacts to {OUTPUT_DIR}...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    np.save(str(OUTPUT_DIR / "item_t1.npy"), cand_t1_normed)
    sp.save_npz(str(OUTPUT_DIR / "item_tags_csr.npz"), tags_csr_normed)
    np.save(str(OUTPUT_DIR / "item_genome.npy"), genome_normed)
    np.save(str(OUTPUT_DIR / "item_movie_ids.npy"), serving_movie_ids)
    np.save(str(OUTPUT_DIR / "item_norms.npy"), item_norms)
    np.save(str(OUTPUT_DIR / "pop_scores.npy"), pop_scores)

    # Remove old dense item_features.npy to reclaim disk/memory footprint
    old_dense_path = OUTPUT_DIR / "item_features.npy"
    if old_dense_path.exists():
        print("  Removing old dense item_features.npy (~1.4 GB)...")
        old_dense_path.unlink()

    with open(OUTPUT_DIR / "feature_names.json", "w", encoding="utf-8") as f:
        json.dump(all_names, f, indent=2)

    with open(OUTPUT_DIR / "genre_names.json", "w", encoding="utf-8") as f:
        json.dump(genre_names, f, indent=2)

    with open(OUTPUT_DIR / "release_era_names.json", "w", encoding="utf-8") as f:
        json.dump(release_era_names, f, indent=2)

    with open(OUTPUT_DIR / "tag_vocab.json", "w", encoding="utf-8") as f:
        json.dump(tag_vocab, f, indent=2)

    with open(OUTPUT_DIR / "genome_tag_names.json", "w", encoding="utf-8") as f:
        json.dump(genome_tag_names, f, indent=2)

    with open(OUTPUT_DIR / "movie_titles.json", "w", encoding="utf-8") as f:
        json.dump(movie_titles, f)

    # Copy config YAMLs: hybrid_v1_1.yaml and hybrid_v1.yaml
    cfg_1_1 = PROJECT_ROOT / "recommender" / "config" / "hybrid_v1_1.yaml"
    if cfg_1_1.exists():
        shutil.copy2(str(cfg_1_1), str(OUTPUT_DIR / "hybrid_v1_1.yaml"))
    shutil.copy2(str(CONFIG_PATH), str(OUTPUT_DIR / "hybrid_v1.yaml"))

    runtime = time.time() - t0
    print(f"\nDone in {runtime:.1f}s")
    print(f"item_t1: {cand_t1_normed.shape}")
    print(f"item_tags_csr: {tags_csr_normed.shape}, nnz={tags_csr_normed.nnz}")
    print(f"item_genome: {genome_normed.shape}")
    print(f"item_movie_ids: {serving_movie_ids.shape}")
    print(f"pop_scores: {pop_scores.shape}, max={pop_scores.max():.0f}")
    print(f"Artifacts saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
