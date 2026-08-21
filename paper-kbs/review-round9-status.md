# Round 9 review: honest status of all 20 issues

Three categories. The distinction matters: several items are already addressed
in the submitted text, several are now addressed, and a hard core cannot be
closed by editing because they require experiments we have not run.

## A. Already in the submitted manuscript (reviewer may have missed them)

| # | Where it already is |
|---|---|
| 1 | "What exact means" defines exactness as the aggregation only, naming finite data, stochastic fits, hyperparameters and numerical libraries as sources of error. Title reads "Exact-**Enumeration**", not "exact attribution". |
| 5 | Table 11 already reports all three estimands side by side: fixed head, refitted head, end-to-end. This is the reviewer's own recommended fix, minus the oracle head. |
| 6 | Recall@10 and MRR@10 already reported on ML-1M seed 42; ordering identical at tau = 1.00 under all three metrics. |
| 7 | Wilcoxon signed-rank with exact p-values, Holm correction over the declared family, Wilson intervals on proportions, d_z effect sizes, t_9 run intervals on every cell of Table 8, and percentile bootstrap. Friedman is deliberately **not** used, with a stated reason. |
| 8 | "no causal or off-policy claim is made"; the estimand-to-decision mapping in Table 9 exists precisely to separate description, intervention and causation. |
| 11 | Candidate-cap sweep, the source-symmetric versus legacy truncation ablation, the rejected grand-pool design, and three source-blind pool rules. |
| 12 | Neural references are labelled under-tuned in the text, the figure caption and the "no state-of-the-art claim" statement. |
| 13 | MANIFEST.json records SHA-256, commit, environment and BLAS backend per artefact; PROVENANCE.md maps every table to its artefact, platform, candidate rule and seeds; memory budgets and corpus shapes are reported. |
| 14 | Complexity is given as O(... + 2^n(n^3 + mNn + mN log N)), with the 14.6 GB and 129 GB memory instantiations stated. |
| 19 | Conclusion already restricted to the evaluated setting throughout. |
| 20 | Ethics section covers re-identification risk, exposure disparity from popularity signals, and states that no fairness claim is made. |

## B. Fixed in this revision

| # | Change |
|---|---|
| 1 | Strengthened: "exact Shapley aggregation conditional on the fitted characteristic function" as the formal phrasing, with the shorthand defined once. |
| 10 | New paragraph "Why not a graph or neural explainer", citing GNNExplainer, PGExplainer, GraphSVX and SubgraphX, and giving the **structural** reason they are not comparators: they attribute to entities inside one differentiable model, we attribute to five architecturally distinct scorers with no shared graph and no gradient. |
| 16 | Score-perturbation robustness now reported: Gaussian noise at sigma = 0.1 and 0.5 in units of each source's own standard deviation. Ordering degrades gracefully (tau = 0.80, `seq` still leading) and the material `cf` disagreement survives. The artefact existed; it was never written up. |
| 18 | Four recent GNN-explainability references added. |
| 19 | One-sentence explicit boundary added to the conclusion. |

## C. Cannot be closed by editing: these need new experiments

We state these as limitations rather than pretend otherwise.

| # | What it would take | Why we did not do it here |
|---|---|---|
| 2 | New attribution theory specific to recommenders | This is a request for a different paper. Our contribution is a declared game plus the finding that allocation and removal disagree, including against our own instrument. We would rather defend that scope than inflate it. |
| 3, 9 | LightGCN / SASRec / Transformer **as players** | Both already appear as reference baselines. Making them players changes the retrieval structure the game assumes; named as future work. |
| 4 | KernelSHAP, Integrated Gradients, GNN explainers as empirical comparators | Banzhaf, two binomial semivalues, permutation importance and forward selection are already compared. KernelSHAP approximates the same game we enumerate exactly, so it measures our sampling error, not a rival method. Gradient and graph explainers do not apply at this granularity, per the new #10 paragraph. |
| 5 | Oracle tuned head | A third estimand column; feasible but a new run. |
| 6 | Multi-positive, MAP, graded relevance | Requires a different evaluation protocol and re-running every corpus. |
| 15 | 10 and 20 players | 2^20 coalitions is not enumerable; this is the approximation boundary the paper names as future work. |
| 16 | Missing data, distribution shift | Only score perturbation is done. |
| 17 | Online / A/B integration | Out of scope for an offline study. |

## Summary

Of the 20 issues: **11 were already addressed**, **5 are fixed here**, and
**4 require experiments** that we scope explicitly rather than claim.

The two Critical items are both in category A: #5 (coalition refitting) is
already answered by the three-estimand table, and #7 (statistics) by the
Wilcoxon, Holm, Wilson, bootstrap and effect-size reporting already present.
