# MoieRec

A personalized, explainable movie recommendation engine and web application evaluated on MovieLens 25M, powered by item-item collaborative filtering with evidence-based explanations.

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Status](https://img.shields.io/badge/Status-Local%20Demo-orange)](#overview)

---

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Highlights](#highlights)
- [Evaluation Results](#evaluation-results)
- [How It Works](#how-it-works)
- [Screenshots](#screenshots)
- [Run It Locally](#run-it-locally)
- [Backend API](#backend-api)
- [Repository Structure](#repository-structure)
- [Design Decisions & Lessons](#design-decisions--lessons)
- [Known Limitations](#known-limitations)
- [Data & Credits](#data--credits)
- [License](#license)

---

## Overview

**MoieRec** is a full-stack movie recommendation platform combining an audited offline machine learning pipeline (trained on MovieLens 25M) with a production-grade FastAPI backend and an interactive React 19 web application. It bridges the gap between offline recommender benchmarking and end-user interactive serving.

---

## Features

### 1. Home Feed & Hero Spotlight
- **Auto-Rotating Hero Carousel**: Cycles through top recommendations on a 10-second interval, featuring smooth crossfades, previous/next controls, and individual slide progress bars.
- **Smart Pause & Accessibility**: Automatically pauses rotation when the browser tab is hidden (`document.hidden`), when hovering over slide titles, overviews, or action buttons, and respects the user's `prefers-reduced-motion` system preference.
- **Source-Derived Honest Labeling**: Labeled `"Picked for you"` strictly when active candidates originate from the personalized recommendation feed; falls back to `"Popular right now"` if recommendations are empty, unseeded (< 3 picks), or in offline fallback.

### 2. Personalized Recommendation Rails
- **Picked for You**: The primary hybrid collaborative-filtering rail ($k=200$ Item-kNN CF with content smoothing for $K \ge 15$ picks), scored dynamically from the user's active picks.
- **Because You Liked \<Title\>**: Up to two dedicated content-similarity rails anchored to the user's most recent likes.
- **Ordering Contract**: The frontend sends `liked_movie_ids` ordered oldest-first (newest like at the tail of the list) so anchor rails reliably reflect the user's latest additions.
- **Order-Invariant Scoring**: The main "Picked for you" candidate selection, ranking order, and float scores are mathematically order-invariant (verified by automated tests in `test_personalized_api.py`).
- **De-Jumped Refresh**: Runtime updates to likes/dislikes on Home debounce for 1.5 seconds before updating rails to avoid jumpy UI layout shifts, while Home mount triggers an immediate refresh.

### 3. Unified Taste Signals (Like & Dislike)
- **Omnipresent Feedback**: Thumbs up (Like) and Thumbs down (Dislike) controls on the Hero Spotlight, Movie Cards, Movie Detail page, and My Library.
- **Shared State**: All controls synchronize through a single `UserTasteContext` in client memory and browser `localStorage`.
- **Decoupled from Lists**: Taste preferences operate completely independently from watch list statuses.

### 4. Per-Movie Watch Status Tracking
- **Four Distinct Statuses**: *Plan to watch*, *Watching*, *Watched*, and *Dropped*.
- **Portaled Dropdown Control**: Built with `createPortal` and dynamic viewport boundary clamping (`WatchStatusControl`) so menus never get clipped by overflow containers on movie cards or detail headers.
- **Catalog Exclusions**: *Watched* and *Dropped* titles are automatically hidden from Home rails and Explore catalog views, and passed via `exclude_movie_ids` to the recommendation engine.
- **Strict Separation of Concerns**: Watch status is **NEVER** used as a recommendation signal; only explicit positive likes drive collaborative filtering.
- **Legacy Migration**: Automatically migrates existing local watchlist entries to the *Plan to watch* status on first load.

### 5. Explore Catalog & Discovery
- **Multi-Select Genre Filter Chips**: Toggle multiple genres simultaneously with active chip badges, perfectly synchronized to the URL query string (`/explore?genres=Action,Sci-Fi`).
- **Flexible Filtering**: Backed by comma-separated genre support on `GET /api/movies/popular` alongside release decade filters and popularity sort orders.

### 6. Avoided Genres Preference
- **Onboarding & Taste Setting**: Pick avoided genres during initial onboarding or manage them anytime in My Taste.
- **Display-Only Filtering**: Acts as a client-side filter to prevent unwanted genres from appearing in rails; it **never** alters offline model weights, features, or backend scores.

### 7. Cold-Start Handling & Network Resilience
- **Skeleton Placeholders**: Shimmer skeleton cards render during feed loading.
- **Server Wake-Up Notice**: Informative notice explains brief backend delays when spinning up cold instances.
- **75s Budget & Auto-Retry**: Client fetchers incorporate a 75-second timeout window with an automatic retry to gracefully accommodate cloud spin-down cold starts.

### 8. Explainability & Library
- **"Why This?" Modal**: Honest attribution showing verified MovieLens co-viewer counts (*"N MovieLens viewers who liked X also liked this"*), shared tags, and percentile ranks. Prohibits fabricated marketing claims.
- **Detailed Movie Views**: High-resolution TMDB backdrops with soft gradient scrims, runtime, directors, release years, TMDB ratings, and content-similarity rails.
- **Command Palette Search**: Global `Ctrl + K` / `Cmd + K` search dialog with debounced catalog query matching.
- **My Library**: Dedicated tabs for Plan, Watching, Watched, Dropped, Liked, and Disliked, with real-time count badges, clear-tab modals, and liked-title genre frequency charts.

---

## Highlights

- **MovieLens 25M Scale**: Evaluated across 25,000,095 ratings spanning 62,423 titles from 162,541 users, reduced via iterative k-core filtering to an 18,276-movie benchmark catalog.
- **Leakage-Audited Temporal Split**: Enforces an 80/10/10 chronological per-user split with candidate masking to ensure evaluations test forward-in-time prediction rather than retrospective memorization.
- **Paired Bootstrap Confidence Intervals**: User-level 95% bootstrap intervals (1,000 resamples) accompany all metrics and paired model comparisons ($\Delta\text{NDCG@10}$).
- **Frozen One-Shot Final Evaluation**: All weights, hyperparameters, and feature blocks were locked on validation data; final numbers were gathered in a single, unretuned pass against guarded held-out partitions (`cold_final` and `test.parquet`).
- **Evidence-Based Explanations**: Recommendations present authentic co-viewer counts and feature overlaps; misleading marketing jargon like *"% match"* or *"acclaimed"* is prohibited by design.
- **Tie-Break Bias Discovered & Fixed**: Empirical audits revealed that default index tie-breaking silently injected a strong negative popularity prior (Spearman $r = -0.5340$), artificially inflating content metrics by +120%; replaced throughout with unbiased uniform random permutations.

---

## Evaluation Results

### Served Model Architecture
The production serving engine executes **item-based collaborative filtering** (asymmetric cosine similarity, $a=0.5$, shrinkage $\lambda=0.0$, top-$k=200$ neighbors) scored dynamically by averaging similarity vectors across the user's active picks.

The scoring schedule was selected on the validation simplex (`cold_dev`):
- **$K \le 14$ seed picks**: **Pure Item-Item CF** ($w_{\text{cf}} = 1.0, w_{\text{content}} = 0.0, w_{\text{pop}} = 0.0$).
- **$K \ge 15$ seed picks**: **90% CF / 10% Content** ($w_{\text{cf}} = 0.9, w_{\text{content}} = 0.1, w_{\text{pop}} = 0.0$).
- *In practice, the system is an adaptive neighborhood CF engine with light content smoothing at high pick counts, not a three-way blend (popularity receives zero weight).*

### Primary Benchmark Metrics

#### 1. Warm TEST Split ($N = 94,604$ evaluated users, final fit on Train + Validation)
| Model | NDCG@10 (95% CI) | Hit Rate@10 (95% CI) | Relative Lift vs Popularity |
| :--- | :---: | :---: | :---: |
| **Popularity** (`most_liked`) | 0.0523 [0.0515, 0.0530] | 0.2557 [0.2528, 0.2583] | Baseline |
| **Content Tier 2** *(snapshot features: tags/genome leak in evaluation)* | 0.0673 [0.0665, 0.0682] | 0.3197 [0.3168, 0.3227] | +28.75% |
| **Item-kNN CF** ($k=200, a=0.5$) | **0.0818 [0.0810, 0.0828]** | **0.3580 [0.3551, 0.3612]** | **+56.40%** |

#### 2. Cold-Start Final Long-Tail ($K = 5$ onboarding picks, top-200 popular movies excluded, $N = 2,372$ users)
| Model | NDCG@10 (95% CI) | Relative Lift vs Popularity |
| :--- | :---: | :---: |
| **Popularity** (`most_liked`) | 0.0402 [0.0365, 0.0438] | Baseline |
| **Item-kNN CF** (Served Hybrid v2) | **0.1051 [0.0991, 0.1118]** | **+161.28%** |

### Evaluation Visualizations
![Cold-Start All Candidates](docs/figures/ndcg_cold_start_all_candidates.png)
*Figure 1: NDCG@10 across all 18,277 candidate movies on held-out cold_final users as onboarding picks K increase.*

![Cold-Start Long-Tail](docs/figures/ndcg_cold_start_long_tail.png)
*Figure 2: NDCG@10 on the long-tail variant (excluding top-200 popular training movies), demonstrating CF's niche discovery.*

![Warm TEST Benchmark](docs/figures/warm_test_metrics_bar.png)
*Figure 3: Warm evaluation metrics at Top-10 on the held-out TEST split with 95% bootstrap error bars.*

### How It Was Evaluated
- **Per-User Temporal Split**: User histories were partitioned chronologically (80% train, 10% validation, 10% test) with seeded tie-breaking to avoid split bias.
- **Positive Threshold**: Only ratings $r \ge 4.0$ are counted as positive interactions; lower ratings are treated as non-relevant.
- **Paired Bootstrap CIs**: 1,000 bootstrap iterations compute user-level confidence bounds and paired comparison significance.
- **Leakage Audit with Shuffled Negative Control**: Item similarities built on randomly shuffled user interaction histories produced NDCG@10 of 0.05198 vs Popularity 0.05183, confirming zero artificial advantage.
- **One-Shot Frozen Run**: Execution completed in 974.45 seconds on held-out `cold_final` and warm `TEST` without hyperparameter re-tuning.

For detailed breakdowns, activity strata, and full comparison matrices, see [docs/ml/final_results.md](docs/ml/final_results.md).

---

## How It Works

```mermaid
flowchart TD
    subgraph DataPipeline["1. Offline Pipeline (MovieLens 25M)"]
        ML["MovieLens 25M CSVs"] --> Preprocess["recommender.preprocessing"]
        Preprocess --> Splits["Deterministic Temporal 80/10/10 Split"]
        Splits --> Train["train.parquet"]
        Splits --> Val["validation.parquet"]
        Splits --> GuardedTest["test.parquet (Guarded)"]
    end

    subgraph Evaluation["2. Offline Evaluation"]
        Train --> CF["Item-Item CF Co-occurrence Matrix"]
        Train --> Content["Tier 1 & Tier 2 Content Features"]
        Val --> Tune["Simplex Tuning (cold_dev)"]
        Tune --> FinalEval["One-Shot Frozen Evaluation"]
        GuardedTest -.-> FinalEval
    end

    subgraph ServingArtifacts["3. Serving Artifacts (data/serving/)"]
        Train --> ExportCat["export_catalog.py -> catalog.sqlite"]
        CF --> ExportModel["export_model_v2_artifacts.py -> model_v2/"]
        Content --> ExportModel
    end

    subgraph ServingRuntime["4. Online Serving"]
        ExportCat --> Backend["FastAPI Backend"]
        ExportModel --> Backend
        TMDB["TMDB API (Posters & Artwork)"] --> Backend
        Backend <-->|"POST /api/personalized/home"| Frontend["React 19 + TypeScript UI"]
    end
```

### The Serving Flow
1. **User Picks in Browser**: The user selects favorite movies during onboarding or browsing; IDs are stored in browser `localStorage`.
2. **Personalized Request**: Frontend issues `POST /api/personalized/home` sending the active array of liked MovieLens IDs.
3. **Item-kNN Scoring**: The FastAPI backend looks up precomputed top-200 neighbor arrays and computes average similarity scores across picks.
4. **Metadata & TMDB Enrichment**: High-ranking items are joined with `catalog.sqlite` and enriched with cached TMDB poster art and overviews.
5. **Feed Delivery with Evidence**: The feed returns ranked rails with reason codes, shared tags, and exact co-watcher counts (*"N MovieLens viewers who liked X also liked this"*).

---

## Screenshots

![Home Page](docs/figures/screenshots/home_personalized.png)
*Figure 4: Personalized home feed featuring the "Picked for You" recommendation rail and rank chips.*

![Why-This Explanation Modal](docs/figures/screenshots/why_this_modal.png)
*Figure 5: "Why This?" modal presenting verified MovieLens co-viewer evidence and shared feature attribution.*

![Library Management](docs/figures/screenshots/library.png)
*Figure 6: Personal library view managing user ratings, watchlist, and liked titles.*

![Explore Catalog](docs/figures/screenshots/explore.png)
*Figure 7: Explore catalog view with multi-genre and release decade filters.*

---

## Run It Locally

<details>
<summary><b>1. Prerequisites & Environment Setup</b></summary>

- **Python**: Version 3.10 to 3.14 (backend works on 3.10+, recommender dependencies tested on 3.10+ / 3.14).
- **Node.js**: Version 18+ and npm.
- **Git**: Installed and available in PATH.
- **TMDB API Key**: Free API key from [themoviedb.org](https://www.themoviedb.org/documentation/api).

Create two isolated Python virtual environments from the project root:
```powershell
# Backend runtime environment
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt

# Recommender ML environment
python -m venv .venv_recommender
.\.venv_recommender\Scripts\python.exe -m pip install -r recommender/requirements.txt
```
</details>

<details>
<summary><b>2. Data Pipeline & Model Artifact Generation</b></summary>

Run all recommender commands as modules from the project root using `.venv_recommender`:

```powershell
# Step 1: Download MovieLens 25M and verify checksum
.\.venv_recommender\Scripts\python.exe -m recommender.preprocessing.download_movielens --dataset ml-25m

# Step 2: Parse raw CSVs into normalized Parquet tables
.\.venv_recommender\Scripts\python.exe -m recommender.preprocessing.parse_movielens --dataset ml-25m

# Step 3: Build activity-filtered benchmark catalog (iterative k-core)
.\.venv_recommender\Scripts\python.exe -m recommender.preprocessing.build_benchmark --dataset ml-25m

# Step 4: Perform deterministic per-user temporal 80/10/10 split
.\.venv_recommender\Scripts\python.exe -m recommender.preprocessing.split_dataset --dataset ml-25m

# Step 5: Build ID mappings and content feature matrices
.\.venv_recommender\Scripts\python.exe -m recommender.preprocessing.build_content_features --dataset ml-25m

# Step 6: Export serving SQLite catalog
.\.venv_recommender\Scripts\python.exe -m recommender.serving.export_catalog

# Step 7: Build collaborative filtering neighbor cache and tune simplex schedule
.\.venv_recommender\Scripts\python.exe -m recommender.hybrid.tune_hybrid_v2

# Step 8: Export baseline and compact model_v2 serving artifacts
.\.venv_recommender\Scripts\python.exe -m recommender.serving.export_model_artifacts
.\.venv_recommender\Scripts\python.exe -m recommender.serving.export_model_v2_artifacts
```
</details>

<details>
<summary><b>3. TMDB Configuration & Cache Warming</b></summary>

Create `backend/.env` by copying `backend/.env.example` and set your TMDB API key:
```powershell
# Copy the template
Copy-Item backend/.env.example backend/.env
```
Edit `backend/.env` and replace `your_tmdb_api_key_here` with your valid key:
```env
TMDB_API_KEY=your_actual_tmdb_v3_key
```

Pre-warm the SQLite artwork cache (`data/serving/tmdb_cache.sqlite`) for top catalog titles:
```powershell
.\.venv\Scripts\python.exe -m app.scripts.warm_tmdb_cache --top 3000
```
</details>

<details>
<summary><b>4. Starting the Application Servers (Step-by-Step)</b></summary>

Open two separate terminal windows in your project root directory:

**Terminal 1 — FastAPI Backend**
```powershell
# Activate backend environment and run Uvicorn server
.\.venv\Scripts\uvicorn.exe app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
- **Interactive API Docs (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Service Health Check**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

**Terminal 2 — React Frontend**
```powershell
# Navigate to frontend and start Vite development server
cd frontend
npm install
npm run dev
```
- **Web Application URL**: [http://localhost:5173](http://localhost:5173)

*To stop the servers at any time, press `Ctrl + C` in each terminal window.*
</details>

<details>
<summary><b>5. Running Automated Tests</b></summary>

```powershell
# Run backend API test suite (61 tests, all passing)
.\.venv\Scripts\pytest.exe backend/tests

# Run recommender parity and evaluation test suite
.\.venv_recommender\Scripts\pytest.exe recommender/tests
```
</details>

<details>
<summary><b>6. Reproducing the Final Evaluation (Read-Only)</b></summary>

The frozen benchmark evaluation was executed via:
```powershell
.\.venv_recommender\Scripts\python.exe scratch/execute_final_evaluation.py
```
> [!WARNING]
> **One-Shot Guards**: The evaluation runner enforces strict guards. Accessing `test.parquet` or `cold_final` without `final=True` and a matching `frozen_config_id` raises a `PermissionError`. The benchmark script was designed to execute once; rerun only if verifying bitwise reproducibility.
</details>

<details>
<summary><b>7. Troubleshooting</b></summary>

- **ISP / DNS Blocking `api.themoviedb.org`**: Some ISPs block or throttle TMDB API requests, causing artwork timeouts or TLS reset errors. Switch your machine's DNS to `1.1.1.1` (Cloudflare) or `8.8.8.8` (Google), or connect through an alternative network.
- **SQLite Database Locked**: On Windows, Uvicorn holds an active file lock on `data/serving/catalog.sqlite` and `data/serving/tmdb_cache.sqlite`. You **must stop the backend** (`Ctrl + C`) before re-running `export_catalog.py` or `warm_tmdb_cache.py`.
- **Module Import Errors**: Always execute recommender scripts with the `-m` flag from the repository root (e.g. `python -m recommender.serving.export_catalog`) rather than executing files directly by file path, ensuring Python resolves package imports correctly.
</details>

---

## Repository Structure

```
MoieRec/
├── backend/                  # FastAPI REST API application
│   ├── app/
│   │   ├── api/              # Route endpoints (/health, /movies, /personalized)
│   │   ├── core/             # Environment configuration and settings
│   │   ├── db/               # SQLite catalog and TMDB cache clients
│   │   ├── schemas/          # Pydantic request and response schemas
│   │   ├── scripts/          # TMDB cache warming utilities
│   │   └── services/         # Recommender adapters and TMDB client
│   ├── requirements.txt      # Backend Python dependencies
│   └── tests/                # Endpoint integration tests
│
├── frontend/                 # React 19 + TypeScript web application
│   ├── src/
│   │   ├── components/       # Cinematic UI components and modals
│   │   ├── pages/            # Home, Explore, Library, and Onboarding
│   │   ├── services/         # API HTTP client functions
│   │   └── types/            # TypeScript interfaces
│   └── package.json          # Node dependencies and scripts
│
├── recommender/              # Decoupled machine learning engine
│   ├── baselines/            # Non-personalized popularity models
│   ├── collaborative/        # Item-item collaborative filtering
│   ├── config/               # Model hyperparameters and dataset settings
│   ├── content_based/        # TF-IDF, metadata features, and cosine scorers
│   ├── evaluation/           # Temporal split protocol, cold-start, metrics
│   ├── hybrid/               # Simplex fusion and tuning routines
│   ├── preprocessing/        # MovieLens ETL, k-core filtering, splitters
│   ├── results/              # Evaluation results (including results/final/)
│   ├── serving/              # Fast compact inference scorer and exporters
│   └── tests/                # Parity and regression test suite
│
├── docs/                     # Technical specifications and research reports
│   ├── figures/              # Generated benchmark charts and curves
│   └── ml/                   # Per-model design notes and final results
│
├── data/                     # Local data partitions (Git-ignored)
├── .env.example              # Environment variables template
└── README.md                 # Project documentation
```

---

## Design Decisions & Lessons

- **Genre-Only Content Is Nearly Useless as a Ranker**: Across an 18,276-movie catalog, coarse genre vectors achieve an NDCG@10 of only 0.0026 on warm test users. Thousands of titles share identical genre sets; genre alone cannot differentiate celebrated masterpieces from obscure low-budget releases.
- **Evaluator Tie-Break Bias Found & Fixed**: Early evaluations used default index tie-breaking, which unknowingly correlated with movie release order and introduced a hidden popularity prior (Spearman $r = -0.5340$), artificially inflating content NDCG by +120%. Replacing tie-breaking with seeded uniform random permutations (`random_perm`) eliminated this artifact across all benchmarks.
- **Popularity Is a Formidable Baseline**: The non-personalized `most_liked` model achieves an NDCG@10 of 0.0523 on warm test. Complex recommender architectures frequently lose to well-tuned popularity baselines unless disciplined co-occurrence signals are utilized.
- **Tier 2 Snapshot Tag Features Leak**: MovieLens tags and tag-genome scores reflect collective platform activity accumulated up to 2019. Recommending a 1995 film using tags applied in 2018 introduces temporal look-ahead; consequently, Tier 2 is strictly documented and reported as a snapshot experiment.
- **Negative Control Proved Authenticity**: When user interaction lists were randomly shuffled to destroy co-occurrence while preserving marginal popularity, item CF NDCG@10 plummeted from 0.0818 to 0.05198 (matching Popularity at 0.05183), proving the observed collaborative lift originates purely from real behavioral co-occurrence.

---

## Backend API

The FastAPI service exposes clean REST endpoints documented interactively via OpenAPI / Swagger at `/docs`.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check returning `{"status": "ok", "service": "MoieRec API"}`. |
| `POST` | `/api/personalized/home` | Personalized home feed rails for active user picks. Requires $\ge 3$ valid liked IDs. |
| `GET` | `/api/movies/popular` | Filtered catalog movies. Supports single or comma-separated `genre` (e.g. `Action,Sci-Fi`), `decade`, `year`, `sort`, `limit`, and `offset`. |
| `GET` | `/api/movies/{id}` | Detailed movie metadata enriched with TMDB credits and overview. |
| `GET` | `/api/movies/{id}/similar` | Content-only nearest neighbors based on Tier 2 genres and tags. |
| `GET` | `/api/movies/batch` | Batch metadata lookup for up to 100 movie IDs (`?ids=1,2,3`). |
| `GET` | `/api/search` | Fast substring catalog search with prefix prioritization (`?q=matrix&limit=10`). |
| `GET` | `/api/meta/filters` | Dynamic metadata listing all available genres and release decades. |
| `GET` | `/api/home` | Curated non-personalized fallback feed. |

### `POST /api/personalized/home` Parameters
- `liked_movie_ids: List[int]` *(required, max 50)*: MovieLens movie IDs picked by the user, ordered oldest-to-newest.
- `exclude_movie_ids: Optional[List[int]]` *(optional)*: MovieLens IDs to strictly exclude from recommendations (watched, dropped, or disliked).
- `limit: Optional[int]` *(optional, default 20, range 1–50)*: Maximum items to return in the main personalized row (frontend requests 40).

The backend test suite verifies complete parity, edge cases, honesty contracts, parameter validation, and order-invariance across **61 automated tests** (`pytest backend/tests`).

---

## Known Limitations

- **Dataset Horizon (MovieLens 25M)**: The underlying dataset concludes in November 2019. The catalog contains no modern releases, streaming-era titles, or post-2019 films.
- **Client-Side Guest Profiles**: Guest picks, watch statuses, and avoided genres persist strictly in the browser's `localStorage`. There are no user accounts, passwords, cloud databases, or cross-device syncing.
- **Evaluation Scope vs. Live UI Features**: The reported offline recommender evaluation (NDCG@10, Hit Rate@10, paired bootstrap intervals) benchmarks the offline machine learning algorithms against held-out MovieLens 25M test splits, not the interactive client-side UI features.
- **Metadata & Artwork Coverage**: Movie metadata and poster artwork are retrieved from TMDB; some niche or archival titles may lack artwork.
- **Simulated Onboarding Approximation**: The offline cold-start protocol approximates user onboarding using a user's first $K$ organic ratings, whereas live web onboarding involves active user browsing.
- **Binary Positivity in Neighborhood CF**: The collaborative model treats ratings $\ge 4.0$ as positive approvals and ignores sub-4.0 distinctions. Latent factor modeling (ALS, SVD) and explicit dislike handling represent avenues for extension.

---

## Data & Credits

- **MovieLens 25M**: Provided by GroupLens Research at the University of Minnesota.  
  *Citation*: F. Maxwell Harper and Joseph A. Konstan. 2015. *The MovieLens Datasets: History and Context*. ACM Transactions on Interactive Intelligent Systems (TiiS) 5, 4: 19:1–19:19. Dataset available at [files.grouplens.org](https://files.grouplens.org/datasets/movielens/ml-25m.zip). Data is not redistributed in this repository.
- **TMDB API Notice**: This product uses the TMDB API but is not endorsed or certified by TMDB.

---

## License

License: Not yet specified (TBD).
