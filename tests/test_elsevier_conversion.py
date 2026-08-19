"""The KBS manuscript must stay in sync with the Springer source and the guide.

`paper-kbs/kbs-article.tex` is generated from `paper/sn-article.tex`. The
Springer file remains the source of truth: `check_paper_numbers.py` validates
it against `artefacts/`, so a hand-forked Elsevier copy would drift from the
data within one revision and nothing would catch it.

These tests pin two things: the generated file matches its generator, and the
output satisfies the Knowledge-Based Systems guide for authors on every point
that can be checked without a TeX run.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts" / "make_elsevier.py"
KBS = ROOT / "paper-kbs" / "kbs-article.tex"
SPRINGER = ROOT / "paper" / "sn-article.tex"


def _mod():
    spec = importlib.util.spec_from_file_location("_els", GEN)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def tex() -> str:
    return KBS.read_text()


def test_generated_file_matches_its_generator(tex):
    expected, _ = _mod().convert(SPRINGER.read_text())
    assert tex == expected, (
        "paper-kbs/kbs-article.tex differs from what scripts/make_elsevier.py "
        "produces. Edit paper/sn-article.tex and re-run the generator.")


# -- Knowledge-Based Systems guide for authors ------------------------------ #

def test_abstract_within_250_words(tex):
    body = tex[tex.index(r"\begin{abstract}") + 16:tex.index(r"\end{abstract}")]
    n = len(body.split())
    assert n <= 250, f"abstract is {n} words; KBS caps it at 250"


def test_between_one_and_seven_keywords(tex):
    body = tex[tex.index(r"\begin{keywords}") + 16:tex.index(r"\end{keywords}")]
    kws = [k.strip() for k in body.split(r"\sep") if k.strip()]
    assert 1 <= len(kws) <= 7, f"{len(kws)} keywords; KBS allows 1-7"


def test_highlights_are_a_separate_file_within_limits():
    """KBS: 3-5 bullets, each at most 85 characters including spaces."""
    hl = (ROOT / "paper-kbs" / "highlights.tex").read_text()
    items = re.findall(r"\\item (.+)", hl)
    assert 3 <= len(items) <= 5, f"{len(items)} highlights; KBS requires 3-5"
    for h in items:
        assert len(h) <= 85, f"{len(h)} chars (max 85): {h}"


def test_numbered_citation_style(tex):
    """KBS wants [n] citations numbered in order of appearance."""
    assert r"\bibliographystyle{elsarticle-num}" in tex


def test_required_declaration_sections_present(tex):
    for heading in (
        "CRediT authorship contribution statement",
        "Declaration of competing interest",
        "Declaration of generative AI",
        "Data availability",
    ):
        assert heading in tex, f"KBS requires a '{heading}' section"


def test_credit_roles_are_from_the_official_taxonomy(tex):
    """Free-text roles are rejected at proof stage."""
    official = {
        "Conceptualization", "Data curation", "Formal analysis",
        "Funding acquisition", "Investigation", "Methodology",
        "Project administration", "Resources", "Software", "Supervision",
        "Validation", "Visualization", "Writing -- original draft",
        "Writing -- review and editing",
    }
    start = tex.index("CRediT authorship contribution statement}")
    block = tex[start + len("CRediT authorship contribution statement}"):
                tex.index("Declaration of competing")]
    # Strip the \textbf{Name:} author labels, then split the role lists.
    roles = set()
    for chunk in re.sub(r"\\textbf\{[^}]*\}", "", block).split("."):
        for r in chunk.split(","):
            r = " ".join(r.split())
            if r and not r.startswith("\\") and "section" not in r:
                roles.add(r)
    unknown = {r for r in roles if r and r not in official}
    assert not unknown, f"not CRediT roles: {sorted(unknown)}"


def test_sections_are_numbered_not_starred_in_the_body(tex):
    """KBS requires numbered sections; only the declarations are starred."""
    body = tex[tex.index(r"\maketitle"):tex.index("CRediT authorship")]
    starred = re.findall(r"\\section\*\{([^}]*)\}", body)
    assert not starred, f"starred sections in the body: {starred}"


# -- double-column mechanics ------------------------------------------------ #

def test_wide_floats_span_both_columns(tex):
    """cas-dc gives ~84mm per column; a wide float overflows the gutter."""
    for m in re.finditer(r"\\begin\{(table|figure)\}", tex):
        end = tex.index(f"\\end{{{m.group(1)}}}", m.end())
        block = tex[m.start():end]
        label = re.search(r"\\label\{([^}]+)\}", block)
        assert r"\textwidth" not in block and r"\linewidth" not in block, (
            f"{label.group(1) if label else '?'} is full-width but not starred")
        assert max(len(l) for l in block.splitlines()) <= 90, (
            f"{label.group(1) if label else '?'} has a long row but is not starred")


def test_at_least_some_floats_were_widened(tex):
    """Guard against the promotion silently doing nothing.

    It once did: the width test ended in a conditional expression, which binds
    looser than `or`, so the whole condition collapsed to False for any float
    without a tabular and every figure stayed single-column.
    """
    assert len(re.findall(r"\\begin\{(?:table|figure)\*\}", tex)) >= 10


def test_no_springer_only_macros_survive(tex):
    for macro in (r"\backmatter", r"\bmhead", r"\botrule", r"\fnm{", r"\sur{",
                  r"\orgdiv", r"\orgname", r"\abstract{", r"\keywords{"):
        assert macro not in tex, f"Springer macro {macro} survived conversion"


def test_documentclass_is_elsevier(tex):
    assert re.search(r"\\documentclass\[[^\]]*\]\{cas-dc\}", tex)


def test_braces_and_environments_balance(tex):
    stripped = re.sub(r"\\.", "  ", tex)
    stripped = re.sub(r"(?<!\\)%.*", "", stripped)
    assert stripped.count("{") == stripped.count("}")

    depth: dict[str, int] = {}
    for m in re.finditer(r"\\(begin|end)\{([^}]+)\}", tex):
        depth[m.group(2)] = depth.get(m.group(2), 0) + (
            1 if m.group(1) == "begin" else -1)
    assert not {k: v for k, v in depth.items() if v}


def test_figures_and_bibliography_travel_with_the_manuscript():
    d = ROOT / "paper-kbs"
    assert (d / "paper.bib").exists()
    assert len(list((d / "figures").glob("Fig*.png"))) == 7
    assert (d / "fetch-template.sh").exists(), (
        "cas-dc.cls is Elsevier's and is not redistributed; the fetch script "
        "must be shipped so the bundle is buildable")


def test_every_included_figure_is_present(tex):
    figs = set(re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", tex))
    for f in figs:
        assert (ROOT / "paper-kbs" / "figures" / f).exists(), f


def test_generator_reports_violations_with_a_nonzero_exit():
    """The conformance check must be able to fail, not just print."""
    src = GEN.read_text()
    assert "KBS GUIDE VIOLATIONS" in src and "return 1" in src
