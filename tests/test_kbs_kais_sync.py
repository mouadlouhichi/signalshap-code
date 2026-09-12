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
    """Undo the intended, purely typographic and venue-naming differences."""
    for env in ("table", "figure", "algorithm"):
        body = body.replace(f"\\begin{{{env}*}}", f"\\begin{{{env}}}")
        body = body.replace(f"\\end{{{env}*}}", f"\\end{{{env}}}")
    body = body.replace(r"\paragraph{", r"\subsubsection{")
    body = body.replace(r"\includegraphics[width=\columnwidth]{Fig3.png}",
                        r"\includegraphics[width=0.7\textwidth]{Fig3.png}")
    # "Online Resource 1" is Springer's term for the supplement; Elsevier uses
    # "supplementary material". A venue leak, so the generator rewrites it.
    # Elsevier says "supplementary material", Springer says "Online Resource".
    body = body.replace(
        "Appendix~A, the supplementary material accompanying this article, "
        "contains",
        "Online Resource~1 (Electronic Supplementary Material; ESM) contains")
    body = body.replace("Supplementary Table~S", "ESM Table~S")
    body = body.replace("Supplementary Section~S", "ESM~S")
    # The two explicit \FloatBarrier calls are dropped from the two-column
    # build: each follows a starred float and pins it, leaving slack beside it.
    body = body.replace("\\FloatBarrier\n", "")
    # The KAIS source carries @@ESMTAB:label@@ placeholders, which the
    # generator resolves against the supplement's real table numbering.
    body = re.sub(r"(?:ESM|Supplementary) Table~S\d+", "@@ESMTAB@@", body)
    body = re.sub(r"@@ESMTAB:[^@]+@@", "@@ESMTAB@@", body)
    return body


def test_bodies_agree_modulo_the_publisher_wrapper() -> None:
    """Compared on whitespace-collapsed text: the generator rewrites some
    sentences, and LaTeX line wrapping differs afterwards without any content
    differing."""
    a = " ".join(_normalise(_kbs_body(KBS.read_text())).split())
    b = " ".join(_normalise(_kais_body(KAIS.read_text())).split())
    assert a == b


def test_every_reported_number_is_identical() -> None:
    """The layout parameter in \\includegraphics is the only permitted
    numeric difference, and it is not a result."""
    def nums(t: str) -> list[str]:
        t = re.sub(r"(?<!\\)%.*", "", t)
        t = re.sub(r"\\includegraphics\[[^\]]*\]", "", t)
        return re.findall(r"[-+]?\d*\.\d+|\d+", t)

    # ESM table numbers are resolved from placeholders by the generator, so
    # they are structurally absent on the KAIS side; strip them both ways.
    def clean(t: str) -> list[str]:
        t = re.sub(r"(?:ESM|Supplementary) Table~S\d+", " ", t)
        t = re.sub(r"(?:ESM|Supplementary Section)~S\d+", " ", t)
        t = re.sub(r"@@ESMTAB:[^@]+@@", " ", t)
        # "Online Resource~1" carries a numeral that the Elsevier rewrite
        # drops. It names the supplement, not a result.
        t = t.replace("Online Resource~1", "the supplement")
        return nums(t)

    assert clean(_kais_body(KAIS.read_text())) == clean(_kbs_body(KBS.read_text()))


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
    # Lower bound only. The count fell from 18 to 9 when stacked and thin
    # headings were merged to reduce white space in the two-column build, so
    # this guards the conversion, not the heading count.
    assert text.count(r"\paragraph{") >= 5


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


def test_esm_table_citations_point_at_the_right_table() -> None:
    """Hand-written S-numbers desynchronised: after the supplement was
    restructured, three of the four cited numbers pointed at the wrong table
    (repeat audit cited S8/renders S9, estimands S9/S10, provenance S3/S4).
    The numbers are now computed, so this pins the resolution."""
    sys.path.insert(0, str(REPO / "scripts"))
    import importlib
    mod = importlib.import_module("make_kbs_from_kais")

    numbering = mod.esm_table_numbers(KBS_ESM.read_text())
    inverse = {v: k for k, v in numbering.items()}
    main = KBS.read_text()

    # Each claim must cite the table that actually carries it.
    expected = {
        "tab:repeat": "not already in their training history",
        "tab:estimands": "All three estimands are reported side by side",
        "tab:provenance": "lists which group is which",
        "tab:analytic": "maximum absolute error",
    }
    for label, phrase in expected.items():
        number = numbering[label].replace("ESM Table~S", "Supplementary Table~S")
        assert phrase in main, f"anchor prose for {label} missing"
        idx = main.index(phrase)
        # The citation may sit just before or just after its anchor phrase.
        window = main[max(0, idx - 200):idx + 400]
        assert number in window, (
            f"{label} renders as {number} but the citation near "
            f"{phrase!r} does not use that number")

    for m in re.finditer(r"Supplementary Table~S\d+", main):
        key = m.group(0).replace("Supplementary Table~S", "ESM Table~S")
        assert key in inverse, f"{m.group(0)} does not exist in the supplement"


def test_no_springer_supplement_terminology_in_the_elsevier_build() -> None:
    """"Online Resource 1" is Springer's name for supplementary material."""
    assert "Online Resource" not in KBS.read_text()
    assert "Online Resource" not in KBS_ESM.read_text()


def test_cover_letter_targets_the_right_journal() -> None:
    letter = (REPO / "paper-kbs-elsevier" / "cover-letter.tex").read_text()
    assert "Knowledge-Based Systems" in letter
    assert "Knowledge and Information Systems" not in letter


# --- heading density: the two-column build was fragmented ------------------ #

def _heading_chunks(path):
    """Yield (level, title, prose_word_count) for the body of a manuscript."""
    t = path.read_text()
    start = t.index(r"\section{Introduction}")
    for end_marker in (r"\section*{CRediT", r"\backmatter"):
        if end_marker in t:
            body = t[start:t.index(end_marker)]
            break
    pat = re.compile(r"^\\(section|subsection|subsubsection|paragraph)\{([^}]*)\}",
                     re.M)
    marks = [(m.start(), m.group(1), m.group(2)) for m in pat.finditer(body)]
    marks.append((len(body), "END", ""))

    def words(chunk: str) -> int:
        chunk = re.sub(r"(?<!\\)%.*", "", chunk)
        chunk = re.sub(
            r"\\begin\{(table|figure|algorithm|tikzpicture)\*?\}.*?"
            r"\\end\{\1\*?\}", "", chunk, flags=re.S)
        chunk = re.sub(r"\$[^$]*\$", " X ", chunk)
        chunk = re.sub(r"\\[a-zA-Z@]+\*?(\[[^\]]*\])?", " ", chunk)
        return len(re.sub(r"[{}&\\]", " ", chunk).split())

    for i in range(len(marks) - 1):
        st, lvl, name = marks[i]
        yield lvl, name, words(body[st:marks[i + 1][0]]) - len(name.split())


def test_no_heading_is_immediately_followed_by_another() -> None:
    """A heading with no prose before the next heading burns vertical space
    twice and reads as a gap. Four such pairs existed in both builds."""
    for path in (KBS, KAIS):
        stacked = [(l, n) for l, n, w in _heading_chunks(path) if w == 0]
        assert not stacked, f"{path.name}: empty headings {stacked}"


def test_no_subsection_is_too_thin_to_justify_a_heading() -> None:
    """Sub-70-word sections fragment a two-column page. Six existed."""
    for path in (KBS, KAIS):
        thin = [(l, n, w) for l, n, w in _heading_chunks(path)
                if l in ("subsection", "subsubsection", "paragraph") and w < 50]
        assert not thin, f"{path.name}: thin sections {thin}"


def test_two_column_float_parameters_are_set_in_the_elsevier_build() -> None:
    """Starred floats obey \\dbltopfraction, not \\topfraction. Eleven of the
    twelve body floats are starred, so leaving these at the LaTeX defaults
    deferred wide tables onto half-empty float pages."""
    text = KBS.read_text()
    for macro in (r"\dbltopfraction", r"\dblfloatpagefraction",
                  r"dbltopnumber"):
        assert macro in text, f"{macro} not set in the two-column build"


def test_kais_does_not_set_two_column_float_parameters() -> None:
    """The Springer build is single column; \\dbltop* would be meaningless."""
    assert r"\dbltopfraction" not in KAIS.read_text()


def test_source_has_no_runs_of_blank_lines() -> None:
    for path in (KBS, KAIS):
        assert not re.search(r"\n\s*\n\s*\n", path.read_text()), path.name


def test_two_column_build_fills_pages() -> None:
    r"""\raggedbottom dumps all leftover space at the foot of the page, and in
    two columns that happens once per column on every page. It was inherited
    from the single-column Springer setup. \flushbottom distributes the slack
    into inter-paragraph glue instead, which is what the reported gaps before
    section headings were."""
    text = re.sub(r"(?<!\\)%.*", "", KBS.read_text())
    assert r"\flushbottom" in text
    assert r"\raggedbottom" not in text


def test_kais_keeps_ragged_bottom() -> None:
    """Single column: ragged bottoms are the conventional choice there."""
    assert r"\raggedbottom" in KAIS.read_text()


def test_no_float_barriers_in_the_two_column_body() -> None:
    r"""placeins[section] put a \FloatBarrier at every section head, and two
    more were explicit in the body. Each forces a flush that reads as a gap.
    The \dbltop* parameters handle deferral properly instead."""
    text = KBS.read_text()
    body = text[text.index(r"\section{Introduction}"):]
    assert "\n\\FloatBarrier" not in body
    assert r"\usepackage[section]{placeins}" not in text
    assert r"\usepackage{placeins}" in text


def test_full_width_floats_use_a_full_width_tabular() -> None:
    r"""A starred float spans both columns, but a plain `tabular` inside it
    sets to its natural width, so a table of narrow numeric columns huddles on
    the left and leaves the rest of the span empty. Table 6 (retirement) and
    Table 3 (preconditions) both did this. The fix is `tabular*` with
    `\extracolsep{\fill}`, or `tabularx`."""
    text = KBS.read_text()
    for m in re.finditer(r"\\begin\{table\*\}(.*?)\\end\{table\*\}", text, re.S):
        inner = m.group(1)
        lab = re.search(r"\\label\{([^}]*)\}", inner)
        label = lab.group(1) if lab else "(unlabelled)"
        envs = re.findall(r"\\begin\{(tabularx|tabular\*|tabular)\}", inner)
        assert envs, f"{label}: no tabular found"
        assert "tabular" not in envs or {"tabularx", "tabular*"} & set(envs), (
            f"{label} spans both columns but its tabular is natural width")


def test_extracolsep_present_where_tabular_star_is_used() -> None:
    r"""`tabular*` without `\extracolsep{\fill}` pads the inter-column gap at
    one end rather than distributing it, which looks worse than not stretching
    at all."""
    for path in (KBS, KAIS):
        text = path.read_text()
        for m in re.finditer(r"\\begin\{tabular\*\}\{[^}]*\}\{([^}]*)\}", text):
            assert "extracolsep" in m.group(1), (
                f"{path.name}: tabular* without \\extracolsep: {m.group(1)[:40]}")


def test_no_author_year_citations_under_a_numeric_style() -> None:
    r"""`elsarticle-num.bst` writes bare `\bibitem{key}` with no optional
    author field, so `\citet`, `\citeauthor` and friends have no name to
    typeset and natbib prints a literal "(author?)" into the PDF. Author names
    must be written in the prose and the citation kept numeric."""
    for path in (KBS, KAIS):
        text = re.sub(r"(?<!\\)%.*", "", path.read_text())
        for macro in (r"\citet", r"\citeauthor", r"\citeyear", r"\Citet"):
            assert macro + "{" not in text, (
                f"{path.name} uses {macro}, which renders as (author?) under a "
                f"numeric bibliography style")


def test_elsevier_supplement_naming() -> None:
    """Springer says ESM / Online Resource; Elsevier says supplementary
    material. Leaving the Springer wording signals a re-badged manuscript."""
    text = KBS.read_text() + KBS_ESM.read_text()
    assert "ESM" not in text
    assert "Online Resource" not in text
    assert "Supplementary" in KBS.read_text()


def test_editor_named_venues_all_have_a_recent_entry() -> None:
    """The KAIS handling editor named five venues. TKDD, KDD and ICDM had no
    entry newer than 2018 after the first pass."""
    cited = _cited_entries(
        [KBS, KBS_ESM], REPO / "paper-kbs-elsevier" / "paper.bib")

    def newest(pattern):
        ys = []
        for body in cited.values():
            if re.search(pattern, body):
                y = re.search(r"year = \{?(\d{4})", body)
                if y:
                    ys.append(int(y.group(1)))
        return max(ys) if ys else None

    venues = {
        "TKDE": r"Knowledge and Data Engineering",
        "TKDD": r"Knowledge Discovery from Data",
        "KAIS": r"Knowledge and Information Systems",
        "KDD": r"SIGKDD",
        "ICDM": r"IEEE International Conference on Data Mining",
    }
    for name, pattern in venues.items():
        y = newest(pattern)
        assert y is not None, f"{name}: no citation at all"
        assert y >= 2021, f"{name}: newest citation is {y}"


def test_section_titles_are_distinguishable() -> None:
    """Two subsections were titled 'Which attribution rule predicts removal
    cost?' and 'Which estimand predicts retirement cost?'."""
    text = KBS.read_text()
    titles = re.findall(r"^\\subsection\{([^}]*)\}", text, re.M)
    starts = [t.lower()[:28] for t in titles]
    dupes = {t for t in starts if starts.count(t) > 1}
    assert not dupes, f"near-identical subsection titles: {dupes}"
