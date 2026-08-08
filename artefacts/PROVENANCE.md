# Artefact provenance

Which artefact, machine and candidate rule produced each object in the paper.
Added because a reviewer found three different `v(G)` values for what is
nominally the same MovieLens seed-42 game and could not tell which was final.

## Platforms

| id | machine | note |
|----|---------|------|
| `M4` | Apple M4, 48 GB, arm64 | produced every reported table and figure |
| `x86` | sandbox, x86-64 | paired within-platform comparisons only |

The two disagree on candidate *contents* for 2 of 6,035 MovieLens users, via
BLAS accumulation order in ALS and truncated SVD. This moves `v(G)` by about
5.4e-4 and raw monotonicity between 16 and 23. Material counts and every
reported sign are unaffected. See spec provenance entry 36.

**Consequence: never compare a number across platforms.** `0.05190` (x86) and
`0.05136` (M4) are the same game.

## Candidate rule

| id | rule | status |
|----|------|--------|
| `sym` | truncate by descending sum of reciprocal per-source ranks | **method of record**, code default |
| `legacy` | best per-source rank, ties by position in `SOURCES` | superseded, order dependent |

## Map

| Paper object | Artefact | Platform | Rule | Seeds |
|---|---|---|---|---|
| Table 1 preconditions | `results_*.json` `e0a_candidates` | M4 | legacy | 42 |
| Table 3 duplicates | `e9_recovery_ml_1m.json` | M4 | legacy | 42 |
| Table 4 analytic games | `e13_synthetic_ground_truth.json` | any | n/a | n/a |
| Table 5 interactions | `interaction_seed_ci_ml_1m.json` | x86 | legacy | 42-51 |
| Table 6 LOO vs Shapley | `results_*.json` + `final_seed_ci.json` | M4 | legacy | 42 / 42-51 |
| Table 7 retirement | `e12_retirement_ml_1m.json` | M4 | legacy | 42 |
| Table 8 retirement seeds | `final_retirement_seeds.json` | M4 | legacy | 42-51 |
| Figure 2 | `final_seed_ci.json` | M4 | legacy | 42-51 |
| Figure 3 | `results_*.json` | M4 | legacy | 42 |
| Semivalues (Sec 10.2) | `e10_values_ml_1m.json` | x86 | legacy | 42 |
| Candidate-rule ablation (Sec 4.1) | `candidate_rule_ablation_ml_1m.json` | x86 | both | 42 |
| Grand-pool ablation (Sec 4.1) | `results_ml_1m.json` `e8_appendix_b` | M4 | legacy | 42 |
| Gowalla subsampling (Sec 11) | `gowalla_subsample_sensitivity.json` | M4 | legacy | 42-51 |
| Metric robustness (Sec 11) | `metric_robustness_ml_1m.json` | x86 | legacy | 42 |
| LOO/gap intervals (Sec 11) | `final_loo_gap_ci.json` | x86 | legacy | 42-51 |

## Known gap, disclosed in Section 4.1

Every reported result uses the `legacy` rule. The `sym` rule is the method of
record and the code default, and the two were compared head to head on
MovieLens (max abs delta phi = 2.8e-5, tau = 1.00, same material flip). A full
three-corpus ten-seed regeneration under `sym` has not been run; it costs
roughly the wall-clock of the original study, most of it Gowalla.

To close it:

    python scripts/run_final_revision.py --only seeds retire --budget-gb 24

Gowalla needs about 24 GB: the budget derives the user cap, and a smaller one
silently substitutes a different corpus. `check_paper_shape()` now refuses to
overwrite the reported artefact in that case.
