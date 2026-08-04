# What you need to do — SignalShap submission

Everything I can do in a sandbox is done. This is what needs your machine, your
judgement, or your credentials. Ordered by what blocks submission soonest.

---

## 1. Compile the Springer manuscript (30 min)

`paper/sn-article.tex` is the manuscript on the official `sn-jnl.cls`
(December 2024 package). The class and `sn-basic.bst` are committed, so it
compiles standalone.

```bash
brew install --cask mactex-no-gui     # or BasicTeX + tlmgr install the deps
cd ~/signalshap-code/paper
make             # runs the number check, then pdflatex x3
```

I could not compile here — no TeX in the sandbox. I validated statically
instead: balanced braces/environments/math, no broken `\ref`, no missing
citations, and every command checked against `sn-jnl.cls`. Two real errors were
caught that way (`\jyear` is absent from this class version; the class does not
load `amsmath`/`graphicx`), but **static checks are not a compiler.** Expect to
fix one or two small things on the first run.

- [ ] Compiles clean with `pdflatex`
- [ ] Zero undefined citations or references in `sn-article.log`
- [ ] Bibliography renders in Springer style

The `paper/` directory is self-contained: class file, bibliography style, and figures all live there, so it zips and uploads as-is.
`paper.tex` is the working version with inline `\input` of generated tables.
Keep `sn-article.tex` authoritative and delete `paper.tex` before submitting, or
you will eventually edit the wrong one.

---

## 2. Fill in what only you can supply (15 min)

- [ ] **Funding statement** — currently `[To be completed.]`
- [ ] **ORCID** for the corresponding author
- [ ] **Co-author emails** — I used plausible `um5.ac.ma` patterns; verify
- [ ] **Acknowledgements** — currently "Not applicable"
- [ ] Decide whether to name the IJACSA 2025 paper as companion prior work

---

## 3. Decide two open scientific questions

These are judgement calls I deliberately did not make for you.

### 3a. Amazon-Book's candidate pool

At `N_max=5000` recall is `0.529`, below your `0.60` gate. Rung 1 reaches
`0.637` at `N_max=20000` — but that is ~24% of its 84k catalogue, so the game
sits closer to full-catalogue ranking than to the fixed-candidate design.

Options: **(a)** keep it with the caveat already written into
§Preconditions; **(b)** drop Amazon-Book and report three corpora; **(c)** keep
it for the intervention only, where the pool size does not matter.

I currently have (a). **(c) is arguably the most defensible** — the
intervention is the paper's central claim and is unaffected by pool size.

### 3b. The C5 fusion claim

`d_z = 0.006`, Holm `p = 0.59`. It is written as "underpowered, not refuted".
A reviewer may still say a contribution you cannot detect is not a
contribution. Consider demoting C5 from the contributions list to a
Future Work paragraph. The paper survives without it; C1–C4 carry it.

---

## 4. Finish the experimental suite (2–4 h compute)

Robustness sweeps, segments, and fusion currently ran fully only on
MovieLens-1M. The other three have E0–E2 and E9.

```bash
cd ~/signalshap-code && git pull
# close other apps first — every freed GB is ~800 more users
jupyter lab notebooks/SignalShap_M4_FullStudy.ipynb
```

Set `SCORE_BUDGET_GB = 10` if corpora auto-downsize more than you like. Then:

```bash
python scripts/make_assets.py
python scripts/check_paper_numbers.py --strict
```

- [ ] All four corpora have E3–E8
- [ ] `check_paper_numbers.py` passes after regenerating

**Run that checker after every re-run.** Stale numbers have reached the
manuscript four times in this project; it is the single highest-yield habit
here.

---

## 5. Pre-submission gates

- [ ] `pytest tests/ -q` — 26 pass, 1 skipped
- [ ] `python scripts/check_paper_numbers.py --strict` — clean
- [ ] Abstract ≤ 250 words *(currently ~200)*
- [ ] Delete the title-rationale comment block in `paper.tex`
- [ ] Re-verify the journal's CiteScore/SJR on Scimago (the spec requires this
      within 24 h of submission)
- [ ] Archive on Zenodo, insert the DOI into Data Availability
- [ ] Build `make zip` for Snapp/Editorial Manager

---

## 6. Repository hygiene

- **`data/ml-1m/` is committed (24 MB).** GroupLens permits redistribution with
  attribution so it is not a licence violation, but most reviewers expect a
  download script. `scripts/fetch_benchmarks.sh` already handles the other
  three.
- **Use `git push --force-with-lease`, not `--force`.** A force-push overwrote
  three of my commits earlier; `--force-with-lease` refuses when the remote has
  commits you have not seen.

---

## Honest status

**Strong:** the intervention replicates on all four corpora (symmetry error
`0.0`, LOO exactly `0.000000`) — that is a ground-truth result about the
estimator, not a dataset artefact. Efficiency verified to `6.9e-18`. Wins over
LightGCN and SASRec at `p<0.001`. Reproducibility discipline is well above the
norm for this venue.

**Weak:** C5 is undetectable at this scale. Three of four corpora have a
non-monotone fitted game, so Property 2 does not formally apply there — this is
reported as a finding, and it is honest, but a reviewer will press on it. The
suite is uneven across corpora until you finish step 4.

**My read:** with step 4 done, this is a credible *Discover AI* submission. The
intervention is the reason — it converts "two methods disagree" into "one method
fails a test with a known answer."
