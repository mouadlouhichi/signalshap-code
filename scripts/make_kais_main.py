#!/usr/bin/env python3
"""Build the KAIS main text and its Electronic Supplementary Material.

Why this is a rewrite and not a filter
--------------------------------------
KAIS caps a regular paper at 15,000 words and charges 500 words for each
full-page display item. The ported manuscript measures ~20,100 body words with
21 display items, so a mechanical extraction cannot reach the limit: the prose
itself has to be rewritten. What IS mechanical, and must be, is every number.
All tables and figures are lifted verbatim from `paper-kbs/kbs-article.tex` via
`extract_floats.py`, so the numbers the reviewers see remain the numbers
`check_paper_numbers.py` validates against `artefacts/`.

Split
-----
Main text keeps eight display items and the argument. Everything else moves to
a self-contained ESM whose numbering is S1, S2, ... and whose captions read
without the main text. Nothing is deleted.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_floats import get as float_src  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "paper-kais"
MAIN = OUT_DIR / "kais-article.tex"
ESM = OUT_DIR / "kais-esm.tex"

# --------------------------------------------------------------------------
# Preamble shared by both documents.
# --------------------------------------------------------------------------

COMMON_PACKAGES = r"""\usepackage{amsmath}
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
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,fit,backgrounds,calc,shapes.geometric}
\graphicspath{{figures/}}

\hypersetup{hypertexnames=false,bookmarksdepth=3}

%% Figure 1 renders as live TikZ. Set \tikzfigurefalse to fall back to the
%% pre-rendered raster in figures/Fig1.png if the submission system's TeX
%% installation misbehaves with TikZ. This \newif MUST precede the figure:
%% without it \iftikzfigure is an undefined control sequence and the compile
%% dies inside the float.
\newif\iftikzfigure
\tikzfiguretrue

%% Figure lettering. sn-jnl.cls redefines the relative size macros (\tiny is
%% 5pt, \footnotesize is 7pt), both below Springer's 8-12pt floor for figure
%% text, so explicit sizes are set here.
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
\emergencystretch=0.75em

\newcommand{\G}{\mathcal{G}}
\newcommand{\Cu}{C_u}
\newcommand{\Ueval}{\mathcal{U}_{\mathrm{eval}}}
\newcommand{\NDCG}{\mathrm{NDCG@10}}
\newcommand{\NDCGat}[1]{\mathrm{NDCG@}#1}
\newcommand{\LOOr}{\mathrm{LOO}_{\mathrm{rank}}}
\newcommand{\LOOe}{\mathrm{LOO}_{\mathrm{e2e}}}
\newcommand{\LOO}{\mathrm{LOO}}
"""

MAIN_PREAMBLE = r"""%% Springer Nature LaTeX template (sn-jnl.cls).
%% Target: Knowledge and Information Systems (KAIS), Springer, journal 10115.
%%
%% GENERATED FILE -- do not edit by hand.
%%   Generator: scripts/make_kais_main.py
%%   Numbers:   all tables/figures lifted verbatim from
%%              paper-kbs/kbs-article.tex via scripts/extract_floats.py, so
%%              they remain the values scripts/check_paper_numbers.py
%%              validates against artefacts/.
%%
%% Build:  pdflatex kais-article && bibtex kais-article
%%         && pdflatex kais-article && pdflatex kais-article
%%
%% KAIS requires numbered citations in square brackets: Numbered + sn-basic.
\documentclass[pdflatex,sn-basic,Numbered]{sn-jnl}

""" + COMMON_PACKAGES

# --------------------------------------------------------------------------
# Front matter. Title drops the coined method name; abstract is rebuilt to
# the 150-250 word window with NDCG expanded on first use and no 1e-18.
# --------------------------------------------------------------------------

FRONT = r"""
\begin{document}

\title[Ranking-stage attribution is not source removal]{Ranking-stage source
attribution is not source removal: exact Shapley analysis of five-source
hybrid recommenders}

%% ORCID as a plain hyperlink: the class's \orcid{} macro does
%% \includegraphics{Orcidlogo.eps} and that logo does not ship with sn-jnl.
\author*[1]{\fnm{Mouad} \sur{Louhichi}\,\href{https://orcid.org/0000-0002-6849-230X}{\textsuperscript{\fontsize{8}{9}\selectfont ORCID}}}\email{mouad\_louhichi@um5.ac.ma}
\author[1]{\fnm{Redwane} \sur{Nesmaoui}}\email{redwane.nesmaoui@um5.ac.ma}
\author[1]{\fnm{Mohamed} \sur{Lazaar}}\email{mohamed.lazaar@ensias.um5.ac.ma}

\affil*[1]{\orgdiv{National Higher School of Computer Science and Systems
Analysis (ENSIAS)}, \orgname{Mohammed V University in Rabat},
\city{Rabat}, \country{Morocco}}

\abstract{Ablation and Shapley attribution answer different questions: the cost
of removing a source, and the allocation of system value among sources.
Substituting one for the other can reverse a component-level decision.

We formulate source attribution in a two-stage hybrid recommender as a
five-player cooperative game over collaborative, content, popularity, recency,
and sequential signals. The payoff is normalised discounted cumulative gain at
rank 10 on a coalition-independent candidate set, with a ridge fusion head fit
per coalition on validation data and scored on test data. With five players the
32 coalitions are enumerated exactly, so the step from the fitted game to
Shapley values carries no sampling error; we show this matters, because
permutation sampling at 500 draws still exceeds both the seed-to-seed spread
and the materiality threshold used here.

On three timestamped corpora, two of the three fitted systems contain a source
for which Shapley and ranking-stage leave-one-out disagree in sign by a
material margin. Across ten stochastic fits, ranking-stage leave-one-out
matches the ordering of observed end-to-end single-source removal losses more
closely than Shapley (mean Kendall $\tau = 0.96$--$1.00$ versus
$0.20$--$0.80$), and identifies the source with the smallest observed removal
loss on 90--100\% of fits versus 0--50\%. We therefore claim credit allocation
under a declared ranking-stage game, not retirement guidance.}

\keywords{hybrid recommender systems, Shapley value, leave-one-out ablation,
source attribution, two-stage ranking}

\maketitle
"""

# --------------------------------------------------------------------------
# Body.
# --------------------------------------------------------------------------

INTRO = r"""
\section{Introduction}\label{sec:intro}

A production hybrid recommender is an ensemble of architecturally distinct
scorers, and two different questions are routinely asked of it: how should the
system's observed ranking quality be divided among its sources, and what would
happen if one source were switched off? These are credit-allocation and
removal-effect questions. They are not the same question, and this paper is
about what goes wrong when they are treated as if they were.

In practice the second question is answered by \emph{leave-one-out} (LOO)
ablation: disable one source, measure the change, attribute it. LOO is a valid
removal estimate, and dependence among sources does not invalidate it, since
the intervention cost is well defined for the interacting system being
measured. It is not, however, an allocation. It is a single marginal
contribution evaluated against the grand coalition, one of the $2^{n-1}$ terms
a full allocation would average. When two sources are mutually substitutable,
which implicit-feedback collaborative filtering and popularity often are,
removing either alone changes little and LOO assigns both near-zero value even
though the shared capability contributes to the system.

Cooperative game theory supplies the missing rule. The Shapley
value~\citep{shapley1953} is the unique allocation satisfying efficiency,
symmetry, null-player and additivity, and it evaluates each player against
\emph{every} coalition. We make the players five architectural sources
(collaborative filtering, content, popularity, recency, sequential
co-occurrence) and the payoff normalised discounted cumulative gain at rank 10
(NDCG@10) on a candidate set that is fixed across coalitions, so that $v(S)$ is
comparable over a common item set. Five players give $2^5=32$ coalitions, which
we enumerate exhaustively; the aggregation therefore contributes no sampling
error, and Section~\ref{sec:verification} shows that this is load-bearing
rather than decorative.

Our central finding is a disagreement. On two of three timestamped corpora,
Shapley allocation and ranking-stage LOO differ in \emph{sign} for at least one
source by a material margin, and on MovieLens-1M that source is collaborative
filtering, the second most valuable source by allocation and a source whose
removal \emph{improves} the fixed-candidate game. When we then retire each
source outright and measure the end-to-end cost, ranking-stage LOO tracks the
observed ordering and Shapley does not. We claim credit allocation under a
declared game; we do not claim retirement guidance, we make no causal or
off-policy claim, and we do not claim state-of-the-art accuracy. Attribution-derived
fusion weights gave no resolvable gain over a global head, a negative result we
report in the supplement (ESM~S5).

\medskip\noindent\textbf{Contributions.}
\begin{itemize}
\item \textbf{C1 (construct).} A ranking-stage cooperative game over
architectural sources, with a coalition-independent candidate set, a per-user
baseline-centred NDCG@10 payoff, and exact enumeration at small $n$.
\item \textbf{C2 (primary, empirical).} On three timestamped hybrids, Shapley
allocation and ranking-stage LOO can disagree in sign by a material margin, and
ranking-stage LOO, not Shapley, is the quantity that tracks observed end-to-end
retirement cost. Section~\ref{sec:discussion} maps decisions to estimands.
\item \textbf{C3 (verification).} The aggregation is checked against known
constraints: six analytic games, duplicate-injection symmetry, efficiency,
additivity and the null player, together with a measurement of what sampling
would have cost.
\end{itemize}

\medskip\noindent We ask three questions. \textbf{RQ1:} does the implementation
satisfy the constraints a correct Shapley aggregation must satisfy, and what
does exactness buy over sampling? \textbf{RQ2:} do Shapley and ranking-stage
LOO disagree materially, and is disagreement associated with substitutive
interaction? \textbf{RQ3:} which of the two better predicts observed end-to-end
retirement cost?

Section~\ref{sec:related} places the work; Section~\ref{sec:methodology}
defines the game, the algorithm and the protocol;
Section~\ref{sec:verification} verifies the aggregation;
Section~\ref{sec:results} reports attribution and retirement;
Sections~\ref{sec:discussion} and~\ref{sec:conclusion} discuss and conclude.
An Electronic Supplementary Material (ESM) holds proofs, full configuration,
and the robustness suite.
"""

RELATED = r"""
\section{Related work and background}\label{sec:related}

\subsection{Related work}

\paragraph{Feature-level attribution versus source-level attribution}
SHAP~\citep{lundberg2017} unified additive feature attribution, with extensions
to trees~\citep{lundberg2020}, data valuation~\citep{ghorbani2019} and
federated contribution~\citep{wang2020federated}.
Surveys~\citep{covert2021explaining,rozemberczki2022shapley} note that
model-agnostic estimators commonly sample, because the coalition lattice is
exponential in the number of players, with exact procedures reserved for
structured model classes. SHAP, LIME~\citep{ribeiro2016} and Integrated
Gradients~\citep{sundararajan2017} all answer ``which input features moved this
prediction?''. We ask which architectural component earned the system's ranking
quality. The unit of attribution differs, the payoff is a ranking metric rather
than a scalar output, and the decision it informs is the allocation of system
value across subsystems. Because there are five such subsystems rather than
hundreds of features, the complete game is small enough to enumerate: that
difference in granularity is what makes exactness available at all.

\paragraph{Component-level games, and the parent phenomenon}
Closer to our unit of analysis is work attributing behaviour to \emph{model
components}. Neuron Shapley~\citep{ghorbani2020neuron} treats individual
neurons as players with a performance payoff; ensemble
games~\citep{rozemberczki2021ensemble} treat whole classifiers as players and
allocate ensemble accuracy among them; and related work attributes changes in
performance rather than individual
predictions~\citep{zhang2023performance,shah2024coar,bell2024lsspa}. Closest to
our result is~\citet{kim2026forecast}, who compare an all-subsets Shapley
measure against leave-one-model-out in ensemble forecasting and relate the
disagreement to overlap in member errors.

We state the consequence plainly: neither component-level performance
attribution nor the contrast between an allocation and a grand-coalition
marginal is new in itself. The phenomenon is known outside recommendation. Our
narrower contribution is to instantiate it as a ranking-stage source game in a
\emph{two-stage} recommender, where removing a player also changes retrieval
and therefore the item set over which the metric is computed, and to adjudicate
the disagreement against an \emph{observed} retirement cost rather than against
another attribution. Shapley attribution has also been applied without labels,
including our own earlier work pairing approximated values with
clustering~\citep{louhichi2025gametheory}; that setting differs on every axis
that matters here, since one can switch off a recommender source but not a
feature of a clustering.

\paragraph{Shapley for ranking}
RankSHAP~\citep{chowdhury2024rankshap},
RankingSHAP~\citep{heuss2025rankingshap} and ShaRP~\citep{pliatsika2024sharp}
bring Shapley to ranked outputs, but they attribute to \emph{features} of a
fixed candidate list and estimate by sampling. Because our players participate
in retrieval, a coalition would otherwise rank a different item set, which is
precisely why the game is defined on a coalition-independent candidate set.

\paragraph{The game is a modelling choice}
\citet{sundararajan2020many} show that different Shapley formulations answer
different questions, so an attribution is only interpretable relative to a
declared game. We declare ours in Section~\ref{sec:game} and treat the choice,
not the axioms, as the substantive commitment. Graph and gradient
explainers~\citep{ying2019gnnexplainer,luo2020pgexplainer} operate inside one
differentiable model and do not apply across five architecturally distinct
scorers with no shared graph.

\paragraph{Hybrid recommenders and ablation practice}
Hybrid designs~\citep{burke2002hybrid} are still assessed component-wise by
ablation, which is the practice this paper qualifies. Offline ranking
evaluation is itself sensitive to protocol and exposure
bias~\citep{ji2023critical}, which is why our applicability diagnostics are
declared in advance in Section~\ref{sec:preconditions}.

\subsection{Background}\label{sec:background}

A cooperative game is a pair $(\G, v)$ with players $\G$, $|\G| = n$, and
$v : 2^{\G}\to\mathbb{R}$ with $v(\varnothing)=0$. The Shapley value
\begin{equation}
\varphi_g(v) = \sum_{S\subseteq\G\setminus\{g\}}
  \frac{|S|!\,(n-|S|-1)!}{n!}\bigl[v(S\cup\{g\})-v(S)\bigr]
\label{eq:shapley}
\end{equation}
is the unique allocation satisfying efficiency
($\sum_g \varphi_g = v(\G)$), symmetry, the null-player property and
additivity. Leave-one-out is the single term at $S = \G\setminus\{g\}$,
\begin{equation}
\LOO(g) = v(\G) - v(\G\setminus\{g\}),
\label{eq:loo}
\end{equation}
so LOO and Shapley coincide only when no coalition other than the grand one is
informative, that is when $v$ is additive.

\paragraph{Two leave-one-out estimands, kept distinct}
This distinction carries the paper's result, so we fix notation for it.
$\LOOr(g)$ removes $g$ from a \emph{fixed-candidate ranker} only, leaving the
candidate set and therefore the item set intact. $\LOOe(g)$ removes it from
retrieval and ranking together, so the surviving sources rebuild the pool; this
is the deployment intervention. The two are not interchangeable, and the gap
matters for what each can be used for: $\LOOe$ equals the observed removal loss
by construction, so it cannot be evaluated as a \emph{predictor} of that loss,
whereas $\LOOr$ can, and is far cheaper because it does not re-run retrieval.
Neither estimand is invalidated by dependence among sources; the intervention
cost is well defined for the interacting system being measured. What LOO cannot
do is allocate, and that is a statement about the estimand rather than about
its statistical quality.

\paragraph{Semivalues, interactions and the payoff}
Semivalues relax efficiency by replacing the weights in
Equation~(\ref{eq:shapley}) with a general coalition-size distribution. Banzhaf
weights all coalitions equally and the binomial family interpolates by a
parameter $q$; both are used as comparators in ESM~S3, where we also record
that the \emph{size-uniform} semivalue is algebraically identical to Shapley
and so is not an independent comparator. Pairwise interaction indices measure
whether two players behave substitutively or complementarily under the same
game. With exactly one relevant test item per user, NDCG@10 reduces to
$1/\log_2(1+\mathrm{rank})$ when that item appears in the top ten and $0$
otherwise, so a coalition value is an average of per-user reciprocal-log gains
over a common item set.
"""

METHOD = r"""
\section{Methodology}\label{sec:methodology}

\subsection{The cooperative game}\label{sec:game}

The players are five source scorers, summarised in
Table~\ref{tab:sources}. Each maps a user $u$ and a candidate item $i$ to a
real score. We use deliberately simple, well-understood scorers: the paper is
about the attribution construct, not about the scorers, and we make no
state-of-the-art claim. We refer to the pipeline that fits these five sources,
enumerates the coalition lattice and aggregates as \emph{SignalShap}.

\begin{table}[tp]
\caption{The five source scorers. Write $\mathcal{H}_u$ for user $u$'s training
history and $t_{\max}$ for the latest training timestamp. ``Declared overlap''
records substitutions predicted before the study was run, and which the
interaction indices later recovered in part.}
\label{tab:sources}
\small
\begin{tabularx}{\textwidth}{@{}llX@{}}
\toprule
Player & Signal & Scoring function $s_g(u,i)$, and declared overlap \\
\midrule
$cf$  & Collaborative
      & Implicit-feedback ALS, $64$ factors, confidence
        $c_{ui}=1+\alpha r_{ui}$ at $\alpha=1$, ridge
        $\lambda_{\mathrm{ALS}}=0.1$, $15$ iterations;
        $s_{cf}=x_u^\top y_i$. Declared to overlap $pop$. \\
\addlinespace[2pt]
$ct$  & Content
      & Cosine similarity in a $5\,000$-term L2-normalised TF--IDF space over
        item text: $p_u$ is the renormalised mean of consumed rows and
        $s_{ct}=p_u^\top M_i$. User-specific but time-invariant. Declared to
        overlap $rec$. \\
\addlinespace[2pt]
$pop$ & Popularity
      & Time-decayed global counts, half-life $h=180$ days:
        $s_{pop}=\log\bigl(1+\sum 2^{-(t_{\max}-t)/(86400h)}\bigr)$. Identical
        across users but not constant along a candidate row, so it survives
        $z$-normalisation. \\
\addlinespace[2pt]
$rec$ & Recency
      & Items assigned to one of $20$ clusters by argmax over a $20$-component
        SVD of a \emph{separate} $2\,000$-term TF--IDF matrix; $s_{rec}=
        2^{-(t_{\max}-\ell_{u\kappa(i)})/(86400\cdot30)}$ for the user's most
        recent interaction $\ell$ in that cluster, else $0$. \\
\addlinespace[2pt]
$seq$ & Co-occurrence
      & PPMI--SVD item embeddings (item2vec-style), pairs at distance $\le 5$,
        $64$ components; user vector is a recency-weighted mean of the last
        $5$ items with weights $0.8^k$. The co-occurrence matrix is
        \emph{symmetric}: order enters only through those weights, so this is
        not a sequential model in the SASRec sense, and the $cf$--$seq$
        interaction may partly reflect two collaborative signals. \\
\bottomrule
\end{tabularx}
\end{table}

Every score is $z$-normalised per user over $\Cu$ before it enters the game.
That removes each source's location and positive linear scale, so the game is
invariant to positive affine rescaling of any source. It does \emph{not} make
only the ordering matter: the head fuses standardised columns linearly, so
relative spacing still affects the fused ranking, and a nonlinear monotone
transform of one source can change the result while preserving that source's
own ordering. Two implementation details are load-bearing for reproducibility.
The $rec$ argmax partition is not invariant to sign reversal of an SVD
component, so each component is canonicalised to a positive largest-magnitude
loading; this makes the partition a function of the data alone and $rec$
bit-identical across solver seeds. Where two singular values coincide, however,
the subspace has no preferred basis and the partition genuinely moves; that is
a property of the spectrum, not of the seed, and is the residual caveat for
$rec$.

\paragraph{A candidate set that does not depend on the coalition}
Every coalition is scored on one candidate set per user. Let $T_g(u,N_g)$ be
the first $N_g$ eligible items under the total order
$(-s_g(u,i),\,\text{item index})$, so that the item index breaks every score
tie including ties at the cutoff boundary. Then
\begin{equation}
\Cu \;=\; \operatorname{Trunc}_{N_{\max}^{(d)}}\!\Bigl(
  \bigcup_{g\in\G} T_g(u,N_g)\Bigr),
\qquad |\Cu| \le N_{\max}^{(d)},
\label{eq:candidates}
\end{equation}
where $d$ indexes the dataset, since the cap is frozen per corpus, and
$\operatorname{Trunc}_N$ retains the first $N$ items after sorting the union by
$\bigl(-\sum_{g\in\G} 1/\operatorname{rank}_g(i),\ \text{item index}\bigr)$,
with a source that did not retrieve $i$ contributing $0$. Sources begin at
equal depth $N_g = \lceil N_{\max}^{(d)}/|\G|\rceil$ and are deepened together
if the union underfills the cap. Both components of the truncation key are
invariant under permuting $\G$, so relabelling the players cannot change the
game. Writing $\Ueval = \{u : |\Cu| > 0\}$, users outside $\Ueval$ are excluded
from every coalition mean and reported separately as candidate-construction
failures.

This is the construct's load-bearing choice. If each coalition retrieved its
own pool, $v(S)$ and $v(S')$ would be NDCG values over different item sets and
their difference would confound ranking quality with retrieval coverage. The
alternative of a grand-coalition-only pool is not neutral either, and we
measured that cost rather than asserting it: under that design $\varphi_{ct}$
changes sign on MovieLens-1M. Three source-blind pool rules (ESM~S3) leave both
material disagreements intact, and oracle-pool recall equals $\rho$ exactly on
every corpus, which independently confirms
Equation~(\ref{eq:dilution}). Source scores enter the head $z$-normalised per
user over $\Cu$, with $z_{u,g,i} = (s_g(u,i)-\mu_{u,g})/\sigma_{u,g}$ when
$\sigma_{u,g} > 0$ and $0$ otherwise, so no source dominates through scale.

\paragraph{Characteristic function}
For coalition $S$ we fit a ridge fusion head $w^{(S)}$ on \emph{validation}
data over the masked score matrix $Z^{(S)}_u$, and evaluate on \emph{test}
data:
\begin{equation}
v(S) \;=\; \frac{1}{|\Ueval|}\sum_{u\in\Ueval}
  \Bigl[\NDCG\bigl(\operatorname{rank}(Z^{(S)}_u w^{(S)}),\,
  \mathbf y^{\mathrm{te}}_u\bigr) - b_u\Bigr],
\label{eq:game}
\end{equation}
with $v(\varnothing)=0$ by construction. The ridge penalty $\lambda$ is frozen
before the study at a value selected on a MovieLens pilot; a sweep over eight
orders of magnitude appears in ESM~S3. The per-user baseline $b_u$ is the
\emph{expected} NDCG@10 of a uniformly random permutation of $C_u$, available
in closed form, rather than a sampled draw; centring on an expectation removes
a variance term that a single random draw would inject into every coalition.

\paragraph{What ``exact'' qualifies}
Equation~(\ref{eq:shapley}) is evaluated over all 32 coalitions with no
sampling. Exactness therefore qualifies \emph{the aggregation step, conditional
on the fitted characteristic function}, and nothing else: finite data,
stochastic fits, hyperparameter choices and floating-point libraries all remain
sources of error, and we quantify the first of these with ten-seed intervals
throughout. Source ordering does not matter: permuting the players changes no
value by more than $2.8\times10^{-5}$.

\subsection{Algorithm and cost}\label{sec:algorithm}

Algorithm~\ref{alg:signalshap} fits the sources once, builds $C_u$ once, then
sweeps the 32 coalitions. Two properties make the values comparable: every
coalition is scored on the same $C_u$, and every head is fit on validation
while every value is measured on test. Cost is dominated by scoring, not by the
game: the lattice contributes a factor of 32, and exact enumeration stays
practical to roughly $n \le 12$. Generative AI (OpenAI Codex) was used for code
scaffolding and consistency checking; every number reported here was recomputed
from the released commit.

\paragraph{The temporal state is frozen}
Sources are fitted on the training fold and not refreshed between the
validation and test steps, so the test step is a two-step-ahead forecast from a
frozen state rather than a one-step-ahead forecast with the validation event
folded in. This understates absolute performance, and we report the size of the
understatement rather than leaving it implicit: refreshing raises $v(\G)$ on
MovieLens-1M by $31.7\%$ $[+30.2\%,+33.1\%]$ over ten seeds, positive on
$10/10$, while preserving the ordering at $\tau = 1.00$ on every seed. The
sources whose values move are $seq$ ($+0.01393$) and $cf$ ($+0.00199$), both
sign-stable; $ct$ and $rec$ move by less than $10^{-4}$ with no stable sign
(ESM~S3). The choice is deliberate, since refreshing would give each coalition
a different information state and break comparability, but it is a limitation
on absolute magnitudes.

\paragraph{A retrievability ceiling on Gowalla}
Because held-out venues are masked if already seen in training, a fraction
$\rho$ of evaluated users cannot have their test item retrieved at all, and
contribute $v_u(S)=0$ for all 32 coalitions. The game then dilutes exactly,
\begin{equation}
v(S) \;=\; \rho \cdot v_{\mathrm{live}}(S),
\label{eq:dilution}
\end{equation}
verified to $1.4\times10^{-17}$ across all coalitions. On Gowalla
$\rho = 0.501$: half the users are exact zeros, all magnitudes are halved,
and orderings, signs, rank correlations and ratios are exactly invariant. The
practical consequence is stated plainly in Section~\ref{sec:preconditions}.

\subsection{Formal properties}\label{sec:theory}

Efficiency holds by construction, so $\sum_g \varphi_g = v(\G)$ exactly. A
natural redundancy property, that a source duplicated into the system should
receive non-negative credit, is \emph{false} without monotonicity: we give a
three-player counterexample in ESM~S1 and record the corrected statement there
with its proof. This matters empirically rather than only formally, because all
three fitted games are non-monotone (Table~\ref{tab:preconditions}), so the
property does not apply on our data and negative $\varphi_g$ values are
faithful computations rather than implementation faults.

\subsection{Experimental setup}\label{sec:setup}

\paragraph{Players, baselines and declared overlaps}
The five players are those of Table~\ref{tab:sources}. Before computing any
attribution we declared two expected substitutions, $cf$--$pop$ (popularity
leaking into implicit-feedback collaborative filtering) and $ct$--$rec$ (shared
content input), so that the interaction indices could be read against a
prediction rather than fitted to. Reference points include a uniform-weight
head, a popularity-only ranker, LightGCN and SASRec; these are context for
absolute magnitudes and are deliberately under-tuned. They are not competitors
and no state-of-the-art claim is made or intended.

\paragraph{Corpora and protocol}
We use three timestamped corpora spanning a $36\times$ density range:
MovieLens-1M ($6\,038$ users, $3\,533$ items), the Video Games category of
Amazon Reviews 2023 ($7\,120 \times 3\,516$), and Gowalla check-ins
($8\,865 \times 82\,134$), each subsampled to fit the memory budget
(Table~\ref{tab:preconditions}). Timestamps are required, which is why these
three were chosen. Splits are per-user leave-last-out:
chronological within a user, which is standard for this protocol but not
globally time-blocked, so pooled training events postdate some users' held-out
events. We measured that rather than assuming it away: the mean fraction of a
user's training events that postdate their test event is $44\%$, $27\%$ and
$19\%$. A globally blocked replication on MovieLens-1M retains 526 of 6\,038
users and reproduces the paper's contrast, $\tau_{\LOOr} = 0.80$ against
$\tau_{\text{Shapley}} = 0.60$ with LOO picking the correct source and Shapley
the wrong one, but does \emph{not} reproduce the per-source attributions:
under the blocked split the flip moves from $cf$ to $pop$ and $seq$. The
phenomenon replicates; the named sources do not. Ten seeds measure training
noise on fixed datasets, not a population of systems.

\paragraph{Reporting protocol}
Attribution and retirement results are reported over ten training seeds
(42--51). Brackets are run-to-run intervals
$\bar x \pm t_{0.975,9}\,s_x/\sqrt{10}$ and describe stochastic refitting on
fixed datasets. We are explicit that this is not population inference: ten
seeds bound training noise for these three corpora, and any statement about how
often the phenomenon occurs across hybrid recommenders in general would require
a sample of systems, which we do not have. Proportions carry Wilson intervals
rather than bare point estimates. A gap is called \emph{material} when it
exceeds $10^{-3}$ in absolute value, the same threshold applied to monotonicity
violations, and this threshold was fixed before the comparisons were run.

\subsection{Preconditions declared before the results}\label{sec:preconditions}

Two preconditions were declared before any attribution was computed, so that a
corpus could be disqualified on grounds independent of its results.

\emph{Monotonicity.} The redundancy argument of Section~\ref{sec:theory}
requires a monotone game. We therefore count violations
$v(S) > v(T)$ for $S \subset T$ on every fitted game rather than assume the
hypothesis. All three corpora violate it materially
(Table~\ref{tab:preconditions}), which is why the paper treats redundancy as an
interpretation rather than a theorem and why negative $\varphi_g$ values are
expected rather than anomalous.

\emph{Candidate recall.} Because the game is defined on a fixed pool, a test
item outside that pool is unreachable by every coalition and contributes zero
to all 32 values. Recall therefore bounds what the game can observe.

"""

PRECONDITIONS_TAIL = r"""
Candidate recall is an applicability diagnostic, not a quality metric, and the
$0.60$ gate was fixed before the runs. Only MovieLens-1M clears it in the
frozen configuration. Amazon-VG reaches $0.589$ at the frozen cap
$N_{\max}=600$ and $0.750$ at $N_{\max}=1\,200$, with the same qualitative
attribution at both, so we report it as gate-clearing only under the larger
cap. On Gowalla the ceiling of Equation~(\ref{eq:dilution}) bounds recall above
by $\rho = 0.501 < 0.60$, so the gate is unattainable at \emph{any} candidate
pool size and the corpus is retained as a relative stress test, for orderings
and signs rather than absolute magnitudes. Artefacts failing the gate are
admitted only via a declared exemption list and carry the restriction string
into every table built from them.
"""

VERIFICATION = r"""
\section{Verifying the aggregation}\label{sec:verification}

Before interpreting any attribution we check the aggregation against
constraints whose answers are known independently of the data.

On observational data the correct allocation is unknown, so this section does
not validate real-system magnitudes. It checks whether the implementation
satisfies constraints fixed in advance.

\paragraph{Known-answer games}
Six analytic games with closed-form Shapley vectors, spanning additive,
substitutive, complementary, null-player, harmful and unanimity structures, are
recovered with maximum absolute error $0$ (ESM~Table~S1). The null-player and
harmful games matter most here: our fitted games are non-monotone and produce
negative $\varphi_g$, so it is necessary to establish that a negative value is
a faithful computation rather than an implementation artefact, and the harmful
game confirms that $-2$ is recovered exactly. Additivity, the remaining
uniqueness axiom that no other check exercises, holds to $4.4\times10^{-16}$.
Efficiency on the fitted corpora holds to machine precision.

\paragraph{Duplicate injection}
Symmetry is checked on real data by injecting a near-duplicate of an existing
source at the level of raw scores, before any $z$-normalisation:
\begin{equation}
s_{g_{\mathrm{dup}}}(u,i) = s_g(u,i) + \eta\,\hat\sigma_g\,\epsilon_{u,i},
\qquad \epsilon_{u,i}\overset{\mathrm{i.i.d.}}{\sim}\mathcal N(0,1),
\label{eq:dup}
\end{equation}
with $g = cf$, $\hat\sigma_g$ one scalar per source over all eligible entries,
and the candidate set built \emph{before} injection and held fixed so that the
clone never enters retrieval and only the player set changes. At $\eta = 0$ the
original and the clone are exchangeable, so any rule satisfying symmetry must
give them equal value; ours does, to numerical precision. Ablation instead
assigns \emph{both} clones zero, since either alone is redundant given the
other. That is the substitutability failure of LOO reproduced under a
controlled constraint rather than inferred from observational data. As $\eta$
grows the copy becomes noisier and LOO becomes non-zero but erratic in sign.

\paragraph{What exactness buys}
Calling the aggregation exact is only meaningful if sampling would have been
worse, so we measured it. On a complete 32-coalition game we estimated
$\varphi$ by permutation sampling and by KernelSHAP at budgets
$M\in\{50,100,500,2000\}$ with 20 repeats each
(Figure~\ref{fig:sampling}). At $M=500$, permutation sampling still has a
95th-percentile error of $2.73\%$ of $v(\G)$, against a ten-seed spread of
$2.22\%$ and a materiality threshold of $1.91\%$; KernelSHAP is worse
throughout at this player count. Sampling error at a realistic budget is
therefore \emph{larger} than the effects this paper reports, and could
manufacture or erase a material sign flip. Exactness is load-bearing rather
than cosmetic. The measurement is made on the end-to-end recall game, the
complete lattice we persist; absolute errors do not transfer to the NDCG game,
but errors relative to $v(\G)$ do.

\begin{figure}[tp]
\centering
\includegraphics[width=0.86\textwidth]{Fig8.png}
\caption{Sampled Shapley error against exact enumeration, as a percentage of
$v(\G)$, over 20 repeats per budget; bands span the mean to the 95th
percentile. Both reference lines are quantities this paper already uses: the
ten-seed spread of the fitted values, and the $10^{-3}$ materiality threshold.
Permutation sampling crosses neither until well past $M=500$.}
\label{fig:sampling}
\end{figure}

\paragraph{Other values and interactions}
A comparator is informative only if it is genuinely a different member of the
semivalue family. The size-uniform weighting $p_k = 1/n$ is not: substituting
it returns Equation~(\ref{eq:shapley}) exactly, because
$|S|!\,(n-|S|-1)!/n! = 1/\bigl(n\binom{n-1}{|S|}\bigr)$, and it agrees to
exactly zero difference. We note this because the identity is easy to miss and
makes that particular comparison vacuous.

Among the genuine comparators, Banzhaf and two binomial semivalues rank the
sources identically to Shapley on MovieLens-1M. Robustness is not uniform
across corpora, and the honest statement is a conjunction rather than a
generalisation. On Gowalla all three agree with Shapley at $\tau = 0.80$, with
the $q = 0.25$ semivalue promoting $ct$ over $cf$ across a margin of only
$0.00037$ and Banzhaf transposing $pop$ and $rec$ across $0.00017$; these are
near-ties, not disagreements of substance. On Amazon-VG the disagreement is
stronger and we report it as a limitation rather than bury it: $\tau = 0.60$,
with Shapley leading on $cf$ and Banzhaf on $seq$. The ordering is therefore
robust to the coalition weighting on two corpora and not on the third.

Pairwise interaction indices recover part of the overlap declared in advance in
Table~\ref{tab:sources}. The two most negative pairs on MovieLens-1M are
$cf$--$seq$ at $-0.054$ and $cf$--$pop$ at $-0.025$, both substitutive, and
$cf$--$pop$ is one of the two declared overlaps. The recovery is partial rather
than complete, which is what we report. Full semivalue and interaction tables
are in ESM~S3.
"""

RESULTS = r"""
\section{Results}\label{sec:results}

\subsection{Allocation and removal disagree}\label{sec:attribution}

"""

RESULTS_MID = r"""
Table~\ref{tab:loo} gives the per-source comparison over ten stochastic fits
and Figure~\ref{fig:scatter} plots it. Two of the three corpora contain a
\emph{material} sign disagreement, meaning one whose gap exceeds the $10^{-3}$
threshold we also apply to monotonicity.

On MovieLens-1M the source is $cf$. Shapley scores it $+0.01573$, the second
most valuable source in the system; $\LOOr$ scores it $-0.00457$, meaning its
removal \emph{improves} the fixed-candidate game. The paired gap is $+0.02030$
$[+0.02007,+0.02053]$, or $38.8\%$ of the ten-seed $v(\G) = 0.05225$, positive
on $10/10$ fits. On Gowalla the source is $pop$, with a gap of $+0.00207$
$[+0.00197,+0.00217]$, $12.2\%$ of $v(\G) = 0.01705$, again $10/10$: LOO scores
the popularity signal negative where Shapley scores it positive. Because the
gap is a paired quantity it is computed per seed and then aggregated, which is
why its interval is not the difference of the two columns beside it.

Amazon-VG is a negative case and bounds the claim. Its only sign flip, on
$rec$, is $0.00063$, below the materiality threshold. The accurate statement is
therefore the weaker one: material sign disagreement occurs on two of the three
systems studied and is absent on the third. Three corpora cannot estimate how
common it is, and nothing in either rule announces in advance whether a given
system will exhibit it. Both material flips survive a $\lambda$ sweep over
eight orders of magnitude, three source-blind candidate pools, and score
perturbation at $\sigma\in\{0.1,0.5\}$ (ESM~S3).

\paragraph{Mechanism}
The account is \emph{qualitatively} the redundancy story, though formally
unavailable: all three fitted games are non-monotone, so the positivity
conclusion of Section~\ref{sec:theory} does not apply and what follows is
interpretation rather than theorem. A source whose signal is covered by others
costs little when removed from the \emph{grand} coalition, because the others
absorb its role, and ablation observes only that single contrast. Exact
enumeration averages the source's contribution over all $16$ coalitions in
which it can appear, including those where nothing covers for it, and so
recovers value the overlap conceals. On MovieLens-1M the collaborative signal
overlaps the sequential and popularity signals; on Gowalla it is the popularity
signal that is covered, by a geographic content signal essentially tied with
$cf$ at the top of the ranking ($0.00678$ against $0.00711$, an ordering that
resampling reverses).

\paragraph{Orderings, and no cross-corpus claim}
The per-corpus orderings are
$seq \succ cf \succ pop \succ rec \succ ct$ (MovieLens-1M),
$cf \succ seq \succ ct \succ pop \succ rec$ (Amazon-VG) and
$cf \succ ct \succ seq \succ pop \succ rec$ (Gowalla, whose leading pair is
within $0.00033$ and exchanges under resampling). Pairwise Kendall $\tau$
between corpora is $0.40$, $0.20$ and $0.80$, none significant at $n = 5$
sources, so we make no cross-corpus consistency claim: identical near-zero
values from sources with no usable input would inflate such a comparison and
are not evidence of agreement.

\subsection{Which estimand predicts retirement cost?}\label{sec:retirement}

The sharper test is whether attribution predicts what removing a source
actually costs. We retired each source \emph{entirely}, from retrieval and
fusion alike, rebuilt candidates from the survivors, refitted, and measured the
observed end-to-end NDCG@10 loss. We write \emph{observed} rather than
\emph{true} throughout: this is one measured realisation under the reported
protocol, not a population quantity.

Two variants of the game bracket the design choice. Holding the deployed
grand-coalition head $w^{(\G)}$ fixed and merely masking it to $S$ gives
$v_{\mathrm{fixed}}$; letting each coalition retrieve its own $C_u(S)$ and
refit gives $v_{\mathrm{e2e}}$, under which coalition values are no longer
comparable across a fixed item set, which is exactly the property the main game
preserves. All three estimands are reported side by side in ESM~Table~S9; their
orderings agree at $\tau \ge 0.80$ on both corpora where the comparison is
available.

"""

RESULTS_TAIL = r"""
The comparison is not tautological, and the reason is the distinction fixed in
Section~\ref{sec:background}. The LOO column of Table~\ref{tab:retirement} is
$\LOOr$, computed on the same kind of fixed-candidate game as the Shapley
column. It is \emph{not} $\LOOe$, which equals the observed loss by
construction and so could not be evaluated as a predictor of it. The finding is
therefore informative: a quantity computable \emph{without} re-running
retrieval predicts the expensive end-to-end outcome, and predicts it far better
than the Shapley value of the same game.

On seed 42 (Table~\ref{tab:retirement}) $\LOOr$'s ranking matches the observed
loss exactly, $\tau = 1.00$ against Shapley's $0.20$ (exact two-sided
permutation $p = 0.017$ and $p = 0.82$ at $n = 5$ sources), and it identifies
$cf$ as the source with the smallest observed removal loss where Shapley
selects $ct$. Removing $cf$ improves the end-to-end metric by $0.00468$.

Over ten seeds (Table~\ref{tab:retire-seeds}) $\LOOr$'s mean rank agreement is
$0.96$, $0.96$ and $1.00$ against Shapley's $0.20$, $0.74$ and $0.80$. $\LOOr$
is not perfect on every seed, but across all thirty fits it is never worse:
29 wins and one tie. The practical gap is starker than the correlations: $\LOOr$
identifies the source with the smallest observed removal loss on $100\%$,
$90\%$ and $100\%$ of seeds against $0\%$, $50\%$ and $0\%$ for Shapley, so on
two of three corpora Shapley never once selects the right source to switch off.
Ten seeds bound these proportions loosely and we give Wilson intervals rather
than let point estimates stand: $100\%$ is $[72,100]$ and $0\%$ is $[0,28]$, so
the separation survives on MovieLens-1M and Gowalla while the Amazon contrast,
$[60,98]$ against $[24,76]$, overlaps. Pairing by seed, $\Delta\tau =
\tau_{\LOOr}-\tau_{\text{Shapley}}$ is $+0.76\ [+0.70,+0.80]$, $+0.22\
[+0.16,+0.28]$ and $+0.20$ with zero variance, no interval containing zero. We
read this as run-to-run stability of the contrast on fixed datasets, not as
population inference over hybrid recommenders.

The result is consistent with the theory rather than a contradiction of it.
Removing $cf$ improves end-to-end NDCG@10 by $0.00468$ while dropping candidate
recall from $0.748$ to $0.691$: the collaborative signal is substantially
substitutive with $seq$ and $pop$, the two most negative interaction pairs, so
inside the grand coalition its scores add noise the others already cover.
Shapley averages over coalitions in which $cf$ has no substitute and therefore
assigns the capability positive value \emph{under the declared game}. We say
that rather than ``correctly'': no external ground truth for the allocation
exists, and the two statements describe different games.
"""

DISCUSSION = r"""
\section{Discussion}\label{sec:discussion}

The two rules answer different questions, and Table~\ref{tab:decisions-kais}
maps each decision to the estimand that answers it. $\LOOe$ is definitionally
aligned with ``what happens in this offline protocol if I remove this one
source''. Shapley answers ``how should measured ranking quality be divided
among sources under the declared game''. We claim only the latter.

\begin{table}[tp]
\caption{Decision-to-estimand mapping. The final row is the paper's own
boundary: the contrast between allocation and removal replicates under a
globally blocked split, while the identity of the flipping source does not.}
\label{tab:decisions-kais}
\small
\begin{tabularx}{\textwidth}{@{}lX@{}}
\toprule
Decision & Estimand that answers it \\
\midrule
Remove one source from the deployed system
  & $\LOOe$; $\LOOr$ tracks it closely here without re-running retrieval \\
Divide measured ranking utility among sources
  & Shapley on the declared game \\
Rank sources under other coalition weightings
  & Banzhaf or binomial semivalues, for ordering only \\
Decide where to invest engineering effort next
  & \emph{Not established.} Requires headroom, cost, latency and risk, none of
    which enter $v$ \\
Trust the named flipping source under a global time split
  & \emph{No.} Trust the allocation-versus-removal contrast: \emph{yes} \\
\bottomrule
\end{tabularx}
\end{table}

A positive $\varphi_g$ licenses the statement that source $g$ is allocated
value under this game. It does not license keeping $g$, and a negative
$\varphi_g$ does not license dropping it; on MovieLens-1M the source with the
second-largest allocation is also the one whose removal improves the metric.
The allocation is descriptive, not prescriptive. In particular it is not a
guide to future engineering investment, which additionally depends on
improvement headroom, implementation cost, latency, maintenance burden and
deployment risk, none of which enter the characteristic function.

\paragraph{Scope of the explainability claim}
The method explains a fitted system at the level of architectural sources. The
global values divide baseline-centred ranking utility and the per-user
decomposition is an exact identity, so faithfulness is defined relative to the
declared characteristic function and verified by the checks of
Section~\ref{sec:verification}. Interaction indices add information about
substitutive behaviour under that same game, but they are not causal redundancy
estimates. We did not evaluate whether end users understand or prefer these
explanations, and we do not establish seed stability of individual-user
attributions. The supported claim is system-diagnostic source attribution, not
human-facing explanation quality.

\subsection{Threats to validity}\label{sec:threats}

\emph{Construct.} The game is ranking-stage: it holds candidates fixed so that
coalition values are comparable, which is exactly why it is not the deployment
intervention. That gap is the paper's subject, not an oversight.
\emph{Internal.} Splits are per-user chronological rather than globally
blocked, with the leakage fractions quantified in Section~\ref{sec:setup}; the
blocked replication preserves the contrast but not the named sources.
\emph{Statistical.} Ten seeds describe training randomness on fixed datasets.
Intervals and paired tests are conditional on treating seeds as exchangeable
runs and are not population inference.
\emph{External.} Three corpora, five deliberately simple players, one
subsample per corpus. Gowalla's magnitudes are halved by the retrievability
ceiling, so only its orderings and signs are read. No causal or off-policy
claim is made, no fairness claim is made, and no state-of-the-art comparison is
intended: the neural components that appear in the supplement are reference
points, are under-tuned, and are not competitors.
\emph{Provenance.} The ten-seed attribution and retirement results are primary
and were regenerated under the final source-symmetric candidate rule. Several
labelled single-seed diagnostics predate that regeneration and are sensitivity
analyses rather than confirmatory evidence; on MovieLens-1M the two rules agree
to $\max_g|\Delta\varphi_g| = 2.8\times10^{-5}$ with identical ordering.
ESM~Table~S3 lists which group is which, including the Gowalla diagnostics that
could not be regenerated because five dense $8\,865\times82\,134$ score
matrices exhausted memory.

\section{Conclusion}\label{sec:conclusion}

Source ablation and Shapley attribution answer different questions, and on two
of three timestamped hybrid recommenders they disagree in sign for at least one
source by a material margin. When each source is retired outright,
ranking-stage leave-one-out tracks the observed end-to-end cost and Shapley
does not: mean rank agreement $0.96$--$1.00$ against $0.20$--$0.80$, and the
source with the smallest observed removal loss identified on $90$--$100\%$ of
fits against $0$--$50\%$. Exact enumeration is what makes these comparisons
safe, since sampling at a realistic budget carries error larger than the
effects themselves.

The claim is bounded: we allocate credit in a declared ranking-stage game on
three corpora with five simple players under one offline protocol, and we do
not offer retirement guidance, causal identification, or a fusion method.
Future work: cost-aware characteristic functions that price latency and
maintenance; principled sampling beyond $n \approx 12$; graph-neural and
Transformer components as players rather than baselines; and a repeat-aware
protocol for check-in data, where the retrievability ceiling bites hardest.
"""

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
      All derived data behind every reported number is released with the code,
      together with \texttt{MANIFEST.json}, which records a SHA-256 for each
      artefact file with the commit and environment that produced it, including
      the BLAS backend. \texttt{PROVENANCE.md} maps every table and figure to
      the artefact, platform, candidate rule and seeds behind it. A reader
      reproducing from raw data must refetch the corpora first, and a run on a
      different BLAS reproduces the reported signs and orderings but not every
      fifth decimal.

\item \textbf{Code availability.} The implementation, configuration files, and
      scripts required to reproduce the reported experiments, tables, and
      figures are publicly available at
      \url{https://github.com/mouadlouhichi/signalshap}, released as tag
      \texttt{kais-submission}; the corresponding commit is recorded inside
      \texttt{MANIFEST.json} alongside the SHA-256 of every artefact.

\item \textbf{Author contributions.} \textbf{M.\ Louhichi:} conceptualisation,
      methodology, software, formal analysis, investigation, writing (original
      draft), visualisation. \textbf{R.\ Nesmaoui:} software, validation, data
      curation, writing (review and editing). \textbf{M.\ Lazaar:} supervision,
      methodology, resources, writing (review and editing).

\item \textbf{Use of AI tools.} In line with Springer Nature's guidance, we
      disclose that the authors used OpenAI Codex for code scaffolding,
      editorial review, and consistency checking, as also stated in
      Section~\ref{sec:algorithm}. No text, result, figure, or citation was
      generated for inclusion without author verification, and no AI system is
      listed as an author.
\end{itemize}

\bibliography{paper}

\end{document}
"""


#: Cross-references inside lifted floats that point at material which the
#: split moved to the ESM, or at equation labels this rewrite renamed. Left
#: unrewritten these render as `??`, which `test_kais_split.py` catches.
REF_FIXUPS = {
    r"\ref{tab:repeats}": "ESM~Table~S8",
    r"\ref{prop:loo}": "Section~\\ref{sec:theory}",
    r"\ref{eq:cand}": r"\ref{eq:candidates}",
    r"\ref{eq:zscore}": r"\ref{eq:candidates}",
    r"\ref{eq:baseline}": r"\ref{eq:game}",
}


def _fix_refs(src: str) -> str:
    for old, new in REF_FIXUPS.items():
        src = src.replace(old, new)
        # \eqref carries its own parentheses; keep it valid when retargeted.
        src = src.replace(old.replace(r"\ref{", r"\eqref{"),
                          new.replace(r"\ref{", r"\eqref{")
                          if new.startswith("\\ref{") else new)
    return src


#: Section labels that live in the main article. The ESM is compiled as its
#: own document, so a \ref to one of these would render as `??`. Springer also
#: asks that supplementary captions be readable on their own, so the right fix
#: is prose naming the main article rather than a dangling cross-reference.
ESM_SECTION_NAMES = {
    "sec:game": "the cooperative game",
    "sec:algorithm": "the algorithm",
    "sec:setup": "the experimental setup",
    "sec:preconditions": "the preconditions",
    "sec:recovery": "the verification section",
    "sec:validating": "the verification section",
    "sec:alternatives": "the semivalue comparison",
    "sec:results": "the results",
    "sec:estimands": "the retirement comparison",
    "sec:threats": "the threats to validity",
    "sec:theory": "the formal properties",
    "sec:discussion": "the discussion",
    "sec:intro": "the introduction",
    "sec:background": "the background",
    "sec:related": "the related work",
    "sec:conclusion": "the conclusion",
    "sec:limitations": "the limitations",
    "sec:explainability": "the explainability scope",
    "sec:sources": "the source definitions",
    "sec:hyperparams": "the configuration",
    "sec:analytic": "the analytic games",
    "app:fusion": "this section",
}


def _esm_localise(src: str) -> str:
    """Rewrite main-article cross-references for the standalone supplement."""
    def repl(m: re.Match[str]) -> str:
        label = m.group(2)
        if label in ESM_SECTION_NAMES:
            return ESM_SECTION_NAMES[label] + " of the main article"
        return m.group(0)

    # "Section~\ref{sec:game}" -> "the cooperative game of the main article"
    src = re.sub(r"(?:Section|Sec\.|Appendix)~?\\ref\{([^}]*)\}",
                 lambda m: (ESM_SECTION_NAMES[m.group(1)] + " of the main article"
                            if m.group(1) in ESM_SECTION_NAMES else m.group(0)),
                 src)
    src = re.sub(r"\\(ref|eqref)\{(sec:[^}]*|app:[^}]*)\}", repl, src)
    # Equation labels defined only in the main article. `_fix_refs` may have
    # already retargeted eq:baseline to eq:game, which is also main-only.
    src = re.sub(r"Equation~?\\eqref\{eq:game\}",
                 "the characteristic function of the main article", src)
    src = re.sub(r"\\eqref\{eq:game\}",
                 "the characteristic function of the main article", src)
    src = re.sub(r"\\ref\{eq:game\}",
                 "the characteristic function of the main article", src)
    # Equation labels that live only in the main article.
    src = re.sub(r"Equation~?\\eqref\{eq:baseline\}",
                 "the baseline definition in the main article", src)
    src = re.sub(r"\\eqref\{eq:baseline\}",
                 "the baseline definition in the main article", src)
    src = re.sub(r"\\ref\{eq:baseline\}",
                 "the baseline definition in the main article", src)
    return src


def build_main() -> str:
    parts = [MAIN_PREAMBLE, FRONT, INTRO]

    # Figure 1 is the pipeline diagram: it orients the reader before any
    # formalism and is one of the eight display items the plan keeps.
    parts.append(_esm_localise(_fix_refs(float_src("fig:workflow", star=False, placement="tp"))))

    parts.append(RELATED)
    parts.append(METHOD)

    # Preconditions table carries the recall gate, rho and monotonicity.
    parts.append(_fix_refs(
        float_src("tab:preconditions", star=False, placement="tp")))
    parts.append(PRECONDITIONS_TAIL)

    # Algorithm stays in main: reviewers ask for it and it is compact.
    parts.append(_fix_refs(float_src("alg:signalshap", placement="tp")))

    parts.append(VERIFICATION)

    parts.append(RESULTS)
    parts.append(_esm_localise(float_src("tab:loo", star=False, placement="tp")))
    parts.append(float_src("fig:scatter", star=False, placement="tp"))
    parts.append(RESULTS_MID)
    parts.append(_esm_localise(float_src("tab:retirement", star=False, placement="tp")))
    parts.append(float_src("tab:retire-seeds", star=False, placement="tp"))
    parts.append(RESULTS_TAIL)

    parts.append(DISCUSSION)
    parts.append(BACK)
    return "\n".join(parts)


# --------------------------------------------------------------------------
# ESM. Self-contained, S-numbered, captions readable without the main text.
# --------------------------------------------------------------------------

ESM_PREAMBLE = r"""%% Electronic Supplementary Material for the KAIS submission.
%%
%% GENERATED FILE -- do not edit by hand. Generator: scripts/make_kais_main.py
%%
%% Self-contained by design: Springer asks that supplementary captions be
%% intelligible without the main text, so each float below restates what it
%% shows. Floats are lifted verbatim from paper-kbs/kbs-article.tex, so every
%% number matches the artefact-validated source.
\documentclass[11pt,a4paper]{article}
\usepackage[margin=25mm]{geometry}
""" + COMMON_PACKAGES + r"""
\usepackage{hyperref}

%% S-numbering for every float and section.
\renewcommand{\thesection}{S\arabic{section}}
\renewcommand{\thetable}{S\arabic{table}}
\renewcommand{\thefigure}{S\arabic{figure}}
\renewcommand{\theequation}{S\arabic{equation}}

\title{Electronic Supplementary Material\\[2mm]
\large Ranking-stage source attribution is not source removal:\\
exact Shapley analysis of five-source hybrid recommenders}
\author{Mouad Louhichi \and Redwane Nesmaoui \and Mohamed Lazaar}
\date{}

\begin{document}
\maketitle

\noindent This supplement holds the proofs, the full experimental
configuration, and the robustness suite for the main article. Sections are
numbered S1--S5 and are referenced from the main text. Every table and figure
here is reproduced from the same artefacts as the main article; captions are
written to be read independently.

\tableofcontents
\newpage
"""

ESM_S1 = r"""
\section{Redundancy requires monotonicity}\label{esm:proofs}

The main text states that a natural redundancy property is false without
monotonicity. We record the property, the counterexample, and the corrected
statement here.

\paragraph{The property as usually stated}
If a source is duplicated into the system, one might expect each copy to
receive non-negative credit. This is false for general characteristic
functions.

\paragraph{Counterexample}
Take three players $\{a, b, c\}$ where $b$ and $c$ are exact duplicates, and
let $v$ be non-monotone: $v(\{a\}) = 1$, $v(\{a,b\}) = v(\{a,c\}) = 0.5$,
$v(\{b\}) = v(\{c\}) = v(\{b,c\}) = 0$, $v(\{a,b,c\}) = 0.5$. The duplicated
pair is symmetric, so $\varphi_b = \varphi_c$ by the symmetry axiom, and
efficiency gives $\varphi_a + 2\varphi_b = 0.5$. Direct enumeration yields
$\varphi_b = \varphi_c = -1/12 < 0$. Both copies receive negative credit.

\paragraph{Corrected statement}
If $v$ is monotone, that is $v(S) \le v(T)$ whenever $S \subseteq T$, then
every marginal contribution is non-negative and hence $\varphi_g \ge 0$ for all
$g$, including duplicated players. Monotonicity is the missing hypothesis.

\paragraph{Why this matters empirically}
All three fitted games in the main article are non-monotone
(Table~2 of the main text records the material violation counts), so the
property does not apply to our data. Negative Shapley values in the main
results are therefore faithful computations under a non-monotone game, not
implementation faults. The harmful analytic game in
Table~\ref{tab:analytic} confirms that the implementation recovers a negative
value exactly when one is correct.
"""

ESM_S2_HEAD = r"""
\section{Notation and full configuration}\label{esm:config}

Table~\ref{tab:notation} fixes notation. Table~\ref{tab:hyper} gives the
complete experimental configuration, including every hyperparameter, its
value, and how it was selected. Table~\ref{tab:provenance} maps each group of
reported results to the artefact, platform, candidate rule and seed range that
produced it, including the one group that was regenerated under a different
candidate rule.
"""

ESM_S3_HEAD = r"""
\section{Verification detail and the robustness suite}\label{esm:robustness}

\subsection{Analytic games and duplicate injection}

Table~\ref{tab:analytic} lists the six analytic games with known Shapley
vectors and the maximum absolute recovery error on each, which is zero
throughout. Table~\ref{tab:recovery} reports the duplicate-injection
diagnostics on MovieLens-1M: an exact clone of the collaborative source
receives credit equal to its original to numerical precision, while
leave-one-out assigns both clones zero.

\subsection{Alternative values and interactions}

Table~\ref{tab:taylor} gives the pairwise Shapley interaction indices on
MovieLens-1M over ten stochastic fits. The two most negative pairs,
$cf$--$seq$ and $cf$--$pop$, are the substitutions declared in advance in the
main text, so the declared overlap is partially recovered by the data.

Semivalue comparison, summarised in the main text, is as follows.
On MovieLens-1M, Banzhaf and both binomial semivalues rank the five sources
identically to Shapley. The size-uniform semivalue is algebraically identical
to Shapley, since
$|S|!\,(n-|S|-1)!/n! = 1/\bigl(n\binom{n-1}{|S|}\bigr)$, and agrees to exactly
zero difference; we note this because the identity is easy to miss and makes
that particular comparison vacuous. On Gowalla, Banzhaf and both binomial
semivalues agree with Shapley at $\tau = 0.80$; the $q = 0.25$ semivalue
promotes $ct$ over $cf$ across a margin of $0.00037$, and Banzhaf and
$q = 0.75$ transpose $pop$ and $rec$ across a margin of $0.00017$. On
Amazon-VG the disagreement is stronger and we report it as a limitation of the
robustness claim: $\tau = 0.60$, with Shapley leading on $cf$ and Banzhaf on
$seq$.

\subsection{Sensitivity analyses}

Table~\ref{tab:ablations} summarises the ablation and sensitivity suite.
Figure~\ref{fig:robustness} shows the candidate-cap and ridge-penalty sweeps at
seed 42, and Figure~\ref{fig:redundancy} the pairwise source-score rank
correlations by corpus. Figure~\ref{fig:shares} gives per-source Shapley values
with seed-based intervals on all three corpora.

The headline robustness results, each verified against its artefact, are:
the ridge penalty $\lambda$ swept over eight orders of magnitude leaves both
material sign flips intact; three source-blind candidate pool rules leave both
flips intact, and oracle-pool recall equals $\rho$ exactly on every corpus,
which independently confirms the dilution identity; Gaussian score perturbation
at $\sigma \in \{0.1, 0.5\}$ in units of each source's own standard deviation
leaves both flips intact on all three corpora; refreshing the frozen temporal
state raises $v(\G)$ on MovieLens-1M by $31.7\%$ $[+30.2\%, +33.1\%]$ while
preserving the ordering at $\tau = 1.00$ on all ten seeds; and swapping the
payoff metric to Recall@10 or MRR@10 preserves the ordering at $\tau = 1.00$.

ESM~Table~S8 audits repeat events, which is what produces the
retrievability ceiling on Gowalla: $49.90\%$ of evaluated users there have
their test venue already in training, and masking makes it unretrievable, so
those users contribute zero to every coalition.

\subsection{Three estimands}

Table~\ref{tab:estimands} reports the same seed-42 game under three
constructions: the refitted head used in the main text, a fixed grand-coalition
head merely masked to each coalition, and a fully end-to-end game in which each
coalition retrieves its own candidates. The refitted-head rows use the final
source-symmetric candidate rule; the other two predate that regeneration and
are retained as a sensitivity analysis, so the table compares \emph{orderings}
across estimands rather than numerical estimates from a single artefact.
"""

ESM_S4_HEAD = r"""
\section{Sampling error against exact enumeration}\label{esm:sampling}

The main text reports that permutation sampling at $M = 500$ has a
95th-percentile error exceeding both the ten-seed spread and the materiality
threshold. Table~\ref{tab:sampling-esm} gives the full grid behind
Figure~8 of the main article.

\begin{table}[htbp]
\centering
\caption{Sampled Shapley error against exact enumeration on a complete
32-coalition game, over 20 repeats per budget. Values are
$\|\hat\varphi - \varphi\|_\infty$ as a percentage of $v(\G)$. For reference,
the ten-seed spread of the fitted values is $2.22\%$ and the $10^{-3}$
materiality threshold is $1.91\%$ of $v(\G)$.}
\label{tab:sampling-esm}
\small
\begin{tabular}{@{}lrrrr@{}}
\toprule
& \multicolumn{2}{c}{Permutation sampling} & \multicolumn{2}{c}{KernelSHAP} \\
\cmidrule(lr){2-3}\cmidrule(lr){4-5}
Budget $M$ & Mean & p95 & Mean & p95 \\
\midrule
$50$   & $6.68\%$ & $10.84\%$ & $20.85\%$ & $25.93\%$ \\
$100$  & $3.32\%$ & $6.33\%$  & $11.44\%$ & $18.60\%$ \\
$500$  & $1.62\%$ & $2.73\%$  & $4.87\%$  & $9.88\%$ \\
$2000$ & $0.90\%$ & $2.16\%$  & $2.34\%$  & $3.67\%$ \\
\bottomrule
\end{tabular}
\end{table}

The measurement uses the end-to-end recall game, which is the only complete
32-coalition characteristic function persisted in the released artefacts.
Enumeration on it satisfies efficiency to $1.1\times10^{-16}$, confirming the
estimator harness. Absolute errors do not transfer to the NDCG@10 game of the
main text; errors relative to $v(\G)$ do, which is why the table is expressed
that way. KernelSHAP is the weaker estimator here because at $n = 5$ its kernel
concentrates on few coalition sizes.
"""

ESM_S6_HEAD = r"""
\section{Full decision-to-estimand mapping}\label{esm:decisions}

The main article gives a five-row summary of which estimand answers which
question. Table~\ref{tab:decisions} is the complete mapping, including the rows
that were compressed for length. It records, for each decision a practitioner
might want to make, the quantity that actually answers it and whether this
study establishes that quantity or leaves it open.
"""

ESM_S5_HEAD = r"""
\section{Attribution-derived fusion: a negative result}\label{esm:fusion}

This section reports an experiment that did not work. We include it because the
natural next step after allocating credit is to \emph{use} the allocation, and
a reader is entitled to know that we tried and that it failed.

We mapped Shapley values to fusion weights, both globally and per user segment,
and compared the resulting ranker against the matched global head on the full
catalogue. Attribution-derived fusion gives no resolvable gain. Fusion weights
never see test outcomes, so this is not a leakage artefact; the allocation
simply is not a good weight vector, which is consistent with the main article's
position that the allocation is descriptive rather than prescriptive.

Figure~\ref{fig:fusion} shows the full-catalogue comparison and
Figure~\ref{fig:segments} the descriptive segment-level values. Segment
heterogeneity is descriptive only: segments were not pre-declared and the
comparison is not powered for segment-level inference. No cross-corpus omnibus
ranking is computed, because the corpora differ in protocol and cannot be
pooled.

This appendix is a negative result about one downstream use of the
attributions. It is not evidence for or against their correctness, which rests
on the checks in Section~\ref{esm:robustness}.
"""


def _esm_float(label: str, *, star: bool = False,
               placement: str = "htbp") -> str:
    """Lift a float into the supplement, localising its cross-references.

    Every ESM float goes through here, so no float can accidentally keep a
    dangling reference to a main-article section.
    """
    return _esm_localise(_fix_refs(
        float_src(label, star=star, placement=placement)))


def build_esm() -> str:
    parts = [ESM_PREAMBLE, ESM_S1, ESM_S2_HEAD]

    # S2: notation and configuration.
    parts.append(_esm_float("tab:notation"))
    parts.append(_esm_float("tab:hyper"))
    parts.append(_esm_float("tab:provenance"))

    # S3: verification detail and the robustness suite.
    parts.append(ESM_S3_HEAD)
    parts.append(_esm_float("tab:analytic"))
    parts.append(_esm_float("tab:recovery"))
    parts.append(_esm_float("tab:taylor"))
    parts.append(_esm_float("tab:ablations"))
    parts.append(_esm_float("tab:repeats"))
    parts.append(_esm_float("tab:estimands"))
    parts.append(_esm_float("fig:shares"))
    parts.append(_esm_float("fig:robustness"))
    parts.append(_esm_float("fig:redundancy"))

    # S4: sampling error (table authored inline, no lifted float).
    parts.append(ESM_S4_HEAD)

    # S5: the full decision mapping.
    parts.append(ESM_S6_HEAD)
    parts.append(_esm_float("tab:decisions"))

    # S6: the fusion negative result.
    parts.append(ESM_S5_HEAD)
    parts.append(_esm_float("fig:fusion"))
    parts.append(_esm_float("fig:segments"))

    parts.append("\n\\end{document}\n")
    return "\n".join(parts)


def count_words(tex: str) -> int:
    """Approximate body word count: prose only, excluding floats and maths.

    Deliberately conservative in the same direction as texcount so the number
    can be compared against the 15,000 limit without flattering ourselves.
    """
    body = tex[tex.index(r"\section{Introduction}"):]
    body = body[:body.index(r"\backmatter")] if r"\backmatter" in body else body
    body = re.sub(r"(?<!\\)%.*", "", body)
    body = re.sub(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", "", body, flags=re.S)
    body = re.sub(
        r"\\begin\{(table|figure|algorithm|tabular|tabularx|tabular\*|align|equation|aligned|algorithmic)\*?\}"
        r".*?\\end\{\1\*?\}", "", body, flags=re.S)
    body = re.sub(r"\$[^$]*\$", " X ", body)
    body = re.sub(r"\\[a-zA-Z@]+\*?(\[[^\]]*\])?", " ", body)
    body = re.sub(r"[{}&\\]", " ", body)
    return len(body.split())


def main() -> int:
    main_tex = build_main()
    esm_tex = build_esm()

    OUT_DIR.mkdir(exist_ok=True)
    MAIN.write_text(main_tex, encoding="utf-8")
    ESM.write_text(esm_tex, encoding="utf-8")

    for name in ("sn-jnl.cls", "sn-basic.bst"):
        shutil.copyfile(REPO / "paper" / name, OUT_DIR / name)
    shutil.copyfile(REPO / "paper-kbs" / "paper.bib", OUT_DIR / "paper.bib")

    figdir = OUT_DIR / "figures"
    figdir.mkdir(exist_ok=True)
    for fig in sorted((REPO / "paper-kbs" / "figures").glob("*.png")):
        shutil.copyfile(fig, figdir / fig.name)

    n_tab = len(re.findall(r"\\begin\{table\}", main_tex))
    n_fig = len(re.findall(r"\\begin\{figure\}", main_tex))
    n_alg = len(re.findall(r"\\begin\{algorithm\}", main_tex))
    words = count_words(main_tex)

    print(f"wrote {MAIN.relative_to(REPO)}")
    print(f"  body words (approx)  {words}")
    print(f"  display items        {n_tab} tables + {n_fig} figures "
          f"+ {n_alg} algorithm = {n_tab + n_fig + n_alg}")
    print(f"wrote {ESM.relative_to(REPO)}")
    print(f"  tables {len(re.findall(r'.begin.table.', esm_tex))}  "
          f"figures {len(re.findall(r'.begin.figure.', esm_tex))}")
    if words > 15000:
        print("  WARNING: over the KAIS 15,000-word limit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
