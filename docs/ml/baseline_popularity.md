# Baseline Model 0: Non-Personalized Popularity

## 1. Executive Summary & Purpose

The Popularity baseline (**Model 0**) serves as the empirical performance floor for all recommendation systems developed in MoieRec. It is entirely non-personalized and computed strictly from the **TRAIN** split. 

Every subsequent model (content-based TF-IDF/embeddings, collaborative filtering via SVD/ALS, and hybrid ensembles) must demonstrate statistically significant improvement over this baseline to justify its computational complexity.

---

## 2. Mathematical Formulations

All scores are computed strictly over candidate catalog movies ($\mathcal{I}_{\text{cand}}$: movies with $\ge 1$ rating in TRAIN) using training interactions only:

1. **`most_rated` (Interaction Frequency):**
   $$\text{score}(i) = v_i$$
   where $v_i = |\mathcal{D}_{\text{train}}(i)|$ is the total count of training ratings for movie $i$.

2. **`most_liked` (Positive Frequency):**
   $$\text{score}(i) = v_i^{+} = \sum_{(u, i) \in \mathcal{D}_{\text{train}}} \mathbb{I}(r_{u, i} \ge \tau)$$
   where $\tau = 4.0$ is the dataset positive rating threshold.

3. **`damped_mean` (Bayesian Damped Rating Average):**
   $$\text{score}(i) = \frac{v_i}{v_i + m} R_i + \frac{m}{v_i + m} C$$
   where:
   - $v_i$: total training rating count for movie $i$
   - $R_i$: empirical mean rating of movie $i$ in train
   - $C$: global training rating mean ($C = 3.5356$)
   - $m$: damping hyperparameter (pseudocount prior)

---

## 3. Validation Grid Search & Tuning

Hyperparameter $m$ was tuned across a geometric grid on the **VALIDATION** split only. Models were evaluated across all **94,303 eligible validation users** ($k = 10$, neutral tie-breaking by fixed seeded random permutation `random_perm`, seen items in train masked).

### Validation Grid Results Table (All 94,303 Validation Users)

| Model Variant | Damping $m$ | Precision@10 | Recall@10 | NDCG@10 | HitRate@10 | MRR@10 | Coverage@10 | Mean Rec. Popularity |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`most_liked`** | **—** | **0.0401** | **0.0450** | **0.0519** | **0.2509** | **0.1048** | **0.0152** | **42,145.4** |
| `most_rated` | — | 0.0396 | 0.0449 | 0.0516 | 0.2500 | 0.1050 | 0.0160 | 42,821.0 |
| `damped_mean` | $m=10000$ | 0.0342 | 0.0380 | 0.0437 | 0.2224 | 0.0894 | 0.0109 | 36,396.5 |
| `damped_mean` | $m=5000$ | 0.0317 | 0.0349 | 0.0407 | 0.2102 | 0.0848 | 0.0102 | 34,179.3 |
| `damped_mean` | $m=2500$ | 0.0278 | 0.0302 | 0.0365 | 0.1917 | 0.0795 | 0.0098 | 29,686.0 |
| `damped_mean` | $m=1000$ | 0.0248 | 0.0269 | 0.0329 | 0.1745 | 0.0735 | 0.0086 | 26,652.9 |
| `damped_mean` | $m=500$ | 0.0230 | 0.0249 | 0.0307 | 0.1644 | 0.0698 | 0.0072 | 24,739.1 |
| `damped_mean` | $m=250$ | 0.0200 | 0.0221 | 0.0272 | 0.1482 | 0.0633 | 0.0063 | 21,808.4 |
| `damped_mean` | $m=100$ | 0.0168 | 0.0183 | 0.0203 | 0.1281 | 0.0432 | 0.0056 | 17,637.1 |
| `damped_mean` | $m=50$ | 0.0164 | 0.0180 | 0.0173 | 0.1262 | 0.0312 | 0.0046 | 17,467.6 |
| `damped_mean` | $m=25$ | 0.0157 | 0.0174 | 0.0159 | 0.1220 | 0.0268 | 0.0039 | 17,123.0 |
| `damped_mean` | $m=10$ | 0.0140 | 0.0161 | 0.0145 | 0.1122 | 0.0248 | 0.0030 | 16,117.8 |
| `damped_mean` | $m=5$ | 0.0119 | 0.0139 | 0.0127 | 0.0976 | 0.0227 | 0.0022 | 13,754.0 |
| `damped_mean` | $m=0$ | 0.0040 | 0.0048 | 0.0037 | 0.0373 | 0.0058 | 0.0010 | 4,844.8 |

### Selection Decision:
- **Winning Model:** `most_liked` achieved the highest validation ranking quality (**NDCG@10 = 0.051920**), marginally outperforming `most_rated` (NDCG@10 = 0.051569).
- **Behavioral Analysis of Damped Mean:**
  - At $m=0$ (pure empirical average rating), performance collapses (NDCG@10 = 0.0037). The model promotes obscure movies with 1 or 2 lucky 5-star ratings that have almost zero broad validation appeal.
  - As damping $m$ increases from 5 to 10,000, quality monotonically improves (NDCG rises from 0.0127 to 0.0437) as high rating count begins dominating the formula. However, even with $m=10000$, `damped_mean` remains substantially inferior to pure count-based frequency methods (`most_liked` / `most_rated`). In implicit feedback and Top-$N$ retrieval, interaction volume is an overwhelming indicator of general relevance.

---

## 4. Final Validation Metrics for Selected Model (`most_liked`)

Evaluated on all 94,303 validation users with 95% bootstrap confidence intervals (1,000 resamples, seed=42):

| Metric | Mean | 95% Bootstrap Confidence Interval |
| :--- | :---: | :---: |
| **NDCG@10** | **0.0519** | **[0.0511, 0.0526]** |
| **Precision@10** | **0.0401** | **[0.0395, 0.0407]** |
| **Recall@10** | **0.0450** | **[0.0443, 0.0457]** |
| **HitRate@10** | **0.2509** | **[0.2482, 0.2536]** |
| **MRR@10** | **0.1048** | **[0.1033, 0.1064]** |
| **Catalog Coverage@10** | **0.0152 (1.52%)** | — |
| **Mean Recommended Popularity** | **42,145.4** | **[42,112.5, 42,178.6]** |

### User-Activity Quartile Breakdown (TRAIN Rating Count)

Users were stratified into quartiles based on their historical training interaction count:

| Activity Bucket | Train Interaction Range | Evaluated Users | Precision@10 | Recall@10 | NDCG@10 | HitRate@10 | MRR@10 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Q1 (Low Activity)** | 40 – 61 ratings | 23,735 | 0.0232 | 0.0574 | 0.0440 | 0.1751 | 0.0700 |
| **Q2 (Med-Low Activity)** | 62 – 102 ratings | 23,650 | 0.0296 | 0.0480 | 0.0422 | 0.2058 | 0.0816 |
| **Q3 (Med-High Activity)** | 103 – 201 ratings | 23,425 | 0.0407 | 0.0426 | 0.0480 | 0.2595 | 0.1045 |
| **Q4 (High Activity)** | 202 – 11,163 ratings | 23,502 | 0.0674 | 0.0328 | 0.0745 | 0.3646 | 0.1649 |

#### Key Insights from Activity Breakdown:
- **Precision scales monotonically with user activity:** Q4 users achieve Precision@10 of 6.74% vs. 2.32% for Q1 users. High-activity users interact with far more movies overall, significantly raising the baseline chance that a universally popular blockbuster matches their taste.
- **Recall exhibits inverse behavior:** Q1 users achieve Recall@10 of 5.74% vs. 3.28% for Q4. Because low-activity users have fewer ground-truth positive ratings in validation, each hit captures a larger fraction of their reachable positive set.
- **Hit Rate disparity:** Over 36.46% of high-activity users have at least one hit in Top-10 popular items, compared to only 17.51% of casual users.

---

## 5. Catalog Coverage & Popularity Bias Interpretation

- **Severe Popularity Concentration:**
  The `most_liked` model achieves a catalog coverage of only **1.52%** (recommending only 277 distinct movies out of 18,275 candidate catalog titles across all 94,303 users). Because it is non-personalized, differences in recommendations across users stem entirely from seen-item masking (when a user has already rated a head item in train, the model advances to item #11, #12, etc.).
- **Extreme Rating Inflation:**
  The average movie recommended by `most_liked` has an average of **42,145 training ratings**. This means the model almost exclusively surfaces ubiquitous cultural staples (*The Shawshank Redemption*, *Pulp Fiction*, *The Matrix*, *Forrest Gump*).
- **The Role of the Baseline:**
  A non-personalized model that achieves 25.1% HitRate@10 demonstrates that popular titles carry enormous baseline utility. Any personalized model must demonstrate that it is not simply regurgitating these 200 head items, but actively uncovering relevant items in the long tail without sacrificing precision.

---

## 6. Sampled-User Mode vs. Full Validation Comparison

To verify runtime efficiency and sample reproducibility, the winning variant was evaluated on a fixed random sample of **5,000 users** (seed=42) and compared against the full population of 94,303 users:

| Metric | Full Population Mean ($N=94,303$) | Sample Mean ($N=5,000$) | Absolute Difference | Sample 95% Bootstrap CI |
| :--- | :---: | :---: | :---: | :---: |
| **Precision@10** | 0.040078 | 0.040040 | 0.000038 | [0.0377, 0.0425] |
| **Recall@10** | 0.045010 | 0.044762 | 0.000248 | [0.0418, 0.0482] |
| **NDCG@10** | 0.051920 | 0.052299 | 0.000379 | [0.0491, 0.0557] |
| **HitRate@10** | 0.250883 | 0.248600 | 0.002283 | [0.2362, 0.2612] |
| **MRR@10** | 0.104840 | 0.106241 | 0.001401 | [0.0994, 0.1135] |
| **Mean Recommended Popularity** | 42,145.36 | 42,126.11 | 19.25 | [41,976.7, 42,273.9] |

### Reproducibility & Sample Validity:
- Running the sampled evaluation twice with the identical seed produced **100% bitwise identical results**.
- For every single metric, the absolute difference between the 5,000-user sample and the full population mean is an order of magnitude smaller than the width of the sample's bootstrap CI. This proves that a 5,000-user sample is a highly reliable surrogate for rapid exploratory evaluation.

---

## 7. Rating-Prediction Baselines (Validation Split)

As specified in Phase 2D (Part B5), non-personalized rating prediction models were evaluated to establish an anchor for RMSE and MAE on explicit rating values:

| Method | Hyperparameter | Validation RMSE | Validation MAE | Interaction Count |
| :--- | :---: | :---: | :---: | :---: |
| **`global_mean`** | — | 1.0529 | 0.8220 | 2,174,367 |
| **`movie_mean`** | — | 0.9524 | 0.7326 | 2,174,367 |
| **`damped_movie_mean`** | $m=10$ | **0.9524** | **0.7325** | 2,174,367 |
| **`damped_movie_mean`** | $m=25$ | 0.9530 | 0.7329 | 2,174,367 |
| **`damped_movie_mean`** | $m=50$ | 0.9542 | 0.7337 | 2,174,367 |

*Note: Rating prediction evaluates numerical deviation on observed ratings. It must not be confused with Top-$N$ ranking quality (NDCG / Hit Rate), which evaluates recommendation list generation over the entire catalog.*
