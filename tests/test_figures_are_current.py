"""The figures in paper/ must be the ones the current artefacts produce.

This is a regression test for a silent, reviewer-visible failure. The copy
from `artefacts/figures/F<N>_*.png` into `paper/figures/Fig<N>.png` was manual
and undocumented, so after the symmetric-rule regeneration the committed
Figure 6 was eleven days old: it plotted a fusion comparison from the legacy
candidate rule while the prose beside it quoted the new numbers, one of which
had changed SIGN. Nothing failed, nothing warned, and the figure contradicted
the text it illustrated.

Rendering PNGs here would be slow and byte-fragile (matplotlib output is not
reproducible across versions), so these tests check the two properties that
actually broke: the publish step exists in the pipeline, and every figure the
manuscript includes is present and no older than the artefacts behind it.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAPER_FIGS = ROOT / "paper" / "figures"
ART_FIGS = ROOT / "artefacts" / "figures"
TEX = ROOT / "paper" / "sn-article.tex"


def _included():
    """Figure files the manuscript actually \\includegraphics."""
    return sorted(set(re.findall(r"\\includegraphics\[[^\]]*\]\{(Fig\d+\.png)\}",
                                 TEX.read_text())))


def test_the_manuscript_includes_figures():
    assert _included(), "no figures referenced; the regex or the tex changed"


def test_every_included_figure_exists():
    for f in _included():
        assert (PAPER_FIGS / f).exists(), f"{f} is referenced but missing"


def test_no_orphan_figures_in_paper():
    """An unreferenced figure is usually a rename that half-happened."""
    on_disk = {p.name for p in PAPER_FIGS.glob("Fig*.png")}
    # Fig1 may be rendered as live TikZ, so it is allowed to be present and
    # unreferenced by \includegraphics.
    orphans = on_disk - set(_included()) - {"Fig1.png"}
    assert not orphans, f"unreferenced figures: {sorted(orphans)}"


@pytest.mark.skipif(not ART_FIGS.exists(), reason="assets not generated here")
def test_published_figures_match_or_are_deliberately_hand_authored():
    """Catch the rot that once shipped a legacy Figure 6.

    Compares CONTENT, not mtimes. An earlier version compared timestamps and
    produced false failures whenever artefacts/ was restored from a backup,
    while missing the case that actually matters.

    Figure 1 is exempt: it renders as live TikZ in the manuscript and its
    raster is a hand-authored fallback, so the generated copy in artefacts/ is
    deliberately NOT the published one.
    """
    import hashlib

    def digest(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    stale = []
    for src in sorted(ART_FIGS.glob("F*_*.png")):
        n = re.match(r"F(\d+)_", src.name)
        if not n or n.group(1) == "1":
            continue
        pub = PAPER_FIGS / f"Fig{n.group(1)}.png"
        if pub.exists() and digest(pub) != digest(src):
            stale.append(pub.name)
    assert not stale, (
        f"{stale} differ from artefacts/figures/. Run "
        f"`python scripts/make_assets.py` to republish.")


def test_figure1_is_live_tikz_with_a_raster_fallback():
    """Fig1's raster may diverge, but only because TikZ is the real source."""
    tex = TEX.read_text()
    assert "\\tikzfiguretrue" in tex
    assert "\\includegraphics[width=\\linewidth]{Fig1.png}" in tex
    assert (PAPER_FIGS / "Fig1.png").exists()


def test_make_assets_publishes_into_the_paper():
    """The copy must be part of the pipeline, not a step someone remembers."""
    body = (ROOT / "scripts" / "make_assets.py").read_text()
    assert 'paper" / "figures"' in body, "make_assets.py must publish"
    assert "shutil.copyfile" in body
    assert "--no-publish" in body, "a diagnostic escape hatch must exist"


def test_diagnostic_assets_are_never_published():
    """--include-failed mixes ungated corpora; those must not reach paper/."""
    body = (ROOT / "scripts" / "make_assets.py").read_text()
    i = body.index("if a.include_failed:\n        print(\"  [not published]")
    j = body.index("shutil.copyfile")
    assert i < j, "the include-failed guard must precede the copy"
