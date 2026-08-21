# Response to reviewers, Knowledge-Based Systems

We thank the reviewers. Every critical item is addressed below. The decisive
question, C1, was investigated numerically before responding, and the answer
determines that this is a labelling issue rather than a computation error.

## C1. Table 11 / Table 12 Shapley mismatch: provenance, not error

We reproduced the discrepancy and traced it. The two tables draw the same
quantity from two different runs:

| | Table 11 (estimands) | Table 12 (retirement) |
|---|---|---|
| artefact | `e11_estimands_ml_1m.json` | `e12_retirement_ml_1m.json` |
| v(G) | 0.051364 | 0.051689 |
| efficiency residual | 6.9e-18 | 0.0 |

Both runs satisfy efficiency exactly **against their own v(G)**, so neither is
miscomputed. They differ because each rebuilds candidates independently, which
moves v(G) in the fifth decimal.

The `ct` sign change is 9e-05 against 2e-05. Both are an order of magnitude
below the 1e-3 materiality threshold the paper declares for monotonicity and
applies to sign flips, and `ct` is reported as an immaterial flip in both. We
verified that no conclusion depends on the choice: both columns give Kendall
tau = +0.20 against the observed loss, the same source ordering
(seq > cf > pop > rec > ct), and the same smallest-loss source.

Fix applied: Table 11 rows are now labelled directly, "refitted head*" for the
final source-symmetric rule and "fixed head†" / "end-to-end†" for the legacy
rule, with a footnote stating that the legacy rows are an ordering sensitivity
and are not artefact-matched. Table 12's caption states which artefact supplies
each column, gives both v(G) values, and records that tau is +0.20 either way.
Table 10 gains an estimand-comparison provenance row.

## C2 to C12

- **C2** Cross-reference corrected to "the 0.05136 seed-42 main-game value
  underlying the refitted-head row of Table 11."
- **C3** The conclusion now separates the two corpora: Amazon-VG clears the gate
  at N_max = 1200, whereas Gowalla's recall is bounded by rho = 0.501 < 0.60, so
  the gate is unattainable at any pool size and a repeat-aware protocol, not a
  larger cap, is what that corpus needs. The "not an impossibility" wording is
  removed.
- **C4** Notation separated: lambda_ALS for ALS regularisation, rho for the
  retrievability ceiling only, gamma_shrink for fusion shrinkage. All three, plus
  phi, LOO and lambda, are now in the notation table.
- **C5** Verified: Eq. (14) is complete in the submitted source, including the
  final -v(S u {b}) + v(S) terms.
- **C6** Addressed with C1.
- **C7** Duplicate injection now given as a numbered equation, with sigma_g
  defined as one scalar per source over eligible entries before z-normalisation,
  epsilon i.i.d. per (user, item), eta = 0 giving an exact clone, and the
  statement that candidates are built before injection and held fixed so the
  clone never enters retrieval. This matches the released implementation.
- **C8** Restored: the per-seed gap aggregation note and the "Gap sign"
  definition in Table 8; the Holm column in Table 13; blocked-time and
  neutral-pool rows in Table 9; the estimand row in Table 10.
- **C9** Abstract now states that Amazon-VG clears the gate in the larger-cap
  sensitivity and that Gowalla is a relative stress test bounded by rho = 0.501.
  Still 233 words.
- **C10** Figure 6 caption states that no pairwise segment contrast survives
  within-corpus Holm correction.
- **C11** Commit hash and tag added to Code availability, cross-referenced to
  the hash recorded in MANIFEST.json.
- **C12** Recency clustering corrected to "a separate 2,000-vocabulary TF-IDF
  item matrix", verified against the implementation, which fits its own
  vectoriser independently of ct's 5,000-term matrix.

## High-priority items

Applied: H2 (exactness qualified as aggregation conditional on the fitted
characteristic function, naming the dependencies), H3 (lambda/|U_fit| reported
per corpus: 1.66e-4, 1.40e-4, 1.13e-4), H4 (pseudoinverse truncation tolerance
declared), H5 (growth termination and single-build matrix reuse stated),
H6 (complexity corrected to O(mnN log(nN))), H10 (Holm-adjusted p = 0.0059
restored).

Already scoped in the submitted text, and left as such: H9 and H11. The paper
states that seed intervals describe training randomness on fixed datasets and
are "not calibrated population intervals", and explicitly does not claim
per-user seed stability.

Deferred with reasons: H7, H8, H12 to H16 require new runs. H8 in particular,
a repeat-aware Gowalla protocol, is now named in the conclusion as the required
next step for that corpus rather than presented as a solved point.

## Editorial

Applied: "prespecified implementation settings" for Table 3; Amazon-VG recall
reconciled to 0.589 against the artefact (0.5889); 12.2% retained with the
unrounded ratio 0.1216 shown, since 12.1595% rounds to 12.2 rather than 12.1;
"cheapest source to retire" replaced throughout by "source with the smallest
observed removal loss"; the per-user identity numbered as Eq. (13); the
counterexample test file named.
