# MoieRec Documentation Index

This directory contains technical specifications, architectural decisions, and machine learning research reports for the MoieRec recommendation system.

---

## Machine Learning & Recommender Documentation (`docs/ml/`)

| Document | Description |
| :--- | :--- |
| [`baseline_popularity.md`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/ml/baseline_popularity.md) | Non-personalized popularity baselines (`most_rated`, `most_liked`, Bayesian `damped_mean`) establishing the empirical benchmark floor. |
| [`cold_start.md`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/ml/cold_start.md) | Simulated onboarding protocol evaluating user preference elicitation across $K \in \{3, 5, 10, 20\}$ seed picks. |
| [`collaborative.md`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/ml/collaborative.md) | Item-item collaborative filtering using asymmetric cosine similarity, top-200 neighbor truncation, and pick-based scoring. |
| [`content_based.md`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/ml/content_based.md) | Feature engineering (Tier 1 clean genres/year vs. Tier 2 snapshot tags/genome) and neutral tie-break diagnostics. |
| [`dataset.md`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/ml/dataset.md) | MovieLens 25M dataset selection, schema mappings (`links.csv` to TMDB), and iterative k-core benchmark extraction. |
| [`evaluation_protocol.md`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/ml/evaluation_protocol.md) | Offline evaluation protocol, per-user chronological 80/10/10 temporal split, candidate masking, and paired bootstrap CIs. |
| [`explainability.md`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/ml/explainability.md) | Transparent recommendation explainability, "Top N% pick" rank semantics, and mathematical criteria for `CF_EVIDENCE`. |
| [`final_results.md`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/ml/final_results.md) | Immutable Phase 2H frozen one-shot evaluation report across held-out `cold_final` and warm `TEST` splits. |
| [`hybrid_v1.md`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/ml/hybrid_v1.md) | Two-component linear percentile fusion ($\alpha \cdot \text{content} + (1-\alpha) \cdot \text{popularity}$) tuned on `cold_dev`. |
| [`hybrid_v2.md`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/ml/hybrid_v2.md) | Three-component simplex blend incorporating item-item CF, content features, and popularity across onboarding buckets. |
| [`recommender_design.md`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/ml/recommender_design.md) | Four-tier model hierarchy architecture, empirical validation rules, and curatorial roadmap formulations. |

---

## Architectural & System Guides

| Document | Description |
| :--- | :--- |
| [`architecture.md`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/architecture.md) | End-to-end system design spanning React frontend, FastAPI backend, SQLite catalog, and serving pipelines. |
| [`api.md`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/api.md) | REST API endpoints, request/response contracts, and schema definitions. |
| [`api_specification.md`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/api_specification.md) | Concise endpoint specifications for health checks, catalog search, and recommendation delivery. |
| [`setup_guide.md`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/setup_guide.md) | Developer runtime setup, virtual environments, Node dependencies, and local verification steps. |
