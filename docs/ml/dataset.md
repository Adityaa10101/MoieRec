# Dataset Architecture & Selection: MovieLens 25M

## 1. Primary Dataset Decision: MovieLens 25M

MoieRec adopts **MovieLens 25M (ml-25m)**, released by GroupLens Research in November 2019, as its primary benchmark dataset.

- **Official Source:** `https://files.grouplens.org/datasets/movielens/ml-25m.zip`
- **Official MD5 Checksum:** `6b51fb2759a8657d3bfcbfc42b592ada`
- **Archive Size:** 261,978,986 bytes (~261.98 MB compressed, ~1.1 GB uncompressed)
- **Population:** 25,000,095 ratings across 62,423 movies by 162,541 users (Jan 09, 1995 to Nov 21, 2019).

### Rapid Development & Smoke-Test Subset: MovieLens Latest-Small
For development, CI test suites, and rapid local iteration, the pipeline supports **MovieLens Latest-Small (ml-latest-small)**:
- **Official Source:** `https://files.grouplens.org/datasets/movielens/ml-latest-small.zip`
- **Official MD5 Checksum:** `31a303aabbc519bd33d025e44d6c2570`
- **Population:** 100,836 ratings across 9,742 movies by 610 users.
- Shares the identical CSV schema with `ml-25m` (excluding genome tables).

---

## 2. Why MovieLens 25M (and Why Not ML-1M or ML-32M)

### Key Advantages of ML-25M:
1. **Direct TMDB & IMDb ID Linking (`links.csv`):**
   `links.csv` provides direct, unambiguous foreign key mapping from MovieLens `movieId` to `tmdbId` and `imdbId`. This allows the backend to enrich offline collaborative embeddings with live TMDB posters, backdrops, trailers, cast lists, and director credits.
2. **Rich Tag Applications (`tags.csv`):**
   Contains 1,093,360 free-text user tags, enabling vocabulary-level semantic TF-IDF representations.
3. **The Tag Genome Matrix (`genome-scores.csv`, `genome-tags.csv`):**
   Provides dense machine-learned tag relevance scores for 1,128 semantic dimensions across 13,816 movies, capturing subtle film attributes (e.g., "atmospheric", "philosophical", "cyberpunk", "nonlinear").
4. **Scale & Statistical Power:**
   Substantially larger catalog (62k movies vs. 3.9k in ML-1M) and user base (162k users vs. 6k in ML-1M), enabling realistic long-tail retrieval and sparsity dynamics.

### Datasets Explicitly Excluded:
- **MovieLens 1M (ML-1M):** Excluded because it lacks `links.csv` (no direct TMDB IDs), lacks user tags and the Tag Genome, and contains demographic features (age, gender, occupation, zip-code) that are not collected by MoieRec.
- **MovieLens 32M (ML-32M):** Excluded due to excessive memory footprint during local development without providing significant structural differences over 25M.
- **Demographic Datasets:** In accordance with MoieRec privacy principles, no demographic, biometric, or geographic user profiling is utilized. All personalization is derived purely from behavioral interaction signals and content attributes.

---

## 3. Catalog Limitations & Real-World Reality

1. **Temporal Cutoff (November 2019):**
   The ML-25M dataset was frozen on November 21, 2019. It contains zero releases from 2020 to present (e.g., *Dune: Part Two*, *Oppenheimer*, *Past Lives*).
2. **TMDB Cold-Start Split:**
   In production MoieRec, recent films ingested directly from TMDB API will have rich metadata (genres, cast, synopsis, posters, popularity metrics) but zero collaborative ratings in the historical MovieLens matrix.
   - Consequently, newly released movies will initially be served via **Tier 1 / Tier 2 Content-Based Models** and **Popularity Models**, and fold into collaborative representations as active platform users rate them.
3. **Genome Coverage:**
   The Tag Genome covers 13,816 of the 62,423 movies (~22.1% of the full catalog; primarily well-known theatrical releases). Movies lacking genome vectors are tracked via an explicit boolean coverage mask (`tier2_genome_mask.npy`) without synthetic value imputation.

---

## 4. TMDB Mapping Plan

MoieRec implements a two-stage identity resolution architecture:

1. **Primary Key Alignment via `links.csv`:**
   Each MovieLens `movieId` is matched directly to its official `tmdbId`.
   - In ML-25M, 62,316 of 62,423 movies (99.83%) possess direct `tmdbId` mappings. Only 107 movies (0.17%) have missing TMDB IDs.
2. **Secondary Fallback (Title + Year Matcher - Future Phase):**
   For records where `tmdbId` is null, a normalized search query matching `(clean_title, year)` against the TMDB Search API with a Levenshtein distance confidence threshold (>= 0.90) and persistent disk caching will be used.
3. **No External Calls in Phase 2C:**
   In Phase 2C, zero external HTTP calls to TMDB or third-party APIs are made. The pipeline operates entirely offline.

---

## 5. Catalog Partitioning: Full vs. Benchmark

| Property | Full Catalog (`data/processed/.../full/`) | Benchmark Subset (`data/processed/.../benchmark/`) |
| :--- | :--- | :--- |
| **Purpose** | Comprehensive metadata, search indexing, descriptive statistics, catalog coverage analysis. | Model training, validation tuning, and offline benchmark evaluation. |
| **Filtering** | None. All movies and ratings preserved. | Iterative k-core activity filtering (converged). |
| **Default Thresholds** | None | `min_user_ratings: 50`, `min_movie_ratings: 20`. |
| **Ratings Count** | 25,000,095 ratings | 22,913,458 ratings |
| **Users Count** | 162,541 users | 102,389 users |
| **Movies Count** | 62,423 movies | 18,277 movies |
| **Data Integrity** | Preserved permanently in Parquet format. | Reproducible from config via `build_benchmark.py`. |

### 5.1 Verified Split Populations (ML-25M Benchmark)

- **Total Benchmark Population:** 102,389 users, 18,277 movies, 22,913,458 ratings.
- **Cold-Start Partition (5.0% held out):** 5,119 users (1,166,644 ratings).
  - `cold_dev` (50% deterministic split): **2,559 users** (used for dev/tuning).
  - `cold_final` (50% deterministic split): **2,560 users** (strictly guarded behind `final=True` for final benchmark).
- **Main Splits Population:** **97,270 users** across all splits:
  - **`train.parquet`:** 97,270 users, 17,398,080 ratings (80.0%), 18,275 distinct movies (2 movies have 0 train ratings). *(Note: Earlier text mentioned "138,493 training users" in a report draft; this was a clerical error. The actual verified count is exactly 97,270 users).*
  - **`validation.parquet`:** 97,270 users, 2,174,367 ratings (10.0%). Evaluated validation users with $\ge 1$ positive rating ($\ge 4.0$): **94,303 users** (2,967 users have 0 positive ratings and are excluded from ranking metric denominators per protocol).
  - **`test.parquet`:** 97,270 users, 2,174,367 ratings (10.0%). 94,604 users with $\ge 1$ positive rating. (Strictly reserved for final frozen evaluation).

---

## 6. Raw Data Hygiene & Verification

1. **Storage Location:** Raw zip archives and unpacked CSVs reside in `data/raw/<dataset>/` and are strictly excluded from version control (`.gitignore`).
2. **Immutability:** Raw files are read-only and never modified in place.
3. **Integrity Verification:** Every downloaded archive is verified against GroupLens published MD5 hashes.
4. **Pre-flight Disk Check:** Available free disk space is verified before initiating any download.
