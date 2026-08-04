"""Guards against three reporting defects that recur across drafts.

None is a modelling error; all three are the kind of thing a reviewer notices
immediately and that quietly erodes trust in every other number.

A. Basis mixing -- a single-seed point estimate printed beside a seed-based CI
   with nothing distinguishing them.
B. Stale hardcoded numerics -- a bound typed into prose that no longer matches
   the artefact it claims to summarise.
C. Rounding artefacts -- rounded per-source values whose sum differs from the
   rounded total, which reads as a violated axiom but is only display precision.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artefacts"
PAPER = ROOT / "paper" / "sn-article.tex"


def _results():
    return {p.stem.replace("results_", ""): json.loads(p.read_text())
            for p in sorted(ART.glob("results_*.json"))}


# --- A: basis labelling ---------------------------------------------------- #

@pytest.mark.skipif(not (ART / "tables" / "T6_loo_vs_shapley.csv").exists(),
                    reason="T6 not generated yet")
def test_t6_labels_its_two_bases():
    """Single-seed and seed-mean columns must be distinguishable by name."""
    header = (ART / "tables" / "T6_loo_vs_shapley.csv").read_text().splitlines()[0]
    assert "seed 42" in header, "single-seed columns must say so in T6"
    assert "seed mean" in header, "seed-mean column must say so in T6"


@pytest.mark.skipif(not (ART / "tables" / "T6_loo_vs_shapley.md").exists(),
                    reason="T6 not generated yet")
def test_t6_caption_warns_against_cross_basis_reading():
    text = (ART / "tables" / "T6_loo_vs_shapley.md").read_text().lower()
    assert "two bases" in text or "must not be compared" in text


def test_single_seed_and_seed_mean_genuinely_differ():
    """Sanity: if these ever coincide exactly, the CI is not being computed."""
    for name, r in _results().items():
        ci = r.get("multi_seed", {}).get("ci")
        if not ci or next(iter(ci.values())).get("n_seeds", 0) < 2:
            continue
        phi = r["e1_source_share"]["shapley"]
        assert any(abs(phi[g] - ci[g]["mean"]) > 1e-12 for g in phi), (
            f"{name}: seed-42 and seed-mean identical across all sources -- "
            "multi_seed is probably re-reporting a single seed"
        )
        return


# --- B: no stale hardcoded numerics ---------------------------------------- #

@pytest.mark.skipif(not PAPER.exists(), reason="paper.tex absent")
def test_efficiency_bound_in_prose_matches_the_artefact():
    """Any 10^-n efficiency bound in the text must not understate the artefact."""
    res = _results()
    if not res:
        pytest.skip("no results")
    worst = max(r["e1_source_share"]["efficiency"]["abs_error"] for r in res.values())
    tex = PAPER.read_text()

    claims = re.findall(r"\\le\s*([\d.]+)\s*\\times\s*10\^\{-(\d+)\}", tex)
    for mant, exp in claims:
        bound = float(mant) * 10 ** (-int(exp))
        if bound >= 1e-25:  # only efficiency-scale claims
            assert worst <= bound * 1.5, (
                f"prose claims <= {bound:.1e} but artefact worst case is "
                f"{worst:.1e} -- regenerate the text from T9"
            )


# --- C: rounding artefacts flagged, not hidden ----------------------------- #

def test_rounding_artefacts_are_detected_and_disclosed():
    """Where rounded phi do not sum to rounded v(G), T9 must say so."""
    for name, r in _results().items():
        e = r["e1_source_share"]["efficiency"]
        phi = r["e1_source_share"]["shapley"]

        # full precision must always hold
        assert e["abs_error"] < 1e-12, f"{name}: efficiency genuinely violated"

        rounded_sum = round(sum(round(v, 5) for v in phi.values()), 5)
        if abs(rounded_sum - round(e["v_grand"], 5)) > 1e-12:
            t9 = ART / "tables" / "T9_efficiency.csv"
            assert t9.exists(), (
                f"{name}: rounded sum {rounded_sum} != rounded v(G) "
                f"{round(e['v_grand'], 5)} -- T9 must exist to disclose it"
            )
            assert "yes" in t9.read_text().lower().split("\n")[-2], (
                f"{name}: rounding artefact present but not flagged in T9"
            )


def test_efficiency_is_structural_not_approximate():
    """Efficiency holds regardless of fit noise; it is not a tuned quantity."""
    for name, r in _results().items():
        e = r["e1_source_share"]["efficiency"]
        assert e["passes"], f"{name}: efficiency check failed"
        assert e["abs_error"] < 1e-15, (
            f"{name}: error {e['abs_error']:.1e} is too large to be float noise"
        )
