# Submission checklist

Status after the two Major-Revision reviews. Everything not marked **YOU** is done.

## Resolved in the manuscript

| Reviewer issue | Resolution |
|---|---|
| R1 #1 / R2 #3: +0.00021 shift between tables | Root-caused. Baseline is **not** invariant: `b_u` cancels only for non-empty `S`, and `w(0)=1/n`, so a baseline change shifts every φ by `-Δ/n`. Verified (seed 42 vs 999: predicted and observed +0.00015926, 8 dp). False invariance claim withdrawn; sensitivity reported; `φ_ct` disclaimed as sign-unstable. 3 regression tests. |
| R1 #2: Algorithm 1 undefined `y_u`, `test_u` | Rewritten with explicit `y^val_u` / `y^te_u`, `I_{|S|}`, tie tolerance, empty coalition scored, per-user loop added. |
| R1 #3: Appendix A unlabelled | `\appendix` + `\section{...}\label{app:fusion}`; CI test asserts a section follows `\appendix`. |
| R2 #1: Eq. (8) is not Shapley–Taylor | Correct — it is Grabisch–Roubens (weights 0.25, 1/12, 1/12, 0.25 vs 0.4, 0.1, 1/15, 0.1). Relabelled + cited; computation retained and its lack of interaction efficiency stated. |
| R2 #6: Table 4 caption false | Only `cf–pop` was pre-declared; `cf–seq` was not and `rec–ct` is positive. Corrected to partial recovery. |
| R2 #9: source-order tie-break | Measured: 120 permutations, 1 identical, worst mean Jaccard **0.9966**. Disclosed with magnitude. |
| R2 #10: analytic games undefined | Table 3 now gives every characteristic function explicitly. |
| Both: hyperparameters (2/10) | New Table `hyper` — all five sources, game, fusion, both neural refs, protocol — plus preprocessing and exact subsampling. |
| R1: missing Background / Discussion / roadmap / future work | All four added. |
| Both: framing | Removed "build-or-retire", "pre-registered", "true loss", "Shapley shares", "misattribution", LOO-independence claim. Exact vs material monotonicity separated. |
| Both: Friedman test | Added. Omnibus **p = 0.014**, but CD = 4.35 and **no pair separable** at 3 blocks. Reported as a limit on the fusion claim. |
| R2: arithmetic | `2500/82134 = 3.04%` (was 3.65%), `11623/82134 = 14.2%` (was 17%). |
| R1: figures colour / radar | All 7 figures monochrome (0 coloured pixels, CI-enforced); radar replaced with point-range. |
| R2: missing references | + Grabisch–Roubens, Faith-Shap, KernelSHAP-IQ, negative interactions. |

## YOU: needs a run (~10–14 h, unattended)

```bash
git pull --rebase origin arena/019fc2ce-signalshap-code
nohup python scripts/run_final_revision.py --budget-gb 24 > /tmp/final.log 2>&1 &
tail -f /tmp/final.log
```

Four blocks, each writing its own artefact so a late crash keeps early results:

- `seeds` — 10-seed attribution on all three corpora. **The single most-repeated
  demand in both reviews**: ten seeds previously went to the *negative* fusion
  appendix while the central claims used three.
- `lambda` — φ across λ ∈ [1e-5, 1e3]. Do the material sign flips survive
  regularisation? If a flip disappears at some λ, that must be reported.
- `friedman` — already run on existing artefacts; re-runs free.
- `retire` — retirement over seeds, so τ = 1.00 gets an interval.

Run a single block with e.g. `--only lambda`.

## Review round 3 (reviewer confirmed correct on both headline items)

| Issue | Status |
|---|---|
| "Uniform semivalue" formula equals Shapley exactly | **Fixed.** Verified numerically: our artefact agreed to 0.0 in every coordinate. Replaced with binomial semivalues q = 0.25 / 0.75; efficiency claim about it withdrawn; regression tests added |
| Sampled baseline still in Algorithm 1, Table 2, Table 7 | **Fixed.** Baseline seed and pi^0 removed; Table 7 regenerated from the deterministic-baseline artefact, where it is identical to Table 6 |
| Abstract/C4 said 0-30%, Table 8 says 0/50/0 | **Fixed** to 0-50%, with Wilson intervals added |
| Section 11 stale (0.01526 / -0.00501 / 0.0203 / 39%) | **Fixed** to 0.01545 / -0.00519 / 0.02064 / 40.2% |
| Source-order-dependent truncation | **Fixed and measured.** Symmetric reciprocal-rank key is now the default; ml_1m ablation shows max abs delta phi = 2.8e-5, same ordering, same material flip. Disclosed that Tables 6-8 predate the switch |
| Promised grand-coalition pool ablation missing | **Added** from the existing E8-a artefact: recall 0.748 to 0.807, v(G) +0.00411, phi_ct flips |
| Grand-pool and lambda "bias theorems" | **Recast** as construct-design choices; Limitations no longer calls them data-independent mathematics |
| Friedman test violating the recall gate | **Deleted** |
| Ten-seed means as primary; sign frequencies | **Added** to Table 6 and Figure 2 (regenerated); all 15 cells are 10/10 sign-stable |
| Complexity omitted full-catalogue scoring | **Fixed**: C_score and O(m n |I|) terms added |
| Bibliography metadata ([11],[13],[15],[28],[31],[37]) | **Fixed** |
| AI-use declaration | **Expanded** to Springer Nature's current wording |

Also closed after the first pass, all on MovieLens-1M (the only corpus whose
raw data fits the sandbox):

| Item | Result |
|---|---|
| Ten-seed CI for `LOO_rank` and for the Shapley-minus-LOO gap | `final_loo_gap_ci.json`. Gap on `cf` = +0.02033 [+0.01995, +0.02071], positive 10/10. **New finding:** `LOO_rank` sign is *not* seed-stable for the near-zero sources (`ct` 7/10, `rec` 5/10), so the two negligible flips are seed noise. Disclosed in the Table 6 caption |
| Recall@10 / MRR@10 robustness | `metric_robustness_ml_1m.json`. All 32 coalitions re-scored under each metric; ordering identical, Kendall tau = 1.00 against NDCG for both |
| Ten-seed interaction intervals | `interaction_seed_ci_ml_1m.json`. Table 7 now reports mean, 95% CI and negative-seed count for all 10 pairs; every pair keeps its sign 10/10. `cf|seq` = -0.0542, `cf|pop` = -0.0254 |

Repeated sparse-corpus subsampling is now **done** and was the reviewer's
"highly desirable" item: Gowalla at 4,652 / 5,910 / 8,865 users. Ordering and
signs hold at all three (tau = 1.00); magnitudes move up to 36% at the smallest.
Reported in Section 11 as a limitation of the Gowalla point estimates.

Still not done, deliberately: Amazon/Gowalla
`LOO_rank` intervals, a full three-corpus regeneration under the symmetric
candidate rule (cost is roughly the original study; ml_1m is done and
reported). These need the machine with all three raw corpora.

## Review round 4

| Issue | Severity | Status |
|---|---|---|
| v(G) = 0.05190 vs 0.05136 | Critical | **Explained.** Difference is 5.4e-4 = the documented arm64/x86-64 residual. Paired sets relabelled as within-platform; `artefacts/PROVENANCE.md` maps every object to artefact/platform/rule/seeds |
| Validation event not in test history | Critical | **Audited and named.** Reviewer read the code correctly. Bias is one-sided and conservative (can only lower NDCG); now documented as a two-step-ahead frozen-state protocol, in Algorithm 1 and Limitations |
| Validation positives outside C_u | High | **Measured.** `validation_recall()` added and wired in; policy (retain) stated with its rationale |
| Figure 2 mixed seed-42 v(G) with 10-seed bars | High | **Fixed and regenerated** |
| Figure 6 segment count 6,035 vs 6,038 | High | **Explained in caption** (3 users have empty candidate sets) |
| Stale "uncertainty not yet done" | High | **Deleted** |
| Paired Delta tau absent | High | **Added** where recoverable: ml_1m +0.76 [+0.70,+0.82], gowalla +0.20. Amazon not reconstructable; runner now stores per-seed tau |
| 1.96 SE at n=10 | Medium | **All seed intervals recomputed with t_9.** No conclusion changed |
| Interaction CIs, Table 5 | High | Recomputed with t_9; CI construction stated |
| `NDCG@10K`, `E[NDCG@1010]` | Low | **Fixed** via `\NDCGat{}`; regression test added |
| Fig 7 internal "F6" label | Low | **Removed** |
| Refs [13] pages, [15] DOI | Low | **Corrected** to 809--818 and 10.1145/3726302.3729971 |
| Intro LOO scoping, "correctly reports", "ablation won it", "approaching the whole catalogue", appendix heading | Medium | **All rewritten** |
| General semivalue equation, rec clustering, initial N_g, PPMI k_s=1, random-state | Medium | **Added to Background / Table 2** |

### 24 GB ten-seed run landed (commits 600fd98, c76e115)

Budget guard held: Gowalla loaded at the correct 8,865 x 82,134. **I checked
the code at that commit and the run used the SYMMETRIC candidate rule**, not
legacy as I first said. That closes the reviewer's Critical #1 for every
inferential result. Corrected in the paper and in PROVENANCE.md.

Two findings corrected the paper rather than confirming it:

- **Gowalla's top source moved `ct` -> `cf`**, separated by 0.00033, and the
  12.6 GB resampling exchanges them again. Now reported as a near-tie; the
  "content signal strong enough to rank second" reading is gone.
- **`phi_ct` on MovieLens is negative on 9/10 seeds, not 10/10.** Table 6 now
  carries a per-source sign column naming both exceptions.

## Protocol sensitivity landed (commit d4a2f3d)

Both mandatory experiments ran on MovieLens-1M and Amazon-VG.

**Temporal state.** Refreshing to a one-step-ahead protocol raises v(G) by 36%
(ml_1m) and 19% (amazon), almost all of it accruing to `seq`, exactly the source
we predicted freezing penalises. Ordering holds on MovieLens (tau = 1.00) but
NOT on Amazon, where the top source moves cf -> seq because the pair is
separated by 0.00015. Now reported as a limitation on absolute values and on
the Amazon ordering.

Note on direction: the measurement agrees with the withdrawn "lower bound"
claim. That does not reinstate it. The claim was unsound as an argument, since
it ignored the simultaneous changes to source scores, C_u and b_u; two
corpora agreeing is evidence, not a bound. I briefly wrote the opposite of the
data in the first draft of this paragraph and corrected it.

**Validation misses.** Real recall at last: 0.799 (ml_1m, 1,216 of 6,035 users
fit on negatives only) and 0.648 (amazon, 2,505 of 7,120). Large minorities, so
the policy mattered. Dropping them moves nothing: max abs delta phi = 3.7e-5
and 2.1e-4, all signs agree. Table 1 now carries validation recall.

## Review round 6

| Issue | Sev | Status |
|---|---|---|
| LOO_e2e defined on baseline-centred v, not raw utility | Critical | **Real bug, fixed.** `utility()` added; retirement now differences raw NDCG. Contamination measured: <= 1.7e-4, tau = 1.00, no conclusion changes |
| v_fixed / v_e2e empty coalition undefined | High | Both set to 0 explicitly |
| Global-time causality unaudited | High | `audit_global_time.py` added; ~50% of pooled training events postdate the median test event. Now described as per-user chronological, not globally causal |
| Gowalla Wilcoxon p = 1.0 | High | **Wrong, fixed.** Correct value is 0.0020, the strongest the test can give. Our guard was backwards |
| Kendall t-intervals exceeding 1.0 | High | Replaced with percentile bootstrap everywhere |
| Abstract/C4/Table 9 stale 0.94-1.00 and 80-100% | High | Updated to 0.96-1.00 and 90-100% |
| "pop constant across candidate row" | High | Corrected: user-invariant, item-varying |
| "only induced ordering matters" | High | Restricted to positive affine invariance |
| Figure 3 stale seed-42 points | High | Regenerated from ten-seed means |
| Table 7 "identical to Table 6" | High | Corrected: same game, seed-42 realisation |
| Amazon rec gap 0.0008 | Med | 0.00063 |
| "not rare" over three corpora | Med | Replaced with a corpus-limited statement |
| "worth removing" for LOO_rank | Med | Now "improves the fixed-candidate ranking game" |
| 32 coalitions vs 16 marginals | Med | Distinguished |
| Duplicated fusion sentence | Low | Removed |
| Table 5 "redundancy" wording | Low | "substitutive interaction under the declared game" |

## Commit 0868d3d: all runs complete

Gowalla protocol sensitivity ran at the correct 8,865 x 82,134 (the budget fix
held), and the retirement rerun refreshed all three `e12_*.json` files with raw
utility.

**Gowalla is the mildest protocol case:** refresh raises v(G) only 3.7% against
36% and 19%, tau = 1.00, top source stable. Its candidate recall slightly
*falls* under refresh (0.4504 -> 0.4488), which contradicts the "recall rises
because a refreshed history retrieves better" generalisation I had written from
two corpora. Corrected.

**Gowalla validation recall is 0.462** and 4,773 of 8,865 users, a majority, fit
on negatives alone. Dropping them still moves attributions only 1.8e-4 with an
identical ordering, so the sparsest corpus with the most affected users is among
the least sensitive. Table 1's n/a is filled.

**Real baseline contamination is 6.7e-4, four times my pilot bound of 1.7e-4.**
Table 7 regenerated from raw utility; every entry moved, no conclusion did.

Two bugs of mine surfaced and are fixed: the script ignored `--budget-gb`
entirely, and it overwrote rather than resumed, deleting the ml_1m and amazon
blocks (recovered from git). Both now pinned by tests.

## LaTeX hardening (no TeX available here)

CTAN is unreachable from this sandbox and there is no TeX distribution, so I
could not compile. Instead I wrote `scripts/check_latex.py`, which lints the
source for the failures that actually cost a round trip, and verified it by
injecting each fault and confirming it fires:

| Check | Probe result |
|---|---|
| undefined control sequence | catches `\FakeMacroXYZ` |
| unbalanced environment | catches a removed `\end{itemize}` |
| tabular row vs column spec | catches an extra and a missing cell |
| tikz style / library missing | catches a dropped `positioning`, `arrows` |
| figure too tall for `topfraction` | measures every figure in mm |
| sn-jnl traps | `\orcid`, `\jyear`, amsthm order, `\graphicspath` |
| restrictive float specifier | catches `[h]`, `[t]` |

Fixing the linter took three attempts, and each failure was instructive:
splitting rows on two backslashes also cuts inside `6\,038`, and filtering out
rows that start with `\midrule` silently exempted the first data row of every
table. A linter that never fails is worse than none, so both probes are now
pytest cases.

**Float placement, the actual eight-round problem.** Loosening
`topfraction` and friends lets LaTeX place a float but does nothing once the
queue backs up: one deferred float delays every later one, which is how six
figures ended up on pages 38-40 of 40. The fix is `\usepackage[section]{placeins}`,
which drains the queue at each section boundary so a float can be late within
its section but cannot leave it. The last `[t]` float, Algorithm 1, is now
`[tbp]`. Measured every figure: the tallest is 46% of the text block, so none
is forced onto a float page.

## What is still open

Audited against the artefacts rather than from memory. Every inferential
experiment now covers all three corpora:

| experiment | ml_1m | amazon | gowalla |
|---|---|---|---|
| 10-seed attribution | yes | yes | yes |
| 10-seed LOO + gap CI | yes | yes | yes |
| 10-seed retirement + paired delta-tau | yes | yes | yes |
| temporal sensitivity | yes | yes | yes |
| validation-miss + validation recall | yes | yes | yes |
| global-time audit | yes | yes | yes |
| raw-utility retirement | yes | yes | yes |

Every headline number in the manuscript traces to an artefact (verified
programmatically). Abstract 249 words, zero em dashes, no TODOs.

## Review round 7: Minor Revision

All five mandatory items were editorial and needed no new experiments.

| Item | Status |
|---|---|
| Roadmap/investment contradiction (p39) | **Fixed.** Shapley now stated as descriptive allocation of current quality, explicitly not a prescription for future investment. Prose and Table 9 agree |
| Revision/reviewer-history prose | **Removed.** 23 "earlier version" and 13 "reviewer" mentions to zero in rendered text. Self-corrections kept where scientific, rephrased as statements about the method |
| Overgeneralised metric heading | **Renamed** to "Metric sensitivity on MovieLens-1M" |
| shifted-PPMI -> PPMI-SVD | **Fixed.** Verified against the code: no shift is subtracted, so k_s = 1 |
| "incomparable across the lattice" | **Replaced.** Coalition-specific candidates now described as a valid game measuring a different retrieval+ranking estimand |

Two CI guards added so the prose cannot regress, and a test that the PPMI
naming stays consistent with the code.

### Globally time-blocked replication (reviewer's #1 experiment)

`scripts/run_global_timeblock.py` ships. It splits at global timestamp
quantiles so no training event postdates any evaluated event, and it is
referenced in the temporal-validity discussion.

I could not run it here: the sandbox has no corpora and no network to fetch
them. I verified the splitter on a synthetic corpus with realistic calendar
overlap: 71.5% user retention and **zero** training events after any test
event, folds strictly time ordered, one held-out event per user. Pinned by a
test.

Note it fails loudly on our synthetic fixture, whose users occupy disjoint time
windows so a global cutoff retains nobody. That is a property of the fixture,
not the method; real corpora overlap.

    python scripts/run_global_timeblock.py --corpora ml_1m --budget-gb 24

### One blocker

1. **The compile.** Everything statically checkable passes. Only a real
   pdfLaTeX run can confirm pagination, package interactions and overfull
   boxes. Upload `paper/signalshap-overleaf.zip`, compiler pdfLaTeX, send the
   log plus which pages Figures 1-7 land on.

### One optional run

2. **Regenerate the legacy-key diagnostics.** Everything inferential is already
   on the symmetric key. Still legacy: Table 1's recall and monotonicity
   columns, duplicate injection, segment profiles, the lambda and candidate-cap
   sweeps, the grand-pool ablation, and the estimand comparison. All are
   structural or directional checks, and on MovieLens the two keys agree to
   2.8e-5 with recall identical to three decimals, so Table 1 is unaffected at
   the precision it reports. Listed in Limitations either way.

   One corpus per invocation, because a combined run would apply the smallest
   user cap to all three:

       python scripts/run_study.py --datasets ml_1m --budget-gb 24
       python scripts/run_study.py --datasets amazon_video_games --budget-gb 24
       python scripts/run_study.py --datasets gowalla_ts --budget-gb 24

   Expect the monotonicity integers to move by a count or two; recall and every
   ordering should not.

### Known limitations, disclosed in the paper in our own words

3. Only MovieLens clears the 0.60 recall gate. A fourth dense timestamped
   corpus is the highest-value experiment we have not run.
4. Interaction indices, Recall@10/MRR@10 robustness and the candidate-rule
   ablation are MovieLens-only. Semivalues cover two corpora.
5. Gowalla's full-catalogue recall sweep between 23,246 and 82,134 items is
   unmeasured, so where the 0.60 crossing lies is unknown.
6. The split is per-user chronological, not globally time-blocked; the exposure
   is measured (44.2 / 27.1 / 19.4% mean future-train fraction) and reported.
7. Neural baselines have unmatched tuning budgets and are contextual references
   only; no SOTA claim is made.
8. No immutable DOI archive (author declined Zenodo; a git tag is cited
   instead). Both reviewers scored reproducibility down partly for this.

Items 3-8 are limitations, not defects: each is stated in the manuscript with
its magnitude. None is a barrier to submission.

## YOU: cannot be automated

1. **First LaTeX compile.** Never done. `brew install --cask mactex-no-gui && cd paper && make`. Since we last spoke I added Background, Discussion, two tables, an algorithm rewrite, and `algorithm`/`algpseudocode`. Send the log either way.
2. **Zenodo DOI: dropped, by decision.** Author declined; submission goes to
   Discover AI only. All DOI promises are removed from the manuscript and the
   cover letter, replaced by a citation of the exact commit that produced the
   numbers. `.zenodo.json`, `CITATION.cff` and `make archive` are kept: they
   cost nothing, and if a reviewer or the editor asks for an immutable archive
   the deposit is then a ten-minute job rather than a rebuild.

   Residual risk, recorded rather than argued: both reviewers scored
   reproducibility 7/10 partly on this, and the last review lists "freeze one
   immutable release" among its mandatory items. A public GitHub repository is
   mutable and can be deleted, which is the substance of the objection. The
   commit hash mitigates but does not remove it. If reproducibility is queried
   in the next round, this is the first thing to revisit.

3. **ORCIDs + affiliations + co-author email confirmation.** Only Louhichi has
   an ORCID in the manuscript and in `.zenodo.json`; add Nesmaoui's and
   Lazaar's if they have them.

## Known open, deliberately

- Only MovieLens clears the 0.60 recall gate. Adding a fourth dense timestamped
  corpus is the highest-value experiment we have not run.
- Neural baselines have unmatched tuning budgets; they are contextual
  references and no SOTA claim is made.
- Cross-fitting is absent from the fusion appendix. The bias works *against*
  the negative conclusion, so it is disclosed rather than repaired.
