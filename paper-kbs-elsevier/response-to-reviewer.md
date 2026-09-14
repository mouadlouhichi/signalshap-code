# Response to the reviewer

Point-by-point. Numbers cited here are in `artefacts/reviewer_q1_q3.json`,
regenerable with `python3 scripts/run_reviewer_q1_q3.py`.

## Addressed in this revision

### Q1. Does Shapley still fail when the game matches the intervention?

**This was the sharpest question and it is now answered in the text.** The
objection is fair: the main game holds candidates fixed, whereas retirement
changes retrieval, so Shapley was arguably being scored on the wrong game.

The end-to-end characteristic function was already computed (it is the third
column of the estimand table), so we scored it against the observed retirement
loss. It does not rescue Shapley:

| Game | ML-1M τ | picks | Amazon-VG τ | picks |
|---|---|---|---|---|
| Refitted head (main) | +0.20 | `ct` ✗ | +0.60 | `rec` ✗ |
| Fixed head | +0.20 | `ct` ✗ | +0.80 | `rec` ✗ |
| **End-to-end (matched)** | **+0.40** | `rec` ✗ | **+0.80** | `rec` ✗ |
| Ranking-stage LOO | **+1.00** | `cf` ✓ | **+1.00** | `ct` ✓ |

Matching the game moves agreement in the expected direction and does not close
the gap. **No Shapley variant nominates the correct source on either corpus;
ranking-stage LOO does on both.** This strengthens the claim: the failure is a
property of allocation as an instrument, not an artefact of the fixed-candidate
construct. Added to Section 5.2.

### Q3 / W5. Is LOO's predictive validity confined to a high-recall regime?

Partially answerable without new runs, and the available evidence runs against
the hypothesis. The three corpora span candidate recall 0.748 / 0.589 / 0.450,
and the artefacts record recall after each single-source retirement:

| Corpus | Recall | Largest retrieval drop | τ(LOO) |
|---|---|---|---|
| MovieLens-1M | 0.748 | 11.9% (`seq`) | +1.00 |
| Amazon-VG | 0.589 | 8.2% (`seq`) | +1.00 |
| Gowalla | 0.450 | 6.1% (`ct`) | +1.00 |

Over the observed range, predictive validity does not degrade as recall falls.
We state the limit explicitly: none of these corpora is retrieval-dominant by
construction, so this locates the failure boundary *outside* the observed
range rather than finding it. Added to Threats to validity.

### W2. What ranking-stage attribution does and does not attribute

Agreed, and this deserved to be front-and-centre rather than a caveat. The
construct section now states, before any result, that because the candidate set
is built from all five sources and frozen, (i) a source whose contribution is
mainly retrieval is **systematically understated**, and (ii) φ_g is **not
end-to-end credit**, and a reader wanting end-to-end credit should read the
retirement losses instead.

### W3. v(S) is the performance of a refitted coalition system

Agreed and now named. The methodology section states that because `w^(S)` is
refit for every S, v(S) measures the refitted coalition system, not the
deployed head restricted to S. The fixed-head variant is the alternative
reading, and the two agree on ordering at τ ≥ 0.80.

### W6 / minor. "Sequential" naming

Already addressed in the source table, which describes `seq` as PPMI–SVD
co-occurrence with a **symmetric** matrix, notes that order enters only via
recency weights, and states that the `cf`–`seq` interaction may partly reflect
two collaborative signals. We kept the short label for table width.

### Minor. Kendall τ resolution at n = 5

Agreed that τ is coarse in steps of 0.2. Correct-source identification rates
with Wilson intervals are already reported alongside every τ, and the
retirement table leads with them.

## Not addressed, and why

### Q2 / W4. Ranking-aware surrogate for the coalition head

**Not done. This is the most substantive gap remaining and we do not claim
otherwise.** The objection is legitimate: the head is fit by ridge regression
on a binary target and evaluated by NDCG@10, and a sign flip could in principle
be an artefact of that mismatch.

It cannot be answered from released artefacts. The ridge head is solved from
Gram sufficient statistics (`XᵀX`, `Xᵀy`) accumulated once and reused across
all 32 coalitions; a pairwise or listwise loss needs the full per-user feature
matrix and a per-coalition optimiser, i.e. a complete refit of every coalition
on every corpus. What partially bounds the concern already: the ridge penalty λ
was swept over eight orders of magnitude with both material sign flips intact,
and score perturbation at σ ∈ {0.1, 0.5} leaves them intact. Neither substitutes
for changing the loss family.

### Q4. A Transformer sequential encoder as a player

**Not done.** SASRec and LightGCN appear as reference points, not players.
Promoting one to a player makes six players, 64 coalitions, and changes the
retrieval structure the game assumes. Our own sampling-error measurement is the
reason to be careful here: at a realistic budget, sampled Shapley error exceeds
the effects we report, so a six-player game would need either exact enumeration
at 64 coalitions or a defensible error budget.

### W1. An additional corpus clearing the gate without a sensitivity setting

**Not done.** This requires a new corpus and a full study run.

## Round 3 (updated review)

### #1. Ambiguity between the seed-42 τ and the ten-seed mean

**You were right, and it was ambiguous rather than inconsistent.** The +1.00
is seed 42; Table 7's 0.96 is the ten-seed mean (8/10 seeds at 1.00, two at
0.80 on both ML-1M and Amazon-VG). Nothing in the paragraph said so. The text
now opens with "All figures in the remainder of this paragraph are seed 42,
the single seed for which the three estimands were computed; the ten-seed
results of Table 7 are the primary evidence and are not affected."

The ten-seed version of the estimand table cannot be produced without new
compute: `v_fixed` and `v_e2e` were only ever computed at seed 42, and
`v_e2e` costs 2^n retrieval passes per seed. We label the scope rather than
extrapolate.

### #2. Explicit definition of v_e2e

Added as Eq. (9), alongside the three details you asked about: the baseline
`b_u(S)` is Eq. (6) re-evaluated on `C_u(S)` and therefore moves with the
coalition; the evaluated user population is held fixed at the main game's so
all coalitions average over the same users; a user whose coalition-specific
candidate set is empty contributes 0; and `v_e2e(∅) = 0` by the same
convention. We also note why retirement losses are differenced on raw NDCG
rather than on `v_e2e`.

### #3. Support for "no Shapley variant nominates the right source"

Added as Table 8: τ and top-1 for all three Shapley variants plus LOO, on both
corpora, with the observed answer in the header. Seed 42, labelled as such.
The text now says the identification result is the sharper one and does not
depend on τ's coarseness at n = 5.

### #4, #5. Retrieval-dominant test and ranking surrogate

Still not done, for the reasons given above. Both need refits.

### Minor. "Sequential" naming

Taken. The abstract and introduction now say "short-term co-occurrence"; the
source table already carried the symmetric-matrix caveat.

## Round 4 (required edits)

### Edit 1. Inconsistency in the regime-dependence paragraph

**You were right to flag it, and the fix is not the one you suggested.** We
checked the provenance: every figure in that paragraph is seed 42, including
the retrieval drops, which come from the same per-source retirement artefact as
the tau. So the paragraph was internally consistent but unlabelled, sitting
beside a table of ten-seed means. It is the same ambiguity you caught in
Section 5.2 last round, which we fixed there and missed here.

Writing "0.96--1.00" would have introduced a real error, because it would pair
ten-seed taus with seed-42 recall drops. The paragraph now states that its
figures are seed 42, gives the seed-42 tau of +1.00, and quotes the ten-seed
means 0.96, 0.96 and 1.00 next to them.

### Edit 2. Terminology consistency

Fixed. Two remaining uses described our own source and are now
"co-occurrence". Three uses remain deliberately: two name the topic of cited
papers ("sequential explainable recommendation", a router "selecting among
sequential encoders") and one is the SASRec contrast that defines the caveat.
Changing those would make them wrong. A test now enforces exactly this split.

### Edit 3. Notation for Eq. (9)

Adopted your suggestion. `Z^{(S)}_u(S)` carried the coalition twice; it is now
`Z_{u,S}`, defined as the standardised score matrix whose rows are the items of
`C_u(S)` and whose columns are the sources in `S`. We also added the sentence
that makes the contrast explicit: both the row set and the column set depend on
S here, whereas in Eq. (5) only the columns do.

### Suggestions not taken

Multi-seed `v_e2e`, a retrieval-dominant stress test, and a ranking-aware head
all require refits. See the reasons under Q2/Q4 above; they are unchanged.

## Round 5 (minor revision)

### Edit 1. Terminology: `seq` versus co-occurrence

**Already satisfied for the part you flagged, with one real gap that we
fixed.** We checked every occurrence: `seq` appears in the manuscript only as
the math symbol `$seq$`, which is the usage you explicitly permit. The
orderings you cite (`seq > cf > pop > rec > ct`) are set in maths, as are the
interaction pairs and the table rows. There is no bare word-form `seq` in the
prose, and a test now enforces that.

The genuine inconsistency was elsewhere: the Signal column of Table 2 read
"Co-occurrence" while the abstract and introduction read "short-term
co-occurrence". The column now reads "Short-term co-occurrence".

### Edit 2. Definition of "observed" in Table 6

Added to the caption. "Observed" means the end-to-end retirement loss under the
same seed and protocol: the source is removed from retrieval and fusion alike,
candidates are rebuilt from the survivors, the head is refit, and the loss is
differenced on **raw** NDCG@10 rather than on the baseline-centred `v`. The
last clause matters and is not pedantry: each coalition retrieves its own
candidate set, so `|C_u|` and hence the expected-random baseline move with the
coalition. Differencing `v` would add a baseline term unrelated to the observed
change. The artefact stores both columns and their difference, and a test
asserts the two are genuinely distinct so the caption is distinguishing
something real rather than restating a definition.

### Questions 1-3

Unchanged from the previous rounds: multi-seed `v_e2e`, a ranking-aware head,
and a retrieval-dominant configuration all require refitting, which we cannot
do in the current environment. They remain stated as limitations. Of the three,
we agree that multi-seed `v_e2e` on one corpus is the cheapest and would most
directly retire the "isolated seed-42 effect" worry.

## Round 6 (minor revision)

### Edit 1. Standardise prose on "co-occurrence"

Already satisfied, and we re-verified it mechanically rather than by eye. With
maths stripped, there is no bare word-form `seq` anywhere in the prose: every
occurrence is the symbol `$seq$`, including the orderings and the interaction
pairs, which is the usage you permit. Every prose mention of the source reads
"co-occurrence", with "short-term" as the qualifier where it is first named in
the abstract, the introduction and the source table. Three uses of
"sequential" remain and are deliberate: two name the topic of cited papers and
one is the SASRec contrast that defines the caveat. A test enforces exactly
this split.

### Edit 2. Materiality threshold in absolute and relative terms

Added at the point where the threshold is declared. The clarification is
slightly more than you asked for, because checking it surfaced a real
subtlety: **the two percentages in the paper use different denominators.** The
seed-42 sampling study divides by v(G) = 0.0517, giving 1.93%; the ten-seed
attribution results divide by v(G) = 0.0522, giving 1.91%. Both are correct
against their own basis and the difference is immaterial at two significant
figures, but nothing said which was which. The text now states both, names
which sections use which denominator, and says why the gap exists.

Writing that sentence also caught an arithmetic slip of our own: 0.05225 rounds
to 0.0522, not 0.0523. Corrected, and a test now pins the rounding.

### Questions 1-3

Unchanged. Multi-seed `v_e2e`, a ranking-aware head and a retrieval-dominant
configuration all require refitting. Of the three we agree multi-seed `v_e2e`
on MovieLens-1M is the cheapest and the most directly responsive, and we would
run it first.

## Round 7 (editorial)

### Editorial 1. Gloss `seq` on first use in the results

Done, with one adjustment to your suggestion. The first `$seq$` inside each
results subsection is a **table row label**, where writing "co-occurrence
(seq)" would widen the column and break the alignment. The gloss therefore
sits on the first genuine running-text use, which is the mechanism sentence:
"substitutive with co-occurrence ($seq$) and popularity ($pop$)". We also
prefixed the orderings sentence with the full symbol key, since that is the
other place a reader meets a string of bare symbols.

### Editorial 2. Materiality gate is absolute

Done, in the words you suggested: "The gate itself is \emph{absolute}: a gap
qualifies on the $10^{-3}$ comparison alone, and the percentages below are
reported for interpretability, never as the test."

### Questions 1-3

Unchanged, and unchanged in priority. Multi-seed $v_{e2e}$ on MovieLens-1M
remains the single most valuable outstanding run: three seeds at $2^5$
retrieval passes each on the smallest corpus, and it directly retires the
"seed-42 may be idiosyncratic" reading of Table 6. The ranking-aware head is
the most expensive, because the current head is solved from Gram sufficient
statistics reused across all 32 coalitions, whereas a pairwise or listwise loss
needs a per-coalition optimiser over the full feature matrix.

## Summary

Four of the six weaknesses and two of the four questions are addressed in the
text, all from released artefacts with no new fitting, so every number is
verifiable by the reviewer from the repository. The remaining three (ranking
surrogate, neural player, additional corpus) each require substantial new
compute, and we have marked them as limitations rather than gestured at them.
