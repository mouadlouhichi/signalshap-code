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
