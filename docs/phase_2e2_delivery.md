# Phase 2E.2 — Real Catalog Slice: Delivery Notes

> **Scope**: Thin vertical slice — Popularity API + TMDB Cache + Real Home/Search/Detail  
> No change to recommender models, evaluation code, splits, or benchmark results.

---

## What Was Delivered

### A — Catalog Export

| Item | Value |
|------|-------|
| Source | `data/processed/ml-25m/benchmark/movies.parquet` + `links.parquet` + `movie_stats.parquet` |
| Output | `data/serving/catalog.sqlite` (gitignored) |
| Total movies exported | 18,277 |
| Movies without `tmdb_id` | 18 (0.10 %) — excluded from all API endpoints |
| Impact on Top-1000 | 0 — all top-1000 have a TMDB ID |
| Script | `recommender/serving/export_catalog.py` |
| Title normalization | `recommender/serving/normalize.py` (stdlib only) |

The export resolves `data/serving/` relative to the project root. `.gitignore` entry added so the generated SQLite file is never committed.

---

### B — Backend API

#### New files

| File | Purpose |
|------|---------|
| `backend/app/services/tmdb.py` | TMDB v3 async client — 8-semaphore, backoff on 429/5xx, adult filter, graceful degradation |
| `backend/app/schemas/movies.py` | Pydantic schemas with honesty contract (see below) |
| `backend/app/api/endpoints/movies.py` | `/home`, `/movies/popular`, `/movies/{id}`, `/search` |
| `backend/app/db/catalog.py` | Read-only SQLite wrapper with `check_same_thread=False` |
| `backend/app/db/tmdb_cache.py` | TTL cache (30d ok / 24h error) with `check_same_thread=False` |
| `backend/app/scripts/warm_tmdb_cache.py` | CLI warm-up for top-N movies |
| `backend/tests/test_movies_api.py` | 29 tests, all pass |

#### Honesty contract (enforced by Pydantic schema)

```python
score: None = None         # no personalized score
match_percent: None = None # null — no personalization
reason_codes: List[str] = []
explanation: None = None
source: str = "popularity" # Model 0 — popularity only
```

These fields are **typed as `None`** (not `Optional[float]`), preventing any code path from ever setting them.

#### CORS

`HOST=127.0.0.1` (localhost only). `CORS_ORIGINS` in `backend/app/core/config.py` restricts cross-origin to `http://localhost:5173` by default.

#### Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | `{"status": "ok", "service": "MoieRec API"}` |
| `GET /api/home` | Hero + 5 named rows (Popular, Sci-Fi, Drama, 2010s, 1990s), all sorted by `train_positive_count DESC` |
| `GET /api/movies/popular` | Params: `genre`, `decade`, `limit` (1–100), `offset` |
| `GET /api/movies/{movie_id}` | Full detail with TMDB enrichment. 404 if no `tmdb_id`. |
| `GET /api/search?q=&limit=` | Normalized title match (`LIKE %q%`), ranked by popularity. Min 2 chars (FastAPI validates). |

All endpoints exclude movies with `tmdb_id IS NULL` from responses.

#### TMDB Cache

- Storage: `data/serving/tmdb_cache.sqlite` (gitignored)
- TTL: 30 days (ok) / 24 hours (error/not_found)
- Adult content: filtered — stored as `not_found` sentinel
- Warm-up: `python -m app.scripts.warm_tmdb_cache --top 3000` from `backend/`

---

### C — Frontend

#### API Layer

| File | Purpose |
|------|---------|
| `frontend/src/api/types.ts` | TypeScript types matching `MovieOut` schema |
| `frontend/src/api/client.ts` | Typed fetchers using `VITE_API_BASE_URL` + AbortController |

#### Updated Components

| Component | Change |
|-----------|--------|
| `HeroSpotlight.tsx` | Uses `ApiMovie`, removed fake match score, TMDB `vote_average` labelled as "TMDB" |
| `MovieCard.tsx` | Uses `ApiMovie`, removed fake match badge, null-safe poster placeholder |
| `RecommendationRow.tsx` | Accepts `ApiMovie[]`, label changed to "MovieLens · Model 0 (Popularity)" |
| `SearchPalette.tsx` | Calls `/api/search` with 250ms debounce + AbortController, falls back to mock on failure with visible warning |
| `TasteRadarDock.tsx` | Removed fake "Taste Vector Active" claim; shows only real local state (watchlist/liked count) |
| `Footer.tsx` | Added required TMDB attribution + GroupLens/MovieLens credit |

#### Updated Pages

| Page | Change |
|------|--------|
| `HomePage.tsx` | Fetches `/api/home`, skeleton loading, offline fallback with "Demo data" banner |
| `MovieDetailPage.tsx` | Fetches `/api/movies/{id}`, skeleton + 404 handling, no fabricated match score |

#### Honesty Audit

- **No** `match_percent`, `match_score`, or percentage values displayed anywhere
- **No** "Because you liked...", "Based on your taste...", or personalization claims
- **No** fake explanation bullets (Why MoieRec recommends...)
- TMDB `vote_average` always shown with label "TMDB rating" or "★ X.X TMDB"
- Row subtitles all say "MovieLens" or "most-liked by MovieLens viewers"
- `source: "popularity"` is present in every `MovieOut` response

---

### D — Tests

```
29 passed, 0 failed, 1 warning (httpx deprecation — benign, not actionable)
```

Test classes:
- `TestHomeEndpoint` — shape, rows, labels
- `TestHonestyContract` — no fabricated scores in home/search/detail
- `TestAdultFilter` — adult payload correctly marked
- `TestMissingTmdbId` — excluded from popular/search/detail
- `TestGracefulDegradation` — TMDB offline returns catalog-only data (not 500)
- `TestCacheTTL` — miss → put → get → expired
- `TestTitleNormalization` — trailing article, year strip, aka removal, accent fold
- `TestSearchRanking` — min length enforced (422), results found, popularity ordering

---

## How To Run

### 1. Export the catalog (recommender venv)

```powershell
.venv_recommender\Scripts\python.exe -m recommender.serving.export_catalog
```

### 2. Warm the TMDB cache (backend venv, optional but recommended)

```powershell
.venv\Scripts\python.exe -m app.scripts.warm_tmdb_cache --top 3000
```

### 3. Run the backend

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Run tests

```powershell
.venv\Scripts\python.exe -m pytest backend/tests/test_movies_api.py -v
```

### 5. Run the frontend

```powershell
Set-Location frontend; npm run dev
```

Make sure `frontend/.env` has:
```
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

---

## Phase 2E.2 Interactive & Personalization Delivery

### Frontend & API Enhancements Delivered

1. **Popularity & Discovery**:
   - Comma-separated multi-genre filtering supported on `GET /api/movies/popular`.
   - Multi-select genre filter chips synced to URL on Explore page (`/explore?genres=Action,Sci-Fi`).

2. **Personalized Feed & Controls**:
   - `POST /api/personalized/home` supports optional `limit` parameter (1..50, default 30).
   - Recency ordering contract: `liked_movie_ids` sent oldest-to-newest so tail elements anchor the "Because you liked" rows.
   - De-jumped refresh: 1.5s debounce on likes/dislikes change while on Home; immediate refresh on Home mount.
   - Full order-invariance test in backend suite (61 passing tests).

3. **User Taste & Watch Status Tracking**:
   - Interactive Like / Dislike controls on Movie Cards, Hero Spotlight, and Movie Detail page.
   - Per-movie watch statuses (`plan`, `watching`, `watched`, `dropped`) with portaled dropdown control (`createPortal`) preventing UI clipping.
   - Safe localStorage migration from legacy watchlist to new status store.
   - Exclusions: watched and dropped movies excluded from hero spotlight and recommendations.
   - Avoided genres preference with dynamic profile filtering.
   - Full My Library page with dedicated tabs, counters, clear-tab modals, and genre breakdown.

---

## What Was NOT Changed

- `recommender/` model code, training, evaluation, or results
- `data/processed/` or any benchmark Parquets
- `test.parquet` or `cold_final` files
- Any committed data files (only `data/serving/` which is gitignored)
- No secrets printed, logged, or written to tracked files
- `backend/.env` not read or opened — loaded only via pydantic-settings at runtime

