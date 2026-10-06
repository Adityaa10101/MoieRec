# Recommender System Design & Model Hierarchy

## 1. Model Hierarchy Architecture

MoieRec structures its recommendation capabilities into a strict 4-level model progression. Each successive model introduces specific inductive biases and must be empirically validated against preceding baselines before deployment.

```
Model 0: Non-Personalized Popularity Baseline
   │
   ▼
Model 1: Content-Based Filtering (Tier 1 & Tier 2)
   │
   ▼
Model 2: Latent Factor Collaborative Filtering (SVD / ALS)
   │
   ▼
Model 3: Curatorial Hybrid Scoring & Re-Ranking
```

### Absolute Scientific Rule: No Superiority Claims Until Measured
No model tier is assumed superior a priori. Complex neural or collaborative models frequently underperform well-tuned popularity or content baselines on sparse datasets. All claims of model efficacy must be supported by empirical NDCG@10 and Recall@10 measurements on the frozen test split.

---

## 2. Model Tier Specifications

### Model 0: Global & Segmented Popularity Baseline
- **Purpose:** Non-personalized zero-information baseline for unauthenticated users or fallback retrieval.
- **Serving Note (Phase 2E.2):** All rows returned by the `/api/home` serving endpoint ("Popular with MovieLens viewers", "Top in Sci-Fi", "Top in Drama", "Top of the 2010s", "Top of the 1990s") are strictly Model 0 popularity baselines (ordered by `train_positive_count` descending with seeded hash tie-break). They are non-personalized, and the API / UI explicitly reflects this with no fabricated personal affinity or match scores.
- **Formulation:**
  $$\text{Score}_{\text{pop}}(i) = \log(1 + C_{\text{train}}(i)) \cdot \bar{r}_{\text{train}}(i)$$
  where $C_{\text{train}}(i)$ is the rating count of movie $i$ in `splits/train_movie_stats.parquet`, and $\bar{r}_{\text{train}}(i)$ is its mean rating.
- **Leakage Prevention:** Popularity metrics must **never** be computed on validation or test splits.

### Model 1: Content-Based Profile Matching
- **Purpose:** Immediate zero-interaction onboarding, new movie cold-start, and explainable item-item retrieval.
- **Representations:**
  - **Tier 1 (Main Evaluation Baseline):** Multi-hot genres + normalized release year/decade.
  - **Tier 2 (Snapshot Experiment):** Tag TF-IDF + Tag Genome matrix with explicit coverage mask.
- **Formulation:** User profile centroid $\mathbf{u}_{\text{content}}$ scored against candidate vectors $\mathbf{v}_i$ via cosine similarity.

### Model 2: Collaborative Matrix Factorization
- **Purpose:** Capturing latent behavioral affinities, cross-genre patterns, and serendipitous discovery.
- **Formulations:** Regularized Alternating Least Squares (Implicit ALS) or Truncated SVD / Biased Matrix Factorization.
- **Inference:** User vector $\mathbf{p}_u \in \mathbb{R}^d$ and item factor $\mathbf{q}_i \in \mathbb{R}^d$ combined as $\hat{r}_{u,i} = \mu + b_u + b_i + \mathbf{p}_u \cdot \mathbf{q}_i$.

### Model 3: Curatorial Hybrid Scoring (Phase 2F: Hybrid v1 Implemented)
- **Purpose:** Production cold-start and onboarding recommendation blending content taste profiles and population popularity.
- **Implemented Model (`hybrid_v1`):**
  - Linear blend over candidate-pool percentile ranks:
    $$\text{FinalScore}(u, i) = \alpha \cdot \text{pct}_{\text{content}}(u, i) + (1 - \alpha) \cdot \text{pct}_{\text{pop}}(i)$$
  - Tuned offline on `cold_dev`: $\alpha = 0.1$, Tier 2 weights $w_{T1}=1.0, w_{\text{tags}}=4.0, w_{\text{genome}}=1.0$.
  - Generates "Picked for You" row and "Because you liked <Title>" content rows in serving API.
- **Future Collaborative Extensions:**
  - Item-kNN scoring vectors from the user's picks and diversity re-ranking will be introduced in subsequent phases.

---

## 3. Curatorial Feature Formulations (Design Placeholders)

The following curatorial concepts define future product features and will be implemented in subsequent phases:

### A. Hidden Gems Feed
- **Intuition:** High predicted relevance to user taste, but situated in the long tail of low global popularity.
- **Mathematical Placeholder Definition:**
  $$\text{GemScore}(u, i) = \tilde{S}_{\text{hybrid}}(u, i) \cdot \left(1.0 - \tilde{P}_{\text{popularity}}(i)\right)^\eta$$
  where $\tilde{P}_{\text{popularity}}(i) \in [0.0, 1.0]$ is the empirical cumulative distribution function (CDF) of movie rating counts in `train`, and $\eta \ge 1.0$ controls the penalty for blockbuster titles.

### B. Outside Your Usual Taste (Controlled Serendipity)
- **Intuition:** Movies possessing high critical quality and reasonable latent appeal, but located at a controlled semantic distance from the user's centroid profile.
- **Mathematical Placeholder Definition:**
  $$\text{SerendipityScore}(u, i) = \tilde{S}_{\text{quality}}(i) \cdot \mathbb{I}\left(\tau_{\min} \le \text{Distance}(\mathbf{u}_{\text{content}}, \mathbf{v}_i) \le \tau_{\max}\right)$$
  ensures the item is neither identical to existing watched films nor incomprehensibly distant.

### C. Maximal Marginal Relevance (MMR) & Intra-List Diversity
- **Intuition:** Eliminate repetitive recommendations (e.g. 5 Marvel films in a row) by balancing relevance with pairwise novelty.
- **Formulation:**
  $$\text{NextItem}(S) = \arg\max_{i \in \mathcal{C} \setminus S} \left[\lambda \cdot \text{Score}(u, i) - (1 - \lambda) \max_{j \in S} \text{Similarity}(i, j)\right]$$
  where $S$ is the set of items already selected in the Top-$N$ list.
