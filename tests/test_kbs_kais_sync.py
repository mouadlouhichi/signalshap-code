"""The KBS and KAIS manuscripts must not drift apart.

They share one body of prose and one set of numbers; only the publisher
wrapper differs. The hand-maintained KBS copy previously shipped in
`signalshap__submission.zip` had already fallen behind the KAIS source on the
introduction, the verification section, the discussion, the retirement table
and the abstract. These tests make that failure mode loud.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
KAIS = REPO / "paper-kais" / "main.tex"
KBS = REPO / "paper-kbs-elsevier" / "main.tex"
KAIS_ESM = REPO / "paper-kais" / "Online-Resource-1.tex"
KBS_ESM = REPO / "paper-kbs-elsevier" / "supplementary-material.tex"


def _kais_body(text: str) -> str:
    return text[text.index(r"\section{Introduction}"):
                text.index(r"\backmatter")].rstrip()


def _kbs_body(text: str) -> str:
    return text[text.index(r"\section{Introduction}"):
                text.index(r"\section*{CRediT")].rstrip()


def _normalise(body: str) -> str:
    """Undo the intended, purely typographic differences."""
    for env in ("table", "figure", "algorithm"):
        body = body.replace(f"\\begin{{{env}*}}", f"\\begin{{{env}}}")
        body = body.replace(f"\\end{{{env}*}}", f"\\end{{{env}}}")
    body = body.replace(r"\paragraph{", r"\subsubsection{")
    body = body.replace(r"\includegraphics[width=\columnwidth]{Fig3.png}",
                        r"\includegraphics[width=0.7\textwidth]{Fig3.png}")
    return body


def test_bodies_agree_modulo_the_publisher_wrapper() -> None:
    assert _normalise(_kbs_body(KBS.read_text())) == _kais_body(KAIS.read_text())


def test_every_reported_number_is_identical() -> None:
    """The layout parameter in \\includegraphics is the only permitted
    numeric difference, and it is not a result."""
    def nums(t: str) -> list[str]:
        t = re.sub(r"(?<!\\)%.*", "", t)
        t = re.sub(r"\\includegraphics\[[^\]]*\]", "", t)
        return re.findall(r"[-+]?\d*\.\d+|\d+", t)

    assert nums(_kais_body(KAIS.read_text())) == nums(_kbs_body(KBS.read_text()))


def test_supplements_differ_only_in_the_title_block() -> None:
    a = KAIS_ESM.read_text()
    b = KBS_ESM.read_text()
    body_a = a[a.index(r"\begin{document}"):]
    body_b = b[b.index(r"\begin{document}"):]
    assert body_a == body_b


def test_no_springer_markup_leaks_into_the_elsevier_file() -> None:
    text = re.sub(r"(?<!\\)%.*", "", KBS.read_text())
    for macro in (r"\fnm{", r"\sur{", r"\affil", r"\abstract{", r"\keywords{",
                  r"\backmatter", r"\bmhead", "sn-jnl", "sn-basic"):
        assert macro not in text, macro


def test_no_elsevier_markup_leaks_into_the_springer_file() -> None:
    text = re.sub(r"(?<!\\)%.*", "", KAIS.read_text())
    for macro in (r"\ead{", r"\corref", r"\fnref", r"\journal{",
                  r"\begin{frontmatter}", "elsarticle"):
        assert macro not in text, macro


def test_wide_floats_span_both_columns_in_the_two_column_build() -> None:
    """elsarticle 5p is two-column at roughly 84mm. A \\textwidth tabular left
    in a single-column float runs into the gutter."""
    text = KBS.read_text()
    for m in re.finditer(r"\\begin\{(table|figure)\}(.*?)\\end\{\1\}",
                         text, re.S):
        inner = m.group(2)
        lab = re.search(r"\\label\{([^}]*)\}", inner)
        label = lab.group(1) if lab else "?"
        assert "textwidth" not in inner and "tabularx" not in inner, (
            f"unstarred float {label} uses the full text width")


def test_kais_keeps_single_column_floats() -> None:
    """The mirror image: sn-basic is single column, where a starred float can
    be deferred to the end or dropped."""
    text = KAIS.read_text()
    assert r"\begin{table*}" not in text
    assert r"\begin{figure*}" not in text


def test_every_cite_key_resolves_in_both_builds() -> None:
    for tex, bib in ((KBS, REPO / "paper-kbs-elsevier" / "paper.bib"),
                     (KAIS, REPO / "paper-kais" / "paper.bib")):
        used: set[str] = set()
        for m in re.finditer(r"\\cite[a-z]*\{([^}]*)\}", tex.read_text()):
            used |= {k.strip() for k in m.group(1).split(",")}
        defined = set(re.findall(r"@\w+\{([^,]+),", bib.read_text()))
        assert not used - defined, f"{tex.name}: {sorted(used - defined)}"


def test_every_reference_resolves_in_the_elsevier_build() -> None:
    text = re.sub(r"(?<!\\)%.*", "", KBS.read_text())
    labels = set(re.findall(r"\\label\{([^}]*)\}", text))
    refs = set(re.findall(r"\\(?:ref|eqref|autoref)\{([^}]*)\}", text))
    assert not refs - labels, sorted(refs - labels)


def test_highlights_fit_the_elsevier_limit() -> None:
    lines = [l for l in (REPO / "paper-kbs-elsevier" / "highlights.txt")
             .read_text().strip().splitlines() if l.strip()]
    assert len(lines) <= 5, f"{len(lines)} highlights"
    for l in lines:
        assert len(l) <= 85, f"{len(l)} chars: {l}"


def test_kbs_supplement_does_not_name_the_other_journal() -> None:
    assert "Knowledge and Information Systems" not in KBS_ESM.read_text()
    assert "Knowledge-Based Systems" not in KAIS_ESM.read_text()


def test_generator_is_reproducible() -> None:
    before = {p: p.read_text() for p in
              (KBS, KBS_ESM, REPO / "paper-kbs-elsevier" / "highlights.txt")}
    subprocess.run([sys.executable, "scripts/make_kbs_from_kais.py"],
                   cwd=REPO, check=True, capture_output=True)
    for p, text in before.items():
        assert p.read_text() == text, f"{p.name} changed on regeneration"


def test_elsevier_build_uses_paragraph_not_subsubsection() -> None:
    """Cosmetic but intended: elsarticle's two-column measure makes a numbered
    fourth level cramped, and \\paragraph is the KBS template convention. Not
    covered by the body-agreement test, which normalises the two forms."""
    text = KBS.read_text()
    assert r"\subsubsection{" not in text
    assert text.count(r"\paragraph{") >= 10


# --- KAIS editor: "comparative studies are insufficient, lacks recent
#     references from TKDE, TKDD, KAIS, KDD, ICDM" ----------------------- #

def _cited_entries(tex_paths, bib_path):
    used: set[str] = set()
    for p in tex_paths:
        for m in re.finditer(r"\\cite[a-z]*\{([^}]*)\}", p.read_text()):
            used |= {k.strip() for k in m.group(1).split(",")}
    bib = bib_path.read_text()
    entries = {m.group(2): " ".join(m.group(3).split())
               for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", bib, re.S)}
    return {k: entries[k] for k in used if k in entries}


def test_editor_named_venues_are_represented_recently() -> None:
    """The handling editor counted our KDD citations exactly: "1 in 2011 and
    1 in 2016". TKDE, TKDD and KAIS were literally absent. A desk complaint
    that specific should not be able to recur silently."""
    cited = _cited_entries(
        [KBS, KBS_ESM], REPO / "paper-kbs-elsevier" / "paper.bib")

    def years(pattern):
        out = []
        for body in cited.values():
            if re.search(pattern, body):
                y = re.search(r"year = \{?(\d{4})", body)
                if y:
                    out.append(int(y.group(1)))
        return out

    tkde = years(r"Knowledge and Data Engineering")
    kais = years(r"Knowledge and Information Systems")
    assert tkde, "no TKDE citation"
    assert kais, "no KAIS citation"
    assert max(tkde) >= 2024, f"newest TKDE citation is {max(tkde)}"
    assert max(kais) >= 2024, f"newest KAIS citation is {max(kais)}"


def test_bibliography_is_recent_enough() -> None:
    cited = _cited_entries(
        [KBS, KBS_ESM], REPO / "paper-kbs-elsevier" / "paper.bib")
    ys = []
    for body in cited.values():
        y = re.search(r"year = \{?(\d{4})", body)
        if y:
            ys.append(int(y.group(1)))
    recent = sum(1 for y in ys if y >= 2022)
    assert recent >= 14, f"only {recent} citations from 2022 onward"


def test_attribution_rule_comparison_is_present() -> None:
    """The editor's substantive point was comparative studies, not citation
    count. The rule comparison is the answer to it."""
    assert "tab:rulecomparison" in KBS.read_text()
    assert "rulecomparison-esm" in KBS_ESM.read_text()


def test_attribution_baselines_match_the_artefact() -> None:
    """Prose numbers must track artefacts/attribution_baselines.json."""
    data = json.loads((REPO / "artefacts" / "attribution_baselines.json").read_text())
    rules = data["rules"]
    # The ordering that carries the argument.
    assert rules["loo_rank"]["kendall_tau_vs_observed_loss"] == pytest.approx(1.0)
    assert rules["forward_selection"]["kendall_tau_vs_observed_loss"] == pytest.approx(0.8)
    for name in ("shapley", "banzhaf", "binomial_q025", "leave_one_in"):
        assert rules[name]["kendall_tau_vs_observed_loss"] == pytest.approx(0.2), name
    # Uniform split is constant: tau undefined, and it must not be scored.
    assert rules["uniform_split"]["kendall_tau_vs_observed_loss"] is None
    assert rules["uniform_split"]["degenerate_constant_vector"] is True


def test_baselines_reproduce_the_published_shapley_and_loo() -> None:
    """The recovered lattice must agree with the values already in the paper,
    otherwise the new comparison is measuring a different game."""
    data = json.loads((REPO / "artefacts" / "attribution_baselines.json").read_text())
    pool = json.loads((REPO / "artefacts" / "pool_sensitivity.json").read_text())
    ref = pool["ml_1m"]["pools"]["union_of_top_n"]
    for g in ("cf", "ct", "pop", "rec", "seq"):
        assert data["rules"]["shapley"]["values"][g] == pytest.approx(
            ref["shapley"][g], abs=1e-12), g
        assert data["rules"]["loo_rank"]["values"][g] == pytest.approx(
            ref["loo"][g], abs=1e-12), g
