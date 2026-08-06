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

## YOU: cannot be automated

1. **First LaTeX compile.** Never done. `brew install --cask mactex-no-gui && cd paper && make`. Since we last spoke I added Background, Discussion, two tables, an algorithm rewrite, and `algorithm`/`algpseudocode`. Send the log either way.
2. **Zenodo DOI, reserved now.** Both reviewers scored reproducibility down partly because the archive is promised "at acceptance"; R2 calls this out explicitly.
3. **ORCIDs + affiliations + co-author email confirmation.**

## Known open, deliberately

- Only MovieLens clears the 0.60 recall gate. Adding a fourth dense timestamped
  corpus is the highest-value experiment we have not run.
- Neural baselines have unmatched tuning budgets; they are contextual
  references and no SOTA claim is made.
- Cross-fitting is absent from the fusion appendix. The bias works *against*
  the negative conclusion, so it is disclosed rather than repaired.
