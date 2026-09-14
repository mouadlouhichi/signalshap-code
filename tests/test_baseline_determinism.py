"""The empty-coalition baseline must be reproducible across environments.

Two machines running identical code, identical config, the same seed and
byte-identical candidate sets produced v0 = 0.005033 and 0.006731. The cause
was `np.random.default_rng(seed).permutation(...)`: NumPy guarantees Generator
reproducibility only within a version series. Because v0 is subtracted from
every coalition value, this moved v(G) from 0.05253 to 0.05030, pushed phi_ct
across zero, and changed the monotonicity count from 16/80 to 23/80.

The baseline is now derived by hashing (seed, user, item).
"""

from __future__ import annotations

import numpy as np
import pytest

from signalshap.game.core import _hash_permute, monotonicity_audit


def test_permutation_is_deterministic():
    c = np.array([10, 20, 30, 40, 50])
    assert np.array_equal(_hash_permute(c, 42, 7), _hash_permute(c, 42, 7))


def test_permutation_is_a_permutation():
    c = np.arange(100) * 3 + 7
    out = _hash_permute(c, 42, 0)
    assert sorted(out.tolist()) == sorted(c.tolist())


def test_permutation_does_not_depend_on_input_order():
    """The old code advanced one Generator inside the user loop.

    Each user's permutation therefore depended on how many users preceded it,
    so any change to eval_users membership silently reshuffled the baseline for
    every later user.
    """
    c = np.array([10, 20, 30, 40, 50])
    shuffled = np.array([50, 10, 40, 20, 30])
    assert np.array_equal(_hash_permute(c, 42, 7), _hash_permute(shuffled, 42, 7))


def test_permutation_varies_with_user_and_seed():
    c = np.arange(50)
    base = _hash_permute(c, 42, 7)
    assert not np.array_equal(base, _hash_permute(c, 42, 8))
    assert not np.array_equal(base, _hash_permute(c, 43, 7))


def test_permutation_does_not_use_numpy_rng():
    """Pin the fix: seeding NumPy differently must not move the baseline."""
    c = np.arange(200)
    np.random.seed(1)
    a = _hash_permute(c, 42, 3)
    np.random.seed(999)
    _ = np.random.default_rng(7).permutation(500)      # perturb global state
    b = _hash_permute(c, 42, 3)
    assert np.array_equal(a, b)


def test_permutation_is_roughly_uniform():
    """A degenerate 'permutation' (e.g. identity) would also be deterministic."""
    first = [int(_hash_permute(np.arange(5), 42, u)[0]) for u in range(2000)]
    counts = [first.count(i) for i in range(5)]
    assert min(counts) > 300 and max(counts) < 500, counts


# --------------------------------------------------------------------------- #
# monotonicity stratification
# --------------------------------------------------------------------------- #


def _game(deltas):
    """Minimal 2-player game whose (S,g) marginals include the given values."""
    a, b = "cf", "ct"
    v = {frozenset(): 0.0, frozenset({a}): deltas[0], frozenset({b}): deltas[1],
         frozenset({a, b}): deltas[2]}
    return v, (a, b)


def test_audit_stratifies_by_magnitude():
    v, srcs = _game([-1e-5, 0.5, 0.4])       # one tiny, one large violation
    out = monotonicity_audit(v, srcs)
    s = out["violations_by_magnitude"]
    assert s["gt_0"] == out["violations"]
    assert s["gt_0.0001"] <= s["gt_0"]
    assert s["gt_0.001"] <= s["gt_0.0001"]


def test_material_count_ignores_negligible_violations():
    """The statistic the Property 2 argument actually depends on."""
    v, srcs = _game([-1e-9, 0.5, 0.5])
    out = monotonicity_audit(v, srcs)
    assert out["violations"] >= 1          # the raw count sees it
    assert out["violations_material"] == 0  # the material one does not


def test_monotone_game_reports_zero_and_applicable():
    v, srcs = _game([0.3, 0.2, 0.6])
    out = monotonicity_audit(v, srcs)
    assert out["violations"] == 0
    assert out["violations_material"] == 0
    assert out["property2_applicable"] is True


# --------------------------------------------------------------------------- #
# Baseline sensitivity (reviewer-derived). The manuscript once claimed phi is
# invariant to the empty-coalition baseline. It is not, and both reviewers
# reconstructed the mechanism from the published tables alone.
# --------------------------------------------------------------------------- #


def _toy_game(baseline_shift: float):
    """5-player game where the empty coalition is PINNED at 0.

    This is Eq. (2): v_u(empty) = 0 exactly, while every non-empty coalition
    carries -b_u. The empty set is therefore the one coalition the baseline
    does not move.
    """
    import random
    from itertools import combinations

    S = ("a", "b", "c", "d", "e")
    rng = random.Random(7)
    raw = {frozenset(c): rng.random()
           for k in range(6) for c in combinations(S, k)}
    v = {}
    for s, val in raw.items():
        v[s] = 0.0 if not s else val - baseline_shift
    return v, S


def test_shapley_shifts_by_delta_over_n_when_baseline_changes():
    """The exact mechanism: changing b shifts every phi by -delta/n."""
    from signalshap.game.core import exact_shapley

    v1, S = _toy_game(0.000)
    v2, _ = _toy_game(0.005)
    p1 = exact_shapley(v1, S)
    p2 = exact_shapley(v2, S)
    shifts = [p2[g] - p1[g] for g in S]
    # Uniform across players...
    assert max(shifts) - min(shifts) < 1e-12
    # ...and exactly -delta/n, with n = 5. Raising the baseline by delta
    # lowers every non-empty coalition, so phi falls by delta/n.
    assert abs(shifts[0] + 0.005 / len(S)) < 1e-12


def test_efficiency_survives_a_baseline_change():
    """Sum phi = v(G) regardless, because v(G) shifts with the baseline."""
    from signalshap.game.core import exact_shapley

    for shift in (0.0, 0.005, 0.02):
        v, S = _toy_game(shift)
        phi = exact_shapley(v, S)
        assert abs(sum(phi.values()) - v[frozenset(S)]) < 1e-12


def test_baseline_would_cancel_if_the_empty_coalition_were_also_shifted():
    """Documents the counterfactual, so the fix is not misremembered later.

    If v(empty) carried -b like every other coalition, the baseline WOULD be a
    pure normalisation. It does not, because Eq. (2) pins v_u(empty) = 0 per
    user -- a requirement of Property 3.
    """
    import random
    from itertools import combinations

    from signalshap.game.core import exact_shapley

    S = ("a", "b", "c", "d", "e")
    rng = random.Random(7)
    raw = {frozenset(c): rng.random()
           for k in range(6) for c in combinations(S, k)}
    p1 = exact_shapley({s: val for s, val in raw.items()}, S)
    p2 = exact_shapley({s: val - 0.005 for s, val in raw.items()}, S)
    assert max(abs(p2[g] - p1[g]) for g in S) < 1e-12


def test_interaction_index_is_grabisch_roubens_not_shapley_taylor():
    """The coefficient must match the index the paper now names.

    A reviewer caught the manuscript citing Shapley-Taylor while computing
    Grabisch-Roubens. At n=5 the weights are 0.25, 1/12, 1/12, 0.25 here
    versus 0.4, 0.1, 1/15, 0.1 for Shapley-Taylor -- up to 2.5x apart.
    """
    from math import factorial

    n = 5
    gr = [factorial(t) * factorial(n - t - 2) / factorial(n - 1)
          for t in range(n - 1)]
    st = [2 * factorial(t) * factorial(n - t - 1) / factorial(n)
          for t in range(n - 1)]
    assert gr == pytest.approx([0.25, 1 / 12, 1 / 12, 0.25])
    assert st == pytest.approx([0.4, 0.1, 1 / 15, 0.1])
    assert max(abs(a - b) for a, b in zip(gr, st)) > 0.1, "indices must differ"


# --------------------------------------------------------------------------- #
# Deterministic expected-random baseline (reviewer Critical #2).
# --------------------------------------------------------------------------- #


def test_expected_random_ndcg_matches_closed_form():
    import math

    from signalshap.game.core import expected_random_ndcg

    for n in (5, 200, 600, 3533):
        want = sum(1 / math.log2(r + 1) for r in range(1, min(10, n) + 1)) / n
        assert abs(expected_random_ndcg(n) - want) < 1e-15


def test_expected_baseline_decreases_with_pool_size():
    """A larger candidate pool makes a random hit rarer."""
    from signalshap.game.core import expected_random_ndcg

    vals = [expected_random_ndcg(n) for n in (200, 600, 3533, 11623)]
    assert vals == sorted(vals, reverse=True)


def test_expected_baseline_is_bounded_by_one():
    from signalshap.game.core import expected_random_ndcg

    assert expected_random_ndcg(1) <= 1.0 + 1e-12
    assert expected_random_ndcg(0) == 0.0


def test_expected_baseline_removes_seed_dependence():
    """The whole point: phi must not move when the baseline seed changes.

    Under the sampled baseline this shifted every phi by -delta/n and moved
    phi_ct across zero. Under the expectation there is no draw to vary.
    """
    import inspect

    import numpy as np

    from signalshap.game.core import expected_random_ndcg

    # The signature admits no seed: the value depends only on |C_u| and K.
    assert "seed" not in inspect.signature(expected_random_ndcg).parameters

    # And perturbing global RNG state cannot move it.
    np.random.seed(1)
    a = expected_random_ndcg(600)
    np.random.seed(999)
    _ = np.random.default_rng(7).permutation(500)
    assert expected_random_ndcg(600) == a


def test_game_defaults_to_the_deterministic_baseline():
    import inspect

    from signalshap.game.core import SignalShapGame

    sig = inspect.signature(SignalShapGame.__init__)
    assert sig.parameters["baseline"].default == "expected"


def test_empty_coalition_is_exactly_zero_per_user():
    """Property 3 needs v_u(empty) = 0 for EVERY user, not just on average.

    Regression: the early return in v_per_user was lost in a refactor. The
    empty coalition then fell through to the scoring path with an all-zero
    weight vector, every candidate tied, lexsort ranked by item index, and the
    "empty" coalition scored an arbitrary ranking -- v(empty) = -0.00147 on
    MovieLens instead of 0. That propagated into every reported number and made
    check_efficiency report a 7.4e-04 violation of Property 1. Cost a full
    re-run of all three corpora.
    """
    import numpy as np

    from signalshap.game.core import SignalShapGame

    n_users, n_items = 12, 40
    rng = np.random.default_rng(0)
    scores = {g: rng.normal(size=(n_users, n_items)).astype(np.float32)
              for g in ("cf", "ct", "pop", "rec", "seq")}
    cands = [np.arange(n_items) for _ in range(n_users)]
    items = {u: int(rng.integers(n_items)) for u in range(n_users)}

    g = SignalShapGame(scores, cands, items, items)
    per_user = g.v_per_user(frozenset())
    assert per_user, "no eval users"
    assert all(x == 0.0 for x in per_user.values()), "v_u(empty) must be 0 per user"
    assert g.v(frozenset()) == 0.0


def test_efficiency_holds_on_a_synthetic_game():
    """sum phi must equal v(G) - v(empty), and v(empty) must be 0."""
    import numpy as np

    from signalshap.game.core import (SignalShapGame, check_efficiency,
                                      exact_shapley)

    rng = np.random.default_rng(3)
    n_users, n_items = 15, 50
    scores = {g: rng.normal(size=(n_users, n_items)).astype(np.float32)
              for g in ("cf", "ct", "pop", "rec", "seq")}
    cands = [np.arange(n_items) for _ in range(n_users)]
    items = {u: int(rng.integers(n_items)) for u in range(n_users)}

    g = SignalShapGame(scores, cands, items, items)
    v = g.v_all()
    eff = check_efficiency(exact_shapley(v), v)
    assert eff["passes"], eff
    assert eff["abs_error"] < 1e-12
