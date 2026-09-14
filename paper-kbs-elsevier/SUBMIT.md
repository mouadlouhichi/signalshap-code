# What to upload to Knowledge-Based Systems

Editorial Manager, `https://www.editorialmanager.com/knosys/`.
Everything below is in `paper-kbs-elsevier/`. Verified at commit `d56d082`.

## Two things must happen before you upload

**1. Compile. Nothing here has been compiled.** The development sandbox has no
TeX, so every check on this package is static. Run:

```sh
cd paper-kbs-elsevier
pdflatex main && bibtex main && pdflatex main && pdflatex main
pdflatex supplementary-material && pdflatex supplementary-material
pdflatex highlights
pdflatex cover-letter
```

Then check: zero `??`, zero `(author?)`, 43 references resolved, and eyeball
the two-column layout, especially the eight full-width tables.

**2. Update the release tag.** Code availability names `kbs-submission` at
`github.com/mouadlouhichi/signalshap`. That tag exists, but it points at commit
`ea8ae5d` from **21 August**, which predates Figure 8 and Section 4.5. Editors
do check this link.

```sh
# push the current state to the public repo, then move the tag onto it
git push public HEAD:main
git tag -f -a kbs-submission -m "KBS submission"
git push --force-with-lease public kbs-submission
```

Moving a published tag is acceptable here because nothing cites the old one
yet. If you would rather not move it, cut a new tag and change the
Code-availability paragraph in `paper-kais/main.tex` to match, then
regenerate.

## Upload list

| # | Editorial Manager item type | File |
|---|---|---|
| 1 | Manuscript (LaTeX source) | `main.tex` |
| 2 | Bibliography | `paper.bib` |
| 3 | LaTeX class | `elsarticle.cls` |
| 4 | Bibliography style | `elsarticle-num.bst` |
| 5 | Figure | `figures/Fig1.png` |
| 6 | Figure | `figures/Fig3.png` |
| 7 | Figure | `figures/Fig8.png` |
| 8 | Manuscript PDF | `main.pdf` (you generate) |
| 9 | **Highlights** | `highlights.pdf` (you generate from `highlights.tex`) |
| 10 | **Supplementary material** | `supplementary-material.pdf` (you generate) |
| 11 | Cover letter | `cover-letter.pdf` (you generate) |

Upload the supplement as a PDF, not as `.tex`. Keep `main.tex` and the figures
as editable sources; Elsevier requires them.

### Highlights

`highlights.tex` is standalone and compiles on Overleaf with a single
`pdflatex` pass. It uses the `highlights` environment that `elsarticle.cls`
provides, so the output is a proper Elsevier Highlights page with the heading,
title and author line, not a bare list. Put `highlights.tex` and
`elsarticle.cls` in the same Overleaf project, or add it to the main project
and set it as the compile target.

`highlights.txt` is the same five bullets as plain text, for portals that ask
you to paste them into a form field. Upload the PDF; keep the text file to
hand.

**Do not upload:** `README.md`, `response-to-reviewer.md`, `SUBMIT.md`,
`suggested-reviewers.md` (that one goes into the portal form, not as a file),
or `reproducibility/` (it is for the public repository).

Only three figures ship because the restructure moved the rest into the
supplement. Fig1 is included even though Figure 1 renders as live TikZ: it is
the raster fallback.

## Portal fields

- **Article type:** Full Length Article.
- **Open access:** decline. Choose the subscription route; the cover letter
  says so and no APC funding was declared.
- **Suggested reviewers:** four are prepared in `suggested-reviewers.md`
  (Zick, Sun, Zangerle, Bauer). **Run a conflict check on each before
  entering them** and confirm the affiliations are current.
- **Declarations:** copy the manuscript's CRediT, competing interests,
  funding, ethics, data availability and generative-AI statements into the
  corresponding portal fields. Elsevier uses the portal text for the published
  version, so the two must agree.
- **Originality:** the letter states the work is not under consideration
  elsewhere. **If the KAIS submission is still open, withdraw it first and
  keep the written confirmation.** Dual submission is an automatic reject at
  both venues.

## What is verified in this package

| Check | Result |
|---|---|
| Test suite | 375 passed, 1 skipped |
| `check_paper_numbers.py` | numbers agree with `artefacts/` |
| `check_latex.py` on `main.tex` | passes |
| Undefined citation keys | 0 |
| Unresolved `\ref` (main and supplement) | 0 |
| `\citet` under a numeric style | 0 (this is what caused `(author?)`) |
| Springer leftovers (ESM, Online Resource, sn-jnl) | 0 |
| Em dashes, banned phrases | 0 |
| References cited | 43 |
| Highlights | 5 bullets, longest 73 characters; `.tex` and `.txt` agree |
| Cover letter | 450 words |
| Figures shipped vs referenced | 3 and 3, no orphans |

## Known limitations, already stated in the manuscript

Reviewers asked for three things that need compute we could not run. All are
written up as limitations rather than glossed:

1. Multi-seed `v_e2e` (Table 6 is seed 42 only).
2. A ranking-aware fusion head instead of ridge.
3. A retrieval-dominant stress test.

If you can run one before submitting, run the first: three seeds on
MovieLens-1M, 2^5 retrieval passes each. It is the cheapest and it directly
answers the "seed 42 may be idiosyncratic" reading of Table 6, which is the
only substantive objection still open.
