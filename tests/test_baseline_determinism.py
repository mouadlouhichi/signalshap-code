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
