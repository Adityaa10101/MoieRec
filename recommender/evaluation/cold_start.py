"""Simulated cold-start onboarding evaluation protocol for MoieRec (Protocol v2).

Tests the product claim:
"A brand-new user picks a few movies they like and gets personalized recommendations immediately."

Protocol v2 (PHASE 2E.1):
1. Cold-start population: 5,119 users (splits/cold_start_users.parquet) partitioned 50/50
   into cold_dev (2,560 users) and cold_final (2,559 users). cold_final is strictly guarded behind final=True.
2. For K in {3, 5, 10}:
   - ONBOARDING = first K positives chronologically by (timestamp, seeded hash tie-break).
   - RELEVANT = the NEXT W=20 positives chronologically after onboarding picks that are in candidate catalog.
   - User inclusion threshold: user must have >= K + W positives in candidate catalog.
   - CANDIDATES = catalog minus the K revealed items.
3. Variants:
   (i) All candidates: candidate catalog minus K revealed items.
   (ii) Long-tail: candidate catalog minus K revealed items AND minus top-200 most-rated TRAIN movies.
        Top-200 most-rated TRAIN movies are ALSO excluded from the relevant set.
4. Reference protocol:
   - Old "all remaining positives" protocol kept as a labeled comparison reference.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from scipy import sparse

from recommender.evaluation.evaluator import (
    Evaluator,
    MetricSummary,
    PairedComparisonResult,
    compute_bootstrap_ci,
    select_topk_exact,
)
from recommender.evaluation.metrics import (
    compute_hits,
    hit_rate_at_k,
    mrr_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from recommender.preprocessing.split_dataset import compute_tie_hash


def partition_cold_start_users(
    cold_users_parquet: Path,
    output_partition_json: Path,
    seed: int = 42,
) -> Dict[str, Any]:
    """Deterministically partition cold-start users 50/50 into cold_dev and cold_final.

    Args:
        cold_users_parquet: Path to splits/cold_start_users.parquet.
        output_partition_json: Destination Path for partition metadata JSON.
        seed: Random seed for deterministic partition.

    Returns:
        Dict with partition metadata.
    """
    df = pd.read_parquet(cold_users_parquet, columns=["user_id"])
    unique_users = np.sort(df["user_id"].unique())
    n_total = len(unique_users)

    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(unique_users)
    n_dev = n_total // 2

    cold_dev = np.sort(shuffled[:n_dev]).tolist()
    cold_final = np.sort(shuffled[n_dev:]).tolist()

    partition_data = {
        "seed": seed,
        "n_total": n_total,
        "n_cold_dev": len(cold_dev),
        "n_cold_final": len(cold_final),
        "cold_dev_user_ids": cold_dev,
        "cold_final_user_ids": cold_final,
    }

    output_partition_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_partition_json, "w", encoding="utf-8") as f:
        json.dump(partition_data, f, indent=2)

    return partition_data


def compute_canonical_top200_train_mids(
    train_df_or_path: Any,
) -> Set[int]:
    """Compute canonical top-200 most-rated movies in train set for Protocol v2 long-tail variant.

    Canonical definition: top 200 by total rating count (all ratings in train).
    """
    if isinstance(train_df_or_path, (str, Path)):
        train_df = pd.read_parquet(train_df_or_path, columns=["movie_id"])
    else:
        train_df = train_df_or_path
    top200 = train_df["movie_id"].value_counts().head(200).index.tolist()
    return set(top200)


def load_cold_start_split(
    split: str = "cold_dev",
    final: bool = False,
    splits_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """Load interactions for a cold-start split with strict runtime guard on cold_final.

    Args:
        split: 'cold_dev' or 'cold_final'.
        final: Must be True to access cold_final.
        splits_dir: Path to processed splits directory.

    Raises:
        PermissionError: If split == 'cold_final' and final is False.
    """
    if splits_dir is None:
        splits_dir = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "ml-25m" / "splits"

    split_norm = split.lower().strip()
    if split_norm == "cold_final" and not final:
        raise PermissionError(
            "Access to cold_final split is strictly guarded! It is reserved for the final frozen report "
            "and cannot be read without final=True."
        )

    partition_path = splits_dir / "cold_start_partition.json"
    if not partition_path.exists():
        partition_cold_start_users(splits_dir / "cold_start_users.parquet", partition_path, seed=42)

    with open(partition_path, "r", encoding="utf-8") as f:
        part_meta = json.load(f)

    if split_norm == "cold_dev":
        allowed_users = set(part_meta["cold_dev_user_ids"])
    elif split_norm == "cold_final":
        allowed_users = set(part_meta["cold_final_user_ids"])
    else:
        raise ValueError(f"Unknown cold split: {split}. Expected 'cold_dev' or 'cold_final'.")

    full_cold_df = pd.read_parquet(splits_dir / "cold_start_users.parquet")
    sub_df = full_cold_df[full_cold_df["user_id"].isin(allowed_users)].copy()
    sub_df["tie_hash"] = compute_tie_hash(sub_df["user_id"].to_numpy(), sub_df["movie_id"].to_numpy(), seed=42)
    sub_df = sub_df.sort_values(by=["user_id", "timestamp", "tie_hash"]).reset_index(drop=True)
    return sub_df.drop(columns=["tie_hash"])


@dataclass
class ColdStartEvaluationResult:
    """Evaluation result for a model under the simulated cold-start onboarding protocol."""
    k_onboarding: int
    model_name: str
    n_evaluated_users: int
    n_excluded_users: int
    precision: MetricSummary
    recall: MetricSummary
    ndcg: MetricSummary
    hit_rate: MetricSummary
    mrr: MetricSummary
    protocol: str = "v2"
    variant: str = "all_candidates"
    per_user_metrics: Optional[Dict[str, np.ndarray]] = None


class ColdStartEvaluator:
    """Evaluates cold-start onboarding recommendation across K in {3, 5, 10} under Protocol v2."""

    def __init__(
        self,
        cold_df: pd.DataFrame,
        candidate_movie_ids: np.ndarray,
        positive_threshold: float = 4.0,
        k_eval: int = 10,
        n_bootstrap: int = 1000,
        seed: int = 42,
    ):
        self.cold_df = cold_df
        self.candidate_movie_ids = np.asarray(candidate_movie_ids)
        self.n_candidates = len(self.candidate_movie_ids)
        self.movie_id_to_cand_idx = {mid: idx for idx, mid in enumerate(self.candidate_movie_ids)}
        self.positive_threshold = positive_threshold
        self.k_eval = k_eval
        self.n_bootstrap = n_bootstrap
        self.seed = seed

        # Filter candidate positives and sort chronologically by (user_id, timestamp, tie_hash)
        pos_df = cold_df[
            (cold_df["rating"] >= positive_threshold) &
            (cold_df["movie_id"].isin(self.movie_id_to_cand_idx))
        ].copy()
        pos_df["tie_hash"] = compute_tie_hash(pos_df["user_id"].to_numpy(), pos_df["movie_id"].to_numpy(), seed=self.seed)
        pos_df = pos_df.sort_values(by=["user_id", "timestamp", "tie_hash"]).reset_index(drop=True)
        pos_df["cand_idx"] = pos_df["movie_id"].map(self.movie_id_to_cand_idx)
        self.user_positives: Dict[int, List[int]] = pos_df.groupby("user_id")["cand_idx"].apply(list).to_dict()
        self.total_cold_users = cold_df["user_id"].nunique()

        # Deterministic seeded random permutation for candidate tie-breaks
        rng = np.random.default_rng(self.seed)
        self.tie_ranks = rng.permutation(self.n_candidates)

    def prepare_data_v2(
        self,
        k_onboarding: int,
        window_w: int = 20,
        long_tail: bool = False,
        top200_train_mids: Optional[Set[int]] = None,
    ) -> Tuple[List[int], List[List[int]], List[Set[int]], List[Set[int]], int]:
        """Prepare cold-start data under Protocol v2.

        Users must have >= k_onboarding + window_w positives in candidate catalog.
        - ONBOARDING = first K positives.
        - RELEVANT = NEXT W=20 positives chronologically.
        - CANDIDATES = catalog minus K revealed items (and minus top-200 if long_tail=True).
        - If long_tail=True: top-200 train movies excluded from candidates AND from relevant set.

        Returns:
            Tuple of (eval_users, revealed_list, ground_truth_list, mask_indices_list, n_excluded)
        """
        min_required = k_onboarding + window_w
        eval_users = []
        revealed_list = []
        ground_truth_list = []
        mask_indices_list = []

        top200_cand = set()
        if long_tail and top200_train_mids:
            top200_cand = {self.movie_id_to_cand_idx[m] for m in top200_train_mids if m in self.movie_id_to_cand_idx}

        for uid in sorted(self.user_positives.keys()):
            pos_list = self.user_positives[uid]
            if len(pos_list) >= min_required:
                revealed = pos_list[:k_onboarding]
                next_w = pos_list[k_onboarding : k_onboarding + window_w]

                if long_tail:
                    gt = set(cand_idx for cand_idx in next_w if cand_idx not in top200_cand)
                    mask = set(revealed) | top200_cand
                else:
                    gt = set(next_w)
                    mask = set(revealed)

                # Include user if they have >= 1 relevant item in ground truth
                if len(gt) > 0:
                    eval_users.append(uid)
                    revealed_list.append(revealed)
                    ground_truth_list.append(gt)
                    mask_indices_list.append(mask)

        n_excluded = self.total_cold_users - len(eval_users)
        return eval_users, revealed_list, ground_truth_list, mask_indices_list, n_excluded

    def prepare_data_old(
        self,
        k_onboarding: int,
    ) -> Tuple[List[int], List[List[int]], List[Set[int]], List[Set[int]], int]:
        """Prepare cold-start data under the OLD 'all remaining positives' reference protocol."""
        min_required = k_onboarding + 5
        eval_users = []
        revealed_list = []
        ground_truth_list = []
        mask_indices_list = []

        for uid in sorted(self.user_positives.keys()):
            pos_list = self.user_positives[uid]
            if len(pos_list) >= min_required:
                revealed = pos_list[:k_onboarding]
                gt = set(pos_list[k_onboarding:])
                mask = set(revealed)

                if len(gt) > 0:
                    eval_users.append(uid)
                    revealed_list.append(revealed)
                    ground_truth_list.append(gt)
                    mask_indices_list.append(mask)

        n_excluded = self.total_cold_users - len(eval_users)
        return eval_users, revealed_list, ground_truth_list, mask_indices_list, n_excluded

    def evaluate_popularity(
        self,
        k_onboarding: int,
        popularity_scores: np.ndarray,
        eval_users: List[int],
        revealed_list: List[List[int]],
        ground_truth_list: List[Set[int]],
        mask_indices_list: List[Set[int]],
        n_excluded: int,
        model_name: str = "popularity_most_liked",
        protocol: str = "v2",
        variant: str = "all_candidates",
    ) -> ColdStartEvaluationResult:
        """Evaluate Popularity baseline under cold-start onboarding protocol."""
        n_users = len(eval_users)
        base_scores = popularity_scores.astype(np.float64, copy=True)
        all_topk = []

        for u_idx in range(n_users):
            user_scores = base_scores.copy()
            user_scores[list(mask_indices_list[u_idx])] = -np.inf
            topk = select_topk_exact(user_scores[None, :], k=self.k_eval, tie_ranks=self.tie_ranks)[0]
            all_topk.append(topk)

        predicted_topk = np.array(all_topk, dtype=int) if all_topk else np.zeros((0, self.k_eval), dtype=int)

        # Vectorized evaluation
        hits = compute_hits(predicted_topk, ground_truth_list)
        gt_counts = np.array([len(gt) for gt in ground_truth_list], dtype=np.int64)

        precisions = precision_at_k(hits, self.k_eval)
        recalls = recall_at_k(hits, gt_counts, self.k_eval)
        ndcgs = ndcg_at_k(hits, gt_counts, self.k_eval)
        hit_rates = hit_rate_at_k(hits, self.k_eval)
        mrrs = mrr_at_k(hits, self.k_eval)

        prec_s = MetricSummary(*compute_bootstrap_ci(precisions, self.n_bootstrap, seed=self.seed))
        rec_s = MetricSummary(*compute_bootstrap_ci(recalls, self.n_bootstrap, seed=self.seed))
        ndcg_s = MetricSummary(*compute_bootstrap_ci(ndcgs, self.n_bootstrap, seed=self.seed))
        hr_s = MetricSummary(*compute_bootstrap_ci(hit_rates, self.n_bootstrap, seed=self.seed))
        mrr_s = MetricSummary(*compute_bootstrap_ci(mrrs, self.n_bootstrap, seed=self.seed))

        per_user = {
            "precision": precisions,
            "recall": recalls,
            "ndcg": ndcgs,
            "hit_rate": hit_rates,
            "mrr": mrrs,
        }

        return ColdStartEvaluationResult(
            k_onboarding=k_onboarding,
            model_name=model_name,
            n_evaluated_users=n_users,
            n_excluded_users=n_excluded,
            precision=prec_s,
            recall=rec_s,
            ndcg=ndcg_s,
            hit_rate=hr_s,
            mrr=mrr_s,
            protocol=protocol,
            variant=variant,
            per_user_metrics=per_user,
        )

    def evaluate_content_model(
        self,
        k_onboarding: int,
        item_features: np.ndarray,
        eval_users: List[int],
        revealed_list: List[List[int]],
        ground_truth_list: List[Set[int]],
        mask_indices_list: List[Set[int]],
        n_excluded: int,
        model_name: str = "content_tier1",
        protocol: str = "v2",
        variant: str = "all_candidates",
    ) -> ColdStartEvaluationResult:
        """Evaluate Content-Based model with profile built strictly from K revealed items."""
        n_users = len(eval_users)

        # Build profile matrix P [n_users, D] via sparse matrix product W * X
        row_indices = []
        col_indices = []
        data_vals = []
        weight_per_item = 1.0 / float(k_onboarding)

        for u_idx, rev in enumerate(revealed_list):
            for cand_i in rev:
                row_indices.append(u_idx)
                col_indices.append(cand_i)
                data_vals.append(weight_per_item)

        W = sparse.csr_matrix(
            (data_vals, (row_indices, col_indices)),
            shape=(n_users, self.n_candidates),
            dtype=np.float32,
        )

        raw_profiles = W.dot(item_features).astype(np.float32)
        norms = np.linalg.norm(raw_profiles, axis=1, keepdims=True)
        safe_norms = np.where(norms > 0, norms, 1.0)
        profiles = raw_profiles / safe_norms

        # Batched scoring and top-k selection
        all_topk = []
        batch_size = 500
        for start_idx in range(0, n_users, batch_size):
            end_idx = min(start_idx + batch_size, n_users)
            b_profiles = profiles[start_idx:end_idx]
            # Scores: [batch_len, n_candidates]
            b_scores = np.dot(b_profiles, item_features.T).astype(np.float64)

            # Mask revealed items and long-tail items
            for b_i, u_idx in enumerate(range(start_idx, end_idx)):
                b_scores[b_i, list(mask_indices_list[u_idx])] = -np.inf

            topk_batch = select_topk_exact(b_scores, k=self.k_eval, tie_ranks=self.tie_ranks)
            all_topk.append(topk_batch)

        predicted_topk = np.vstack(all_topk) if all_topk else np.zeros((0, self.k_eval), dtype=int)

        # Vectorized evaluation
        hits = compute_hits(predicted_topk, ground_truth_list)
        gt_counts = np.array([len(gt) for gt in ground_truth_list], dtype=np.int64)

        precisions = precision_at_k(hits, self.k_eval)
        recalls = recall_at_k(hits, gt_counts, self.k_eval)
        ndcgs = ndcg_at_k(hits, gt_counts, self.k_eval)
        hit_rates = hit_rate_at_k(hits, self.k_eval)
        mrrs = mrr_at_k(hits, self.k_eval)

        prec_s = MetricSummary(*compute_bootstrap_ci(precisions, self.n_bootstrap, seed=self.seed))
        rec_s = MetricSummary(*compute_bootstrap_ci(recalls, self.n_bootstrap, seed=self.seed))
        ndcg_s = MetricSummary(*compute_bootstrap_ci(ndcgs, self.n_bootstrap, seed=self.seed))
        hr_s = MetricSummary(*compute_bootstrap_ci(hit_rates, self.n_bootstrap, seed=self.seed))
        mrr_s = MetricSummary(*compute_bootstrap_ci(mrrs, self.n_bootstrap, seed=self.seed))

        per_user = {
            "precision": precisions,
            "recall": recalls,
            "ndcg": ndcgs,
            "hit_rate": hit_rates,
            "mrr": mrrs,
        }

        return ColdStartEvaluationResult(
            k_onboarding=k_onboarding,
            model_name=model_name,
            n_evaluated_users=n_users,
            n_excluded_users=n_excluded,
            precision=prec_s,
            recall=rec_s,
            ndcg=ndcg_s,
            hit_rate=hr_s,
            mrr=mrr_s,
            protocol=protocol,
            variant=variant,
            per_user_metrics=per_user,
        )

    def evaluate_scores(
        self,
        k_onboarding: int,
        scores: np.ndarray,
        eval_users: List[int],
        revealed_list: List[List[int]],
        ground_truth_list: List[Set[int]],
        mask_indices_list: List[Set[int]],
        n_excluded: int,
        model_name: str = "custom",
        protocol: str = "v2",
        variant: str = "all_candidates",
    ) -> ColdStartEvaluationResult:
        """Evaluate precomputed user scores matrix under cold-start onboarding protocol."""
        n_users = len(eval_users)
        all_topk = []
        batch_size = 500

        for start_idx in range(0, n_users, batch_size):
            end_idx = min(start_idx + batch_size, n_users)
            b_scores = scores[start_idx:end_idx].astype(np.float64, copy=True)
            for b_i, u_idx in enumerate(range(start_idx, end_idx)):
                b_scores[b_i, list(mask_indices_list[u_idx])] = -np.inf
            topk_batch = select_topk_exact(b_scores, k=self.k_eval, tie_ranks=self.tie_ranks)
            all_topk.append(topk_batch)

        predicted_topk = np.vstack(all_topk) if all_topk else np.zeros((0, self.k_eval), dtype=int)

        hits = compute_hits(predicted_topk, ground_truth_list)
        gt_counts = np.array([len(gt) for gt in ground_truth_list], dtype=np.int64)

        precisions = precision_at_k(hits, self.k_eval)
        recalls = recall_at_k(hits, gt_counts, self.k_eval)
        ndcgs = ndcg_at_k(hits, gt_counts, self.k_eval)
        hit_rates = hit_rate_at_k(hits, self.k_eval)
        mrrs = mrr_at_k(hits, self.k_eval)

        prec_s = MetricSummary(*compute_bootstrap_ci(precisions, self.n_bootstrap, seed=self.seed))
        rec_s = MetricSummary(*compute_bootstrap_ci(recalls, self.n_bootstrap, seed=self.seed))
        ndcg_s = MetricSummary(*compute_bootstrap_ci(ndcgs, self.n_bootstrap, seed=self.seed))
        hr_s = MetricSummary(*compute_bootstrap_ci(hit_rates, self.n_bootstrap, seed=self.seed))
        mrr_s = MetricSummary(*compute_bootstrap_ci(mrrs, self.n_bootstrap, seed=self.seed))

        per_user = {
            "precision": precisions,
            "recall": recalls,
            "ndcg": ndcgs,
            "hit_rate": hit_rates,
            "mrr": mrrs,
        }

        return ColdStartEvaluationResult(
            k_onboarding=k_onboarding,
            model_name=model_name,
            n_evaluated_users=n_users,
            n_excluded_users=n_excluded,
            precision=prec_s,
            recall=rec_s,
            ndcg=ndcg_s,
            hit_rate=hr_s,
            mrr=mrr_s,
            protocol=protocol,
            variant=variant,
            per_user_metrics=per_user,
        )
