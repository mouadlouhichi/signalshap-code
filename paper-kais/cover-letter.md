Dear Editor,

Please consider our manuscript "Ranking-stage source attribution is not source
removal: exact Shapley analysis of five-source hybrid recommenders" for
*Knowledge and Information Systems*.

Hybrid recommenders combine architecturally distinct sources, but component
worth is still judged almost exclusively by leave-one-out ablation. We show
that ablation and Shapley allocation answer different questions, and that
conflating them can reverse a component-level decision. The paper contributes
(i) a fully specified ranking-stage cooperative game over five sources with
exact enumeration of all 32 coalitions, and (ii) a comparative study on
MovieLens-1M, Amazon Video Games and Gowalla in which ranking-stage
leave-one-out, not Shapley, tracks observed end-to-end single-source removal
cost. On two of the three systems the two rules disagree in sign by a material
margin; on the third they do not, and we report that negative case rather than
generalising past it.

We also measured what exact enumeration buys. Estimating the same values by
permutation sampling at 500 draws leaves a 95th-percentile error larger than
both the seed-to-seed spread and the materiality threshold used throughout, so
exactness is load-bearing for the effects we report rather than a presentational
convenience.

We claim credit allocation under a declared game. We do not claim a new fusion
method: attribution-derived fusion weights gave no resolvable gain over a
global head, and we report that negative result in the supplement. We make no
causal or off-policy claim and no state-of-the-art comparison.

The work sits in the journal's information-systems and knowledge-evaluation
remit, since it changes how hybrid architectures are diagnosed, and it includes
comparative evaluation against leave-one-out, Banzhaf and binomial semivalues.
An Electronic Supplementary Material file contains the proof, the full
configuration, and the robustness suite. All code and derived artefacts are
public, with a SHA-256 manifest tying every reported number to the commit that
produced it.

This manuscript is original, is not under review elsewhere, and is not an
extension of a conference paper. We request the subscription route; no
article-processing-charge funding is available.

Suggested reviewers: [3-5 names working on recommender evaluation, explainable
ranking, or cooperative games in machine learning, excluding close
collaborators.]

Sincerely,

Mouad Louhichi, Redwane Nesmaoui, Mohamed Lazaar
ENSIAS, Mohammed V University in Rabat
mouad_louhichi@um5.ac.ma
