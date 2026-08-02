"""Pins the necessity of the monotonicity hypothesis in Property 2 (spec v1.1.2, §5).

v1.1.1 stated Property 2 as:

    If v(S u {g1}) = v(S u {g2}) = v(S u {g1,g2}) for every S subseteq G \\ {g1,g2},
    then LOO(g1) = LOO(g2) = 0 while phi_g1 = phi_g2 > 0 whenever v({g1}) > 0.

That statement is FALSE. This module encodes a three-player counterexample that
satisfies every hypothesis and still yields phi_g1 = phi_g2 < 0, and asserts that
adding monotonicity repairs it. The tests exist so the assumption is enforced by
CI rather than by prose.
"""

from __future__ import annotations

from itertools import combinations
from math import factorial, isclose

import pytest

# --------------------------------------------------------------------------- #
# Exact Shapley over the full coalition lattice (no sampling).
# --------------------------------------------------------------------------- #


def powerset(players):
    for k in range(len(players) + 1):
        yield from (frozenset(c) for c in combinations(players, k))


def shapley(players, v):
    """Exact Shapley values via the closed-form weighted-marginal sum."""
    n = len(players)
    phi = {}
    for g in players:
        others = [p for p in players if p != g]
        total = 0.0
        for S in powerset(others):
            w = factorial(len(S)) * factorial(n - len(S) - 1) / factorial(n)
            total += w * (v[S | {g}] - v[S])
        phi[g] = total
    return phi


def loo(players, v):
    grand = frozenset(players)
    return {g: v[grand] - v[grand - {g}] for g in players}


def is_monotone(players, v):
    """v(S u {g}) >= v(S) for every S and every g not in S."""
    return all(
        v[S | {g}] >= v[S] - 1e-12
        for S in powerset(players)
        for g in players
        if g not in S
    )


def is_exactly_redundant(players, v, g1, g2):
    """v(S u {g1}) = v(S u {g2}) = v(S u {g1,g2}) for all S in G \\ {g1,g2}."""
    rest = [p for p in players if p not in (g1, g2)]
    return all(
        isclose(v[S | {g1}], v[S | {g2}], abs_tol=1e-12)
        and isclose(v[S | {g1}], v[S | {g1, g2}], abs_tol=1e-12)
        for S in powerset(rest)
    )


# --------------------------------------------------------------------------- #
# The counterexample (spec v1.1.2, §5 and Appendix A).
# --------------------------------------------------------------------------- #

PLAYERS = ("g1", "g2", "g3")

# g1 and g2 are exactly redundant; v({g1}) = 1 > 0; v is NOT monotone
# (adding g3 to {g1} drops 1.0 -> 0.5, and the grand coalition is worse than {g3}).
NON_MONOTONE_V = {
    frozenset(): 0.0,
    frozenset({"g1"}): 1.0,
    frozenset({"g2"}): 1.0,
    frozenset({"g3"}): 5.0,
    frozenset({"g1", "g2"}): 1.0,
    frozenset({"g1", "g3"}): 0.5,
    frozenset({"g2", "g3"}): 0.5,
    frozenset({"g1", "g2", "g3"}): 0.5,
}

# Same redundancy structure, but monotone: Property 2 should now hold.
MONOTONE_V = {
    frozenset(): 0.0,
    frozenset({"g1"}): 1.0,
    frozenset({"g2"}): 1.0,
    frozenset({"g3"}): 5.0,
    frozenset({"g1", "g2"}): 1.0,
    frozenset({"g1", "g3"}): 5.5,
    frozenset({"g2", "g3"}): 5.5,
    frozenset({"g1", "g2", "g3"}): 5.5,
}


def test_counterexample_satisfies_v1_1_1_hypotheses():
    """The hypotheses of the v1.1.1 statement all hold on this game."""
    assert is_exactly_redundant(PLAYERS, NON_MONOTONE_V, "g1", "g2")
    assert NON_MONOTONE_V[frozenset({"g1"})] > 0
    assert NON_MONOTONE_V[frozenset()] == 0.0


def test_loo_collapses_as_predicted():
    """LOO does collapse to zero for both redundant sources -- that part was right."""
    l = loo(PLAYERS, NON_MONOTONE_V)
    assert isclose(l["g1"], 0.0, abs_tol=1e-12)
    assert isclose(l["g2"], 0.0, abs_tol=1e-12)


def test_v1_1_1_property2_conclusion_is_false():
    """Redundancy + v({g1}) > 0 does NOT imply phi_g1 > 0. This is the whole point."""
    phi = shapley(PLAYERS, NON_MONOTONE_V)
    assert isclose(phi["g1"], -5 / 12, abs_tol=1e-12)  # -0.41666...
    assert isclose(phi["g2"], -5 / 12, abs_tol=1e-12)
    assert isclose(phi["g3"], 4 / 3, abs_tol=1e-12)
    assert phi["g1"] < 0, "counterexample no longer refutes the v1.1.1 statement"


def test_symmetry_and_efficiency_still_hold():
    """The failure is not a broken Shapley implementation: the axioms are intact."""
    phi = shapley(PLAYERS, NON_MONOTONE_V)
    assert isclose(phi["g1"], phi["g2"], abs_tol=1e-12)  # symmetry
    assert isclose(
        sum(phi.values()), NON_MONOTONE_V[frozenset(PLAYERS)], abs_tol=1e-12
    )  # efficiency


def test_game_is_not_monotone():
    """The missing hypothesis, isolated."""
    assert not is_monotone(PLAYERS, NON_MONOTONE_V)


def test_monotonicity_repairs_property2():
    """v1.1.2's corrected Property 2: monotone + redundant => phi >= v({g1})/|G| > 0."""
    assert is_monotone(PLAYERS, MONOTONE_V)
    assert is_exactly_redundant(PLAYERS, MONOTONE_V, "g1", "g2")

    l = loo(PLAYERS, MONOTONE_V)
    assert isclose(l["g1"], 0.0, abs_tol=1e-12)
    assert isclose(l["g2"], 0.0, abs_tol=1e-12)

    phi = shapley(PLAYERS, MONOTONE_V)
    floor = MONOTONE_V[frozenset({"g1"})] / len(PLAYERS)
    assert phi["g1"] > 0
    assert phi["g1"] >= floor - 1e-12, "Shapley floor phi >= v({g1})/|G| violated"
    assert isclose(phi["g1"], phi["g2"], abs_tol=1e-12)
    assert isclose(sum(phi.values()), MONOTONE_V[frozenset(PLAYERS)], abs_tol=1e-12)


# --------------------------------------------------------------------------- #
# E0-b: the audit that must run against the real fitted game (spec §11).
# --------------------------------------------------------------------------- #


def monotonicity_violations(players, v):
    """Every (S, g) pair with g not in S where v(S u {g}) < v(S).

    Against the real five-source game this enumerates |G| * 2^(|G|-1) = 80 pairs.
    Wire this into E0-b and report count / max magnitude / sources in T2.
    """
    out = []
    for S in powerset(players):
        for g in players:
            if g in S:
                continue
            delta = v[S | {g}] - v[S]
            if delta < 0:
                out.append((tuple(sorted(S)), g, delta))
    return out


def test_audit_helper_counts_all_pairs():
    n = len(PLAYERS)
    checked = sum(1 for S in powerset(PLAYERS) for g in PLAYERS if g not in S)
    assert checked == n * 2 ** (n - 1) == 12  # 80 for the real five-player game

    violations = monotonicity_violations(PLAYERS, NON_MONOTONE_V)
    assert violations, "non-monotone game must report violations"
    assert not monotonicity_violations(PLAYERS, MONOTONE_V)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))


# --------------------------------------------------------------------------- #
# Regression guards against two wrong formulas seen in a parallel draft.
# Both look plausible and both fail on the counterexample above. Keep these
# green so neither can be reintroduced into §5.
# --------------------------------------------------------------------------- #


def test_pairwise_closed_form_is_wrong():
    """REJECTED: phi_g1 = 1/2 [v(G) - v(G \\ {g1,g2})].

    Under exact redundancy this is not a valid closed form. It ignores every
    coalition structure below the grand coalition and is off by 5.4x here.
    """
    G = frozenset(PLAYERS)
    bogus = 0.5 * (NON_MONOTONE_V[G] - NON_MONOTONE_V[G - {"g1", "g2"}])
    true = shapley(PLAYERS, NON_MONOTONE_V)["g1"]

    assert bogus == pytest.approx(-2.25)
    assert true == pytest.approx(-5 / 12)
    assert bogus != pytest.approx(true), "the rejected closed form must not be adopted"


def test_shapley_floor_constant_is_one_over_n_not_one_half():
    """REJECTED: phi_g1 >= 1/2 v({g1}). The correct anchor constant is 1/|G|.

    The weights over T subseteq G \\ {g1,g2} sum to 1/2 -- that is P(g1 precedes
    g2) in a random ordering -- but the term carrying the v({g1}) anchor is
    |T| = 0, whose weight is 1/n. Conflating the two overstates the bound by
    n/2 (2.5x for the five-player game).
    """
    from fractions import Fraction as Frac

    for n in (3, 5, 8):
        # total mass on coalitions T excluding both g1 and g2
        mass = sum(
            Frac(factorial(t) * factorial(n - t - 1), factorial(n))
            * len(list(combinations(range(n - 2), t)))
            for t in range(n - 1)
        )
        w_empty = Frac(factorial(0) * factorial(n - 1), factorial(n))

        assert mass == Frac(1, 2), "mass over T should be 1/2 for every n"
        assert w_empty == Frac(1, n), "anchor weight should be 1/n"
        if n != 2:
            assert mass != w_empty, "1/2 and 1/n are different quantities"

    # The bound the spec states is the one that survives on a monotone game.
    phi = shapley(PLAYERS, MONOTONE_V)
    v_g1 = MONOTONE_V[frozenset({"g1"})]
    assert phi["g1"] >= v_g1 / len(PLAYERS) - 1e-12  # correct: v({g1})/|G|
    assert phi["g1"] < 0.5 * v_g1, "the 1/2 constant is not attainable here"
