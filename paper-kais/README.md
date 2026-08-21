# KAIS submission (Knowledge and Information Systems, Springer)

Target journal: *Knowledge and Information Systems* (Springer, journal 10115).

## Why this directory exists

The manuscript has now been formatted for three venues. Only the container
changes; the numbers do not.

| Directory | Journal | Class | Columns | Bibliography |
|---|---|---|---|---|
| `paper/` | Discover AI (Springer) | `sn-jnl` | single | `sn-basic` |
| `paper-kbs/` | Knowledge-Based Systems (Elsevier) | `cas-dc` | double | `elsarticle-num` |
| `paper-kais/` | **Knowledge and Information Systems (Springer)** | `sn-jnl` | single | `sn-basic` |

KAIS asks for the Springer Nature LaTeX template and for reference citations
identified by numbers in square brackets, which is `sn-jnl.cls` with the
`Numbered` option and the `sn-basic` reference style.

## Generated, not hand-edited

`kais-article.tex` is produced by `../scripts/make_kais.py` from
`../paper-kbs/kbs-article.tex`, which is the **latest** manuscript: it carries
every review round including the round-9 revisions, the hand edits, and the
abstract residual correction. The older `paper/sn-article.tex` is deliberately
*not* the source, because it predates those edits.

Edit `paper-kbs/kbs-article.tex` and re-run `make regen`. Do not hand-edit
`kais-article.tex`; `tests/test_kais_port.py` asserts that the two bodies agree
and that re-running the generator is a no-op.

## What the port actually changes

Three things, and only three:

1. **Front matter.** Elsevier's `\ead`, `\credit`, `\cormark`/`\cortext` and
   `\affiliation{organization=...}` become Springer's `\author*[1]{\fnm{}\sur{}}`,
   `\email{}` and `\affil*[1]{\orgdiv{}...}`. `abstract` and `keywords` are
   environments in cas-dc and macros in sn-jnl.

2. **Column count.** cas-dc is two-column with a ~84mm measure, so every wide
   float had been promoted to a starred float spanning both columns. sn-basic is
   single column with a 160mm text block. **18 starred floats are demoted.** This
   is not cosmetic: in a one-column class LaTeX routes a starred float through
   the double-column mechanism, which can defer it to the end of the document or
   drop it outright with `Float(s) lost`.

3. **Back matter.** Elsevier's separate CRediT / competing-interest / data /
   code / ethics / funding headings collapse into Springer's single
   `Declarations` list, and the generative-AI disclosure is rephrased to
   Springer Nature's guidance. The content is carried over unchanged.

The body prose, all tables, the TikZ figure and every number are carried
verbatim.

## Style files

`sn-jnl.cls` and `sn-basic.bst` ship in this directory. Unlike Elsevier's
`cas-dc.cls`, they are LPPL-licensed and redistributable, so there is no
`fetch-template.sh` step here and the bundle is self-contained.

## Build

```sh
make regen   # rebuild from the KBS manuscript
make         # static checks, then pdflatex + bibtex + pdflatex + pdflatex
make zip     # submission bundle
```

`make check` runs `check_latex.py` against this file and `check_paper_numbers.py`
against the artefacts. It does **not** run the generator, so it cannot overwrite
work in progress.

## Before submitting

- [ ] Compile and confirm 0 errors and 0 undefined references. This sandbox has
      no TeX, so the PDF has not been produced here.
- [ ] Update the Code-availability commit hash and create the
      `kais-submission` tag (the text currently names that tag; it does not yet
      exist).
- [ ] KAIS has no Highlights item, unlike KBS. `../paper-kbs/highlights.tex` is
      not part of this submission.
- [ ] Rewrite `../paper-kbs/cover-letter.md` to name KAIS rather than KBS.
