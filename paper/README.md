# Manuscript

`paper.tex` + `paper.bib`, targeting *Discover Artificial Intelligence*.

## Build

```bash
cd .. && python scripts/run_study.py --synthetic && python scripts/make_assets.py
cd paper && make
```

Figures are read from `../artefacts/figures/`; tables are `\input{}` from
`../artefacts/tables/*.tex`. **No number is typed into the manuscript by hand** —
regenerate assets and the paper follows.

## Before submitting

1. **Run on real corpora.** Every number is currently from the synthetic pilot.
   Put raw files in `data/raw/` and re-run without `--synthetic`.
2. **Re-check the negative result.** C4/C5 fail on synthetic data because the
   planted structure contains no segment heterogeneity. Real behavioural data
   may differ; if it does, §6 needs rewriting from a negative result to a
   positive one.
3. Add funding statement and ORCID.
4. Re-verify the journal's SJR on Scimago.
5. Archive the artefact on Zenodo and insert the DOI.
