"""The KAIS port must carry the KBS manuscript over without changing content.

The risk this guards is drift: paper-kais/kais-article.tex is generated, and a
hand edit to either file could silently desynchronise the two submissions so
that one journal sees different numbers from the other.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KBS = REPO / "paper-kbs" / "kbs-article.tex"
KAIS = REPO / "paper-kais" / "kais-article.tex"


def _kbs_body(text: str) -> str:
    return text[text.index(r"\section{Introduction}"):
                text.index(r"\section*{CRediT authorship contribution statement}")].rstrip()


def _kais_body(text: str) -> str:
    return text[text.index(r"\section{Introduction}"):
                text.index(r"\backmatter")].rstrip()


def _demote(body: str) -> str:
    return re.sub(r"\\(begin|end)\{(table|figure)\*\}", r"\\\1{\2}", body)


def test_bodies_agree_modulo_float_demotion() -> None:
    """The only permitted body difference is table*/figure* -> table/figure."""
    assert _demote(_kbs_body(KBS.read_text())) == _kais_body(KAIS.read_text())


def test_no_starred_floats_survive() -> None:
    """A starred float in a single-column class can be deferred or lost."""
    body = _kais_body(KAIS.read_text())
    assert r"\begin{table*}" not in body
    assert r"\begin{figure*}" not in body


def test_float_demotion_is_not_vacuous() -> None:
    """Guard the guard: if the KBS file had no starred floats the test above
    would pass for the wrong reason."""
    assert _kbs_body(KBS.read_text()).count(r"\begin{table*}") > 5


def test_abstracts_agree() -> None:
    kbs = KBS.read_text()
    kais = KAIS.read_text()
    a1 = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", kbs, re.S).group(1).strip()
    a2 = kais[kais.index(r"\abstract{") + len(r"\abstract{"):
              kais.index(r"\keywords{")].strip().rstrip("}").strip()
    assert a1 == a2


def test_no_elsevier_markup_in_springer_file() -> None:
    """cas-dc front-matter macros are undefined under sn-jnl."""
    text = re.sub(r"(?<!\\)%.*", "", KAIS.read_text())
    for macro in (r"\ead", r"\credit", r"\cormark", r"\cortext",
                  r"\printcredits", r"\shorttitle", r"\shortauthors",
                  "elsarticle", "cas-dc", r"\begin{keywords}"):
        assert macro not in text, macro


def test_natbib_not_loaded_twice() -> None:
    """sn-jnl.cls loads natbib itself under sn-basic+Numbered; loading it in
    the preamble as the Elsevier build did is an option clash."""
    preamble = KAIS.read_text().split(r"\begin{document}")[0]
    preamble = re.sub(r"(?<!\\)%.*", "", preamble)
    assert "natbib" not in preamble


def test_class_and_bst_are_vendored() -> None:
    """Springer requires the style files in the submission, and unlike
    cas-dc.cls these are LPPL and redistributable."""
    for name in ("sn-jnl.cls", "sn-basic.bst"):
        assert (REPO / "paper-kais" / name).is_file()


def test_generator_is_reproducible() -> None:
    """Re-running the generator must not change the committed file."""
    before = KAIS.read_text()
    subprocess.run([sys.executable, "scripts/make_kais.py"],
                   cwd=REPO, check=True, capture_output=True)
    assert KAIS.read_text() == before
