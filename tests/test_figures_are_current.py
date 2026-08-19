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
def test_published_figures_are_not_older_than_their_source():
    """Catch the exact rot that shipped a legacy Figure 6.

    Compares mtimes rather than bytes: matplotlib output is not
    byte-reproducible across versions, so a hash comparison would fail for
    reasons that have nothing to do with staleness.
    """
    stale = []
    for src in ART_FIGS.glob("F*_*.png"):
        n = re.match(r"F(\d+)_", src.name)
        if not n:
            continue
        pub = PAPER_FIGS / f"Fig{n.group(1)}.png"
        if pub.exists() and pub.stat().st_mtime < src.stat().st_mtime - 1:
            stale.append(pub.name)
    assert not stale, (
        f"{stale} are older than artefacts/figures/. Run "
        f"`python scripts/make_assets.py` to republish.")


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
