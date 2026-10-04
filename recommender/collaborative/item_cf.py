"""Item-Item Collaborative Filtering (Neighborhood CF) for MoieRec.

Implementation for Phase 2G-Lite:
- Built strictly from TRAIN ratings (main-split users, r >= positive_threshold).
- Co-occurrence counts n_ij = |{u in train : r_{u,i} >= 4.0 and r_{u,j} >= 4.0}|.
- Single item positive counts n_i = |{u in train : r_{u,i} >= 4.0}|.
- Similarity variants:
    sim(i, j) = [n_ij / (n_i^a * n_j^(1-a))] * [n_ij / (n_ij + lambda)]
    where a in {0.5, 0.7}, lambda in {0, 20, 100}, top-k neighbors with k in {50, 100, 200}.
    sim(i, i) = 0.0 (zero diagonal).
- Warm scoring:
    scores = user_train_positives @ S
    where seen items are masked by the evaluator.
- Cold-start scoring:
    cf_score(item) = mean over K picks of sim(pick, item)
    (using truncated neighbors; items outside every pick's neighbor list score 0.0).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import scipy.sparse as sp

from recommender.evaluation.protocol import Recommender


def get_default_cache_dir() -> Path:
    """Return default git-ignored directory for collaborative filtering caches."""
    root_dir = Path(__file__).resolve().parent.parent.parent
    return root_dir / "data" / "processed" / "ml-25m" / "collaborative"


def compute_item_cooccurrence_and_counts(
    train_df: pd.DataFrame,
    candidate_mids: np.ndarray,
    positive_threshold: float = 4.0,
    cache_dir: Optional[Path] = None,
    save: bool = True,
) -> Tuple[sp.csr_matrix, np.ndarray]:
    """Compute and optionally cache n_ij co-occurrences and n_i counts from train positives.

    Args:
        train_df: Train interactions [user_id, movie_id, rating].
        candidate_mids: Sorted candidate movie IDs array.
        positive_threshold: Threshold defining positive rating (>= 4.0).
        cache_dir: Directory to save cache files.
        save: Whether to save to disk.

    Returns:
        (N, n_i): N is sp.csr_matrix of co-occurrences, n_i is 1D array of positive counts.
    """
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    npz_path = cache_dir / "item_cooccurrence.npz"
    counts_path = cache_dir / "item_counts.npy"
    mids_path = cache_dir / "candidate_movie_ids.npy"

    if npz_path.exists() and counts_path.exists() and mids_path.exists():
        cached_mids = np.load(mids_path)
        if len(cached_mids) == len(candidate_mids) and np.array_equal(cached_mids, candidate_mids):
            N = sp.load_npz(npz_path)
            n_i = np.load(counts_path)
            return N, n_i

    # Filter train positives on candidate catalog
    cand_to_idx = {mid: i for i, mid in enumerate(candidate_mids)}
    pos_train = train_df[train_df["rating"] >= positive_threshold]
    valid_pos = pos_train[pos_train["movie_id"].isin(cand_to_idx)].copy()

    unique_users = np.sort(valid_pos["user_id"].unique())
    user_to_idx = {uid: i for i, uid in enumerate(unique_users)}

    u_idx = valid_pos["user_id"].map(user_to_idx).to_numpy(dtype=np.int32)
    i_idx = valid_pos["movie_id"].map(cand_to_idx).to_numpy(dtype=np.int32)
    data = np.ones(len(valid_pos), dtype=np.float32)

    R = sp.csr_matrix(
        (data, (u_idx, i_idx)),
        shape=(len(unique_users), len(candidate_mids)),
        dtype=np.float32,
    )
    n_i = np.asarray(R.sum(axis=0)).ravel()

    R_csc = R.tocsc()
    N = (R_csc.T).dot(R_csc).astype(np.int32)

    if save:
        cache_dir.mkdir(parents=True, exist_ok=True)
        sp.save_npz(npz_path, N)
        np.save(counts_path, n_i)
        np.save(mids_path, candidate_mids)

    return N, n_i


def compute_or_load_topk_neighbors(
    a: float = 0.5,
    lam: float = 0.0,
    k_max: int = 200,
    cache_dir: Optional[Path] = None,
    train_df: Optional[pd.DataFrame] = None,
    candidate_mids: Optional[np.ndarray] = None,
    positive_threshold: float = 4.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute or load top-k_max neighbors, similarities, and co-occurrences.

    Returns:
        (topk_indices, topk_similarities, topk_cooccurrences) each of shape [n_items, k_max].
    """
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    tag = f"a{int(round(a * 10))}_lam{int(round(lam))}"
    cache_file = cache_dir / f"top200_{tag}.npz"

    if cache_file.exists():
        data = np.load(cache_file)
        return data["indices"], data["similarities"], data["cooccurrences"]

    # Compute from co-occurrence matrix
    if candidate_mids is None:
        mids_path = cache_dir / "candidate_movie_ids.npy"
        if mids_path.exists():
            candidate_mids = np.load(mids_path)
        else:
            root_dir = Path(__file__).resolve().parent.parent.parent
            bench_movies = pd.read_parquet(root_dir / "data" / "processed" / "ml-25m" / "benchmark" / "movies.parquet")
            candidate_mids = np.sort(bench_movies["movie_id"].unique())

    npz_path = cache_dir / "item_cooccurrence.npz"
    counts_path = cache_dir / "item_counts.npy"

    if npz_path.exists() and counts_path.exists():
        N = sp.load_npz(npz_path)
        n_i = np.load(counts_path)
    else:
        if train_df is None:
            root_dir = Path(__file__).resolve().parent.parent.parent
            train_df = pd.read_parquet(root_dir / "data" / "processed" / "ml-25m" / "splits" / "train.parquet")
        N, n_i = compute_item_cooccurrence_and_counts(
            train_df, candidate_mids, positive_threshold=positive_threshold, cache_dir=cache_dir
        )

    n_items = len(n_i)
    denom_i = np.where(n_i > 0, n_i ** a, 1.0).astype(np.float32)
    denom_j = np.where(n_i > 0, n_i ** (1.0 - a), 1.0).astype(np.float32)

    topk_indices = np.zeros((n_items, k_max), dtype=np.int32)
    topk_sims = np.zeros((n_items, k_max), dtype=np.float32)
    topk_cooc = np.zeros((n_items, k_max), dtype=np.int32)

    block_size = 1000
    for start in range(0, n_items, block_size):
        end = min(start + block_size, n_items)
        b_len = end - start
        dense_block = N[start:end].toarray().astype(np.float32)
        d_i = denom_i[start:end, None]

        mask = dense_block > 0
        sim_block = np.zeros_like(dense_block)
        val = dense_block[mask]
        d = (d_i * denom_j)[mask]
        shrink = val / (val + lam) if lam > 0 else 1.0
        sim_block[mask] = (val / d) * shrink

        # Zero diagonal
        for r in range(b_len):
            sim_block[r, start + r] = 0.0

        part_idx = np.argpartition(-sim_block, k_max, axis=1)[:, :k_max]
        r_idx = np.arange(b_len)[:, None]
        part_scores = sim_block[r_idx, part_idx]
        sort_order = np.argsort(-part_scores, axis=1)
        sorted_idx = np.take_along_axis(part_idx, sort_order, axis=1)
        sorted_scores = np.take_along_axis(part_scores, sort_order, axis=1)
        sorted_cooc = np.take_along_axis(dense_block, sorted_idx, axis=1).astype(np.int32)

        topk_indices[start:end] = sorted_idx
        topk_sims[start:end] = sorted_scores
        topk_cooc[start:end] = sorted_cooc

    cache_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        cache_file,
        indices=topk_indices,
        similarities=topk_sims,
        cooccurrences=topk_cooc,
    )
    return topk_indices, topk_sims, topk_cooc


class ItemItemCollaborativeRecommender(Recommender):
    """Item-Item Neighborhood Collaborative Filtering Recommender.

    Scores candidate items for users by spreading weight across truncated top-k item similarities:
        score(u, j) = sum_{i in user_train_positives} sim(i, j)
    """

    def __init__(
        self,
        a: float = 0.5,
        shrinkage: float = 0.0,
        k: int = 100,
        positive_threshold: float = 4.0,
        cache_dir: Optional[Path] = None,
    ):
        """Initialize Item-Item Collaborative Filtering Recommender.

        Args:
            a: Asymmetric exponent on pick item count n_i (0.5 for symmetric cosine).
            shrinkage: Shrinkage parameter lambda >= 0.
            k: Number of nearest neighbors to keep per item.
            positive_threshold: Threshold defining positive interaction (>= 4.0).
            cache_dir: Optional directory with cached counts/similarities.
        """
        self.a = float(a)
        self.shrinkage = float(shrinkage)
        self.k = int(k)
        self.positive_threshold = float(positive_threshold)
        self.cache_dir = cache_dir or get_default_cache_dir()

        # Model state
        self.candidate_movie_ids: Optional[np.ndarray] = None
        self.movie_id_to_cand_idx: Optional[Dict[int, int]] = None
        self.n_candidates: int = 0
        self.S: Optional[sp.csr_matrix] = None  # Truncated sparse similarity [n_candidates, n_candidates]
        self.user_train_positives: Optional[sp.csr_matrix] = None  # [n_eval_users, n_candidates]

        # Raw neighbor lookup tables (for evidence & serving)
        self.raw_mids: Optional[np.ndarray] = None
        self.topk_indices: Optional[np.ndarray] = None
        self.topk_sims: Optional[np.ndarray] = None
        self.topk_cooc: Optional[np.ndarray] = None

    def fit(self, train_df: pd.DataFrame, context: Optional[dict] = None) -> "ItemItemCollaborativeRecommender":
        """Fit model strictly on training split interactions.

        Args:
            train_df: Training interactions DataFrame [user_id, movie_id, rating, timestamp].
            context: Optional dict containing 'candidate_movie_ids', 'eval_user_ids', 'user_id_to_eval_idx'.
        """
        root_dir = Path(__file__).resolve().parent.parent.parent
        bench_movies_path = root_dir / "data" / "processed" / "ml-25m" / "benchmark" / "movies.parquet"

        if context is not None and "candidate_movie_ids" in context:
            self.candidate_movie_ids = np.asarray(context["candidate_movie_ids"])
        elif bench_movies_path.exists():
            bench_df = pd.read_parquet(bench_movies_path, columns=["movie_id"])
            self.candidate_movie_ids = np.sort(bench_df["movie_id"].unique())
        else:
            self.candidate_movie_ids = np.sort(train_df["movie_id"].unique())

        self.n_candidates = len(self.candidate_movie_ids)
        self.movie_id_to_cand_idx = {mid: i for i, mid in enumerate(self.candidate_movie_ids)}

        # Load candidate movie IDs of precomputed cache (benchmark catalog: 18,277)
        mids_path = self.cache_dir / "candidate_movie_ids.npy"
        if mids_path.exists():
            self.raw_mids = np.load(mids_path)
        else:
            self.raw_mids = self.candidate_movie_ids

        raw_to_cand = {mid: self.movie_id_to_cand_idx.get(mid, -1) for mid in self.raw_mids}

        # Load top-200 neighbor tables for (self.a, self.shrinkage)
        indices_200, sims_200, cooc_200 = compute_or_load_topk_neighbors(
            a=self.a,
            lam=self.shrinkage,
            k_max=200,
            cache_dir=self.cache_dir,
            train_df=train_df,
            candidate_mids=self.raw_mids,
            positive_threshold=self.positive_threshold,
        )

        self.topk_indices = indices_200
        self.topk_sims = sims_200
        self.topk_cooc = cooc_200

        # Construct truncated similarity matrix S for self.k
        k_use = min(self.k, 200)
        row_list = []
        col_list = []
        val_list = []

        for raw_i, raw_mid in enumerate(self.raw_mids):
            cand_i = raw_to_cand[raw_mid]
            if cand_i == -1:
                continue

            for rank in range(k_use):
                sim = sims_200[raw_i, rank]
                if sim <= 0.0:
                    break
                raw_j = indices_200[raw_i, rank]
                raw_j_mid = self.raw_mids[raw_j]
                cand_j = raw_to_cand.get(raw_j_mid, -1)
                if cand_j != -1 and cand_j != cand_i:
                    row_list.append(cand_i)
                    col_list.append(cand_j)
                    val_list.append(sim)

        self.S = sp.csr_matrix(
            (val_list, (row_list, col_list)),
            shape=(self.n_candidates, self.n_candidates),
            dtype=np.float32,
        )

        # Build evaluated user train positive matrix if requested
        if context is not None and "user_id_to_eval_idx" in context:
            user_id_to_eval_idx = context["user_id_to_eval_idx"]
            n_eval_users = len(context.get("eval_user_ids", user_id_to_eval_idx))

            pos_train = train_df[train_df["rating"] >= self.positive_threshold]
            valid_train = pos_train[
                pos_train["user_id"].isin(user_id_to_eval_idx) &
                pos_train["movie_id"].isin(self.movie_id_to_cand_idx)
            ]

            u_rows = valid_train["user_id"].map(user_id_to_eval_idx).to_numpy(dtype=np.int32)
            i_cols = valid_train["movie_id"].map(self.movie_id_to_cand_idx).to_numpy(dtype=np.int32)
            vals = np.ones(len(valid_train), dtype=np.float32)

            self.user_train_positives = sp.csr_matrix(
                (vals, (u_rows, i_cols)),
                shape=(n_eval_users, self.n_candidates),
                dtype=np.float32,
            )

        return self

    def score(self, user_indices: np.ndarray) -> np.ndarray:
        """Compute recommendation scores for evaluated users.

        Args:
            user_indices: 1D array of user row indices.

        Returns:
            2D float32 array of shape [len(user_indices), n_candidates].
        """
        if self.S is None or self.user_train_positives is None:
            raise RuntimeError("Model must be fitted with user context before calling score().")

        batch_u = self.user_train_positives[user_indices]
        scores = batch_u.dot(self.S).toarray()
        return scores.astype(np.float32)

    def score_picks(self, pick_mids: List[int]) -> np.ndarray:
        """Compute CF scores over candidate catalog for cold-start user picks.

        cf_score(item) = mean over K picks of sim(pick, item).
        Items outside every pick's neighbor list score 0.0.

        Args:
            pick_mids: List of revealed pick movie IDs.

        Returns:
            1D float32 array of shape [n_candidates].
        """
        if self.S is None:
            raise RuntimeError("Model must be fitted before calling score_picks().")

        k_picks = len(pick_mids)
        if k_picks == 0:
            return np.zeros(self.n_candidates, dtype=np.float32)

        # Collect rows from S for valid picks
        pick_indices = [
            self.movie_id_to_cand_idx[mid]
            for mid in pick_mids
            if mid in self.movie_id_to_cand_idx
        ]

        if not pick_indices:
            return np.zeros(self.n_candidates, dtype=np.float32)

        # Sum similarities from each pick and divide by k_picks
        sub_S = self.S[pick_indices]
        pick_sum = np.asarray(sub_S.sum(axis=0)).ravel()
        scores = pick_sum / float(k_picks)
        return scores.astype(np.float32)

    def explain_pick_contribution(
        self,
        pick_mids: List[int],
        target_movie_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Find the top contributing pick for a recommended item.

        Returns dict with:
            pick_id: MovieLens movie ID of top contributing pick.
            similarity: sim(pick, target)
            cooccurrence: n_ij between pick and target
        """
        if self.S is None or self.raw_mids is None:
            return None

        target_idx = self.movie_id_to_cand_idx.get(target_movie_id)
        if target_idx is None:
            return None

        best_sim = -1.0
        best_pick_id = None
        best_cooc = 0

        raw_mid_to_idx = {mid: i for i, mid in enumerate(self.raw_mids)}
        raw_target_idx = raw_mid_to_idx.get(target_movie_id)
        if raw_target_idx is None:
            return None

        for p_mid in pick_mids:
            p_cand_idx = self.movie_id_to_cand_idx.get(p_mid)
            if p_cand_idx is None:
                continue

            sim_val = float(self.S[p_cand_idx, target_idx])
            if sim_val > best_sim and sim_val > 0.0:
                best_sim = sim_val
                best_pick_id = p_mid

                # Lookup co-occurrence count
                raw_p_idx = raw_mid_to_idx.get(p_mid)
                if raw_p_idx is not None and self.topk_indices is not None:
                    # Check in raw_p_idx neighbor list
                    nbrs = self.topk_indices[raw_p_idx]
                    coocs = self.topk_cooc[raw_p_idx]
                    match_pos = np.where(nbrs == raw_target_idx)[0]
                    if len(match_pos) > 0:
                        best_cooc = int(coocs[match_pos[0]])

        if best_pick_id is None:
            return None

        return {
            "pick_id": best_pick_id,
            "similarity": best_sim,
            "cooccurrence": best_cooc,
        }
