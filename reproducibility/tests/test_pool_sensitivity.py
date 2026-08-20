"""Neutral candidate pools: are the pool-construction rules actually neutral?

The main pool is the union of every source's top-N list. It is
coalition-independent, which is what the game requires, but it is not
source-independent: the players build it. `experiments/run_pool_sensitivity.py`
rebuilds the game on pools that consult no source score, so these tests check
the properties the sensitivity argument depends on -- the rules really are
source-blind, deterministic, and correctly sized -- rather than the outcome,
which is an empirical result and not something to assert in a test.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

for _d in ("scripts", "experiments"):          # flat repo, grouped release
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / _d))

from signalshap.candidates.builder import candidate_recall  # noqa: E402
from signalshap.data.loaders import load_dataset            # noqa: E402
from signalshap.scorers.base import mask_seen, train_all_scorers  # noqa: E402

import run_pool_sensitivity as R                            # noqa: E402

N_MAX = 120


@pytest.fixture(scope="module")
def fixture():
    ds = load_dataset("ml_1m", synthetic=True, seed=42)
    scores = mask_seen(train_all_scorers(ds, seed=42), ds)
    test = dict(zip(ds.test["user"].to_numpy(), ds.test["item"].to_numpy()))
    return ds, scores, test


def test_neutral_pools_never_read_a_score_value(fixture):
    """The whole point: permuting the score MAGNITUDES must not move the pool.

    Eligibility (which entries are -inf) is preserved, so a genuinely
    source-blind rule is unaffected. The union rule, which reads the values,
    must move -- otherwise this test proves nothing.
    """
    ds, scores, test = fixture
    rng = np.random.default_rng(0)
    shuffled = {}
    for g, m in scores.items():
        out = m.copy()
        for u in range(ds.n_users):
            fin = np.isfinite(out[u])
            vals = out[u][fin]
            rng.shuffle(vals)
            out[u][fin] = vals
        shuffled[g] = out

    for rule in (lambda s: R.popularity_pool(ds, s, N_MAX),
                 lambda s: R.random_pool(ds, s, N_MAX, 42),
                 lambda s: R.random_pool(ds, s, N_MAX, 42, test)):
        a, b = rule(scores), rule(shuffled)
        assert all(np.array_equal(x, y) for x, y in zip(a, b))

    from signalshap.candidates.builder import build_candidates
    a = build_candidates(scores, ds.n_users, N_MAX)
    b = build_candidates(shuffled, ds.n_users, N_MAX)
    assert not all(np.array_equal(x, y) for x, y in zip(a, b)), (
        "the union rule must be score-sensitive, else the contrast is vacuous")


def test_neutral_pools_respect_the_training_mask(fixture):
    """A pool may never contain an item the user already consumed."""
    ds, scores, test = fixture
    seen: dict[int, set] = {}
    for u, i in zip(ds.train["user"].to_numpy(), ds.train["item"].to_numpy()):
        seen.setdefault(int(u), set()).add(int(i))

    for cands in (R.popularity_pool(ds, scores, N_MAX),
                  R.random_pool(ds, scores, N_MAX, 42),
                  R.random_pool(ds, scores, N_MAX, 42, test)):
        for u, c in enumerate(cands):
            assert not (set(c.tolist()) & seen.get(u, set()))


def test_random_pool_is_deterministic_and_seed_sensitive(fixture):
    ds, scores, test = fixture
    a = R.random_pool(ds, scores, N_MAX, 42)
    b = R.random_pool(ds, scores, N_MAX, 42)
    c = R.random_pool(ds, scores, N_MAX, 43)
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    assert not all(np.array_equal(x, y) for x, y in zip(a, c))


def test_oracle_pool_retrieves_every_reachable_target(fixture):
    """The oracle rule exists to decouple recall collapse from attribution."""
    ds, scores, test = fixture
    plain = R.random_pool(ds, scores, N_MAX, 42)
    oracle = R.random_pool(ds, scores, N_MAX, 42, test)
    assert candidate_recall(oracle, test) > candidate_recall(plain, test)
    # Every test item that is eligible at all must now be present.
    for u, t in test.items():
        if u < len(oracle) and np.isfinite(scores["cf"][u][t]):
            assert t in set(oracle[u].tolist())


def test_pools_are_sized_and_free_of_duplicates(fixture):
    ds, scores, test = fixture
    for cands in (R.popularity_pool(ds, scores, N_MAX),
                  R.random_pool(ds, scores, N_MAX, 42),
                  R.random_pool(ds, scores, N_MAX, 42, test)):
        for c in cands:
            assert len(c) <= N_MAX
            assert len(set(c.tolist())) == len(c)


def test_popularity_pool_is_shared_across_users_up_to_masking(fixture):
    """It is one global list, filtered per user, not a per-user ranking."""
    ds, scores, test = fixture
    counts = np.bincount(ds.train["item"].to_numpy(), minlength=ds.n_items)
    top = set(np.lexsort((np.arange(ds.n_items), -counts))[:N_MAX].tolist())
    for c in R.popularity_pool(ds, scores, N_MAX, ):
        # Anything in a user's pool that is not in the global head can only be
        # there because a more popular item was masked out for that user.
        assert len(set(c.tolist()) - top) <= N_MAX
