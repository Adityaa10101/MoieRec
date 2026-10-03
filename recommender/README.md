# MoieRec Recommender Pipeline & Evaluation Foundation

Dataset-agnostic, config-driven data processing pipeline, activity filtering, chronological splitting, feature engineering, and evaluation foundation for the MoieRec movie recommendation platform.

---

## Architecture Overview

```
recommender/
├── config/
│   └── datasets.yaml                 # Single source of truth for datasets & split configs
├── preprocessing/
│   ├── adapters/                     # Dataset adapters (normalized table interface)
│   │   ├── base.py                   # NormalizedDataset dataclass & BaseDatasetAdapter
│   │   └── csv_adapter.py            # MovieLens CSV adapter (ml-25m & ml-latest-small)
│   ├── download_movielens.py         # Verified streaming downloader with MD5 & disk checks
│   ├── validate_movielens.py         # Structural, constraint, and referential integrity validator
│   ├── parse_movielens.py            # Full catalog Parquet converter & catalog stats
│   ├── build_benchmark.py            # Iterative k-core filter & sensitivity grid analyzer
│   ├── split_dataset.py              # Vectorized per-user chronological split & cold-start partition
│   ├── build_content_features.py     # ID mappings, Tier 1 baseline, & Tier 2 snapshot features
│   └── utils.py                      # Common disk, hash, and config utilities
├── tests/                            # Comprehensive pytest suite
└── requirements.txt                  # Pinned Phase 2C dependencies
```

---

## Environment & Dependency Isolation

To protect the production backend environment, the recommender pipeline operates in a dedicated virtual environment (`.venv_recommender`):

```powershell
# 1. Create dedicated recommender environment (if not already created)
python -m venv .venv_recommender

# 2. Activate environment
.\.venv_recommender\Scripts\Activate.ps1

# 3. Install pinned Phase 2C dependencies
pip install -r recommender/requirements.txt
```

### Pinned Dependencies
- `numpy==2.5.2`
- `pandas==3.0.5`
- `pyarrow==24.0.0`
- `scipy==1.18.1`
- `scikit-learn==1.9.1`
- `pyyaml==6.0.3`
- `pytest==9.1.1`
- `certifi==2026.7.22`

---

## Exact Pipeline Command Sequence

All scripts are completely dataset-agnostic and accept `--dataset <name>` (`ml-25m` or `ml-latest-small`).

### Development / Smoke Test Execution (`ml-latest-small`)

Run this first to verify end-to-end correctness in seconds:

```powershell
# 1. Download & verify archive
python -m recommender.preprocessing.download_movielens --dataset ml-latest-small

# 2. Validate structural integrity & foreign keys
python -m recommender.preprocessing.validate_movielens --dataset ml-latest-small

# 3. Parse full catalog Parquet tables & compute catalog stats
python -m recommender.preprocessing.parse_movielens --dataset ml-latest-small

# 4. Build benchmark subset via iterative k-core & evaluate threshold grid
python -m recommender.preprocessing.build_benchmark --dataset ml-latest-small

# 5. Split benchmark into train/val/test + cold-start partition & compute train stats
python -m recommender.preprocessing.split_dataset --dataset ml-latest-small

# 6. Extract ID mappings, Tier 1 baseline, and Tier 2 snapshot features
python -m recommender.preprocessing.build_content_features --dataset ml-latest-small

# 7. Run test suite
pytest recommender/tests/ -v
```

---

### Primary Benchmark Execution (`ml-25m`)

```powershell
# 1. Download & verify 25M archive (~262 MB zip, verified against official MD5)
python -m recommender.preprocessing.download_movielens --dataset ml-25m

# 2. Validate MovieLens 25M catalog, constraints, and genome coverage
python -m recommender.preprocessing.validate_movielens --dataset ml-25m

# 3. Parse normalized full catalog Parquet tables
python -m recommender.preprocessing.parse_movielens --dataset ml-25m

# 4. Build benchmark subset (iterative k-core 50/20 & 3x3 threshold grid)
python -m recommender.preprocessing.build_benchmark --dataset ml-25m

# 5. Execute vectorized chronological 80/10/10 split & cold-start user partition
python -m recommender.preprocessing.split_dataset --dataset ml-25m

# 6. Build ID mappings, Tier 1 baseline features, and Tier 2 snapshot features
python -m recommender.preprocessing.build_content_features --dataset ml-25m

# 7. Execute test suite
pytest recommender/tests/ -v

# 8. Export serving catalog to SQLite (Phase 2E.2 serving slice)
python -m recommender.serving.export_catalog
```

---

## Data Structure & Storage Layout

Processed data is stored under `data/processed/<dataset>/` and strictly excluded from git:

- `full/`: Complete cleaned catalog tables (`ratings.parquet`, `movies.parquet`, `tags.parquet`, `links.parquet`, `genome_scores.parquet`, `genome_tags.parquet`, `dataset_summary.json`).
- `benchmark/`: Iterative k-core filtered subset for model experiments (`ratings.parquet`, `movies.parquet`, `tags.parquet`, `links.parquet`, `dataset_summary.json`, `grid_analysis.json`).
- `splits/`: Deterministic evaluation partitions (`train.parquet`, `validation.parquet`, `test.parquet`, `cold_start_users.parquet`, `train_movie_stats.parquet`, `train_user_stats.parquet`, `split_metadata.json`).
- `id_mappings/`: Stable non-contiguous index mappings (`movie_id_to_full_idx.parquet`, `movie_id_to_benchmark_idx.parquet`, `user_id_to_benchmark_idx.parquet`).
- `features/`: Content representations (`tier1_baseline_features.npz`, `tier2_tag_tfidf.npz`, `tier2_genome_matrix.npy`, `tier2_genome_mask.npy`, `feature_metadata.json`).

---

## Leakage Prevention Rules

1. **Modeling & Candidate Statistics:** Popularity counts, mean ratings, and positive ratios are computed strictly from the `TRAIN` split (`splits/train_movie_stats.parquet`). Full catalog statistics are labeled descriptive only.
2. **Chronological Splitting:** Enforces strict causality per user history (`train_max <= val_min <= test_min`).
3. **Candidate Pool Masking:** For validation evaluation, user train items are excluded from candidate pools. For test evaluation, user train and validation items are excluded.
4. **Tier 2 Snapshot Caveat:** Tag TF-IDF and Tag Genome were aggregated over history up to Nov 2019 and must be evaluated as a separate snapshot experiment.
