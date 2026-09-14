## Review round 8 (Major Revision, 12 items)

Seven closed; the rest need runs on your machine.

| # | Item | Status |
|---|---|---|
| 4 | Paired LOO-Shapley gap intervals | **DONE.** All 15 cells now carry a t_9 run interval and a sign count. 14/15 unanimous; the exception is `rec` on ml_1m at 9/10, worth 0.4% of v(G). Both material flips exclude zero |
| 5 | Interactions on Amazon and Gowalla | **DONE, and the mechanism replicates.** Both were already computed but never reported. On Gowalla the most negative pair is `ct|pop` and `pop` is the flip source, mirroring `cf` on ml_1m. Amazon, the negative case, has a strong `cf|seq` interaction but no flip, so interaction alone does not predict one |
| 6 | Complete three-game RQ3 table | **DONE.** New Table with all three attribution vectors for ml_1m and Amazon. Gowalla omitted and said so: end-to-end needs 32 retrieval passes over 82,134 items |
| 9 | Amazon above the recall gate | **DONE from the existing sweep.** At N_max=1200 Amazon reaches recall 0.750, matching MovieLens' 0.748, with tau=0.80 and the same top two sources. Kept N=600 as the frozen configuration, reported the gate-clearing point as robustness |
| 1 | Artifact does not reproduce | **Substantially closed.** `make_manifest.py` writes SHA-256 for all 52 artefacts plus commit, environment and BLAS backend. The "does not reproduce" sentence is replaced by a precise statement of what does and does not transfer |
| 2 | Repeat-item diagnostics | **DONE, and it changed a claim.** New Table `tab:repeats`. ML-1M is exactly clean (0/0/0%). Amazon 6.04% / 2.78% / 5.27%. **Gowalla 14.21% / 49.90% / 52.61%.** Half of Gowalla's evaluated users have a test venue already in training, so `mask_seen` makes it unretrievable and v_u(S)=0 for all 32 coalitions. Those users dilute the whole game by an exact constant: v(S) = rho * v_live(S), rho=0.501, verified to 1.4e-17 over all coalitions and confirmed by 6 new tests |

## Round 8 runs completed on the M4 (commit 4936244)

| # | Item | Result |
|---|---|---|
| 3 | Blocked retirement | **REPLICATES.** tau_LOO 0.80 vs tau_Shapley 0.60 (advantage +0.20, same direction as the main result). LOO names the truly cheapest source (`pop`); Shapley names `rec` and is wrong. The allocation-versus-removal claim survives a globally causal split even though the per-source attributions do not |
| 7 | Ten-seed refreshed history | v(G) +31.7% [+30.2%,+33.1%], 10/10 seeds positive, so the protocol effect far exceeds seed noise. Ordering preserved on every seed (tau=1.00, 10/10). Gains concentrate in `seq` (+0.01393) and `cf` (+0.00199), both sign-stable; `ct` and `rec` move <1e-4 with no stable sign |
| 10 | Neutral candidate pools | All three corpora. tau vs union 0.80 almost everywhere (1.00 for Gowalla popularity). Both material flips (`cf` on ML-1M, `pop` on Gowalla) survive pools no source helped build. Top source changes only on Amazon oracle (cf->seq) and Gowalla random (cf->ct, the known near-tie). **Oracle recall came out at exactly rho: 1.000 / 0.972 / 0.501, an independent confirmation of Eq. (14)** |
| 6 | Legacy diagnostics | ML-1M and Amazon regenerated under the symmetric rule. **Gowalla OOM-killed after 116 min** (five dense 8,865 x 82,134 matrices at 24 GB); its diagnostics stay legacy and Table `tab:provenance` now says so |

### What the regeneration changed in the paper

- **Fusion difference flipped sign**: the attribution-derived head is now 0.00009 *below* the global head (was +0.00003), Holm p=0.23. Appendix A's negative result is *strengthened*, and the sign instability across candidate rules is now stated explicitly
- Table 1 raw monotonicity: ML-1M 23 -> 26, Amazon 12 -> 14. **Material counts unchanged (7/4/6)**, which is exactly the reproducibility argument the paper already makes; the prose now cites three runs instead of two
- Amazon test recall 0.588 -> 0.589
- Segment heterogeneity: ML-1M 8/30 -> 7/30, Amazon 5/30 -> 7/30. Gowalla's 4/30 flagged as legacy

Nothing above weakens a claim. The one sign flip makes a negative result more negative.

### Figures regenerated (this pass)

All seven figures in `paper/figures/` were **eleven days stale**: they predated
the symmetric-rule regeneration. Figure 6 plotted the legacy fusion comparison
while the prose quoted the new numbers, one of which had changed sign, so the
figure contradicted the text beside it. Regenerated, and the publish step is
now part of `make_assets.py` with a test that catches staleness.

Also fixed: five of seven figures and all seven tables ordered corpora
alphabetically instead of dense-to-sparse, so a regeneration silently moved
MovieLens to the right-hand panel.

### Still open

- Gowalla legacy diagnostics need a machine with more headroom, or a chunked scorer. Not blocking: Gowalla's primary attribution and retirement numbers come from the ten-seed artefact, which is already symmetric on all three corpora
- No immutable DOI (Zenodo declined)

## Compiled PDF audited (signalshap-code_fix.zip)

Unzipped and read the real compile output, not just the source.

**The compile is clean.** 52 pages, **zero errors**, **zero overfull boxes**,
zero undefined references, zero BibTeX warnings, no duplicate labels, no `[?]`
citations. The clipped Table 2 the new review flagged is already fixed by your
`\tabcolsep` and `\small` edits.

**Float placement confirmed in the PDF itself:** Fig 1 p4, Fig 2 p26, Fig 3
p31, Fig 4 p33, Fig 5 p36, Fig 6 p46, Fig 7 p47; tables spread p9 to p41.
Nothing stranded at the end. `placeins` holds.

**The zip predates HEAD**, so two things it still contains are already fixed
here: a 293-word abstract (43 over the limit) and three em dashes.

**Findings from the new review in `paper-reviews/`, verified individually:**

| # | Finding | Verdict |
|---|---|---|
| 6 | Table 6 labels `rec` a sign flip when both means are positive | **Was real; you already fixed it.** I re-verified all four dagger markers against the artefact: all correct |
| 11 | Table 2 clipped, ~302pt overfull | **Fixed** in your commit; log shows 0 overfull |
| 12 | `and others` author, README entry count | **Fixed** in your commit |
| 12 | Brand capitalisation in bibliography | **Partly open, now fixed.** LightGCN/RankSHAP/ShaRP/KernelSHAP-IQ were already protected; `shapley` still rendered lowercase in 5 entries. Brace-protected 9 title occurrences |
| 10 | Cover letter describes a four-corpus study | **Fixed** in your commit |

Also adopted your improved `hou2026bridging` entry: the published ACL version
with full metadata, replacing my arXiv preprint.

Findings 1-5 and 7-9 are definitional and statistical scoping points that need
judgement rather than a mechanical fix; they are listed below as open.

## THE COMPILE RAN (commit a38b393)

Ten rounds of asking, and the `.synctex` in your commit is the proof. Extracted
from it directly:

- **50 pages, pdfLaTeX, no missing figures.** Fig1 is absent from the file list
  because it renders as live TikZ (`\tikzfiguretrue`), which is correct.
- **Float placement is FIXED.** Previous compile: all six data figures stranded
  on pages 38-40 of 40. Now:

| float | page | first ref | drift |
|---|---|---|---|
| fig:workflow | 4 | 2 | +2 |
| fig:shares | 23 | 23 | 0 |
| fig:scatter | 30 | 29 | +1 |
| fig:redundancy | 32 | 32 | 0 |
| fig:robustness | 35 | 30 | +5 |
| fig:segments | 43 | 43 | 0 |
| fig:fusion | 44 | 44 | 0 |

  `placeins` did its job: nothing migrates past its section. The two tables
  with large drift (`tab:preconditions` +11, `tab:retire-seeds` +34) are
  forward-referenced from the Introduction, which is normal.

## Regressions the restructure introduced, now fixed

Your `fix paper` commit was mostly good but reverted or broke seven things the
checkers caught:

| Issue | Fix |
|---|---|
| Two em dashes reintroduced | Replaced with commas (house style) |
| `fig:segments`, `tab:notation`, `tab:provenance` never cited | Citations added at the natural points |
| `fig:robustness` float placed after `fig:redundancy` but cited before | Float moved to match citation order |
| Abstract 251 words | Trimmed to 250 |
| `.fls`, `.fdb_latexmk`, `.synctex` committed (75k lines) | Gitignored |
| Two tests stale after renames (`eq:taylor`, `thmstyleone`) | Tests updated; the paper was right |
| `run_protocol_sensitivity` citation dropped | Restored |

My own linter also needed fixing: it did not know `booktabs`, so every
`\bottomrule` row counted as one cell against the column spec. Corrected and
re-verified against an injected fault.

## Globally blocked replication: the result is not flattering

`run_global_timeblock.py` ran on MovieLens-1M. It does what it was built to do,
zero training events postdate any evaluated event, and the answer weakens the
paper's generality rather than confirming it.

| | main (per-user, 10 seeds) | globally blocked (seed 42) |
|---|---|---|
| users | 6,038 | **526 (8.7%)** |
| candidate recall | 0.748 | **0.464, below our own 0.60 gate** |
| v(G) | 0.0522 | 0.0095 |
| ordering | seq > cf > pop > rec > ct | cf > seq > pop > ct > rec |
| material flip | cf | **pop and seq** |

Agreement with the main run: Shapley ordering tau = 0.60, LOO ordering
tau = -0.40.

**What I wrote into the paper.** The qualitative claim survives: a material
sign disagreement between allocation and ranking-stage removal is still present
when every trace of cross-user future information is removed. The per-source
attributions do NOT replicate, and the paper now says so in both the protocol
section and Limitations. Two reasons stop us reading more into it: the blocked
corpus fails our own recall gate, so by our stated policy it supports relative
contrasts only, and at 8.7% coverage it is a different population rather than a
cleaner measurement of the same one.

This is now the sharpest limitation in the manuscript. A corpus dense enough to
survive a global cutoff while clearing the recall gate would settle it.

## Restructure: round-7 fixes were reverted, and two declarations were lost

The restructure commits reset the manuscript to its pre-round-7 text. I
re-applied all 38 edits and found two further regressions the checkers caught:

- **Code availability and Use of AI tools declarations had been deleted.** The
  AI declaration is a Springer requirement. Both restored.
- **Seven subsections became subsubsections**, nesting four levels deep, which
  breaks Discover AI's three-level limit. Promoted back.

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
