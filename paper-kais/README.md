# KAIS submission package

Target journal: **Knowledge and Information Systems (Springer)**.

## Submission files

- `main.tex`, `main.pdf`: manuscript source and compiled PDF.
- `Online-Resource-1.tex`, `Online-Resource-1.pdf`: electronic supplementary material.
- `paper.bib`, `sn-jnl.cls`, `sn-basic.bst`: bibliography and Springer class/style files.
- `figures/`: all manuscript figures.
- `cover-letter.tex`, `cover-letter.pdf`: KAIS cover letter.
- `suggested-reviewers.md`: reviewer shortlist requiring an author conflict check.
- `MANIFEST.json`: release commit and SHA-256 records.
- `SUBMISSION_CHECKLIST.md`: remaining portal and external checks.
- `reproducibility/`: Figure 2 reconstruction script and stored results.

## Build

```text
pdflatex main
bibtex main
pdflatex main
pdflatex main
```

The supplementary material is standalone:

```text
pdflatex Online-Resource-1
pdflatex Online-Resource-1
```