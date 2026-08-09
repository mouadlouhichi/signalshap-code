"""Regression tests for two errors a reviewer caught in review round 3.

1. The manuscript reported a "uniform semivalue" as a distinct comparator to
   Shapley and claimed it violates efficiency. Both statements were false:
   p_k = 1/n IS the Shapley weighting, because
   |S|!(n-|S|-1)!/n! = 1/(n * C(n-1,|S|)). The artefact had agreed to 0.0 in
   every coordinate on every corpus and we had read that as robustness.
2. Candidate truncation broke ties by position in the SOURCES tuple, so
   relabelling the players could change the game being attributed.
"""
from __future__ import annotations

from itertools import combinations, permutations

import numpy as np
import pytest

from signalshap.attribution.values import (
    banzhaf_value, binomial_semivalue, semivalue,
)
from signalshap.candidates.builder import build_candidates_for_user
from signalshap.game.core import exact_shapley

SRC = ("cf", "ct", "pop", "rec", "seq")


def _random_game(seed: int) -> dict:
    rng = np.random.default_rng(seed)
    out = {}
    for k in range(len(SRC) + 1):
        for c in combinations(SRC, k):
            out[frozenset(c)] = 0.0 if not c else float(rng.normal())
    out[frozenset()] = 0.0
    return out


@pytest.mark.parametrize("seed", range(5))
def test_size_uniform_semivalue_is_exactly_shapley(seed):
    """The claimed alternative value is Shapley, to floating point."""
    v = _random_game(seed)
    n = len(SRC)
    psi = semivalue(v, {k: 1.0 / n for k in range(n)}, SRC)
    phi = exact_shapley(v, SRC)
    assert max(abs(psi[g] - phi[g]) for g in SRC) < 1e-15


@pytest.mark.parametrize("seed", range(5))
def test_binomial_semivalues_are_not_shapley(seed):
    """The replacement comparators must actually differ from Shapley."""
    v = _random_game(seed)
    phi = exact_shapley(v, SRC)
    for q in (0.25, 0.75):
        psi = binomial_semivalue(v, q, SRC)
        assert max(abs(psi[g] - phi[g]) for g in SRC) > 1e-6, q


@pytest.mark.parametrize("seed", range(5))
def test_binomial_at_half_is_banzhaf(seed):
    v = _random_game(seed)
    a, b = binomial_semivalue(v, 0.5, SRC), banzhaf_value(v, SRC)
    assert max(abs(a[g] - b[g]) for g in SRC) < 1e-15


def test_shapley_alone_satisfies_efficiency():
    v = _random_game(11)
    grand = v[frozenset(SRC)]
    assert abs(sum(exact_shapley(v, SRC).values()) - grand) < 1e-12
    # Not a requirement of the others, and we no longer claim otherwise.
    assert abs(sum(binomial_semivalue(v, 0.25, SRC).values()) - grand) > 1e-6


def _scores_with_rank_ties():
    """Each source owns a disjoint block, so many items share a best rank."""
    base = {}
    for i, g in enumerate(SRC):
        m = np.full((1, 60), -10.0)
        m[0, i * 12:(i + 1) * 12] = np.arange(12)[::-1]
        base[g] = m
    return base


def _build(monkeypatch, scores, order, n_max, symmetric):
    """Build C_u with the declared source order permuted.

    The builder reads the global SOURCES tuple, not the dict order, so a test
    that only shuffles the dict would pass vacuously. It did, in the first
    version of this file.
    """
    import signalshap.candidates.builder as B
    monkeypatch.setattr(B, "SOURCES", tuple(order))
    return B.build_candidates_for_user(scores, 0, n_max, symmetric=symmetric)


@pytest.mark.parametrize("n_max", [7, 13, 26])
def test_candidate_set_is_invariant_to_source_order(monkeypatch, n_max):
    scores = _scores_with_rank_ties()
    ref = _build(monkeypatch, scores, SRC, n_max, True)
    for perm in list(permutations(SRC))[:24]:
        assert np.array_equal(
            ref, _build(monkeypatch, scores, perm, n_max, True)), perm


@pytest.mark.parametrize("n_max", [7, 13, 26])
def test_legacy_rule_is_order_dependent_so_the_test_above_has_teeth(
        monkeypatch, n_max):
    """Guards against the invariance test passing for a trivial reason."""
    scores = _scores_with_rank_ties()
    ref = _build(monkeypatch, scores, SRC, n_max, False)
    assert any(
        not np.array_equal(ref, _build(monkeypatch, scores, perm, n_max, False))
        for perm in permutations(SRC)
    )


def test_validation_recall_counts_negatives_only_users():
    """The head is fitted on the validation indicator, so a user whose
    validation positive is not retrieved contributes an all-zero target. A
    reviewer asked how many such users there are; nothing measured it."""
    from signalshap.candidates.builder import validation_recall

    cands = [np.array([1, 2, 3]), np.array([4, 5]), np.array([], dtype=np.int64)]
    valid = {0: 2, 1: 99, 2: 7}          # hit, miss, empty candidate set
    r = validation_recall(cands, valid)
    assert r["users_scored"] == 2        # the empty-candidate user is skipped
    assert r["users_with_positive"] == 1
    assert r["users_negatives_only"] == 1
    assert abs(r["validation_recall"] - 0.5) < 1e-12


def test_ndcg_macro_does_not_double_print_the_cutoff():
    """\\NDCG already expands to NDCG@10, so \\NDCG_K rendered 'NDCG@10K'."""
    from pathlib import Path

    tex = Path(__file__).resolve().parents[1] / "paper" / "sn-article.tex"
    if not tex.exists():
        import pytest
        pytest.skip("paper not present")
    body = tex.read_text()
    assert r"\NDCG_K" not in body
    assert r"\NDCG_{10}" not in body
    assert r"\newcommand{\NDCGat}" in body


def test_artefact_consumers_tolerate_metadata_keys():
    """Provenance strings must not break code that iterates corpora.

    Adding `_note_ci` and `_candidate_rule` at the top level of two artefacts
    broke three separate tests that did `for c, v in d.items()` and indexed
    straight into v. Rather than remove the metadata, which is what makes the
    artefacts self-describing, consumers skip non-dict values. This pins that.
    """
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "artefacts"
    for fname in ("final_seed_ci.json", "final_retirement_seeds.json"):
        f = root / fname
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        meta = [k for k, v in d.items() if not isinstance(v, dict)]
        assert meta, f"{fname} should carry provenance metadata"
        corpora = [k for k, v in d.items() if isinstance(v, dict)]
        assert corpora, f"{fname} should still have corpus blocks"
        # Every corpus block must name the candidate rule, directly or at the
        # top level, so no artefact is ambiguous about which game produced it.
        assert "_candidate_rule" in d or all(
            "candidate_rule" in d[c] for c in corpora), fname
