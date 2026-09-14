# Editorial Manager: "Provide additional information"

Answers for the KNOSYS submission form. Every factual claim here is checked
against the repository; the two that are **not yet true** are flagged as
blockers and must be fixed before you fill the form in.

---

## 1. Your research data

### Do you want to share data?

**Yes.**

The manuscript already carries a Data-availability and a Code-availability
section, so answering "No" here would contradict the paper. Saying yes also
answers the KBS reproducibility expectation directly.

### Link to data repository

```
https://github.com/mouadlouhichi/signalshap
```

> **BLOCKER.** This link is published verbatim in the article and editors do
> follow it. The public repository is currently at commit `ea8ae5d`, pushed
> **21 August 2026**. It does not contain `artefacts/fig2_ndcg_sampling.json`,
> `artefacts/attribution_baselines.json` or `artefacts/reviewer_q1_q3.json`,
> which are the artefacts behind Figure 8 and the whole of Section 4.5. A
> reviewer clicking this link today cannot reproduce the sampling-error figure
> or the attribution-rule comparison.
>
> Push the current state before you submit.

If you would rather mint a DOI, a Zenodo release is preferable to a bare
GitHub URL: `.zenodo.json` is already in the repository root and is ready to
drive the record. Connect the repo on Zenodo, cut the release, and paste the
Zenodo DOI URL here instead. A DOI is archival; a GitHub URL is not, and some
editors mark the latter down.

### Repository name

```
GitHub
```

(or `Zenodo` if you take the DOI route above.)

### Source of data

**Original data.**

This is not a claim that the corpora are ours. They are not: MovieLens-1M,
Gowalla check-ins from SNAP, and the Video Games category of Amazon Reviews
2023 are all public third-party benchmarks, all cited, none redistributed.

The form is not asking where your *inputs* came from. It is asking about the
thing at the end of the link you just pasted. That link does not point at the
corpora. It points at `artefacts/`: 59 files, 2.0 MB, containing the
32-coalition value lattices, the ten-seed retirement runs, the analytic
validation suite, `MANIFEST.json` with a SHA-256 and producing commit per
file, and `PROVENANCE.md` mapping every table and figure to the artefact,
platform, candidate rule and seeds behind it. None of that existed before this
study. It is the output of our experiments and it is what validates the
reported findings, which is Elsevier's own definition of research data
("results of observations or experimentation that validate research
findings", explicitly including software, code and algorithms).

So: public inputs, original outputs. "Reference data" on this form means you
are pointing at somebody else's dataset that your article merely supports or
reuses. If you selected that, you would be telling the editor that the link
leads to a redistributed copy of MovieLens, and the first reviewer to click it
would find something else entirely.

Using public benchmark corpora is also completely standard in this field and
is not a weakness. It is why the results are checkable at all. The corpora are
handled the correct way already: cited in the reference list, with fetch
scripts rather than copies.

One caveat worth knowing. Some authors read "original" as "raw, unprocessed"
rather than "produced by us"; the term is genuinely overloaded and Elsevier
does not define it on the form. Under that alternative reading the answer
would flip. It does not change the recommendation, because under either
reading "reference data" describes the corpora you are *not* sharing, and the
Data-availability section in the manuscript already spells the whole situation
out in prose, which is what an editor actually reads.

### Title of the data set

```
SignalShap: exact 32-coalition attribution artefacts for three recommender corpora
```

82 characters, within the 200 limit. It names the unit of analysis (the
coalition lattice), the scale (32, so exact), and the scope (three corpora).

---

## 2. Free Preprint Service (SSRN)

**Recommendation: NO.**

This is a judgement call and you may reasonably differ, so here is the actual
trade-off rather than a bare answer.

The case against, which I think decides it: **the KAIS submission.** If that
is still open, posting to SSRN while a second journal holds the manuscript
turns a withdrawal problem into a public, timestamped, DOI-bearing record of
a dual submission. `SUBMIT.md` already flags withdrawing from KAIS as a
must-do. Do not add a preprint DOI to that situation. Elsevier states the
preprint decision has no effect on the editorial outcome, and that is true of
the *editorial* process; it is not true of the dual-submission question.

Secondary: SSRN posts at desk-review pass, which is exactly the gate this
paper failed once already at KAIS on comparative-baseline grounds. A public
version that the editor then desk-rejects is a permanent artefact.

The case for: early DOI, early citations, and the work is already public in
the repository, so little is being withheld.

If KAIS is formally withdrawn, with written confirmation in hand, and you want
the early DOI, switching to YES is defensible. Otherwise no.

---

## 3. Manuscript subject area

KBS's editor-assignment list varies; pick in this order of preference,
whichever appears:

1. **Recommender systems**: the exact unit of analysis; every experiment is a
   hybrid recommender.
2. **Explainable AI / Interpretability**: the contribution is an attribution
   method and its failure mode.
3. **Machine learning**: safe fallback.

Prefer a recommender-systems option over an explainability one if both are
offered. The paper's contribution is a negative result about *which estimand*
answers a system-level question, and that lands with a recommender-systems
editor. A pure XAI editor is more likely to route it to reviewers who read it
as a Shapley-approximation paper, which it is not: the point is that exact
Shapley still does not answer the removal question.

Avoid "Data mining" and "Knowledge representation" if the above are present.

---

## Other portal fields

These are already settled in `SUBMIT.md` and are repeated here so the form can
be filled in one pass:

- **Article type:** Full Length Article.
- **Open access:** decline; subscription route. No APC funding was declared.
- **Suggested reviewers:** four in `suggested-reviewers.md`. Conflict-check
  each and confirm affiliations are current before entering them.
- **Declarations:** copy CRediT, competing interests, funding, ethics, data
  availability and the generative-AI statement from the manuscript verbatim.
  Elsevier publishes the portal text, so the two must match.

---

## Blockers, consolidated

| # | Blocker | Why it matters |
|---|---|---|
| 1 | Public repo is 3 weeks stale and missing three artefacts | The data link in the article resolves to a state that cannot reproduce Figure 8 or Section 4.5 |
| 2 | Tag `kbs-submission` points at the stale commit | Code availability names this tag. It exists, but resolves to `ea8ae5d` (21 August), which predates Figure 8 and Section 4.5 |
| 3 | KAIS not confirmed withdrawn | Decides the SSRN answer, and dual submission is an automatic reject at both venues |
| 4 | Nothing has been compiled | No TeX in the development environment; every LaTeX check is static |

Blockers 1 and 2 are the same push:

```sh
# from the signalshap-code checkout, against the public repo
git push public HEAD:main
git tag -f -a kbs-submission -m "KBS submission"
git push --force-with-lease public kbs-submission
```

Then re-verify that `artefacts/fig2_ndcg_sampling.json` is visible on the
public repo at that tag before pasting the link into the form.
