# Recommendation Explainability & Rank Semantics (Phase 2F / 2F.1)

## 1. Rank Semantics: "Top N% pick"

In MoieRec, recommendations feature an honest rank chip: **Top N% pick** (e.g. `Top 2% pick`).

### Absolute Prohibition of Banned Phrasing
- The words **"Acclaimed"**, **"Strong Match"**, and **"% match"** are **strictly prohibited** across the system, documentation, backend responses, and UI components.
- The rank metric is **NOT** a probability of user engagement.
- It is **NOT** a confidence interval or a simulated compatibility score.
- **Formula**:
  $$N = \max(1, 100 - \text{match\_percent})$$
  where `match_percent` is the candidate item's percentile rank within the candidate pool ($0-100$ integer).
- **Mandatory Tooltip**:
  > *"Relative rank among candidates for your picks, not a probability."*

---

## 2. Percentile Normalization & Hybrid Decomposition

Raw content cosine similarity and popularity counts cannot be directly summed due to different scales and distributions.

1. **Candidate Pool Percentile Normalization**:
   For candidate pool $\mathcal{C}$ with size $M$:
   $$\text{pct}_c(i) = \frac{\text{rank}(s_c(i)) - 1}{M - 1}, \quad \text{pct}_p(i) = \frac{\text{rank}(s_p(i)) - 1}{M - 1}$$
   where ties receive the average fractional rank.
2. **Hybrid Utility Function**:
   $$\text{final}(i) = \alpha(K) \cdot \text{pct}_c(i) + (1 - \alpha(K)) \cdot \text{pct}_p(i)$$
   Under `hybrid_v1.1`, $\alpha(K)$ is determined dynamically by the bucket schedule:
   - $K \in [3, 4] \rightarrow \alpha = 0.3$
   - $K \in [5, 7] \rightarrow \alpha = 0.6$
   - $K \in [8, 14] \rightarrow \alpha = 0.7$
   - $K \ge 15 \rightarrow \alpha = 0.8$
3. **Additive Component Decomposition**:
   $$\text{content\_component} = \alpha(K) \cdot \text{pct}_c(i)$$
   $$\text{popularity\_component} = (1 - \alpha(K)) \cdot \text{pct}_p(i)$$
   These two components strictly sum to the final hybrid score, displayed as real numbers and percentage bars alongside $\alpha$ in the Why-This telemetry modal.

---

## 3. Grounded Explanation Contract & Honest Reason Labels

Every explanation and reason code displayed in the UI is derived from verified mathematical evidence. Fabricated meters, generic copy, and synthetic numbers are strictly forbidden.

### Verified Reason Codes & Formatted Labels (C1):
1. **`SIMILAR_TO_PICK`**:
   - Criterion: Emitted **only if** the cosine similarity between the candidate and the user's nearest liked movie exceeds the data-derived threshold ($\tau_{\text{sim}} \ge 0.1278$, 95th percentile of pairwise item cosines over 50,000 random item pairs).
   - Display String: `"Similar to <pick title>"`
2. **`SHARED_GENRES`**:
   - Criterion: Emitted **only if** at least one genre feature has a positive contribution ($> 0$) to the dot product between the user profile and candidate item vector, and is presented in the top shared features breakdown.
   - Display String: `"Shared genres: <genres>"`
3. **`SHARED_TAGS`**:
   - Criterion: Emitted **only if** at least one tag or genome feature has a positive contribution ($> 0$) to the dot product, and is presented in the top shared features breakdown.
   - Display String: `"Shared tags: <tags>"`
4. **`POPULAR_WITH_VIEWERS`**:
   - Criterion: Emitted **only if** the popularity component exceeds or equals the content component ($\text{popularity\_comp} \ge \text{content\_comp}$).
   - Display String: `"Popular with MovieLens viewers"`
5. **Rule of Evidence**:
   - **No evidence $\rightarrow$ no reason code.** If an item does not satisfy a code's mathematical criterion, that code is not returned.

---

## 4. Row Badges & Semantic Attribution (C2)

Row badges clearly distinguish the underlying algorithmic source of every section:
- **"Picked for You"**: Badge carries **`PERSONALIZED · HYBRID v1.1`** (source: `hybrid_v1.1`).
- **"Because you liked <Title>"**: Badge carries **`SIMILAR BY GENRES & TAGS`** (source: `content_similarity`).
- **Baseline Rows**: Badge carries **`MODEL 0 (POPULARITY)`** (source: `popularity`).

---

## 5. Serving Explanation Schema

```json
{
  "explanation": {
    "nearest_pick": {
      "movie_id": 260,
      "title": "Star Wars: Episode IV - A New Hope",
      "similarity": 0.4521
    },
    "top_shared_features": [
      {
        "feature": "Sci-Fi",
        "raw_name": "t1:genre:Sci-Fi",
        "contribution": 0.0821,
        "feature_type": "genre"
      },
      {
        "feature": "space",
        "raw_name": "tag:space",
        "contribution": 0.0415,
        "feature_type": "tag"
      },
      {
        "feature": "space opera",
        "raw_name": "genome:space opera",
        "contribution": 0.0389,
        "feature_type": "genome_tag"
      }
    ],
    "components": {
      "content": 0.5892,
      "popularity": 0.3940
    },
    "match_percent": 98,
    "alpha": 0.60,
    "similarity_threshold": 0.1278,
    "reason_labels": {
      "SIMILAR_TO_PICK": "Similar to Star Wars: Episode IV - A New Hope",
      "SHARED_GENRES": "Shared genres: Sci-Fi",
      "SHARED_TAGS": "Shared tags: space, space opera"
    }
  }
}
```
