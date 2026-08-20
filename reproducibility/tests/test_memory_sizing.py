"""Corpus sizing (provenance entry #18).

run_study.py was OOM-killed on Gowalla because the memory sizing lived only in
run_full_revision.py: the pipeline was called directly, SIGNALSHAP_MAX_USERS was
never set, and the loaders happily returned all 52,985 users.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

from signalshap.memory import (MIN_USERS, check_fits, default_budget_gb,
                               fit_users, scores_gb, size_corpus)

ROOT = Path(__file__).resolve().parents[1]


def test_gowalla_full_size_is_the_number_that_killed_the_run():
    """53k x 122k really is ~129 GB of score matrices -- not a guess."""
    gb = scores_gb(52_985, 121_866)
    assert 125 < gb < 135
    ok, msg = check_fits("gowalla_ts", 52_985, 121_866, budget_gb=16.0)
    assert ok is False
    assert "OOM" in msg


def test_fit_users_inverts_scores_gb():
    n_items, budget = 68_443, 16.0
    n = fit_users(n_items, budget)
    # The derived cap must fit once the peak multiplier is applied.
    assert scores_gb(n, n_items) * 1.6 <= budget * 1.05
    # ...and be the LARGEST such count, not a token subsample.
    assert scores_gb(n * 2, n_items) * 1.6 > budget


def test_fit_users_never_returns_a_useless_corpus():
    assert fit_users(10 ** 9, 0.001) == MIN_USERS


def test_fit_users_respects_the_corpus_ceiling():
    assert fit_users(100, 1000.0, n_users=900) == 900


def test_budget_defaults_to_a_fraction_of_free_ram():
    assert default_budget_gb(None) >= 4.0
    assert default_budget_gb(7.5) == 7.5


def test_size_corpus_installs_the_env_var_every_loader_reads():
    """_env_cap() is the only thing standing between us and a 129 GB alloc."""
    class _Probe:
        n_items = 20_000

    os.environ.pop("SIGNALSHAP_MAX_USERS", None)
    cap = size_corpus("fake", lambda: _Probe(), budget_gb=8.0, verbose=False)
    assert os.environ["SIGNALSHAP_MAX_USERS"] == str(cap)
    # Probe count is scaled up 3x, so the cap is conservative.
    assert cap == fit_users(60_000, 8.0)
    os.environ.pop("SIGNALSHAP_MAX_USERS", None)


def test_explicit_max_users_can_only_shrink_the_cap():
    class _Probe:
        n_items = 100

    cap = size_corpus("fake", lambda: _Probe(), budget_gb=1000.0,
                      max_users=750, verbose=False)
    assert cap == 750
    os.environ.pop("SIGNALSHAP_MAX_USERS", None)


def test_check_fits_passes_a_sized_corpus():
    ok, msg = check_fits("gowalla_ts", 5_910, 68_443, budget_gb=16.0)
    assert ok is True
    assert "8.1 GB" in msg          # the size the successful run reported


@pytest.mark.parametrize("script", ["run_study.py", "run_full_revision.py"])
def test_both_entry_points_size_before_running(script):
    """The regression itself: sizing in one script only is not a safeguard."""
    src = (ROOT / "scripts" / script).read_text()
    tree = ast.parse(src)
    called = {n.func.id for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "size_corpus" in called, f"{script} loads corpora without sizing them"
    assert "check_fits" in called, f"{script} never verifies it came in under budget"


@pytest.mark.parametrize("script", ["run_study.py", "run_full_revision.py"])
def test_no_script_keeps_a_private_copy_of_the_sizing_math(script):
    """Duplicated sizing is how the two scripts drifted apart in the first place."""
    src = (ROOT / "scripts" / script).read_text()
    assert "PEAK_MULTIPLIER =" not in src
    assert "def _fit_users" not in src
    assert "def _free_gb" not in src


def test_paper_corpus_shape_guard_catches_a_resized_gowalla():
    """A 12.6 GB budget silently substituted a different Gowalla and the
    resulting artefact overwrote the reported one in place. The guard exists
    so that can only happen deliberately, via --allow-resize."""
    from signalshap.memory import check_paper_shape

    ok, why = check_paper_shape("gowalla_ts", 4652, 59597)
    assert not ok
    assert "8,865" in why and "82,134" in why

    assert check_paper_shape("gowalla_ts", 8865, 82134)[0]
    assert check_paper_shape("ml_1m", 6038, 3533)[0]
    # Unknown corpora are not policed.
    assert check_paper_shape("some_new_corpus", 1, 1)[0]


def test_budget_derives_the_paper_gowalla_only_near_24gb():
    """Documents the budget that reproduces the manuscript's Gowalla."""
    from signalshap.memory import fit_users

    assert fit_users(82134, 12.6) < 5000      # the run that went wrong
    assert fit_users(82134, 24.0) >= 8865     # the reported corpus
