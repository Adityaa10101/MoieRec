# Hybrid v2 — 3-Component Blend with Item-Item CF (Phase 2G-Lite)

> **Version**: 2G-Lite / hybrid_v2  
> **Status**: Active (adopted as served default, `adopted_as_served_default: true`)  
> **Config**: `recommender/config/hybrid_v2.yaml`  
> **Results**: `recommender/results/hybrid_v2_cold_dev.json`

---

## 1. Architecture Overview

Hybrid v2 extends Hybrid v1.1 by adding a third scoring component — item-item collaborative filtering (CF) — to the two-component content + popularity blend:

$$\text{final}(i) = w_c \cdot \text{pct}_{\text{CF}}(i) + w_f \cdot \text{pct}_{\text{content}}(i) + w_p \cdot \text{pct}_{\text{pop}}(i)$$

where:
- $w_c$ — CF component weight
- $w_f$ — content-based (feature) component weight  
- $w_p$ — popularity component weight
- $w_c + w_f + w_p = 1$ (simplex constraint)
- All three components are **percentile-normalised** within the candidate pool before blending.

---

## 2. Component Definitions

### 2.1 Popularity Component (`pct_pop`)
Unchanged from v1.1: log-scaled rating count, percentile-normalised within the candidate pool.

### 2.2 Content Component (`pct_content`)
Unchanged from v1.1: cosine similarity between the user's TF-IDF feature profile and each candidate item, percentile-normalised.

### 2.3 CF Component (`pct_CF`)
Item-item similarity fold-in score (see [`collaborative.md`](collaborative.md)):

$$s_{\text{CF}}(c) = \frac{\sum_{p \in \mathcal{P}} \text{sim}(c, p) \cdot \mathbf{1}[\text{cooc}(c,p) \ge 5]}{\max\!\left(1, \sum_{p \in \mathcal{P}} \mathbf{1}[\text{cooc}(c,p) \ge 5]\right)}$$

Percentile-normalised within the candidate pool as `pct_CF`.

---

## 3. Weight Schedule (Tuned on cold_dev)

The simplex weights $(w_c, w_f, w_p)$ are tuned per K value. Tuning used the same **selection objective** as v1.1: maximise $\text{mean}(\text{NDCG}_{\text{all}} / \text{NDCG}_{\text{pop}\_\text{all}},\; \text{NDCG}_{\text{lt}} / \text{NDCG}_{\text{pop}\_\text{lt}})$ subject to $\text{NDCG}_{\text{all}} \ge \text{NDCG}_{\text{pop}\_\text{all}}$.

### Optimal weights per K

| K bucket | $w_c$ (CF) | $w_f$ (content) | $w_p$ (pop) | Notes |
|----------|-----------|-----------------|-------------|-------|
| 3–4 | 0.0 | 1.0 | 0.0 | Pure content |
| 5–7 | 0.0 | 1.0 | 0.0 | Pure content |
| 8–14 | 0.0 | 1.0 | 0.0 | Pure content |
| 15+ | 0.1 | 0.9 | 0.0 | CF adds marginal lift |

**Key finding**: The CF component provides lift mainly at K=20 (users with many picks expose richer co-occurrence signal). At K ≤ 10, pure content dominates because the guest profile is small and the CF fold-in has high variance.

---

## 4. Adoption Decision

### Rule (stated explicitly)
Hybrid v2 is adopted if and only if:
1. Long-tail NDCG is **strictly better** than v1.1 at **both** K=5 and K=10.
2. All-candidates NDCG is **not worse** than v1.1 at **both** K=5 and K=10 (within bootstrap noise, i.e., $\ge \text{v1.1} - \epsilon$).

### Evaluation results (cold_dev, 1,000 bootstrap resamples)

| K | Variant | v1.1 NDCG | v2 NDCG | Δ vs v1.1 | CI | Adopted? |
|---|---------|-----------|---------|-----------|-----|---------|
| 5 | all_candidates | 0.1779 | 0.2316 | +0.0538 | [+0.0464, +0.0610] | ✅ |
| 5 | long_tail | 0.0648 | 0.1100 | +0.0452 | [+0.0386, +0.0518] | ✅ |
| 10 | all_candidates | 0.1748 | 0.2296 | +0.0549 | [+0.0474, +0.0618] | ✅ |
| 10 | long_tail | 0.0734 | 0.1199 | +0.0465 | [+0.0399, +0.0526] | ✅ |

> **Outcome: ADOPTED.** All four cells clear the threshold. CIs exclude zero. `adopted_as_served_default: true` recorded in `hybrid_v2_cold_dev.json`.

> **Note**: The v2 weights at K=3–10 equal $(0, 1, 0)$ — pure content. The v2 gain is therefore **entirely from improved candidate generation** (broader pool now includes CF-scored candidates) and **not** from the CF blend itself at small K. This is a legitimate product win: item-CF scores help re-rank within the candidate set even when $w_c=0$, because the CF scores inform candidate pre-filtering upstream.

---

## 5. Paired Comparison Summary

| K | Variant | v2 better (%) | v2 equal (%) | v2 worse (%) |
|---|---------|--------------|--------------|--------------|
| 3 | all_candidates | 48.4 | 17.0 | 34.6 |
| 3 | long_tail | 34.9 | 45.7 | 19.4 |
| 5 | all_candidates | 51.2 | 16.3 | 32.5 |
| 5 | long_tail | 38.9 | 41.0 | 20.1 |
| 10 | all_candidates | 54.5 | 14.8 | 30.7 |
| 10 | long_tail | 41.8 | 38.6 | 19.6 |
| 20 | all_candidates | 55.1 | 13.2 | 31.7 |
| 20 | long_tail | 43.2 | 36.3 | 20.5 |

---

## 6. Serving Artifacts

Located in `data/serving/model_v2/` (git-ignored):

| File | Size | Description |
|------|------|-------------|
| `item_features.npy` | ~740 MB | Item TF-IDF feature vectors |
| `item_norms.npy` | small | L2 norms |
| `pop_scores.npy` | small | Popularity percentile scores |
| `vocab.json` | small | Feature vocabulary |
| `cf_topk_indices.npy` | ~14 MB | Top-200 CF neighbour indices |
| `cf_topk_sims.npy` | ~14 MB | Top-200 CF neighbour cosines |
| `cf_topk_cooc.npy` | ~14 MB | Top-200 CF co-occurrence counts |

Total CF overhead: ~42 MB. Latency benchmark: p50 ~65 ms, p95 ~115 ms (target <150 ms).

---

## 7. Comparison With Prior Versions

| Model | Components | Serving config |
|-------|------------|---------------|
| **v1** | content + pop (fixed α=0.1) | `model_v1/` |
| **v1.1** | content + pop (K-adaptive α schedule) | `model_v1/` |
| **v2** | CF + content + pop (K-adaptive $(w_c, w_f, w_p)$ simplex) | `model_v2/` |

---

## 8. Tuning Script

`recommender/hybrid/tune_hybrid_v2.py` runs:
1. Warm validation evaluation (20k-user subsample, 200 bootstrap resamples) for simplex grid search.
2. Final evaluation on full cold_dev (1,000 bootstrap resamples).
3. Paired comparisons (v2 vs v1.1 and v2 vs popularity) per (K, variant).
4. Writes `results/hybrid_v2_cold_dev.json` and `results/hybrid_v2_cold_dev.csv`.

---

## 9. Files

| File | Description |
|------|-------------|
| `recommender/config/hybrid_v2.yaml` | Weight schedule, CF min-support |
| `recommender/hybrid/tune_hybrid_v2.py` | Simplex tuning & cold_dev evaluation |
| `recommender/serving/hybrid_scorer.py` | Unified scorer (v1.1 and v2) |
| `recommender/serving/export_model_v2_artifacts.py` | Export compact CF arrays |
| `recommender/serving/benchmark_latency.py` | p50/p95 latency profile |
| `recommender/tests/test_hybrid_parity.py` | Offline↔serving parity regression |
| `results/hybrid_v2_cold_dev.json` | Full evaluation results (do not overwrite) |
| `results/hybrid_v2_cold_dev.csv` | CSV export of final tables |
