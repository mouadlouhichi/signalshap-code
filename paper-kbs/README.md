# Knowledge-Based Systems submission

Elsevier CAS double-column version of the manuscript, targeting
[Knowledge-Based Systems](https://www.sciencedirect.com/journal/knowledge-based-systems).

## This file is generated

`kbs-article.tex` is produced from `../paper/sn-article.tex` by
`../scripts/make_elsevier.py`. **Do not edit it by hand.** The Springer file
stays the source of truth for prose and numbers, because
`scripts/check_paper_numbers.py` validates that file against `artefacts/`. A
hand-forked Elsevier copy would drift from the data within one revision and
nothing would catch it. `tests/test_elsevier_conversion.py` fails if the two
diverge.

```bash
python scripts/make_elsevier.py        # regenerate after editing the source
```

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

## Still open before submission

- **No immutable DOI.** The data-availability statement points at a GitHub
  repository and a hashed manifest, not a permanent archive. KBS applies
  research-data Option C, so a Zenodo or Mendeley Data deposit would satisfy
  it cleanly.
- The submission tag still reads `discover-ai-submission` in the repository;
  retag before submitting.
