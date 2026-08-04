"""Games with analytically known Shapley vectors (review Issue: ground truth).

The duplicate-injection diagnostic verifies symmetry, which an exact
implementation satisfies by construction. The reviewer correctly noted that
this is necessary but weak: it says nothing about whether the *magnitudes* are
right, because no absolute ground truth was available.

Here we supply one. These games have closed-form Shapley vectors derivable by
hand, covering the structures the paper cares about:

    additive      independent sources, phi_g = v({g})
    substitutes   perfect redundancy
    complements   value only when paired
    null          a source contributing exactly nothing
    harmful       a source with strictly negative contribution
    threshold     a unanimity game, phi_g = v(G)/n

Any correct implementation must reproduce all six exactly. Unlike symmetry,
these can fail in a way that reveals a real bug.
"""

from __future__ import annotations

from fractions import Fraction as F
from itertools import combinations


def _lattice(players):
    for k in range(len(players) + 1):
        yield from (frozenset(c) for c in combinations(players, k))


# --------------------------------------------------------------------------- #
# Game constructors, each paired with its analytic Shapley vector
# --------------------------------------------------------------------------- #


def additive_game(contribs: dict[str, F]) -> tuple[dict, dict]:
    """v(S) = sum of member contributions. Shapley = the contributions."""
    players = tuple(contribs)
    v = {S: sum(contribs[g] for g in S) for S in _lattice(players)}
    return v, dict(contribs)


def substitutes_game(pair_value: F, others: dict[str, F]) -> tuple[dict, dict]:
    """Two perfect substitutes plus independent others.

    v gains `pair_value` if EITHER substitute is present. By symmetry each
    receives pair_value/2, since the pair jointly forms a unanimity-like block
    over the "at least one present" event.
    """
    players = ("s1", "s2") + tuple(others)
    v = {}
    for S in _lattice(players):
        val = pair_value if ("s1" in S or "s2" in S) else F(0)
        val += sum(others[g] for g in S if g in others)
        v[S] = val
    exact = {"s1": pair_value / 2, "s2": pair_value / 2, **others}
    return v, exact


def complements_game(joint: F, singles: dict[str, F]) -> tuple[dict, dict]:
    """Two sources that pay `joint` only together, plus independent others.

    For the complementary pair the marginal is `joint` only when the partner is
    already present, which happens in half of all orderings, so each receives
    joint/2 on top of its standalone value.
    """
    players = ("c1", "c2") + tuple(singles)
    v = {}
    for S in _lattice(players):
        val = joint if ("c1" in S and "c2" in S) else F(0)
        val += sum(singles[g] for g in S if g in singles)
        v[S] = val
    exact = {"c1": joint / 2, "c2": joint / 2, **singles}
    return v, exact


def null_player_game(contribs: dict[str, F]) -> tuple[dict, dict]:
    """A dummy source contributing exactly zero in every coalition."""
    v, exact = additive_game(contribs)
    players = tuple(contribs) + ("null",)
    v2 = {}
    for S in _lattice(players):
        v2[S] = sum(contribs[g] for g in S if g in contribs)
    exact2 = {**exact, "null": F(0)}
    return v2, exact2


def harmful_player_game(good: dict[str, F], harm: F) -> tuple[dict, dict]:
    """A source that strictly reduces value wherever it appears."""
    players = tuple(good) + ("bad",)
    v = {}
    for S in _lattice(players):
        val = sum(good[g] for g in S if g in good)
        if "bad" in S:
            val -= harm
        v[S] = val
    return v, {**good, "bad": -harm}


def unanimity_game(players: tuple[str, ...], total: F) -> tuple[dict, dict]:
    """v(S) = total iff S is the grand coalition. Shapley = total/n each."""
    G = frozenset(players)
    v = {S: (total if S == G else F(0)) for S in _lattice(players)}
    return v, {g: total / len(players) for g in players}


# --------------------------------------------------------------------------- #
# Suite
# --------------------------------------------------------------------------- #


def build_suite() -> dict[str, tuple[dict, dict]]:
    """All six games with their exact Shapley vectors, in rationals."""
    return {
        "additive": additive_game({"a": F(3), "b": F(2), "c": F(1)}),
        "substitutes": substitutes_game(F(4), {"x": F(1)}),
        "complements": complements_game(F(6), {"x": F(2)}),
        "null_player": null_player_game({"a": F(3), "b": F(2)}),
        "harmful": harmful_player_game({"a": F(5)}, F(2)),
        "unanimity": unanimity_game(("p", "q", "r"), F(9)),
    }


def validate_implementation(tol: float = 1e-12) -> dict:
    """Check the production estimator against every analytic vector.

    Unlike the symmetry diagnostic, a failure here is unambiguous: the
    implementation returned a magnitude that provably differs from the closed
    form.
    """
    from ..game.core import exact_shapley

    results = {}
    for name, (v, exact) in build_suite().items():
        players = tuple(sorted({p for S in v for p in S}))
        vf = {S: float(x) for S, x in v.items()}
        got = exact_shapley(vf, players)
        errs = {g: abs(got[g] - float(exact[g])) for g in players}
        results[name] = {
            "players": list(players),
            "expected": {g: str(exact[g]) for g in players},
            "computed": {g: round(got[g], 12) for g in players},
            "max_abs_error": max(errs.values()),
            "passes": max(errs.values()) < tol,
            "efficiency_error": abs(sum(got.values()) - vf[frozenset(players)]),
        }
    results["_summary"] = {
        "n_games": len(build_suite()),
        "all_pass": all(r["passes"] for k, r in results.items()
                        if not k.startswith("_")),
        "worst_error": max(r["max_abs_error"] for k, r in results.items()
                           if not k.startswith("_")),
    }
    return results
