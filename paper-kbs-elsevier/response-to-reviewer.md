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

## Summary

Four of the six weaknesses and two of the four questions are addressed in the
text, all from released artefacts with no new fitting, so every number is
verifiable by the reviewer from the repository. The remaining three (ranking
surrogate, neural player, additional corpus) each require substantial new
compute, and we have marked them as limitations rather than gestured at them.
