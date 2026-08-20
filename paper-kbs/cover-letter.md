# Cover letter, *Knowledge-Based Systems*

**Manuscript:** SignalShap: Exact-Enumeration Ranking-Stage Attribution of
Sources in Hybrid Recommenders
**Article type:** Research paper
**Corresponding author:** Mouad Louhichi, ENSIAS, Mohammed V University in
Rabat, Rabat, Morocco (mouad_louhichi@um5.ac.ma, ORCID 0000-0002-6849-230X)
**Co-authors:** Redwane Nesmaoui, Mohamed Lazaar

---

Dear Editors,

We submit *SignalShap: Exact-Enumeration Ranking-Stage Attribution of Sources
in Hybrid Recommenders* for consideration as a Research paper in
*Knowledge-Based Systems*.

## The problem

A production hybrid recommender is an ensemble of architecturally distinct
scorers: collaborative filtering, content, popularity, recency, and sequential
signals. Two different questions are routinely asked about them and routinely
conflated. *How should the system's measured value be divided among its
sources?* is credit allocation. *What would we lose if we retired one source?*
is a removal effect. Leave-one-out ablation answers the second. It is widely
used as though it answered the first, and it fails there under redundancy,
because removing either of two substitutable sources changes little and both
are assigned near-zero value.

The natural correction is to reach for the Shapley value. Our results say that
correction is only half right, and we report the half that cuts against us.

## What the paper contributes

We recast source attribution as a five-player cooperative game whose payoff is
NDCG@10 on a fixed, coalition-independent candidate set. Five players give
2^5 = 32 coalitions, so the Shapley value is obtained by exhaustive
enumeration on a CPU, with no sampling error in the aggregation.

The small player count matters twice. It makes the computation exact, and more
importantly it makes the method *checkable*. Six analytic games with known
closed-form solutions are recovered to an efficiency residual of at most
6.9e-18, and a controlled duplicate-source experiment creates an
exchangeability constraint that any symmetric allocation must satisfy.

The empirical core is a conditional comparison of two rules across three
timestamped corpora spanning a 36x density range. On MovieLens-1M and Gowalla
the two rules disagree in **sign** by a material margin: the gap for `cf` on
MovieLens is +0.02030 [+0.02007, +0.02053], 38.8% of v(G), and for `pop` on
Gowalla +0.00207 [+0.00197, +0.00217]. Both intervals exclude zero across ten
stochastic fits. Amazon-VG has no material disagreement, which makes it the
informative negative case: a strong substitutive interaction is not by itself
sufficient to produce a sign flip.

## The result that argues against our own instrument

We think this is the reason the paper is worth reading. Having built a Shapley
method, we tested whether its output predicts what retiring a source actually
costs, measured end to end with retrieval rebuilt from the survivors. **It does
not, and leave-one-out does better on every corpus and every seed:** Kendall
rank agreement 0.96 against 0.20 on MovieLens-1M, 0.96 against 0.74 on
Amazon-VG, 1.00 against 0.80 on Gowalla, with paired differences of +0.76,
+0.22 and +0.20 and Wilcoxon p = 0.0020, 0.0039, 0.0020.

We therefore claim credit allocation within a declared ranking-stage game, and
explicitly **not** retirement or investment guidance. The paper states this in
the abstract, the contributions, and the conclusion rather than leaving it for
a reader to infer.

Two further checks were run because they could have overturned the finding.
Under a globally causal split, where no training event postdates any evaluated
event, the per-source attributions do *not* replicate, and we say so; but the
allocation-versus-removal disagreement does (0.80 against 0.60, with
leave-one-out identifying the genuinely cheapest source while the allocation
does not). Rebuilding the game on candidate pools that consult no source score
preserves both material flips, so the phenomenon is not an artefact of letting
the players choose the candidates.

## Negative and limiting results we report rather than omit

- Attribution-derived fusion weights show **no** resolvable advantage over a
  matched globally tuned head. The measured difference changed sign between
  candidate-truncation rules, which is itself the argument that no advantage
  exists. This is Appendix A, presented as a negative result, not a
  contribution.
- All three fitted games are **non-monotone**, so the redundancy-positivity
  property does not apply as stated. We publish a counterexample showing the
  property is false without monotonicity, and audit the condition rather than
  assume it.
- Only MovieLens-1M clears our declared 0.60 candidate-recall gate under the
  frozen configuration. On Gowalla the gate is unreachable at **any** pool
  size: 49.9% of evaluated users have a test venue already in their training
  history, so the training mask caps recall at 0.501 by construction. That
  ceiling was confirmed independently when an oracle candidate pool returned
  recall of exactly 1.000, 0.972 and 0.501 on the three corpora.
- We make no state-of-the-art claim. LightGCN and SASRec appear as contextual
  references and received smaller tuning budgets than a performance comparison
  would require.

## Fit with the journal

The work is a methodological contribution to knowledge-based and
knowledge-driven systems: how a system assembled from heterogeneous knowledge
sources can be audited, and which instrument answers which question about it.
It sits between explainable AI and applied recommender research, both within
the journal's scope, and the practical conclusion, that the standard tool is
the right one for retirement decisions while a game-theoretic allocation
answers a different question, is directly usable by practitioners maintaining
such systems.

## Reproducibility

The implementation, the frozen configuration, every artefact behind a reported
number, and the test suite are publicly available at
<https://github.com/mouadlouhichi/signalshap>. The release ships
`MANIFEST.json`, recording a SHA-256 for each artefact together with the commit
and environment that produced it including the BLAS backend, and
`PROVENANCE.md`, which maps every table and figure to the artefact, platform,
candidate rule and seeds behind it.

We state one residual limitation precisely rather than in general terms. The
raw corpora are not redistributed, because the GroupLens license forbids it, so
reproduction from data requires refetching them with the supplied scripts.
Independently, ALS and truncated SVD accumulate in an order set by the BLAS, so
a run on a different backend reproduces every reported sign, ordering and
material count, but not every fifth decimal. We disclose this in the manuscript
rather than presenting bitwise determinism we cannot deliver.

## Declarations

The work is original, is not under consideration elsewhere, and all authors
have approved the submission. We declare no competing interests and received no
funding. Use of a large language model for editorial review and consistency
checking is disclosed in the manuscript; all mathematical claims were verified
independently, and the central counterexample is machine-checked. The study is
a secondary analysis of previously released, de-identified public datasets and
involved no new participant recruitment.

## Suggested reviewers

We have no conflicts with, and no prior collaboration with, researchers working
on Shapley-based attribution for ranking and recommendation. We would welcome
reviewers from that community, and from applied recommender systems, given the
paper's emphasis on which estimand supports which decision.

Thank you for considering our manuscript. We look forward to your assessment.

Sincerely,

Mouad Louhichi, on behalf of all authors
ENSIAS, Mohammed V University in Rabat
