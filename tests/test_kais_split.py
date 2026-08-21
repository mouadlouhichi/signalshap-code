"""The KAIS main/ESM split must lose nothing and must resolve everywhere.

Three failure modes this guards:

1. A float silently dropped by the split, so a number the paper relies on is in
   neither document.
2. A `\\ref` in one document pointing at a `\\label` that now lives in the other,
   which pdflatex renders as `??`.
3. Prose drifting away from the artefact-validated numbers, since the main text
   was rewritten by hand while the tables were lifted verbatim.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MAIN = REPO / "paper-kais" / "kais-article.tex"
ESM = REPO / "paper-kais" / "kais-esm.tex"
KBS = REPO / "paper-kbs" / "kbs-article.tex"
ART = REPO / "artefacts"


def _labels(text: str) -> set[str]:
    return set(re.findall(r"\\label\{([^}]*)\}", text))


def _refs(text: str) -> set[str]:
    out: set[str] = set()
    for m in re.finditer(r"\\(?:ref|eqref|autoref)\{([^}]*)\}", text):
        out.add(m.group(1))
    return out


def test_every_reference_resolves_within_its_own_document() -> None:
    """Springer compiles the two files separately, so a cross-document \\ref
    would render as ??."""
    for path in (MAIN, ESM):
        text = path.read_text()
        text = re.sub(r"(?<!\\)%.*", "", text)
        missing = _refs(text) - _labels(text)
        assert not missing, f"{path.name} has unresolved refs: {sorted(missing)}"


def test_no_float_is_lost_between_main_and_esm() -> None:
    """Every labelled float in the source manuscript must survive somewhere."""
    sys.path.insert(0, str(REPO / "scripts"))
    from extract_floats import float_blocks

    source_labels = set(float_blocks(KBS.read_text()))
    kept = _labels(MAIN.read_text()) | _labels(ESM.read_text())
    # tab:notation etc. must all land in one of the two documents.
    lost = source_labels - kept
    assert not lost, f"floats dropped by the split: {sorted(lost)}"


def test_main_text_display_item_budget() -> None:
    """KAIS charges 500 words per full-page display item; the plan caps main
    text at a small number."""
    text = MAIN.read_text()
    n = (len(re.findall(r"\\begin\{table\}", text))
         + len(re.findall(r"\\begin\{figure\}", text))
         + len(re.findall(r"\\begin\{algorithm\}", text)))
    assert n <= 10, f"{n} display items in main text"


def test_no_starred_floats_in_either_document() -> None:
    """Both documents are single column; a starred float can be lost."""
    for path in (MAIN, ESM):
        text = path.read_text()
        assert r"\begin{table*}" not in text, path.name
        assert r"\begin{figure*}" not in text, path.name


def test_abstract_is_within_springer_window() -> None:
    text = MAIN.read_text()
    abstract = text[text.index(r"\abstract{") + len(r"\abstract{"):
                    text.index(r"\keywords{")]
    abstract = abstract.strip().rstrip("}").strip()
    words = len(re.sub(r"\\[a-zA-Z]+", " ", abstract).split())
    assert 150 <= words <= 250, f"abstract is {words} words"


def test_abstract_has_no_machine_epsilon_theatre() -> None:
    """Unit-test residuals do not belong in an abstract."""
    text = MAIN.read_text()
    abstract = text[text.index(r"\abstract{"):text.index(r"\keywords{")]
    assert "10^{-18}" not in abstract
    assert "10^{-16}" not in abstract


def test_title_does_not_lead_with_the_coined_name() -> None:
    text = MAIN.read_text()
    title = re.search(r"\\title\[[^\]]*\]\{(.*?)\}\n", text, re.S).group(1)
    assert not title.strip().startswith("SignalShap"), title


def test_banned_phrases_absent_from_both_documents() -> None:
    """Phrases previous reviewers required be removed. The KAIS playbook's
    own suggested abstract reintroduced 'cheapest source', so this is a live
    risk, not a hypothetical one."""
    banned = ["cheapest source", "pre-registered", "predeclared",
              "build-or-retire", "true loss", "true cost", "Shapley shares"]
    for path in (MAIN, ESM):
        flat = " ".join(path.read_text().lower().split())
        for phrase in banned:
            assert phrase.lower() not in flat, f"{phrase!r} in {path.name}"


def test_no_em_dashes() -> None:
    for path in (MAIN, ESM):
        raw = path.read_text()
        body = raw[raw.index(r"\begin{document}"):]
        body = re.sub(r"(?<!\\)%.*", "", body)
        assert "\u2014" not in body, path.name
        assert not re.search(r"(?<!-)---(?!-)", body), path.name


# --- numbers in the rewritten prose must match the artefacts ---------------- #

def test_headline_retirement_numbers_match_artefact() -> None:
    seeds = json.loads((ART / "final_retirement_seeds.json").read_text())
    text = MAIN.read_text()
    taus = []
    for corpus in ("ml_1m", "amazon_video_games", "gowalla_ts"):
        rec = seeds[corpus]
        taus.append(round(rec["tau_loo"]["mean"], 2))
    # The main text states LOO mean agreement as 0.96, 0.96 and 1.00.
    assert taus == [0.96, 0.96, 1.00], taus
    assert "$0.96$, $0.96$ and $1.00$" in text


def test_sampling_error_numbers_match_artefact() -> None:
    data = json.loads((ART / "sampling_error.json").read_text())
    p95 = data["budgets"]["500"]["permutation"]["relative_to_v_grand_p95"]
    assert f"{p95 * 100:.2f}" == "2.73", p95
    assert "2.73\\%" in MAIN.read_text()


def test_material_flip_fractions_match_artefact() -> None:
    ci = json.loads((ART / "final_seed_ci.json").read_text())
    text = MAIN.read_text()
    # cf on ML-1M: gap 0.02030 as a fraction of v(G)=0.05225 is 38.8%.
    gap = ci["ml_1m"]["gap_ci"]["cf"]["mean"]
    assert f"{gap:.5f}" == "0.02030", gap
    assert "38.8\\%" in text
    # pop on Gowalla: 0.00207 of 0.01705 is 12.2%, not 12.1%.
    gap_g = ci["gowalla_ts"]["gap_ci"]["pop"]["mean"]
    assert f"{gap_g:.5f}" == "0.00207", gap_g
    assert "12.2\\%" in text


def test_generator_is_reproducible() -> None:
    before_main, before_esm = MAIN.read_text(), ESM.read_text()
    subprocess.run([sys.executable, "scripts/make_kais_main.py"],
                   cwd=REPO, check=True, capture_output=True)
    assert MAIN.read_text() == before_main
    assert ESM.read_text() == before_esm


def test_conditionals_are_declared_before_use() -> None:
    """A \\newif dropped from the preamble makes \\iftikzfigure an undefined
    control sequence and kills the compile inside Figure 1. This actually
    happened while building the split, so the guard is not hypothetical.

    Comments are stripped first: the preamble commentary explains the hazard
    and would otherwise register as the first use.
    """
    for path in (MAIN, ESM):
        text = re.sub(r"(?<!\\)%.*", "", path.read_text())
        first_use = text.find(r"\iftikzfigure")
        if first_use == -1:
            continue
        decl = text.find(r"\newif\iftikzfigure")
        assert decl != -1, f"{path.name} uses \\iftikzfigure without \\newif"
        assert decl <= first_use, f"{path.name} declares it after first use"


# --- regression guards for the round-2 audit blockers ---------------------- #

def test_every_cite_key_exists_in_the_bib() -> None:
    """B2: three keys had wrong year suffixes and rendered as [?]. A desk
    editor who skims page 4 bounces that as incomplete."""
    tex = MAIN.read_text() + ESM.read_text()
    used: set[str] = set()
    for m in re.finditer(r"\\cite[a-z]*\{([^}]*)\}", tex):
        used |= {k.strip() for k in m.group(1).split(",")}
    bib = set(re.findall(r"@\w+\{([^,]+),",
                         (REPO / "paper-kais" / "paper.bib").read_text()))
    assert not used - bib, f"undefined cite keys: {sorted(used - bib)}"


def test_core_artefacts_of_the_field_are_cited() -> None:
    """B5: a recsys reviewer reading 'we use MovieLens-1M, ALS, NDCG@10' with
    no citations reads it as sloppy, not as brevity."""
    tex = MAIN.read_text()
    for key in ("harper2015movielens", "cho2011friendship", "ni2019justifying",
                "hu2008collaborative", "levy2014neural",
                "jarvelin2002cumulated", "grabisch1999",
                "wilcoxon1945", "holm1979"):
        assert key in tex, f"{key} is used in the text but never cited"


def test_reference_count_is_defensible() -> None:
    tex = MAIN.read_text() + ESM.read_text()
    used: set[str] = set()
    for m in re.finditer(r"\\cite[a-z]*\{([^}]*)\}", tex):
        used |= {k.strip() for k in m.group(1).split(",")}
    assert len(used) >= 30, f"only {len(used)} references cited"


def test_algorithm_equation_pointers_are_correct() -> None:
    """B4: Algorithm 1 pointed at Eq. (3) for standardisation and Eq. (4) for
    the baseline, which were candidate construction and the characteristic
    function. That made the algorithm unimplementable from the PDF."""
    tex = MAIN.read_text()
    alg = re.search(r"\\begin\{algorithm\}(.*?)\\end\{algorithm\}",
                    tex, re.S).group(1)
    # The standardisation and baseline lines must name their own equations.
    assert "eq:zscore" in alg, "algorithm does not reference the z-norm equation"
    assert "eq:baseline" in alg, "algorithm does not reference the baseline"
    for label in ("eq:zscore", "eq:baseline", "eq:candidates"):
        assert f"\\label{{{label}}}" in tex, f"{label} referenced but never defined"


def test_algorithm_is_placed_in_its_own_subsection() -> None:
    """B4: the float drifted to page 11, several pages past its discussion."""
    tex = MAIN.read_text()
    alg = tex.index(r"\begin{algorithm}")
    sec_algorithm = tex.index(r"\subsection{Algorithm and cost}")
    sec_next = tex.index(r"\subsection{Formal properties}")
    assert sec_algorithm < alg < sec_next, "Algorithm 1 is outside section 3.2"


def test_sampling_artefact_declares_which_game_it_used() -> None:
    """B3: the figure must not silently be computed on a different game from
    the one the prose claims."""
    data = json.loads((ART / "sampling_error.json").read_text())
    assert data["game"] in ("ranking_stage_ndcg10", "end_to_end_recall")
    if data["game"] == "end_to_end_recall":
        assert "FALLBACK" in data["caveat"]
        # The manuscript must then disclose the substitution, not hide it.
        assert "recall game" in MAIN.read_text()


def test_amazon_larger_cap_is_in_the_preconditions_table() -> None:
    """R1: showing only the failing cap invites 'why is this corpus here?'."""
    tex = MAIN.read_text()
    table = re.search(r"\\label\{tab:preconditions\}(.*?)\\end\{table\}",
                      tex, re.S).group(1)
    assert "1\\,200" in table, "the gate-clearing cap is not a row"
    assert "0.750" in table


def test_wilcoxon_is_not_framed_as_population_inference() -> None:
    """B6: the Table 5 caption contradicted the retirement subsection."""
    tex = MAIN.read_text()
    assert "primary family" not in tex


def test_no_nested_table_reference_in_footnotes() -> None:
    """B6: a retargeted \\ref produced 'Table~ESM Table~S8'."""
    assert "Table~ESM" not in MAIN.read_text()
    assert "Table ESM Table" not in MAIN.read_text()


def test_tikz_folds_do_not_justify_their_text() -> None:
    """B6: `align=center` with a fixed text width justified VALIDATION across
    the node, rendering as 'V ALIDA TION' in the PDF."""
    tex = MAIN.read_text()
    fold = re.search(r"snfold/\.style=\{(.*?)\}", tex, re.S).group(1)
    assert "align=flush center" in fold, (
        "snfold justifies its text; VALIDATION will be letter-spaced")


def test_esm_pointers_resolve_to_the_right_supplement_items() -> None:
    """B1/R: the main article cites the supplement by S-number. Two were wrong
    by hand (analytic games cited as S1 but rendering as S4; fusion as S5 but
    rendering as S6), so the numbers are now computed from the ESM."""
    sys.path.insert(0, str(REPO / "scripts"))
    import importlib
    mod = importlib.import_module("make_kais_main")

    numbering = mod.esm_numbering(ESM.read_text())
    main = MAIN.read_text()

    # Each claim in the main text must point at the item that carries it.
    expected = {
        "tab:analytic": "analytic games",
        "tab:estimands": "three estimands",
        "tab:provenance": "provenance",
        "tab:repeats": "repeat audit",
        "esm:fusion": "fusion negative result",
        "esm:proofs": "counterexample",
        "esm:robustness": "robustness suite",
    }
    for label in expected:
        assert label in numbering, f"{label} has no S-number"
        assert numbering[label] in main, (
            f"{label} renders as {numbering[label]} but the main text never "
            f"cites that number")


def test_no_unresolved_esm_placeholders() -> None:
    for path in (MAIN, ESM):
        assert "@@ESM:" not in path.read_text(), path.name
