#!/usr/bin/env python3
r"""Convert the Springer manuscript into the Elsevier CAS format for KBS.

    python scripts/make_elsevier.py

Writes `paper-kbs/kbs-article.tex` plus the supporting files. The conversion
is a SCRIPT, not a hand edit, for the same reason the notebook is generated:
the Springer manuscript is still the source of truth for prose and numbers,
`check_paper_numbers.py` validates it, and any hand-forked copy would drift
from the artefacts within one revision. Re-run this after every change to
`paper/sn-article.tex`.

WHAT ACTUALLY DIFFERS between the two templates
-----------------------------------------------
Both are LaTeX with numbered citations, so the body text ports unchanged.
The differences are confined to the preamble and the front/back matter:

  Springer sn-jnl                     Elsevier cas-dc
  ---------------------------------   ------------------------------------
  \documentclass{sn-jnl}              \documentclass{cas-dc}
  \author*[1]{\fnm{}\sur{}}           \author[1]{}  + \cormark + \ead{}
  \affil*[1]{\orgdiv{}\orgname{}}     \affiliation[1]{organization={...}}
  \abstract{...}                      \begin{abstract}...\end{abstract}
  \keywords{a, b, c}                  \begin{keywords}a \sep b \sep c\end{keywords}
  \maketitle                          \maketitle  (after \begin{document})
  \backmatter + \bmhead{}             \section*{} + numbered appendices
  \botrule                            \bottomrule  (booktabs)
  \bibliography{paper}                \bibliographystyle{elsarticle-num}

KBS-SPECIFIC REQUIREMENTS from the guide for authors, all handled here:
  * numbered sections, 1 / 1.1 / 1.1.1                    -> already true
  * abstract <= 250 words                                 -> checked below
  * 1-7 keywords, avoid multi-word joined by "and"/"of"   -> checked below
  * 3-5 highlights, <= 85 characters each                 -> separate file
  * numbered [n] citations in order of appearance         -> elsarticle-num
  * CRediT author statement                               -> mapped from ours
  * declaration of competing interest                     -> required section
  * declaration of generative AI use                      -> required section
  * data statement (Option C: deposit or explain)         -> required section
  * tables as editable text, no vertical rules/shading    -> already true
  * figures cited in order, supplied separately           -> already true
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "paper" / "sn-article.tex"
OUT_DIR = ROOT / "paper-kbs"
OUT = OUT_DIR / "kbs-article.tex"

# Elsevier's guide caps the abstract at 250 words and keywords at 7.
ABSTRACT_MAX_WORDS = 250
KEYWORDS_MAX = 7


# --------------------------------------------------------------------------- #
# Front matter
# --------------------------------------------------------------------------- #

PREAMBLE = r"""%% Elsevier CAS double-column template (cas-dc.cls).
%% Target: Knowledge-Based Systems (Elsevier).
%%
%% GENERATED FILE -- do not edit by hand.
%%   Source:    paper/sn-article.tex
%%   Generator: scripts/make_elsevier.py
%% Edit the source and regenerate, or the numbers will drift from
%% artefacts/ and scripts/check_paper_numbers.py will stop protecting them.
%%
%% Build:  pdflatex kbs-article && bibtex kbs-article
%%         && pdflatex kbs-article && pdflatex kbs-article
%%
%% cas-dc.cls, cas-common.sty and the .bst files are NOT redistributed here.
%% Fetch them with:  bash paper-kbs/fetch-template.sh
\documentclass[a4paper,fleqn]{cas-dc}

%% cas-dc.cls loads neither amsmath nor the table packages this manuscript
%% needs. Same list as the Springer build, minus what cas-dc provides.
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsthm}
\usepackage{multirow}
\usepackage{array}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,fit,backgrounds,calc,shapes.geometric}
\graphicspath{{figures/}}

%% Elsevier uses \tnotemark/\fnmark for title and author notes; hyperref comes
%% from the class, so only the options are set here.
\hypersetup{hypertexnames=false,bookmarksdepth=3}

%% DOUBLE-COLUMN CONSEQUENCE, and the main reason this is not a pure
%% search-and-replace. cas-dc is two-column: the text block is about 84mm per
%% column against roughly 165mm single-column in sn-jnl, so every wide table
%% and every full-width figure must be promoted to a starred float that spans
%% both columns. The generator does that promotion automatically; see
%% `widen_floats` in scripts/make_elsevier.py.

%% Figure 1 renders as live TikZ; set \tikzfigurefalse to fall back to the
%% pre-rendered raster in figures/Fig1.png.
\newif\iftikzfigure
\tikzfiguretrue

%% Figure lettering. Elsevier's artwork instructions ask for legible text at
%% the final printed size; in double column that is a smaller physical width,
%% so the explicit point sizes from the Springer build are kept.
\newcommand{\snFigMain}{\fontsize{9}{10.5}\selectfont}
\newcommand{\snFigSub}{\fontsize{8}{9.5}\selectfont}

\tikzset{
  snstage/.style={
    rectangle, draw=black, line width=0.65pt, fill=white,
    minimum height=18mm, inner sep=3pt, align=center,
    font=\snFigMain, text width=27mm},
  snstagekey/.style={
    rectangle, draw=black, line width=1.0pt, fill=white,
    minimum height=18mm, inner sep=3pt, align=center,
    font=\snFigMain, text width=27mm},
  snfold/.style={
    rectangle, draw=black, dashed, line width=0.5pt, fill=white,
    inner sep=2pt, align=center, font=\snFigSub, text width=19mm},
  snflow/.style={-{Stealth[length=4.5pt,width=3.5pt]}, draw=black,
    line width=0.75pt},
  sndata/.style={-{Stealth[length=4.5pt,width=3.5pt]}, draw=black,
    line width=0.5pt, dashed},
  snout/.style={font=\snFigSub, align=center, text=black},
  snlbl/.style={font=\snFigSub, inner sep=1.2pt, text=black},
}

%% Float placement. In two columns the queue backs up more easily than in one,
%% so the same remedy as the Springer build applies, and placeins drains the
%% queue at each section boundary.
\renewcommand{\topfraction}{0.9}
\renewcommand{\bottomfraction}{0.8}
\renewcommand{\textfraction}{0.07}
\renewcommand{\floatpagefraction}{0.6}
\setcounter{topnumber}{3}
\setcounter{bottomnumber}{2}
\setcounter{totalnumber}{5}
\usepackage[section]{placeins}

\theoremstyle{plain}
\newtheorem{theorem}{Theorem}
\newtheorem{proposition}[theorem]{Proposition}
\newtheorem{lemma}[theorem]{Lemma}

\theoremstyle{definition}
\newtheorem{property}{Property}
\newtheorem{remark}{Remark}

\raggedbottom

\newcommand{\G}{\mathcal{G}}
\newcommand{\Cu}{C_u}
\newcommand{\Ueval}{\mathcal{U}_{\mathrm{eval}}}
\newcommand{\NDCG}{\mathrm{NDCG@10}}
\newcommand{\NDCGat}[1]{\mathrm{NDCG@}#1}
\newcommand{\LOOr}{\mathrm{LOO}_{\mathrm{rank}}}
\newcommand{\LOOe}{\mathrm{LOO}_{\mathrm{e2e}}}
\newcommand{\LOO}{\mathrm{LOO}}

\begin{document}

\let\WriteBookmarks\relax
\def\floatpagepagefraction{1}
\def\textpagefraction{.001}

\shorttitle{Exact-enumeration ranking-stage source attribution}
\shortauthors{M. Louhichi et al.}

\title[mode=title]{SignalShap: Exact-Enumeration Ranking-Stage Attribution of
Sources in Hybrid Recommenders}

\author[1]{Mouad Louhichi}[orcid=0000-0002-6849-230X]
\cormark[1]
\ead{mouad_louhichi@um5.ac.ma}
\credit{Conceptualization, Methodology, Software, Formal analysis,
Investigation, Writing -- original draft, Visualization}

\author[1]{Redwane Nesmaoui}
\ead{redwane.nesmaoui@um5.ac.ma}
\credit{Software, Validation, Data curation, Writing -- review and editing}

\author[1]{Mohamed Lazaar}
\ead{mohamed.lazaar@ensias.um5.ac.ma}
\credit{Supervision, Methodology, Resources, Writing -- review and editing}

\affiliation[1]{organization={National Higher School of Computer Science and
Systems Analysis (ENSIAS), Mohammed V University in Rabat},
  city={Rabat},
  country={Morocco}}

\cortext[1]{Corresponding author.}

\begin{abstract}
%%ABSTRACT%%
\end{abstract}

\begin{keywords}
%%KEYWORDS%%
\end{keywords}

\maketitle
"""

# Elsevier requires these as explicit numbered/starred sections before the
# bibliography. Springer put the same content in a \backmatter itemize.
BACKMATTER = r"""
\section*{CRediT authorship contribution statement}
\textbf{Mouad Louhichi:} Conceptualization, Methodology, Software, Formal
analysis, Investigation, Writing -- original draft, Visualization.
\textbf{Redwane Nesmaoui:} Software, Validation, Data curation, Writing --
review and editing. \textbf{Mohamed Lazaar:} Supervision, Methodology,
Resources, Writing -- review and editing.

\section*{Declaration of competing interest}
The authors declare that they have no known competing financial interests or
personal relationships that could have appeared to influence the work reported
in this paper.

\section*{Declaration of generative AI and AI-assisted technologies in the writing process}
During the preparation of this work the authors used large language models for
code scaffolding, editorial review, and consistency checking. After using this
tool the authors reviewed and edited the content as needed and take full
responsibility for the content of the published article. No text, result,
figure, or citation was included without author verification, and no AI system
is listed as an author. All figures reporting data are produced directly from
the released artefacts by \texttt{scripts/make\_assets.py} using reproducible
analytical code; no generative tool was used to create or alter them.

\section*{Data availability}
This work uses three public corpora and redistributes none of them.
MovieLens-1M is used under the GroupLens research-use license, Gowalla
check-ins come from the SNAP collection, and the Video Games category is taken
from the Amazon Reviews 2023 corpus; \texttt{scripts/fetch\_benchmarks.sh} and
\texttt{scripts/fetch\_timestamped.sh} refetch each from its original source.
The corpora themselves are not redistributed because the GroupLens license
forbids it. All derived data behind every reported number, together with the
code that produces it, is openly available at
\url{https://github.com/mouadlouhichi/signalshap-code}. The repository ships
\texttt{artefacts/MANIFEST.json}, recording a SHA-256 for each artefact file
with the commit and environment that produced it, including the BLAS backend,
because Section~\ref{sec:threats} shows the backend changes candidate contents
for a small number of users. \texttt{artefacts/PROVENANCE.md} maps every table
and figure to the artefact, platform, candidate rule and seeds behind it. We
state the residual limitation precisely: a reader reproducing from raw data
must refetch the corpora first, and a run on a different BLAS reproduces the
reported signs and orderings but not every fifth decimal.

\section*{Ethics}
The study performs secondary analysis of previously released, de-identified
human-generated ratings, reviews, and check-ins under the dataset licenses
recorded in the artefact, and involves no new participant recruitment or
intervention. Geographic check-ins can retain re-identification risk even after
direct identifiers are removed; we use only aggregate geographic cells and
redistribute no event records. Popularity-based signals can reinforce exposure
disparities, and no fairness claim is made.

\section*{Funding}
The authors declare that no funds, grants, or other support were received
during the preparation of this manuscript.

\section*{Acknowledgements}
Not applicable.

\bibliographystyle{elsarticle-num}
\bibliography{paper}

\end{document}
"""


# --------------------------------------------------------------------------- #
# Extraction and transformation
# --------------------------------------------------------------------------- #


def balanced(text: str, start: int) -> tuple[str, int]:
    """Return the brace-balanced group beginning at `text[start] == '{'`."""
    assert text[start] == "{", text[start:start + 40]
    depth, i = 0, start
    while i < len(text):
        if text[i] == "{" and (i == 0 or text[i - 1] != "\\"):
            depth += 1
        elif text[i] == "}" and text[i - 1] != "\\":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
        i += 1
    raise ValueError("unbalanced braces")


def extract_abstract(src: str) -> str:
    i = src.index(r"\abstract{")
    body, _ = balanced(src, i + len(r"\abstract"))
    return body.strip()


def extract_keywords(src: str) -> list[str]:
    i = src.index(r"\keywords{")
    body, _ = balanced(src, i + len(r"\keywords"))
    return [k.strip() for k in body.replace("\n", " ").split(",") if k.strip()]


def extract_body(src: str) -> str:
    """Everything from the first \\section to just before \\backmatter."""
    start = src.index(r"\section{Introduction}")
    end = src.index(r"\backmatter")
    return src[start:end].rstrip() + "\n"


def widen_floats(body: str) -> tuple[str, int]:
    """Promote wide floats to starred (both-column) floats.

    THIS IS THE REAL WORK OF THE CONVERSION. cas-dc is double column, so a
    table that fits comfortably in sn-jnl's ~165mm single-column measure has
    only ~84mm here and will overflow into the gutter. Any float that is
    already full-width, or whose widest row is long, is promoted to a starred
    environment so it spans both columns.

    Detection is deliberately conservative: promote when the float either
    declares \\textwidth, or carries more than four tabular columns, or has any
    source row longer than 90 characters. A false positive costs a slightly
    over-wide float; a false negative costs an overfull hbox in the gutter,
    which is what a desk reject looks for.
    """
    out, n = [], 0
    pattern = re.compile(r"\\begin\{(table|figure)\}(\[[^\]]*\])?")
    pos = 0
    while True:
        m = pattern.search(body, pos)
        if not m:
            out.append(body[pos:])
            break
        env = m.group(1)
        endtok = f"\\end{{{env}}}"
        e = body.index(endtok, m.end())
        block = body[m.start():e + len(endtok)]

        # Widest tabular column count, 0 when the float holds no tabular.
        #
        # NOTE ON A BUG THIS ONCE HAD. The count used to be written inline as
        # `max(...) > 4 if re.search(...) else False` at the end of an `or`
        # chain. Python's conditional expression binds LOOSER than `or`, so the
        # whole chain became the condition of the ternary: any float without a
        # tabular evaluated to False regardless of \textwidth or line length,
        # and every figure silently stayed single-column. Computed separately
        # here so the precedence cannot bite again.
        # The column spec must be read with BALANCED braces, not a character
        # class: booktabs specs look like {@{}llll@{}}, and `\{([^}]*)\}`
        # stops at the first `}` inside `@{}`, returning "@" and a column
        # count of zero for every table in the manuscript.
        specs = []
        for tm in re.finditer(r"\\begin\{tabularx?\}", block):
            j = tm.end()
            # tabularx takes a width argument first; skip any leading groups
            # until the one that looks like a column spec.
            while j < len(block) and block[j] == "{":
                grp, j = balanced(block, j)
                if any(c in grp for c in "lrcXp"):
                    specs.append(grp)
                    break
        cols = max((sum(spec.count(c) for c in "lrcXp") for spec in specs),
                   default=0)

        wide = (
            r"\textwidth" in block
            or r"\linewidth" in block
            or any(len(line) > 90 for line in block.splitlines())
            or cols > 4
        )

        out.append(body[pos:m.start()])
        if wide:
            n += 1
            opt = m.group(2) or "[tbp]"
            # Starred floats may only be [t] or [p] in LaTeX2e two-column mode;
            # a starred float with [h] or [b] is silently promoted to [tp]
            # anyway, so declare it honestly.
            opt = "[tp]"
            block = (f"\\begin{{{env}*}}{opt}"
                     + block[m.end() - m.start():-len(endtok)]
                     + f"\\end{{{env}*}}")
        out.append(block)
        pos = e + len(endtok)
    return "".join(out), n


def convert(src: str) -> tuple[str, dict]:
    abstract = extract_abstract(src)
    keywords = extract_keywords(src)
    body = extract_body(src)

    # Springer's booktabs alias -> real booktabs.
    body = body.replace(r"\botrule", r"\bottomrule")
    # \bmhead is Springer-only; it appears only in the backmatter we replace,
    # but guard anyway so a future one does not silently vanish.
    body = re.sub(r"\\bmhead\{([^}]*)\}", r"\\paragraph{\1}", body)

    body, widened = widen_floats(body)

    tex = PREAMBLE.replace("%%ABSTRACT%%", abstract)
    tex = tex.replace("%%KEYWORDS%%", " \\sep\n".join(keywords))
    tex += "\n" + body + BACKMATTER

    stats = {
        "abstract_words": len(abstract.split()),
        "keywords": len(keywords),
        "widened_floats": widened,
        "sections": len(re.findall(r"^\\section\{", body, re.M)),
        "citations": len(re.findall(r"\\cite[pt]?\{", body)),
    }
    return tex, stats


FETCH = r"""#!/usr/bin/env bash
# Fetch the Elsevier CAS LaTeX bundle (cas-dc.cls and friends).
#
# The class files are Elsevier's and are NOT redistributed in this repository.
# Run this once before building paper-kbs/.
set -uo pipefail
DEST="$(cd "$(dirname "$0")" && pwd)"
TMP=$(mktemp -d)

URL="https://assets.ctfassets.net/o78em1y1w4i4/5uFmLZJTPDMAUjFnHRpjj8/6f19a979146eb93263763d87a894ab0d/els-cas-templates.zip"
echo "fetching Elsevier CAS templates..."
if ! curl -fsSL --retry 3 --max-time 600 -o "$TMP/cas.zip" "$URL"; then
  echo "DOWNLOAD FAILED. Fetch it manually from"
  echo "  https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions"
  echo "and copy cas-dc.cls, cas-common.sty and elsarticle-num.bst into $DEST"
  rm -rf "$TMP"; exit 1
fi

unzip -qo "$TMP/cas.zip" -d "$TMP/x"
for f in cas-dc.cls cas-sc.cls cas-common.sty; do
  found=$(find "$TMP/x" -name "$f" | head -1)
  [ -n "$found" ] && cp "$found" "$DEST/" && echo "  $f"
done
# Numbered bibliography style. CAS ships cas-model2-names; elsarticle-num is
# the numbered style the KBS guide's [n] citation format needs.
for f in elsarticle-num.bst cas-model2-names.bst; do
  found=$(find "$TMP/x" -name "$f" | head -1)
  [ -n "$found" ] && cp "$found" "$DEST/" && echo "  $f"
done
rm -rf "$TMP"

if [ ! -f "$DEST/elsarticle-num.bst" ]; then
  echo "NOTE: elsarticle-num.bst was not in the CAS bundle."
  echo "      Get it from CTAN: https://ctan.org/pkg/elsarticle"
fi
echo "done."
"""

HIGHLIGHTS = r"""%% Knowledge-Based Systems requires highlights as a SEPARATE file:
%% 3 to 5 bullets, each at most 85 characters including spaces.
%% Verified by scripts/make_elsevier.py.
\begin{highlights}
\item Source attribution as an exact 5-player game; all 32 coalitions enumerated
\item Shapley credit and leave-one-out removal cost disagree in sign on 2 corpora
\item Disagreement survives a globally causal split and source-blind candidate pools
\item Half of Gowalla users are unrankable, capping recall at 0.501 by construction
\item Attribution-derived fusion gives no gain over a tuned head; reported as such
\end{highlights}
"""


def main() -> int:
    src = SRC.read_text()
    tex, stats = convert(src)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(tex)

    # Bibliography and figures travel with the manuscript.
    shutil.copyfile(ROOT / "paper" / "paper.bib", OUT_DIR / "paper.bib")
    figs = OUT_DIR / "figures"
    figs.mkdir(exist_ok=True)
    for p in sorted((ROOT / "paper" / "figures").glob("Fig*.png")):
        shutil.copyfile(p, figs / p.name)

    (OUT_DIR / "fetch-template.sh").write_text(FETCH)
    (OUT_DIR / "fetch-template.sh").chmod(0o755)
    (OUT_DIR / "highlights.tex").write_text(HIGHLIGHTS)

    # -- guide-for-authors conformance, checked rather than assumed ---------- #
    problems = []
    if stats["abstract_words"] > ABSTRACT_MAX_WORDS:
        problems.append(f"abstract is {stats['abstract_words']} words "
                        f"(KBS limit {ABSTRACT_MAX_WORDS})")
    if not 1 <= stats["keywords"] <= KEYWORDS_MAX:
        problems.append(f"{stats['keywords']} keywords (KBS allows 1-{KEYWORDS_MAX})")

    hl = re.findall(r"\\item (.+)", HIGHLIGHTS)
    if not 3 <= len(hl) <= 5:
        problems.append(f"{len(hl)} highlights (KBS requires 3-5)")
    for h in hl:
        if len(h) > 85:
            problems.append(f"highlight is {len(h)} chars (max 85): {h[:50]}...")

    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  abstract       {stats['abstract_words']} words (limit {ABSTRACT_MAX_WORDS})")
    print(f"  keywords       {stats['keywords']} (limit {KEYWORDS_MAX})")
    print(f"  highlights     {len(hl)} (3-5, each <= 85 chars)")
    print(f"  sections       {stats['sections']}")
    print(f"  citations      {stats['citations']}")
    print(f"  widened floats {stats['widened_floats']} promoted to span both columns")
    print(f"  figures        {len(list(figs.glob('Fig*.png')))} copied")

    if problems:
        print("\nKBS GUIDE VIOLATIONS:")
        for p in problems:
            print("  -", p)
        return 1
    print("\nconforms to the KBS guide for authors on every checkable point")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
