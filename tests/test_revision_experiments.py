"""Tests for the experiments added in response to review."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from signalshap.attribution.values import (  # noqa: E402
    banzhaf_value, semivalue, shapley_taylor_interaction)
from signalshap.experiments.synthetic_games import validate_implementation  # noqa: E402
from signalshap.game.core import exact_shapley  # noqa: E402


def test_analytic_games_reproduce_exactly():
    """Magnitude validation: six closed-form Shapley vectors must match.

    Stronger than the symmetry diagnostic, which an exact implementation
    satisfies by construction. These include null and harmful players.
    """
    r = validate_implementation()
    assert r["_summary"]["all_pass"], {
        k: v for k, v in r.items() if not k.startswith("_") and not v["passes"]}
    assert r["_summary"]["worst_error"] < 1e-12


def test_semivalue_with_shapley_weights_equals_shapley():
    players = ("a", "b", "c")
    from itertools import combinations
    v = {}
    for k in range(4):
        for c in combinations(players, k):
            S = frozenset(c)
            v[S] = len(S) ** 2  # arbitrary superadditive game
    n = len(players)
    got = semivalue(v, {k: 1.0 / n for k in range(n)}, players)
    want = exact_shapley(v, players)
    for g in players:
        assert abs(got[g] - want[g]) < 1e-12


def test_banzhaf_differs_from_shapley_but_shares_symmetry():
    players = ("a", "b", "c")
    from itertools import combinations
    v = {}
    for k in range(4):
        for c in combinations(players, k):
            S = frozenset(c)
            v[S] = 1.0 if "a" in S else 0.0   # a is a dictator
    b = banzhaf_value(v, players)
    s = exact_shapley(v, players)
    assert abs(b["b"]) < 1e-12 and abs(b["c"]) < 1e-12, "dummies get zero"
    assert abs(s["b"]) < 1e-12 and abs(s["c"]) < 1e-12
    assert b["a"] == pytest.approx(1.0)


def test_interaction_index_detects_redundancy_and_synergy():
    """Negative pairwise index = redundancy; positive = complementarity."""
    from itertools import combinations
    players = ("a", "b")

    sub = {}
    for k in range(3):
        for c in combinations(players, k):
            S = frozenset(c)
            sub[S] = 1.0 if S else 0.0        # either alone suffices
    assert shapley_taylor_interaction(sub, players)["a|b"] < 0

    comp = {}
    for k in range(3):
        for c in combinations(players, k):
            S = frozenset(c)
            comp[S] = 1.0 if len(S) == 2 else 0.0   # need both
    assert shapley_taylor_interaction(comp, players)["a|b"] > 0


def test_fixed_head_game_does_not_refit():
    from signalshap.experiments.estimands import FixedHeadGame
    import inspect
    src = inspect.getsource(FixedHeadGame._fit_weights)
    assert "_grand_w" in src, "fixed head must cache the grand-coalition head"


def test_shapley_to_weights_is_a_simplex():
    from signalshap.fusion.heads import shapley_to_weights
    srcs = ("cf", "ct", "pop", "rec", "seq")
    phi = {"cf": 0.015, "ct": -0.002, "pop": 0.006, "rec": 0.0, "seq": 0.03}
    w = shapley_to_weights(phi, srcs, tau=0.01, rho=0.0)
    assert np.all(w >= 0), "negative weights would invert a source's scores"
    assert w.sum() == pytest.approx(1.0)
    assert srcs[int(np.argmax(w))] == "seq"


def test_hierarchical_bootstrap_is_wider_than_naive():
    """Two-level resampling must not understate uncertainty."""
    from signalshap.stats.tests import hierarchical_bootstrap, bootstrap_ci
    rng = np.random.default_rng(0)
    # a real seed effect: each seed shifted differently
    a = {s: rng.normal(0.06 + 0.01 * i, 0.05, 400) for i, s in enumerate((42, 43, 44))}
    b = {s: rng.normal(0.06, 0.05, 400) for s in (42, 43, 44)}
    h = hierarchical_bootstrap(a, b, n_boot=1500, seed=1)
    pooled = np.concatenate([a[s] - b[s] for s in a])
    naive = bootstrap_ci(pooled, n_boot=1500, seed=1)
    assert (h["hi"] - h["lo"]) > (naive["hi"] - naive["lo"]), (
        "hierarchical interval should be wider when a seed effect exists")


def test_tost_declares_equivalence_for_a_null_effect():
    from signalshap.stats.tests import tost_equivalence
    rng = np.random.default_rng(0)
    x = rng.normal(0.06, 0.01, 3000)
    y = x + rng.normal(0, 1e-4, 3000)
    assert tost_equivalence(x, y, margin=0.005)["equivalent"]
