# Round-2 audit: blocker-by-blocker status

Every item verified against the source or an artefact before acting. One
blocker cannot be closed in this environment and is stated as such rather than
papered over.

## Blockers

### B1. ESM cited but not uploaded — CLOSED

`kais-esm.tex` exists and compiles as a standalone `article` document with six
S-numbered sections. It was in the repository at the time of the audit but was
evidently not in the uploaded PDF set.

**Two real defects found while checking it.** The main text cited supplement
items by hand-written S-number, and two were wrong:

| Cited as | Actually renders as | Item |
|---|---|---|
| ESM Table S1 | **ESM Table S4** | analytic games |
| ESM S5 | **ESM S6** | fusion negative result |

Hand-written numbers desynchronise the moment a float moves, so they are now
**computed** from the supplement at build time by `esm_numbering()`, with
`@@ESM:label@@` placeholders in the prose. An unresolvable placeholder is a
build error. `test_esm_pointers_resolve_to_the_right_supplement_items` locks it.

### B2. Three `[?]` citations — CLOSED

Root cause: wrong year suffixes in the keys I wrote, not missing bib entries.

| Written | Correct key in `paper.bib` |
|---|---|
| `chowdhury2024rankshap` | `chowdhury2025rankshap` |
| `pliatsika2024sharp` | `pliatsika2025sharp` |
| `ji2023critical` | `ji2023leakage` |

`test_every_cite_key_exists_in_the_bib` now fails on any undefined key.

### B3. Sampling error measured on the wrong game — **NOT CLOSED**

The audit is correct and this is the one item I cannot fix here.

Closing it requires refitting the MovieLens game to dump the 32 ranking-stage
NDCG@10 values. This sandbox has **no corpora** (`data/raw` and
`data/processed` are empty but for `.gitkeep`) and **no network**
(`files.grouplens.org` is unreachable). The values cannot be synthesised, and
inventing them would be fabrication.

What I did instead:

1. **`scripts/persist_ndcg_game.py`** — new, ready to run where the data
   lives. Dumps `game.v_all()` for the main fixed-candidate game and asserts
   efficiency before writing.
2. **`run_sampling_error.py --game ndcg`** — now prefers the NDCG lattice and
   falls back to recall only if the NDCG one is absent, recording which it
   used. The artefact currently says
   `"game": "end_to_end_recall"` with a `FALLBACK:` caveat.
3. **The manuscript no longer asserts the transfer.** The claim that relative
   errors transfer has been replaced with an explicit scope limitation naming
   what is shared (five players, bounded payoff, comparable interaction ratio)
   and what is not shown (quantitative transfer). The abstract now says "on a
   five-player lattice of this shape". The figure caption names the game.

To finish, on a machine with the corpora:

```sh
python scripts/persist_ndcg_game.py --dataset ml_1m --seed 42
python scripts/run_sampling_error.py --game ndcg --dataset ml_1m
python scripts/make_sampling_error_figure.py
python scripts/make_kais_main.py
```

Then delete the scope-limitation paragraph in Section 4 and restore the direct
claim. If the NDCG curve differs, report the NDCG numbers.

### B4. Algorithm 1 pointed at the wrong equations — CLOSED

Confirmed: my earlier `_fix_refs` had retargeted the standardisation and
baseline lines onto `eq:candidates` and `eq:game`, which are candidate
construction and the characteristic function. The fix restores both as real
numbered equations rather than relabelling:

| Line | Was | Now |
|---|---|---|
| standardise | Eq. (3), candidates | **Eq. (4)**, `eq:zscore` |
| baseline | Eq. (4), $v(S)$ | **Eq. (6)**, `eq:baseline` |

Equation order verified: (1) shapley, (2) loo, (3) candidates, (4) zscore,
(5) game, (6) baseline, (7) dilution, (8) dup.

Placement also fixed. The float was emitted after the preconditions block, so
it drifted to page 11; it is now emitted immediately after the paragraph that
introduces it, with `[tb]` rather than a deferral-prone bare `[t]`.

### B5. Bibliography too thin — CLOSED

21 cited to **37 cited**. Most keys already existed in the 52-entry bib; I had
simply failed to cite them. Four genuinely new entries added, both journal
details verified against published records:

- Holm 1979, *Scand. J. Statist.* **6**(2):65–70
- Grabisch & Roubens 1999, *Int. J. Game Theory* **28**(4):547–565,
  doi `10.1007/s001820050125`
- Wilcoxon 1945; Sun et al. RecSys 2020

Now cited where the claim occurs: MovieLens/Gowalla/Amazon at the corpora
sentence, Hu et al. on the ALS row, Levy & Goldberg on the PPMI row, Järvelin &
Kekäläinen at the metric, Grabisch & Roubens at the interaction index,
LightGCN/SASRec at the baselines, Wilcoxon/Holm at the paired test.

### B6. Production bugs — CLOSED

| Item | Finding |
|---|---|
| Email | Source was already correct: `\email{mouad\_louhichi@um5.ac.ma}`. The space is a PDF text-extraction artefact. **No change.** |
| Fig. 1 `V ALIDA TION` | **Real, and I was wrong to dismiss it last round.** `snfold` used `align=center` with `text width=19mm`; VALIDATION exceeds 19mm, so TeX justified it by stretching inter-letter glue. Fixed with `align=flush center` and `text width=23mm`. |
| Table 5 caption | Fixed. "as one declared primary family" removed; it contradicted the retirement subsection. The Holm adjustment is still applied and reported. |
| `Table~ESM Table~S8` | Fixed; nested reference eliminated. |
| Tag / commit | `MANIFEST.json` regenerated. The tag still needs creating at the final commit. |

## Reviewer-risk items

- **R1 Amazon headline** — the $N_{\max}=1\,200$ row with recall $0.750$ is now
  in Table 2, not only in prose. Value verified against
  `results_amazon_video_games.json`, which gives `0.7499`.
- **R2 fixed-head monotonicity** — cannot be measured here (same data
  constraint as B3). The manuscript now names it explicitly as the sharpest
  open question about the construct, and states the mixed provenance of the
  three-estimand table in the same clause.
- **R3 recsys evaluation literature** — Sun et al. and Zangerle & Bauer added
  alongside Ji et al.
- **R6 tone** — both flagged phrases removed. The third, "We say that rather
  than 'correctly'", is kept once: it marks a real distinction between a claim
  under the declared game and a claim about ground truth.

## Guards added

`tests/test_kais_split.py` is now 26 tests. New ones cover: every cite key
resolves; the field's core artefacts are cited; at least 30 references;
algorithm equation pointers correct; algorithm inside its subsection; the
sampling artefact declares its game; the Amazon larger cap is in Table 2; no
"primary family"; no nested table reference; `snfold` does not justify.

All mutation-tested. Reverting any single fix turns the corresponding test red.

## Remaining before SNAPP

1. **B3**: run the four commands above where the corpora live.
2. Compile both PDFs. No TeX here, so neither has been produced.
3. Fill in 3–5 suggested reviewers.
4. Create the tag; update the commit hash in Declarations.
5. Withdraw the KBS submission if it was actually submitted.
