# KBS submission (Knowledge-Based Systems, Elsevier)

**Generated from the KAIS manuscript. Do not hand-edit.**

## Source of truth

`paper-kais/main.tex` holds the prose and the numbers for both submissions.
`scripts/make_kbs_from_kais.py` re-targets it at `elsarticle`. Edit the KAIS
file and run:

```sh
python3 scripts/make_kbs_from_kais.py
```

This replaces the hand-maintained copy that used to live in
`signalshap__submission.zip`. That copy had already drifted: it was built from
an earlier KAIS revision and was stale on the introduction, the verification
section, the discussion, the retirement table and the abstract, while still
reporting the same headline numbers. Generating removes that failure mode.

## What the generator changes, and nothing else

| | KAIS (`sn-jnl`) | KBS (`elsarticle`) |
|---|---|---|
| Front matter | `\author*[1]{\fnm{}\sur{}}`, `\affil*`, `\abstract{}` | `frontmatter`, `\ead`, `\cortext`, `abstract` env |
| Columns | single, 160mm | **two**, ~84mm per column |
| Wide floats | plain `table`/`figure` | **starred**, spanning both columns (10 of them) |
| Fourth level | `\subsubsection` | `\paragraph` (17 converted) |
| Back matter | one `Declarations` list | separate CRediT / competing interest / data / code / AI headings |
| Highlights | not used | `highlights.txt`, its own upload item |
| Supplement title | "Online Resource 1" | "Supplementary Material" |

The body is otherwise byte-identical after normalisation, and the numeric
token streams match exactly. The single permitted numeric difference is the
`0.7` in `width=0.7\textwidth` for Fig. 3, which becomes `\columnwidth`; that
is a layout parameter, not a result.

`tests/test_kbs_kais_sync.py` (13 tests) enforces all of the above.

## Files

- `main.tex`, `paper.bib`, `elsarticle.cls`, `elsarticle-num.bst`
- `figures/` (Fig1, Fig3, Fig8)
- `supplementary-material.tex`
- `highlights.txt`, five bullets, all under 85 characters
- `cover-letter.tex`
- `suggested-reviewers.md`
- `reproducibility/` Figure 2 reconstruction script and stored lattice

## Before submitting

- [ ] Compile `main.tex` and `supplementary-material.tex`. **No TeX in this
      sandbox, so neither PDF has been produced here.** The two-column recast
      has not been visually checked; the wide floats are the thing to look at.
- [ ] Confirm the Code-availability tag `kbs-submission-v2` exists and the
      commit in `MANIFEST.json` reproduces Figure 2.
- [ ] **Do not submit this and the KAIS version at the same time.** They are
      the same manuscript. Pick one venue; withdraw before submitting to the
      other.
