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


def test_validation_miss_can_rotate_the_ridge_solution():
    """We claimed such users only shrink the weights. They can rotate them.

    A validation-miss user adds a PSD block to A and nothing to c. For
    w = (A + lam I)^-1 c that rescales eigendirections unevenly, so the
    solution turns as well as shortens. The manuscript asserted the opposite.
    """
    lam = 1.0
    Z1 = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    y1 = np.array([1.0, 0.0, 0.0])
    A1, c1 = Z1.T @ Z1, Z1.T @ y1
    w1 = np.linalg.solve(A1 + lam * np.eye(2), c1)

    Zm = np.array([[3.0, 0.2], [2.5, 0.1]])       # miss user: no positive
    w2 = np.linalg.solve(A1 + Zm.T @ Zm + lam * np.eye(2), c1)

    cos = (w1 @ w2) / (np.linalg.norm(w1) * np.linalg.norm(w2))
    angle = np.degrees(np.arccos(np.clip(cos, -1, 1)))
    assert np.linalg.norm(w2) < np.linalg.norm(w1)   # it does shrink
    assert angle > 1.0                               # but it also rotates


def test_protocol_sensitivity_script_is_registered():
    """The frozen-vs-refreshed experiment must ship, not just be promised."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    src = (root / "scripts" / "run_protocol_sensitivity.py")
    assert src.exists()
    body = src.read_text()
    # Two states, not one refit on train+val: refitting everything masks the
    # validation target and silently fits on an all-zero right-hand side.
    assert "_two_state_game" in body
    assert "history = train + val" in body or "train + val" in body
    tex = (root / "paper" / "sn-article.tex")
    if tex.exists():
        assert "run\\_protocol\\_sensitivity" in tex.read_text()


def test_utility_is_raw_and_v_is_centred():
    """Retirement loss must difference raw utility, not the centred game.

    End to end each coalition retrieves its own candidates, so |C_u| and hence
    the expected-random baseline differ between the full system and the
    survivors. Differencing v() then carries a b(G\\{g}) - b(G) term that is not
    part of the observed change. A reviewer derived this; the fix was to expose
    utility() alongside v().
    """
    from signalshap.game.core import SignalShapGame

    rng = np.random.default_rng(0)
    n_items = 40
    scores = {g: rng.normal(size=(3, n_items)).astype(np.float32) for g in SRC}
    cands = [np.arange(n_items) for _ in range(3)]
    valid = {u: int(rng.integers(n_items)) for u in range(3)}
    test = {u: int(rng.integers(n_items)) for u in range(3)}
    g = SignalShapGame(scores, cands, valid, test)

    S = frozenset(SRC)
    assert abs((g.utility(S) - g.v0) - g.v(S)) < 1e-9   # v = utility - baseline
    assert g.utility(frozenset()) == 0.0
    assert g.v0 > 0.0                                    # baseline is non-trivial
    # The two differ by exactly the baseline, so they are not interchangeable.
    assert abs(g.utility(S) - g.v(S)) > 1e-12


def test_wilcoxon_on_constant_positive_differences_is_significant():
    """Ten identical positive differences are the strongest signal, not the weakest.

    Our runner special-cased constant difference vectors to p = 1.0. That is
    backwards: the signed-rank statistic is 0 and the exact two-sided p is
    2/2^10. Only an all-zero vector is uninformative.
    """
    from scipy.stats import wilcoxon

    d = np.full(10, 0.20)
    assert abs(float(wilcoxon(d).pvalue) - 2 / 2 ** 10) < 1e-9
    assert float(wilcoxon(d).pvalue) < 0.01


def test_kendall_tau_intervals_stay_inside_the_support():
    """A t interval on ten bounded tau values produced [0.90, 1.02]."""
    import json
    from pathlib import Path

    f = Path(__file__).resolve().parents[1] / "artefacts" / "final_retirement_seeds.json"
    if not f.exists():
        import pytest
        pytest.skip("artefact absent")
    d = json.loads(f.read_text())
    for c, v in d.items():
        if not isinstance(v, dict) or "tau_loo" not in v:
            continue
        for k in ("tau_loo", "tau_shapley"):
            assert -1.0 <= v[k]["lo"] <= 1.0, (c, k)
            assert -1.0 <= v[k]["hi"] <= 1.0, (c, k)


def test_protocol_sensitivity_resumes_instead_of_overwriting():
    """Running one corpus must not delete the others.

    A `--corpora gowalla_ts` pass started from an empty dict and wiped the
    ml_1m and amazon results already on disk. This is the same non-resumable
    failure that once cost eight hours in block_seeds, reintroduced in a new
    script; the guard is a load-on-start, not a comment.
    """
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1]
           / "scripts" / "run_protocol_sensitivity.py").read_text()
    assert "resuming" in src
    assert "protocol_sensitivity.json" in src.split("def main")[1]


def test_protocol_sensitivity_actually_uses_its_budget_flag():
    """--budget-gb was accepted and ignored, so Gowalla loaded at full size."""
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1]
           / "scripts" / "run_protocol_sensitivity.py").read_text()
    assert "size_corpus" in src, "budget flag must size the corpus"
    assert "check_paper_shape" in src, "must refuse a resized corpus"


def test_latex_static_checks_pass():
    """No TeX in CI, so lint the source for the errors that break a compile."""
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "check_latex.py"
    if not (root / "paper" / "sn-article.tex").exists():
        import pytest
        pytest.skip("paper absent")
    r = subprocess.run([sys.executable, str(script)],
                       capture_output=True, text=True, cwd=root)
    assert r.returncode == 0, r.stdout + r.stderr


def test_latex_linter_detects_a_broken_table():
    """A linter that never fails is worse than none: prove it catches a fault."""
    import re
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    tex = root / "paper" / "sn-article.tex"
    if not tex.exists():
        import pytest
        pytest.skip("paper absent")
    original = tex.read_text()
    lines = original.split("\n")
    hit = next((k for k, l in enumerate(lines)
                if l.startswith("MovieLens-1M &")), None)
    assert hit is not None
    lines[hit] = lines[hit].replace("MovieLens-1M &", "MovieLens-1M & X &", 1)
    try:
        tex.write_text("\n".join(lines))
        r = subprocess.run([sys.executable, str(root / "scripts" / "check_latex.py")],
                           capture_output=True, text=True, cwd=root)
        assert r.returncode == 1, "linter missed an extra table cell"
        assert "cells, spec has" in r.stdout
    finally:
        tex.write_text(original)


def test_run_study_refuses_to_shrink_a_corpus_silently():
    """Taking the smallest cap across corpora substitutes a different corpus.

    run_study sized every corpus, then applied min(caps) to all of them via one
    process-wide env var. A multi-corpus invocation would therefore have run
    MovieLens at Gowalla's cap and overwritten results_ml_1m.json with numbers
    from a corpus the manuscript does not describe.
    """
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1]
           / "scripts" / "run_study.py").read_text()
    assert "check_paper_shape" in src, "must verify the manuscript's shape"
    assert "min(caps.values())" not in src, "must not silently shrink corpora"
    assert "one at a time" in src


def test_global_timeblock_split_admits_no_future_training_events():
    """The whole point of the blocked split: nothing is fitted on the future."""
    import importlib.util
    from pathlib import Path

    import pandas as pd

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "gt", root / "scripts" / "run_global_timeblock.py")
    gt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gt)

    rng = np.random.default_rng(0)
    rows = []
    for u in range(200):                       # users overlap in calendar time
        ts = np.sort(rng.uniform(1e9, 1e9 + 1e7, size=rng.integers(20, 60)))
        for t in ts:
            rows.append((u, int(rng.integers(0, 300)), float(t), len(rows)))
    df = pd.DataFrame(rows, columns=["user", "item", "timestamp",
                                     "original_record_index"])

    class DS:
        pass
    ds = DS(); ds.n_users, ds.n_items = 200, 300
    ds.train, ds.valid, ds.test = df, df.iloc[:0].copy(), df.iloc[:0].copy()

    blocked, stats = gt.global_split(ds)
    assert stats["train_events_after_any_test_event"] == 0
    assert stats["users_retained"] > 0
    # One held-out event per user per fold.
    assert blocked.valid["user"].is_unique
    assert blocked.test["user"].is_unique
    # And the folds really are time ordered.
    assert blocked.train["timestamp"].max() <= blocked.valid["timestamp"].min()
    assert blocked.valid["timestamp"].max() <= blocked.test["timestamp"].min()
