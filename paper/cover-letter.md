# Cover letter — *Discover Artificial Intelligence*

**Manuscript:** SignalShap: Exact Ranking-Stage Attribution of Sources in Hybrid Recommenders
**Article type:** Research
**Corresponding author:** Mouad Louhichi, ENSIAS, Mohammed V University in Rabat

---

Dear Editors,

We submit *SignalShap: Exact Ranking-Stage Attribution of Sources in Hybrid
Recommenders* for consideration as a Research article.

**Context.** Production recommender systems combine several architecturally
distinct scorers — collaborative filtering, content, popularity, recency, and
sequential signals — and teams routinely decide which to invest in or retire.
Those decisions rest on leave-one-out ablation, which measures what is lost
when a component is removed from the complete system. That is the right
quantity only when components contribute independently, and real hybrids do
not: implicit-feedback matrix factorisation is strongly popularity-driven, so
overlapping components can each appear worthless when removed alone.

**Contribution.** We recast the problem as a five-player cooperative game whose
payoff is a fixed-candidate NDCG@10 on a coalition-independent candidate set.
The small player count matters twice over. It makes the Shapley value exactly
enumerable over all 32 coalitions, avoiding the sampling error that
feature-level attribution must accept. More importantly, it makes the method
*checkable*: we inject a controlled duplicate of a real source, which makes the
pair exchangeable and therefore fixes a constraint the attribution must satisfy
regardless of the data. SignalShap meets it to numerical precision on all four
corpora, alongside efficiency to $6.9\times10^{-18}$.

**Why this journal.** The work sits at the intersection of explainable AI and
applied machine learning, addressing how AI systems assembled from multiple
components can be audited — a methodological question within the journal's
scope and of practical interest to practitioners building such systems.

**What we claim, and what we do not.** We are deliberate about scope. The
duplicate experiment verifies symmetry and efficiency on real fitted games; it
does not establish that the absolute magnitudes are the uniquely correct
engineering credit, and we say so in the abstract, the validation section, and
the threats-to-validity section. We report three findings that went against
our expectations: the fitted game is non-monotone on three of four corpora, so
our own Property 2 does not formally apply there; segment-adaptive fusion does
not separate from a well-tuned global head; and on three corpora the temporal
players operate on an ordering with no temporal meaning, making their
attributions uninterpretable rather than merely small. An earlier draft
described the latter as "lower bounds", which was unjustified and is withdrawn.
We also show by counterexample that Shapley credit is *not* conserved under
player replication, correcting a claim we had previously made.

**Reproducibility.** Code, frozen configuration, cached score matrices, and
every JSON backing a reported number are available at
<https://github.com/mouadlouhichi/signalshap-code>. The repository provides one
command per table and figure, and a test suite covering the efficiency,
symmetry, monotonicity, and leakage-freedom invariants. An archived release
with a DOI will be deposited at acceptance.

**Declarations.** The work is original, is not under consideration elsewhere,
and all authors have approved the submission. We declare no competing
interests. Use of large language models for code scaffolding and editorial
review is disclosed in the manuscript; all mathematical claims were
independently verified and the central counterexample is machine-checked.

We look forward to your assessment.

Sincerely,
Mouad Louhichi, on behalf of all authors
