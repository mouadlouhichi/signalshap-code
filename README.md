# SignalShap

**Exact Shapley credit assignment over collaborative, content, and contextual signals.**

Hybrid recommenders fuse several architecturally distinct signals, but practice attributes
system quality to them with leave-one-out ablation, which fails under redundancy. SignalShap
recasts source attribution as a five-player cooperative game with fixed-candidate NDCG@10 as
its characteristic function. With five players the Shapley value is computed **exactly** over
2^5 = 32 coalitions on a laptop CPU — no sampling.

Specification: [`SignalShap_Implementation_Spec.md`](SignalShap_Implementation_Spec.md).

## Quickstart

```bash
pip install -e ".[dev]"
python scripts/run_study.py --synthetic   # E0-E8 -> artefacts/*.json
python scripts/make_assets.py             # F1-F7, T1-T8
pytest tests/ -v
```

Or step through [`notebooks/SignalShap_Reproduction.ipynb`](notebooks/SignalShap_Reproduction.ipynb),
which walks the whole pipeline with the reasoning inline.

Without raw data the loaders fall back to deterministic **synthetic corpora** with planted
structure (popularity skew, latent factors, content clusters, temporal drift), so the pipeline
runs end-to-end before any download. Every artefact records `synthetic: true`.

## Layout

```
src/signalshap/
  config.py              frozen, pre-registered values
  data/loaders.py        loading, leave-last-out split, as-used density
  scorers/base.py        cf(ALS) ct(TF-IDF) pop(decay) rec(cluster) seq(item2vec)
  candidates/builder.py  union-of-top-N + growth loop + truncation
  game/core.py           v(S), exact Shapley, monotonicity audit
  attribution/           LOO, forward, permutation, MC Shapley
  segments/              segmentation + SignalShap-Fuse
  fusion/fullcatalog.py  full-catalog protocol for T5
  stats/tests.py         Wilcoxon, permutation, Holm-Bonferroni, d_z
  plots/assets.py        F1-F7, T1-T8
  pipeline.py            E0-E8 orchestration
```

## Five design rules worth knowing before reading results

1. **Candidates are coalition-independent.** `C_u` is the union of each source's own top-N,
   so every coalition scores the same items. Drawing candidates from the grand-coalition
   scorer inflates `v(G)` against every `v(S)` and biases every attribution; that design
   survives only as ablation E8-a.
2. **"Exact" means exact *given the fitted v*.** The 32-coalition aggregation has no sampling
   error, but `v(S)` is estimated, so `phi_g` carries seed CIs in the main text.
3. **λ is frozen.** Tuning it per coalition is optimistic bias growing with `|S|` — the same
   pathology as grand-coalition candidates, by another route.
4. **Monotonicity is audited, never assumed.** Property 2 is *false* without it: a game
   satisfying exact redundancy with `v({g1})=1>0` yields `phi = -0.4167`. E0-b checks all 80
   `(S,g)` pairs; violations are findings, not defects.
5. **Two gates precede everything.** Candidate recall (the ceiling on every metric) and the
   monotonicity audit (the precondition for Property 2). Both are in T2. Read them first.

## Tests

| File | Pins |
|---|---|
| `test_property2_counterexample.py` | Monotonicity hypothesis; rejects the `½v({g1})` floor and the `½[v(G)-v(G\{g1,g2})]` closed form |
| `test_density_ordering.py` | The C3 density contrast, plus a provenance gate so estimates cannot pass as measurements |

## License

MIT. Datasets retain their own licenses — see spec §5.
