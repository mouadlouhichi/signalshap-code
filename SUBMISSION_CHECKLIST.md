# What you need to do

Everything runnable in a sandbox is done. This is what needs your machine, your
data, or your judgement. Ordered by what blocks resubmission soonest.

---

## 0. Read this first: one result changed the paper's claim

The retirement simulation (E12) found that **leave-one-out predicts the true
cost of removing a source better than Shapley** — rank agreement τ = 1.00
versus 0.20 — and correctly picks `cf` as cheapest to retire where Shapley picks
`ct`. Removing `cf` actually *improves* NDCG@10 by 0.0056 because it is largely
redundant with `seq` and `pop`.

This is not a refutation. The two methods answer different questions: LOO
measures the grand-coalition quantity a single-source removal needs, Shapley
measures average marginal credit. But it does mean **the paper can no longer
claim retirement guidance**, and I have rewritten it to claim credit allocation
only.

If you disagree with that framing, this is the decision to revisit before
anything else — it propagates to the title, abstract, and contributions.

---

## 1. Re-run on real corpora (blocking, 3–6 h)

The sandbox lost the raw benchmark files mid-session and the loader silently
substituted synthetic data. I caught it (candidate recall jumped to 1.000),
quarantined those runs in `artefacts/synthetic_pilot/`, and cut the paper back
to **real MovieLens-1M only**. That makes the reviewer's "effectively one
dataset" criticism literally true right now.

```bash
cd ~/signalshap-code && git pull
bash scripts/fetch_benchmarks.sh        # Gowalla, Yelp2018, Amazon-Book
# MovieLens-1M goes in data/raw/ml-1m/ separately

python scripts/run_study.py             # E0–E8, all corpora
python scripts/run_revision_experiments.py --dataset ml_1m   # E10–E13
python scripts/make_assets.py
python scripts/check_paper_numbers.py --strict
```

`run_revision_experiments.py` **aborts** if the loader falls back to synthetic
data, so this failure cannot recur silently.

- [ ] Four corpora present, all `synthetic: false`
- [ ] `check_paper_numbers.py` clean after regenerating
- [ ] Restore the four-corpus rows in Table 1 and the recovery table

---

## 2. Ten or more seeds with hierarchical inference (blocking, ~4 h)

Three seeds cannot characterise training variability, and users sharing a
fitted model are not independent replicates. Both tools are implemented:

```python
from signalshap.stats.tests import hierarchical_bootstrap, tost_equivalence
```

`hierarchical_bootstrap` resamples seeds then users; `tost_equivalence` tests
practical equivalence against a **pre-specified** margin.

- [ ] Re-run with `SEEDS = tuple(range(42, 52))`
- [ ] Report hierarchical CIs alongside the Wilcoxon p-values
- [ ] **Pre-specify the smallest meaningful NDCG difference before looking**,
      then run TOST against the global head

Expect the hierarchical intervals to be wider than the current ones. That width
is the honest answer, and reporting it is stronger than defending `p < 0.001`.

---

## 3. Timestamped corpora (blocking for the temporal players)

Three of five players (`rec`, `seq`, time-decayed `pop`) are uninterpretable on
the LightGCN splits, which carry no timestamps. Either:

- **(a)** swap in timestamped corpora — Amazon Reviews with timestamps, MIND,
  or Last.fm-1K — and run the full five-source game; or
- **(b)** run a reduced two-source game (`cf`, `ct`) on the untimestamped
  corpora and say so.

I'd take (a) for at least two corpora. (b) is defensible but concedes the
cross-density comparison.

---

## 4. Matched baseline tuning (~2 h)

LightGCN and SASRec got modest, unequal budgets. Any reviewer will discount the
`p < 0.001` wins until the budgets match.

- [ ] Equal search space, trials, and early-stopping for all methods
- [ ] Report the search space and selected values in a table

---

## 5. Fill in what only you can supply (15 min)

- [ ] **Funding statement** — still `[To be completed]`; `check_discover_ai.py`
      flags it and it blocks submission
- [ ] ORCID for the corresponding author
- [ ] Verify co-author emails (I used plausible `um5.ac.ma` patterns)
- [ ] Archive on Zenodo and insert the DOI — the reviewer asked for an
      immutable artefact **at review time**, not at acceptance

---

## 6. Compile and check (30 min)

```bash
cd paper && make          # runs both checkers, then pdflatex ×3
make zip                  # flat bundle for Snapp
```

No TeX exists in the sandbox, so **the manuscript has never been compiled.** I
validated statically — balanced environments, resolved refs and citations, every
command checked against `sn-jnl.cls`, required packages present — and that caught
three real errors (`\jyear` absent from the class, missing `amsmath`/`graphicx`,
missing `multirow`). Expect one or two layout nudges on the first run; the TikZ
figure's node spacing is the likeliest.

`\tikzfigurefalse` reverts Figure 1 to the raster in one line if TikZ misbehaves.

---

## What is already done

| | |
|---|---|
| Lemma 1 | Rewritten two-sided with a complete proof; `O(ε)` removed |
| Ridge duplication | Reviewer was right; redundancy now **measured** over 16 coalitions at both λ and λ=0 |
| Per-user normalisation | Fixed in Eq. (3) and the code — this changed two published numbers |
| Analytic ground truth | Six closed-form games, all exact (E13) |
| Alternative values | Banzhaf, semivalues, Shapley–Taylor interactions (E10) |
| Estimand comparison | Fixed vs refitted vs end-to-end heads (E11) |
| Retirement simulation | E12 — the negative result above |
| Fusion mapping | Explicit softmax with temperature and shrinkage |
| Leakage | Verified absent, documented, and pinned by tests |
| Springer compliance | 15 automated checks; only funding outstanding |
| Tests | 43 passing, 2 skipped |

---

## Honest assessment

**Major Revision remains right.** The mathematical objections are resolved and
the missing experiments now exist and run, which is real progress. But the
empirical base is currently one corpus and three seeds, and E12 narrowed the
practical claim. Items 1–4 are the difference between a defensible resubmission
and a second round of the same criticisms.

The strongest remaining assets are the analytic validation (E13), the
interaction indices localising redundancy, and the candour about E12 — reviewers
reward a paper that reports the result that weakens its own framing.
