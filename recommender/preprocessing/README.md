# Preprocessing Module

## Planned Components:
- **`data_loader.py`**: Ingestion of MovieLens 100k/1M datasets and TMDB enrichment data.
- **`cleaner.py`**: Missing value handling, duplicate resolution, and timestamp parsing.
- **`matrix_builder.py`**: Mapping user/movie IDs to contiguous indices and building scipy sparse matrices.
- **`splitter.py`**: Stratified and temporal splitting for offline evaluation.
