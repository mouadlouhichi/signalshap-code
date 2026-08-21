# What still needs a run

Nothing is blocking submission. Everything below is optional strengthening,
ordered by value per hour. All commands assume the M4 and `--budget-gb 24`.

## Tier 1: cheap, closes a named reviewer item

### 1. Semivalues on Gowalla (closes H14 / #4 completely)

Round-9 review asked why Banzhaf and the binomial semivalues are MovieLens
only. We just found the Amazon artefact and it *disagrees* with Shapley
(tau = 0.60, different leading source), which is now reported. Gowalla is the
only corpus still missing. It needs the 32 coalition values, which the
ten-seed artefact does not store, so it is a real run.

```
# NOTE: this script has no --budget-gb. It does NOT size the corpus, so a bare
# Gowalla call loads the full 52,985 x 121,866 matrix and will be OOM-killed.
# Pass the user cap explicitly, matching the reported 8,865-user shape, and
# skip the 2^n retrieval experiments, which are not needed for semivalues.
PYTHONPATH=src python scripts/run_revision_experiments.py \
    --dataset gowalla_ts --max-users 8865 --skip-e2e
```

Verify afterwards that the corpus shape is the reported one:

```
python -c "import json;d=json.load(open('artefacts/e10_values_gowalla_ts.json'));print(d.get('dataset'))"
```

Cost: one 32-coalition game on 8,865 x 82,134. Tens of minutes, not hours.
Value: turns "we did not compute it on Gowalla" into a three-corpus statement,
and the Amazon disagreement makes the third data point genuinely informative.

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

Run item 1 if you want one more reviewer item fully closed for well under an
hour. Everything else can wait for an actual revision request, since the
current text scopes each of them honestly as a limitation.
