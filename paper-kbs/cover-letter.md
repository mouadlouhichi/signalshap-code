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

**The gap.** A production hybrid recommender combines architecturally distinct
scorers: collaborative filtering, content, popularity, recency, and sequential
signals. Two questions are routinely asked about them and routinely conflated.
*How should the system's measured value be divided among its sources?* is
credit allocation. *What would we lose if we retired one source?* is a removal
effect. Leave-one-out ablation answers the second and is widely used as though
it answered the first, where it fails under redundancy: removing either of two
substitutable sources changes little, so both are assigned near-zero value.

**Contribution.** We recast source attribution as a five-player cooperative
game whose payoff is NDCG@10 on a fixed, coalition-independent candidate set.
Five players give 32 coalitions, so the Shapley value is computed by exhaustive
enumeration on a CPU with no sampling error in the aggregation. The small
player count also makes the method checkable: the known Shapley vectors of six
analytic games are recovered to within 4.4e-16, and a controlled
duplicate-source experiment imposes an exchangeability constraint that any
symmetric allocation must satisfy. Across three timestamped corpora spanning a
36x density range, two contain a source for which the two rules disagree in
sign by a material margin, with ten-seed intervals excluding zero.

**A negative result we lead with.** Having built a Shapley method, we tested
whether its output predicts what retiring a source actually costs, measured end
to end with retrieval rebuilt from the survivors. It does not, and leave-one-out
does better on all three corpora, never worse on any of the thirty fits. We
therefore claim credit
allocation within a declared ranking-stage game, and explicitly not retirement
or investment guidance. The distinction survives a globally causal split and
candidate pools that consult no source score. We also report that
attribution-derived fusion gives no resolvable advantage over a matched global
head, that all three fitted games are non-monotone so the redundancy-positivity
property does not apply as stated, and that only one corpus clears our declared
candidate-recall gate. We make no state-of-the-art claim.

**Fit with the journal.** This is a methodological contribution to
knowledge-driven systems: how a system assembled from heterogeneous knowledge
sources can be audited, and which instrument answers which question about it.
It sits between explainable AI and applied recommender research, and its
practical conclusion is directly usable by practitioners maintaining such
systems.

**Availability.** The implementation, frozen configuration, every artefact
behind a reported number, and the test suite are public at
<https://github.com/mouadlouhichi/signalshap>. The release ships a SHA-256
manifest recording the commit and environment behind each artefact, and a
provenance map from every table and figure to its source. Two limits are stated
precisely in the manuscript rather than in general terms: the raw corpora are
not redistributed because the GroupLens license forbids it, and because ALS and
truncated SVD accumulate in a BLAS-dependent order, a run on a different
backend reproduces every reported sign, ordering and material count but not
every fifth decimal.

**Declarations.** The work is original, is not under consideration elsewhere,
and all authors have approved the submission. We declare no competing interests
and received no funding. The study is a secondary analysis of previously
released, de-identified public datasets and involved no new participant
recruitment. Required declarations, including the use of generative AI in
manuscript preparation, appear in the manuscript.

Thank you for considering our work. We look forward to your assessment.

Sincerely,

Mouad Louhichi, on behalf of all authors
ENSIAS, Mohammed V University in Rabat
