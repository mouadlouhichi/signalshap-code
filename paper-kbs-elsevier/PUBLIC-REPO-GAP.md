# What the public repository is missing

Compared `github.com/mouadlouhichi/signalshap` at tag `kbs-submission`
(commit `ea8ae5d`, 21 August 2026) against the current working tree.

The tag exists and the manuscript now names it correctly. The problem is not
the tag name, it is where the tag points: **161 files there, 444 here.**

## 1. Artefacts that back floats in the manuscript

These are the ones that matter, because a reviewer following the
Code-availability link cannot reproduce the corresponding float without them.

| Missing artefact | What it backs |
|---|---|
| `artefacts/fig2_ndcg_sampling.json` | **Figure 8** and every sampling-error number in the abstract (3.27%, 2.22%, 1.93%). Holds the recovered 32-coalition NDCG lattice |
| `artefacts/attribution_baselines.json` | **Table `tab:rulecomparison`**, all of **Section 4.5**, the eight-rule comparison that answers the editor's "insufficient comparative baselines" complaint |
| `artefacts/reviewer_q1_q3.json` | The estimand-matched Shapley result and the regime-dependence check |
| `artefacts/sampling_error.json` | The earlier recall-game sampling run the figure is compared against |

Section 4.5 is the section written specifically to answer the desk-reject.
Shipping the paper with its supporting artefact absent from the public repo is
the worst single item on this list.

## 2. Whole directories absent

- `artefacts/tables/` (27 files): T1 to T9 as `.csv`, `.md` and `.tex`
- `artefacts/figures/` (7 files): F1 to F7 rendered figures
- `artefacts/synthetic_pilot/` (5 files): the pilot corpora results
- `configs/`: **the frozen configuration**. Code availability promises
  "configuration files"; the public tag has none
- `notebooks/`, `reproducibility/`, `paper-kbs-elsevier/`

Artefact count: **52 public, 95 here.**

## 3. Scripts added since the tag (29)

Including every script that produced the new work:
`run_attribution_baselines.py`, `run_reviewer_q1_q3.py`, `run_sampling_error.py`,
`persist_ndcg_game.py`, `make_sampling_error_figure.py`,
`rebuild_sampling_figure.py`, `make_kbs_from_kais.py`, `extract_floats.py`,
`check_latex.py`, `sync_reproducibility.py`.

The public tag still has the old layout: `experiments/` and
`data_preparation/` rather than `scripts/`. Two source files still carry the
old paths in their messages (`memory.py`, `data/loaders.py`), so error text
there tells a reader to run a script that has moved.

## 4. Tests added since the tag (7)

`test_kbs_kais_sync.py` (70 tests), `test_kais_split.py`,
`test_elsevier_conversion.py`, `test_reporting_consistency.py`,
`test_reproducibility_release.py`, `test_figures_are_current.py`,
`test_round8_notebook.py`.

Current suite: **387 passing, 1 skipped.** A reviewer running the public
checkout gets a much smaller suite.

## 5. MANIFEST is stale

| | public tag | here |
|---|---|---|
| `git_commit` | `a037abc` | `5b46ad7` |
| `git_describe` | `discover-ai-submission-58-ga037abc` | `5b46ad7-dirty` |
| `n_artefacts` | 55 | 59 |

`git_describe` still names the **Discover AI** submission. The manuscript says
the commit behind every number is recorded in `MANIFEST.json`; at the public
tag that commit is from a different submission entirely.

## What is NOT missing

`src/signalshap/` is effectively identical. The two differing files
(`memory.py`, `data/loaders.py`) differ only in docstring and error-message
paths after the `experiments/` to `scripts/` move. **No algorithmic code is
missing.** The results are reproducible from the public tag in principle; what
is missing is the evidence, the configuration and the newer drivers.

Also note `.DS_Store` is committed at the public tag. Worth deleting.

## Fix

```sh
# from this checkout, with `public` pointing at github.com/mouadlouhichi/signalshap
git remote add public https://github.com/mouadlouhichi/signalshap   # if needed
git push public HEAD:main
git tag -f -a kbs-submission -m "KBS submission"
git push --force-with-lease public kbs-submission
```

Moving the tag is safe here: nothing cites the old one yet, and it currently
points at a Discover AI era commit.

Regenerate `MANIFEST.json` on the M4 before pushing, so `git_commit` and
`git_describe` match what the paper claims. Note the current value is
`5b46ad7-dirty`; a dirty describe should not ship.

Then confirm, before pasting the URL into Editorial Manager, that
`artefacts/fig2_ndcg_sampling.json` and `artefacts/attribution_baselines.json`
are both visible on the public repo at that tag.

## Decide what to exclude first

This checkout has items that should not go public as-is:

- Seven `.zip` files at the root (`paper-kbs.zip`, `signalshap-main2.zip`, ...)
- `kbs-article.pdf`, a stale CAS-format build
- `paper-reviews/` and `response-to-reviewer.md` if they name reviewers
- `paper-kbs/`, the superseded KBS directory

`paper-kbs-elsevier/` itself is fine to publish and arguably should be, since
it makes the submission reproducible end to end.
