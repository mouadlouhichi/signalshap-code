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


# --------------------------------------------------------------------------- #
# Timestamp handling (found while fetching real corpora)
# --------------------------------------------------------------------------- #


def test_epoch_conversion_is_resolution_independent():
    """pandas 2.x may parse to datetime64[s|ms|us], not always [ns].

    The common idiom `.astype("int64") // 10**9` silently under-reports by
    1000x on a [us] column: the result still looks like a plausible epoch
    integer, so nothing raises, but every recency and time-decay computation
    downstream is wrong. This pins the fix.
    """
    import pandas as pd
    from signalshap.data.timestamped import _to_epoch_seconds

    want = 1287532527  # 2010-10-19T23:55:27Z
    for raw in ("2010-10-19T23:55:27Z", "2010-10-19 23:55:27"):
        got = int(_to_epoch_seconds(pd.Series([raw])).iloc[0])
        assert got == want, f"{raw}: got {got}, want {want}"


def test_implausible_epoch_is_rejected():
    """A resolution mismatch must fail loudly rather than corrupt `rec`."""
    import pandas as pd
    import pytest as _pt
    from signalshap.data.timestamped import _prepare

    bad = pd.DataFrame({
        "user": [0, 0, 1, 1] * 3,
        "item": [1, 2, 1, 2] * 3,
        # 1287532 seconds = 1970, the symptom of dividing [us] by 1e9
        "timestamp": list(range(1287532, 1287544)),
    })
    with _pt.raises(ValueError, match="plausible Unix-seconds"):
        _prepare(bad, "probe", None, 42)


def test_temporal_validity_rejects_positional_index():
    """The failure that produced the withdrawn results must stay detectable."""
    from signalshap.data.loaders import make_synthetic
    from signalshap.data.timestamped import temporal_validity_report

    ds = make_synthetic("probe", 120, 200, 0.03, seed=1)
    for fold in ("train", "valid", "test"):
        d = getattr(ds, fold).copy()
        d["timestamp"] = d["original_record_index"]
        setattr(ds, fold, d)
    rep = temporal_validity_report(ds)
    assert rep["looks_like_positional_index"] or not rep["temporally_valid"]
