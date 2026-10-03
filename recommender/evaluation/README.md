# Evaluation Module

## Planned Components:
- **`rating_metrics.py`**:
  - Root Mean Squared Error (RMSE)
  - Mean Absolute Error (MAE)
- **`ranking_metrics.py`**:
  - Precision@K
  - Recall@K
  - F1@K
  - Normalized Discounted Cumulative Gain (NDCG@K)
  - Hit Rate@K
  - Mean Reciprocal Rank (MRR)
- **`system_metrics.py`**:
  - Catalog Coverage
  - Intra-list Diversity (ILD)
  - Novelty / Serendipity
- **`benchmark.py`**: Automated offline test suite comparing baseline models against the hybrid pipeline.
