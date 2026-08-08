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

**Not done: the full three-corpus regeneration under the symmetric candidate
rule.** This is the reviewer's Critical #1 and it needs your machine. Everything
else is closed. Run:

    python scripts/run_final_revision.py --only seeds retire --budget-gb 24

That now also emits per-seed LOO, gap, tau and the paired bootstrap on all three
corpora, closing the remaining High items in one pass. Send me the artefacts and
I will regenerate Tables 6-8, Figures 2-3 and the prose.

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
