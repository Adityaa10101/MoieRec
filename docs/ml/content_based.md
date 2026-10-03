# Content-Based Recommender (Model 1) Specification & Empirical Findings

## 1. Executive Summary & Design Principles

The Content-Based Recommender (Model 1) represents MoieRec's first personalized model. Unlike the non-personalized Popularity Baseline (Model 0), Model 1 learns individual user preference vectors from their explicit historical ratings and matches them to candidate item representations using cosine similarity.

### Core Capabilities & Limitations:
1. **Long-Tail Discovery & Anti-Popularity:**
   - Popularity baselines concentrate recommendations on a tiny fraction of the catalog (Catalog Coverage = **1.52%**, Mean Recommended Train Popularity = **42,145.4 ratings**).
   - Content-based modeling distributes recommendations across a broad catalog footprint (**Coverage = 16.96%**, Mean Recommended Train Popularity = **1,692.3 ratings**), an **11.2x expansion** in item catalog diversity with an average popularity reduction of **-95.98%**.
2. **Transparent Explainability:**
   - Every recommendation can be decomposed into exact feature contributions ($\mathbf{p}_{u, f} \cdot \mathbf{x}_{i, f}$).
   - `explain(user_idx, item_idx, top_n=3)` attributes recommendations to specific genres and eras without black-box opacity.
3. **Instant Onboarding Personalization:**
   - A brand-new user with zero collaborative history can select $K \in \{3, 5, 10\}$ movies during onboarding, enabling immediate personalized recommendations without waiting for collaborative matrix factorizations or graph traversals.
4. **Ranking Limitation (Why Content Loses to Popularity):**
   - In offline Top-$N$ ranking accuracy over all validation users, Tier 1 Content-Based (**NDCG@10 = 0.0028**, HitRate@10 = 0.0223) is strictly inferior to Popularity Most Liked (**NDCG@10 = 0.0519**, HitRate@10 = 0.2509), with a statistically significant relative lift of **-94.57%** ($p < 0.05$).
   - **Neutral Tie-Breaking Insight:** Earlier evaluations (Phase 2E) reported Tier 1 NDCG@10 of 0.0051 under lower-index tie-breaking. Diagnostic A1 demonstrated that index tie-breaking injected a strong negative popularity prior (Spearman $r = -0.5340$), artificially inflating NDCG by +120%. Under neutral `random_perm` tie-breaking, the true unadulterated genre-only NDCG is 0.0028.
   - **Why?** 19 coarse genre dimensions contain zero collaborative co-occurrence signal. On an 18,275 item catalog, recommending purely by genre overlap matches broad thematic categories (e.g. Comedy, Drama) but completely lacks the quality/consensus signals required to separate acclaimed masterpieces from obscure low-engagement films. Content-only models cannot substitute for collaborative filtering among warm users; their architectural role in MoieRec is cold-start bootstrapping, explainability attribution, and candidate diversity in hybrid ranking.

---

## 2. Feature Representation & Model Architecture

### Tier 1 Clean Temporal Representation (21 Dimensions)
Extracted strictly from pre-split metadata (`features/tier1_baseline_features.npz`):
- **19 Genre Indicators:** Binary flags across MovieLens standard genres (Action, Adventure, Animation, Children, Comedy, Crime, Documentary, Drama, Fantasy, Film-Noir, Horror, IMAX, Musical, Mystery, Romance, Sci-Fi, Thriller, War, Western).
- **Normalized Release Year:** Min-max scaled year $\in [0, 1]$ (spanning 1878 to 2019).
- **Missing Year Flag:** Indicator for movies without release year data.
- **Normalization:** Each item feature vector $\mathbf{x}_i$ is $L_2$-normalized after applying feature weights:
  $$\mathbf{x}_i \leftarrow \frac{\mathbf{x}_i}{\|\mathbf{x}_i\|_2}$$

### Tier 2 Snapshot Feature Representation (Tags & Genome)
Combines clean metadata with rich text and semantic signals:
- **Block 1 (Tier 1):** 19 genres + release year (weight $w_{\text{t1}}$).
- **Block 2 (Tag TF-IDF):** 18,768 vocabulary dimensions derived from user tagging (`tier2_tag_tfidf.npz`, weight $w_{\text{tags}}$).
- **Block 3 (Tag Genome):** 1,128 tag relevance dimensions (`tier2_genome_matrix.npy`, weight $w_{\text{genome}}$), masked by `tier2_genome_mask.npy` (75.59% catalog coverage; unrated items have a zero block with no synthetic imputation).
- **Concatenated Representation:**
  $$\mathbf{x}_i = \frac{[w_{\text{t1}} \mathbf{x}_{i, \text{t1}}, \; w_{\text{tags}} \mathbf{x}_{i, \text{tags}}, \; w_{\text{genome}} \mathbf{x}_{i, \text{genome}}]}{\sqrt{w_{\text{t1}}^2 \|\mathbf{x}_{i, \text{t1}}\|^2 + w_{\text{tags}}^2 \|\mathbf{x}_{i, \text{tags}}\|^2 + w_{\text{genome}}^2 \|\mathbf{x}_{i, \text{genome}}\|^2}}$$

> [!WARNING]
> **CRITICAL TEMPORAL LEAKAGE NOTICE (TIER 2 SNAPSHOT):**
> Tag TF-IDF and Tag Genome features were aggregated over historical data up to November 2019. Because user tags and genome relevance scores encapsulate future post-release information, Tier 2 features leak semantic signals across chronological splits. These results are reported in a separate experiment labeled `snapshot_features=true` and must never be mixed into Tier 1 clean temporal results.

---

## 3. User Profile Weighting Variants

User profiles $\mathbf{p}_u$ are constructed strictly from training interactions ($\mathcal{D}_{\text{train}}$) via sparse-matrix multiplication:
$$\mathbf{P}_{\text{raw}} = \mathbf{W} \mathbf{X}, \quad \mathbf{p}_u = \frac{\mathbf{p}_{u, \text{raw}}}{\|\mathbf{p}_{u, \text{raw}}\|_2}$$

Four interaction weighting strategies $\mathbf{W}_{u, i}$ were evaluated on the validation split:
1. **`pos_mean`:** Equal weighting over positive interactions ($r_{u, i} \ge 4.0$). Disregards negative feedback.
2. **`rating_weighted`:** Linear rating weighting across all train ratings ($w_{u, i} = r_{u, i}$).
3. **`centered`:** Mean-centered rating weighting ($w_{u, i} = r_{u, i} - \bar{r}_u$). Positive deviations pull the profile toward preferred attributes; negative deviations push the profile away from disliked genres.
4. **`pos_rating_weighted`:** Rating-weighted positives ($w_{u, i} = r_{u, i}$ for $r_{u, i} \ge 4.0$; 0 otherwise).

### Zero-Profile Users & Neutral Boundary Handling:
Users with no qualifying ratings receive all-zero profile vectors $\mathbf{p}_u = \mathbf{0}$, producing uniform zero cosine scores. Deterministic tie-breaking orders candidates by a fixed seeded random permutation (`tie_break="random_perm"`, `seed=42`), eliminating any popularity bias. Zero-profile user counts are explicitly tracked and reported.

---

## 4. Part B: Tier 1 Validation Grid Search (20,000 Users)

The hyperparameter space (4 profile variants $\times$ 2 genre IDF options $\times$ 4 year weights $w_{\text{year}} \in \{0.0, 0.25, 0.5, 1.0\} = 32$ configurations) was evaluated on a fixed validation sample of 20,000 users (`seed=42`) with `random_perm` tie-breaking.

### Grid Results Summary (Top Configurations on Sample $N=20,000$):

| Profile Variant | Genre IDF | $w_{\text{year}}$ | NDCG@10 | Precision@10 | Recall@10 | HitRate@10 | MRR@10 | Zero-Prof Users |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`pos_rating_weighted` (BEST)** | **True** | **0.00** | **0.002880** | **0.002390** | **0.002996** | **0.0226** | **0.006506** | **1** |
| `pos_mean` | True | 0.00 | 0.002831 | 0.002345 | 0.002953 | 0.0222 | 0.006394 | 1 |
| `pos_rating_weighted` | False | 0.00 | 0.002675 | 0.002220 | 0.002743 | 0.0214 | 0.006001 | 1 |
| `pos_mean` | False | 0.00 | 0.002665 | 0.002175 | 0.002710 | 0.0209 | 0.005990 | 1 |
| `centered` | True | 0.00 | 0.002549 | 0.002010 | 0.002348 | 0.0187 | 0.005705 | 4 |
| `rating_weighted` | True | 0.00 | 0.002503 | 0.002155 | 0.002673 | 0.0208 | 0.005470 | 0 |
| `centered` | True | 1.00 | 0.002383 | 0.001885 | 0.002190 | 0.0173 | 0.005273 | 4 |
| `centered` | True | 0.25 | 0.002360 | 0.001835 | 0.002111 | 0.0167 | 0.005256 | 4 |
| `centered` | False | 0.00 | 0.002343 | 0.001885 | 0.002238 | 0.0179 | 0.005086 | 4 |
| `centered` | True | 0.50 | 0.002343 | 0.001825 | 0.002097 | 0.0167 | 0.005230 | 4 |

### Architectural Insights from Tuning:
1. **Genre IDF Provides Genuine Discriminative Signal:** Unlike in the biased index tie-break setup, IDF weighting consistently improves accuracy across both `pos_rating_weighted` (0.002880 vs 0.002675) and `pos_mean` (0.002831 vs 0.002665) by downweighting ubiquitous genres (Drama, Comedy).
2. **Positive-Rating Weighting Beats Mean-Centering:** Under neutral tie-breaking, `pos_rating_weighted` achieves the best score (0.002880), outperforming `centered` (0.002549). Scaling 4.5 and 5.0 star films higher than 4.0 stars produces superior positive preference direction.
3. **Release Year Penalizes Content Ranking:** Across all variants, $w_{\text{year}} = 0.00$ maximizes ranking accuracy. Adding release year as a continuous scalar collapses cosine similarity around chronological clusters.

---

## 5. Full Validation Evaluation (All 94,303 Users)

The chosen Tier 1 configuration (`pos_rating_weighted`, `use_genre_idf=True`, `year_weight=0.0`) was evaluated across all 94,303 validation users with 1,000 bootstrap resamples.

### Metric Performance (Tier 1 vs Popularity Most Liked):

| Metric | Content-Based Tier 1 (95% CI) | Popularity Most Liked (95% CI) | Paired Diff (A - B) | 95% Bootstrap CI | Relative Lift | Distinguishable? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **NDCG@10** | **0.002819** [0.002681, 0.002967] | **0.051920** [0.051107, 0.052611] | -0.049101 | [-0.049806, -0.048358] | -94.57% | **YES ($p < 0.05$)** |
| **HitRate@10** | **0.022300** [0.021367, 0.023371] | **0.250883** [0.248115, 0.253694] | -0.228583 | [-0.231454, -0.225721] | -91.11% | **YES ($p < 0.05$)** |
| **Recall@10** | **0.002984** [0.002806, 0.003170] | **0.045010** [0.044264, 0.045719] | -0.042026 | [-0.042738, -0.041289] | -93.37% | **YES ($p < 0.05$)** |
| **Precision@10** | **0.002327** [0.002230, 0.002434] | **0.040078** [0.039524, 0.040628] | — | — | — | — |
| **MRR@10** | **0.006199** [0.005842, 0.006559] | **0.104840** [0.103258, 0.106467] | — | — | — | — |
| **Catalog Coverage** | **0.169631** (16.96%) | **0.015157** (1.52%) | — | — | **+1,019.2%** | — |
| **Mean Recommended Pop** | **1,692.3** [1,681.0, 1,702.5] | **42,145.4** [42,112.2, 42,177.8] | — | — | **-95.98%** | — |

### User Win/Equal/Loss Distribution:
- **NDCG@10:** Content-Based Better: **1.70%** | Equal: **74.08%** | Popularity Better: **24.23%**
- **HitRate@10:** Content-Based Better: **1.48%** | Equal: **75.05%** | Popularity Better: **23.47%**
- **Recall@10:** Content-Based Better: **1.51%** | Equal: **74.60%** | Popularity Better: **23.89%**

### Performance Across Strata & Quartiles:
- **Session-Span Breakdown:**
  - `< 1 day` (Onboarding Spree, 43,434 users): NDCG@10 = 0.002592, HitRate@10 = 0.018580, Precision@10 = 0.001932.
  - `1 - 30 days` (Casual, 15,541 users): NDCG@10 = 0.002757, HitRate@10 = 0.021427, Precision@10 = 0.002271.
  - `$\ge 30$ days` (Multi-session, 35,328 users): NDCG@10 = 0.003127, HitRate@10 = 0.027259, Precision@10 = 0.002836.
- **Activity Quartiles:**
  - $Q_1$ (Lowest Train Ratings): NDCG@10 = 0.002621, HitRate@10 = 0.015215.
  - $Q_2$ (Med-Low Train Ratings): NDCG@10 = 0.002377, HitRate@10 = 0.017757.
  - $Q_3$ (Med-High Train Ratings): NDCG@10 = 0.002651, HitRate@10 = 0.022373.
  - $Q_4$ (Highest Train Ratings): NDCG@10 = 0.003634, HitRate@10 = 0.033953.

---

## 6. Explainability Feature (`explain()`)

For production explainability and UI badges, `explain(user_idx, item_idx, top_n=3)` decomposes the cosine similarity score into individual feature contributions:
$$\text{Score}(u, i) = \sum_{f} \mathbf{p}_{u, f} \cdot \mathbf{x}_{i, f}$$

### Guarantees & Verification:
- **Exact Sum:** The sum of all feature contributions matches the model score within float tolerance ($< 10^{-5}$).
- **Non-Zero Filter:** Zero-contribution features are strictly omitted.
- **Relative Share:** Features are reported with percentage shares of the total score.

```python
# Example explanation output:
[
  {"feature": "genre:Drama", "contribution": 0.428105, "percentage": 61.2},
  {"feature": "genre:Sci-Fi", "contribution": 0.271390, "percentage": 38.8}
]
```

---

## 7. Part C: Tier 2 Snapshot Experiment (Tags & Genome)

> [!WARNING]
> **TEMPORAL LEAKAGE NOTICE:** Tier 2 features (Tags and Tag Genome) incorporate MovieLens tags and genome relevance scores calculated over the entire dataset history through November 2019. This leaks future semantic information across chronological split points. These results are recorded solely as an exploratory ceiling and are labeled `snapshot_features=true`.

### Extended Tuning Grid Search (20,000 Users, Seed 42):
Evaluated across $w_{\text{tags}} \in \{1, 2, 4, 8\} \times w_{\text{genome}} \in \{0.5, 1, 2, 4\}$ with $w_{\text{t1}}=1.0$ (16 configurations):
- **Top Config:** `t1_1.0_tags_8_gen_0.5` with block weights $\{w_{\text{t1}}: 1.0, w_{\text{tags}}: 8.0, w_{\text{genome}}: 0.5\} \implies$ **NDCG@10 = 0.065859**, Precision = 0.047865, HitRate = 0.3171.
- Runner-up: `t1_1.0_tags_8_gen_1.0` $\implies$ NDCG@10 = 0.057451.
- Strong penalty with high genome weight ($w_{\text{genome}} \ge 2.0$ drops NDCG to $< 0.010$).

### Full Validation Metrics (All 94,303 Users):
- **NDCG@10:** **0.066616** [95% CI: 0.065755, 0.067354]
- **HitRate@10:** **0.316777** [0.313690, 0.319652]
- **Recall@10:** **0.057411** [0.056568, 0.058159]
- **Precision@10:** **0.048277** [0.047711, 0.048809]
- **MRR@10:** **0.141857** [0.139928, 0.143581]
- **Catalog Coverage:** **0.182107** (18.21%)
- **Genome Coverage Among Recommendations:** **99.7394%**
- **Mean Recommended Popularity:** **25,230.95** [25,175.9, 25,286.7]
- **Zero-Profile Users:** 7

### Paired Comparisons:
- **vs Tier 1:**
  - NDCG@10 Diff: **+0.063796** [95% CI: +0.062929, +0.064556] (Lift: **+2,262.71%**, $p < 0.05$).
  - T2 > T1: 31.35% | Equal: 67.30% | T2 < T1: 1.34%.
- **vs Popularity (Most Liked):**
  - NDCG@10 Diff: **+0.014696** [95% CI: +0.013927, +0.015484] (Lift: **+28.30%**, $p < 0.05$).
  - T2 > Pop: 22.93% | Equal: 62.05% | T2 < Pop: 15.02%.

---

## 8. Part D: Simulated Cold-Start Protocol v2 Evaluation (`cold_dev`)

Evaluated strictly on `cold_dev` (2,559 users; 50% deterministic split). `cold_final` (2,560 users) remains guarded and untouched for the final frozen evaluation.

### Protocol v2 Overview:
- **Revealed Onboarding:** First $K$ chronological positives ($r \ge 4.0$).
- **Relevant Target Set:** Next $W=20$ chronological positives in candidate catalog.
- **Two Candidate Variants:** (i) All candidates, (ii) Long-tail (catalog and relevant sets exclude the 200 most-rated train movies).
- **Old Reference:** All remaining positives.

### Empirical Results across $K \in \{3, 5, 10\}$:

#### Variant (i): All Candidates ($W=20$)
| Onboarding $K$ | Model | Evaluated Users | NDCG@10 [95% CI] | Precision@10 [95% CI] | Recall@10 [95% CI] | HitRate@10 [95% CI] | MRR@10 [95% CI] |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **$K = 3$** | Popularity Most Liked | 2,456 | 0.1956 [0.1885, 0.2025] | 0.1826 [0.1758, 0.1888] | 0.0913 [0.0879, 0.0944] | 0.7215 [0.7040, 0.7378] | 0.3900 [0.3757, 0.4038] |
| | Content Tier 1 | 2,456 | 0.0053 [0.0043, 0.0064] | 0.0049 [0.0040, 0.0059] | 0.0025 [0.0020, 0.0029] | 0.0448 [0.0370, 0.0529] | 0.0157 [0.0122, 0.0194] |
| | Content Tier 2 Snapshot | 2,456 | 0.1112 [0.1053, 0.1172] | 0.0981 [0.0926, 0.1037] | 0.0491 [0.0463, 0.0519] | 0.5147 [0.4947, 0.5342] | 0.2644 [0.2483, 0.2801] |
| **$K = 5$** | Popularity Most Liked | 2,420 | 0.1849 [0.1783, 0.1916] | 0.1731 [0.1666, 0.1795] | 0.0865 [0.0833, 0.0898] | 0.7004 [0.6814, 0.7178] | 0.3724 [0.3587, 0.3862] |
| | Content Tier 1 | 2,420 | 0.0069 [0.0056, 0.0083] | 0.0066 [0.0054, 0.0078] | 0.0033 [0.0027, 0.0039] | 0.0599 [0.0504, 0.0694] | 0.0200 [0.0162, 0.0242] |
| | Content Tier 2 Snapshot | 2,420 | 0.1361 [0.1294, 0.1423] | 0.1214 [0.1154, 0.1273] | 0.0607 [0.0577, 0.0637] | 0.6140 [0.5946, 0.6331] | 0.3183 [0.3013, 0.3347] |
| **$K = 10$** | Popularity Most Liked | 2,317 | 0.1635 [0.1565, 0.1704] | 0.1546 [0.1478, 0.1610] | 0.0773 [0.0739, 0.0805] | 0.6500 [0.6306, 0.6698] | 0.3276 [0.3134, 0.3418] |
| | Content Tier 1 | 2,317 | 0.0066 [0.0053, 0.0080] | 0.0070 [0.0057, 0.0084] | 0.0035 [0.0028, 0.0042] | 0.0647 [0.0544, 0.0751] | 0.0171 [0.0135, 0.0210] |
| | Content Tier 2 Snapshot | 2,317 | **0.1575** [0.1506, 0.1645] | 0.1430 [0.1364, 0.1492] | 0.0715 [0.0682, 0.0746] | **0.6802** [0.6612, 0.6992] | **0.3542** [0.3370, 0.3709] |

#### Variant (ii): Long-Tail (Top-200 Blockbusters Excluded)
| Onboarding $K$ | Model | Evaluated Users | NDCG@10 [95% CI] | Precision@10 [95% CI] | Recall@10 [95% CI] | HitRate@10 [95% CI] | MRR@10 [95% CI] |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **$K = 3$** | Popularity Most Liked | 2,434 | 0.0409 [0.0366, 0.0453] | 0.0305 [0.0275, 0.0336] | 0.0389 [0.0347, 0.0433] | 0.2416 [0.2243, 0.2588] | 0.0947 [0.0841, 0.1054] |
| | Content Tier 1 | 2,434 | 0.0028 [0.0020, 0.0037] | 0.0023 [0.0016, 0.0029] | 0.0028 [0.0020, 0.0036] | 0.0205 [0.0152, 0.0263] | 0.0066 [0.0046, 0.0090] |
| | Content Tier 2 Snapshot | 2,434 | 0.0367 [0.0330, 0.0404] | 0.0289 [0.0260, 0.0318] | 0.0319 [0.0287, 0.0353] | 0.2120 [0.1960, 0.2284] | 0.0873 [0.0779, 0.0967] |
| **$K = 5$** | Popularity Most Liked | 2,393 | 0.0411 [0.0369, 0.0458] | 0.0308 [0.0276, 0.0340] | 0.0397 [0.0354, 0.0441] | 0.2453 [0.2282, 0.2633] | 0.0940 [0.0838, 0.1054] |
| | Content Tier 1 | 2,393 | 0.0037 [0.0027, 0.0048] | 0.0034 [0.0025, 0.0044] | 0.0034 [0.0025, 0.0044] | 0.0305 [0.0238, 0.0376] | 0.0090 [0.0065, 0.0118] |
| | Content Tier 2 Snapshot | 2,393 | **0.0478** [0.0436, 0.0520] | **0.0370** [0.0339, 0.0402] | **0.0403** [0.0367, 0.0441] | **0.2641** [0.2461, 0.2817] | **0.1155** [0.1050, 0.1264] |
| **$K = 10$** | Popularity Most Liked | 2,280 | 0.0397 [0.0355, 0.0441] | 0.0315 [0.0282, 0.0349] | 0.0394 [0.0351, 0.0438] | 0.2500 [0.2325, 0.2680] | 0.0901 [0.0799, 0.1012] |
| | Content Tier 1 | 2,280 | 0.0046 [0.0035, 0.0058] | 0.0046 [0.0035, 0.0057] | 0.0041 [0.0031, 0.0052] | 0.0412 [0.0333, 0.0496] | 0.0111 [0.0083, 0.0142] |
| | Content Tier 2 Snapshot | 2,280 | **0.0616** [0.0569, 0.0664] | **0.0503** [0.0463, 0.0543] | **0.0522** [0.0479, 0.0567] | **0.3404** [0.3206, 0.3601] | **0.1449** [0.1332, 0.1572] |

#### Paired Comparisons vs Popularity (Content Tier 2 vs Popularity):
- **All Candidates:**
  - $K=3$: NDCG Diff = -0.084482 [-0.092781, -0.076395] (Lift: -43.18%, $p < 0.05$)
  - $K=5$: NDCG Diff = -0.048817 [-0.057398, -0.040243] (Lift: -26.41%, $p < 0.05$)
  - $K=10$: NDCG Diff = -0.006081 [-0.015243, +0.003265] (Lift: -3.72%, **statistically indistinguishable from zero**, $p > 0.05$); HitRate Diff = **+0.030211** (Lift: **+4.65%**, $p < 0.05$); MRR Diff = **+0.026601** (Lift: **+8.12%**, $p < 0.05$).
- **Long-Tail Discovery:**
  - $K=3$: NDCG Diff = -0.004258 [-0.009419, +0.000854] (Lift: -10.42%, statistically indistinguishable from zero)
  - $K=5$: NDCG Diff = **+0.006683** [+0.001646, +0.011880] (Lift: **+16.27%**, $p < 0.05$); HitRate Diff = **+0.018805** (Lift: **+7.67%**, $p < 0.05$)
  - $K=10$: NDCG Diff = **+0.021864** [+0.016335, +0.027473] (Lift: **+55.16%**, $p < 0.05$); HitRate Diff = **+0.090351** (Lift: **+36.16%**, $p < 0.05$); MRR Diff = **+0.054770** (Lift: **+60.82%**, $p < 0.05$).

### Interpretation & Product Takeaways:
1. **The Long-Tail Tipping Point:** While raw Popularity achieves higher hits on ubiquitous blockbusters when $K \le 5$ in unconstrained catalogs, it stalls completely in the long tail (NDCG ~0.040 across all $K$). Content Tier 2 with semantic tags and genome attributes decisively overtakes Popularity in the long tail at $K=5$ (+16.3% lift) and dominates at $K=10$ (+55.2% NDCG lift, +36.2% Hit Rate lift).
2. **Catalog Bias vs Genuine Personalization:** Popularity's apparent high performance in unrestricted catalogs is a byproduct of head-item concentration. In real production onboarding, surfacing universally known movies provides low serendipity. Content models successfully unlock non-head discovery.
3. **Explicit Non-Comparability Notice:** Cold-start tables are strictly **NOT comparable** with the main validation tables because the relevant set in Protocol v2 is defined as the next $W=20$ chronological positives rather than the entire validation split history.

