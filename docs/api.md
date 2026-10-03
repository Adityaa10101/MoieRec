# MoieRec Serving API Specification (Phase 2E.2)

> **Version**: 2E.2  
> **Status**: Active (Model 0: Non-Personalized Popularity Baseline)  
> **Base URL**: `http://127.0.0.1:8000`

---

## 1. Overview & Honesty Contract

The MoieRec serving API provides real catalog data sourced from MovieLens 25M benchmark splits combined with TMDB metadata (synopses, posters, backdrops, cast, director).

### Honesty Contract & Anti-Deception Rules
1. **Zero Personalization Claims**: In Phase 2E.2, recommendations are strictly non-personalized popularity rankings (Model 0). No collaborative filtering, embeddings, or neural ranking is claimed or simulated.
2. **Explicit Nulls for Uncomputed Signals**:
   - `match_percent`: `null` (never fabricated percentages like "97% Match")
   - `score`: `null`
   - `reason_codes`: `[]` (empty list)
   - `explanation`: `null` (never fabricated text like "Because you love world-building")
   - `source`: `"popularity"`
3. **TMDB Integrity**:
   - Adult content (`adult == true`) is filtered from all responses.
   - Movies without verified `tmdb_id` links are excluded from user-facing discovery.
   - If TMDB is unreachable, responses degrade gracefully by returning catalog fields (title, year, genres) with null image URLs; the API never fails or returns 500 on external dependency failure.

---

## 2. Data Models

### `MovieOut` Schema

| Field | Type | Description |
| :--- | :--- | :--- |
| `movie_id` | `integer` | MovieLens integer identifier |
| `tmdb_id` | `integer` or `null` | Verified TheMovieDB identifier |
| `title` | `string` | Human-friendly display title (normalized: trailing articles moved to front, years and `(a.k.a. ...)` stripped) |
| `year` | `integer` or `null` | Release year |
| `genres` | `list[string]` | Genre classifications |
| `overview` | `string` or `null` | Plot synopsis from TMDB |
| `poster_url` | `string` or `null` | Full URL to poster image (`w342` for cards, `w500` for details) |
| `backdrop_url` | `string` or `null` | Full URL to backdrop image (`w780` for cards, `w1280` for hero) |
| `runtime` | `integer` or `null` | Runtime in minutes |
| `vote_average` | `float` or `null` | TMDB community rating (0.0 to 10.0 scale) |
| `cast` | `list[CastMember]` | Top-billed cast (up to 8 members: `name`, `character`, `profile_path`) |
| `director` | `list[string]` | Directorial credits |
| `rank` | `integer` or `null` | Ranking position within row / result list |
| `score` | `null` | Uncomputed in Phase 2E.2 |
| `match_percent` | `null` | Uncomputed in Phase 2E.2 |
| `reason_codes` | `list[string]` | Empty in Phase 2E.2 (`[]`) |
| `explanation` | `null` | Uncomputed in Phase 2E.2 |
| `source` | `string` | `"popularity"` |

---

## 3. Endpoints

### 3.1 `GET /api/home`
Returns curated rows and hero spotlight for the home feed.

- **Response**:
  ```json
  {
    "hero": { ...MovieOut... },
    "rows": [
      {
        "id": "popular",
        "title": "Popular with MovieLens Viewers",
        "subtitle": "Most watched films across training data",
        "movies": [ ...MovieOut... ]
      },
      {
        "id": "sci-fi",
        "title": "Top in Sci-Fi",
        "subtitle": "Highest positive rating counts in Science Fiction",
        "movies": [ ...MovieOut... ]
      },
      {
        "id": "drama",
        "title": "Top in Drama",
        "subtitle": "Highest positive rating counts in Drama",
        "movies": [ ...MovieOut... ]
      },
      {
        "id": "2010s",
        "title": "Top of the 2010s",
        "subtitle": "Most appreciated releases from 2010 to 2019",
        "movies": [ ...MovieOut... ]
      },
      {
        "id": "1990s",
        "title": "Top of the 1990s",
        "subtitle": "Most appreciated releases from 1990 to 1999",
        "movies": [ ...MovieOut... ]
      }
    ]
  }
  ```

### 3.2 `GET /api/movies/popular`
Paginated popular catalog listing with optional genre and decade filters.

- **Parameters**:
  - `genre` (optional string): e.g. `Action`, `Sci-Fi`
  - `decade` (optional integer): e.g. `1990` (filters 1990–1999), `2010` (filters 2010–2019)
  - `limit` (optional integer, default `20`, max `100`)
  - `offset` (optional integer, default `0`)
- **Response**: `List[MovieOut]`

### 3.3 `GET /api/movies/{movie_id}`
Detailed record for an individual movie by its MovieLens `movie_id`.

- **Parameters**:
  - `movie_id` (path integer)
- **Response**: `MovieOut` (with high-resolution `w500` poster and `w1280` backdrop)
- **Status Codes**:
  - `200 OK`: Found and returned
  - `404 Not Found`: Movie does not exist in benchmark or lacks a verified TMDB ID

### 3.4 `GET /api/search`
Prefix and substring title search ranked by training popularity count.

- **Parameters**:
  - `q` (required string, min length 2): Query term (case-insensitive, diacritic-insensitive)
  - `limit` (optional integer, default `10`, max `50`)
- **Response**: `List[MovieOut]`

### 3.5 `GET /api/health`
System status and catalog health indicator.

- **Response**:
  ```json
  {
    "status": "healthy",
    "catalog_loaded": true,
    "catalog_count": 18277,
    "cache_entries": 3000
  }
  ```
