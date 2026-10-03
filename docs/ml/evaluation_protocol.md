# Offline Evaluation Protocol & Metrics Specification

## 1. Ground Truth & Binary Relevance Definition

Recommendation in MoieRec is formulated as Top-$N$ ranking under implicit and thresholded explicit feedback.

- **Positive Threshold (`positive_threshold`):**
  A rating $r_{u, i} \ge 4.0$ (configurable in `recommender/config/datasets.yaml`) constitutes an explicit **positive** interaction.
  - Ratings $< 4.0$ (e.g. 0.5 to 3.5) represent neutral or negative impressions and are **NOT** treated as relevant targets in Top-$N$ ranking evaluation.
- **Single Source of Truth:**
  The threshold is loaded strictly from configuration and propagated through split metadata and metric calculation.

---

## 2. Temporal Splitting Protocol

1. **Deterministic User Partitioning:**
   - 5% of eligible users are held out entirely as cold-start evaluation users (`splits/cold_start_users.parquet`).
2. **Per-User Chronological 80/10/10 Split:**
   - For each remaining user $u$ with ratings ordered deterministically by $(\text{timestamp}, \text{tie\_hash})$ where $\text{tie\_hash} = \text{hash}_{64}(\text{user\_id}, \text{movie\_id}, \text{seed}=42)$:
     - $n_{\text{test}} = \max(1, \text{round}(0.1 \cdot n_u))$
     - $n_{\text{val}} = \max(1, \text{round}(0.1 \cdot n_u))$
     - $n_{\text{train}} = n_u - n_{\text{val}} - n_{\text{test}}$
     - Earliest $n_{\text{train}}$ items $\to \mathcal{D}_{\text{train}}$
     - Next $n_{\text{val}}$ items $\to \mathcal{D}_{\text{val}}$
     - Latest $n_{\text{test}}$ items $\to \mathcal{D}_{\text{test}}$
3. **Temporal Ordering Reality & Session Spree Limitation:**
   - Analysis of MovieLens 25M (`session_stats.json`) reveals:
     - **46.51% of users** have their entire rating history span less than 24 hours ($< 1$ day).
     - **23.56% of all ratings** share an identical timestamp with another rating by the same user.
     - The **median user history span** across the benchmark is only **2.03 days**.
   - *Limitation:* For nearly half of all users, "chronological" order is effectively the click order of an onboarding rating spree rather than longitudinal viewing over months or years. Deterministic secondary sorting by seeded hash of `(user_id, movie_id)` is strictly enforced to prevent arbitrary ranking order without injecting movie_id popularity bias.

---

## 3. Candidate Generation, Reachable Positives, & Leakage Prevention

### Candidate Catalog:
- **Candidate Catalog $\mathcal{I}_{\text{cand}}$:** Benchmark movies with $\ge 1$ rating in the **TRAIN** split (18,275 movies in ML-25M).
- **DOCUMENTATION NOTE ON NEW ITEMS:**
  This benchmark does **not** evaluate recommendation of completely new, unrated items. New-item recommendation for TMDB-only releases is a separate production capability, to be evaluated separately in later phases using content-based signals; it must not be confused with collaborative user cold-start.

### Reachable Relevant Items:
- A user's positive in the evaluated split ($r_{u, i} \ge \text{positive\_threshold}$) is **reachable** if and only if movie $i \in \mathcal{I}_{\text{cand}}$.
- Any positive whose movie has zero train ratings is dropped from the reachable relevant set:
  - In ML-25M Validation: **0 out of 984,414 positives** (0.00%) have zero train ratings.
  - In ML-25M Test: **30 out of 1,003,456 positives** (0.003%) have zero train ratings.
- Ranking metrics (NDCG ideal DCG, recall denominator, hit rate, MRR) are computed strictly against the **reachable** relevant set.

### Seen-Item Masking:
- **Validation Mode:** Candidates exclude the user's TRAIN items ($\mathcal{C}_{\text{val}}(u) = \mathcal{I}_{\text{cand}} \setminus \mathcal{I}_{\text{train}}(u)$).
- **Test Mode:** Candidates exclude both TRAIN and VALIDATION items ($\mathcal{C}_{\text{test}}(u) = \mathcal{I}_{\text{cand}} \setminus (\mathcal{I}_{\text{train}}(u) \cup \mathcal{I}_{\text{val}}(u))$).
- **Vectorized Masking:** Masking is implemented via a sparse user $\times$ item binary CSR matrix in memory, never through iterative Python user loops.
- **Test Mode Guard:** Test mode execution is strictly guarded in code: it raises an explicit exception unless called with `final=True` and a valid frozen-configuration identifier. In Phase 2D, the real test file is never read.

---

## 4. Evaluation Eligibility Rule

- Relevant items for ranking are defined strictly as $\mathcal{R}_{\text{reachable}}(u) = \{i \in \text{Split}(u) \mid r_{u,i} \ge \text{positive\_threshold} \text{ and } i \in \mathcal{I}_{\text{cand}}\}$.
- **Denominator Rule:** Users with zero reachable positive ratings in the evaluated split ($|\mathcal{R}_{\text{reachable}}(u)| = 0$) are excluded from ranking metric denominators (Recall, Precision, NDCG, HitRate, MRR) to avoid undefined scores.
- The total user count and eligible user percentage are reported in audit metadata.

---

## 5. The Final-Fit Workflow

To prevent hyperparameter over-fitting on the test set, MoieRec follows the strict two-step Final-Fit protocol:

```
[Phase 1: Validation Tuning]
  - Train candidate models on TRAIN split only.
  - Evaluate and tune hyperparameters on VALIDATION split.
  - Select best model architecture and optimal weights.

[Phase 2: Final Fit & Evaluation]
  - Freeze all hyperparameter configurations.
  - Refit selected model on combined TRAIN + VALIDATION splits.
  - Evaluate on TEST split exactly ONCE.
  - Report frozen test numbers without post-hoc tuning.
```

---

## 6. Metric Formulations

Let $\hat{L}_{10}(u) = [i_1, i_2, \dots, i_{10}]$ be the Top-10 recommended items for user $u$, and let $\mathcal{R}(u)$ be the user's ground-truth relevant items in the evaluated split.

### Precision@10:
$$\text{Precision@10}(u) = \frac{|\hat{L}_{10}(u) \cap \mathcal{R}(u)|}{10}$$

### Recall@10:
$$\text{Recall@10}(u) = \frac{|\hat{L}_{10}(u) \cap \mathcal{R}(u)|}{|\mathcal{R}(u)|}$$

### HitRate@10:
$$\text{HitRate@10}(u) = \mathbb{I}\left(|\hat{L}_{10}(u) \cap \mathcal{R}(u)| > 0\right)$$

### Normalized Discounted Cumulative Gain (NDCG@10):
$$\text{DCG@10}(u) = \sum_{k=1}^{10} \frac{\mathbb{I}(i_k \in \mathcal{R}(u))}{\log_2(k + 1)}, \quad \text{NDCG@10}(u) = \frac{\text{DCG@10}(u)}{\text{IDCG@10}(u)}$$
where $\text{IDCG@10}(u)$ is the ideal DCG obtained by sorting all relevant items at the top ranks.

### Mean Reciprocal Rank (MRR@10 - Secondary):
$$\text{MRR@10}(u) = \begin{cases} \frac{1}{\text{rank}_{\text{first}}}, & \text{if first relevant item is at rank } \le 10 \\ 0, & \text{otherwise} \end{cases}$$

### Rating Prediction Metrics (Secondary Task):
$$\text{RMSE} = \sqrt{\frac{1}{|\mathcal{D}|}\sum_{(u,i) \in \mathcal{D}} (\hat{r}_{u,i} - r_{u,i})^2}, \quad \text{MAE} = \frac{1}{|\mathcal{D}|}\sum_{(u,i) \in \mathcal{D}} |\hat{r}_{u,i} - r_{u,i}|$$
*Note: Rating prediction (RMSE/MAE) is treated strictly as an auxiliary diagnostic and is never the primary product ranking metric.*

### Reserved Metrics:
- **Catalog Coverage:** Unique items recommended across all users divided by total catalog size.
- **Intra-List Diversity:** Average pairwise cosine distance between recommended items in $\hat{L}_{10}(u)$.
- **Popularity Bias / Mean Recommended Popularity:** Average training interaction count of recommended items.

---

## 7. User Breakdown Strata & Segmented Evaluation

To reveal model performance variations across distinct engagement patterns, the evaluator produces granular breakdowns alongside global metrics:

### 1. User Activity Quartiles:
Partitioned by the count of user interactions in $\mathcal{D}_{\text{train}}$:
- **Q1 (Low Activity):** 40 to 61 train ratings (23,727 users)
- **Q2 (Med-Low Activity):** 62 to 102 train ratings (23,652 users)
- **Q3 (Med-High Activity):** 103 to 201 train ratings (23,421 users)
- **Q4 (High Activity):** 202 to 11,163 train ratings (23,503 users)

### 2. Session-Span Strata:
Computed from the full span of user interaction timestamps: $\Delta t = (\max(t_u) - \min(t_u)) / 86400.0$ days:
- **Stratum 1: $< 1$ day (Onboarding Spree):** 46.06% of evaluated users (43,434 users). These users rated their entire history in a single concentrated session.
- **Stratum 2: $1 - 30$ days (Short-term / Casual):** 16.48% of evaluated users (15,541 users).
- **Stratum 3: $\ge 30$ days (Multi-session / Longitudinal):** 37.46% of evaluated users (35,328 users). Multi-month/year users exhibiting genuine temporal drift.

---

## 8. Tie-Break Bias Elimination & Exact Neutral Boundary Handling

### 1. Chronological Boundary Tie-Break Bias & Resolution (Phase 2E.1):
Earlier splits sorted tied timestamps deterministically by `(timestamp, movie_id)`. Because MovieLens IDs roughly correlate with the chronological addition of movies to the MovieLens system, tied ratings at a split cut point skewed held-out items toward newer movie IDs.
In Phase 2E.1, the secondary sort key was replaced with a deterministic seeded 64-bit hash of `(user_id, movie_id)` (`seed=42`).

**Comparison of Split Cut Skew (Old vs New):**
- **Train|Validation Cut:** **17.21% of users** (16,745 users) have their split cut point fall inside a tied-timestamp group.
  - *Old (`movie_id` sort):* Train mean `movie_id` = **12,067.0** vs Val = **24,289.1** (normalized rank: **0.266** vs **0.767**).
  - *New (hash tie-break):* Train mean `movie_id` = **19,995.4** vs Val = **17,870.6** (normalized rank: **0.49916** vs **0.50096** — perfectly neutral ~0.50!).
- **Validation|Test Cut:** **15.81% of users** (15,376 users) have their split cut point fall inside a tied-timestamp group.
  - *Old (`movie_id` sort):* Val mean `movie_id` = **11,073.9** vs Test = **24,274.8** (normalized rank: **0.235** vs **0.769**).
  - *New (hash tie-break):* Val mean `movie_id` = **16,906.6** vs Test = **15,523.2** (normalized rank: **0.50029** vs **0.49971** — perfectly neutral ~0.50!).
- **Conclusion:** The split cut skew has been completely eliminated.

### 2. Evaluator Neutral Tie-Breaking (`select_topk_exact` with `random_perm`):
Earlier evaluations broke equal-score ties by lower candidate catalog index (which corresponds to lower `movie_id`, heavily correlated with train popularity: Spearman $r = -0.5340$). In Phase 2E.1, this was replaced with a fixed, seeded random permutation of candidate items (`tie_break="random_perm"`):
- Spearman correlation with candidate `movie_id`: $r = -0.0051$ ($p = 0.49$).
- Spearman correlation with train `rating_count`: $r = +0.0078$ ($p = 0.29$).
- Guaranteed neutral tie-breaking without popularity contamination, while preserving exact boundary selection and identical outputs across repeated runs.

---

## 9. Paired Statistical Comparison Protocol (`Evaluator.compare`)

To determine whether the performance difference between two models $\mathcal{M}_A$ and $\mathcal{M}_B$ is statistically distinguishable from zero, the evaluator implements paired bootstrap hypothesis testing:
1. **User Alignment:** Evaluates per-user metric arrays $\mathbf{m}_A$ and $\mathbf{m}_B$ computed across the exact same evaluated users ($N = 94,303$).
2. **Mean Difference & Relative Lift:**
   $$\Delta = \bar{m}_A - \bar{m}_B, \quad \text{Lift} = \frac{\bar{m}_A - \bar{m}_B}{\bar{m}_B}$$
3. **Paired Vectorized Bootstrap CI:**
   Resamples $N$ users with replacement over 1,000 bootstrap iterations (`seed=42`) using chunked matrix indexing to generate empirical 95% confidence intervals $[\Delta_{\text{lower}}, \Delta_{\text{upper}}]$.
4. **Distinguishability:** The difference is statistically distinguishable from zero ($p < 0.05$) if and only if $0 \notin [\Delta_{\text{lower}}, \Delta_{\text{upper}}]$.
5. **Win/Tie/Loss Shares:** Reports percentage of users where $m_{A}(u) > m_{B}(u)$, $m_{A}(u) = m_{B}(u)$, and $m_{A}(u) < m_{B}(u)$.

---

## 10. Simulated Cold-Start Onboarding Evaluation Protocol (Protocol v2)

Tests the product claim: *"A brand-new user picks a few movies they like and gets personalized recommendations immediately."*

### 1. Population & Guard:
- 5,119 cold-start users held out in `splits/cold_start_users.parquet` are deterministically partitioned 50/50 (`seed=42`) into:
  - `cold_dev` (2,559 users): used for hyperparameter tuning and model evaluation.
  - `cold_final` (2,560 users): strictly guarded behind `final=True` and reserved for the final benchmark report.

### 2. Protocol v2 Specification:
For each onboarding set size $K \in \{3, 5, 10\}$:
1. **Eligibility Filter:** User must have $\ge K + W$ ($W = 20$) positive ratings ($r_{u, i} \ge \text{positive\_threshold}$) in candidate catalog items.
2. **Revealed Picks:** User's candidate positives are ordered chronologically by `(timestamp, tie_hash)`. The first $K$ positives form the **ONBOARDING** revealed set $\mathcal{O}_K(u)$.
3. **Target Relevant Set:** The NEXT $W=20$ candidate positives chronologically form the ground-truth relevant set.
4. **Evaluation Variants:**
   - **Variant (i) All Candidates:** Candidate catalog minus the $K$ revealed items.
   - **Variant (ii) Long-Tail:** Candidate catalog minus the $K$ revealed items AND minus the 200 most-rated TRAIN movies. The 200 most-rated TRAIN movies are also excluded from the relevant set.
   - **Reference Protocol:** Old "all remaining positives" protocol kept as a labeled comparison reference.
5. **Evaluated Models:**
   - **Popularity Baseline (`most_liked`):** Recommends top candidate items by train positive volume, masking revealed (and long-tail) items.
   - **Content-Based Tier 1:** User profile constructed solely from the $K$ revealed items.
   - **Content-Based Tier 2 Snapshot:** User profile constructed solely from the $K$ revealed items using Tier 2 feature vectors (labeled `snapshot_features=true`).
6. **Comparability Caveat:** Cold-start tables are **NOT** comparable with validation tables because the relevant evaluation sets and candidate spaces are fundamentally different.


