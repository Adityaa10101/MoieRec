# Cold-Start Strategy & Evaluation Protocol

## 1. The Core Cold-Start Reality

A real, newly registered MoieRec user is **never present in the historical MovieLens matrix**. 

Collaborative filtering matrix factorization models (such as SVD, ALS, or BPR) cannot produce user latent factors without pre-existing training rows. Furthermore, retraining full matrix factorization models on every new user interaction is computationally prohibitive.

MoieRec addresses cold-start through a systematic 4-phase user evolution lifecycle:

```
[New User Registration]
         │
         ▼
[Phase 1: Curatorial Onboarding] ──► Select 3–5 favorite films or aesthetic clusters
         │
         ▼
[Phase 2: Content-Based Profile] ──► Instant weighted vector from Tier 1/2 item features
         │
         ▼
[Phase 3: Real-Time Content Recs] ──► Cosine similarity over candidate catalog (0ms latency)
         │
         ▼
[Phase 4: Collaborative Scoring] ──► Item-kNN scoring from the user's picks over precomputed item similarities
         │
         ▼
[Steady State: Hybrid Model]     ──► Weighted blend: α*Content + β*Collaborative + γ*Popularity
```

---

## 2. The 4-Phase Cold-Start Lifecycle

### Phase 1: Curatorial Onboarding (Day 0, Minute 0)
- During registration, the user is presented with a diverse grid of high-affinity films spanning varied genres and eras (e.g. *Arrival*, *Blade Runner 2049*, *Inception*, *Parasite*, *Spirited Away*, *The Dark Knight*).
- The user selects 3 to 5 titles they admire.
- **Inference-Time Data Principle:** These selections are treated strictly as **inference-time personalization input**, never as offline model training rows.

### Phase 2: Instant Content-Based User Profile
- Let $\{m_1, m_2, \dots, m_K\}$ be the $K$ onboarding films with binary ratings $r_k = 1.0$.
- The user profile vector $\mathbf{u}_{\text{content}}$ is constructed instantly as a normalized centroid of the item feature representations $\mathbf{v}_k$:
  $$\mathbf{u}_{\text{content}} = \frac{\sum_{k=1}^K \mathbf{v}_k}{\left\|\sum_{k=1}^K \mathbf{v}_k\right\|_2}$$
- Where $\mathbf{v}_k$ denotes the Tier 1 baseline feature vector (multi-hot genres + normalized release decade).

### Phase 3: Immediate Content Retrieval
- Candidate items $j \in \mathcal{C}$ are scored in real time via cosine similarity:
  $$\text{Score}_{\text{content}}(u, j) = \cos(\mathbf{u}_{\text{content}}, \mathbf{v}_j) = \frac{\mathbf{u}_{\text{content}} \cdot \mathbf{v}_j}{\|\mathbf{u}_{\text{content}}\|_2 \|\mathbf{v}_j\|_2}$$
- Provides zero-latency, highly relevant recommendations without requiring any collaborative matrix operations.

### Phase 4: Collaborative Item-kNN Scoring (Scoring from User's Picks)
- When the user accumulates ratings, item-kNN collaborative filtering scores candidates from the user's picks:
  - The item factor matrix $\mathbf{V} \in \mathbb{R}^{M \times d}$ is held **fixed** (frozen from the offline model).
  - The user's latent factor $\mathbf{u}_{\text{collab}} \in \mathbb{R}^d$ is computed via ridge regression:
    $$\mathbf{u}_{\text{collab}} = \left(\mathbf{V}_u^T \mathbf{V}_u + \lambda \mathbf{I}\right)^{-1} \mathbf{V}_u^T \mathbf{r}_u$$
    where $\mathbf{V}_u$ consists of the item factors of movies rated by user $u$, $\mathbf{r}_u$ is their centered rating vector, and $\lambda$ is a regularization coefficient.
- This operation takes < 2 milliseconds and immediately activates collaborative signals.

---

## 3. Simulated Cold-Start Evaluation Protocol (Protocol v2)

To empirically evaluate how effectively MoieRec onboards new users, the data pipeline isolates a dedicated, held-out partition:

1. **Held-Out User Partition (`splits/cold_start_users.parquet`):**
   - 5% of eligible benchmark users (`cold_start_user_fraction = 0.05`, deterministic seed 42) are excluded from the main `train`, `validation`, and `test` splits (5,119 total users).
   - Partitioned deterministically 50/50 into:
     - `cold_dev` (**2,559 users**): used for hyperparameter tuning and model validation.
     - `cold_final` (**2,560 users**): strictly guarded behind `final=True` and reserved for the final frozen benchmark.
   - Zero ratings from these users appear during model training.

2. **Protocol v2 Simulation Procedure (K-Revealed with Fixed Evaluation Window):**
   - For each cold-start user in `cold_dev` with chronological ratings sorted by `(timestamp, hash_tie_break)`:
     - **Onboarding Set:** The first $K$ positive ratings ($r \ge 4.0$) in the candidate catalog form the revealed onboarding selections ($K \in \{3, 5, 10\}$).
     - **Relevant Set ($W = 20$):** The NEXT $W = 20$ positive ratings chronologically immediately following the $K$ onboarding picks that fall in the candidate catalog. Users must possess $\ge K + W$ positive ratings to be evaluated; users with fewer are excluded from ranking metric denominators.
     - **Candidate Catalog:** Benchmark candidate catalog minus the $K$ revealed items.

3. **Evaluation Variants:**
   - **Variant (i) — All Candidates:** Candidates = all catalog items minus the $K$ revealed items. Relevant set = next $W=20$ positive ratings.
   - **Variant (ii) — Long-Tail Discovery:** Candidates = catalog minus the $K$ revealed items AND minus the **200 most-rated training movies**. The relevant set also excludes any of these top-200 head movies (with remaining items evaluated, requiring $\ge 1$ positive). This isolates the recommender's ability to discover long-tail gems without riding universal blockbuster coattails.
   - **Variant (iii) — Old Reference ("All Remaining Positives"):** Evaluates all remaining unrevealed positive ratings (users need $\ge K + 5$ positives). Retained strictly as an informational baseline for backward comparison.

> [!IMPORTANT]
> **CRITICAL PROTOCOL COMPARABILITY NOTICE:**
> Cold-start evaluation tables are **NOT COMPARABLE** with the main validation tables.
> - Main validation measures top-10 accuracy against all held-out validation ratings (where users have dozens or hundreds of unseen ratings, and candidates include head items).
> - Cold-start Protocol v2 measures accuracy against a restricted future horizon ($W=20$ next chronological positives) using only $K \in \{3, 5, 10\}$ revealed onboarding movies with zero prior user collaborative matrix representation.

---

## 4. Empirical Cold-Start Findings on `cold_dev` (Phase 2E.1)

Evaluated across $K \in \{3, 5, 10\}$ on `cold_dev` (seed=42):

### 1. Long-Tail Discovery (Top-200 Blockbusters Excluded):
- In the long tail, **Content Tier 2 (Snapshot)** overtakes Popularity at $K=5$ and strongly dominates at $K=10$:
  - **$K = 5$:** Tier 2 NDCG@10 = **0.0478** vs. Popularity = **0.0411** (Paired diff: **+0.0067**, relative lift: **+16.27%**). HitRate@10 = **0.2641** vs. **0.2453**.
  - **$K = 10$:** Tier 2 NDCG@10 = **0.0616** vs. Popularity = **0.0397** (Paired diff: **+0.0219**, relative lift: **+55.16%**, $p < 0.05$). HitRate@10 = **0.3404** vs. **0.2500** (lift: **+36.16%**). MRR@10 = **0.1449** vs. **0.0901** (lift: **+60.82%**).

### 2. All Candidates (Unrestricted Catalog):
- For small $K=3$ and $K=5$, Popularity holds an edge because users frequently rate ubiquitous blockbusters next.
- However, by $K = 10$, Content Tier 2 surpasses Popularity in **Hit Rate** (**0.6802** vs. **0.6500**) and **MRR** (**0.3542** vs. **0.3276**), while reaching parity in NDCG@10 (**0.1575** vs. **0.1635**, diff: -0.0061).

---

## 6. Implementation Status (Phase 2F: Hybrid v1 Implemented)

In Phase 2F, **Hybrid v1** was tuned and deployed as the serving onboarding engine:
- Combines Tier 2 Content Profile ($\alpha = 0.1$) with Population Popularity ($1 - \alpha = 0.9$) using candidate-pool percentile ranks.
- Strictly outperforms both Popularity and Content-Only across all $K \in \{3, 5, 10\}$ on both `all_candidates` and `long_tail` variants with 95% paired bootstrap confidence intervals strictly excluding zero.
- Phase 4 was implemented in Phase 2G-Lite via item-kNN scoring from the user's picks over precomputed item–item similarities.

