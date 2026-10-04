#!/usr/bin/env python3
"""
recommender/serving/hybrid_scorer.py
====================================
Serving Scorer for Hybrid Models:
- Supports Hybrid v2 (Phase 2G-Lite): Content + CF + Popularity blend on simplex.
- Backward-compatible with Hybrid v1.1 / v1 (Phase 2F/2F.1): Content + Popularity with alpha schedule.

Requirements:
- Strict dependencies: numpy, scipy, pyyaml only (NO pandas, NO pyarrow).
- Used by both recommender parity tests AND backend serving API.
- Block-structured serving footprint (Tier 1 dense, Tags CSR, Genome dense, Norms).
- Compact CF neighbor arrays (no dense item-item matrix, ~42 MB footprint).
- Fast precomputed feature display strings (Latency target p50 < 150 ms).
- Dynamic weights schedule by bucket for Hybrid v2:
    K 3-4   -> tuned K=3  (w_c=0.0, w_f=1.0, w_p=0.0)
    K 5-7   -> tuned K=5  (w_c=0.0, w_f=1.0, w_p=0.0)
    K 8-14  -> tuned K=10 (w_c=0.0, w_f=1.0, w_p=0.0)
    K >= 15 -> tuned K=20 (w_c=0.1, w_f=0.9, w_p=0.0)
- Evidence extraction & Label Honesty:
    - nearest_pick: liked movie with highest cosine (id, title, cosine)
    - top_shared_features: top 3 positively contributing shared features (genres / tags)
    - components: {content: w_c * pct_content, cf: w_f * pct_cf, popularity: w_p * pct_pop}
    - cf_pick: top contributing pick for CF with (id, title, similarity, cooccurrence)
    - match_percent: integer 0-100 (relative rank among pool candidates, NOT a probability)
    - reason_codes and honest reason_labels:
        SIMILAR_TO_PICK      -> "Similar to <pick title>"
        SHARED_TAGS          -> "Shared tags: <tags>"
        SHARED_GENRES        -> "Shared genres: <genres>"
        POPULAR_WITH_VIEWERS -> "Popular with MovieLens viewers"
        CO_LIKED_BY_USERS    -> "N MovieLens viewers who liked <pick> also liked this" (emitted iff n_ij >= cf_min_support)
    - Forbidden strings anywhere in output/UI: "Acclaimed", "Strong Match", "% match".
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import scipy.sparse as sp
import scipy.stats as st
import yaml


def select_topk_exact(
    scores: np.ndarray,
    k: int,
    tie_ranks: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Select top-k items descending by score with deterministic tie-breaking.
    Pure numpy implementation matching evaluator.select_topk_exact.
    """
    if scores.ndim == 1:
        scores = scores[None, :]
        squeeze = True
    else:
        squeeze = False

    n_users, n_items = scores.shape
    if tie_ranks is None:
        tie_ranks = np.arange(n_items, dtype=np.int32)

    k = min(k, n_items)
    if k <= 0:
        res = np.zeros((n_users, 0), dtype=np.int32)
        return res[0] if squeeze else res

    # 1. Fast introselect partition at k
    part_idx = np.argpartition(-scores, k - 1, axis=1)[:, :k]
    row_idx = np.arange(n_users)[:, None]
    part_scores = scores[row_idx, part_idx]
    part_tie_ranks = tie_ranks[part_idx]

    # 2. Sort the k items by (-score, tie_ranks) using lexsort
    sub_order = np.lexsort((part_tie_ranks, -part_scores), axis=1)
    topk = np.take_along_axis(part_idx, sub_order, axis=1)

    # 3. Boundary tie check
    sorted_part_scores = np.take_along_axis(part_scores, sub_order, axis=1)
    k_scores = sorted_part_scores[:, -1]

    topk_k_score_counts = np.sum(sorted_part_scores == k_scores[:, None], axis=1)
    total_k_score_counts = np.sum(scores == k_scores[:, None], axis=1)

    tied_row_mask = (total_k_score_counts > topk_k_score_counts) & np.isfinite(k_scores)
    tied_rows = np.flatnonzero(tied_row_mask)

    if len(tied_rows) > 0:
        for u in tied_rows:
            s_star = k_scores[u]
            higher_items = np.flatnonzero(scores[u] > s_star)
            tied_items = np.flatnonzero(scores[u] == s_star)

            needed_from_tied = k - len(higher_items)
            tied_order = np.argsort(tie_ranks[tied_items])
            chosen_tied = tied_items[tied_order[:needed_from_tied]]

            combined = np.concatenate([higher_items, chosen_tied])
            comb_scores = scores[u, combined]
            comb_ties = tie_ranks[combined]
            comb_order = np.lexsort((comb_ties, -comb_scores))
            topk[u] = combined[comb_order]

    return topk[0] if squeeze else topk


class HybridScorer:
    """Production serving scorer for Hybrid Recommender Models (hybrid_v2 and hybrid_v1.1).

    Uses only numpy, scipy, and pyyaml.
    Supports block-structured serving footprint (Tier 1 dense, Tags CSR, Genome dense, Norms).
    Supports compact CF neighbor arrays for neighborhood collaborative filtering.
    """

    def __init__(self, artifacts_dir: Optional[Path] = None):
        if artifacts_dir is None:
            v2_path = Path(__file__).resolve().parent.parent.parent / "data" / "serving" / "model_v2"
            v1_path = Path(__file__).resolve().parent.parent.parent / "data" / "serving" / "model_v1"
            artifacts_dir = v2_path if v2_path.exists() else v1_path
        self.artifacts_dir = Path(artifacts_dir)
        self.load_artifacts()

    def load_artifacts(self) -> None:
        """Load model artifacts and index mappings from artifacts_dir."""
        # 1. Config: check hybrid_v2.yaml first, then hybrid_v1_1.yaml, then hybrid_v1.yaml
        cfg_2_0 = self.artifacts_dir / "hybrid_v2.yaml"
        cfg_1_1 = self.artifacts_dir / "hybrid_v1_1.yaml"
        cfg_1_0 = self.artifacts_dir / "hybrid_v1.yaml"
        if cfg_2_0.exists():
            config_path = cfg_2_0
        elif cfg_1_1.exists():
            config_path = cfg_1_1
        elif cfg_1_0.exists():
            config_path = cfg_1_0
        else:
            raise FileNotFoundError(f"Config file not found in {self.artifacts_dir}")

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        v_str = str(self.config.get("version", ""))
        if "v2" in v_str or "2.0" in v_str:
            self.version = "2.0"
            self.is_v2 = True
        elif "1.1" in v_str:
            self.version = "1.1"
            self.is_v2 = False
        else:
            self.version = "1.0"
            self.is_v2 = False

        self.similarity_threshold = float(self.config.get("similarity_threshold", 0.1278))
        self.tie_break_seed = int(self.config.get("tie_break_seed", 42))

        # Content block weights
        bw = self.config.get("content_block_weights", self.config.get("block_weights", {}))
        self.w_t1 = float(bw.get("w_t1", 1.0))
        self.w_tags = float(bw.get("w_tags", 4.0))
        self.w_genome = float(bw.get("w_genome", 1.0))

        # Schedule buckets
        if self.is_v2:
            self.bucket_schedule = self.config.get(
                "bucket_schedule",
                {
                    "K_3_4": {"w_c": 0.0, "w_f": 1.0, "w_p": 0.0},
                    "K_5_7": {"w_c": 0.0, "w_f": 1.0, "w_p": 0.0},
                    "K_8_14": {"w_c": 0.0, "w_f": 1.0, "w_p": 0.0},
                    "K_15_plus": {"w_c": 0.1, "w_f": 0.9, "w_p": 0.0},
                },
            )
            # Minimum support for CO_LIKED_BY_USERS (90th percentile of stored pairs, computed offline)
            cf_cfg = self.config.get("collaborative_config", {})
            self.cf_min_support = int(cf_cfg.get("cf_min_support", 185))
        else:
            self.alpha_buckets = self.config.get(
                "alpha_by_bucket",
                {"K_3_4": 0.3, "K_5_7": 0.6, "K_8_14": 0.7, "K_15_plus": 0.8},
            )
            self.default_alpha = float(self.config.get("alpha", 0.5))

        # 2. Block Arrays (Footprint optimized)
        self.item_t1 = np.load(self.artifacts_dir / "item_t1.npy").astype(np.float32)
        self.item_tags_csr = sp.load_npz(self.artifacts_dir / "item_tags_csr.npz").astype(np.float32)
        self.item_genome = np.load(self.artifacts_dir / "item_genome.npy").astype(np.float32)
        self.item_norms = np.load(self.artifacts_dir / "item_norms.npy").astype(np.float32)
        self.inv_item_norms = (1.0 / np.where(self.item_norms > 0, self.item_norms, 1.0)).astype(np.float32)

        # Catalog metadata
        self.item_movie_ids = np.load(self.artifacts_dir / "item_movie_ids.npy").astype(np.int32)
        self.pop_scores = np.load(self.artifacts_dir / "pop_scores.npy").astype(np.float32)

        self.n_items = len(self.item_movie_ids)
        self.d_t1 = self.item_t1.shape[1]
        self.d_tags = self.item_tags_csr.shape[1]
        self.d_genome = self.item_genome.shape[1]
        self.dim = self.d_t1 + self.d_tags + self.d_genome

        # 3. Collaborative filtering compact neighbor arrays (v2 only)
        if self.is_v2:
            self.cf_indices = np.load(self.artifacts_dir / "cf_topk_indices.npy").astype(np.int32)
            self.cf_sims = np.load(self.artifacts_dir / "cf_topk_sims.npy").astype(np.float32)
            self.cf_cooc = np.load(self.artifacts_dir / "cf_topk_cooc.npy").astype(np.int32)
        else:
            self.cf_indices = None
            self.cf_sims = None
            self.cf_cooc = None

        # 4. Metadata JSONs
        with open(self.artifacts_dir / "feature_names.json", "r", encoding="utf-8") as f:
            self.feature_names = json.load(f)

        with open(self.artifacts_dir / "genre_names.json", "r", encoding="utf-8") as f:
            self.genre_names = set(json.load(f))

        with open(self.artifacts_dir / "genome_tag_names.json", "r", encoding="utf-8") as f:
            self.genome_tag_names = set(json.load(f))

        movie_titles_path = self.artifacts_dir / "movie_titles.json"
        if movie_titles_path.exists():
            with open(movie_titles_path, "r", encoding="utf-8") as f:
                raw_titles = json.load(f)
                self.movie_titles = {int(k): v for k, v in raw_titles.items()}
        else:
            self.movie_titles = {}

        # Fast lookup index
        self.movie_id_to_idx = {int(mid): idx for idx, mid in enumerate(self.item_movie_ids)}

        # Deterministic candidate tie-break permutation
        rng = np.random.default_rng(self.tie_break_seed)
        self.tie_ranks = rng.permutation(self.n_items).astype(np.int32)

        # Precompute stripped feature display names and types once at load (Latency Fix C3)
        self.clean_feature_info: List[Tuple[str, str, str]] = []
        for f_idx, raw_name in enumerate(self.feature_names):
            if f_idx < self.d_t1:
                f_type = "genre" if "genre" in raw_name else "release_era"
                clean_name = raw_name.replace("t1:genre:", "").replace("genre:", "").replace("t1:", "")
            elif f_idx < self.d_t1 + self.d_tags:
                f_type = "tag"
                clean_name = raw_name.replace("tag:", "")
            else:
                f_type = "genome_tag"
                clean_name = raw_name.replace("genome:", "")
            self.clean_feature_info.append((clean_name, raw_name, f_type))

    def get_alpha(self, k: int) -> float:
        """Read alpha from the bucket schedule for v1.1."""
        if k <= 4:
            return float(self.alpha_buckets.get("K_3_4", 0.3))
        elif k <= 7:
            return float(self.alpha_buckets.get("K_5_7", 0.6))
        elif k <= 14:
            return float(self.alpha_buckets.get("K_8_14", 0.7))
        else:
            return float(self.alpha_buckets.get("K_15_plus", 0.8))

    def get_weights(self, k: int) -> Tuple[float, float, float]:
        """Read weights (w_c, w_f, w_p) from the bucket schedule for Hybrid v2."""
        if not self.is_v2:
            a = self.get_alpha(k)
            return a, 0.0, 1.0 - a

        if k <= 4:
            b = self.bucket_schedule.get("K_3_4", {"w_c": 0.0, "w_f": 1.0, "w_p": 0.0})
        elif k <= 7:
            b = self.bucket_schedule.get("K_5_7", {"w_c": 0.0, "w_f": 1.0, "w_p": 0.0})
        elif k <= 14:
            b = self.bucket_schedule.get("K_8_14", {"w_c": 0.0, "w_f": 1.0, "w_p": 0.0})
        else:
            b = self.bucket_schedule.get("K_15_plus", {"w_c": 0.1, "w_f": 0.9, "w_p": 0.0})
        return float(b["w_c"]), float(b["w_f"]), float(b["w_p"])

    def is_valid_movie_id(self, movie_id: int) -> bool:
        """Check if movie_id exists in the serving catalog."""
        return int(movie_id) in self.movie_id_to_idx

    def get_title(self, movie_id: int) -> str:
        """Get movie title by movie_id."""
        return self.movie_titles.get(int(movie_id), f"Movie {movie_id}")

    def score(
        self,
        liked_movie_ids: List[int],
        exclude_movie_ids: Optional[List[int]] = None,
        top_k: int = 20,
        alpha: Optional[float] = None,
    ) -> Tuple[List[Dict[str, Any]], List[int]]:
        """Score candidate catalog items using the hybrid model.

        Args:
            liked_movie_ids: List of MovieLens movie_ids picked by the user.
            exclude_movie_ids: Optional list of movie_ids to exclude (disliked, already seen, etc.)
            top_k: Number of recommendations to return (default: 20).
            alpha: Optional override for alpha (v1.1 only).

        Returns:
            Tuple of:
                ranked_items: List of item dicts with rank, score, match_percent, reason_codes, explanation, source
                ignored_ids: List of input liked_movie_ids that were not in the serving catalog.
        """
        if exclude_movie_ids is None:
            exclude_movie_ids = []

        # Validate liked IDs
        valid_liked: List[int] = []
        ignored_ids: List[int] = []
        for mid in liked_movie_ids:
            if self.is_valid_movie_id(mid):
                if mid not in valid_liked:
                    valid_liked.append(mid)
            else:
                ignored_ids.append(mid)

        if not valid_liked:
            return [], ignored_ids

        k_liked = len(valid_liked)
        if self.is_v2:
            w_c, w_f, w_p = self.get_weights(k_liked)
            alpha_used = w_c
        else:
            alpha_used = float(alpha) if alpha is not None else self.get_alpha(k_liked)
            w_c, w_f, w_p = alpha_used, 0.0, 1.0 - alpha_used

        # Build candidate pool: items in catalog NOT in valid_liked and NOT in exclude_ids
        exclude_set = set(valid_liked) | set(int(m) for m in exclude_movie_ids if self.is_valid_movie_id(m))

        pool_mask = np.ones(self.n_items, dtype=bool)
        for mid in exclude_set:
            if mid in self.movie_id_to_idx:
                pool_mask[self.movie_id_to_idx[mid]] = False

        pool_indices = np.flatnonzero(pool_mask)
        n_pool = len(pool_indices)
        if n_pool == 0:
            return [], ignored_ids

        # 1. Profile construction: mean of liked items' Tier 2 vectors in block structure
        liked_indices = np.array([self.movie_id_to_idx[mid] for mid in valid_liked], dtype=np.int32)
        liked_inv_norms = self.inv_item_norms[liked_indices]  # [K]

        # T1 block raw mean
        p_t1_raw = np.mean(
            self.item_t1[liked_indices] * (liked_inv_norms[:, None] * self.w_t1),
            axis=0,
        )

        # Tag block raw mean
        tag_liked_csr = self.item_tags_csr[liked_indices]
        tag_scaled = tag_liked_csr.multiply(liked_inv_norms[:, None] * self.w_tags)
        p_tag_raw = np.array(tag_scaled.mean(axis=0)).flatten()

        # Genome block raw mean
        p_gen_raw = np.mean(
            self.item_genome[liked_indices] * (liked_inv_norms[:, None] * self.w_genome),
            axis=0,
        )

        # Total profile norm
        total_p_norm = np.sqrt(
            np.sum(p_t1_raw ** 2) + np.sum(p_tag_raw ** 2) + np.sum(p_gen_raw ** 2)
        )
        if total_p_norm > 0:
            p_t1 = (p_t1_raw / total_p_norm).astype(np.float32)
            p_tag = (p_tag_raw / total_p_norm).astype(np.float32)
            p_gen = (p_gen_raw / total_p_norm).astype(np.float32)
        else:
            p_t1, p_tag, p_gen = p_t1_raw, p_tag_raw, p_gen_raw

        # 2. Content scores across all items via block dot-products
        s_t1 = self.item_t1.dot(p_t1 * self.w_t1)
        s_tag = self.item_tags_csr.dot(p_tag * self.w_tags)
        s_gen = self.item_genome.dot(p_gen * self.w_genome)
        all_content_scores = ((s_t1 + s_tag + s_gen) * self.inv_item_norms).astype(np.float64)
        content_scores_pool = all_content_scores[pool_indices]

        # 3. Popularity scores across the pool
        pop_scores_pool = self.pop_scores[pool_indices].astype(np.float64)

        # 4. Percentile ranks across the pool (ties get average rank)
        if n_pool > 1:
            c_ranks = st.rankdata(content_scores_pool, method="average")
            pct_content_pool = (c_ranks - 1.0) / float(n_pool - 1.0)

            p_ranks = st.rankdata(pop_scores_pool, method="average")
            pct_pop_pool = (p_ranks - 1.0) / float(n_pool - 1.0)
        else:
            pct_content_pool = np.ones(1, dtype=np.float64)
            pct_pop_pool = np.ones(1, dtype=np.float64)

        # 5. Collaborative Filtering component (v2 only)
        if self.is_v2 and self.cf_indices is not None:
            cf_scores_all = np.zeros(self.n_items, dtype=np.float32)
            for p in liked_indices:
                neigh_idx = self.cf_indices[p]
                neigh_sim = self.cf_sims[p]
                v_mask = (neigh_idx >= 0) & (neigh_sim > 0)
                if np.any(v_mask):
                    np.add.at(cf_scores_all, neigh_idx[v_mask], neigh_sim[v_mask] / float(k_liked))

            cf_scores_pool = cf_scores_all[pool_indices].astype(np.float64)
            if n_pool > 1:
                f_ranks = st.rankdata(cf_scores_pool, method="average")
                pct_cf_pool = (f_ranks - 1.0) / float(n_pool - 1.0)
            else:
                pct_cf_pool = np.ones(1, dtype=np.float64)

            # Final 3-component simplex blend
            final_scores_pool = w_c * pct_content_pool + w_f * pct_cf_pool + w_p * pct_pop_pool
        else:
            pct_cf_pool = np.zeros(n_pool, dtype=np.float64)
            final_scores_pool = alpha_used * pct_content_pool + (1.0 - alpha_used) * pct_pop_pool

        # 6. Final percentile within the pool (for match_percent, 0 to 100)
        if n_pool > 1:
            fin_ranks = st.rankdata(final_scores_pool, method="average")
            pct_final_pool = (fin_ranks - 1.0) / float(n_pool - 1.0)
        else:
            pct_final_pool = np.ones(1, dtype=np.float64)

        # 7. Exact top-k selection with tie-breaking
        pool_tie_ranks = self.tie_ranks[pool_indices]
        k_to_fetch = min(top_k, n_pool)
        topk_pool_idx = select_topk_exact(
            final_scores_pool[None, :],
            k=k_to_fetch,
            tie_ranks=pool_tie_ranks,
        )[0]

        # 8. Evidence extraction only for returned items (Latency Fix C3)
        ranked_items = []
        for rank, p_idx in enumerate(topk_pool_idx, start=1):
            global_item_idx = pool_indices[p_idx]
            movie_id = int(self.item_movie_ids[global_item_idx])
            title = self.get_title(movie_id)
            inv_norm_cand = float(self.inv_item_norms[global_item_idx])

            # (a) Nearest content pick: liked movie with highest cosine similarity
            cand_t1_v = self.item_t1[global_item_idx]
            cand_tag_csr = self.item_tags_csr[global_item_idx]
            cand_gen_v = self.item_genome[global_item_idx]

            liked_t1_dots = self.item_t1[liked_indices].dot(cand_t1_v) * (self.w_t1 ** 2)
            liked_tag_dots = np.array(
                self.item_tags_csr[liked_indices].dot(cand_tag_csr.T).toarray()
            ).flatten() * (self.w_tags ** 2)
            liked_gen_dots = self.item_genome[liked_indices].dot(cand_gen_v) * (self.w_genome ** 2)

            liked_cosines = (liked_t1_dots + liked_tag_dots + liked_gen_dots) * (
                liked_inv_norms * inv_norm_cand
            )
            best_liked_pos = int(np.argmax(liked_cosines))
            nearest_pick_mid = valid_liked[best_liked_pos]
            nearest_pick_cos = float(liked_cosines[best_liked_pos])
            nearest_pick = {
                "movie_id": nearest_pick_mid,
                "title": self.get_title(nearest_pick_mid),
                "similarity": round(nearest_pick_cos, 4),
            }

            # (b) Top shared features: top 3 positive feature contributions to profile-item cosine
            c_t1 = (p_t1 * cand_t1_v) * (self.w_t1 * inv_norm_cand)
            tag_col_idx = cand_tag_csr.indices
            tag_vals = cand_tag_csr.data
            c_tags = (p_tag[tag_col_idx] * tag_vals) * (self.w_tags * inv_norm_cand)
            c_gen = (p_gen * cand_gen_v) * (self.w_genome * inv_norm_cand)

            pos_features = []
            # T1 pos
            for f_idx, val in enumerate(c_t1):
                if val > 0:
                    clean_name, raw_name, f_type = self.clean_feature_info[f_idx]
                    pos_features.append((val, clean_name, raw_name, f_type))

            # Tags pos
            tag_offset = self.d_t1
            for local_col, val in zip(tag_col_idx, c_tags):
                if val > 0:
                    global_feat_idx = tag_offset + local_col
                    clean_name, raw_name, f_type = self.clean_feature_info[global_feat_idx]
                    pos_features.append((val, clean_name, raw_name, f_type))

            # Genome pos
            genome_offset = self.d_t1 + self.d_tags
            for local_col, val in enumerate(c_gen):
                if val > 0:
                    global_feat_idx = genome_offset + local_col
                    clean_name, raw_name, f_type = self.clean_feature_info[global_feat_idx]
                    pos_features.append((val, clean_name, raw_name, f_type))

            # Sort positive contributions descending
            pos_features.sort(key=lambda x: -x[0])
            top_shared_features = []
            for val, clean_name, raw_name, f_type in pos_features[:3]:
                top_shared_features.append({
                    "feature": clean_name,
                    "raw_name": raw_name,
                    "contribution": round(float(val), 4),
                    "feature_type": f_type,
                })

            # (c) Components
            if self.is_v2:
                components = {
                    "content": round(float(w_c * pct_content_pool[p_idx]), 4),
                    "cf": round(float(w_f * pct_cf_pool[p_idx]), 4),
                    "popularity": round(float(w_p * pct_pop_pool[p_idx]), 4),
                }
            else:
                components = {
                    "content": round(float(alpha_used * pct_content_pool[p_idx]), 4),
                    "popularity": round(float((1.0 - alpha_used) * pct_pop_pool[p_idx]), 4),
                }

            # (d) Match percent: relative rank within pool (0-100 integer)
            match_pct = int(round(float(pct_final_pool[p_idx]) * 100))
            match_pct = max(0, min(100, match_pct))

            # (e) Reason codes & Honest Labels
            reason_codes = []
            reason_labels = {}

            # SIMILAR_TO_PICK: only if nearest_pick cosine >= similarity_threshold
            if nearest_pick_cos >= self.similarity_threshold:
                reason_codes.append("SIMILAR_TO_PICK")
                reason_labels["SIMILAR_TO_PICK"] = f"Similar to {nearest_pick['title']}"

            # Extract shared genres and tags from top_shared_features
            shared_genres = [
                f["feature"] for f in top_shared_features if f["feature_type"] == "genre" and f["contribution"] > 0
            ]
            shared_tags = [
                f["feature"] for f in top_shared_features if f["feature_type"] in ("tag", "genome_tag") and f["contribution"] > 0
            ]

            if shared_genres:
                reason_codes.append("SHARED_GENRES")
                reason_labels["SHARED_GENRES"] = f"Shared genres: {', '.join(shared_genres)}"

            if shared_tags:
                reason_codes.append("SHARED_TAGS")
                reason_labels["SHARED_TAGS"] = f"Shared tags: {', '.join(shared_tags)}"

            # POPULAR_WITH_VIEWERS: only if popularity component is the dominant or positive contributor
            if not self.is_v2:
                if components["popularity"] >= components["content"]:
                    reason_codes.append("POPULAR_WITH_VIEWERS")
                    reason_labels["POPULAR_WITH_VIEWERS"] = "Popular with MovieLens viewers"
            else:
                if w_p > 0 and components["popularity"] >= max(components["content"], components["cf"]):
                    reason_codes.append("POPULAR_WITH_VIEWERS")
                    reason_labels["POPULAR_WITH_VIEWERS"] = "Popular with MovieLens viewers"

            # (f) CF Contributor & CO_LIKED_BY_USERS Reason Code (C2)
            cf_pick = None
            if self.is_v2 and self.cf_indices is not None:
                best_cf_sim = -1.0
                best_cf_pick_mid = None
                best_cf_cooc = 0
                for p_pos, p_idx_serving in enumerate(liked_indices):
                    neigh_row = self.cf_indices[p_idx_serving]
                    matches = np.flatnonzero(neigh_row == global_item_idx)
                    if len(matches) > 0:
                        loc = matches[0]
                        s = float(self.cf_sims[p_idx_serving, loc])
                        c = int(self.cf_cooc[p_idx_serving, loc])
                        if s > best_cf_sim and s > 0:
                            best_cf_sim = s
                            best_cf_pick_mid = valid_liked[p_pos]
                            best_cf_cooc = c

                if best_cf_pick_mid is not None and best_cf_sim > 0:
                    cf_pick = {
                        "movie_id": best_cf_pick_mid,
                        "title": self.get_title(best_cf_pick_mid),
                        "similarity": round(best_cf_sim, 4),
                        "cooccurrence": best_cf_cooc,
                    }
                    if best_cf_cooc >= self.cf_min_support:
                        reason_codes.append("CO_LIKED_BY_USERS")
                        reason_labels["CO_LIKED_BY_USERS"] = (
                            f"{best_cf_cooc:,} MovieLens viewers who liked {self.get_title(best_cf_pick_mid)} also liked this"
                        )

            explanation = {
                "nearest_pick": nearest_pick,
                "top_shared_features": top_shared_features,
                "components": components,
                "match_percent": match_pct,
                "alpha": round(alpha_used, 4),
                "similarity_threshold": self.similarity_threshold,
                "reason_labels": reason_labels,
            }
            if self.is_v2:
                explanation["weights"] = {"w_c": round(w_c, 2), "w_f": round(w_f, 2), "w_p": round(w_p, 2)}
                explanation["cf_pick"] = cf_pick

            ranked_items.append({
                "movie_id": movie_id,
                "title": title,
                "rank": rank,
                "score": round(float(final_scores_pool[p_idx]), 4),
                "match_percent": match_pct,
                "reason_codes": reason_codes,
                "explanation": explanation,
                "source": "hybrid_v2" if self.is_v2 else "hybrid_v1.1",
            })

        return ranked_items, ignored_ids

    def similar_items(
        self,
        movie_id: int,
        n: int = 20,
    ) -> List[Dict[str, Any]]:
        """Find content-only nearest neighbors for a single movie using cosine similarity.

        Args:
            movie_id: The query MovieLens movie_id.
            n: Number of neighbors to return (default: 20).

        Returns:
            List of neighbor dicts with movie_id, title, score (cosine), source="content_similarity"
        """
        if not self.is_valid_movie_id(movie_id):
            return []

        q_idx = self.movie_id_to_idx[int(movie_id)]
        q_inv = float(self.inv_item_norms[q_idx])

        # Block-structured dot product
        s_t1 = self.item_t1.dot(self.item_t1[q_idx] * (self.w_t1 ** 2 * q_inv))
        q_tag_row = self.item_tags_csr[q_idx]
        s_tag = np.array(
            self.item_tags_csr.dot(q_tag_row.T).toarray()
        ).flatten() * (self.w_tags ** 2 * q_inv)
        s_gen = self.item_genome.dot(self.item_genome[q_idx] * (self.w_genome ** 2 * q_inv))

        cosines = ((s_t1 + s_tag + s_gen) * self.inv_item_norms).astype(np.float64)
        cosines[q_idx] = -np.inf  # exclude self

        k_fetch = min(n, self.n_items - 1)
        if k_fetch <= 0:
            return []

        top_indices = select_topk_exact(cosines[None, :], k=k_fetch, tie_ranks=self.tie_ranks)[0]

        neighbors = []
        for rank, idx in enumerate(top_indices, start=1):
            mid = int(self.item_movie_ids[idx])
            title = self.get_title(mid)
            score_val = float(cosines[idx])
            neighbors.append({
                "movie_id": mid,
                "title": title,
                "rank": rank,
                "score": round(score_val, 4),
                "source": "content_similarity",
            })

        return neighbors
