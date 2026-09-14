"""Pins the claim that fusion weights never see test outcomes.

The paper states that coalition heads, segment weights, head-family choice and
shrinkage are all fitted on the VALIDATION fold and frozen before test
evaluation. If that ever stops being true the fusion comparison becomes
circular -- attribution derived from test NDCG would be used to build a ranker
scored on the same test NDCG -- which is the single most damaging thing a
reviewer could find. These tests make the claim falsifiable.
"""
from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from signalshap.fusion import heads
from signalshap.segments import segments


def _src(fn):
    return inspect.getsource(fn)


def test_ridge_head_fits_on_validation_targets_only():
    src = _src(segments._fit_ridge)
    assert "targets" in src
    assert "test_items" not in src, "ridge head must not reference test items"


def test_segment_weights_are_fitted_on_validation():
    src = _src(segments.signalshap_fuse_v2)
    fit_calls = re.findall(r"_design\((.*?)\)", src)
    assert fit_calls, "expected design-matrix construction"
    # every design matrix is built from validation targets
    assert "game.valid_items" in src
    # test items appear ONLY inside evaluate_weights calls
    for line in src.splitlines():
        if "test_items" in line:
            assert "evaluate_weights" in line, (
                f"test_items used outside evaluation: {line.strip()}"
            )


def test_head_and_shrinkage_selected_on_validation_fold():
    """Selection must take validation targets and nothing test-derived."""
    params = inspect.signature(heads.select_on_validation).parameters
    assert "valid_targets" in params, "selection must receive validation targets"
    assert not any("test" in p for p in params), (
        f"selection signature exposes test data: {list(params)}"
    )
    src = _src(heads.select_on_validation)
    # no attribute access to a test-item mapping anywhere in the body
    assert not re.search(r"\btest_items\b", src)
    assert not re.search(r"\.test\b", src)


def test_selection_docstring_states_the_guarantee():
    doc = (heads.select_on_validation.__doc__ or "").lower()
    assert "test" in doc and ("never" in doc or "not" in doc), (
        "the leakage guarantee should be documented where it is implemented"
    )


def test_fusion_returns_frozen_weights():
    """Weights must be produced once, not refit per evaluated user."""
    src = _src(segments.signalshap_fuse_v2)
    assert "w_seg[segments[u]]" in src, "expected a frozen per-segment lookup"


def test_coalition_heads_and_coalition_values_use_disjoint_folds():
    """The reviewer's cross-fitting concern, checked at the source.

    A reviewer suggested that coalition heads and the attribution that scores
    them might share a validation fold, which would make v(S) in-sample and
    optimistically biased even without test leakage. They do not: SignalShapGame
    accumulates its Gram matrix from ``valid_items`` and evaluates NDCG in
    ``v_per_user`` against ``test_items``. This test pins that separation, so a
    future refactor cannot quietly introduce the bias.

    Note the scope: this covers the MAIN attribution result. The
    attribution-derived fusion weights of Appendix A are a separate path and
    are a genuine instance of the concern; that experiment is reported as a
    negative result rather than as a contribution.
    """
    import inspect

    from signalshap.game import core

    fit_src = inspect.getsource(core.SignalShapGame._gram)
    eval_src = inspect.getsource(core.SignalShapGame.v_per_user)

    assert "valid_items" in fit_src, "head must be fitted on the validation fold"
    assert "test_items" not in fit_src, "TEST LEAKAGE: head fitted on test labels"
    assert "test_items" in eval_src, "coalition value must be scored on test"
    assert "valid_items" not in eval_src, "v(S) scored in-sample on the fit fold"
