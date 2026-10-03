# MoieRec Recommender Engine

This package implements the machine learning recommendation core for MoieRec. It is designed to combine collaborative filtering, content-based semantics, and an explainable hybrid ranking layer.

## Architecture & Submodules

### 1. `preprocessing/`
Handles raw data ingestion (MovieLens & TMDB dumps), dataset cleaning, missing value resolution, user/item mapping tokenization, and train/validation/test split generation.
- Data ingestion pipelines
- Metadata cleaning and normalization
- Interaction matrix builders
- Splitting utilities (temporal and stratified)

### 2. `content_based/`
Builds semantic representations of movie metadata and calculates similarity metrics.
- Feature extraction (TF-IDF, BERT/Sentence-Transformers for synopses, genre/cast embeddings)
- Vector index / Cosine similarity calculations
- Content-based candidate generation

### 3. `collaborative/`
Implements interaction-driven recommendation algorithms.
- User-item interaction sparse matrix representations
- Matrix Factorization algorithms (SVD, ALS)
- Implicit feedback modeling
- Latent factor candidate generation

### 4. `hybrid/`
Merges recommendations from both collaborative and content-based engines.
- Ensemble score weighted combination
- Re-ranking pipeline (incorporating user taste profiles & discovery controls)
- Serendipity & diversity filtering
- Explanation generation (extracting feature contributions and rationales for recommendations)

### 5. `evaluation/`
Comprehensive offline evaluation metrics framework.
- Rating prediction accuracy: RMSE, MAE
- Top-K ranking metrics: Precision@K, Recall@K, F1@K, NDCG@K, Hit Rate
- Beyond-accuracy metrics: Catalog coverage, intra-list diversity, novelty

### 6. `models/`
Storage directory for trained model artifacts, serialized weights (e.g. SVD matrices, embeddings), and model metadata. Model binary files are excluded from Git tracking.
