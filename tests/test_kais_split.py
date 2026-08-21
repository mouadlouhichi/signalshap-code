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
