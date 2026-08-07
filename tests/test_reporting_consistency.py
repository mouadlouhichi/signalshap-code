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


# --------------------------------------------------------------------------- #
# Artwork must be black-only (Springer greyscale reproduction, colourblind
# safety, and the game-theoretic XAI convention).
# --------------------------------------------------------------------------- #


def test_architecture_figure_is_monochrome():
    """Fig 1 is the schematic and must be black-only.

    Data figures keep colour -- five sources across three corpora is more than
    grey levels can carry -- but the architecture diagram follows the
    game-theoretic XAI convention of a black-only schematic.
    """
    from pathlib import Path

    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image", reason="Pillow not installed")

    f = Path(__file__).resolve().parents[1] / "paper" / "figures" / "Fig1.png"
    im = np.asarray(Image.open(f).convert("RGB")).astype(int)
    coloured = ((im.max(axis=2) - im.min(axis=2)) > 12).mean()
    assert coloured < 1e-4, f"Fig1 is {coloured:.2%} coloured; it must be black-only"


def test_data_figures_stay_readable_without_colour():
    """Colour may not be the ONLY channel: every source also gets a marker
    and a hatch, so the data figures survive greyscale reproduction and
    colour-vision deficiency."""
    from signalshap.plots.assets import PALETTE, SOURCE_HATCH, SOURCE_MARK

    assert set(PALETTE) == set(SOURCE_MARK) == set(SOURCE_HATCH)
    assert len(set(SOURCE_MARK.values())) == len(SOURCE_MARK)
    assert len(set(SOURCE_HATCH.values())) == len(SOURCE_HATCH)


def test_palette_is_colourblind_safe():
    """Okabe-Ito. Pinning the hexes stops a future edit reaching for red/green."""
    from signalshap.plots.assets import PALETTE

    okabe_ito = {"#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00",
                 "#56B4E9", "#F0E442", "#999999", "#000000"}
    for g, c in PALETTE.items():
        assert c.upper() in okabe_ito, f"{g}={c} is outside the Okabe-Ito set"


def test_display_names_cover_the_study_corpora():
    """Raw loader ids leaked into figure legends and table rows once."""
    from signalshap.plots.assets import DISPLAY

    for corpus in ("ml_1m", "gowalla_ts", "amazon_video_games"):
        assert corpus in DISPLAY, f"{corpus} would render as a raw identifier"
        assert "_" not in DISPLAY[corpus]


# --------------------------------------------------------------------------- #
# Language and framing constraints the reviewers required.
# --------------------------------------------------------------------------- #

REVIEWER_BANNED = {
    "build-or-retire": "contradicts the paper's own retirement result",
    "pre-registered": "no external registration exists; use 'frozen'",
    "misattribution": "assumes Shapley is correct; no ground truth exists",
    "true loss": "one observed realisation, not a population quantity",
    "true cost": "one observed realisation, not a population quantity",
    "Shapley shares": "values are not normalised shares",
    "what practitioners actually want": "unsupported claim about practitioners",
    "only when components contribute independently": "LOO is valid under dependence",
}


def test_reviewer_banned_phrases_are_absent():
    from pathlib import Path

    tex = (Path(__file__).resolve().parents[1] / "paper" / "sn-article.tex").read_text()
    flat = " ".join(tex.lower().split())
    for phrase, why in REVIEWER_BANNED.items():
        assert phrase.lower() not in flat, f"'{phrase}' present: {why}"


def test_required_structural_sections_exist():
    """Reviewer 1 asked for standalone Background and Discussion sections."""
    from pathlib import Path

    tex = (Path(__file__).resolve().parents[1] / "paper" / "sn-article.tex").read_text()
    for label in ("sec:background", "sec:discussion", "sec:hyperparams",
                  "sec:algorithm", "app:fusion"):
        assert f"\\label{{{label}}}" in tex, f"missing section {label}"


def test_appendix_is_labelled():
    """Reviewer 1 found Appendix A rendered with no heading at all."""
    from pathlib import Path

    tex = (Path(__file__).resolve().parents[1] / "paper" / "sn-article.tex").read_text()
    assert "\\appendix" in tex
    i = tex.index("\\appendix")
    assert "\\section{" in tex[i:i + 400], "no \\section follows \\appendix"


def test_interaction_index_named_consistently():
    """Must not cite Shapley-Taylor for a Grabisch-Roubens computation."""
    from pathlib import Path

    tex = (Path(__file__).resolve().parents[1] / "paper" / "sn-article.tex").read_text()
    i = tex.index("\\label{eq:taylor}")
    window = tex[max(0, i - 2500):i]
    assert "grabisch1999interaction" in window, \
        "the interaction equation must cite Grabisch-Roubens"
