# MoieRec — Personalized & Explainable Movie Recommender

MoieRec is a personalized, explainable movie recommendation web application developed as a serious full-stack machine learning college mini-project.

Instead of operating as a static demonstration, MoieRec integrates content-based filtering, collaborative filtering, and an explainable hybrid re-ranking pipeline served via a FastAPI backend to an interactive cinematic React frontend.

---

## Current Status: Phase 1 (Foundation)

> [!NOTE]
> **Implemented in Phase 1 (Current):**
> - Modular repository structure (`frontend/`, `backend/`, `recommender/`, `data/`, `docs/`)
> - Frontend foundation: React 19, Vite, TypeScript, Tailwind CSS, Framer Motion, Lucide React
> - Service-oriented API client and UI/service decoupling
> - Backend foundation: FastAPI, Pydantic, Uvicorn, CORS configuration
> - Operational health check endpoint: `GET /api/health`
> - Structured recommender package layout with submodule contracts
> - Partitioned data folders with `.gitkeep` and Git exclusion patterns
> - Local development setup and environment variable configuration

> [!IMPORTANT]
> **Planned for Later Phases (Not Yet Implemented):**
> - User authentication & JWT session management
> - MongoDB models and database connection
> - TMDB API integration and live poster/backdrop ingestion
> - MovieLens dataset downloading and offline ETL pipelines
> - Collaborative filtering models (SVD, ALS)
> - Content-based NLP vectorization (TF-IDF, Embeddings)
> - Hybrid score combination, serendipity ranking, and explanations
> - Final Home, Movie Details, Movie DNA, and Discovery UI pages

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
│   │   ├── db/           # Database connectors (MongoDB / Motor)
│   │   ├── models/       # Database document models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # Business logic & recommender adapters
│   │   └── main.py       # FastAPI application entry point
│   └── requirements.txt
│
├── recommender/          # ML Engine Package (Decoupled from API)
│   ├── preprocessing/    # Cleaning, sparse matrix building, train/test split
│   ├── content_based/    # TF-IDF, metadata embeddings, cosine similarity
│   ├── collaborative/    # Matrix factorization (SVD, ALS)
│   ├── hybrid/           # Weighted fusion, re-ranking, and explanations
│   ├── evaluation/       # Top-K ranking, RMSE, coverage, diversity metrics
│   └── models/           # Checkpoints and serialized model artifacts
│
├── data/                 # Dataset partitions (Git-ignored)
│   ├── raw/              # Original MovieLens & TMDB dumps
│   ├── processed/        # Tokenized matrices & cleaned datasets
│   └── external/         # External ID mappings & taxonomies
│
├── docs/                 # Architectural notes & developer guides
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

### Machine Learning / Recommender Stack (Planned)
- **Scientific Computing**: NumPy, Pandas, SciPy (Sparse matrices)
- **Algorithms**: Scikit-Learn (TF-IDF, SVD), Implicit / Surprise
- **Evaluation**: Custom ranking suite (Precision@K, Recall@K, NDCG@K, Coverage, Diversity)

### Planned Data Sources
1. **MovieLens (100k / 1M)**: User-item rating matrices and timestamps for collaborative filtering and offline benchmarking.
2. **The Movie Database (TMDB) API**: Dynamic movie artwork, overviews, cast, crew, keywords, and release dates for content-based semantics and rich UI presentation.

---

## Local Development Commands

### 1. Environment Configuration
Copy the environment template:
```bash
# Root
cp .env.example .env
```

### 2. Backend (FastAPI)
```bash
# Create virtual environment (one-time)
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Start backend server
uvicorn app.main:app --app-dir backend --reload --port 8000
```
- API Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

### 3. Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
- Client runs at: `http://localhost:5173`

---

## Future Implementation Phases

1. **Phase 2A (Current Foundation)**: Clean architecture, modular packages, verified local runtimes.
2. **Phase 2B (Data Engineering & Preprocessing)**: MovieLens dataset download, clean ETL pipeline, sparse matrix generation, and metadata tokenization.
3. **Phase 3 (Core ML Models)**: Content-based similarity engine and collaborative matrix factorization.
4. **Phase 4 (Hybrid Pipeline & Explainability)**: Score fusion, diversity re-ranking, and explanation extraction.
5. **Phase 5 (Database & Backend Services)**: MongoDB integration, TMDB proxy services, user watchlist/interaction persistence.
6. **Phase 6 (Cinematic Frontend & Discovery UI)**: Movie cards, recommendation carousels, taste profiles, interactive explanation badges, and discovery controls.
