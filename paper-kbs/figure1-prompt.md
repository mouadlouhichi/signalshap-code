# Prompt: redesign the SignalShap architecture / workflow figure (Figure 1)

Copy everything between the rules into a fresh LLM session. It is
self-contained: it carries the method, the constraints, the journal's artwork
rules, and the specific failure modes the current figure has, so the model does
not need the paper.

Two notes before you use it.

**Pick one output format.** The prompt asks for TikZ, because Figure 1 is
currently live TikZ inside the manuscript (`\tikzfiguretrue`), which keeps
lettering vector-sharp and matched to the body font. If you would rather have a
raster you can drop into `figures/Fig1.png`, change the "Deliverable" section to
ask for a matplotlib script instead, and keep everything else.

**The hard constraint is honesty, not beauty.** The current figure is a clean
four-box left-to-right chain. That is the thing to fix: the pipeline is not a
chain, and a diagram that implies it is oversells the method. The prompt makes
that explicit and asks for the awkward parts to be drawn rather than smoothed
over.

---

## Task

Design the architecture and workflow figure (Figure 1) for a paper submitted to
*Knowledge-Based Systems* (Elsevier). Output compilable TikZ. I will tell you
what the system does, what the figure must convey, and what is currently wrong
with it. Ask me questions if something is underspecified; do not invent
mechanism.

## What the method is

**SignalShap** attributes the value of a hybrid recommender to its five signal
sources by treating them as players in a cooperative game and computing exact
Shapley values.

The five sources (players), each an independent scorer producing a
user-by-item score matrix:

| id | signal | how it scores |
|---|---|---|
| `cf` | collaborative filtering | ALS on implicit feedback, 64 factors |
| `ct` | content | TF-IDF cosine over item metadata |
| `pop` | popularity | log-frequency with 180-day exponential decay |
| `rec` | recency | decay over the user's last touch of an item's content cluster |
| `seq` | sequential | PPMI-SVD over windowed co-occurrence, 64 dims |

Two of these overlap **by declared design, not by discovery**: `pop`-`cf` (ALS
on implicit feedback chases popularity) and `rec`-`ct` (recency is defined over
content clusters). The overlap is the point of the paper, so the figure should
not draw five identical parallel boxes as if they were independent.

## The pipeline, stage by stage

1. **Split.** Leave-last-two-out per user, chronological. Last interaction is
   test, second-to-last is validation, the rest is training.

2. **Fit sources.** All five fit on the **training fold only**. Each produces a
   dense score matrix over eligible items. Items the user already consumed in
   training are masked to `-inf`.

3. **Build one fixed candidate set per user.** `C_u` is the union of each
   source's own top-N list, grown in up to 10 passes until it reaches the cap
   `N_max`, then truncated by summed reciprocal rank with ties broken by item
   index.

   **This is the single most important structural fact in the figure.** `C_u`
   is built once and is *coalition-independent*: all 32 coalitions rank exactly
   the same items. The rejected alternative, drawing candidates from the
   grand-coalition scorer, would hand the grand coalition a pool selected in its
   own favour and bias every Shapley value. The figure must make the
   "built once, shared by all coalitions" property unmissable.

4. **Enumerate all 2^5 = 32 coalitions.** For each subset `S` of the five
   sources, fit a ridge fusion head `w^(S)` on the **validation** targets, rank
   `C_u` by the fused score, and evaluate NDCG@10 against the **test** item.
   The coalition value is

   `v(S) = mean over users of [ NDCG@10(ranking under S) - b_u ]`

   with `v(empty) = 0` exactly and per user. `b_u` is a deterministic
   expected-random-ranking baseline, closed form, no permutation drawn.

   Efficiency: the ridge head needs only the Gram sufficient statistics
   `A = sum_u |C_u|^-1 Z_u^T Z_u` and `c = sum_u |C_u|^-1 Z_u^T y_u^val`,
   accumulated **once**. Every coalition is a submatrix `A_SS`, `c_S`. There is
   no 32-fold pass over the data. If the figure shows the coalition loop, it
   should not imply 32 full refits over the corpus.

5. **Aggregate to Shapley values** by exact enumeration over all 32 coalitions:
   no sampling, no KernelSHAP-style estimator variance. Produces both a global
   `phi_g` per source and a per-user decomposition `phi_g(u)`, which are related
   by exact linearity.

6. **Diagnostics out.** Source credit, ranking-stage leave-one-out for
   comparison, and pairwise interaction indices.

## The three data folds, and the one subtlety worth drawing

This trips up readers, and the current figure hides it:

- sources fit on **train**
- fusion heads fit on **validation** targets
- coalition values scored on **test**

so no coalition value is measured in-sample. But the source *state is frozen at
the training fold*: the validation interaction is **not** appended to the user's
history before test scoring and **not** masked out of the test ranking. One
frozen source state serves both folds. It is a two-step-ahead evaluation from a
frozen state, not one-step-ahead. If you can convey that with a visual device
rather than a sentence, do.

## What the figure must convey, in priority order

1. `C_u` is built once, before any coalition exists, and is shared by all 32.
2. Three folds feed three different stages (train -> sources, validation ->
   heads, test -> evaluation).
3. The 32-coalition enumeration is exhaustive and exact, not sampled.
4. Output is two-level: one value per source, and a per-user decomposition.
5. The five players are not independent; two pairs overlap by design.

## What is wrong with the current figure

It is four boxes in a row, left to right: `Source models` -> `Fixed candidates`
-> `Coalition game` -> `Shapley values`, with three dashed arrows dropping in
from `Train` / `Validation` / `Test` boxes above, and one arrow out to a
`source credit / LOO / interactions` label below.

Specific problems:

- **It reads as a linear chain.** The coalition stage is a loop over 32
  subsets, and the candidate stage is a fan-in from five sources followed by a
  fan-out to all coalitions. Neither is a link in a chain.
- **The "shared by all coalitions" property is invisible.** It is the design
  decision the whole method rests on, and the figure shows it as one box among
  four.
- **The five sources are one undifferentiated box** reading `cf, ct, pop, rec,
  seq`, so the declared overlaps cannot be seen.
- **The fold arrows are ambiguous.** All three drop in from above with similar
  styling; nothing shows that they attach at *different* stages for different
  purposes, or that the source state stays frozen at train.
- **Nothing conveys exactness.** "32 heads" appears as text; the reader has no
  visual cue that this is the complete lattice rather than a sample.

## Constraints

**Journal (Elsevier, Knowledge-Based Systems):**
- Double-column layout. Assume roughly 84 mm for a single column; if the design
  needs the full width, say so and target about 175 mm as a `figure*`.
- Lettering must stay legible at final printed size. Keep font sizes within a
  narrow band; no 6 pt labels beside 14 pt headings.
- Colour is allowed and appears in colour online, but must remain readable in
  greyscale and to readers with impaired colour vision. If you use colour,
  double-encode with shape, hatch, or line weight so nothing depends on hue
  alone. The safe palette here is Okabe-Ito.
- Caption is a brief title plus a description; the figure must not depend on
  the caption to be intelligible.

**House style:**
- **No em dashes anywhere in the rendered text.** This is CI-enforced.
- Do not use the phrase "pre-registered"; write "frozen" or "declared".
- Source ids are lowercase italic maths: `cf`, `ct`, `pop`, `rec`, `seq`.
- Notation already in use, match it: `C_u` candidate set, `S` a coalition,
  `G` the grand coalition, `v(S)` coalition value, `phi_g` Shapley value,
  `phi_g(u)` per-user value, `w^(S)` fusion head, `N_max` candidate cap,
  `b_u` baseline, `U_eval` evaluated users.

**Technical:**
- TikZ only, using `arrows.meta`, `positioning`, `fit`, `backgrounds`, `calc`,
  `shapes.geometric`. No external images, no shell-escape, no lualatex-only
  features.
- Must compile inside `\begin{figure}` under `cas-dc.cls` with `pdflatex`.
- Self-contained: define every style you use in a `\tikzset` block at the top.

## What not to do

- Do not add stages that do not exist. There is no re-ranking step, no online
  serving loop, no feedback arrow from the output back into the sources.
- Do not draw the coalition stage as a neural network or as a generic "model".
- Do not imply the Shapley values feed back into the recommender. An appendix
  tests attribution-derived fusion weights and reports a **negative** result;
  the main pipeline is diagnostic only.
- Do not label anything "explainable AI" or "interpretable". The paper claims
  system-diagnostic source attribution, not human-facing explanation.
- Do not smooth over the awkward parts. If the frozen-state subtlety or the
  32-way fan-out makes the layout harder, draw it anyway. A figure that looks
  tidier than the method is worse than one that looks busier.

## Deliverable

1. **Two or three distinct design options**, described in prose first, one
   paragraph each, before any code. Say what each makes salient and what each
   sacrifices. I want to choose a layout, not receive one.
2. Once I pick, the **complete TikZ code** for that option, compilable as-is.
3. A **caption**: brief title, then a description that explains every symbol
   and abbreviation appearing in the figure.
4. A short note on **how it degrades in greyscale**, and whether it needs the
   full page width or fits one column.

Start with the design options. Do not write code yet.
