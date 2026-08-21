# What still needs a run

Nothing is blocking submission. Everything below is optional strengthening,
ordered by value per hour. All commands assume the M4 and `--budget-gb 24`.

## Tier 1: DONE

### 1. Semivalues on Gowalla (H14 / #4) -- completed

Ran, folded into the manuscript, and the result is more interesting than
either outcome anticipated. Banzhaf and both binomial semivalues agree with
Shapley at tau = 0.80, and three of four values put `cf` first. The `q=0.25`
semivalue, which up-weights small coalitions, promotes `ct` instead. That is a
second and independent route to a caveat the paper already carries: Shapley
separates `cf` from `ct` on Gowalla by only 0.00037, and reweighting the
coalition sizes inverts a margin that small. Under Banzhaf and `q=0.75` the
transposition instead falls between `pop` and `rec`, separated by 0.00017.

Net effect on the claim: the ordering is robust to the choice of semivalue on
MovieLens-1M, robust on Gowalla except for a leading pair already treated as a
near-tie, and NOT robust on Amazon-VG, where the leading source itself changes.
The manuscript now states the conjunction rather than the best case.

### 2. Oracle tuned head (closes #5 fully)

Table 11 already has fixed head, refitted head and end-to-end. The reviewer
asked for a fourth column: a head tuned per coalition rather than fitted at a
frozen lambda. This would separate "source contribution" from "optimisation
flexibility" completely instead of bracketing it.

Not implemented. Needs a small addition to `compare_estimands`, then a rerun
on ML-1M and Amazon. Perhaps an hour of work plus two short runs.

## Tier 2: moderate, strengthens a limitation into a result

### 3. Repeat-aware Gowalla protocol (closes H8, the strongest criticism)

The conclusion now says a repeat-aware protocol, not a bigger candidate cap,
is what Gowalla needs. Actually running it would convert that from a stated
limitation into a measured sensitivity: admit revisits as valid targets, or
mask only the immediately preceding event, and report the attribution under
both policies.

Not implemented. The change is in `mask_seen` and the split, and it touches
the evaluation protocol, so it needs care rather than just compute.

### 4. Pairing-preserving bootstrap for the retirement contrast (H9)

Seed intervals measure training variability, not user-sampling variability.
The paper says so explicitly and narrows the claim, which is defensible. A
bootstrap resampling users with the seed pairing preserved (B = 1000) would
let the claim be population-level instead.

Cost: 1000 resamples x 3 corpora over cached per-user values. Cheap if the
per-user retirement losses were cached; they are not, so it needs a rerun of
the retirement simulation with per-user output.

## Tier 3: expensive, probably not worth it before a decision

### 5. Gowalla legacy-diagnostic regeneration

Still the only symmetric-rule gap. `run_study.py --datasets gowalla_ts` was
OOM-killed after 116 minutes: five dense 8,865 x 82,134 float32 matrices are
14.6 GB before the game allocates. Needs a chunked scorer or a bigger machine.
Table 10 already discloses this, and Gowalla's primary numbers come from the
ten-seed artefact, which is symmetric on all three corpora.

### 6. Neural players (#3, #9)

Making LightGCN or SASRec a *player* rather than a reference baseline changes
the retrieval structure the game assumes. This is a follow-up paper, not a
revision item.

## Explicitly not worth running

- **KernelSHAP as a comparator (#4).** It approximates the same game we
  enumerate exactly. Running it would measure our sampling error, not a rival
  method. Say this rather than run it.
- **Friedman across corpora.** Would pool absolute NDCG from corpora that fail
  the recall gate, over three blocks. The paper already explains why it is
  omitted.
- **10 and 20 players (#15).** 2^20 coalitions is not enumerable; that is the
  approximation boundary the paper names as future work.

## Recommendation

Tier 1 is done. Nothing else is worth running before a decision: every
remaining item is scoped in the manuscript as a limitation, and the two that
would most strengthen the paper (a repeat-aware Gowalla protocol and neural
players) are follow-up work rather than revisions.
