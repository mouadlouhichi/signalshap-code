# SignalShap

**Exact-enumeration ranking-stage attribution of sources in hybrid recommenders.**

Reproducibility release for the paper *SignalShap: Exact-Enumeration
Ranking-Stage Attribution of Sources in Hybrid Recommenders*. Everything
needed to regenerate every number, table and figure in the manuscript is
here: the implementation, the frozen configuration, the released artefacts
with SHA-256 hashes, and a provenance map from each paper object back to the
artefact that produced it.

**CPU only.** No GPU, no CUDA, no PyTorch. Five sources give
2<sup>5</sup> = 32 coalitions, so the Shapley value is computed by exhaustive
enumeration on a laptop rather than sampled.

---

## What the method does

A production hybrid recommender fuses several architecturally distinct
scorers. Two different questions get asked about them, and they are routinely
conflated:

- **How should the system's value be divided among its sources?** That is
  credit allocation, and the Shapley value is the canonical answer.
- **What would we lose if we retired one source?** That is a removal effect,
  and leave-one-out ablation estimates it.

SignalShap makes the difference measurable. It declares a five-player
cooperative game whose payoff is NDCG@10 on a fixed, coalition-independent
candidate set, enumerates all 32 coalitions exactly, and compares the
resulting allocation against measured end-to-end removal cost.

**Headline result:** the two rules disagree in *sign* by a material margin on
two of three corpora, and leave-one-out predicts retirement cost better than
the Shapley allocation on all three. SignalShap allocates the value of a
declared ranking-stage game; that allocation is **not** the operational cost
of retiring a source. The paper claims credit allocation, not retirement
guidance.

### The five players

| id | signal | implementation |
|----|--------|----------------|
| `cf` | collaborative filtering | ALS on implicit feedback, 64 factors, `alpha = 1` |
| `ct` | content | TF-IDF cosine over item metadata, 5000 terms |
| `pop` | popularity | log-frequency with 180-day exponential decay |
| `rec` | recency | decay over the user's last touch of an item's content cluster |
| `seq` | sequential | PPMI-SVD over windowed co-occurrence, 64 dims |

Two pairs overlap **by declared design, not by discovery**: `pop`-`cf` (ALS on
implicit feedback chases popularity) and `rec`-`ct` (recency is defined over
content clusters). Stating this in advance is what makes the redundancy
analysis a test rather than a story.

---

## Quickstart

```bash
git clone <this repo> && cd <this repo>
pip install -r requirements.txt

# runs end to end with no downloads, on planted synthetic corpora
PYTHONPATH=src python experiments/run_study.py --synthetic --datasets ml_1m --seeds 42 43

# figures and tables from the artefacts
PYTHONPATH=src python scripts/make_assets.py

# 204 tests, no data required
PYTHONPATH=src python -m pytest tests/ -q
```

The synthetic path exists so the pipeline is verifiable before any download:
the loaders fall back to deterministic corpora with planted structure
(popularity skew, latent factors, content clusters, temporal drift). Every
artefact from a synthetic run records `synthetic: true`, and no synthetic
number is reportable.

---

## Reproducing the paper

### 1. Fetch the corpora

The raw corpora are **not redistributed**: the GroupLens license forbids it.
Both scripts are idempotent.

```bash
bash data_preparation/fetch_benchmarks.sh    # MovieLens-1M, from GroupLens
bash data_preparation/fetch_timestamped.sh   # Gowalla check-ins (SNAP), Amazon Video Games
```

### 2. Run the study, one corpus at a time

```bash
PYTHONPATH=src python experiments/run_study.py --datasets ml_1m              --budget-gb 24
PYTHONPATH=src python experiments/run_study.py --datasets amazon_video_games --budget-gb 24
PYTHONPATH=src python experiments/run_study.py --datasets gowalla_ts         --budget-gb 24
```

**One corpus per invocation, deliberately.** `run_study.py` refuses a
multi-corpus call whose corpora need different memory-derived user caps: a
single process-wide cap would silently apply the smallest to all of them and
substitute a different MovieLens than the one reported. The refusal is a
feature; do not work around it.

`--budget-gb` caps how much RAM the five dense score matrices may use, and the
user count per corpus is *derived* from it rather than guessed, so a large
corpus downsizes instead of being OOM-killed. **Leave it at 24.** The reported
corpus shapes were produced at that budget and `check_paper_shape` refuses to
overwrite the artefacts if a different budget yields a different shape.

> **Known limit.** Gowalla at 8,865 x 82,134 needs 14.6 GB for the score
> matrices before the game allocates anything, and the full E0-E8 suite was
> OOM-killed on a 48 GB machine after 116 minutes. Its sweeps and segment
> diagnostics therefore remain under the legacy candidate rule. Gowalla's
> *primary* attribution and retirement numbers are unaffected: those come from
> `final_seed_ci.json`, which is source-symmetric on all three corpora.

### 3. Ten-seed runs and the sensitivity analyses

```bash
PYTHONPATH=src python experiments/run_final_revision.py --only seeds   --budget-gb 24
PYTHONPATH=src python experiments/run_final_revision.py --only retire  --budget-gb 24
PYTHONPATH=src python experiments/run_protocol_sensitivity.py --corpora ml_1m --budget-gb 24 \
    --seeds 42 43 44 45 46 47 48 49 50 51
PYTHONPATH=src python experiments/run_global_timeblock.py --corpora ml_1m --budget-gb 24 --retirement
PYTHONPATH=src python experiments/run_pool_sensitivity.py --corpora ml_1m --budget-gb 24
PYTHONPATH=src python data_preparation/audit_repeat_items.py \
    --corpora ml_1m amazon_video_games gowalla_ts --budget-gb 24
```

Or all of the outstanding ones in one resumable command:

```bash
bash experiments/run_round8_remaining.sh 24
```

Every script resumes from what is already on disk, so an interrupted run can
be restarted and a stage that already succeeded is cheap to repeat.

### 4. Verify

```bash
PYTHONPATH=src python scripts/make_manifest.py       # SHA-256 for every artefact
PYTHONPATH=src python scripts/check_run_valid.py ml_1m
```

---

## Provenance: which artefact backs which number

`artefacts/PROVENANCE.md` is the authoritative map. It exists because a
reviewer found three different `v(G)` values for what is nominally the same
MovieLens seed-42 game and could not tell which was final. It records, per
paper object, the artefact, the **platform**, the **candidate rule** and the
**seeds**.

`artefacts/MANIFEST.json` records a SHA-256 for every artefact file together
with the commit, the environment, and the BLAS backend that produced it.

### Two things that will otherwise waste your time

**Never compare a number across platforms.** arm64 and x86-64 agree on
candidate set *sizes* exactly but differ in candidate *contents* for 2 of
6,035 MovieLens users, because ALS and truncated SVD accumulate in different
orders under different BLAS. That moves `v(G)` by about 5.4e-4 and the raw
monotonicity count between 16 and 26. `0.05190` (x86) and `0.05136` (M4) are
the same game. Every reported sign, ordering and material count is unaffected,
which is exactly why the paper reports a material count alongside the raw one.

**Two candidate rules exist.** `symmetric_reciprocal_rank` is the method of
record and the code default. `legacy_best_rank_source_order` is superseded and
order-dependent, retained only so the ablation can measure what that
dependence cost. Every artefact stamps which rule produced it.

---

## Key results

Ten-seed means, source-symmetric candidate rule, from `final_seed_ci.json`.

### Allocation against ranking-stage removal

| corpus | source | Shapley | LOO(rank) |
|---|---|---|---|
| MovieLens-1M | `cf` | **+0.01573** | **-0.00457** |
| MovieLens-1M | `seq` | +0.02993 | +0.01745 |
| Gowalla | `pop` | **+0.00051** | **-0.00156** |
| Gowalla | `cf` | +0.00711 | +0.00743 |
| Amazon-VG | `cf` | +0.01980 | +0.00890 |

The bolded rows are the **material sign disagreements**: `cf` on MovieLens
(gap 38.8% of `v(G)`) and `pop` on Gowalla (12.2% of `v(G)`). Both intervals
exclude zero across ten seeds. Amazon-VG has none, which is what makes it the
useful negative case: a strong substitutive interaction is not by itself
sufficient to produce a flip.

### Does attribution predict retirement cost?

Rank agreement with measured end-to-end removal loss, ten seeds:

| corpus | tau(LOO) | tau(Shapley) | paired delta | Wilcoxon p |
|---|---|---|---|---|
| MovieLens-1M | 0.96 | 0.20 | +0.76 [0.70, 0.80] | 0.0020 |
| Amazon-VG | 0.96 | 0.74 | +0.22 [0.16, 0.28] | 0.0039 |
| Gowalla | 1.00 | 0.80 | +0.20 (zero variance) | 0.0020 |

Leave-one-out wins on every corpus and every seed. **This is a result against
the paper's own instrument, and it is the point:** the Shapley allocation
answers a different question, so it should not be read as retirement guidance.

### Applicability

| corpus | users x items | density | N_max | test recall | gate |
|---|---|---|---|---|---|
| MovieLens-1M | 6,038 x 3,533 | 2.697% | 600 | 0.748 | pass |
| Amazon-VG | 7,120 x 3,516 | 0.469% | 600 | 0.589 | below |
| Gowalla | 8,865 x 82,134 | 0.075% | 11,623 | 0.450 | below |

Candidate recall is the ceiling on every ranking metric, so it is reported as
a precondition rather than a result. Under the declared 0.60 gate only
MovieLens clears it; the other two are retained for *relative* contrasts only
and excluded from absolute NDCG comparison.

On Gowalla the gate is **unreachable at any `N_max`**: 49.9% of its evaluated
users have a test venue already in their training history, which the mask
makes ineligible, so recall is bounded above by 0.501 and the measured 0.450
is 0.898 of the attainable ceiling. Those users contribute
`v_u(S) = 0` for all 32 coalitions and dilute the whole game by an exact
constant factor, `v(S) = rho * v_live(S)`. Every ordering, sign and
ratio-to-`v(G)` is invariant to that dilution; every absolute magnitude is
roughly halved.

---

## Layout

```
reproducibility/
├── README.md                  this file
├── requirements.txt           pip dependencies
├── environment.yml            conda environment
├── configs/                   frozen.yaml: N_max, recall gate, seeds, amendment log
├── src/                       the implementation (importable package)
├── scripts/                   verification and asset generation
├── data_preparation/          corpus fetching and characterisation
├── experiments/               everything that produces results
├── tables/                    generated tables (md, csv, tex)
└── figures/                   generated figures (png)
```

### What lives where

| directory | contents |
|---|---|
| `data_preparation/` | `fetch_benchmarks.sh`, `fetch_timestamped.sh` (corpus download), `audit_repeat_items.py`, `audit_global_time.py`, `measure_kcore_sweep.py` (corpus characterisation) |
| `experiments/` | `run_study.py` (main E0-E8 suite), `run_final_revision.py` (ten-seed), `run_protocol_sensitivity.py`, `run_global_timeblock.py`, `run_pool_sensitivity.py`, `rerun_all.sh`, `run_round8_remaining.sh` |
| `scripts/` | `make_assets.py` (figures and tables), `make_manifest.py` (SHA-256), `check_run_valid.py`, `check_paper_numbers.py` |
| `tables/`, `figures/` | regenerated by `scripts/make_assets.py`; committed so they can be compared against a fresh run |
| `artefacts/` | released JSON results, `MANIFEST.json`, `PROVENANCE.md` |
| `tests/` | 204 tests, no data required |

### Inside `src/signalshap/`

```
config.py              frozen configuration, admissibility ladder
memory.py              corpus sizing from a RAM budget, shape guards
data/loaders.py        loading, leave-last-two-out split, as-used density
scorers/base.py        cf, ct, pop, rec, seq + mask_seen
scorers/neural.py      LightGCN and SASRec reference baselines (NumPy)
candidates/builder.py  union-of-top-N, growth loop, truncation rules
game/core.py           v(S), exact Shapley, monotonicity audit
attribution/values.py  Banzhaf, semivalues, Grabisch-Roubens interactions
attribution/baselines.py  LOO, forward selection, permutation, MC Shapley
experiments/estimands.py  three games + end-to-end retirement simulation
experiments/recovery.py   duplicate-injection symmetry recovery
experiments/synthetic_games.py  analytic games with known Shapley vectors
segments/segments.py   segmentation and SignalShap-Fuse
fusion/fullcatalog.py  full-catalogue protocol
stats/tests.py         Wilcoxon, permutation, Holm-Bonferroni, bootstrap
plots/assets.py        figures and tables, artefact-driven
pipeline.py            E0-E8 orchestration
```

Note `src/signalshap/experiments/` (library code, imported) is distinct from
the top-level `experiments/` directory (runnable entry points).

---

## Design decisions worth knowing before reading results

1. **Candidates are coalition-independent.** `C_u` is the union of each
   source's own top-N, so every coalition ranks exactly the same items. The
   rejected alternative, drawing candidates once from the grand-coalition
   scorer, hands the grand coalition a pool selected in its own favour and
   biases every attribution, since attributions are built entirely from
   differences `v(S + g) - v(S)`. That design is retained as an ablation so
   the bias avoided can be measured.

2. **The ridge penalty is frozen, never tuned per coalition.** Tuning per
   coalition is optimistic bias that grows with `|S|`, which inflates `v(G)`
   against small coalitions.

3. **`v(empty) = 0` exactly and per user**, not merely on the mean. Property 3
   requires the per-user version. The empty-coalition baseline is the
   closed-form expected NDCG of a random ranking: deterministic, identical on
   every machine, no seed. An earlier sampled version made a sign-based
   finding depend on which permutation happened to be drawn.

4. **The baseline does not cancel.** It shifts every `phi_g` by exactly
   `-delta/n`, because it survives in the empty-to-singleton marginal. The
   manuscript once claimed invariance here; that claim was false and is
   withdrawn.

5. **The game is non-monotone on all three corpora**, so the
   redundancy-positivity property does not apply and a negative `phi_g` is a
   substantive finding rather than numerical error. This is a genuine result
   about coalition-conditional refitting, not an inconvenience.

6. **"Exact" means exact given the fitted `v`.** The 32-coalition aggregation
   has no sampling error, unlike Monte-Carlo Shapley. But `v(S)` is itself
   estimated from ridge heads fitted on a validation fold, so `phi_g` carries
   estimation error and is reported with seed-based intervals throughout.
   Never read "exact" as "no error"; read it as "no sampling error".

---

## Tests

```bash
PYTHONPATH=src python -m pytest tests/ -q     # 204 passed, 4 skipped
```

The suite is not decoration. Several tests exist because the corresponding bug
shipped once and cost a full re-run:

| test | what it prevents |
|---|---|
| `test_property2_counterexample` | the redundancy-positivity claim is **false** without monotonicity; the counterexample is published |
| `test_baseline_determinism` | a hash-derived baseline, after a NumPy Generator difference moved `v(G)` across machines |
| `test_masked_user_dilution` | the exact `v(S) = rho * v_live(S)` identity, verified to 1.4e-17 |
| `test_svd_sign_determinism` | `rec` is bit-identical across solver seeds, and exhibits the tied-subspace case a sign convention cannot fix |
| `test_no_test_leakage` | heads fit on validation, never on test |
| `test_nmax_registration` | an unregistered corpus is a specification error, not an occasion to guess a default |
| `test_memory_sizing` | a resized corpus can never silently overwrite the reported artefacts |
| `test_density_ordering` | the corpus density ordering the cross-corpus claim depends on |
| `test_ridge_duplication` | minimum-norm behaviour under exact duplicate sources |
| `test_runner_script` | every batch stage uses a portable interpreter and a flag its target actually defines |

---

## Citation

```bibtex
@article{louhichi2026signalshap,
  title   = {SignalShap: Exact-Enumeration Ranking-Stage Attribution of
             Sources in Hybrid Recommenders},
  author  = {Louhichi, Mouad and Nesmaoui, Redwane and Lazaar, Mohamed},
  journal = {Knowledge-Based Systems},
  year    = {2026},
  note    = {under review}
}
```

## License

MIT, see `LICENSE`. The corpora are **not** covered by it and are not
redistributed: MovieLens-1M is used under the GroupLens research-use license,
Gowalla check-ins come from the SNAP collection, and the Video Games category
is from the Amazon Reviews 2023 corpus. Refetch each from its original source
with the supplied scripts.
