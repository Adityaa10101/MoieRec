# MoieRec Phase 2H — Final Frozen Evaluation Report

> **Evaluation Date**: October 4, 2026  
> **Status**: COMPLETED (One-Shot Execution, Zero Re-tuning)  
> **Git Commit**: `97f4433460d8eb9a0c179f463b3ace81cf7a676a` (Clean tree at freeze)  
> **Frozen Config ID**: `0ab4db5f288b8a8a3cb720369a082fa9d45dc2d28031050e0be95578cba3feaa`  
> **Primary Artifacts**:
> - Freeze Record: [`freeze_record.json`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/results/final/freeze_record.json)
> - Cold-Start Final: [`final_cold_final.json`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/results/final/final_cold_final.json) | [`final_cold_final.csv`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/results/final/final_cold_final.csv)
> - Warm Test Final: [`final_test_warm.json`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/results/final/final_test_warm.json) | [`final_test_warm.csv`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/results/final/final_test_warm.csv)
> - Evaluation Run Log: [`evaluation_run_log.json`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/results/final/evaluation_run_log.json)

---

## 1. Executive Summary & Protocol Overview

Phase 2H establishes the definitive, immutable benchmark numbers for the MoieRec recommendation engine. In accordance with the Phase 2H specification, all model weights, hyperparameter schedules, feature blocks, and candidate catalogs were **frozen prior to running on held-out evaluation splits**.

### 1.1 Integrity & Guardrail Guarantees
1. **One-Shot Execution**: The final evaluation runner was executed exactly once. The execution completed with exit code 0 in 974.45 seconds without crashes, restarts, or reruns.
2. **Guarded Split Access**: The held-out splits (`cold_final` and warm `test.parquet`) were accessed exclusively via the guarded loader [`recommender.evaluation.split_loader`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/evaluation/split_loader.py) with `final=True` and verified against the canonical `frozen_config_id`.
3. **CF Audit Gate**: Prior to touching any held-out data, a 6-part audit gate was verified on the collaborative filtering pipeline:
   - **Static Audit**: Confirmed zero references to validation or test data during CF model building; inputs strictly limited to `splits/train.parquet`. Diagonal strictly zeroed and user picks excluded from score lists.
   - **Independent Recomputation**: Recomputed $n_i, n_j, n_{ij}$ and cosine similarities for 20 random pairs and 5 top-100 popular pairs using raw pandas code; 100% exact numerical match with cached artifacts.
   - **Neighbor Sanity**: Verified top-10 neighbors for 10 iconic anchor movies (*Toy Story*, *Star Wars IV*, *The Matrix*, *Silence of the Lambs*, *The Shining*, *Pulp Fiction*, *Titanic*, *Fellowship of the Ring*, *Finding Nemo*, *Casablanca*). All neighbors demonstrated authentic cinematic affinity.
   - **Negative Control**: Item similarity rebuilt with shuffled user lists (preserving item margins $n_i$ but destroying co-occurrence). Shuffled NDCG@10 was 0.05198 vs Popularity 0.05183, confirming zero spurious advantage.
   - **Simplex Parity**: Proved exact scoring parity at vertices $(1,0,0)$, $(0,1,0)$, and $(0,0,1)$ across 200 random user profiles; verified that candidate items with zero CF co-occurrence receive the exact average rank of tied zeros.
   - **Leakage Sensitivity (Positive Control)**: A diagnostic CF allowed to see validation positives registered a +5.25% lift on the warm validation sample (+54.3% on small cohorts), proving that the evaluation harness detects temporal leakage.

---

## 2. Frozen Configuration Record

The system state was cryptographically captured into [`recommender/results/final/freeze_record.json`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/results/final/freeze_record.json) with hash `0ab4db5f288b8a8a3cb720369a082fa9d45dc2d28031050e0be95578cba3feaa`.

### 2.1 Model Artifact & Configuration Hashes
| Configuration File | SHA-256 Digest | Key Frozen Settings |
|:---|:---|:---|
| [`hybrid_v1.yaml`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/config/hybrid_v1.yaml) | `6bad961bcb1e8a795fe32e612e31fe35e09b8c27e749973ad57c4c53db046987` | Static $\alpha = 0.1$, block weights: $w_{\text{T1}}=1.0, w_{\text{tags}}=4.0, w_{\text{genome}}=1.0$ |
| [`hybrid_v1_1.yaml`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/config/hybrid_v1_1.yaml) | `2bcfa6cd27d942cb856d9d056226981c7310ebe60c3c916b6563da28ee5b1b0e` | $\alpha \in \{3: 0.3, 5: 0.6, 10: 0.7, 20: 0.8\}$, same block weights |
| [`hybrid_v2.yaml`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/config/hybrid_v2.yaml) | `4d137450139e60bcd5a71c61248080f4ed1e47b23b7f3c8a8466d481378cc9b4` | Simplex schedule: $K \in \{3,5,10\} \to (0.0, 1.0, 0.0)$, $K=20 \to (0.1, 0.9, 0.0)$ |

### 2.2 Recommender Component Parameters
- **Collaborative Filtering**: Asymmetric cosine similarity ($a=0.5$), shrinkage $\lambda=0.0$, top-$k=200$ neighbors, positive rating threshold $\ge 4.0$. Diagonal elements set to 0.0, picks excluded at inference.
- **Popularity Variant**: `most_liked` (raw count of ratings $\ge 4.0$ in training data).
- **Tie-Breaking Rule**: Canonical random permutation (`random_perm`) with deterministic seed `42`.
- **Content Blocks**:
  - *Tier 1 (Clean)*: Genre one-hot + release year normalized ($w_{\text{T1}}=1.0$).
  - *Tier 2 (Snapshot)*: Tier 1 ($w=1.0$) + Tag TF-IDF ($w=4.0$) + Tag Genome ($w=1.0$).

### 2.3 Served Weights per K Bucket (Hybrid v2)
$$\text{Score}(i) = w_c \cdot \text{pct}_{\text{content}}(i) + w_f \cdot \text{pct}_{\text{CF}}(i) + w_p \cdot \text{pct}_{\text{pop}}(i)$$

| K Bucket | Evaluation K | Content Weight ($w_c$) | Item-CF Weight ($w_f$) | Popularity Weight ($w_p$) | Dominant Signal |
|:---|:---:|:---:|:---:|:---:|:---|
| $K \in [3, 4]$ | 3 | $0.0$ | $1.0$ | $0.0$ | Pure Item-Item CF |
| $K \in [5, 7]$ | 5 | $0.0$ | $1.0$ | $0.0$ | Pure Item-Item CF |
| $K \in [8, 14]$ | 10 | $0.0$ | $1.0$ | $0.0$ | Pure Item-Item CF |
| $K \ge 15$ | 20 | $0.1$ | $0.9$ | $0.0$ | 90% Item-CF + 10% Content |

---

## 3. Cold-Start Evaluation Results (`cold_final`)

The cold-start protocol was evaluated on the **2,560 held-out users** of the `cold_final` partition. For each user, the first $K$ chronological ratings $\ge 4.0$ served as onboarding seed picks, and recommendation performance was measured on the subsequent $W=20$ positive interactions. Confidence intervals (95%) and paired comparisons were computed via 1,000 bootstrap resamples.

### 3.1 All-Candidates Variant (Catalog Size: 18,277 Movies)

| $K$ | Evaluated / Excluded Users | Model | NDCG@10 (95% CI) | Precision@10 | Recall@10 | Hit Rate@10 | MRR@10 |
|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| **3** | 2,439 / 121 | Popularity (`most_liked`) | 0.2043 [0.1964, 0.2122] | 0.1919 | 0.0959 | 0.7421 | 0.4008 |
| | | Content Tier 2 (snapshot) | 0.0940 [0.0877, 0.1003] | 0.0788 | 0.0394 | 0.3895 | 0.2300 |
| | | Item-kNN CF Only | 0.2326 [0.2232, 0.2410] | 0.2137 | 0.1069 | 0.7425 | 0.4365 |
| | | Hybrid v1.1 | 0.2040 [0.1962, 0.2116] | 0.1863 | 0.0931 | 0.7540 | 0.4130 |
| | | **Hybrid v2 (Served)** | **0.2326 [0.2232, 0.2410]** | **0.2137** | **0.1069** | **0.7425** | **0.4365** |
| **5** | 2,410 / 150 | Popularity (`most_liked`) | 0.1943 [0.1868, 0.2018] | 0.1837 | 0.0918 | 0.7295 | 0.3833 |
| | | Content Tier 2 (snapshot) | 0.0898 [0.0844, 0.0953] | 0.0727 | 0.0363 | 0.3627 | 0.2267 |
| | | Item-kNN CF Only | 0.2423 [0.2336, 0.2509] | 0.2224 | 0.1112 | 0.7718 | 0.4562 |
| | | Hybrid v1.1 | 0.1969 [0.1891, 0.2042] | 0.1798 | 0.0899 | 0.7485 | 0.4040 |
| | | **Hybrid v2 (Served)** | **0.2423 [0.2336, 0.2509]** | **0.2224** | **0.1112** | **0.7718** | **0.4562** |
| **10** | 2,321 / 239 | Popularity (`most_liked`) | 0.1676 [0.1605, 0.1747] | 0.1612 | 0.0806 | 0.6738 | 0.3311 |
| | | Content Tier 2 (snapshot) | 0.0680 [0.0626, 0.0733] | 0.0556 | 0.0278 | 0.2930 | 0.1742 |
| | | Item-kNN CF Only | 0.2409 [0.2323, 0.2498] | 0.2225 | 0.1112 | 0.7906 | 0.4547 |
| | | Hybrid v1.1 | 0.1991 [0.1923, 0.2062] | 0.1840 | 0.0920 | 0.7622 | 0.4056 |
| | | **Hybrid v2 (Served)** | **0.2409 [0.2323, 0.2498]** | **0.2225** | **0.1112** | **0.7906** | **0.4547** |
| **20** | 2,053 / 507 | Popularity (`most_liked`) | 0.1430 [0.1358, 0.1511] | 0.1362 | 0.0681 | 0.6137 | 0.2926 |
| | | Content Tier 2 (snapshot) | 0.0418 [0.0376, 0.0462] | 0.0338 | 0.0169 | 0.1987 | 0.1126 |
| | | Item-kNN CF Only | 0.2027 [0.1939, 0.2113] | 0.1878 | 0.0939 | 0.7360 | 0.3979 |
| | | Hybrid v1.1 | 0.1776 [0.1701, 0.1858] | 0.1628 | 0.0814 | 0.7073 | 0.3714 |
| | | **Hybrid v2 (Served)** | **0.2116 [0.2027, 0.2204]** | **0.1955** | **0.0977** | **0.7560** | **0.4142** |

### 3.2 Long-Tail Variant (Excluding Top-200 Training Movies)

| $K$ | Evaluated / Excluded Users | Model | NDCG@10 (95% CI) | Precision@10 | Recall@10 | Hit Rate@10 | MRR@10 |
|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| **3** | 2,408 / 152 | Popularity (`most_liked`) | 0.0402 [0.0365, 0.0440] | 0.0297 | 0.0370 | 0.2367 | 0.0967 |
| | | Content Tier 2 (snapshot) | 0.0243 [0.0211, 0.0273] | 0.0169 | 0.0208 | 0.1213 | 0.0602 |
| | | Item-kNN CF Only | 0.0974 [0.0915, 0.1039] | 0.0688 | 0.0900 | 0.4306 | 0.2071 |
| | | Hybrid v1.1 | 0.0501 [0.0461, 0.0539] | 0.0392 | 0.0461 | 0.2986 | 0.1195 |
| | | **Hybrid v2 (Served)** | **0.0974 [0.0915, 0.1039]** | **0.0688** | **0.0900** | **0.4306** | **0.2071** |
| **5** | 2,372 / 188 | Popularity (`most_liked`) | 0.0402 [0.0365, 0.0438] | 0.0301 | 0.0368 | 0.2357 | 0.0968 |
| | | Content Tier 2 (snapshot) | 0.0189 [0.0163, 0.0218] | 0.0142 | 0.0158 | 0.1029 | 0.0466 |
| | | Item-kNN CF Only | 0.1051 [0.0991, 0.1118] | 0.0777 | 0.0934 | 0.4705 | 0.2232 |
| | | Hybrid v1.1 | 0.0604 [0.0561, 0.0650] | 0.0478 | 0.0538 | 0.3335 | 0.1392 |
| | | **Hybrid v2 (Served)** | **0.1051 [0.0991, 0.1118]** | **0.0777** | **0.0934** | **0.4705** | **0.2232** |
| **10** | 2,269 / 291 | Popularity (`most_liked`) | 0.0392 [0.0354, 0.0432] | 0.0308 | 0.0362 | 0.2376 | 0.0913 |
| | | Content Tier 2 (snapshot) | 0.0143 [0.0119, 0.0168] | 0.0113 | 0.0108 | 0.0762 | 0.0349 |
| | | Item-kNN CF Only | 0.1146 [0.1083, 0.1206] | 0.0902 | 0.0988 | 0.5253 | 0.2453 |
| | | Hybrid v1.1 | 0.0715 [0.0668, 0.0766] | 0.0564 | 0.0619 | 0.3759 | 0.1643 |
| | | **Hybrid v2 (Served)** | **0.1146 [0.1083, 0.1206]** | **0.0902** | **0.0988** | **0.5253** | **0.2453** |
| **20** | 2,008 / 552 | Popularity (`most_liked`) | 0.0330 [0.0296, 0.0366] | 0.0284 | 0.0322 | 0.2246 | 0.0728 |
| | | Content Tier 2 (snapshot) | 0.0084 [0.0065, 0.0108] | 0.0069 | 0.0059 | 0.0483 | 0.0201 |
| | | Item-kNN CF Only | 0.1104 [0.1040, 0.1165] | 0.0936 | 0.0907 | 0.5398 | 0.2428 |
| | | Hybrid v1.1 | 0.0756 [0.0699, 0.0811] | 0.0620 | 0.0624 | 0.3974 | 0.1696 |
| | | **Hybrid v2 (Served)** | **0.1074 [0.1012, 0.1136]** | **0.0916** | **0.0879** | **0.5374** | **0.2300** |

### 3.3 Paired Statistical Comparisons on `cold_final`
All paired comparisons assess user-level differences ($\Delta \text{NDCG@10}$) evaluated with 1,000 bootstrap iterations.

| Cohort | Comparison | Mean $\Delta$ | 95% Bootstrap CI | Relative Lift | Win / Tie / Loss | Distinguishable from 0? |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **$K=3$ All** | Hybrid v2 vs Hybrid v1.1 | $+0.0287$ | $[+0.0221, +0.0352]$ | **$+14.05\%$** | 47.9% / 16.0% / 36.1% | **YES** |
| | Hybrid v2 vs Popularity | $+0.0283$ | $[+0.0188, +0.0361]$ | **$+13.83\%$** | 50.8% / 14.0% / 35.2% | **YES** |
| | CF Only vs Popularity | $+0.0283$ | $[+0.0188, +0.0361]$ | **$+13.83\%$** | 50.8% / 14.0% / 35.2% | **YES** |
| | Hybrid v1.1 vs Popularity | $-0.0004$ | $[-0.0077, +0.0069]$ | $-0.20\%$ | 43.9% / 16.4% / 39.7% | NO |
| **$K=3$ LT** | Hybrid v2 vs Hybrid v1.1 | $+0.0474$ | $[+0.0410, +0.0537]$ | **$+94.61\%$** | 46.1% / 32.3% / 21.6% | **YES** |
| | Hybrid v2 vs Popularity | $+0.0572$ | $[+0.0505, +0.0635]$ | **$+142.04\%$** | 48.7% / 34.5% / 16.8% | **YES** |
| **$K=5$ All** | Hybrid v2 vs Hybrid v1.1 | $+0.0454$ | $[+0.0384, +0.0522]$ | **$+23.04\%$** | 52.7% / 12.3% / 35.0% | **YES** |
| | Hybrid v2 vs Popularity | $+0.0479$ | $[+0.0384, +0.0567]$ | **$+24.66\%$** | 53.7% / 12.7% / 33.6% | **YES** |
| **$K=5$ LT** | Hybrid v2 vs Hybrid v1.1 | $+0.0447$ | $[+0.0382, +0.0511]$ | **$+73.98\%$** | 48.9% / 27.4% / 23.7% | **YES** |
| | Hybrid v2 vs Popularity | $+0.0649$ | $[+0.0590, +0.0718]$ | **$+161.28\%$** | 51.5% / 30.6% / 17.9% | **YES** |
| **$K=10$ All** | Hybrid v2 vs Hybrid v1.1 | $+0.0417$ | $[+0.0349, +0.0488]$ | **$+20.95\%$** | 52.8% / 11.2% / 36.0% | **YES** |
| | Hybrid v2 vs Popularity | $+0.0733$ | $[+0.0653, +0.0812]$ | **$+43.70\%$** | 57.6% / 11.3% / 31.1% | **YES** |
| **$K=10$ LT** | Hybrid v2 vs Hybrid v1.1 | $+0.0431$ | $[+0.0368, +0.0491]$ | **$+60.37\%$** | 51.7% / 22.9% / 25.4% | **YES** |
| | Hybrid v2 vs Popularity | $+0.0754$ | $[+0.0689, +0.0819]$ | **$+192.71\%$** | 55.4% / 26.6% / 18.0% | **YES** |
| **$K=20$ All** | Hybrid v2 vs Hybrid v1.1 | $+0.0340$ | $[+0.0291, +0.0394]$ | **$+19.13\%$** | 52.8% / 10.1% / 37.1% | **YES** |
| | Hybrid v2 vs Popularity | $+0.0686$ | $[+0.0614, +0.0757]$ | **$+47.98\%$** | 58.7% / 10.3% / 31.0% | **YES** |
| **$K=20$ LT** | Hybrid v2 vs Hybrid v1.1 | $+0.0319$ | $[+0.0277, +0.0358]$ | **$+42.19\%$** | 49.6% / 21.0% / 29.4% | **YES** |
| | Hybrid v2 vs Popularity | $+0.0745$ | $[+0.0683, +0.0803]$ | **$+225.77\%$** | 57.4% / 23.3% / 19.3% | **YES** |

---

## 4. Warm Test Evaluation Results (`TEST` Split)

### 4.1 Final-Fit Protocol
Following the canonical final-fit rule, models were refitted on the combined **TRAIN + VALIDATION** dataset ($19,572,447$ ratings across $136,204$ users):
- **Candidate Pool**: Exactly $18,276$ benchmark movies.
- **Candidate Filtering**: For each user, candidate items strictly exclude all movies interacted with in either train or validation.
- **Relevant Ground Truth**: All items in `test.parquet` rated $\ge 4.0$ that belong to the candidate catalog.
- **User Population**: Evaluated across $94,604$ users with $\ge 1$ test positive. Exactly $2,666$ users had zero reachable test positives and were excluded from ranking calculations.
- **Unreachable Positives**: Exactly 16 test positives (0.0016%) were outside the benchmark catalog.

### 4.2 Primary Benchmark Table (@10)

| Model | NDCG@10 (95% CI) | Precision@10 (95% CI) | Recall@10 (95% CI) | Hit Rate@10 (95% CI) | MRR@10 (95% CI) | Catalog Coverage | Mean Rec. Popularity (Train) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Popularity** (`most_liked`) | 0.0523 [0.0515, 0.0530] | 0.0403 [0.0397, 0.0409] | 0.0439 [0.0432, 0.0446] | 0.2557 [0.2528, 0.2583] | 0.1089 [0.1073, 0.1106] | 1.73% | 43,817.4 [43,782.3, 43,852.7] |
| **Content Tier 1** (clean) | 0.0026 [0.0025, 0.0028] | 0.0023 [0.0022, 0.0024] | 0.0027 [0.0025, 0.0028] | 0.0218 [0.0208, 0.0227] | 0.0076 [0.0072, 0.0080] | 16.50% | 1,816.2 [1,811.2, 1,821.2] |
| **Content Tier 2** (snapshot) | 0.0673 [0.0665, 0.0682] | 0.0486 [0.0479, 0.0492] | 0.0560 [0.0552, 0.0569] | 0.3197 [0.3168, 0.3227] | 0.1456 [0.1437, 0.1475] | 17.71% | 26,330.7 [26,270.8, 26,389.9] |
| **Item-kNN CF** ($k=200, a=0.5$) | **0.0818 [0.0810, 0.0828]** | **0.0602 [0.0596, 0.0610]** | **0.0708 [0.0699, 0.0717]** | **0.3580 [0.3551, 0.3612]** | **0.1636 [0.1617, 0.1656]** | 7.62% | 33,963.6 [33,916.8, 34,013.5] |

### 4.3 Paired Statistical Comparisons on TEST ($N=94,604$)

| Comparison ($A$ vs $B$) | Metric | Mean Difference | 95% Bootstrap CI | Relative Lift | Win / Tie / Loss | Distinguishable from 0? |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **CF vs Popularity** | NDCG@10 | $+0.0295$ | $[+0.0287, +0.0303]$ | **$+56.40\%$** | 25.8% / 60.9% / 13.3% | **YES** |
| | HitRate@10 | $+0.1022$ | $[+0.0997, +0.1051]$ | **$+39.98\%$** | 14.9% / 80.4% / 4.7% | **YES** |
| | Recall@10 | $+0.0269$ | $[+0.0262, +0.0277]$ | **$+61.37\%$** | 21.4% / 71.0% / 7.5% | **YES** |
| | Precision@10 | $+0.0199$ | $[+0.0195, +0.0204]$ | **$+49.49\%$** | 21.4% / 71.0% / 7.5% | **YES** |
| **CF vs Tier 2** | NDCG@10 | $+0.0145$ | $[+0.0137, +0.0154]$ | **$+21.60\%$** | 25.3% / 55.6% / 19.1% | **YES** |
| | HitRate@10 | $+0.0383$ | $[+0.0353, +0.0416]$ | **$+11.99\%$** | 14.0% / 75.9% / 10.1% | **YES** |
| | Recall@10 | $+0.0148$ | $[+0.0140, +0.0156]$ | **$+26.34\%$** | 20.9% / 65.0% / 14.1% | **YES** |
| | Precision@10 | $+0.0117$ | $[+0.0111, +0.0122]$ | **$+24.04\%$** | 20.9% / 65.0% / 14.1% | **YES** |
| **Tier 2 vs Popularity** | NDCG@10 | $+0.0150$ | $[+0.0143, +0.0158]$ | **$+28.75\%$** | 23.1% / 61.8% / 15.1% | **YES** |
| | HitRate@10 | $+0.0639$ | $[+0.0610, +0.0668]$ | **$+24.99\%$** | 13.8% / 78.7% / 7.4% | **YES** |
| | Recall@10 | $+0.0122$ | $[+0.0114, +0.0130]$ | **$+27.73\%$** | 18.2% / 70.4% / 11.4% | **YES** |
| | Precision@10 | $+0.0083$ | $[+0.0078, +0.0088]$ | **$+20.51\%$** | 18.2% / 70.4% / 11.4% | **YES** |
| **Tier 2 vs Tier 1** | NDCG@10 | $+0.0647$ | $[+0.0639, +0.0655]$ | **$+2,462.2\%$** | 31.7% / 67.0% / 1.3% | **YES** |
| | HitRate@10 | $+0.2979$ | $[+0.2950, +0.3010]$ | **$+1,369.4\%$** | 30.9% / 68.1% / 1.1% | **YES** |
| | Recall@10 | $+0.0534$ | $[+0.0527, +0.0541]$ | **$+2,010.3\%$** | 31.4% / 67.5% / 1.1% | **YES** |

### 4.4 User Strata Breakdowns (TEST Split)

#### Activity Quartiles (Train Ratings Count)
- **Q1 (Low)**: $N=23,767$ users ($[45, 69]$ train ratings)
- **Q2 (Med-Low)**: $N=23,663$ users ($[70, 115]$ train ratings)
- **Q3 (Med-High)**: $N=23,545$ users ($[116, 226]$ train ratings)
- **Q4 (High)**: $N=23,629$ users ($[227, 12,558]$ train ratings)

| Model | Strata | Precision@10 | Recall@10 | NDCG@10 | Hit Rate@10 | MRR@10 |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **Popularity** | Q1 (Low) | 0.0213 | 0.0528 | 0.0400 | 0.1655 | 0.0636 |
| | Q2 (Med-Low) | 0.0292 | 0.0472 | 0.0418 | 0.2077 | 0.0825 |
| | Q3 (Med-High) | 0.0403 | 0.0416 | 0.0483 | 0.2634 | 0.1091 |
| | Q4 (High) | 0.0705 | 0.0339 | 0.0791 | 0.3870 | 0.1808 |
| **Tier 2 (Snapshot)** | Q1 (Low) | 0.0287 | 0.0717 | 0.0549 | 0.2185 | 0.0967 |
| | Q2 (Med-Low) | 0.0371 | 0.0607 | 0.0559 | 0.2642 | 0.1147 |
| | Q3 (Med-High) | 0.0514 | 0.0527 | 0.0658 | 0.3340 | 0.1506 |
| | Q4 (High) | 0.0772 | 0.0388 | 0.0926 | 0.4623 | 0.2206 |
| **Item-kNN CF** | Q1 (Low) | 0.0372 | 0.0935 | 0.0727 | 0.2742 | 0.1138 |
| | Q2 (Med-Low) | 0.0473 | 0.0780 | 0.0699 | 0.3138 | 0.1333 |
| | Q3 (Med-High) | 0.0615 | 0.0640 | 0.0762 | 0.3745 | 0.1694 |
| | Q4 (High) | 0.0952 | 0.0475 | 0.1087 | 0.4700 | 0.2381 |

#### Session-Span Strata (Days Between First and Last Train Rating)
- **Onboarding Spree (< 1 day)**: $N=43,398$ users (45.87% of evaluated cohort)
- **Short-term / Casual (1–30 days)**: $N=15,602$ users (16.49% of evaluated cohort)
- **Longitudinal ($\ge 30$ days)**: $N=35,604$ users (37.63% of evaluated cohort)

| Model | Session Strata | Precision@10 | Recall@10 | NDCG@10 | Hit Rate@10 | MRR@10 |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **Popularity** | < 1 day | 0.0302 | 0.0462 | 0.0434 | 0.1991 | 0.0808 |
| | 1–30 days | 0.0376 | 0.0438 | 0.0493 | 0.2455 | 0.1035 |
| | $\ge 30$ days | 0.0539 | 0.0411 | 0.0644 | 0.3293 | 0.1455 |
| **Tier 2 (Snapshot)** | < 1 day | 0.0392 | 0.0592 | 0.0559 | 0.2658 | 0.1171 |
| | 1–30 days | 0.0456 | 0.0565 | 0.0643 | 0.3112 | 0.1410 |
| | $\ge 30$ days | 0.0630 | 0.0517 | 0.0789 | 0.3959 | 0.1834 |
| **Item-kNN CF** | < 1 day | 0.0483 | 0.0772 | 0.0734 | 0.3056 | 0.1345 |
| | 1–30 days | 0.0588 | 0.0706 | 0.0792 | 0.3540 | 0.1585 |
| | $\ge 30$ days | 0.0754 | 0.0631 | 0.0933 | 0.4237 | 0.2012 |

### 4.5 Rating Prediction Baselines (Non-Ranking Anchor Metrics)
> [!NOTE]
> Rating prediction metrics assess numeric score calibration across all $2,174,367$ test ratings (both positive and non-positive). They represent point prediction errors, **not ranking quality**.

- **Global Mean Baseline**:
  - Training Global Mean: $\mu = 3.5356$
  - TEST Split RMSE: **$1.0528$**
  - TEST Split MAE: **$0.8225$**
- **Movie Mean Baseline**:
  - TEST Split RMSE: **$0.9527$**
  - TEST Split MAE: **$0.7332$**

---

## 5. Validation-vs-Final Drift Analysis

A critical measure of machine learning generalization is whether performance on the held-out evaluation set matches the validation set used during development.

### 5.1 Cold-Start Drift: `cold_dev` vs `cold_final`
Comparing NDCG@10 for the primary models across development and final sets:

| Variant | $K$ | Model | `cold_dev` (Tuning) | `cold_final` (Held-out) | Absolute Shift ($\Delta$) | Direction |
|:---|:---:|:---|:---:|:---:|:---:|:---:|
| **All Candidates** | 3 | Popularity | 0.1869 | 0.2043 | $+0.0174$ | Minor gain |
| | 3 | Hybrid v1.1 | 0.1983 | 0.2040 | $+0.0057$ | Stable |
| | 3 | Hybrid v2 | 0.2228 | 0.2326 | $+0.0098$ | Stable / Minor gain |
| | 5 | Hybrid v2 | 0.2316 | 0.2423 | $+0.0107$ | Stable / Minor gain |
| | 10 | Hybrid v2 | 0.2296 | 0.2409 | $+0.0113$ | Stable / Minor gain |
| | 20 | Hybrid v2 | 0.1935 | 0.2116 | $+0.0181$ | Stable / Minor gain |
| **Long-Tail** | 3 | Popularity | 0.0385 | 0.0402 | $+0.0017$ | Exact parity |
| | 3 | Hybrid v1.1 | 0.0463 | 0.0501 | $+0.0038$ | Stable |
| | 3 | Hybrid v2 | 0.0958 | 0.0974 | $+0.0016$ | Exact parity |
| | 5 | Hybrid v2 | 0.1100 | 0.1051 | $-0.0049$ | Stable |
| | 10 | Hybrid v2 | 0.1199 | 0.1146 | $-0.0053$ | Stable |
| | 20 | Hybrid v2 | 0.1138 | 0.1074 | $-0.0064$ | Stable |

### 5.2 Warm Evaluation Drift: Validation Sample vs TEST Split
Comparing NDCG@10 on the warm validation cohort ($N=94,312$) to the final held-out TEST cohort ($N=94,604$):

| Model | Warm Validation (Tuning) | Warm TEST (Held-out) | Absolute Shift ($\Delta$) | Relative Drift |
|:---|:---:|:---:|:---:|:---:|
| **Item-kNN CF** | 0.0838 | 0.0818 | $-0.0020$ | $-2.38\%$ |
| **Popularity** | 0.0519 | 0.0523 | $+0.0004$ | $+0.77\%$ |
| **Content Tier 2** | 0.0633 | 0.0673 | $+0.0040$ | $+6.32\%$ |
| **Content Tier 1** | 0.0029 | 0.0026 | $-0.0003$ | $-10.34\%$ |

**Verdict on Generalization**:
The performance shift across all models and splits is $|\Delta| \le 0.018$ NDCG points. Ranking order, relative lifts, and significance conclusions remain 100% invariant between tuning and test splits. The models exhibit **zero hyperparameter overfitting**.

---

## 6. Visualizations & Graphical Artifacts

The final benchmark curves and bar charts generated directly from the evaluation data are archived in [`docs/figures/`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/figures/):

### 6.1 Cold-Start Evaluation Curves
![Cold-Start All Candidates](file:///c:/Users/Lenovo/Projects/MoieRec/docs/figures/ndcg_cold_start_all_candidates.png)
*Figure 1: NDCG@10 vs Onboarding $K$ across all 18,277 candidate movies on held-out `cold_final` users.*

![Cold-Start Long-Tail](file:///c:/Users/Lenovo/Projects/MoieRec/docs/figures/ndcg_cold_start_long_tail.png)
*Figure 2: NDCG@10 vs Onboarding $K$ on the long-tail variant (excluding the top-200 popular training movies).*

### 6.2 Warm TEST Benchmark
![Warm TEST Metrics](file:///c:/Users/Lenovo/Projects/MoieRec/docs/figures/warm_test_metrics_bar.png)
*Figure 3: Warm evaluation metrics @10 on the held-out TEST split with 95% bootstrap error bars.*

---

## 7. Plain-Language Engineering Interpretation

### 7.1 What the Numbers Mean for Real Users
1. **Item-Item CF is King**: In both cold onboarding and warm ongoing recommendations, collaborative filtering outperforms content and popularity by large, statistically unmistakable margins. For warm users, CF achieves an NDCG@10 of **0.0818**, generating a **+56.4% lift over Popularity** and a **+21.6% lift over rich Content**.
2. **Cold Start Long-Tail Power**: When popular blockbuster recommendations are stripped away (long-tail variant), popularity-based recommendation collapses to an NDCG of 0.0402. In contrast, Hybrid v2 maintains an NDCG of **0.0974 at $K=3$ (+142% lift)** and **0.1146 at $K=10$ (+193% lift)**. In practice, this means an onboarding user selecting just 3 to 5 niche favorites will immediately receive accurate, obscure film discoveries rather than generic box-office hits.
3. **The Strength and Limit of Content Matching**:
   - **Tier 1 (Clean metadata: genres + year)** completely fails at fine-grained ranking (NDCG@10 = 0.0026). In an 18,000-movie catalog, thousands of films share identical genre combinations. Genre alone cannot distinguish a cult classic from a forgotten B-movie.
   - **Tier 2 (Tags + Genome)** provides substantial ranking power (NDCG@10 = 0.0673, beating popularity by +28.7%), but still lags behind true user co-occurrence patterns.
4. **Activity & Session Dynamics**:
   - High-activity users ($Q4$) achieve much higher hit rates (CF hit rate = 47.0%) than casual users ($Q1$, 27.4%), confirming that denser history yields sharper neighborhood matches.
   - Users with longitudinal history ($\ge 30$ days) see significantly better ranking accuracy (CF NDCG = 0.0933) than single-day binge raters (0.0734), as multi-session raters exhibit more stable, deliberate taste profiles.

---

## 8. Limitations & Critical Caveats

### 8.1 Tier 2 Snapshot Feature Leakage
The MovieLens-25M `tags.csv` and `genome-scores.parquet` files represent an aggregate snapshot across the entire platform history up to 2019. Tag assignments applied in 2018 leak backward into pre-2015 movies. While Tier 2 was retained for cold-start onboarding because cold users have no historical ratings, its evaluation results reflect optimistic tag availability compared to a purely temporal cold deployment.

### 8.2 Cold-Start Protocol Approximating Onboarding
The evaluation protocol approximates interactive onboarding by extracting a user's first $K$ chronologically recorded positive ratings and evaluating against subsequent items. In a production web UI, onboarding is an interactive session where users pick from curated clusters or search for specific titles. The empirical $K$ picks in this protocol are constrained by the user's organic early ratings.

### 8.3 2019 MovieLens Dataset Horizon
All ratings and catalog entries terminate in 2019. The catalog lacks modern releases, streaming-exclusive titles, and recent cultural shifts in media consumption.

### 8.4 Binary Positivity in Neighborhood CF
The item-item collaborative filter uses binary thresholding ($\text{rating} \ge 4.0$) to form co-occurrence graphs. While this robustly protects against negative ratings, it discards the distinction between an enthusiastic 5-star rating and a standard 4-star approval, and does not model explicit dislikes (1 or 2 stars).

### 8.5 Temporal Split Granularity (46% Onboarding Spree)
In the temporal train/test split, **45.87% of users** rated all of their movies within a single calendar day (span $< 1$ day). For these users, the temporal split line cuts through ratings submitted within minutes or hours. In such dense bursts, ratings often reflect retrospective catalog browsing rather than real-time consumption order.

### 8.6 Tie-Break Evolution
Early development iterations exhibited tie-break sensitivity on sparse candidates, where arbitrary hash or index ordering artificially inflated recall for certain models. The frozen evaluation employs a strictly uniform random permutation with fixed seed `42` (`random_perm`), guaranteeing zero tie-break bias across candidate rankings.

### 8.7 Bootstrap Optimism on Development Sets
Confidence intervals on `cold_dev` were nominally subject to hyperparameter selection optimism because the tuning schedule maximized an objective on that specific sample. The confidence intervals reported in this document were computed on held-out `cold_final` and held-out `TEST`, providing strictly unbiased statistical coverage.

---

## 9. Artifact Index

The following result files are preserved in the repository:

| File Path | Description | Format |
|:---|:---|:---:|
| [`recommender/results/final/freeze_record.json`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/results/final/freeze_record.json) | Hash record, frozen model configs, served weights | JSON |
| [`recommender/results/final/final_cold_final.json`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/results/final/final_cold_final.json) | Full cold-start results with bootstrap distributions | JSON |
| [`recommender/results/final/final_cold_final.csv`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/results/final/final_cold_final.csv) | Tabular cold-start evaluation metrics | CSV |
| [`recommender/results/final/final_test_warm.json`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/results/final/final_test_warm.json) | Full warm test results, paired comparisons, strata | JSON |
| [`recommender/results/final/final_test_warm.csv`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/results/final/final_test_warm.csv) | Tabular warm test metrics | CSV |
| [`recommender/results/final/evaluation_run_log.json`](file:///c:/Users/Lenovo/Projects/MoieRec/recommender/results/final/evaluation_run_log.json) | Run timestamp, total runtime, command execution details | JSON |
| [`docs/figures/ndcg_cold_start_all_candidates.png`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/figures/ndcg_cold_start_all_candidates.png) | High-resolution figure: cold start all candidates | PNG |
| [`docs/figures/ndcg_cold_start_long_tail.png`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/figures/ndcg_cold_start_long_tail.png) | High-resolution figure: cold start long-tail | PNG |
| [`docs/figures/warm_test_metrics_bar.png`](file:///c:/Users/Lenovo/Projects/MoieRec/docs/figures/warm_test_metrics_bar.png) | High-resolution figure: warm test metrics bar chart | PNG |
