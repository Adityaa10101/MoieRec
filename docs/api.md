# MoieRec Serving API Specification (Phase 2G-Lite)

> **Version**: 2G-Lite  
> **Status**: Active (Model 0: Popularity Baseline + Hybrid v2 Personalization)  
> **Base URL**: `http://127.0.0.1:8000`

---

## 1. Overview & Honesty Contract

The MoieRec serving API provides real catalog data sourced from MovieLens 25M benchmark splits combined with TMDB metadata (synopses, posters, backdrops, cast, director) and real-time offline-tuned hybrid personalization.

### Honesty Contract & Anti-Deception Rules
1. **Stateless Personalization**: Recommendations in `POST /api/personalized/home` are computed from explicit guest picks (`liked_movie_ids`) using the offline-tuned `hybrid_v2` model (item-item CF + Tier 2 content similarity + popularity percentiles, K-adaptive simplex weights).
2. **Transparent Rank Semantics**:
   - `match_percent`: Defined strictly as the item's relative percentile rank within the candidate pool ($0-100$). Never displayed or claimed as a "match probability".
   - `score`: The real combined hybrid score $\alpha \cdot \text{pct}_{\text{content}} + (1 - \alpha) \cdot \text{pct}_{\text{popularity}}$.
   - `reason_codes`: Emitted only when backed by concrete mathematical evidence:
     - `SIMILAR_TO_PICK`: Only if nearest pick cosine $\ge 0.1278$ (95th percentile data-derived threshold).
     - `SHARED_GENRES`: Only if at least one shared genre has positive contribution.
     - `SHARED_TAGS`: Only if at least one shared tag or genome feature has positive contribution.
     - `POPULAR_WITH_VIEWERS`: Only if popularity component $\ge$ content component.
   - `explanation`: Full breakdown of nearest pick, top 3 positive feature contributions, and component weights.
3. **TMDB Integrity**:
   - Adult content (`adult == true`) is filtered from all responses.
   - Movies without verified `tmdb_id` links are excluded from user-facing discovery.
   - Rows contain only movies with verified TMDB posters (backfilled from candidate ranking).

---

## 2. Data Models

### `ExplanationOut` Schema

| Field | Type | Description |
| :--- | :--- | :--- |
| `nearest_pick` | `NearestPickExplanation` | User pick with highest cosine similarity (`movie_id`, `title`, `similarity`) |
| `top_shared_features`| `list[SharedFeatureExplanation]` | Top 3 positively contributing features (`feature`, `raw_name`, `contribution`, `feature_type`) |
| `components` | `ComponentsExplanation` | Decomposed hybrid components (`cf`, `content`, `popularity`) — v2 adds `cf` |
| `cf_pick` | `CfPickExplanation` or `null` | CF evidence: the user pick that contributes most CF signal (`movie_id`, `title`, `sim`, `cooc`) |
| `match_percent` | `integer` | Relative percentile rank within candidate pool ($0-100$) |
| `similarity_threshold` | `float` or `null` | Data-derived threshold for `SIMILAR_TO_PICK` (0.1278) |
| `alpha` | `float` or `null` | Dynamic alpha (v1.1) or `null` for v2 |
| `weights` | `object` or `null` | v2 simplex weights: `{"w_c": float, "w_f": float, "w_p": float}` |
| `reason_labels` | `dict[string, string]` or `null` | Human-readable honest labels for each active reason code |

### `CfPickExplanation` Schema (v2 only)

| Field | Type | Description |
| :--- | :--- | :--- |
| `movie_id` | `integer` | MovieLens ID of the contributing user pick |
| `title` | `string` | Display title |
| `sim` | `float` | Item-item cosine similarity between candidate and this pick |
| `cooc` | `integer` | Co-occurrence count (users who rated both in train set) |

### `MovieOut` Schema

| Field | Type | Description |
| :--- | :--- | :--- |
| `movie_id` | `integer` | MovieLens integer identifier |
| `tmdb_id` | `integer` or `null` | Verified TheMovieDB identifier |
| `title` | `string` | Display title |
| `year` | `integer` or `null` | Release year |
| `genres` | `list[string]` | Genre classifications |
| `overview` | `string` or `null` | Plot synopsis from TMDB |
| `poster_url` | `string` or `null` | Full URL to poster image |
| `backdrop_url` | `string` or `null` | Full URL to backdrop image |
| `runtime` | `integer` or `null` | Runtime in minutes |
| `vote_average` | `float` or `null` | TMDB community rating |
| `cast` | `list[CastMember]` | Top-billed cast |
| `directors` | `list[string]` | Directorial credits |
| `train_positive_count`| `integer` or `null` | Training set positive interactions |
| `rank` | `integer` or `null` | Ranking position within row |
| `score` | `float` or `null` | Hybrid score or cosine similarity |
| `match_percent` | `integer` or `null` | Relative percentile rank ($0-100$) |
| `reason_codes` | `list[string]` | Verified reason codes |
| `explanation` | `ExplanationOut` or `null` | Structured explainability telemetry |
| `source` | `string` | `"hybrid_v2"`, `"hybrid_v1.1"`, `"content_similarity"`, or `"popularity"` |

---

## 3. Endpoints

### 3.1 `POST /api/personalized/home`
Stateless personalized recommendations based on user picks.
- **Request Body**:
  ```json
  {
    "liked_movie_ids": [1, 260, 1196],
    "exclude_movie_ids": [318]
  }
  ```
- **Requirements**:
  - Requires $\ge 3$ valid MovieLens IDs in the serving catalog.
  - If $< 3$ valid IDs: returns `personalized: false` with explanatory message and `rows: []`.
  - Unknown IDs ignored and returned in `ignored_ids`.
- **Response Shape**:
  ```json
  {
    "personalized": true,
    "k": 5,
    "config_version": "2",
    "weights_used": {"w_c": 0.0, "w_f": 1.0, "w_p": 0.0},
    "ignored_ids": [],
    "rows": [ ... ]
  }
  ```
- **Rows Returned**:
  - Row 1: "Picked for You" (Hybrid v2, 20 items with TMDB posters; badge: `"PERSONALIZED · HYBRID v2"`, `source: "hybrid_v2"`)
  - Rows 2–3: "Because you liked <Title>" (Content similarity for the 2 most recent picks; badge: `"SIMILAR BY GENRES & TAGS"`, `source: "content_similarity"`)
- **Reason Code Contract (Label Honesty)**:
  - `SIMILAR_TO_PICK`: `"Similar to <pick title>"`
  - `SHARED_TAGS`: `"Shared tags: <tags>"`
  - `SHARED_GENRES`: `"Shared genres: <genres>"`
  - `POPULAR_WITH_VIEWERS`: `"Popular with MovieLens viewers"`
  - Forbidden terms: "Acclaimed", "Strong Match", "% match".
  - Card chip: `"Top N% pick"` where $N = \max(1, 100 - \text{match\_percent})$.

### 3.2 `GET /api/movies/{movie_id}/similar?limit=20`
Content-only nearest neighbors for a single movie using Tier 2 cosine similarity.
- **Source**: `"content_similarity"`
- **Response**: `List[MovieOut]`

### 3.3 `GET /api/home`
Non-personalized popularity baseline rows and hero spotlight.

### 3.4 `GET /api/movies/popular`
Paginated popular catalog listing with optional `genre` and `decade` filters.

### 3.5 `GET /api/movies/{movie_id}`
Detailed record for an individual movie by its MovieLens `movie_id`.

### 3.6 `GET /api/search?q=&limit=`
Prefix and substring title search ranked by training popularity count.

### 3.7 `GET /api/health`
System status and catalog health indicator.
