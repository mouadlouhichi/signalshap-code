"""User segmentation and SignalShap-Fuse (spec §1 C4/C5, §10 E3/E4).

Segments are behavioural: activity quantile crossed with recency skew. Fusion
weights are then learned PER SEGMENT on the validation fold and applied at
test time, which is the closed loop that turns attribution into a measurable
ranking gain.

Inference cost is "negligible (O(1) segment-lookup)", NOT zero (spec §20) --
the O(1) justification is a table lookup on precomputed user-segment ids.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import SOURCES
from ..game.core import ndcg_at_k


SEGMENT_NAMES = ("cold_stable", "cold_recency", "heavy_stable", "heavy_recency")


def assign_segments(train: pd.DataFrame, n_users: int) -> np.ndarray:
    """Segment id per user: activity (median split) x recency skew (median split).

    Recency skew = fraction of a user's interactions in the newer half of their
    own timespan; high values mean bursty/recent behaviour.
    """
    seg = np.zeros(n_users, dtype=int)
    if len(train) == 0:
        return seg
    g = train.groupby("user")
    counts = g.size()
    skew = g["timestamp"].apply(
        lambda t: 0.5 if t.max() == t.min()
        else float((t > (t.min() + t.max()) / 2).mean())
    )
    c_med = counts.median()
    s_med = skew.median()
    for u in counts.index:
        heavy = int(counts[u] > c_med)
        recency = int(skew[u] > s_med)
        seg[u] = heavy * 2 + recency
    return seg


def segment_shapley_profiles(per_user_phi: dict[str, np.ndarray], users: list[int],
                             segments: np.ndarray) -> dict[str, dict[str, float]]:
    """Mean per-user Shapley value within each segment (C4)."""
    out = {}
    u_seg = np.array([segments[u] for u in users])
    for s in range(len(SEGMENT_NAMES)):
        mask = u_seg == s
        out[SEGMENT_NAMES[s]] = {
            g: float(v[mask].mean()) if mask.any() else 0.0
            for g, v in per_user_phi.items()
        }
        out[SEGMENT_NAMES[s]]["n_users"] = int(mask.sum())
    return out


# --------------------------------------------------------------------------- #
# Fusion variants (spec §7 recommender baselines + C5)
# --------------------------------------------------------------------------- #


def _fit_ridge(feat: dict[int, np.ndarray], candidates: list[np.ndarray],
               targets: dict[int, int], users: list[int], lam: float,
               n_src: int) -> np.ndarray:
    X_parts, y_parts = [], []
    for u in users:
        if u not in feat:
            continue
        X_parts.append(feat[u])
        y_parts.append((candidates[u] == targets[u]).astype(float))
    if not X_parts:
        return np.ones(n_src) / n_src
    X, y = np.vstack(X_parts), np.concatenate(y_parts)
    return np.linalg.solve(X.T @ X + lam * np.eye(n_src), X.T @ y)


def evaluate_weights(feat: dict[int, np.ndarray], candidates: list[np.ndarray],
                     test_items: dict[int, int], users: list[int],
                     w_of_user, k: int = 10) -> np.ndarray:
    """Per-user NDCG@k under a (possibly user-dependent) weight vector."""
    out = np.zeros(len(users))
    for i, u in enumerate(users):
        s = feat[u] @ w_of_user(u)
        order = np.lexsort((candidates[u], -s))
        out[i] = ndcg_at_k(candidates[u][order], test_items[u], k)
    return out


def signalshap_fuse_v2(game, segments: np.ndarray, lam: float = 1.0, seed: int = 42) -> dict:
    """C5 with head + shrinkage selected on the VALIDATION fold (spec §2.4).

    The v1 head (plain per-segment ridge) is retained below for comparison.
    Selection uses cross-validation inside the validation fold only; test data
    is never consulted, so a win here is a real win and a loss is a real loss.
    """
    from ..fusion.heads import (fit_pairwise_logistic, fit_ridge_head,
                                select_on_validation, shrink)

    n_src = len(game.sources)
    feat, cands = game.feat, game.candidates
    sel = select_on_validation(feat, cands, game.valid_items, game.fit_users,
                               segments, lam, game.k, seed=seed)

    def _design(us):
        Xs, ys, gs = [], [], []
        for u in us:
            y = (cands[u] == game.valid_items[u]).astype(float)
            Xs.append(feat[u]); ys.append(y); gs.append((feat[u], y))
        return (np.vstack(Xs), np.concatenate(ys), gs) if Xs else (None, None, [])

    X, y, groups = _design(game.fit_users)
    if X is None:
        w_global = np.ones(n_src) / n_src
    else:
        w_global = (fit_ridge_head(X, y, lam) if sel["head"] == "ridge"
                    else fit_pairwise_logistic(groups, lam, seed=seed))

    w_seg = {}
    for s in range(len(SEGMENT_NAMES)):
        mem = [u for u in game.fit_users if segments[u] == s]
        if len(mem) < 10:
            w_seg[s] = w_global
            continue
        Xs, ys, gs = _design(mem)
        raw = (fit_ridge_head(Xs, ys, lam) if sel["head"] == "ridge"
               else fit_pairwise_logistic(gs, lam, seed=seed))
        w_seg[s] = shrink(raw, w_global, sel["alpha"])

    users = game.eval_users
    w_uniform = np.ones(n_src) / n_src
    return {
        "uniform": evaluate_weights(feat, cands, game.test_items, users,
                                    lambda u: w_uniform, game.k),
        "global": evaluate_weights(feat, cands, game.test_items, users,
                                   lambda u: w_global, game.k),
        "signalshap_fuse": evaluate_weights(feat, cands, game.test_items, users,
                                            lambda u: w_seg[segments[u]], game.k),
        "weights": {"uniform": w_uniform.tolist(), "global": w_global.tolist(),
                    **{f"segment_{SEGMENT_NAMES[s]}": w.tolist() for s, w in w_seg.items()}},
        "selection": sel, "sources": list(game.sources), "users": users,
    }


def signalshap_fuse(game, segments: np.ndarray, lam: float = 1.0) -> dict:
    """C5: segment-adaptive fusion, compared against uniform and global.

    Returns per-user NDCG@10 arrays for each variant so downstream paired tests
    (Wilcoxon + d_z) operate on the user as the unit of analysis (spec §11).
    """
    n_src = len(game.sources)
    users = game.eval_users
    feat, cands = game.feat, game.candidates

    w_uniform = np.ones(n_src) / n_src
    w_global = _fit_ridge(feat, cands, game.valid_items, game.fit_users, lam, n_src)

    w_seg = {}
    for s in range(len(SEGMENT_NAMES)):
        members = [u for u in game.fit_users if segments[u] == s]
        w_seg[s] = _fit_ridge(feat, cands, game.valid_items, members, lam, n_src) \
            if len(members) >= 10 else w_global

    return {
        "uniform": evaluate_weights(feat, cands, game.test_items, users,
                                    lambda u: w_uniform, game.k),
        "global": evaluate_weights(feat, cands, game.test_items, users,
                                   lambda u: w_global, game.k),
        "signalshap_fuse": evaluate_weights(feat, cands, game.test_items, users,
                                            lambda u: w_seg[segments[u]], game.k),
        "weights": {
            "uniform": w_uniform.tolist(),
            "global": w_global.tolist(),
            **{f"segment_{SEGMENT_NAMES[s]}": w.tolist() for s, w in w_seg.items()},
        },
        "sources": list(game.sources),
        "users": users,
    }
