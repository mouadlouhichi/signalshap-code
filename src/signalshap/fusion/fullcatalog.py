"""Full-catalog evaluation for T5 (spec §7).

THE TWO-PROTOCOL SPLIT, which must be stated in the paper and in T5's caption:

  * v(S) is FIXED-CANDIDATE within C_u. That is required for
    coalition-independence and is the definition of the game.
  * T5 REPORTING is full-catalog for every method. SignalShap-Fuse assigns
    -inf outside C_u, so items missed by candidate generation count as misses
    rather than being excluded from the denominator.

Why: if SignalShap-Fuse were capped by candidate recall while LightGCN ranked
the full catalogue, the two numbers would differ by the DENOMINATOR, not by the
fusion mechanism. Scoring outside-C_u items as misses makes the recall ceiling
a visible, quantified cost of the method. Restricting the baseline to C_u was
rejected: it handicaps a strong baseline by confining it to a pool built from
five other scorers' top-lists.
"""

from __future__ import annotations

import numpy as np

from ..game.core import ndcg_at_k, z_normalise


def full_catalog_metrics(score_row: np.ndarray, target: int, k_ndcg: int = 10,
                         k_recall: int = 20, k_mrr: int = 10) -> dict:
    """NDCG@10 / Recall@20 / MRR@10 over the entire catalogue."""
    order = np.lexsort((np.arange(len(score_row)), -score_row))
    hit = np.flatnonzero(order == target)
    if hit.size == 0:
        return {"ndcg": 0.0, "recall": 0.0, "mrr": 0.0}
    pos = int(hit[0])
    return {
        "ndcg": float(1.0 / np.log2(pos + 2)) if pos < k_ndcg else 0.0,
        "recall": 1.0 if pos < k_recall else 0.0,
        "mrr": float(1.0 / (pos + 1)) if pos < k_mrr else 0.0,
    }


def evaluate_full_catalog(scores: dict[str, np.ndarray], candidates: list[np.ndarray],
                          test_items: dict[int, int], users: list[int],
                          sources: tuple[str, ...], weights_of_user,
                          restrict_to_candidates: bool = True) -> dict:
    """Evaluate a weighted fusion over the FULL catalogue.

    With restrict_to_candidates=True (the SignalShap-Fuse setting) every item
    outside C_u is scored -inf, so the recall ceiling shows up honestly in the
    headline number.
    """
    n_items = next(iter(scores.values())).shape[1]
    acc = {"ndcg": [], "recall": [], "mrr": []}
    for u in users:
        z = np.column_stack([z_normalise(scores[g][u]) for g in sources])
        s = z @ weights_of_user(u)
        if restrict_to_candidates:
            mask = np.full(n_items, -np.inf)
            mask[candidates[u]] = 0.0
            s = s + mask
        m = full_catalog_metrics(s, test_items[u])
        for key in acc:
            acc[key].append(m[key])
    return {
        "ndcg_at_10": float(np.mean(acc["ndcg"])),
        "recall_at_20": float(np.mean(acc["recall"])),
        "mrr_at_10": float(np.mean(acc["mrr"])),
        "per_user_ndcg": np.array(acc["ndcg"]),
        "n_users": len(users),
    }


def popularity_reference(scores: dict[str, np.ndarray], test_items: dict[int, int],
                         users: list[int]) -> dict:
    """A full-catalog reference baseline that needs no GPU.

    Stands in for LightGCN in the CPU pipeline; the GPU baselines of spec §7
    plug in through the same interface.
    """
    acc = {"ndcg": [], "recall": [], "mrr": []}
    for u in users:
        m = full_catalog_metrics(scores["pop"][u], test_items[u])
        for key in acc:
            acc[key].append(m[key])
    return {
        "ndcg_at_10": float(np.mean(acc["ndcg"])),
        "recall_at_20": float(np.mean(acc["recall"])),
        "mrr_at_10": float(np.mean(acc["mrr"])),
        "per_user_ndcg": np.array(acc["ndcg"]),
        "n_users": len(users),
    }
