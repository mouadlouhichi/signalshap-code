# Knowledge-Based Systems submission

Elsevier CAS double-column version of the manuscript, targeting
[Knowledge-Based Systems](https://www.sciencedirect.com/journal/knowledge-based-systems).

## This manuscript is edited directly

`kbs-article.tex` was **bootstrapped** from `../paper/sn-article.tex` by
`../scripts/make_elsevier.py`, but it is no longer generated. The KBS version
has since been edited directly: double-column math reflow, symbol
disambiguation, two corrected bibliography entries, and the Elsevier
declaration sections. Those edits are the submission.

**Do not run the generator against this file.** `make regen` exists for a
fresh re-port and will overwrite the submitted text, the bibliography and the
figures. `make check` deliberately does not call it.

What still guards the numbers is `scripts/check_paper_numbers.py`, which
validates against `artefacts/`, plus the guide-conformance tests in
`tests/test_elsevier_conversion.py`.

## Build

The Elsevier class files are Elsevier's and are not redistributed here.

```bash
bash fetch-template.sh    # cas-dc.cls, cas-common.sty, elsarticle-num.bst
make                      # checks, then pdflatex + bibtex + pdflatex x2
make zip                  # flat bundle for Editorial Manager
```

If `fetch-template.sh` cannot reach Elsevier's CDN, download
[els-cas-templates.zip](https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions)
manually and copy `cas-dc.cls`, `cas-common.sty` and `elsarticle-num.bst` here.

## What changed from the Springer version

Both templates are LaTeX with numbered citations, so the body ports unchanged.
The differences are confined to the preamble and the front and back matter.

| Springer `sn-jnl` | Elsevier `cas-dc` |
|---|---|
| `\documentclass{sn-jnl}` | `\documentclass[a4paper,fleqn]{cas-dc}` |
| `\author*[1]{\fnm{}\sur{}}` | `\author[1]{}` + `\cormark` + `\ead{}` + `\credit{}` |
| `\affil*[1]{\orgdiv{}\orgname{}}` | `\affiliation[1]{organization={...}}` |
| `\abstract{...}` | `\begin{abstract}...\end{abstract}` |
| `\keywords{a, b}` | `\begin{keywords}a \sep b\end{keywords}` |
| `\backmatter` + `\bmhead{}` | starred declaration sections |
| `\botrule` | `\bottomrule` |
| single column | **double column** |

The double-column layout is the only substantive change. `cas-dc` gives about
84 mm per column against roughly 165 mm in `sn-jnl`, so every wide float is
promoted to a starred `table*` / `figure*` that spans both columns. The
generator does this automatically; 17 of 21 floats are promoted, and the four
that are not are genuinely narrow.

## Guide-for-authors conformance

Checked by the generator on every run, and by
`tests/test_elsevier_conversion.py` in CI:

- abstract at most 250 words (currently 235)
- 1 to 7 keywords (currently 6)
- 3 to 5 highlights, each at most 85 characters, in a **separate file**
  (`highlights.tex`) as KBS requires
- numbered `[n]` citations in order of appearance (`elsarticle-num`)
- numbered sections `1` / `1.1` / `1.1.1`, no starred sections in the body
- CRediT authorship contribution statement, using only official taxonomy roles
- declaration of competing interest
- declaration of generative AI use, including the figure-generation disclosure
  Elsevier's GenAI policy asks for
- data availability statement following research-data **Option C**: the derived
  data and code are deposited and linked, and the reason the raw corpora are
  not redistributed is stated
- tables as editable text, no vertical rules or shading
- figures cited in order and supplied as separate files

## Files to upload

| File | Purpose |
|---|---|
| `kbs-article.tex` | manuscript |
| `paper.bib` | bibliography |
| `figures/Fig1-7.png` | artwork, separate files |
| `highlights.tex` | highlights, uploaded as its own item |
| `cas-dc.cls`, `cas-common.sty`, `*.bst` | after `fetch-template.sh` |


## Submission checklist

Verified on the current tree. Re-run `make check` and `make zip` after any edit.

| item | state |
|---|---|
| compiles, pdflatex | 30 pages, 0 errors, 0 undefined refs or citations |
| content within margins | max reach 544pt of 595pt; no page within 15pt of the edge |
| abstract | 214 words (cap 250) |
| keywords | 6 (cap 7) |
| highlights | 5 bullets, longest 78 chars (3-5, cap 85), separate file |
| citations | `elsarticle-num`, numbered `[n]` in order |
| sections | numbered; no starred sections in the body |
| CRediT statement | present, official taxonomy roles only |
| competing interest | present |
| generative AI declaration | present |
| data availability | present, Option C wording |
| code availability | present, public repository |
| bundle | editable sources only; `make zip` fails if build products leak |

### Upload as separate items

1. `signalshap-kbs.zip` (manuscript sources, bibliography, figures)
2. `highlights.tex` content, as the Highlights item
3. `kbs-article.pdf` as the reviewer PDF

### Known, deliberate

- **One overfull hbox of 123.6pt is reported at `\maketitle`.** It is internal
  to the CAS abstract frame and does not reach the page edge; nothing is
  clipped. Three further boxes are under 13pt.
- **`kbs-article.tex` is no longer generated.** `make_elsevier.py` bootstrapped
  it from the Springer source; the text has since been edited directly, so
  `make check` does not re-run the generator. Use `make regen` only for a
  fresh re-port, and expect it to overwrite the submitted text and figures.
- **Table 7 draws one row from two runs.** The Shapley column reproduces the
  estimand table so the two agree; the other columns come from the retirement
  run. Their grand-coalition values differ in the fifth decimal. Kendall tau
  is +0.20 either way, and the caption and `artefacts/PROVENANCE.md` say so.

## Still open before submission

- **No immutable DOI.** Code availability now points at a public repository,
  which addresses the reviewer's stated blocker, but KBS applies research-data
  Option C and that asks for a persistent identifier. A Zenodo or Mendeley
  Data deposit would close it properly; a GitHub URL can move.
- **The public repository is the pre-reorganisation snapshot.** It runs and
  its tests pass, but it predates `environment.yml`, `data_preparation/`,
  `experiments/`, `tables/` and `figures/`. Push the current
  `reproducibility/` contents before submitting, so the cited repository
  matches what the paper describes.
