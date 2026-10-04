# MoieRec — Personalized & Explainable Movie Recommender

MoieRec is a personalized, explainable movie recommendation web application developed as a serious full-stack machine learning college mini-project.

Instead of operating as a static demonstration, MoieRec integrates content-based filtering, collaborative filtering, and an explainable hybrid re-ranking pipeline served via a FastAPI backend to an interactive cinematic React frontend.

---

## Current Status: Phase 2G-Lite (Item-Item CF + Hybrid v2)

> [!NOTE]
> **Fully Implemented (Phases 1 – 2G-Lite):**
> - React 19 + Vite + TypeScript + Tailwind CSS + Framer Motion cinematic frontend
> - FastAPI backend with TMDB metadata proxy, SQLite catalog, and offline hybrid scoring
> - Content-based TF-IDF vectorisation over genres, tags, and MovieLens genome features
> - Item-item collaborative filtering with TF-IDF normalisation and min-support guard
> - Hybrid v2 recommender: 3-component simplex blend (CF + content + popularity), K-adaptive weight schedule
> - Cold-Start Protocol v2 evaluation (NDCG@K, Recall@K, long-tail variant, 1000 bootstrap resamples)
> - Offline parity regression tests (offline ↔ serving score match to 1e-5)
> - Explainability: nearest pick, shared features, CF evidence, honest reason codes, Why-This modal
> - Honest rank semantics: "Top N% pick" chip (never a probability or match %)

> [!IMPORTANT]
> **Out of Scope (by design):**
> - User authentication & JWT session management
> - MongoDB models and database connection
> - Matrix factorization / ALS / SVD
> - MMR diversity re-ranking
> - Collaborative filtering with session persistence

---

## Planned Architecture

```
MoieRec/
│
├── frontend/             # Single Page Application (React + Vite + TypeScript)
│   ├── src/
│   │   ├── components/   # Reusable UI & presentation widgets
│   │   ├── pages/        # Route page components
│   │   ├── layouts/      # App wrappers & navigational shells
│   │   ├── hooks/        # Custom state & query hooks
│   │   ├── services/     # Decoupled API HTTP clients
│   │   ├── types/        # TypeScript interfaces & types
│   │   ├── data/         # Static app constants & metadata
│   │   ├── utils/        # Helper utility functions
│   │   ├── animations/   # Framer Motion transition variants
│   │   ├── assets/       # Static assets & icons
│   │   ├── App.tsx       # Root component
│   │   └── main.tsx      # Entry point
│   ├── package.json
│   └── vite.config.ts
│
├── backend/              # Asynchronous REST API (FastAPI)
│   ├── app/
│   │   ├── api/          # Route controllers & endpoints
│   │   ├── core/         # Settings & environment configuration
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # Business logic & recommender adapters
│   │   └── main.py       # FastAPI application entry point
│   └── requirements.txt
│
├── recommender/          # ML Engine Package (decoupled from API)
│   ├── preprocessing/    # Cleaning, sparse matrix building, train/test split
│   ├── content_based/    # TF-IDF, metadata embeddings, cosine similarity
│   ├── collaborative/    # Item-item CF (cosine + min-support guard)
│   ├── hybrid/           # Weighted simplex fusion (v1, v1.1, v2)
│   ├── evaluation/       # Cold-Start Protocol v2, NDCG@K, bootstrap CIs
│   ├── serving/          # HybridScorer, export scripts, latency benchmark
│   ├── config/           # hybrid_v1.yaml, hybrid_v2.yaml
│   ├── tests/            # Parity and regression tests
│   └── results/          # Offline evaluation result files
│
├── data/                 # Dataset partitions (Git-ignored)
│   ├── raw/              # Original MovieLens & TMDB dumps
│   ├── processed/        # Tokenized matrices & cleaned datasets
│   ├── serving/          # SQLite catalog + model artifacts (git-ignored)
│   └── external/         # External ID mappings & taxonomies
│
├── docs/                 # Architectural notes & developer guides
│   └── ml/               # Per-model documentation
├── .env.example          # Environment variables template
├── .gitignore            # Git exclusion rules
└── README.md             # Project documentation
```

---

## Technology Stack

### Frontend
- **Framework**: [React 19](https://react.dev/) + [Vite](https://vite.dev/)
- **Language**: [TypeScript](https://www.typescriptlang.org/)
- **Styling**: [Tailwind CSS v4](https://tailwindcss.com/)
- **Motion**: [Framer Motion](https://www.framer.com/motion/)
- **Icons**: [Lucide React](https://lucide.dev/)

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Server**: [Uvicorn](https://www.uvicorn.org/)
- **Validation**: [Pydantic v2](https://docs.pydantic.dev/) & [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Environment**: Python 3.14+ (or >=3.10)

### Machine Learning / Recommender Stack
- **Scientific Computing**: NumPy, Pandas, SciPy (sparse matrices)
- **Algorithms**: Scikit-Learn (TF-IDF cosine similarity), custom item-item CF
- **Evaluation**: Custom Cold-Start Protocol v2 (NDCG@K, Recall@K, long-tail variant, 1,000 bootstrap resamples)
- **Hybrid Fusion**: K-adaptive simplex blend (CF + content + popularity)
- **Serving**: HybridScorer with compact top-K arrays (~42 MB CF overhead, p50 ~65 ms)

### Data Sources
1. **MovieLens 25M**: User-item rating matrices and timestamps for offline benchmarking. Partitioned into train / cold_dev / cold_final splits.
2. **The Movie Database (TMDB) API**: Dynamic movie artwork, overviews, cast, crew, keywords, and release dates for content-based semantics and rich UI presentation.

---

## Local Development Commands (Phase 2E.2 Serving Slice)

### 1. Build Serving Artifacts (Recommender Environment)
Generate `data/serving/catalog.sqlite` and `data/serving/model_v2/`:
```powershell
# Using .venv_recommender:
# 1. Export catalog sqlite
.\.venv_recommender\Scripts\python.exe -m recommender.serving.export_catalog

# 2. Build item-item CF cache and run hybrid v2 tuning on cold_dev
.\.venv_recommender\Scripts\python.exe -m recommender.collaborative.item_cf
.\.venv_recommender\Scripts\python.exe -m recommender.hybrid.tune_hybrid_v2

# 3. Export v1.1 serving artifacts
.\.venv_recommender\Scripts\python.exe recommender/serving/export_model_artifacts.py

# 4. Export v2 compact CF arrays
.\.venv_recommender\Scripts\python.exe -m recommender.serving.export_model_v2_artifacts
```

### 2. Backend Environment & TMDB Configuration
Create `backend/.env` (git-ignored) with your TMDB v3 API key:
```bash
TMDB_API_KEY=your_tmdb_v3_api_key_here
HOST=127.0.0.1
PORT=8000
```

### 3. Pre-Warm TMDB Cache (Backend Environment)
Warm the SQLite cache (`data/serving/tmdb_cache.sqlite`) with TMDB metadata for the top-popular movies:
```powershell
# Run from backend/ directory or with backend in PYTHONPATH:
cd backend
..\.venv\Scripts\python.exe -m app.scripts.warm_tmdb_cache --top 3000
cd ..
```

### 4. Start Backend Server
```powershell
# Using .venv:
.\.venv\Scripts\uvicorn.exe app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```
- API Documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/health`
- Personalized feed: `POST http://127.0.0.1:8000/api/personalized/home`
- Home feed: `http://127.0.0.1:8000/api/home`

### 5. Start Frontend Dev Server
```bash
cd frontend
npm install
npm run dev
```
- Client runs at: `http://localhost:5173` (proxies or connects to backend at `http://127.0.0.1:8000`)

---

## Implementation Phases

1. **Phase 1 (Foundation)**: Clean architecture, modular packages, verified local runtimes.
2. **Phase 2A–2B (Data Engineering)**: MovieLens 25M download, ETL pipeline, sparse matrix generation, metadata tokenization.
3. **Phase 2C–2E (Content-Based + Serving)**: TF-IDF vectorisation, cosine similarity, FastAPI serving slice, TMDB integration.
4. **Phase 2F–2F.2 (Hybrid v1 / v1.1)**: Popularity + content hybrid, Cold-Start Protocol v2, alpha schedule tuning, long-tail reconciliation.
5. **Phase 2G-Lite (Item-Item CF + Hybrid v2)**: Item-item collaborative filtering, 3-component simplex blend, adoption evaluation, frontend Why-This CF evidence. ← **Current**
