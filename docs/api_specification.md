# MoieRec API Specification

## Base URL
- Development: `http://localhost:8000/api`

---

## Implemented Endpoints (Phase 1)

### `GET /api/health`
Checks the operational readiness of the API server.

**Response**: `200 OK`
```json
{
  "status": "ok",
  "service": "MoieRec API"
}
```

---

## Planned Endpoints (Future Phases)

- `GET /api/movies/recommendations`: Retrieve hybrid recommendations for authenticated user.
- `GET /api/movies/:id`: Fetch movie detail and metadata enriched with TMDB.
- `POST /api/ratings`: Record user rating interaction.
- `GET /api/taste-profile`: Retrieve user taste DNA and feature preferences.
- `GET /api/explain/:movieId`: Fetch explainable rationale for a specific movie recommendation.
