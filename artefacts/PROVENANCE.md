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
| Table 6 LOO vs Shapley | `final_seed_ci.json` | M4 | **sym** | 42-51 (all columns) |
| Table 7 retirement | `e12_retirement_ml_1m.json` | M4 | legacy | 42 |
| Table 8 retirement seeds | `final_retirement_seeds.json` | M4 | **sym** | 42-51 |
| Paired delta tau (Sec 13) | `final_retirement_seeds.json` `paired_delta_tau` | M4 | **sym** | 42-51 |
| Figure 2 | `final_seed_ci.json` | M4 | **sym** | 42-51 |
| LOO/gap intervals, all corpora | `final_seed_ci.json` `loo_ci`/`gap_ci` | M4 | **sym** | 42-51 |
| Figure 3 | `results_*.json` | M4 | legacy | 42 |
| Semivalues (Sec 10.2) | `e10_values_ml_1m.json` | x86 | legacy | 42 |
| Candidate-rule ablation (Sec 4.1) | `candidate_rule_ablation_ml_1m.json` | x86 | both | 42 |
| Grand-pool ablation (Sec 4.1) | `results_ml_1m.json` `e8_appendix_b` | M4 | legacy | 42 |
| Gowalla subsampling (Sec 11) | `gowalla_subsample_sensitivity.json` | M4 | sym vs sym | 42-51 |
| Metric robustness (Sec 11) | `metric_robustness_ml_1m.json` | x86 | legacy | 42 |
| Temporal + validation-miss sensitivity (Sec 5) | `protocol_sensitivity.json` | M4 | sym | 42 (all three corpora) |
| Global-time audit (Sec 7) | `global_time_audit.json` | M4 | n/a | n/a |
| Globally blocked replication (Sec 7) | `global_timeblock.json` | M4 | sym | 42, ml_1m only |
| Table 7 single-seed retirement | `e12_retirement_ml_1m.json` | M4 | **sym** | 42, raw utility |
| Validation recall, Table 1 | `protocol_sensitivity.json` | M4 | sym | 42 |
| LOO/gap intervals, ml_1m only (superseded) | `final_loo_gap_ci.json` | x86 | legacy | 42-51 |

## Status after commit 600fd98

The 24 GB ten-seed run closed the interval gaps: `final_seed_ci.json` now
carries per-seed LOO and gap plus t_9 intervals and sign counts on all three
corpora, and `final_retirement_seeds.json` carries per-seed tau and the paired
bootstrap. Table 6 is now ten-seed throughout rather than mixing a seed-42
point estimate with a ten-seed interval.

Two findings from that run changed the paper rather than confirming it:

- Gowalla's top source moved from `ct` to `cf`, and the two are separated by
  only 0.00033. Under the 12.6 GB resampling they exchange again, so the paper
  now reports a near-tie and makes no stable-top-source claim on that corpus.
- `phi_ct` on MovieLens is negative on 9 of 10 seeds, not 10. The earlier
  caption asserted all fifteen cells were 10/10. Table 6 now carries a
  per-source sign column.

## Candidate-rule status

**Closed for the inferential results.** Commit 600fd98 regenerated the ten-seed
attribution and retirement study on all three corpora under `sym`, which is the
method of record. Verified rather than assumed: `sym` was already the default
in `builder.py` and `pipeline.py` at that commit, and ml_1m seed 42 differs
from the previous legacy-key run by 2.7e-4, the scale of the rule change.

**Still `legacy`, and listed in the paper's Limitations:**

| Object | Source | Why it is acceptable |
|---|---|---|
| Table 1 recall + monotonicity | `results_*.json` | recall identical to 3 dp under both keys (0.748) |
| Table 3 duplicate injection | `e9_recovery_ml_1m.json` | tests exact symmetry and exact-zero LOO, not values |
| Estimand comparison (Sec 13) | `e11_estimands_*.json` | reports rank agreement between three games |
| Segment profiles (Fig 5) | `results_*.json` `e3_segments` | descriptive, no inferential claim |
| lambda + candidate-cap sweeps | `results_*.json` `e5_robustness` | reports direction of change, not level |
| Grand-pool ablation | `results_ml_1m.json` `e8_appendix_b` | one-seed design argument |
| Semivalues, interactions, metric robustness | x86 single-seed | each labelled in the text |

To regenerate all of these under the symmetric key:

    python scripts/run_study.py --datasets ml_1m --budget-gb 24
    python scripts/run_study.py --datasets amazon_video_games --budget-gb 24
    python scripts/run_study.py --datasets gowalla_ts --budget-gb 24

That rewrites `results_*.json` and every e-block it contains. Expect Table 1's
monotonicity integers to move by a count or two; the recall column and every
ordering should not move.

Artefacts now stamp `candidate_rule` themselves, so this table cannot silently
drift again.
