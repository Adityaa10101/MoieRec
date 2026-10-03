# Content-Based Filtering Module

## Planned Components:
- **`feature_extractor.py`**: Extraction and vectorization of movie features (genres, directors, cast, plot keywords, TF-IDF / transformer embeddings).
- **`similarity.py`**: Computation and indexing of pairwise cosine similarities across movies.
- **`engine.py`**: Recommender engine returning top-N movies similar to user taste profiles or seed movies.
