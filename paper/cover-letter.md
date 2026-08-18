# Cover letter — *Discover Artificial Intelligence*

**Manuscript:** SignalShap: Exact Ranking-Stage Attribution of Sources in Hybrid Recommenders
**Article type:** Research
**Corresponding author:** Mouad Louhichi, ENSIAS, Mohammed V University in Rabat

---

Dear Editors,

We submit *SignalShap: Exact Ranking-Stage Attribution of Sources in Hybrid
Recommenders* for consideration as a Research article.

**Context.** Production recommender systems combine architecturally distinct
scorers—collaborative filtering, content, popularity, recency, and sequential
signals. Leave-one-out ablation measures the effect of removing one source from
the deployed system, even when sources interact. It is not, however, a complete
rule for dividing the system's measured value among overlapping components.
The manuscript distinguishes this removal estimand from Shapley credit
allocation rather than treating either as universally superior.

**Contribution.** We recast the problem as a five-player cooperative game whose
payoff is a fixed-candidate NDCG@10 on a coalition-independent candidate set.
The small player count matters twice over. It makes the Shapley value exactly
enumerable over all 32 coalitions, avoiding the sampling error that
feature-level attribution must accept. More importantly, it makes the method
*checkable*: six analytic games verify the exact aggregation, and a controlled
duplicate-source experiment on MovieLens creates an exchangeability constraint
that any symmetric allocation must satisfy. SignalShap meets that constraint
to numerical precision, alongside efficiency residuals no larger than
$6.9\times10^{-18}$ across the three reported corpora.

**Why this journal.** The work sits at the intersection of explainable AI and
applied machine learning, addressing how AI systems assembled from multiple
components can be audited — a methodological question within the journal's
scope and of practical interest to practitioners building such systems.

**What we claim, and what we do not.** The invariant checks verify the
implementation of the Shapley aggregation; they do not establish a unique
ground-truth allocation for the real systems. All three fitted games are
non-monotone, so the manuscript audits rather than assumes the monotonicity
condition used in its redundancy result. Across ten stochastic training runs
per corpus, ranking-stage leave-one-out tracks observed end-to-end retirement
cost more closely than ranking-stage Shapley. We therefore claim Shapley credit
allocation only under the declared game, not retirement or investment guidance.
Segment-derived fusion shows no resolvable advantage over a matched global
head. Two corpora fail the declared candidate-recall gate and are restricted to
relative contrasts.

**Reproducibility.** The implementation is public at
<https://github.com/mouadlouhichi/signalshap-code>. The existing
`discover-ai-submission` tag predates the revised ten-seed tables and is not
presented as their exact archive. Before submission, we will create a new
immutable tag containing the final manuscript, complete configuration, cached
score matrices, table/figure manifest, tests, and every JSON backing a reported
number; the strict number checker must pass against that tag.

**Declarations.** The work is original, is not under consideration elsewhere,
and all authors have approved the submission. We declare no competing
interests. Use of large language models for code scaffolding and editorial
review is disclosed in the manuscript; all mathematical claims were
independently verified and the central counterexample is machine-checked.

We look forward to your assessment.

Sincerely,
Mouad Louhichi, on behalf of all authors
