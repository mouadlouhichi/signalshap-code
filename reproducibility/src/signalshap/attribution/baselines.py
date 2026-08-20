"""Attribution baselines (spec §7): LOO, forward selection, permutation, MC Shapley.

LOO is the industry default and the direct target of Property 2 -- it collapses
to zero for redundant sources while the Shapley value stays positive (given
monotonicity).
"""

from __future__ import annotations

from itertools import combinations
from math import factorial

import numpy as np

from ..config import SOURCES
from ..game.core import all_coalitions, shapley_weight


def loo_attribution(v: dict[frozenset, float], sources: tuple[str, ...] = SOURCES) -> dict[str, float]:
    """LOO(g) = v(G) - v(G \\ {g}). Zero for exactly-redundant sources."""
    G = frozenset(sources)
    return {g: v[G] - v[G - {g}] for g in sources}


def forward_selection(v: dict[frozenset, float], sources: tuple[str, ...] = SOURCES) -> dict[str, float]:
    """Greedy forward stepwise: credit = marginal gain when first selected."""
    cur, out = frozenset(), {}
    remaining = set(sources)
    while remaining:
        best_g = max(remaining, key=lambda g: v[cur | {g}] - v[cur])
        out[best_g] = v[cur | {best_g}] - v[cur]
        cur = cur | {best_g}
        remaining.discard(best_g)
    return out


def permutation_importance(v: dict[frozenset, float], sources: tuple[str, ...] = SOURCES,
                           seed: int = 42, n_perm: int = 200) -> dict[str, float]:
    """Mean marginal contribution over random orderings (all orderings if few)."""
    n = len(sources)
    rng = np.random.default_rng(seed)
    acc = {g: [] for g in sources}
    for _ in range(n_perm):
        order = list(rng.permutation(list(sources)))
        cur = frozenset()
        for g in order:
            acc[g].append(v[cur | {g}] - v[cur])
            cur = cur | {g}
    return {g: float(np.mean(x)) for g, x in acc.items()}


def mc_shapley(v: dict[frozenset, float], sources: tuple[str, ...] = SOURCES,
               n_perm: int = 50, seed: int = 42) -> dict[str, float]:
    """Monte-Carlo Shapley at a matched budget (spec §7, §10-E5).

    Reported as a CORRECTNESS claim: with five players the exact computation is
    both error-free and cheaper, so sampling buys nothing here.
    """
    rng = np.random.default_rng(seed)
    acc = {g: 0.0 for g in sources}
    for _ in range(n_perm):
        order = list(rng.permutation(list(sources)))
        cur = frozenset()
        for g in order:
            acc[g] += v[cur | {g}] - v[cur]
            cur = cur | {g}
    return {g: x / n_perm for g, x in acc.items()}


def redundancy_kendall_tau(scores: dict[str, np.ndarray], candidates: list[np.ndarray],
                           users: list[int], sources: tuple[str, ...] = SOURCES,
                           max_users: int = 300) -> dict[str, float]:
    """Mean per-user Kendall tau between source score vectors over C_u.

    Quantifies the redundancy that Lemma 1 links to the LOO-Shapley gap. The
    pop-cf and rec-ct pairs are PRE-REGISTERED to score high (spec §4).
    """
    from scipy.stats import kendalltau

    out = {}
    sample = users[:max_users]
    for a, b in combinations(sources, 2):
        vals = []
        for u in sample:
            c = candidates[u]
            if len(c) < 3:
                continue
            x, y = scores[a][u][c], scores[b][u][c]
            if np.std(x) < 1e-12 or np.std(y) < 1e-12:
                continue
            t = kendalltau(x, y).correlation
            if np.isfinite(t):
                vals.append(t)
        out[f"{a}|{b}"] = float(np.mean(vals)) if vals else 0.0
    return out


def ablate_source(v: dict[frozenset, float], drop: str,
                  sources: tuple[str, ...] = SOURCES) -> dict[str, float]:
    """E6: drop a source and recompute Shapley over the remaining four."""
    kept = tuple(g for g in sources if g != drop)
    n = len(kept)
    phi = {}
    for g in kept:
        others = [s for s in kept if s != g]
        total = 0.0
        for k in range(len(others) + 1):
            for c in combinations(others, k):
                S = frozenset(c)
                total += shapley_weight(len(S), n) * (v[S | {g}] - v[S])
        phi[g] = total
    return phi
