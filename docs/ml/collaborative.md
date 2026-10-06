# Item-Item Collaborative Filtering (Phase 2G-Lite)

> **Version**: 2G-Lite  
> **Status**: Active (served as a component in Hybrid v2)  
> **Module**: `recommender/collaborative/item_cf.py`

---

## 1. Motivation

Content-based filtering (Phase 2C–2E) encodes a movie via its genres, tags, and genome features. Two thematically unrelated movies that users co-rate highly will not be captured by content similarity alone. Item-item collaborative filtering (neighborhood CF) plugs this gap: it scores a candidate by aggregating ratings from users who also rated the candidate, weighted by the cosine similarity of the user's picks and the co-rated items.

Because MoieRec operates **without user accounts** (stateless, session-only profile), the CF component runs via **item-kNN scoring from the user's picks**: given a guest's explicit liked-movie picks, we look up pre-computed item–item similarities and aggregate a score on the fly at serving time.

---

## 2. Co-Occurrence & Similarity Construction

### 2.1 Data split
All CF computations use only the **train split** (`data/processed/train.parquet`). The held-out `cold_dev` and `cold_final` partitions are never read during model construction.

### 2.2 Co-occurrence matrix
For each pair of items $(i, j)$, the co-occurrence count is defined as the number of **train users** who rated both items:

$$\text{cooc}(i, j) = \left| \{ u \in \mathcal{U}_{\text{train}} : r_{ui} > 0 \text{ and } r_{uj} > 0 \} \right|$$

The matrix is stored in COO/CSR format as `cf_cooc_csr.npz`.

### 2.3 User-item matrix & TF-IDF normalisation
The user–item matrix uses **binary implicit feedback** (rated ≥ 1 ⇒ 1). Each column (item) is IDF-weighted to down-weight globally popular movies:

$$\text{IDF}(i) = \log\!\left(\frac{|\mathcal{U}_{\text{train}}|}{1 + \text{df}(i)}\right)$$

where $\text{df}(i)$ is the number of users who rated item $i$. The resulting matrix $\mathbf{M}$ has rows $\ell_2$-normalized.

### 2.4 Cosine item–item similarity
Item similarity is the cosine of the IDF-weighted binary columns:

$$\text{sim}(i, j) = \frac{\mathbf{m}_i \cdot \mathbf{m}_j}{\|\mathbf{m}_i\| \cdot \|\mathbf{m}_j\|}$$

A **minimum co-occurrence guard** (`cf_min_support = 5`, tunable in `hybrid_v2.yaml`) zeroes out any pair $(i, j)$ with $\text{cooc}(i,j) < 5$ to prevent noise from rarely co-rated pairs.

### 2.5 Compact top-K neighbour cache
For each item $i$, we store only the top-200 most similar items (by cosine) as dense arrays:
- `cf_topk_indices.npy` — shape `(n_items, 200)`, `int32`
- `cf_topk_sims.npy` — shape `(n_items, 200)`, `float32`
- `cf_topk_cooc.npy` — shape `(n_items, 200)`, `int32`

Combined size: ~42 MB. These are exported to `data/serving/model_v2/` by  
`recommender/serving/export_model_v2_artifacts.py`.

---

## 3. Serving Score (Item-kNN Scoring from the User's Picks)

Given a guest profile $\mathcal{P} = \{p_1, \ldots, p_K\}$ (liked movie IDs, K picks), the CF score for candidate $c$ is:

$$s_{\text{CF}}(c) = \frac{\sum_{p \in \mathcal{P}} \text{sim}(c, p) \cdot \mathbf{1}[\text{cooc}(c,p) \ge \tau]}{\max\!\left(1,\, \sum_{p \in \mathcal{P}} \mathbf{1}[\text{cooc}(c,p) \ge \tau]\right)}$$

where $\tau = \text{cf\_min\_support}$ (default 5). Items with no qualifying neighbours receive a score of 0.

The raw CF score is then **percentile-normalised** within the candidate pool before blending (see Hybrid v2).

---

## 4. Similarity Tuning

Tuning was run on `cold_dev` (warm validation: random 20k-user subsample) using `recommender/collaborative/tune_validation_cf.py`. The variants explored:

| Variant | Description |
|---------|-------------|
| `cosine_raw` | Raw cosine, no min-support guard |
| `cosine_min5` | Cosine with min co-occurrence ≥ 5 (selected) |
| `cosine_min10` | Cosine with min co-occurrence ≥ 10 |
| `cosine_idf` | IDF-weighted cosine |
| `jaccard` | Jaccard coefficient on binary ratings |
| `bm25_like` | BM25-inspired weighting |

**Selected**: `cosine_min5` — best mean NDCG@5 on warm validation (see `results/cf_validation.json`).

---

## 5. Cold-Start Evaluation

The CF component was evaluated using the **Cold-Start Protocol v2** (`recommender/evaluation/cold_start.py`):
- **Split**: `cold_dev` (2,559 held-out users with ≥ 5 train ratings)
- **K values**: 3, 5, 10, 20
- **Variants**: all-candidates and long-tail (top-200 popularity excluded from candidates and relevant items)
- **Bootstrap**: 1,000 resamples for final tables, 200 while tuning

Results are in `results/cf_validation.json` and embedded in `results/hybrid_v2_cold_dev.json` (column `cf_ndcg`).

---

## 6. Limitations & Future Work

- **No matrix factorisation**: Phase 2G-Lite deliberately excludes SVD/ALS/latent factor models.
- **No cold item support**: Items with zero train ratings have no neighbours and receive CF score = 0.
- **Static profile**: User preferences are captured from the single-session pick list only. Sequence/temporal dynamics are not modelled.
- **Scale**: The full MovieLens-25M item space is not pre-computed pairwise; only top-200 neighbours per item are stored.

---

## 7. Files

| File | Description |
|------|-------------|
| `recommender/collaborative/item_cf.py` | CF model class: build co-occurrence, similarity, score |
| `recommender/collaborative/tune_validation_cf.py` | Similarity variant tuning on warm validation |
| `recommender/collaborative/__init__.py` | Package init |
| `recommender/serving/export_model_v2_artifacts.py` | Export compact top-K arrays |
| `recommender/config/hybrid_v2.yaml` | `cf_min_support` and blend weights |
| `data/serving/model_v2/cf_topk_indices.npy` | Top-200 neighbour indices (serving artifact) |
| `data/serving/model_v2/cf_topk_sims.npy` | Top-200 neighbour cosine similarities |
| `data/serving/model_v2/cf_topk_cooc.npy` | Top-200 neighbour co-occurrence counts |
| `results/cf_validation.json` | Similarity variant tuning results |
