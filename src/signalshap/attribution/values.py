"""Alternative cooperative values and interaction indices (review Issue #8).

Shapley uniqueness holds *once a game is fixed*, and it does not select the
game or the value. A reviewer is entitled to ask whether the reported source
ranking is an artefact of choosing Shapley in particular. This module supplies
the comparators needed to answer that:

  * **Banzhaf value** -- uniform weight over coalitions rather than over
    permutations; satisfies symmetry and dummy, but not efficiency.
  * **Weighted semivalues** -- the family containing both, parameterised by a
    distribution over coalition sizes. Note that the SIZE-UNIFORM member,
    p_k = 1/n, IS the Shapley value: Shapley's permutation weight
    |S|!(n-|S|-1)!/n! equals (1/n) / C(n-1,|S|), i.e. mass 1/n spread evenly
    over the C(n-1,k) coalitions of each size. An earlier version of this
    module and of the manuscript reported it as a distinct comparator; a
    reviewer caught that, and the artefact confirmed it numerically (max
    |phi - psi| = 0.0 on every source). The distinct comparators are now the
    binomial semivalues p ~ Bin(n-1, q) with q != 0.5 alongside Banzhaf
    (q = 0.5).
  * **Shapley interaction index** (Grabisch-Roubens, order 2) -- pairwise
    redundancy, which matters here because redundancy is the paper's whole
    motivation and main effects alone cannot express it.

All are exact enumerations over the 2^n lattice, since n = 5.
"""

from __future__ import annotations

from itertools import combinations
from math import comb, factorial

import numpy as np

from ..config import SOURCES


def _subsets(players):
    for k in range(len(players) + 1):
        yield from (frozenset(c) for c in combinations(players, k))


def banzhaf_value(v: dict, sources: tuple[str, ...] = SOURCES) -> dict[str, float]:
    """Banzhaf value: mean marginal contribution over all coalitions.

    Unlike Shapley it weights every coalition equally rather than every
    *permutation*, so it does not satisfy efficiency. Reported precisely to
    show which conclusions survive a change of value.
    """
    n = len(sources)
    out = {}
    for g in sources:
        others = [s for s in sources if s != g]
        total = sum(v[S | {g}] - v[S] for S in _subsets(others))
        out[g] = total / (2 ** (n - 1))
    return out


def semivalue(v: dict, weights: dict[int, float] | None = None,
              sources: tuple[str, ...] = SOURCES) -> dict[str, float]:
    """Weighted semivalue with an explicit distribution over coalition sizes.

    `weights[k]` is the total mass placed on coalitions of size k among the
    n-1 possible predecessors. Shapley uses uniform mass per size; Banzhaf uses
    mass proportional to the number of coalitions of that size.
    """
    n = len(sources)
    if weights is None:  # Shapley
        weights = {k: 1.0 / n for k in range(n)}
    out = {}
    for g in sources:
        others = [s for s in sources if s != g]
        total = 0.0
        for S in _subsets(others):
            k = len(S)
            per = weights.get(k, 0.0) / max(comb(n - 1, k), 1)
            total += per * (v[S | {g}] - v[S])
        out[g] = total
    return out


def binomial_semivalue(v: dict, q: float,
                       sources: tuple[str, ...] = SOURCES) -> dict[str, float]:
    """Binomial (probabilistic) semivalue: each other player joins w.p. q.

    Coalition-size mass p_k = C(n-1,k) q^k (1-q)^(n-1-k). q = 0.5 recovers
    Banzhaf. q != 0.5 gives a value that is genuinely NOT Shapley: small q
    weights small predecessor coalitions, so a source that is valuable alone
    but redundant in company scores higher; large q does the reverse. This is
    the robustness question the size-uniform "semivalue" was supposed to ask
    but could not, because it is Shapley identically.
    """
    n = len(sources)
    pk = {k: comb(n - 1, k) * q ** k * (1.0 - q) ** (n - 1 - k) for k in range(n)}
    return semivalue(v, pk, sources)


def shapley_taylor_interaction(v: dict, sources: tuple[str, ...] = SOURCES,
                               order: int = 2) -> dict[str, float]:
    """Grabisch-Roubens Shapley INTERACTION index, order 2.

    NOT the Shapley-Taylor index, despite the legacy function name. A reviewer
    caught the manuscript citing Shapley-Taylor while this coefficient --
    |S|!(n-|S|-2)!/(n-1)! -- is Grabisch-Roubens. At n=5 the two weightings are
    0.25, 1/12, 1/12, 0.25 here versus 0.4, 0.1, 1/15, 0.1 for Shapley-Taylor,
    differing by up to 2.5x. Both are legitimate interaction indices; only the
    label was wrong. Grabisch-Roubens does not satisfy interaction efficiency,
    so pairwise terms do not sum with singletons to v(G); we use them only to
    rank redundancy. The function name is kept for artefact compatibility.

    For order 2 the pairwise term quantifies whether two sources are
    complementary (positive) or redundant (negative) beyond their main
    effects. This is the natural instrument for the paper's central claim, and
    its absence was a fair criticism: main-effect Shapley values alone cannot
    distinguish redundancy from low individual value.
    """
    n = len(sources)
    out: dict[str, float] = {}

    # Order-1 terms: discrete derivative at the empty set.
    for g in sources:
        out[g] = v[frozenset({g})] - v[frozenset()]

    # Order-2 terms: averaged second-order discrete derivative.
    for a, b in combinations(sources, 2):
        rest = [s for s in sources if s not in (a, b)]
        total = 0.0
        for S in _subsets(rest):
            k = len(S)
            w = factorial(k) * factorial(n - k - order) / factorial(n - order + 1)
            delta = (v[S | {a, b}] - v[S | {a}] - v[S | {b}] + v[S])
            total += w * delta
        out[f"{a}|{b}"] = order * total
    return out


def compare_values(v: dict, sources: tuple[str, ...] = SOURCES) -> dict:
    """Shapley vs Banzhaf vs a size-uniform semivalue, with rank agreement.

    The question this answers is not "which value is right?" but "does the
    engineering conclusion depend on that choice?". If the top-ranked source
    is stable across values, the conclusion is robust to the choice; if it is
    not, the paper must say so.
    """
    from ..game.core import exact_shapley
    from scipy.stats import kendalltau

    n = len(sources)
    shap = exact_shapley(v, sources)
    banz = banzhaf_value(v, sources)
    # p_k = 1/n is Shapley itself, kept only as an implementation check.
    semi_uniform_is_shapley = semivalue(v, {k: 1.0 / n for k in range(n)}, sources)
    semi_lo = binomial_semivalue(v, 0.25, sources)
    semi_hi = binomial_semivalue(v, 0.75, sources)

    order = list(sources)
    s_vec = [shap[g] for g in order]
    b_vec = [banz[g] for g in order]

    tau = kendalltau(s_vec, b_vec).correlation
    return {
        "shapley": shap,
        "banzhaf": banz,
        "semivalue_binomial_q025": semi_lo,
        "semivalue_binomial_q075": semi_hi,
        "semivalue_size_uniform": semi_uniform_is_shapley,
        "size_uniform_equals_shapley_max_abs_diff": float(
            max(abs(semi_uniform_is_shapley[g] - shap[g]) for g in sources)),
        "shapley_top": max(shap, key=shap.get),
        "banzhaf_top": max(banz, key=banz.get),
        "top_source_agrees": max(shap, key=shap.get) == max(banz, key=banz.get),
        "kendall_tau_shapley_banzhaf": float(tau) if np.isfinite(tau) else 0.0,
        "kendall_tau_shapley_q025": float(
            kendalltau(s_vec, [semi_lo[g] for g in order]).correlation),
        "kendall_tau_shapley_q075": float(
            kendalltau(s_vec, [semi_hi[g] for g in order]).correlation),
        "top_source_all_values": sorted({
            max(d, key=d.get) for d in (shap, banz, semi_lo, semi_hi)}),
        "sums": {k: float(sum(d.values())) for k, d in
                 (("shapley", shap), ("banzhaf", banz),
                  ("q025", semi_lo), ("q075", semi_hi))},
        "note": (
            "Banzhaf does not satisfy efficiency, so its values do not sum to "
            "v(G); only the induced ORDERING is comparable across values. The "
            "size-uniform semivalue is Shapley identically (see the diff key), "
            "so the distinct comparators are Banzhaf and the binomial "
            "semivalues at q = 0.25 and q = 0.75."
        ),
    }
