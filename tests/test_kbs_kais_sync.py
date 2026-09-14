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
ART = REPO / "artefacts"


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


# --- reviewer round 3: Q1 (estimand-matched game) and Q3 (regime) ---------- #

def _q1q3():
    return json.loads((REPO / "artefacts" / "reviewer_q1_q3.json").read_text())


def test_estimand_matched_shapley_still_fails() -> None:
    """Q1: the reviewer asked whether Shapley recovers the retirement ordering
    once the game matches the intervention. It does not, and the claim in the
    text must track the artefact."""
    q1 = _q1q3()["q1_estimand_matched_shapley"]
    assert q1["ml_1m"]["games"]["end_to_end"][
        "kendall_tau_vs_observed_loss"] == pytest.approx(0.4)
    assert q1["amazon_video_games"]["games"]["end_to_end"][
        "kendall_tau_vs_observed_loss"] == pytest.approx(0.8)
    # The load-bearing claim: no Shapley variant nominates the right source,
    # and ranking-stage LOO does on both corpora.
    for corpus in q1.values():
        for game in corpus["games"].values():
            assert game["identifies_correctly"] is False
        assert corpus["loo_rank"]["identifies_correctly"] is True
    text = KBS.read_text()
    assert "+0.40$ on MovieLens-1M" in text
    assert "$+0.80$ on Amazon-VG" in text


def test_regime_dependence_numbers_match() -> None:
    """Q3: LOO_rank holds tau = +1.00 across the observed recall range."""
    q3 = _q1q3()["q3_retrieval_sensitivity"]
    expected = {"ml_1m": "11.9", "amazon_video_games": "8.2",
                "gowalla_ts": "6.1"}
    text = KBS.read_text()
    for corpus, pct in expected.items():
        got = f"{q3[corpus]['largest_drop_relative'] * 100:.1f}"
        assert got == pct, f"{corpus}: artefact {got}%, prose {pct}%"
        assert f"{pct}\\%" in text
        assert q3[corpus]["kendall_tau_loo"] == pytest.approx(1.0)


def test_construct_scope_is_stated_before_the_results() -> None:
    """W2: the candidate set is built from all five sources, so the allocation
    is not end-to-end credit. That has to be said where the construct is
    defined, not only in the threats section."""
    text = KBS.read_text()
    scope = text.index("bounds what the word")
    results = text.index(r"\section{Results}")
    assert scope < results, "construct scope stated after the results"
    assert "not end-to-end credit for source" in text
    assert "systematically understated" in text


def test_refit_interpretation_is_stated() -> None:
    """W3: v(S) is the performance of a refitted coalition system."""
    text = KBS.read_text()
    assert "performance of the" in text and "refitted" in text


def test_estimand_match_table_matches_the_artefacts() -> None:
    """Reviewer: the +1.00 for LOO is seed 42 while Table 7 reports a 0.96
    ten-seed mean. Both are right, but the text was ambiguous. The comparison
    table is seed-42 only and must say so, and every cell must come from the
    artefacts."""
    from scipy import stats

    players = ("cf", "ct", "pop", "rec", "seq")
    text = KBS.read_text()
    table = re.search(r"\\label\{tab:estimandmatch\}(.*?)\\end\{tabular\*\}",
                      text, re.S).group(1)

    for corpus in ("ml_1m", "amazon_video_games"):
        est = json.loads((ART / f"e11_estimands_{corpus}.json").read_text())
        ret = json.loads((ART / f"e12_retirement_{corpus}.json").read_text())
        observed = ret["true_retirement_loss"]
        target = [observed[g] for g in players]
        correct = min(players, key=lambda g: observed[g])
        assert f"observed: ${correct}$" in text, corpus

        for game in ("refit_head", "fixed_head", "end_to_end"):
            phi = est[game]["shapley"]
            tau, _ = stats.kendalltau([phi[g] for g in players], target)
            assert f"${tau:+.2f}$" in table, f"{corpus}/{game} tau {tau:+.2f}"
            pick = min(players, key=lambda g: phi[g])
            assert f"${pick}$" in table, f"{corpus}/{game} pick {pick}"
            # The load-bearing claim.
            assert pick != correct, (
                f"{corpus}/{game} now picks correctly; the text says none do")


def test_seed_provenance_of_the_estimand_paragraph_is_explicit() -> None:
    """The ambiguity the reviewer flagged: a seed-42 tau sitting beside a
    ten-seed mean with nothing distinguishing them."""
    text = KBS.read_text()
    assert "seed 42, the single seed" in text
    assert "are the primary evidence" in text


def test_e2e_game_is_defined_not_only_described() -> None:
    """Reviewer asked for v_e2e to be as explicit as Eq. (5), including how
    the baseline and empty candidate sets are handled."""
    text = KBS.read_text()
    assert r"\label{eq:e2e}" in text
    for detail in ("re-evaluated on $C_u(S)$", "contributes $0$",
                   r"v_{\mathrm{e2e}}(\varnothing)=0"):
        assert detail in text, detail


def test_seq_is_not_called_sequential_before_its_caveat() -> None:
    """Reviewer (minor): 'sequential' misleads; the signal is symmetric
    co-occurrence with recency weighting. The abstract and introduction
    reached the reader before the caveat in the source table."""
    text = KBS.read_text()
    head = text[:text.index(r"\label{tab:sources}")]
    assert "and sequential signals" not in head
    assert "and sequential sources" not in head
    assert "short-term" in head


def test_regime_paragraph_labels_its_seed_and_the_ten_seed_means() -> None:
    """Reviewer round 4, required edit 1. The regime-dependence paragraph put
    a seed-42 tau of +1.00 next to a table of ten-seed means (0.96/0.96/1.00)
    with nothing distinguishing them. Both are correct; the text was silent.
    Note the reviewer's own suggested fix (write 0.96-1.00) would have been
    wrong: it would mix ten-seed taus with seed-42 recall drops."""
    text = KBS.read_text()
    para = text[text.index("Regime dependence"):]
    para = para[:para.index(r"\emph{External.}")]
    assert "seed 42" in para, "regime paragraph does not name its seed"

    seeds = json.loads((ART / "final_retirement_seeds.json").read_text())
    means = [round(seeds[c]["tau_loo"]["mean"], 2)
             for c in ("ml_1m", "amazon_video_games", "gowalla_ts")]
    assert means == [0.96, 0.96, 1.00], means
    assert "$0.96$, $0.96$ and $1.00$" in para, (
        "ten-seed means not quoted alongside the seed-42 figure")

    # And the seed-42 figure it quotes must be real.
    for corpus in ("ml_1m", "amazon_video_games", "gowalla_ts"):
        j = json.loads((ART / f"e12_retirement_{corpus}.json").read_text())
        assert j["kendall_tau_loo_vs_truth"] == pytest.approx(1.0)


def test_sequential_only_describes_cited_work_or_the_caveat() -> None:
    """Reviewer round 4, required edit 2. Our own source is short-term
    co-occurrence. The word 'sequential' may remain only where it names a
    cited paper's topic or the SASRec contrast that defines the caveat."""
    text = KBS.read_text()
    allowed = (
        "sequential explainable recommendation",   # cited TKDE paper
        "among sequential",                        # cited ICDM router
        "not a sequential model in the SASRec",    # the caveat itself
    )
    for m in re.finditer(r"[^.]*sequential[^.]*\.", text):
        sentence = " ".join(m.group(0).split())
        assert any(a in sentence for a in allowed), (
            f"'sequential' used for our own source: {sentence[:110]}")


def test_e2e_equation_notation_is_unambiguous() -> None:
    """Reviewer round 4, required edit 3. `Z^{(S)}_u(S)` carried the coalition
    twice and was hard to parse."""
    text = KBS.read_text()
    assert "Z^{(S)}_u(S)" not in text
    assert r"Write $Z_{u,S}$ for" in text
    assert r"\operatorname{rank}(Z_{u,S}" in text


def test_source_label_terminology_is_consistent() -> None:
    """Reviewer round 5, edit 1. `seq` is fine as a math symbol but the prose
    and the table label must agree on the words. The Signal column said
    'Co-occurrence' while the abstract and introduction said 'short-term
    co-occurrence'."""
    text = KBS.read_text()
    assert "$seq$ & Short-term co-occurrence" in text
    # And no bare word-form `seq` outside maths.
    nomath = re.sub(r"\$[^$]*\$", " MATH ", re.sub(r"(?<!\\)%.*", "", text))
    assert not re.search(r"\bseq\b", nomath), "bare 'seq' in prose"


def test_observed_is_defined_where_it_is_used() -> None:
    """Reviewer round 5, edit 2. 'Observed cheapest source' needed a one-line
    definition: end-to-end, same seed and protocol, differenced on raw NDCG@10
    rather than on the baseline-centred v."""
    text = KBS.read_text()
    caption = re.search(r"\\caption\{Estimand-matched comparison(.*?)\}\s*\n\\label",
                        text, re.S).group(1)
    for phrase in ("removed from retrieval and fusion",
                   "candidates are rebuilt", "raw", "NDCG@10",
                   "baseline therefore moves"):
        assert phrase in caption, f"caption missing: {phrase}"


def test_observed_definition_matches_the_artefact() -> None:
    """The caption claims the loss differences raw utility, not centred v.
    The artefact records both, so the claim is checkable."""
    j = json.loads((ART / "e12_retirement_ml_1m.json").read_text())
    raw = j["true_retirement_loss"]
    centred = j["retirement_loss_centred_legacy"]
    shift = j["baseline_shift_after_removal"]
    # centred = raw + baseline shift, so they are genuinely different objects
    # and the caption is distinguishing something real.
    for g in raw:
        assert centred[g] == pytest.approx(raw[g] + shift[g], abs=1e-9), g
    assert any(abs(shift[g]) > 1e-6 for g in shift), (
        "baseline shift is negligible; the caption's distinction would be moot")


def test_materiality_percentages_state_their_denominator() -> None:
    """Reviewer round 6, edit 2. The paper quotes 1e-3 both absolutely and as a
    percentage of v(G), but v(G) differs between the seed-42 sampling study
    (0.051689) and the ten-seed attribution results (0.05225). 1.93% and 1.91%
    are both correct against their own denominator; the text must say which."""
    text = KBS.read_text()
    sampling = json.loads((ART / "fig2_ndcg_sampling.json").read_text())["sampling"]
    v42 = sampling["v_grand"]
    v10 = 0.05225

    # The two percentages must be arithmetically right.
    assert f"{1e-3 / v42 * 100:.2f}" == "1.93", v42
    assert f"{1e-3 / v10 * 100:.2f}" == "1.91", v10
    # And the values they are quoted against must round as printed.
    assert f"{v42:.4f}" == "0.0517"
    assert f"{v10:.4f}" == "0.0522"

    for phrase in (r"$1.93\%$ of the seed-42", r"$1.91\%$ of",
                   r"seed-42 $v(\G) = 0.0517$",
                   r"ten-seed $v(\G) = 0.0522$",
                   "use the ten-seed denominator"):
        assert phrase in text, f"missing: {phrase}"
    # Guard the rounding itself: 0.05225 prints as 0.0522, not 0.0523.
    assert r"$v(\G) = 0.0523$" not in text


def test_flip_ratios_use_the_ten_seed_denominator() -> None:
    """The 38.8% and 12.2% figures the text attributes to the ten-seed basis
    must actually be computed that way."""
    ci = json.loads((ART / "final_seed_ci.json").read_text())
    cf = ci["ml_1m"]["gap_ci"]["cf"]["mean"]
    pop = ci["gowalla_ts"]["gap_ci"]["pop"]["mean"]
    assert f"{cf / 0.05225 * 100:.1f}" == "38.8"
    assert f"{pop / 0.01705 * 100:.1f}" == "12.2"


def test_prose_names_the_source_consistently() -> None:
    """Reviewer round 6, edit 1: standardise on co-occurrence in prose."""
    text = re.sub(r"(?<!\\)%.*", "", KBS.read_text())
    nomath = re.sub(r"\$[^$]*\$", " M ", text)
    assert not re.search(r"\bseq\b", nomath), "bare 'seq' in prose"
    # Every sentence that still says "sequential" must be about cited work or
    # the SASRec caveat, never about our own source.
    allowed = ("sequential explainable recommendation", "among sequential",
               "not a sequential model in the SASRec")
    for m in re.finditer(r"[^.]*sequential[^.]*\.", nomath):
        sentence = " ".join(m.group(0).split())
        assert any(a in sentence for a in allowed), sentence[:110]


def test_source_symbols_are_glossed_in_running_text() -> None:
    """Reviewer round 7, editorial 1. `seq` is fine as a symbol, but a reader
    meeting it in running text should not have to page back to Table 2. The
    first occurrence inside each results subsection is a table row label, where
    expanding the name would break the column, so the gloss sits on the first
    genuine prose use and on the orderings sentence."""
    text = KBS.read_text()
    assert "substitutive with co-occurrence ($seq$) and popularity ($pop$)" in text
    assert "short-term co-occurrence $seq$), are" in text


def test_materiality_gate_is_stated_as_absolute() -> None:
    """Reviewer round 7, editorial 2. Readers could take the percentage for
    the test. The gate is the absolute 1e-3 comparison; percentages are
    interpretive only."""
    text = KBS.read_text()
    assert r"The gate itself is" in text
    assert r"\emph{absolute}" in text
    assert "never as the test" in text
