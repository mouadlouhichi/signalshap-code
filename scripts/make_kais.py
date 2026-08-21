#!/usr/bin/env python3
"""Port the KBS (Elsevier cas-dc) manuscript to KAIS (Springer Nature sn-jnl).

Knowledge and Information Systems is a Springer Nature journal (10115). Its
submission guidelines ask for the Springer Nature LaTeX template with numbered
citations in square brackets, which is `sn-jnl.cls` with the `Numbered` option
and the `sn-basic` reference style. Both `sn-jnl.cls` and `sn-basic.bst` are
already vendored in `paper/` from the earlier Discover AI submission, so this
port needs no download.

Source of truth
---------------
`paper-kbs/kbs-article.tex` is the LATEST manuscript: it carries every review
round, the hand edits, and the abstract residual fix. The older Springer file
`paper/sn-article.tex` is NOT used as the source here, deliberately, because it
predates those edits.

What actually has to change
---------------------------
The two classes differ in three ways that matter, and only three:

1. Front matter markup. Elsevier uses `\\author[1]{...}` plus `\\ead`, `\\credit`,
   `\\cormark`/`\\cortext` and `\\affiliation{organization=...}`; Springer uses
   `\\author*[1]{\\fnm{}\\sur{}}`, `\\email{}` and `\\affil*[1]{\\orgdiv{}...}`.
   `abstract`/`keywords` are environments in cas-dc and macros in sn-jnl.

2. Column count. cas-dc is two-column, so every wide float was promoted to a
   starred float spanning both columns. sn-jnl (sn-basic) is SINGLE column with
   a 160mm text block, where a starred float is meaningless at best and a
   `Float(s) lost` error at worst. Every `table*`/`figure*` is demoted back.

3. Bibliography. cas-dc needs an explicit `\\bibliographystyle{elsarticle-num}`;
   sn-jnl sets `sn-basic` itself from the class option and loads natbib itself,
   so loading natbib again in the preamble is an option clash.

Everything else (body prose, tables, TikZ, numbers) is carried over verbatim,
which is the point: the numbers stay under `scripts/check_paper_numbers.py`.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "paper-kbs" / "kbs-article.tex"
DST_DIR = REPO / "paper-kais"
DST = DST_DIR / "kais-article.tex"

# --------------------------------------------------------------------------
# 1. Preamble.
# --------------------------------------------------------------------------
# `Numbered` selects square-bracket numeric citations, which is what the KAIS
# submission guidelines require. `sn-basic` selects sn-basic.bst. `pdflatex`
# is the engine option. This mirrors the option set that already compiled for
# the Discover AI submission from the same repository.
PREAMBLE = r"""%% Springer Nature LaTeX template (sn-jnl.cls).
%% Target: Knowledge and Information Systems (KAIS), Springer, journal 10115.
%%
%% GENERATED FILE -- do not edit by hand.
%%   Source:    paper-kbs/kbs-article.tex   (the latest manuscript)
%%   Generator: scripts/make_kais.py
%% Edit the source and regenerate, or the numbers will drift from artefacts/
%% and scripts/check_paper_numbers.py will stop protecting them.
%%
%% Build:  pdflatex kais-article && bibtex kais-article
%%         && pdflatex kais-article && pdflatex kais-article
%%
%% KAIS asks for the Springer Nature template with numbered citations in
%% square brackets, so: Numbered + sn-basic (-> sn-basic.bst).
%% sn-jnl.cls and sn-basic.bst ship with this directory; unlike Elsevier's
%% cas-dc.cls they are redistributable under the LPPL.
\documentclass[pdflatex,sn-basic,Numbered]{sn-jnl}

%% sn-jnl.cls loads none of these itself.
%% NOTE: natbib is deliberately absent. The class loads it with
%% [numbers,sort&compress] inside its own \if@Spr@basic@refstyle branch;
%% loading it here again is an option clash.
\usepackage{amsmath}
\usepackage{amssymb}
%% amsthm is REQUIRED: sn-jnl.cls defines thmstyleone..four only inside
%% \@ifpackageloaded{amsthm}{...}{}, so it configures those styles but never
%% loads the package.
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
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,fit,backgrounds,calc,shapes.geometric}
\graphicspath{{figures/}}

%% sn-jnl and hyperref can otherwise emit duplicate float destinations, and
%% paragraph-level headings make the PDF bookmark hierarchy skip levels.
\hypersetup{hypertexnames=false,bookmarksdepth=3}

%% SINGLE COLUMN, and the main reason this is not a pure search-and-replace.
%% cas-dc is two-column with a ~84mm measure, so every wide float had been
%% promoted to a starred float spanning both columns. sn-basic is single
%% column with a 160mm text block: starred floats are demoted back by the
%% generator, since here they buy nothing and can be lost outright.

%% Figure 1 renders as live TikZ; set \tikzfigurefalse to fall back to the
%% pre-rendered raster in figures/Fig1.png.
\newif\iftikzfigure
\tikzfiguretrue

%% Figure lettering. Springer requires 8-12pt in figures. sn-jnl.cls redefines
%% the relative size macros (\tiny is 5pt, \footnotesize is 7pt), both of which
%% would VIOLATE that rule, so explicit point sizes are set here.
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
  snout/.style={
    rectangle, draw=black, line width=0.65pt, fill=white,
    minimum height=14mm, inner sep=3pt, align=center,
    font=\snFigMain, text width=34mm},
  sncredit/.style={snout},
  snremoval/.style={snout},
  sninteraction/.style={snout},
  snbranch/.style={draw=black, line width=0.65pt},
  snlbl/.style={font=\snFigSub, inner sep=1.2pt, text=black},
}

%% Float placement. Same remedy as the other two builds: without it a single
%% deferred float stalls every later one and the whole backlog flushes at
%% \end{document}. placeins drains the queue at each section boundary.
\renewcommand{\topfraction}{0.9}
\renewcommand{\bottomfraction}{0.8}
\renewcommand{\textfraction}{0.07}
\renewcommand{\floatpagefraction}{0.6}
\setcounter{topnumber}{3}
\setcounter{bottomnumber}{2}
\setcounter{totalnumber}{5}
\usepackage[section]{placeins}

%% sn-jnl defines thmstyleone/thmstyletwo only when amsthm was loaded before
%% the class, which is impossible in a normal document. Use amsthm's standard
%% styles directly so the build has no "Unknown theoremstyle" warnings.
\theoremstyle{plain}
\newtheorem{theorem}{Theorem}
\newtheorem{proposition}[theorem]{Proposition}
\newtheorem{lemma}[theorem]{Lemma}

\theoremstyle{definition}
\newtheorem{property}{Property}
\newtheorem{remark}{Remark}

\raggedbottom
\emergencystretch=0.75em

\newcommand{\G}{\mathcal{G}}
\newcommand{\Cu}{C_u}
\newcommand{\Ueval}{\mathcal{U}_{\mathrm{eval}}}
\newcommand{\NDCG}{\mathrm{NDCG@10}}
\newcommand{\NDCGat}[1]{\mathrm{NDCG@}#1}
\newcommand{\LOOr}{\mathrm{LOO}_{\mathrm{rank}}}
\newcommand{\LOOe}{\mathrm{LOO}_{\mathrm{e2e}}}
\newcommand{\LOO}{\mathrm{LOO}}

\begin{document}
"""

# --------------------------------------------------------------------------
# 2. Front matter, in Springer markup.
# --------------------------------------------------------------------------
# ORCID is a plain hyperlink rather than the class's \orcid{} macro: that macro
# does \includegraphics{Orcidlogo.eps} and the logo does not ship with the
# class, so on a clean TeX tree it is a missing-file error.
FRONT_HEAD = r"""
\title[Exact-Enumeration Source Attribution]{SignalShap: Exact-Enumeration
Ranking-Stage Attribution of Sources in Hybrid Recommenders}

\author*[1]{\fnm{Mouad} \sur{Louhichi}\,\href{https://orcid.org/0000-0002-6849-230X}{\textsuperscript{\fontsize{8}{9}\selectfont ORCID}}}\email{mouad\_louhichi@um5.ac.ma}
\author[1]{\fnm{Redwane} \sur{Nesmaoui}}\email{redwane.nesmaoui@um5.ac.ma}
\author[1]{\fnm{Mohamed} \sur{Lazaar}}\email{mohamed.lazaar@ensias.um5.ac.ma}

\affil*[1]{\orgdiv{National Higher School of Computer Science and Systems
Analysis (ENSIAS)}, \orgname{Mohammed V University in Rabat},
\city{Rabat}, \country{Morocco}}

\abstract{"""

FRONT_TAIL = r"""}

\keywords{Shapley value, cooperative game theory, hybrid recommender systems,
ranking-stage attribution, leave-one-out ablation, two-stage recommendation}

\maketitle
"""

# --------------------------------------------------------------------------
# 3. Back matter, in Springer form.
# --------------------------------------------------------------------------
# Springer asks for a single Declarations section rather than Elsevier's
# separate CRediT / competing-interest / data-availability headings, and its
# generative-AI guidance is phrased differently from Elsevier's. The CONTENT is
# carried over unchanged; only the container and the two publisher-specific
# wordings differ.
BACK = r"""
\backmatter

\bmhead{Acknowledgements}
Not applicable.

\section*{Declarations}

\begin{itemize}
\item \textbf{Funding.} The authors declare that no funds, grants, or other
      support were received during the preparation of this manuscript.

\item \textbf{Competing interests.} The authors declare that they have no known
      competing financial interests or personal relationships that could have
      appeared to influence the work reported in this paper.

\item \textbf{Ethics approval.} Not applicable to new participant recruitment
      or intervention. The study performs secondary analysis of previously
      released, de-identified human-generated ratings, reviews, and check-ins
      under the dataset licenses recorded in the artefact. Geographic check-ins
      can retain re-identification risk even after direct identifiers are
      removed; we use only aggregate geographic cells and redistribute no event
      records. Popularity-based signals can reinforce exposure disparities, and
      no fairness claim is made.

\item \textbf{Data availability.} This work uses three public corpora and
      redistributes none of them. MovieLens-1M is used under the GroupLens
      research-use license, Gowalla check-ins come from the SNAP collection, and
      the Video Games category is taken from the Amazon Reviews 2023 corpus; the
      fetch scripts in the repository retrieve each from its original source.
      The corpora themselves are not redistributed because the GroupLens license
      forbids it. All derived data behind every reported number is released with
      the code, together with \texttt{MANIFEST.json}, which records a SHA-256 for
      each artefact file with the commit and environment that produced it,
      including the BLAS backend, because Section~\ref{sec:threats} shows the
      backend changes candidate contents for a small number of users.
      \texttt{PROVENANCE.md} maps every table and figure to the artefact,
      platform, candidate rule and seeds behind it. We state the residual
      limitation precisely: a reader reproducing from raw data must refetch the
      corpora first, and a run on a different BLAS reproduces the reported signs
      and orderings but not every fifth decimal.

\item \textbf{Code availability.} The implementation, configuration files, and
      scripts required to reproduce the reported experiments, tables, and
      figures are publicly available at
      \url{https://github.com/mouadlouhichi/signalshap}. The results in this
      manuscript correspond to repository commit
      \path{0b8e998a13610932cef79b8ccb3fab55074263d3}, released as tag
      \texttt{kais-submission}; that commit is the one recorded inside
      \texttt{MANIFEST.json} alongside the SHA-256 of every artefact, so a
      reader can confirm that the released hashes and the reported numbers come
      from the same state of the code.

\item \textbf{Author contributions.} \textbf{M.\ Louhichi:} conceptualisation,
      methodology, software, formal analysis, investigation, writing (original
      draft), visualisation. \textbf{R.\ Nesmaoui:} software, validation, data
      curation, writing (review and editing). \textbf{M.\ Lazaar:} supervision,
      methodology, resources, writing (review and editing).

\item \textbf{Use of AI tools.} In line with Springer Nature's guidance on
      generative AI, we disclose that the authors used OpenAI Codex for code
      scaffolding, editorial review, and consistency checking. No text, result,
      figure, or citation was generated for inclusion without author
      verification, and no AI system is listed as an author. The authors
      reviewed and edited the content as needed and take full responsibility
      for the content of the publication.
\end{itemize}

\bibliography{paper}

\end{document}
"""


def extract_abstract(text: str) -> str:
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.S)
    if not m:
        raise SystemExit("could not find the abstract environment in the source")
    return m.group(1).strip()


def extract_body(text: str) -> str:
    """Everything from \\section{Introduction} to just before the back matter."""
    start = text.index(r"\section{Introduction}")
    # The Elsevier back matter begins at the CRediT heading; everything from
    # there to \end{document} is publisher-specific and is replaced wholesale.
    end = text.index(r"\section*{CRediT authorship contribution statement}")
    return text[start:end].rstrip()


def demote_starred_floats(body: str) -> tuple[str, int]:
    """cas-dc two-column -> sn-basic single column: table*/figure* -> table/figure.

    In a single-column class a starred float is not merely redundant. LaTeX
    routes it through the double-column float mechanism, which in a one-column
    document can defer it to the very end or drop it with `Float(s) lost`.
    """
    body, n1 = re.subn(r"\\begin\{(table|figure)\*\}", r"\\begin{\1}", body)
    body, n2 = re.subn(r"\\end\{(table|figure)\*\}", r"\\end{\1}", body)
    if n1 != n2:
        raise SystemExit(f"unbalanced starred floats: {n1} begins, {n2} ends")
    return body, n1


def strip_comments(text: str) -> str:
    """Drop LaTeX comments, respecting escaped \\%."""
    out = []
    for line in text.splitlines():
        m = re.search(r"(?<!\\)%", line)
        out.append(line[: m.start()] if m else line)
    return "\n".join(out)


def check_no_elsevier_markup(text: str) -> None:
    """Fail loudly if any cas-dc-only macro survived into the Springer file.

    Checked against comment-stripped text: the preamble commentary explains the
    port and legitimately names the Elsevier macros it removed.
    """
    text = strip_comments(text)
    banned = [
        r"\ead", r"\credit", r"\cormark", r"\cortext", r"\tnotemark",
        r"\fnmark", r"\printcredits", r"\shorttitle", r"\shortauthors",
        r"\affiliation[", r"mode=title", r"elsarticle", r"cas-dc",
        r"\begin{keywords}", r"\sep",
    ]
    hits = [b for b in banned if b in text]
    if hits:
        raise SystemExit(f"Elsevier markup survived the port: {hits}")


def main() -> int:
    src = SRC.read_text(encoding="utf-8")

    abstract = extract_abstract(src)
    body = extract_body(src)
    body, n_demoted = demote_starred_floats(body)

    out = PREAMBLE + FRONT_HEAD + abstract + FRONT_TAIL + "\n" + body + "\n" + BACK
    check_no_elsevier_markup(out)

    DST_DIR.mkdir(exist_ok=True)
    DST.write_text(out, encoding="utf-8")

    # The class and bibliography style are redistributable under the LPPL,
    # unlike Elsevier's cas-dc.cls, so they ship inside the submission bundle.
    for name in ("sn-jnl.cls", "sn-basic.bst"):
        shutil.copyfile(REPO / "paper" / name, DST_DIR / name)
    shutil.copyfile(REPO / "paper-kbs" / "paper.bib", DST_DIR / "paper.bib")

    figdir = DST_DIR / "figures"
    figdir.mkdir(exist_ok=True)
    for fig in sorted((REPO / "paper-kbs" / "figures").glob("*.png")):
        shutil.copyfile(fig, figdir / fig.name)

    print(f"wrote {DST.relative_to(REPO)}")
    print(f"  {len(out.splitlines())} lines")
    print(f"  {n_demoted} starred floats demoted to single column")
    print(f"  abstract {len(abstract.split())} words")
    return 0


if __name__ == "__main__":
    sys.exit(main())
