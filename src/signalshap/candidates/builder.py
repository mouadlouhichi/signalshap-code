"""Coalition-independent candidate generation (spec §2.1-§2.3).

The single most consequential design decision in the project. Candidates are
the union of each source's own top-N list, so EVERY coalition scores exactly
the same items. The rejected alternative -- draw candidates once from the
grand-coalition scorer -- hands the grand coalition a pool selected in its own
favour, inflating v(G) relative to every v(S) and biasing every Shapley value,
since attributions are built entirely from differences v(S u {g}) - v(S).

That rejected design is kept as `grand_coalition_candidates` for ablation E8-a,
which quantifies the bias avoided.
"""

from __future__ import annotations

import numpy as np

from ..config import SOURCES


def _topn(scores: np.ndarray, u: int, n: int) -> np.ndarray:
    """Top-n items for user u, ties broken by ascending item index.

    Deterministic tie-breaking (spec §2.3 step 5): np.lexsort orders by the
    last key first, so this sorts by (-score, item_index).
    """
    row = scores[u]
    n = min(n, int(np.isfinite(row).sum()))
    if n <= 0:
        return np.empty(0, dtype=np.int64)
    part = np.argpartition(-row, n - 1)[:n]
    return part[np.lexsort((part, -row[part]))]


def build_candidates_for_user(
    scores: dict[str, np.ndarray], u: int, n_max: int, max_iters: int = 10,
) -> np.ndarray:
    """Proportional-growth union with deterministic truncation (spec §2.3).

    Returns items sorted by (best per-source rank, source order, item index) --
    the same key used for truncation, so the prefix property holds and the set
    is reproducible across seeds and coalitions.
    """
    sources = [g for g in SOURCES if g in scores]
    n_g = {g: int(np.ceil(n_max / len(sources))) for g in sources}
    caps = {g: int(np.isfinite(scores[g][u]).sum()) for g in sources}

    lists: dict[str, np.ndarray] = {}
    for _ in range(max_iters):
        lists = {g: _topn(scores[g], u, min(n_g[g], caps[g])) for g in sources}
        union = set().union(*(set(v.tolist()) for v in lists.values())) if lists else set()
        if len(union) >= n_max or all(n_g[g] >= caps[g] for g in sources):
            break
        delta = n_max - len(union)
        step = int(np.ceil(delta / len(sources)))
        for g in sources:
            n_g[g] = min(n_g[g] + step, caps[g])

    # Step 6: rank each candidate by its best position across sources.
    best: dict[int, tuple[int, int]] = {}
    for s_idx, g in enumerate(sources):
        for rank, item in enumerate(lists.get(g, [])):
            item = int(item)
            if item not in best or (rank, s_idx) < best[item]:
                best[item] = (rank, s_idx)
    if not best:
        return np.empty(0, dtype=np.int64)
    ordered = sorted(best.items(), key=lambda kv: (kv[1][0], kv[1][1], kv[0]))
    return np.array([i for i, _ in ordered[:n_max]], dtype=np.int64)


def build_candidates(
    scores: dict[str, np.ndarray], n_users: int, n_max: int, max_iters: int = 10,
) -> list[np.ndarray]:
    return [
        build_candidates_for_user(scores, u, n_max, max_iters) for u in range(n_users)
    ]


def grand_coalition_candidates(
    scores: dict[str, np.ndarray], n_users: int, n_max: int,
) -> list[np.ndarray]:
    """REJECTED v1.0 design, retained for ablation E8-a only (spec §2.1).

    Candidates drawn once from the equally-weighted grand-coalition scorer.
    Never use for main results: it biases every sub-coalition against the
    grand coalition.
    """
    stack = np.stack([np.nan_to_num(scores[g], neginf=0.0) for g in SOURCES])
    z = (stack - stack.mean(axis=2, keepdims=True)) / (stack.std(axis=2, keepdims=True) + 1e-9)
    fused = z.sum(axis=0)
    fused[~np.isfinite(next(iter(scores.values())))] = -np.inf
    return [_topn(fused, u, n_max) for u in range(n_users)]


def candidate_recall(candidates: list[np.ndarray], test_items: dict[int, int]) -> float:
    """Pr[test_u in C_u] -- the ceiling on every ranking metric (spec §2.2)."""
    if not test_items:
        return 0.0
    hits = sum(
        1 for u, it in test_items.items()
        if u < len(candidates) and it in set(candidates[u].tolist())
    )
    return hits / len(test_items)
