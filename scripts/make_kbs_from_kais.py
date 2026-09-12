#!/usr/bin/env python3
"""Derive the Elsevier (KBS) manuscript from the Springer (KAIS) manuscript.

Why generate rather than hand-maintain
--------------------------------------
The two submissions share one body of prose and one set of numbers. Keeping
two hand-edited copies is how they drift: the version of `kbs-submission/`
shipped in `signalshap__submission.zip` was built from an earlier KAIS
revision and had already fallen behind on the introduction, the verification
section, the discussion, the retirement table and the abstract.

This script takes `paper-kais/main.tex` as the single source of prose and
mechanically re-targets it at `elsarticle`. Re-run it whenever the KAIS file
changes.

What actually differs between the two, and nothing else
-------------------------------------------------------
1. **Class and front matter.** `sn-jnl` uses `\\author*[1]{\\fnm{}\\sur{}}`,
   `\\affil*`, `\\abstract{}` and `\\keywords{}`; `elsarticle` uses
   `frontmatter`, `\\author[aff]`, `\\ead`, `\\cortext`/`\\fntext`, an
   `abstract` environment and a `keyword` environment with `\\sep`.

2. **Column count.** `sn-basic` is single column at 160mm. `elsarticle` with
   `5p,twocolumn` is two columns at roughly 84mm per column, so every wide
   float must be promoted to a starred float that spans both columns. This is
   the reverse of the KAIS port, which demoted them.

3. **Sectioning depth.** Elsevier's two-column measure makes a numbered
   fourth level cramped, and the KBS template convention is `\\paragraph`, so
   `\\subsubsection` becomes `\\paragraph`.

4. **Back matter.** Springer's single `Declarations` list becomes Elsevier's
   separate CRediT, competing-interest, data-availability and generative-AI
   headings, and KBS additionally wants Highlights as their own file.

Everything else, including every number, is carried across unchanged.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KAIS_DIR = REPO / "paper-kais"
KBS_DIR = REPO / "paper-kbs-elsevier"
SRC = KAIS_DIR / "main.tex"
DST = KBS_DIR / "main.tex"

# Floats that must span both columns in a two-column layout. Everything here
# is either a wide table or a full-width figure; Fig3 is the one deliberate
# exception, a square scatter that reads fine inside one column.
WIDE_FLOATS = {
    "fig:workflow", "tab:sources", "alg:signalshap", "tab:preconditions",
    "fig:sampling", "tab:loo", "tab:retirement", "tab:retire-seeds",
    "tab:decisions-kais",
    # Six columns on a \textwidth tabularx. In a single-column float this
    # overruns the 84mm measure and runs into the gutter.
    "tab:notation",
    # Five columns including a 0.30\textwidth prose column.
    "tab:rulecomparison",
}
NARROW_FLOATS = {"fig:scatter"}

PREAMBLE = r"""%% Elsevier LaTeX submission.
%% Target: Knowledge-Based Systems (KBS), Elsevier.
%%
%% GENERATED FILE -- do not edit by hand.
%%   Source:    paper-kais/main.tex
%%   Generator: scripts/make_kbs_from_kais.py
%% The KAIS manuscript is the single source of prose and numbers. Edit that
%% file and regenerate, or the two submissions will drift apart, which is
%% exactly what happened to the previous hand-maintained copy.
%%
%% Build:  pdflatex main && bibtex main && pdflatex main && pdflatex main
\documentclass[final,5p,times,twocolumn]{elsarticle}

\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsthm}
\usepackage{graphicx}
\usepackage{multirow}
\usepackage{array}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{microtype}
\usepackage{xurl}
\usepackage[hidelinks]{hyperref}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,fit,backgrounds,calc,shapes.geometric}
\graphicspath{{figures/}}

\hypersetup{hypertexnames=false,bookmarksdepth=3}

%% Figure 1 renders as live TikZ. Set \tikzfigurefalse to fall back to the
%% pre-rendered raster in figures/Fig1.png. This \newif MUST precede the
%% figure: without it \iftikzfigure is an undefined control sequence and the
%% compile dies inside the float.
\newif\iftikzfigure
\tikzfiguretrue

%% Explicit figure lettering sizes keep the diagrams legible and independent
%% of the document class's relative-size definitions.
\newcommand{\snFigMain}{\fontsize{9}{10.5}\selectfont}
\newcommand{\snFigSub}{\fontsize{8}{9.5}\selectfont}
"""

FRONTMATTER = r"""
\journal{Knowledge-Based Systems}
\biboptions{sort&compress}

\begin{document}

\begin{frontmatter}

\title{SignalShap: Exact Ranking-Stage Source Attribution for Hybrid
Recommenders}

\author[ensias]{Mouad Louhichi\corref{cor1}\fnref{orcid1}}
\ead{mouad_louhichi@um5.ac.ma}
\author[ensias]{Redwane Nesmaoui}
\ead{redwane.nesmaoui@um5.ac.ma}
\author[ensias]{Mohamed Lazaar}
\ead{mohamed.lazaar@ensias.um5.ac.ma}

\cortext[cor1]{Corresponding author.}
\fntext[orcid1]{ORCID: 0000-0002-6849-230X.}
\address[ensias]{National Higher School of Computer Science and Systems
Analysis (ENSIAS), Mohammed V University in Rabat, Rabat, Morocco}

\begin{abstract}
%(ABSTRACT)s
\end{abstract}

\begin{keyword}
hybrid recommender systems \sep Shapley value \sep leave-one-out ablation
\sep source attribution \sep two-stage ranking
\end{keyword}

\end{frontmatter}
"""

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

\section*{Funding}
The authors declare that no funds, grants, or other support were received
during the preparation of this manuscript.

\section*{Ethics}
The study performs secondary analysis of previously released, de-identified
human-generated ratings, reviews, and check-ins under the dataset licenses
recorded in the artefact, and involves no new participant recruitment or
intervention. Geographic check-ins can retain re-identification risk even after
direct identifiers are removed; we use only aggregate geographic cells and
redistribute no event records. Popularity-based signals can reinforce exposure
disparities, and no fairness claim is made.

\section*{Data availability}
This work uses three public corpora and redistributes none of them.
MovieLens-1M is used under the GroupLens research-use license, Gowalla
check-ins come from the SNAP collection, and the Video Games category is taken
from the Amazon Reviews 2023 corpus; the fetch scripts in the repository
retrieve each from its original source. All derived data behind every reported
number is released with the code, together with \texttt{MANIFEST.json}, which
records a SHA-256 for each artefact file with the commit and environment that
produced it, including the BLAS backend. \texttt{PROVENANCE.md} maps every
table and figure to the artefact, platform, candidate rule and seeds behind it.
A reader reproducing from raw data must refetch the corpora first, and a run on
a different BLAS reproduces the reported signs and orderings but not every
fifth decimal.

\section*{Code availability}
The implementation, configuration files, and scripts required to reproduce the
reported experiments, tables, and figures are publicly available at
\url{https://github.com/mouadlouhichi/signalshap}, released as tag
\texttt{kbs-submission-v2}; the corresponding commit is recorded inside
\texttt{MANIFEST.json} alongside the SHA-256 of every artefact.

\section*{Declaration of generative AI and AI-assisted technologies in the
manuscript preparation process}
In accordance with Elsevier's disclosure policy, the authors used OpenAI Codex
for code scaffolding, editorial review, and consistency checking, as also
stated in Section~\ref{sec:algorithm}. After using this tool, the authors
reviewed and edited the content as needed and take full responsibility for the
content of the publication. No AI system is listed as an author.

\bibliographystyle{elsarticle-num}
\bibliography{paper}

\end{document}
"""



def esm_table_numbers(esm_tex: str) -> dict[str, str]:
    r"""Map ESM table labels to their rendered S-numbers.

    The main article cites the supplement by number. Hand-written numbers
    desynchronise the moment a table moves, and they did: after the supplement
    was restructured, three of the four cited numbers pointed at the wrong
    table. The repeat audit was cited as S8 but renders as S9, the estimand
    table as S9 but renders as S10, and the provenance table as S3 but renders
    as S4. Computing them removes the failure mode.
    """
    body = esm_tex[esm_tex.index(r"\begin{document}"):]
    out: dict[str, str] = {}
    n = 0
    for m in re.finditer(r"\\begin\{table\}(.*?)\\end\{table\}", body, re.S):
        n += 1
        lab = re.search(r"\\label\{([^}]*)\}", m.group(1))
        if lab:
            out[lab.group(1)] = "ESM Table~S%d" % n
    return out


def extract(src: str) -> tuple[str, str, str]:
    """Split the KAIS source into (tikz/macro block, abstract, body)."""
    # Everything between the figure-lettering macros and \begin{document} is
    # shared setup: tikzset, float parameters, theorem styles, \newcommands.
    i = src.index(r"\tikzset{")
    j = src.index(r"\begin{document}")
    setup = src[i:j]

    a0 = src.index(r"\abstract{") + len(r"\abstract{")
    a1 = src.index(r"\keywords{")
    abstract = src[a0:a1].strip().rstrip("}").strip()

    b0 = src.index(r"\section{Introduction}")
    b1 = src.index(r"\backmatter")
    body = src[b0:b1].rstrip()
    return setup, abstract, body


def widen_floats(body: str) -> tuple[str, int]:
    """Promote wide floats to starred, two-column-spanning versions.

    Reverse of the KAIS port. A wide table left unstarred in `elsarticle`
    overruns the 84mm column; `\\textwidth` tabulars in particular silently
    run into the gutter.
    """
    n = 0
    pattern = re.compile(
        r"\\begin\{(table|figure|algorithm)\}(\[[^\]]*\])?(.*?)\\end\{\1\}",
        re.S)

    def repl(m: re.Match[str]) -> str:
        nonlocal n
        env, place, inner = m.group(1), m.group(2) or "", m.group(3)
        lab = re.search(r"\\label\{([^}]*)\}", inner)
        label = lab.group(1) if lab else ""
        if label in NARROW_FLOATS:
            return m.group(0)
        if label in WIDE_FLOATS:
            n += 1
            return f"\\begin{{{env}*}}{place}{inner}\\end{{{env}*}}"
        return m.group(0)

    return pattern.sub(repl, body), n


def retarget_graphics(body: str) -> str:
    """`\\textwidth` inside a one-column float is wrong in two columns."""
    # fig:scatter stays in a single column, so its box is \columnwidth.
    body = body.replace(r"\includegraphics[width=0.7\textwidth]{Fig3.png}",
                        r"\includegraphics[width=\columnwidth]{Fig3.png}")
    return body


#: The supplement is venue-neutral apart from its title block, so it is
#: retitled rather than maintained twice. Springer calls it "Online Resource 1";
#: Elsevier calls it supplementary material.
ESM_RETITLE = [
    (r"\title{Online Resource 1\\[4pt]" "\n"
     r"\large Electronic Supplementary Material for\\[3pt]",
     r"\title{Supplementary Material\\[4pt]" "\n"
     r"\large for\\[3pt]"),
    (r"\normalsize \textit{Knowledge and Information Systems}}",
     r"\normalsize \textit{Knowledge-Based Systems}}"),
]

HIGHLIGHTS = """\
- Exact Shapley attribution is computed over all 32 source coalitions.
- Shapley and ranking-stage LOO disagree on two of three corpora.
- Ranking-stage LOO better predicts observed source-retirement cost.
- Fixed candidates separate ranking attribution from retrieval effects.
- The method allocates source credit without prescribing source retirement.
"""


def build_esm() -> tuple[str, int]:
    """Retitle the KAIS supplement for Elsevier. Content is untouched."""
    esm = (KAIS_DIR / "Online-Resource-1.tex").read_text(encoding="utf-8")
    n = 0
    for old, new in ESM_RETITLE:
        if old not in esm:
            raise SystemExit(f"ESM retitle pattern not found:\n{old!r}")
        esm = esm.replace(old, new)
        n += 1
    if "Knowledge and Information Systems" in esm:
        raise SystemExit("KAIS journal name survived into the KBS supplement")
    return esm, n


def main() -> int:
    src = SRC.read_text(encoding="utf-8")
    setup, abstract, body = extract(src)
    esm, n_retitle = build_esm()

    body, n_wide = widen_floats(body)
    body = retarget_graphics(body)

    # Elsevier convention, and the two-column measure makes a numbered fourth
    # level cramped.
    body, n_sub = re.subn(r"\\subsubsection\{", r"\\paragraph{", body)

    # Resolve @@ESMTAB:label@@ against the supplement's ACTUAL numbering.
    numbering = esm_table_numbers(esm)
    missing = []

    def _resolve(m):
        label = m.group(1)
        if label not in numbering:
            missing.append(label)
            return m.group(0)
        return numbering[label]

    body = re.sub(r"@@ESMTAB:([^@]+)@@", _resolve, body)
    abstract = re.sub(r"@@ESMTAB:([^@]+)@@", _resolve, abstract)
    if missing:
        raise SystemExit(f"ESM placeholder for unknown label(s): {missing}")
    if "@@ESMTAB:" in body:
        raise SystemExit("unresolved ESM placeholder")

    # "Online Resource 1" is Springer's name for the supplement. Elsevier calls
    # it supplementary material, and the KBS supplement is titled that way, so
    # leaving the Springer term in the body is a venue leak.
    body = body.replace(
        "Online Resource~1 (Electronic Supplementary Material; ESM) contains",
        "Appendix~A, the supplementary material accompanying this article, "
        "contains")

    # Elsevier calls it supplementary material, not ESM. Sixteen "ESM Sn" /
    # "ESM Table Sn" pointers would otherwise read as a Springer manuscript
    # that had been re-badged. The S-numbering itself is kept, because the
    # supplement numbers its own sections and tables that way.
    body = body.replace("ESM Table~S", "Supplementary Table~S")
    body = body.replace("ESM~S", "Supplementary Section~S")
    body = body.replace("ESM S", "Supplementary Section~S")

    # Two-column float parameters. The float block is inherited from the
    # single-column KAIS setup, where \dbltop* is irrelevant because there are
    # no starred floats. In elsarticle 5p, 11 of the 12 body floats ARE
    # starred, and starred floats are governed by \dbltopfraction and
    # \dblfloatpagefraction, not by \topfraction. Left at the LaTeX defaults
    # (0.7 and 0.5) a full-width table is often refused at the top of a page
    # and deferred to a float page it only half fills, which is the main
    # source of white space in the two-column build.
    # --- Page-filling policy, the dominant cause of the visible gaps -------
    #
    # Three things interact in the two-column build, and all three had been
    # inherited unchanged from the single-column Springer setup:
    #
    # 1. \raggedbottom tells LaTeX NOT to stretch a page to full height, so
    #    all leftover space is dumped at the bottom. In two columns that
    #    happens twice per page. \flushbottom distributes the slack into the
    #    inter-paragraph glue instead, which is what a journal two-column
    #    layout expects and what elsarticle assumes.
    #
    # 2. placeins was loaded with [section], so every \section issues a
    #    \FloatBarrier. With 7 sections and 11 starred floats that forces a
    #    flush at each section boundary, and under \raggedbottom the flush is
    #    visible as a gap immediately before the heading. The barriers were
    #    added for the Springer build, where one deferred float stalled the
    #    whole queue; the \dbltop* parameters now handle that properly, so the
    #    barrier is no longer earning its cost.
    #
    # 3. Section skips are set for a single-column measure and are loose at
    #    84mm.
    setup = setup.replace(
        "\\raggedbottom",
        "%% \\flushbottom, not \\raggedbottom: in two columns ragged bottoms\n"
        "%% leave slack at the foot of BOTH columns on every page.\n"
        "\\flushbottom")
    setup = setup.replace(
        "\\usepackage[section]{placeins}",
        "%% placeins without [section]: a \\FloatBarrier at every section head\n"
        "%% forces a flush that reads as a gap before the heading. \\FloatBarrier\n"
        "%% remains available where a barrier is genuinely wanted.\n"
        "\\usepackage{placeins}")

    # The two explicit \FloatBarrier calls in the body each sit immediately
    # after a starred float. Under the old [section] regime they were belt and
    # braces; with \dbltop* tuned and \flushbottom in force they only pin a
    # wide float in place and leave the slack beside it. \FloatBarrier is
    # still available from placeins if a barrier is ever wanted again.
    body = body.replace("\n\\FloatBarrier\n", "\n")

    setup_marker = "\\usepackage{placeins}"
    dbl = (
        "%% Two-column floats: starred floats obey the \\dbltop* parameters,\n"
        "%% and 11 of 12 body floats here are starred.\n"
        "\\renewcommand{\\dbltopfraction}{0.9}\n"
        "\\renewcommand{\\dblfloatpagefraction}{0.6}\n"
        "\\setcounter{dbltopnumber}{3}\n"
        + setup_marker)
    if setup_marker not in setup:
        raise SystemExit("placeins marker not found in shared setup")
    setup = setup.replace(setup_marker, dbl, 1)

    front = FRONTMATTER.replace("%(ABSTRACT)s", abstract)
    out = PREAMBLE + "\n" + setup + front + "\n" + body + "\n" + BACKMATTER
    # Concatenating the parts can leave a run of blank lines at each seam.
    # Harmless to LaTeX, but it hides real structural gaps during review.
    out = re.sub(r"\n[ \t]*\n([ \t]*\n)+", "\n\n", out)

    KBS_DIR.mkdir(exist_ok=True)
    DST.write_text(out, encoding="utf-8")

    (KBS_DIR / "supplementary-material.tex").write_text(esm, encoding="utf-8")

    # KBS wants Highlights as a separate item, max five bullets of <= 85
    # characters each.
    (KBS_DIR / "highlights.txt").write_text(HIGHLIGHTS, encoding="utf-8")
    over = [b for b in HIGHLIGHTS.strip().splitlines() if len(b) > 85]
    if over:
        raise SystemExit(f"highlight over 85 characters: {over}")

    shutil.copyfile(KAIS_DIR / "paper.bib", KBS_DIR / "paper.bib")
    for name in ("suggested-reviewers.md",):
        shutil.copyfile(KAIS_DIR / name, KBS_DIR / name)

    figdir = KBS_DIR / "figures"
    figdir.mkdir(exist_ok=True)
    for fig in sorted((KAIS_DIR / "figures").glob("*.png")):
        shutil.copyfile(fig, figdir / fig.name)

    repro = KBS_DIR / "reproducibility"
    repro.mkdir(exist_ok=True)
    for f in sorted((KAIS_DIR / "reproducibility").glob("*")):
        shutil.copyfile(f, repro / f.name)

    print(f"wrote {DST.relative_to(REPO)}")
    print(f"  {n_wide} floats widened to span both columns")
    print(f"  {n_sub} subsubsections converted to paragraphs")
    print(f"  abstract {len(abstract.split())} words")
    print(f"wrote {(KBS_DIR / 'supplementary-material.tex').relative_to(REPO)}"
          f"  ({n_retitle} retitle substitutions)")
    print(f"wrote {(KBS_DIR / 'highlights.txt').relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
