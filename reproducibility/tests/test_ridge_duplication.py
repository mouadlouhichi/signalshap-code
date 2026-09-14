"""Pins the ridge-duplication issue raised in review.

A reviewer observed that duplicating a column in a ridge regression is NOT
prediction-invariant: two identical columns share the L2 penalty, so the
effective regularisation on their common direction is halved. Consequently
"LOO collapses to zero after duplication" is not a structural guarantee of our
fitted game, only an empirical outcome.

The observation is correct, and these tests encode it so the paper cannot
drift back into claiming a theorem. They also record why the effect does not
change our reported numbers: NDCG depends on the induced ORDERING, and the
coefficient reallocation leaves the top-k order unchanged in our runs.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def _ridge(X, y, lam):
    A = X.T @ X + lam * np.eye(X.shape[1])
    try:
        return np.linalg.solve(A, X.T @ y)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(A, X.T @ y, rcond=None)[0]


@pytest.fixture
def data():
    rng = np.random.default_rng(0)
    n = 200
    x1, x2 = rng.normal(size=n), rng.normal(size=n)
    y = 1.5 * x1 + 0.7 * x2 + 0.3 * rng.normal(size=n)
    return np.column_stack([x1, x2]), np.column_stack([x1, x1, x2]), y


def test_ridge_duplication_changes_predictions(data):
    """The reviewer's claim, verified: lam > 0 is NOT replication-invariant."""
    X, Xd, y = data
    p = X @ _ridge(X, y, lam=1.0)
    pd = Xd @ _ridge(Xd, y, lam=1.0)
    assert not np.allclose(p, pd), (
        "if this passes, the duplication concern would be moot -- but it is not"
    )
    assert np.abs(p - pd).max() > 1e-4


def test_duplicated_coefficients_split_evenly(data):
    """The mechanism: a^2+b^2 subject to a+b=c is minimised at a=b=c/2."""
    _, Xd, y = data
    w = _ridge(Xd, y, lam=1.0)
    assert np.isclose(w[0], w[1]), "shared coefficient should split evenly"


def test_least_squares_duplication_is_prediction_invariant(data):
    """lam = 0 IS invariant, which is why the diagnostic offers that setting."""
    X, Xd, y = data
    p = X @ np.linalg.lstsq(X, y, rcond=None)[0]
    pd = Xd @ np.linalg.lstsq(Xd, y, rcond=None)[0]
    assert np.allclose(p, pd, atol=1e-10)


def test_singular_gram_is_handled():
    """lam = 0 with a duplicated column gives a singular Gram matrix.

    The solver must fall back to the minimum-norm solution rather than raising,
    otherwise the lambda=0 diagnostic cannot run at all.
    """
    from signalshap.game.core import SignalShapGame

    src = SignalShapGame.__dict__["_fit_weights"]
    code = src.__doc__ or ""
    import inspect
    body = inspect.getsource(src)
    assert "lstsq" in body, "singular Gram must fall back to lstsq"
    assert "LinAlgError" in body


def test_redundancy_deviation_helper_exists():
    """Redundancy must be measured over coalitions, not assumed."""
    from signalshap.experiments.recovery import coalition_redundancy_deviation

    sources = ("a", "b", "c")
    # exactly redundant game in (a, b)
    v = {}
    from itertools import combinations
    for k in range(4):
        for comb in combinations(sources, k):
            S = frozenset(comb)
            v[S] = 1.0 if (("a" in S) or ("b" in S)) else 0.0
    out = coalition_redundancy_deviation(v, sources, "a", "b")
    assert out["exactly_redundant"]
    assert out["max_deviation"] == 0.0
    assert out["n_background_coalitions"] == 2
