# Manuscript — Springer Nature template

Self-contained submission directory for *Discover Artificial Intelligence*.

| File | Purpose |
|---|---|
| `sn-article.tex` | The manuscript |
| `paper.bib` | Bibliography (24 entries) |
| `sn-jnl.cls` | Official Springer Nature class, December 2024 package |
| `sn-basic.bst` | Official Springer bibliography style |
| `figures/` | F1–F7, copied from `artefacts/figures/` |

Nothing here references paths outside this directory, so the folder can be
zipped and uploaded as-is.

## Build

```bash
make          # number check, then pdflatex → bibtex → pdflatex ×2
make zip      # flat submission.zip for Snapp / Editorial Manager
```

Requires a TeX distribution: `brew install --cask mactex-no-gui`, or BasicTeX
plus `tlmgr install natbib booktabs`.

## When results change

Figures are **copies**. After re-running the study, refresh them:

```bash
cd .. && python scripts/make_assets.py
cp artefacts/figures/*.png paper/figures/
python scripts/check_paper_numbers.py --strict
```

`make` runs that last check automatically and refuses to build on drift.
Inline numbers in the prose still need updating by hand — the checker tells you
which ones.

## Before submitting

See `../SUBMISSION_CHECKLIST.md`. The short version: fill in funding and ORCID,
delete the title-rationale comment block, and confirm the abstract is under
250 words.

## Compiling on Overleaf

Upload `signalshap-overleaf.zip` (built by `make zip`). It contains the `.tex`,
`.bib`, the Springer class and `.bst`, and `figures/` — nothing else is needed.

Set the Overleaf compiler to **pdfLaTeX** and the TeX Live version to **2021 or
later** (`algpseudocode` and `tikz` `arrows.meta` need it).

Two things to know if the compile misbehaves:

- **TikZ figure.** Figure 1 is drawn in TikZ. If the submission system's TeX
  chokes on it, set `\tikzfigurefalse` in the preamble and it falls back to the
  pre-rendered `figures/Fig1.png`, which is kept in sync with the TikZ source.
- **ORCID.** We deliberately do *not* use the class's `\orcid{}` macro. It calls
  `\includegraphics{Orcidlogo.eps}`, and that logo does not ship with
  `sn-jnl.cls` — the compile fails with a missing-file error. The ORCID is a
  plain `\href` instead.

Checks that run without TeX, and which should pass before you compile:

```bash
python scripts/check_paper_numbers.py --strict   # every number traces to an artefact
python scripts/check_discover_ai.py              # journal formatting rules
pytest tests/ -q                                 # 123 pass
```
