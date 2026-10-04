# Recommendation Explainability & Rank Semantics (Phase 2G-Lite / hybrid_v2)

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
2. **Hybrid Utility Function (v2)**:
   $$\text{final}(i) = w_c(K) \cdot \text{pct}_{\text{CF}}(i) + w_f(K) \cdot \text{pct}_c(i) + w_p(K) \cdot \text{pct}_p(i)$$
   Under `hybrid_v2`, K-adaptive simplex weights $(w_c, w_f, w_p)$ replace the scalar $\alpha$:
   - $K \in [3, 14] \rightarrow (w_c, w_f, w_p) = (0.0, 1.0, 0.0)$ — pure content
   - $K \ge 15 \rightarrow (w_c, w_f, w_p) = (0.1, 0.9, 0.0)$ — 10% CF, 90% content
3. **Additive Component Decomposition**:
   $$\text{cf\_component} = w_c(K) \cdot \text{pct}_{\text{CF}}(i)$$
   $$\text{content\_component} = w_f(K) \cdot \text{pct}_c(i)$$
   $$\text{popularity\_component} = w_p(K) \cdot \text{pct}_p(i)$$
   The three components strictly sum to the final hybrid score, displayed as real numbers and percentage bars alongside $(w_c, w_f, w_p)$ in the Why-This telemetry modal.

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
5. **`CF_EVIDENCE`** (v2 only):
   - Criterion: Emitted **only if** the CF component weight $w_c > 0$ AND the candidate has at least one qualifying neighbour (co-occurrence $\ge 5$) among the user's picks.
   - Display String: `"Co-watched with <pick title> by <cooc> viewers"`
6. **Rule of Evidence**:
   - **No evidence $\rightarrow$ no reason code.** If an item does not satisfy a code's mathematical criterion, that code is not returned.

---

## 4. Row Badges & Semantic Attribution (C2)

Row badges clearly distinguish the underlying algorithmic source of every section:
- **"Picked for You"**: Badge carries **`PERSONALIZED · HYBRID v2`** (source: `hybrid_v2`).
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
    "cf_pick": {
      "movie_id": 1196,
      "title": "Star Wars: Episode V - The Empire Strikes Back",
      "sim": 0.7832,
      "cooc": 142
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
      "cf": 0.0,
      "content": 0.7142,
      "popularity": 0.0
    },
    "match_percent": 98,
    "weights": {"w_c": 0.0, "w_f": 1.0, "w_p": 0.0},
    "alpha": null,
    "similarity_threshold": 0.1278,
    "reason_labels": {
      "SIMILAR_TO_PICK": "Similar to Star Wars: Episode IV - A New Hope",
      "SHARED_GENRES": "Shared genres: Sci-Fi",
      "SHARED_TAGS": "Shared tags: space, space opera"
    }
  }
}
```
