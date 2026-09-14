# KAIS playbook: verification pass and execution status

Every checkable claim in the playbook was tested against the manuscript and the
artefacts before acting on it. Items are grouped by whether the claim held.

## A. Verified correct, and acted on

### Length (the desk-reject risk, and the playbook is right)

Measured on `paper-kais/kais-article.tex`, excluding tables, maths and TikZ:

| Quantity | Measured | KAIS limit |
|---|---|---|
| Body words | **20,142** | 15,000 |
| Tables | 14 | — |
| Figures | 7 (now 8) | — |
| Display items | **21** | playbook target 8 |

Even before the FAQ's +500 words per full-page display item, the manuscript is
roughly 5,000 words over. With display items counted it is far worse. This is
the single largest threat and the playbook's central point stands.

### P1: sampling-error measurement (DONE, and the result is favourable)

`scripts/run_sampling_error.py` + `scripts/make_sampling_error_figure.py`
produce `artefacts/sampling_error.json` and `paper-kais/figures/Fig8.png`.

The playbook framed this as a coin flip: if sampling at M=500 sits below seed
noise, demote "exact" to a convenience. **It does not.** Permutation sampling,
p95 over 20 repeats, as a percentage of v(G):

| M | Permutation | KernelSHAP |
|---|---|---|
| 50 | 10.84% | 25.93% |
| 100 | 6.33% | 18.60% |
| 500 | **2.73%** | 9.88% |
| 2000 | 2.16% | 3.67% |

Both yardsticks the paper already uses:

- seed-to-seed range over ten fits: **2.22%** of v(G)
- the 1e-3 materiality threshold: **1.91%** of v(G)

Permutation sampling at M=500 (2.73%) exceeds both. It only crosses the
materiality line somewhere past M=2000. **Exactness is load-bearing**: a
sampled estimator at a realistic budget could manufacture or erase a material
sign flip, which is the paper's headline finding. KernelSHAP is worse
throughout, as expected at n=5 where its kernel is concentrated on few sizes.

**Honest scope limit, recorded in the artefact:** the only complete
32-coalition characteristic function persisted in `artefacts/` is
`e11_estimands_*.json -> end_to_end.coalition_recall`, the end-to-end *recall*
game, not the ranking-stage NDCG@10 game. Absolute errors do not transfer;
errors relative to v(G) do, and that is what is plotted. Enumeration on that
game satisfies efficiency to 1.1e-16, confirming the estimator harness is
correct. Reproducing this on the NDCG game requires persisting its 32 values,
which is a cheap re-run but was not done here.

### P3 (partial): Table 4 stray footnote (FIXED)

Real bug, now removed from `paper-kbs/kbs-article.tex`. `tab:repeats` carried a
verbatim copy of the provenance footnote belonging to `tab:estimands`, complete
with `*` and `†` markers that appear nowhere in its own body.
`tab:estimands` retains its copy, where the markers are actually used.

### Global-time leakage numbers

Playbook cites 44%/27%/19%. `artefacts/global_time_audit.json` gives ML-1M
`future_train_fraction_vs_test.mean = 0.4416`. Confirmed.

### Amazon N_max=1200 recall

Playbook cites 0.750. `results_amazon_video_games.json` gives
`e5_robustness.candidate_size.n_max_1200.candidate_recall = 0.7499`. Confirmed,
and the manuscript already states 0.750 in two places.

## B. Claims that are WRONG (do not act on these)

### P3 bug list: three of five do not exist

| Claim | Reality |
|---|---|
| Email underscore "rendered as space" | Source is `\email{mouad\_louhichi@um5.ac.ma}`, correctly escaped. Any space is a **PDF text-extraction artefact** of the reviewer's copy-paste, not a source defect. |
| Fig. 1 shows `V ALIDA TION` | Source is `\textbf{VALIDATION}`. Same cause: TikZ node kerning confuses PDF text extraction. Renders correctly. |
| `SignalShapformulates` smash | Zero occurrences. `grep -o "SignalShap[a-z]"` returns nothing. |

These three are all artefacts of reading the compiled PDF's text layer rather
than the source. Changing the source to "fix" them would introduce real bugs.

### Abstract residual conflation "still present"

Already fixed (commit `18f65bf`, restored after being reverted by `6e67e64`).
The abstract now separates the analytic-game recovery, the additivity residual
(4.4e-16) and the fitted-corpus efficiency (6.9e-18).

### The playbook's own abstract reintroduces a banned phrase

Its paste-ready abstract contains **"identifies the cheapest source to drop"**.
"Cheapest source to retire" was removed from this manuscript at reviewer
request and is CI-guarded; the current text says "the source with the smallest
observed removal loss". The playbook's wording is a regression to language a
previous reviewer specifically objected to. **Do not paste that abstract
verbatim.**

Its abstract is also ~250 words against its own stated 220-230 target, and
retains "predeclared", which is the banned "pre-registered" idea in a thin
disguise. The current abstract uses "frozen".

## C. Not yet done, and why

| Item | Status |
|---|---|
| §§1-7 restructure to 14.5k words | **Not started.** This is 8-10 days of authorial rewriting, not a mechanical edit. It needs your voice and your judgement about what to cut. |
| ESM split | Blocked on the restructure. |
| P2 Table 11 provenance re-run | Needs a fitting run; the two artefacts are already disclosed as mixed provenance, and both `ct` values sit far below the 1e-3 threshold. Lower value than the playbook implies. |
| P4 Amazon headline cap | A judgement call about framing, yours to make. Both numbers are already in the text. |
| P5-P7 | Optional; P7 (SASRec as a sixth player) needs sampled Shapley at 2^6, which the new P1 result now shows is error-prone at this scale. |
| Title change | Yours to decide. Note the playbook's preferred title is 15 words and drops the method name, which is a real trade: "SignalShap" is the name under which the public repo, the tag and the artefacts are all published. |

## D. One structural disagreement worth stating

The playbook says to demote verification (analytic games, duplicate injection,
efficiency, additivity) from a contribution to "one subsection". That is right
for KAIS framing. But P1 now gives those checks a *purpose* they lacked: the
sampling-error figure shows the exact aggregation is not decoration, because
the sampled alternative is not accurate enough to resolve the paper's own
headline effect. Verification and exactness should be compressed into one
subsection **together with Fig. 8**, rather than compressed and scattered.
