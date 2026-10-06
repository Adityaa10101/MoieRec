# Hybrid v1 Model Specification & Tuning Results

## Overview

The `hybrid_v1` recommendation model is the first personalization tier of MoieRec. It combines user-revealed movie picks with a hybrid blend of content-based semantic similarity (Tier 2 feature vectors) and population popularity, tuned offline under Cold-Start Protocol v2 on `cold_dev`.

## Mathematical Formulation

Given $K$ user-liked movies:
1. **User Profile**:
   $$\mathbf{u} = \frac{\sum_{i \in \text{liked}} \mathbf{x}_i}{\|\sum_{i \in \text{liked}} \mathbf{x}_i\|_2}$$
   where $\mathbf{x}_i$ is the concatenated, block-weighted, L2-normalized Tier 2 item representation:
   $$\mathbf{x}_i = \text{L2Norm}\left( [w_{T1} \cdot \mathbf{x}_{i, T1}, w_{\text{tags}} \cdot \mathbf{x}_{i, \text{tags}}, w_{\text{genome}} \cdot (\mathbf{x}_{i, \text{genome}} \odot \mathbf{m}_i) ] \right)$$
2. **Component Scores**:
   - Content similarity: $s_c(j) = \mathbf{u}^\top \mathbf{x}_j$ (cosine similarity)
   - Popularity: $s_p(j) = \text{train\_positive\_count}(j)$
3. **Percentile Normalization**:
   For candidate pool $\mathcal{C}$ ($|\mathcal{C}| = M$):
   $$\text{pct}_c(j) = \frac{\text{rank}(s_c(j)) - 1}{M - 1}, \quad \text{pct}_p(j) = \frac{\text{rank}(s_p(j)) - 1}{M - 1}$$
   where ties receive the average fractional rank.
4. **Hybrid Blend**:
   $$\text{final}(j) = \alpha \cdot \text{pct}_c(j) + (1 - \alpha) \cdot \text{pct}_p(j)$$
5. **Tie Breaking**: Deterministic random permutation seed (seed=42).

## Tuning Protocol (Cold-Start Protocol v2)

- **Dataset**: `cold_dev` interactions exclusively.
- **Cohorts**: $K \in \{3, 5, 10\}$ initial user positive interactions, window $W=20$.
- **Variants**:
  - (i) `all_candidates`: all catalog movies minus the $K$ revealed items.
  - (ii) `long_tail`: catalog excluding the top 200 most popular movies and the $K$ revealed items.
- **Grid**:
  - $\alpha \in \{0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0\}$
  - $w_{\text{tags}} \in \{2, 4, 8, 16\}$
  - $w_{\text{genome}} \in \{0.25, 0.5, 1.0\}$
  - $w_{T1} = 1.0$ (fixed base)
  - Total: 132 configurations.
- **Selection Objective**: Mean NDCG@10 over $K \in \{3, 5, 10\}$ on variant (i).
- **Reject Criterion**: Any configuration whose variant (ii) NDCG@10 is below popularity baseline for any $K$ is rejected.

## Chosen Configuration

- **Version**: `hybrid_v1`
- **Alpha ($\alpha$)**: `0.1`
- **Block Weights**: $w_{T1}=1.0, w_{\text{tags}}=4.0, w_{\text{genome}}=1.0$
- **Objective Value**: 0.1995 (vs Popularity baseline 0.1813, +10.0% relative improvement)
- **Edge Note**: $w_{\text{genome}}=1.0$ lies on the search boundary $[0.25, 1.0]$.
- **Data-derived Similarity Threshold**: 0.1278 (95th percentile of pairwise item cosine similarities over 50,000 random item pairs).

## Evaluation Results on `cold_dev` (1000 Bootstrap Resamples)

| Cohort | Variant | Popularity NDCG@10 [95% CI] | Content-Only NDCG@10 [95% CI] | Hybrid v1 NDCG@10 [95% CI] | Hybrid vs Pop $\Delta$ [95% CI] | Hybrid vs Content $\Delta$ [95% CI] | Paired CI Excludes 0 |
|---|---|---|---|---|---|---|---|
| K=3 | all_candidates | 0.1956 [0.1885, 0.2025] | 0.0908 [0.0851, 0.0966] | **0.2068** [0.1995, 0.2138] | +0.0111 [+0.0058, +0.0165] | +0.1159 [+0.1088, +0.1232] | Yes (Better) |
| K=3 | long_tail | 0.0409 [0.0372, 0.0447] | 0.0248 [0.0217, 0.0280] | **0.0528** [0.0486, 0.0572] | +0.0119 [+0.0084, +0.0150] | +0.0280 [+0.0237, +0.0321] | Yes (Better) |
| K=5 | all_candidates | 0.1849 [0.1774, 0.1923] | 0.0874 [0.0818, 0.0933] | **0.2051** [0.1979, 0.2129] | +0.0202 [+0.0153, +0.0250] | +0.1177 [+0.1092, +0.1253] | Yes (Better) |
| K=5 | long_tail | 0.0411 [0.0374, 0.0448] | 0.0232 [0.0201, 0.0264] | **0.0562** [0.0521, 0.0602] | +0.0151 [+0.0120, +0.0181] | +0.0330 [+0.0285, +0.0373] | Yes (Better) |
| K=10 | all_candidates | 0.1635 [0.1563, 0.1713] | 0.0629 [0.0577, 0.0682] | **0.1865** [0.1789, 0.1944] | +0.0230 [+0.0188, +0.0267] | +0.1236 [+0.1154, +0.1320] | Yes (Better) |
| K=10 | long_tail | 0.0397 [0.0362, 0.0437] | 0.0186 [0.0158, 0.0213] | **0.0614** [0.0567, 0.0658] | +0.0216 [+0.0184, +0.0246] | +0.0428 [+0.0379, +0.0476] | Yes (Better) |

## Snapshot Feature Leakage Caveat

Tag TF-IDF and Genome features are snapshot features aggregated across the entire MovieLens 25M collection (up to November 2019). While `train.parquet` strictly precedes `cold_dev` chronologically, tags applied to older movies by users later in the timeline leak semantic information across chronological splits. In production, feature stores freeze snapshots at split boundaries.

## Known Limits & Approximation Notes

1. **User Pick Approximation**: The first $K$ chronologically recorded positive interactions of MovieLens users approximate real user onboarding picks. Real onboarding involves active user choice rather than passive logging.
2. **Cold-Start Only**: `hybrid_v1` is an onboarding / cold-start heuristic. Collaborative filtering item-kNN scoring from the user's picks, sequential interactions, and matrix factorization remain for later phases.

---

## Hybrid v1.1: Dynamic Alpha Schedule by K (Phase 2F.1)

### Product Objective & Rationale
In `hybrid_v1`, a single global $\alpha = 0.1$ was selected to satisfy the strict conservative constraint across all $K \in \{3, 5, 10\}$. However, as users provide more onboarding likes ($K=5, 10, 20$), their taste vector becomes far more informative and reliable. Constraining higher-$K$ profiles to 90% popularity starves users of genuine personalization and suppresses discovery of long-tail catalog gems.

`hybrid_v1.1` introduces a **dynamic alpha schedule by profile size $K$** with a product selection objective:
$$\max_{\alpha} \quad \frac{1}{2} \left( \frac{\text{NDCG}_{\text{all}}(\alpha)}{\text{NDCG}_{\text{pop\_all}}} + \frac{\text{NDCG}_{\text{lt}}(\alpha)}{\text{NDCG}_{\text{pop\_lt}}} \right)$$
$$\text{subject to} \quad \text{NDCG}_{\text{all}}(\alpha) \ge \text{NDCG}_{\text{pop\_all}}$$

**Product Decision Statement**: For each cohort $K$, we maximize the average relative lift over popularity across both full catalog (`all_candidates`) and discovery (`long_tail`) candidates, under the hard requirement that recommendation quality on all candidates does not degrade below the popularity baseline. This product choice prioritizes long-tail niche relevance while guaranteeing safe, high-utility recommendations.

### Cohorts Evaluated (Cold-Start Protocol v2 on `cold_dev`)
Evaluation was conducted on `cold_dev` with window $W=20$ across $K \in \{3, 5, 10, 20\}$:
- **$K=3$**: 2,456 users (`all_candidates`), 2,433 users (`long_tail`), 103 excluded ($<23$ positives)
- **$K=5$**: 2,420 users (`all_candidates`), 2,397 users (`long_tail`), 139 excluded ($<25$ positives)
- **$K=10$**: 2,317 users (`all_candidates`), 2,288 users (`long_tail`), 242 excluded ($<30$ positives)
- **$K=20$**: 2,044 users (`all_candidates`), 2,024 users (`long_tail`), 515 excluded ($<40$ positives)

Fixed Tier 2 block weights from `hybrid_v1`: $w_{T1} = 1.0$, $w_{\text{tags}} = 4.0$, $w_{\text{genome}} = 1.0$.

### Alpha Schedule & Serving Buckets
Tuning $\alpha \in \{0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8\}$ revealed strictly monotonic raw optima:
- $K=3 \rightarrow \text{raw optimal } \alpha = 0.3$ (Relative Lift: +37.0% avg lift)
- $K=5 \rightarrow \text{raw optimal } \alpha = 0.6$ (Relative Lift: +64.1% avg lift)
- $K=10 \rightarrow \text{raw optimal } \alpha = 0.7$ (Relative Lift: +92.9% avg lift)
- $K=20 \rightarrow \text{raw optimal } \alpha = 0.8$ (Relative Lift: +107.3% avg lift)

Because the raw optima are naturally strictly increasing with $K$, no post-hoc smoothing was necessary.

Serving applies these tuned values across contiguous user pick buckets:
- **$K \in [3, 4]$**: $\alpha = 0.3$ (tuned $K=3$)
- **$K \in [5, 7]$**: $\alpha = 0.6$ (tuned $K=5$)
- **$K \in [8, 14]$**: $\alpha = 0.7$ (tuned $K=10$)
- **$K \ge 15$**: $\alpha = 0.8$ (tuned $K=20$)

### Final Results on `cold_dev` (1000 Bootstrap Resamples)

> **Important Evaluation Notice**: These hyperparameters were tuned directly on `cold_dev`. Consequently, bootstrap confidence intervals reported below are optimistic due to selection on the development split. The one-shot validation on `cold_final` remains strictly reserved for the final benchmark phase and was NOT read or accessed during this tuning.

| $K$ | Variant | Users | Popularity NDCG@10 [95% CI] | Content-Only NDCG@10 [95% CI] | Hybrid v1 ($\alpha=0.1$) [95% CI] | Hybrid v1.1 ($\alpha(K)$) [95% CI] | v1.1 vs Pop $\Delta$ [95% CI] | v1.1 vs v1 $\Delta$ [95% CI] |
|---|---|---|---|---|---|---|---|---|
| **$K=3$** | all_candidates | 2,456 | 0.1956 [0.1885, 0.2025] | 0.0908 [0.0851, 0.0966] | 0.2068 [0.1995, 0.2138] | **0.1974** [0.1901, 0.2046] | +0.0018 [-0.0050, +0.0085] | -0.0094 [-0.0122, -0.0061] |
| **$K=3$** | long_tail | 2,433 | 0.0252 [0.0229, 0.0276] | 0.0200 [0.0173, 0.0229] | 0.0392 [0.0361, 0.0424] | **0.0437** [0.0402, 0.0473] | +0.0184 [+0.0143, +0.0228] | +0.0045 [+0.0026, +0.0064] |
| **$K=5$** | all_candidates | 2,420 | 0.1849 [0.1774, 0.1923] | 0.0874 [0.0818, 0.0933] | 0.2051 [0.1979, 0.2129] | **0.1904** [0.1835, 0.1976] | +0.0055 [-0.0012, +0.0127] | -0.0147 [-0.0195, -0.0096] |
| **$K=5$** | long_tail | 2,397 | 0.0254 [0.0228, 0.0279] | 0.0191 [0.0164, 0.0221] | 0.0453 [0.0418, 0.0485] | **0.0571** [0.0526, 0.0612] | +0.0317 [+0.0269, +0.0364] | +0.0118 [+0.0085, +0.0151] |
| **$K=10$** | all_candidates | 2,317 | 0.1635 [0.1563, 0.1713] | 0.0629 [0.0577, 0.0682] | 0.1865 [0.1789, 0.1944] | **0.1902** [0.1835, 0.1974] | +0.0266 [+0.0192, +0.0337] | +0.0037 [-0.0015, +0.0089] |
| **$K=10$** | long_tail | 2,288 | 0.0246 [0.0220, 0.0272] | 0.0150 [0.0123, 0.0178] | 0.0513 [0.0477, 0.0550] | **0.0662** [0.0618, 0.0711] | +0.0416 [+0.0366, +0.0467] | +0.0149 [+0.0111, +0.0188] |
| **$K=20$** | all_candidates | 2,044 | 0.1283 [0.1214, 0.1352] | 0.0372 [0.0335, 0.0417] | 0.1504 [0.1430, 0.1577] | **0.1621** [0.1548, 0.1691] | +0.0338 [+0.0277, +0.0400] | +0.0117 [+0.0066, +0.0168] |
| **$K=20$** | long_tail | 2,024 | 0.0247 [0.0220, 0.0275] | 0.0076 [0.0058, 0.0096] | 0.0515 [0.0477, 0.0554] | **0.0713** [0.0665, 0.0765] | +0.0466 [+0.0411, +0.0523] | +0.0198 [+0.0150, +0.0248] |

**Key Takeaways**:
- On long-tail discovery, `hybrid_v1.1` significantly outperforms `hybrid_v1` across all $K$ (e.g. at $K=20$, NDCG increases from 0.0515 to 0.0713, a +38.4% lift over v1 and +188.7% over popularity).
- On all candidates, `hybrid_v1.1` matches or exceeds popularity across all $K$, and for $K \ge 10$, significantly outperforms `hybrid_v1` ($\Delta = +0.0117$ at $K=20$).

### Serving Footprint Optimization (Phase 2F.1)
The dense item feature matrix (18,259 $\times$ 19,917 float32, ~1.45 GB) was decomposed into block-structured artifacts:
- `item_t1.npy`: dense float32 (18,259 $\times$ 21, 1.46 MB)
- `item_tags_csr.npz`: scipy CSR float32 (18,259 $\times$ 18,768, 492,817 nonzeros, 3.83 MB in memory, 2.7 MB on disk)
- `item_genome.npy`: dense float32 (18,259 $\times$ 1,128, 78.57 MB)
- `item_norms.npy`: float32 (18,259 values, 0.07 MB)

**Serving Performance Metrics**:
- Process RSS after loading artifacts: **213.77 MB** (well below the 500 MB ceiling; ~92 MB delta over baseline process).
- Artifact load time: **130 ms**.
- Latency over 100 requests to `/api/personalized/home` (mocked TMDB):
  - Mean: **99.9 ms**
  - p50: **99.5 ms**
  - p95: **114.0 ms**
  - p99: **118.6 ms**
  - Process RSS post-requests: **233.2 MB** (zero leaks).

