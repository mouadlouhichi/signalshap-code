"""Eq. (14): users whose test item is masked out dilute v by a constant factor.

Half of Gowalla's evaluated users have a test venue that already appears in
their own training history. `mask_seen` sets that item to -inf in every
source, so it enters no candidate set, NDCG_u = 0 and b_u = 0 under every
coalition, and therefore v_u(S) = 0 identically for all 32 coalitions.

Because v(S) averages over U_eval, such users are not noise: they are exact
zeros that scale the whole game. Writing rho for the retrievable fraction,

    v(S) = rho * v_live(S)   for every S,

and by linearity of the Shapley operator phi_g = rho * phi_g_live. The paper
depends on this: it is why every Gowalla ORDERING, sign, Kendall tau and
ratio-to-v(G) is exactly invariant to the dilution while every absolute
magnitude is halved. If this identity broke, the Gowalla results would need
requalifying rather than rescaling.
"""
from __future__ import annotations

import numpy as np
import pytest

from signalshap.candidates.builder import build_candidates
from signalshap.config import SOURCES
from signalshap.game.core import SignalShapGame, all_coalitions, exact_shapley


def _split(seed: int, dead_frac: float, n_users: int = 240, n_items: int = 180,
           n_max: int = 40):
    """Build a game plus the same game with the masked users removed."""
    rng = np.random.default_rng(seed)
    scores = {g: rng.normal(size=(n_users, n_items)) for g in SOURCES}
    cands = build_candidates(scores, n_users, n_max)
    valid = {u: int(cands[u][rng.integers(0, len(cands[u]))]) for u in range(n_users)}

    test, dead = {}, set()
    for u in range(n_users):
        if rng.random() < dead_frac:
            # Stand-in for a masked item: present in no candidate set, so the
            # user scores zero under every coalition, exactly as mask_seen does.
            outside = sorted(set(range(n_items)) - set(cands[u].tolist()))
            test[u] = int(outside[0])
            dead.add(u)
        else:
            test[u] = int(cands[u][rng.integers(0, len(cands[u]))])

    full = SignalShapGame(scores, cands, valid, test)
    live = SignalShapGame(scores, cands, valid,
                          {u: i for u, i in test.items() if u not in dead})
    return full, live


@pytest.mark.parametrize("dead_frac", [0.25, 0.499, 0.75])
def test_masked_users_scale_every_coalition_value_by_rho(dead_frac):
    full, live = _split(seed=7, dead_frac=dead_frac)
    rho = len(live.eval_users) / len(full.eval_users)
    assert 0.0 < rho < 1.0

    for S in all_coalitions(SOURCES):
        assert full.v(S) == pytest.approx(rho * live.v(S), abs=1e-15)


def test_shapley_inherits_the_same_factor():
    full, live = _split(seed=11, dead_frac=0.5)
    rho = len(live.eval_users) / len(full.eval_users)
    phi_full = exact_shapley(full.v_all())
    phi_live = exact_shapley(live.v_all())

    for g in SOURCES:
        assert phi_full[g] == pytest.approx(rho * phi_live[g], abs=1e-15)


def test_ordering_and_ratios_are_invariant_but_magnitudes_are_not():
    """The precise reason Gowalla's contrasts are reported and its levels are not."""
    full, live = _split(seed=3, dead_frac=0.6)
    phi_full = exact_shapley(full.v_all())
    phi_live = exact_shapley(live.v_all())
    grand = frozenset(SOURCES)

    # Ordering: identical.
    assert (sorted(SOURCES, key=lambda g: -phi_full[g])
            == sorted(SOURCES, key=lambda g: -phi_live[g]))
    # Signs: identical.
    assert all(np.sign(phi_full[g]) == np.sign(phi_live[g]) for g in SOURCES)
    # Share of v(G): identical, because the factor cancels in the ratio.
    for g in SOURCES:
        assert (phi_full[g] / full.v(grand)
                == pytest.approx(phi_live[g] / live.v(grand), rel=1e-9))
    # Levels: genuinely different, so this is not a vacuous test.
    assert abs(full.v(grand) - live.v(grand)) > 1e-4


def test_a_fully_masked_population_gives_the_zero_game():
    full, _ = _split(seed=5, dead_frac=1.0)
    for S in all_coalitions(SOURCES):
        assert full.v(S) == pytest.approx(0.0, abs=1e-15)
    assert all(v == pytest.approx(0.0, abs=1e-15)
               for v in exact_shapley(full.v_all()).values())
