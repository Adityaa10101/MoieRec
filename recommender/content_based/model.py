"""Content-based recommender model (Model 1) for MoieRec.

Implements Tier 1 item representations (genres + release year) and Tier 2 snapshot
representations (genres + year + tag TF-IDF + genome), with customizable user profile
weighting strategies, cosine similarity scoring, and explainability extraction.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy import sparse

from recommender.evaluation.protocol import Recommender


class ProfileVariant(str, Enum):
    POS_MEAN = "pos_mean"
    RATING_WEIGHTED = "rating_weighted"
    CENTERED = "centered"
    POS_RATING_WEIGHTED = "pos_rating_weighted"


class ContentBasedRecommender(Recommender):
    """Content-based recommender using item feature representations and user interaction profiles."""

    def __init__(
        self,
        profile_variant: Union[str, ProfileVariant] = ProfileVariant.POS_MEAN,
        use_genre_idf: bool = False,
        year_weight: float = 0.5,
        missing_year_weight: float = 0.0,
        positive_threshold: float = 4.0,
        tier: int = 1,
        tier2_block_weights: Optional[Dict[str, float]] = None,
        feature_dir: Optional[Path] = None,
    ):
        """Initialize Content-Based Recommender.

        Args:
            profile_variant: One of 'pos_mean', 'rating_weighted', 'centered', 'pos_rating_weighted'.
            use_genre_idf: If True, scale genre columns by inverse document frequency over candidate movies.
            year_weight: Multiplier for normalized release year feature (e.g., 0.0, 0.25, 0.5, 1.0).
            missing_year_weight: Multiplier for missing year indicator flag (default 0.0).
            positive_threshold: Threshold defining positive feedback (used in pos_mean and pos_rating_weighted).
            tier: Feature tier (1 for Tier 1 genres+year, 2 for Tier 2 snapshot).
            tier2_block_weights: Dict with weights for 'tier1', 'tags', and 'genome' blocks.
            feature_dir: Directory containing pre-extracted features (.npz, .npy).
        """
        self.profile_variant = ProfileVariant(profile_variant)
        self.use_genre_idf = bool(use_genre_idf)
        self.year_weight = float(year_weight)
        self.missing_year_weight = float(missing_year_weight)
        self.positive_threshold = float(positive_threshold)
        self.tier = int(tier)
        self.tier2_block_weights = tier2_block_weights or {"tier1": 1.0, "tags": 1.0, "genome": 1.0}
        self.feature_dir = feature_dir

        # Fitted state
        self.candidate_movie_ids: Optional[np.ndarray] = None
        self.movie_id_to_cand_idx: Optional[Dict[int, int]] = None
        self.n_candidates: int = 0
        self.item_features: Optional[np.ndarray] = None  # L2-normalized float32 [n_candidates, D]
        self.feature_names: List[str] = []
        self.user_profiles: Optional[np.ndarray] = None  # L2-normalized float32 [n_users, D]
        self.n_zero_profile_users: int = 0
        self.evaluated_user_ids: Optional[np.ndarray] = None

    def fit(self, train_df: pd.DataFrame, context: Optional[dict] = None) -> "ContentBasedRecommender":
        """Fit item representation and build user profiles strictly from training interactions.

        Args:
            train_df: Train interactions [user_id, movie_id, rating, timestamp].
            context: Context dictionary containing:
                     - 'candidate_movie_ids': array of candidate movie IDs in order
                     - 'user_id_to_eval_idx': optional mapping from user_id to row index in profile matrix
                     - 'eval_user_ids': optional array of user IDs
                     - 'feature_dir': optional Path to feature directory
        """
        root_dir = Path(__file__).resolve().parent.parent.parent
        feat_dir = self.feature_dir or (context.get("feature_dir") if context else None)
        if feat_dir is None:
            feat_dir = root_dir / "data" / "processed" / "ml-25m" / "features"
            if not feat_dir.exists():
                feat_dir = root_dir / "data" / "processed" / "ml-latest-small" / "features"

        # 1. Candidate Catalog Setup
        if context is not None and "candidate_movie_ids" in context:
            self.candidate_movie_ids = np.asarray(context["candidate_movie_ids"])
        else:
            self.candidate_movie_ids = np.sort(train_df["movie_id"].unique())

        self.n_candidates = len(self.candidate_movie_ids)
        self.movie_id_to_cand_idx = {mid: idx for idx, mid in enumerate(self.candidate_movie_ids)}

        # 2. Build / Slice Item Representation X [n_candidates, D]
        self._build_item_representation(feat_dir)

        # 3. Build User Profiles from TRAIN only: P = W_train * X
        if context is None or context.get("build_user_profiles", True):
            self._build_user_profiles(train_df, context)

        return self

    def _build_item_representation(self, feat_dir: Path) -> None:
        """Construct L2-normalized candidate item representation."""
        t1_path = feat_dir / "tier1_baseline_features.npz"
        meta_path = feat_dir / "feature_metadata.json"

        # If files exist on disk, slice and weight
        if t1_path.exists() and meta_path.exists():
            t1_csr = sparse.load_npz(t1_path)
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json_meta = pd.read_json(meta_path, typ="series")
                t1_info = json_meta["tier1_baseline"]
                feat_names = list(t1_info["feature_names"])
                n_genres = int(t1_info["n_genres"])

            # Map benchmark_idx to candidate_idx
            id_map_path = feat_dir.parent / "id_mappings" / "movie_id_to_benchmark_idx.parquet"
            if id_map_path.exists():
                m2b = pd.read_parquet(id_map_path).set_index("movie_id")["benchmark_idx"].to_dict()
                cand_bench_indices = [m2b[mid] for mid in self.candidate_movie_ids]
            else:
                cand_bench_indices = list(range(self.n_candidates))

            # Slice candidate rows: dense float32 array
            cand_t1 = t1_csr[cand_bench_indices].toarray().astype(np.float32)

            # Apply Genre IDF weighting if requested
            if self.use_genre_idf:
                # Compute IDF strictly over candidate movies
                genre_matrix = cand_t1[:, :n_genres]
                doc_freq = np.sum(genre_matrix > 0, axis=0)
                # Smoothed IDF: ln(N / (df + 1)) + 1.0
                idf = np.log((float(self.n_candidates) / (doc_freq + 1.0))) + 1.0
                cand_t1[:, :n_genres] *= idf

            # Apply Year weight & Missing Year weight
            cand_t1[:, n_genres] *= self.year_weight
            cand_t1[:, n_genres + 1] *= self.missing_year_weight

            # Tier 1 normalization
            t1_norms = np.linalg.norm(cand_t1, axis=1, keepdims=True)
            t1_norms = np.where(t1_norms > 0, t1_norms, 1.0)
            cand_t1 = cand_t1 / t1_norms

            if self.tier == 1:
                self.item_features = cand_t1
                # Format feature names
                cleaned_names = []
                for fn in feat_names:
                    if fn == "norm_year":
                        cleaned_names.append("release era")
                    elif fn == "missing_year_flag":
                        cleaned_names.append("missing release year")
                    else:
                        cleaned_names.append(fn)
                self.feature_names = cleaned_names
                return

            # Tier 2: Enhanced Snapshot features
            elif self.tier == 2:
                blocks = []
                w_t1 = self.tier2_block_weights.get("tier1", 1.0)
                blocks.append(cand_t1 * w_t1)
                all_names = [f"t1:{n}" for n in feat_names]

                # Tag TF-IDF block
                tags_path = feat_dir / "tier2_tag_tfidf.npz"
                if tags_path.exists() and self.tier2_block_weights.get("tags", 0.0) > 0:
                    w_tags = self.tier2_block_weights["tags"]
                    tags_csr = sparse.load_npz(tags_path)[cand_bench_indices]
                    # Row-normalize tags
                    tag_norms = sparse.linalg.norm(tags_csr, axis=1)
                    tag_norms = np.where(tag_norms > 0, tag_norms, 1.0)[:, None]
                    tags_dense = (tags_csr / tag_norms).astype(np.float32)
                    if sparse.issparse(tags_dense):
                        tags_dense = tags_dense.toarray()
                    blocks.append(tags_dense * w_tags)
                    all_names.extend([f"tag_tfidf_{i}" for i in range(tags_dense.shape[1])])

                # Genome block
                genome_path = feat_dir / "tier2_genome_matrix.npy"
                mask_path = feat_dir / "tier2_genome_mask.npy"
                if genome_path.exists() and mask_path.exists() and self.tier2_block_weights.get("genome", 0.0) > 0:
                    w_genome = self.tier2_block_weights["genome"]
                    genome_mat = np.load(genome_path)[cand_bench_indices].astype(np.float32)
                    genome_mask = np.load(mask_path)[cand_bench_indices].astype(np.float32)[:, None]
                    # Masked genome block (0 for unrated/missing)
                    masked_genome = genome_mat * genome_mask
                    gen_norms = np.linalg.norm(masked_genome, axis=1, keepdims=True)
                    gen_norms = np.where(gen_norms > 0, gen_norms, 1.0)
                    blocks.append((masked_genome / gen_norms) * w_genome)
                    all_names.extend([f"genome_dim_{i}" for i in range(masked_genome.shape[1])])

                concat_X = np.hstack(blocks)
                tot_norms = np.linalg.norm(concat_X, axis=1, keepdims=True)
                tot_norms = np.where(tot_norms > 0, tot_norms, 1.0)
                self.item_features = (concat_X / tot_norms).astype(np.float32)
                self.feature_names = all_names
                return

        else:
            # Fallback synthetic features (for unit tests without data directory)
            self.item_features = np.eye(self.n_candidates, dtype=np.float32)
            self.feature_names = [f"item_{i}" for i in range(self.n_candidates)]

    def _build_user_profiles(self, train_df: pd.DataFrame, context: Optional[dict] = None) -> None:
        """Compute user profile vectors via sparse matrix product W * X."""
        # Determine evaluated users mapping
        if context is not None and "user_id_to_eval_idx" in context:
            user_to_idx = context["user_id_to_eval_idx"]
            n_users = len(user_to_idx)
            self.evaluated_user_ids = context.get("eval_user_ids", np.sort(list(user_to_idx.keys())))
        else:
            unique_users = np.sort(train_df["user_id"].unique())
            user_to_idx = {uid: idx for idx, uid in enumerate(unique_users)}
            n_users = len(unique_users)
            self.evaluated_user_ids = unique_users

        # Filter train interactions to candidate items and mapped users
        valid_mask = train_df["user_id"].isin(user_to_idx) & train_df["movie_id"].isin(self.movie_id_to_cand_idx)
        sub_train = train_df[valid_mask].copy()

        # Compute weights based on profile variant
        if self.profile_variant == ProfileVariant.POS_MEAN:
            sub_train = sub_train[sub_train["rating"] >= self.positive_threshold]
            weights = np.ones(len(sub_train), dtype=np.float32)

        elif self.profile_variant == ProfileVariant.RATING_WEIGHTED:
            weights = sub_train["rating"].to_numpy(dtype=np.float32)

        elif self.profile_variant == ProfileVariant.CENTERED:
            # Weight = rating - user_train_mean
            user_means = sub_train.groupby("user_id")["rating"].mean()
            sub_train["mean_r"] = sub_train["user_id"].map(user_means)
            weights = (sub_train["rating"] - sub_train["mean_r"]).to_numpy(dtype=np.float32)

        elif self.profile_variant == ProfileVariant.POS_RATING_WEIGHTED:
            sub_train = sub_train[sub_train["rating"] >= self.positive_threshold]
            weights = sub_train["rating"].to_numpy(dtype=np.float32)

        else:
            raise ValueError(f"Unknown profile variant: {self.profile_variant}")

        # Construct sparse interaction weight matrix W [n_users, n_candidates]
        u_indices = sub_train["user_id"].map(user_to_idx).to_numpy(dtype=np.int32)
        i_indices = sub_train["movie_id"].map(self.movie_id_to_cand_idx).to_numpy(dtype=np.int32)

        W = sparse.csr_matrix(
            (weights, (u_indices, i_indices)),
            shape=(n_users, self.n_candidates),
            dtype=np.float32,
        )

        # Dense user profiles: P = W * X (float32 array [n_users, D])
        # Using sparse-dense matrix multiplication: W.dot(item_features)
        raw_profiles = W.dot(self.item_features).astype(np.float32)

        # L2 normalization of user profiles
        norms = np.linalg.norm(raw_profiles, axis=1, keepdims=True)
        zero_mask = (norms.squeeze() == 0.0)
        self.n_zero_profile_users = int(np.sum(zero_mask))

        # Safe normalize (zero profiles remain zero)
        safe_norms = np.where(norms > 0, norms, 1.0)
        self.user_profiles = raw_profiles / safe_norms

    def score(self, user_indices: np.ndarray) -> np.ndarray:
        """Compute cosine similarity scores between user profiles and candidate item features.

        Args:
            user_indices: 1D array of user row indices in user_profiles.

        Returns:
            2D float32 array of shape [len(user_indices), n_candidates].
        """
        if self.user_profiles is None or self.item_features is None:
            raise RuntimeError("Model must be fitted before calling score().")

        # Slice batch profiles [batch_size, D]
        batch_p = self.user_profiles[user_indices]

        # Cosine similarity: dot product of L2-normalized vectors
        # Shape: [batch_size, D] @ [D, n_candidates] -> [batch_size, n_candidates]
        scores = np.dot(batch_p, self.item_features.T)
        return scores.astype(np.float32)

    def explain(self, user_idx: int, item_idx: int, top_n: int = 3) -> List[Dict[str, Any]]:
        """Extract top feature contributions explaining the cosine recommendation score.

        Feature contribution is defined as p_{u, f} * x_{i, f} (after normalization).
        Guarantees:
        - Sum of all feature contributions equals model score within float tolerance.
        - Never names a feature with zero contribution.

        Args:
            user_idx: Internal user row index.
            item_idx: Internal candidate item index.
            top_n: Maximum number of contributing features to return.

        Returns:
            List of dicts: [{"feature": name, "contribution": float, "percentage": float}, ...]
        """
        if self.user_profiles is None or self.item_features is None:
            raise RuntimeError("Model must be fitted before calling explain().")

        p = self.user_profiles[user_idx]
        x = self.item_features[item_idx]

        # Element-wise contribution to the dot product
        contributions = p * x
        total_score = float(np.sum(contributions))

        # Filter strictly positive contributions
        pos_indices = np.flatnonzero(contributions > 1e-7)
        if len(pos_indices) == 0:
            return []

        # Sort descending by contribution
        sorted_pos = pos_indices[np.argsort(-contributions[pos_indices])]
        top_indices = sorted_pos[:top_n]

        results = []
        for idx in top_indices:
            feat_name = self.feature_names[idx] if idx < len(self.feature_names) else f"feature_{idx}"
            contrib = float(contributions[idx])
            pct = (contrib / total_score * 100.0) if total_score > 0 else 0.0
            results.append({
                "feature": feat_name,
                "contribution": round(contrib, 6),
                "percentage": round(pct, 2),
            })
        return results
