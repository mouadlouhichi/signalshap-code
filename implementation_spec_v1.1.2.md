# SignalShap — Implementation Specification (v1.1.2, Q1-Ready, Post-Fix-Review)

> **SUPERSEDED.** This file is revision history for `v1.1.2` only. The authoritative specification is **`SignalShap_Implementation_Spec.md`**. Do not build, cite, or edit from this document.

**Target journal:** *Discover Artificial Intelligence* (Springer Nature — open access, CiteScore 6.0, Q1 in Artificial Intelligence). *SJR value to be re-verified against the live Scimago page immediately before submission (see §17).*
**Article type:** Research article.
**Working title:** *Game Theory Meets Recommendation: Exact Shapley Credit Assignment over Collaborative, Content, and Contextual Signals*.
**Authors:** Mouad Louhichi¹\*, Redwane Nesmaoui¹, Mohamed Lazaar¹.
**Affiliation:** ¹National Higher School of Computer Science and Systems Analysis (ENSIAS), Mohammed V University in Rabat, Morocco.
**Corresponding author:** mouad_louhichi@um5.ac.ma.
**Companion prior work:** *Game Theory Meets Explainable AI* (IJACSA 2025) — SignalShap is its direct methodological successor at the architectural-source granularity.

> **Version 1.1.2 changelog.** Nine patches from the v1.1.1 technical review. One is a **correctness fix, not a clarification**: Property 2 as stated in v1.1.1 is **false** — exact redundancy plus $v(\{g_1\})>0$ does *not* imply $\varphi_{g_1}>0$, and a three-player counterexample satisfying every hypothesis yields $\varphi_{g_1}=\varphi_{g_2}=-0.4167$ (see §5 and `tests/test_property2_counterexample.py`). Property 2 now carries an explicit **monotonicity** hypothesis, discharged empirically by a new monotonicity audit (E0-b). Critically, the coalition-conditional ridge refit of §4 is *itself* the mechanism most likely to break monotonicity, so §4 and §5 are now coupled and must be read together. The other eight patches: (ii) **frozen-$\lambda$ protocol** — $\lambda$ is no longer tuned per coalition (that was optimistic bias growing with $|S|$, not mere noise); (iii) **per-dataset $N_{\max}$ pre-registered** in Week 1, since the recall gate previously had no viable remediation path; (iv) $v(\varnothing)=0$ derived exactly from a frozen permutation, plus a note that $\varphi_g$ is invariant to $v_0$ altogether; (v) **T5 is now full-catalog for every method**, so SignalShap-Fuse's recall ceiling is a visible cost rather than a hidden denominator advantage; (vi) expected pop–cf and rec–ct redundancy **pre-registered in §10** as a hypothesis RQ2 tests, not a discovery; (vii) $C_u$ **truncation rule** pinned; (viii) candidate recall reported **per cell** in T8; (ix) Holm–Bonferroni family-composition disclosure. Timeline extended to **nine weeks** — now a floor, not a comfortable estimate.

> **Version 1.1.1 changelog.** Two residual-gap patches applied after peer review of v1.1: (i) §4 now specifies an explicit *procedure* for building the union-of-top-N-per-source candidate set (rather than only naming the $|C_u|\le 200$ target), so per-user candidate size is reproducible from the config alone; (ii) **candidate recall** is now a first-class precondition metric — reported in T2 and re-stated at the top of §4 of the paper as the ceiling on every ranking metric that follows. Nothing else in v1.1 changes.

> **Version 1.1 changelog.** This revision incorporates the seven Section-A conflicts, seven Section-B spec issues, four Section-C provenance warnings, and the priority-ordered action list from `SignalShap_Review_of_Fixes.md`. The most consequential correction is the candidate-generation protocol in §4 (was: grand-coalition-only, which biases every sub-coalition against the grand coalition; now: union-of-top-N-per-source, which gives every coalition an identical, coalition-independent candidate set). Framing has also been de-escalated where v1.0 implied theoretical novelty for what are in fact restatements of standard Shapley axioms.

> **Selection status.** This document is the authoritative build, experiment, writing, and submission plan chosen after a comparative review of four candidate blueprints (ActionShap, FairShap, MHyperShap, SignalShap). SignalShap was selected because it maximizes the probability of first-round acceptance at *Discover AI* under the constraints of (a) low compute, (b) exact — not sampled — Shapley values, (c) full independence from the DyHuCoG codebase (which contains 63 documented reproducibility gaps and is therefore not safe to inherit), and (d) natural continuity with the authors' IJACSA 2025 line of work.

---

## 0. Selection Rationale (Why SignalShap over the Other Three)

| Criterion | ActionShap | FairShap | MHyperShap | **SignalShap** |
|---|---|---|---|---|
| Codebase status | Only a gate notebook | Depends on DyHuCoG (63 gaps) | Blueprint only, must build SynAgentBench | **Independent, standard components** |
| Shapley computation | Monte Carlo, 250–500 permutations/user | Monte Carlo estimator | Monte Carlo (M=50) | **Exact — 32 coalitions, closed form** |
| Reviewer attack surface | Large | Medium | Very large | **Minimal** |
| Formal claims | Empirical hypotheses only | 1 light proposition | Uniqueness theorem + convergence proposition | **3 restated Shapley properties + 1 remark** |
| Compute required | GPU + retraining | Single RTX 4090 | RTX 4090 + LLM inference | **Shapley on laptop CPU; base scorers on modest GPU (once)** |
| Author domain fit | Recommender XAI (fit) | Fits, but depends on DyHuCoG | Zero prior LLM/agent publications | **Natural IJACSA extension** |
| Time to submission | 6+ months | ~3 months | 6+ months | **8 weeks** |
| Overall acceptance risk | High | Medium | Very high | **Low** |

**Verdict.** SignalShap is the only candidate that is simultaneously (i) reviewer-hard-to-attack, (ii) executable end-to-end with the Shapley game running on a laptop CPU, (iii) independent of a codebase the team has audited and found unsafe, and (iv) a natural continuation of the authors' published IJACSA 2025 line.

---

## 1. Refinements Applied vs. the Original SignalShap Blueprint (updated for v1.1)

1. **Three datasets** (ML-1M + Amazon-Book + LastFM-2K) — retire Amazon-Beauty from the analysis-doc lineage; density-contrast narrative re-derived against Amazon-Book's ~0.05 % density.
2. **Candidate generation is now union-of-top-N-per-source** (see §4). This replaces v1.0's grand-coalition-only design, which biased every sub-coalition against the grand coalition.
3. **Base scorers frozen to: ALS ($cf$), TF-IDF ($ct$), popularity-with-decay ($pop$), recency ($rec$), item2vec ($seq$).** SASRec demoted to an Appendix-B robustness variant to preserve the low-compute Shapley-on-CPU story.
4. **Fusion mechanism** is ridge-regularized linear head, with a Week-3 smoke test against a pairwise-logistic ranker to confirm stability of Shapley shares.
5. **Explicit positioning against feature-level XAI** (SHAP, LIME, IG) in §2 and §5 of the paper.
6. **Zenodo-archived, DOI-tagged reproducibility artefact** committed before submission (mandatory under *Discover AI* Data Availability policy).
7. **Statistical protocol tightened** (see §12): Wilcoxon signed-rank is the primary paired-NDCG test; within-user permutation is the primary LOO–Shapley-gap test; paired *t* and bootstrap CIs are demoted to Appendix-B robustness tables; Holm–Bonferroni family sizes declared per table.
8. **Five-part robustness matrix** (candidate size, seed, monotone rescaling, cold-user fallback, per-source noise) plus a **regenerated-candidates ablation** now in Appendix B.
9. **Framing corrections** — Prop 1/2/3 are relabelled *Formal Properties*, framed as restatements of standard Shapley axioms in the source-attribution setting; "review-proof" language removed everywhere; "zero additional inference cost" narrowed to "negligible ($O(1)$ segment lookup)"; "laptop CPU" narrowed to the Shapley computation itself.
10. **Ethics + LLM disclosures** — Data Availability Statement names licenses explicitly for each dataset; LLM-usage disclosure block present.
11. **AI-generated ideation is quarantined** — the parallel Deep Analysis document is a Genspark brainstorming artefact and must never be cited or allowed to leak structure into the paper (see §21).
12. **Candidate-set construction pinned as an explicit procedure** (§4) rather than a target size, and **candidate recall reported as a precondition** in T2 and at the top of §4 of the paper (both added in v1.1.1).
13. **Property 2 corrected** (v1.1.2) — the v1.1.1 statement is false without monotonicity; the hypothesis is now explicit and audited empirically (§5, E0-b).
14. **Estimation error in $v$ acknowledged as first-class** (v1.1.2) — $\lambda$ frozen, $v(S)$ seed-variance propagated into main-text $\varphi_g$ CIs, monotonicity violations counted and reported (§4, §5, §12).
15. **Evaluation protocol unified to full catalog** (v1.1.2) — T5 no longer compares a candidate-restricted method against full-catalog baselines (§8).

---

## 2. One-Paragraph Thesis

Hybrid recommender systems fuse several architecturally distinct signals — collaborative filtering, content, popularity, recency, and sequential order — but current practice attributes system quality to these signals with leave-one-out (LOO) ablation, which provably fails whenever two signals are redundant. We recast source attribution as a five-player cooperative game with fixed-candidate NDCG@10 as its characteristic function. Because the player set has size five, the Shapley value is computed *exactly* over $2^5=32$ coalitions on a laptop CPU in seconds; there is no sampling error. We formally restate three standard Shapley properties in the source-attribution setting (exact additive decomposition, LOO redundancy collapse, and free per-user decomposition) and show empirically on MovieLens-1M, Amazon-Book, and LastFM-2K that Shapley shares differ from LOO shares in the direction and magnitude predicted by the redundancy geometry of each dataset. We then close the loop with **SignalShap-Fuse**, a segment-adaptive fusion whose weights are tuned per Shapley-derived user segment and which improves NDCG@10 at negligible ($O(1)$ segment-lookup) additional inference cost.

---

## 3. Contributions

- **C1 — Source-level cooperative game.** A hybrid-recommendation cooperative game whose players are architectural signal sources, whose characteristic function is a fixed-candidate NDCG@10 on a coalition-independent candidate set, and whose small player set admits exact Shapley computation.
- **C2 — Formal restatement of three standard Shapley properties** in the source-attribution setting, plus a scale-invariance remark. The mathematical content of these properties is not novel; the contribution is their careful instantiation for hybrid-signal games and their use to *predict* and *empirically falsify* LOO behaviour.
- **C3 — Empirical falsification of LOO under redundancy** on three benchmarks of contrasting density (dense movies, sparse books, medium music).
- **C4 — Segment heterogeneity mapping.** Shapley-derived per-user attributions aggregated into behavioural segments (heavy / cold, dense / sparse history, recency-driven / stability-driven), with a permutation test for heterogeneity.
- **C5 — SignalShap-Fuse.** A closed-loop, segment-adaptive fusion mechanism whose weights come from segment-level Shapley profiles and which improves NDCG@10 at negligible ($O(1)$ segment-lookup) additional inference cost.
- **C6 — Fully reproducible artefact.** Zenodo-archived code, cached score matrices, dataset-license notice, and configuration files.

---

## 4. Cooperative Game Definition (v1.1.2 — coalition-independent candidates, frozen $\lambda$)

Let $\mathcal{G}=\{cf,ct,pop,rec,seq\}$ be the five signal sources.

**Candidate set $C_u$ (coalition-independent).** For each user $u$ and each source $g$, take the top-$N_g$ items under that single source's scorer. Set

$$
C_u \;=\; \bigcup_{g\in\mathcal{G}} \text{top-}N_g^{(g)}(u),\qquad |C_u|\le N_{\max}^{(d)},
$$

where $N_{\max}^{(d)}$ is **pre-registered per dataset** (see below), so that every coalition $S\subseteq\mathcal{G}$ scores exactly the same items and differences in $v(S)$ reflect fusion within $S$, not retrieval from a coalition-favoring pool. The v1.0 alternative (candidates drawn once from the grand-coalition scorer) is retained as **Appendix-B ablation "regenerated candidates"** because it systematically inflates $v(\mathcal{G})$ relative to $v(S)$ for $S\subsetneq\mathcal{G}$.

**Pre-registered $N_{\max}^{(d)}$ (new in v1.1.2, Fix R2).** v1.1.1 fixed $N_{\max}=200$ for all datasets *and* imposed a hard CI gate at mean candidate recall $\ge 0.60$ (§21). Those two rules are jointly unsatisfiable on a sparse catalogue: with $\approx 90{,}000$ items at $\approx 0.05\,\%$ density, recall@200 on Amazon-Book is realistically $0.10$–$0.25$, and the only remediation v1.1.1 offered — "re-tune the top-$N_g$ growth schedule" — **cannot manufacture recall that the base scorers' own top-lists do not contain**. The growth loop redistributes budget between sources; it does not create it.

The alternative remedy (restrict evaluation to users with $\text{test}_u\in C_u$) is **rejected**: it would restrict the user population *differentially by density*, over-representing easy users precisely on the sparse datasets, which confounds the density-contrast narrative that C3 rests on.

Therefore $N_{\max}^{(d)}$ is pre-registered per dataset **in Week 1, before any attribution number is computed**:

| Dataset | Catalogue size | Pre-registered $N_{\max}^{(d)}$ |
|---|---|---|
| MovieLens-1M | $\approx 3{,}706$ | $200$ |
| LastFM-2K | $\approx 17{,}632$ | $500$ |
| Amazon-Book | $\approx 90{,}000$ | $1{,}000$ |

**Fallback ladder if Amazon-Book fails the gate even at $N_{\max}=1000$ (new in v1.1.2).** Raising $N_{\max}$ is the first remedy but it is not unbounded: candidate-set size enters the per-coalition scoring cost linearly, so a pool large enough to rescue recall on a $90{,}000$-item catalogue could begin to erode the laptop-CPU claim for that dataset. The escalation order is therefore fixed in advance, and each rung is preferred to the one below it:

1. **Raise $N_{\max}$ to 2000.** Still tractable; report the wall-clock cost honestly in T4 and re-verify the §6 compute claim holds. Cheap, no narrative change.
2. **Tighten the corpus, not the pool.** Apply a standard $k$-core filter ($k=5$ or $k=10$) to Amazon-Book, shrinking the catalogue rather than growing the candidate set. This is common practice in the recommendation literature, is disclosable in one sentence, and improves recall by removing items no scorer could rank anyway. **Preferred over rungs 3–4.**
3. **Accept a low ceiling and report it as a finding.** A sparse-catalogue dataset where union-of-top-$N$ retrieval cannot reach $0.60$ is itself informative about the limits of the fixed-candidate game. Report attribution *conditional on* the stated ceiling, state the limitation in §5, and drop Amazon-Book from any absolute-NDCG comparison against LightGCN while retaining it for the *relative* LOO-vs-Shapley contrast — which is the claim C3 actually needs, and which is far less sensitive to the ceiling than absolute ranking quality.
4. **Substitute the dataset.** Swap Amazon-Book for the preprocessed Gowalla split already held in reserve (§18), and document the swap and its reason in the artefact.

Rung 4 is a last resort because the density-contrast narrative (dense movies / sparse books / medium music) is part of C3. Rung 3 preserves that narrative at the cost of a weaker absolute claim, which is the better trade. **The chosen rung is recorded in the artefact with its date, the recall numbers that triggered it, and the compute cost.**

These values are frozen in `configs/` at the end of Week 1 and may not be changed after E1 begins. The cost of the larger pools (more items to score per coalition) is linear in $|C_u|$ and remains trivially within the laptop-CPU budget, since the 32 coalitions reuse cached score matrices. T4 reports wall-clock per dataset so the trade is visible.

**Construction procedure for $C_u$ (pinned in Week 1).** Because overlap between sources is user-dependent, the target $|C_u|\le N_{\max}^{(d)}$ is reached by a deterministic proportional-growth loop, not a global constant $N_g$:

1. Set $N_g^{(0)} = \lceil N_{\max}^{(d)} / |\mathcal{G}|\rceil$ for every source.
2. Materialise $C_u^{(0)} \;=\; \bigcup_{g} \text{top-}N_g^{(0)}(u)$; if $|C_u^{(0)}| \ge N_{\max}^{(d)}$ (no overlap), go to step 6.
3. Otherwise let $\Delta = N_{\max}^{(d)} - |C_u^{(0)}|$ and grow every $N_g$ by $\lceil \Delta / |\mathcal{G}|\rceil$; re-materialise the union.
4. Iterate step 3, capping $N_g$ at each source's catalogue-size limit, until either $|C_u| \ge N_{\max}^{(d)}$ or every $N_g$ is capped (i.e., no source has more items to offer). Cap the total loop at $10$ iterations for determinism.
5. Break ties inside every $\text{top-}N_g^{(g)}(u)$ by `(score, timestamp, original_record_index)` so the union is identical across seeds.
6. **Truncation rule (new in v1.1.2, Fix R7).** The union can *overshoot* $N_{\max}^{(d)}$, because step 3 grows all five $N_g$ simultaneously and the newly admitted items may not overlap. When $|C_u| > N_{\max}^{(d)}$, truncate deterministically by sorting the union on the key `(best per-source rank of the item across g ∈ 𝒢, source order as listed in 𝒢, original_record_index)` ascending, and keeping the first $N_{\max}^{(d)}$. All three key components are seed-independent, so the truncated $C_u$ is reproducible. Without this rule the Week-1 unit test asserting identical $C_u$ across seeds passes while $|C_u|$ silently diverges from the config — the test checks *stability*, not *conformance to $N_{\max}$*, so both assertions are required.

Under this procedure, $|C_u|$ can be *below* $N_{\max}^{(d)}$ for tiny users whose source top-lists are exhausted before the union grows, but after step 6 it can never exceed $N_{\max}^{(d)}$ and it never depends on which coalition is being evaluated. The empirical distribution of $|C_u|$ across users is reported per dataset in T2. The full loop is implemented in `src/signalshap/candidates/` and covered by three unit tests: identical $C_u$ across all $2^5$ coalition contexts, identical $C_u$ across the five seeds, and $|C_u|\le N_{\max}^{(d)}$ for every user.

**Fusion score.** For each coalition $S$,

$$
\hat s_{u,i}(S) \;=\; \sum_{g\in S} w_g^{(S)}\, z_{u,g,i},
$$

where $z_{u,g,i}$ is the per-user, per-source z-normalised raw score of source $g$ for item $i\in C_u$, and $\{w_g^{(S)}\}_{g\in S}$ is a ridge-regularized linear head refit on the validation fold *conditioned on the coalition* $S$. A pairwise-logistic head is trained in parallel as a Week-3 smoke test; the primary results use ridge iff Shapley-share orderings are stable across both.

**Frozen $\lambda$ protocol (new in v1.1.2, Fix R1b).** The ridge penalty $\lambda$ is **chosen once and frozen across all 32 coalitions, all users, all segments, and all datasets**. It is *not* tuned per coalition. Rationale: tuning $\lambda$ on the same validation fold used to evaluate $v(S)$ is not a variance problem, it is **optimistic bias that grows with $|S|$** — larger coalitions have more weights to fit and therefore more opportunity to overfit the held-out interaction. That would systematically inflate $v(\mathcal{G})$ relative to small coalitions, producing a bias in the same direction as, but mechanically independent of, the grand-coalition candidate bias already fixed in v1.1. Left unaddressed it would silently re-introduce the exact pathology v1.1 was cut to remove.

A nested split (fit weights on one slice, tune $\lambda$ on another, evaluate on test) is **rejected** as the remedy: under leave-last-out there is a single validation interaction per user, which is not meaningfully splittable further. Instead:

1. $\lambda$ is fixed to a single value chosen in Week 3 on a **pilot dataset** (ML-1M validation fold, grand coalition only), documented with the selection curve in Appendix B.
2. That value is written into `configs/` and frozen before E1.
3. Sensitivity is reported, not tuned: E5 adds a $\lambda\in\{0.1,1,10\}$ sweep (E5-vi) confirming that Shapley-share *orderings* are stable across an order of magnitude either side of the frozen value.

**Estimation error in $v$ (new in v1.1.2, Fix R1a).** Because $w^{(S)}$ is *fitted*, each $v(S)$ is an estimate, not a fixed number. The paper must not let "exact Shapley" imply "error-free attribution": exactness is a property of the **aggregation** (the closed-form 32-coalition sum has no sampling error), not of the **inputs**. The honest formulation, to be used verbatim in the abstract and §3, is *"the Shapley value is computed exactly given the fitted characteristic function."* Accordingly:

- Per-coalition $v(S)$ variance across the five seeds is reported in Appendix B.
- $\varphi_g$ is reported with seed-based CIs **in the main text** (T6, F2), not relegated to Appendix B as in v1.1.1. See §12.
- Monotonicity violations induced by the refit are counted and reported — see the audit in §5 and E0-b, which is the precondition for Property 2 being applicable at all.

**Characteristic function.**

$$
v(S) \;=\; \frac{1}{|\mathcal{U}|}\sum_{u\in\mathcal{U}}\mathrm{NDCG@10}\bigl(\text{rank}_i\hat s_{u,i}(S)\,;\,\text{test}_u\cap C_u\bigr) \;-\; v_0,
$$

with $v(\varnothing)=0$ pinned by construction (baseline $v_0$ = NDCG@10 of a fixed random ranker over $C_u$).

**Precise reading of $v(\varnothing)=0$ (clarified in v1.1.2, Fix R3).** "Fixed" means **one frozen permutation $\pi_u$ of $C_u$, drawn once under seed 42 and reused for every coalition, every user, and every experiment** — not a fresh random draw whose expectation is taken. Under that reading the empty-coalition ranking is *defined* as $\pi_u$ itself (no scores exist to rank by), so per user $\mathrm{NDCG@10}(\pi_u) - v_0(u) = 0$ **exactly**, not approximately-in-expectation. This matters twice over: Property 1 is the one claim mechanically unit-tested to floating-point tolerance in Week 1, and Property 3 requires $v(\varnothing)=0$ to hold **per user**, not merely on the mean. The frozen permutation is serialised in the artefact.

**$\varphi_g$ is invariant to $v_0$.** Every marginal contribution $v(S\cup\{g\})-v(S)$ cancels the offset, so the Shapley values do not depend on $v_0$ at all. Its only function is cosmetic — it lets Property 1 read $\sum_g\varphi_g=v(\mathcal{G})$ instead of $\sum_g\varphi_g=v(\mathcal{G})-v(\varnothing)$. **§3 of the paper must say this explicitly**, so the random-ranker baseline is not presented as a substantive modelling choice; a reviewer who works out that it is cosmetic will otherwise start auditing what else in the construction is decorative.

**Exact Shapley.**

$$
\varphi_g \;=\; \sum_{S\subseteq\mathcal{G}\setminus\{g\}}\frac{|S|!\,(|\mathcal{G}|-|S|-1)!}{|\mathcal{G}|!}\bigl[v(S\cup\{g\})-v(S)\bigr],
$$

a closed-form sum over $2^5=32$ coalitions.

---

## 5. Formal Properties (Restatements)

These are direct instantiations of standard Shapley axioms in the source-attribution setting. They are *not* claimed as new theorems; they are stated here so the paper can reason about LOO failure precisely.

- **Property 1 (Efficiency / additive decomposition).** $\sum_{g\in\mathcal{G}}\varphi_g = v(\mathcal{G})$. *Instantiation.* Direct from Shapley efficiency for $(\mathcal{G},v)$ with $v(\varnothing)=0$.
- **Property 2 (LOO redundancy collapse) — CORRECTED in v1.1.2.** *Let $v$ be **monotone***, i.e. $v(S\cup\{g\})\ge v(S)$ for every $S\subseteq\mathcal{G}$ and every $g\notin S$. If two sources $g_1,g_2$ satisfy $v(S\cup\{g_1\})=v(S\cup\{g_2\})=v(S\cup\{g_1,g_2\})$ for every $S\subseteq\mathcal{G}\setminus\{g_1,g_2\}$, then $\mathrm{LOO}(g_1)=\mathrm{LOO}(g_2)=0$ while $\varphi_{g_1}=\varphi_{g_2}\ \ge\ v(\{g_1\})/|\mathcal{G}|\ >\ 0$ whenever $v(\{g_1\})>0$. *Instantiation.* LOO collapse follows from the LOO definition plus the redundancy hypothesis; equality $\varphi_{g_1}=\varphi_{g_2}$ follows from Shapley symmetry; the strict lower bound follows from monotonicity via the permutation-average form of the Shapley value, in which the ordering placing $g_1$ first contributes $v(\{g_1\})$ with weight $1/|\mathcal{G}|$ and every remaining ordering contributes a non-negative marginal.

  > **Why the monotonicity hypothesis is not optional.** The v1.1.1 statement of Property 2 omitted it and is **false as written**. Counterexample on three players, satisfying the redundancy hypothesis exactly with $v(\{g_1\})=1>0$:
  >
  > | $S$ | $\varnothing$ | $g_1$ | $g_2$ | $g_3$ | $g_1g_2$ | $g_1g_3$ | $g_2g_3$ | $g_1g_2g_3$ |
  > |---|---|---|---|---|---|---|---|---|
  > | $v(S)$ | $0$ | $1.0$ | $1.0$ | $5.0$ | $1.0$ | $0.5$ | $0.5$ | $0.5$ |
  >
  > Redundancy holds ($1.0=1.0=1.0$ at $S=\varnothing$; $0.5=0.5=0.5$ at $S=\{g_3\}$), $\mathrm{LOO}(g_1)=\mathrm{LOO}(g_2)=0$ as predicted, symmetry and efficiency both hold — and yet the exact Shapley values are $\varphi_{g_1}=\varphi_{g_2}=\mathbf{-0.4167}$, $\varphi_{g_3}=+1.3333$, summing to $0.5=v(\mathcal{G})$. The redundant sources receive **negative** credit despite positive standalone value. Redundancy alone is therefore compatible with $\varphi<0$; the positivity clause needs monotonicity as a separate structural assumption. This counterexample is pinned in CI as `tests/test_property2_counterexample.py`.
  >
  > **This couples §5 to §4.** The coalition-conditional ridge refit is precisely the mechanism that can break monotonicity — a head refit on $S\cup\{g\}$ may score worse than the head refit on $S$ (regularisation, validation overfit on a single held-out interaction). So the refit is not merely a variance problem for Property 1's confidence intervals; it is the plausible route by which Property 2's hypothesis fails on real data. The two sections must be read and fixed together.

  **Monotonicity audit (E0-b, precondition).** Monotonicity is an *assumption to be discharged empirically*, never asserted. For each dataset and seed, check all $|\mathcal{G}|\cdot 2^{|\mathcal{G}|-1}=80$ pairs $(S,g)$ with $g\notin S$ for $v(S\cup\{g\})\ge v(S)$. Report the violation count, the maximum violation magnitude, and which sources are involved, in T2 alongside candidate recall. If violations are non-trivial, that is **a finding to report in §4 of the paper, not a defect to hide**: it would mean the fitted hybrid game is genuinely non-monotone, Property 2 does not apply as stated, and any negative $\varphi_g$ must be interpreted as real rather than as numerical error.
- **Property 3 (Free per-user decomposition).** $\varphi_g=\frac{1}{|\mathcal{U}|}\sum_u\varphi_g(u)$. *Instantiation.* Linearity of the Shapley operator applied to a per-user mean characteristic function.
- **Lemma 1 ($\varepsilon$-redundancy) — new in v1.1.2, Fix R4.** Exact redundancy is a measure-zero condition that will never hold on real data, so Property 2 can motivate E2 but can never be *instantiated* by it. Lemma 1 supplies the approximate version that E2 actually tests, and it necessarily has **two separate parts under two separate assumptions** — the counterexample above is exactly the reason the second part cannot be derived from redundancy alone:
  - **(i) LOO collapse.** If $g_1,g_2$ are $\varepsilon$-redundant, i.e. $|v(S\cup\{g_1\})-v(S\cup\{g_1,g_2\})|\le\varepsilon$ for all $S\subseteq\mathcal{G}\setminus\{g_1,g_2\}$, then $|\mathrm{LOO}(g_2)|\le\varepsilon$. Immediate from the definition of LOO.
  - **(ii) Shapley floor.** If **additionally** $v$ is monotone and $v(\{g_1\})\ge c$, then $\varphi_{g_1}\ \ge\ c/|\mathcal{G}| - O(\varepsilon)$. Requires the permutation-averaging argument, and requires monotonicity — it does **not** follow from $\varepsilon$-redundancy.

  Together: the LOO–Shapley gap for an $\varepsilon$-redundant pair is at least $c/|\mathcal{G}| - O(\varepsilon)$. E2's empirical correlation between Kendall $\tau$ redundancy and the observed gap is then a **predicted consequence of a stated bound**, not a loose analogy. Monotonicity may be weakened to bounded synergy ($v(S\cup\{g\})-v(S)\ge-\delta$) at the cost of an additive $\delta$ term in (ii); use whichever the E0-b audit supports. Budget: a short lemma with two cases and an Appendix-A subsection — roughly half a day, not "two lines."

- **Remark 1 (Affine scale invariance).** Per-user z-normalisation makes $\varphi_g$ invariant under any user- and source-specific affine map $z\mapsto az+b$. Invariance does *not* extend to nonlinear monotone maps; this is verified empirically in §11-E5(iii).

Full derivations are in Appendix A, which also reproduces the Property-2 counterexample table so the necessity of the monotonicity hypothesis is on the record rather than implied.

---

## 6. Player Instantiation (Base Scorers — v1.1)

Each source is a well-documented, off-the-shelf recommender. Nothing is invented here.

| ID | Source | Concrete base model | Rationale (v1.1) |
|---|---|---|---|
| $cf$ | Collaborative filtering | **ALS** matrix factorization (implicit-feedback), 64 factors | Deterministic, closed-form updates, no learning-rate tuning, ~seconds on CPU per dataset. Justified over BPR-MF in §3 of the paper. |
| $ct$ | Content-based | TF-IDF cosine over item metadata (genres, titles, authors, tags) | No embedding drift; fully reproducible from raw files. |
| $pop$ | Popularity | Global item-frequency scorer with time decay $\tau$ | Cheap baseline sanity signal; also a stress-test player for redundancy against $cf$. |
| $rec$ | Recency | Exponential recency of the user's most recent interaction with an item's content cluster | Contextual, cheap. |
| $seq$ | Sequential | **item2vec** next-item scorer (Word2vec-style, skip-gram over interaction sequences) | Preserves the CPU-friendly Shapley narrative. **SASRec is relegated to Appendix-B robustness** so the Shapley story does not depend on Transformer training. |

Each scorer is trained *once* on the train split; its per-user score matrix is materialised and cached in `parquet`. Every coalition reuses cached matrices. The 32 refits are ridge heads over already-materialised score tensors and complete in seconds on a laptop CPU.

**Compute-claim scope (per Fix B4).** The Shapley computation itself — the 32-coalition sweep, per-user attribution, statistical tests, and SignalShap-Fuse — runs on a laptop CPU in seconds per dataset. Training the base scorers (especially item2vec) and the reference baselines (LightGCN, plus SASRec in the appendix) uses a single consumer GPU for a few minutes each, one time only.

---

## 7. Datasets (Three, All Public)

| Dataset | Domain | Users | Items | Density | Split | License / Terms of Use |
|---|---|---|---|---|---|---|
| MovieLens-1M | Movies | 6 040 | 3 706 | ≈ 4.5 % | Leave-last-out temporal | GroupLens research-use license (research and educational use, redistribution with attribution) |
| Amazon-Book (2018) | Books | ≈ 50 000 subsampled from the 2018 raw corpus | ≈ 90 000 | ≈ 0.05 % | Leave-last-out temporal | Amazon Reviews Dataset (Ni et al., 2019), academic use permitted per the dataset host's conditions |
| LastFM-2K | Music | 1 892 | 17 632 | ≈ 0.28 % | Leave-last-out temporal | HetRec 2011 / GroupLens redistribution, non-commercial research use |

Splits: user's last interaction → test, second-to-last → validation, remainder → train. All timestamp ties resolved deterministically by `(timestamp, original_record_index)`. All raw files, subsampling scripts, subsampling seed, and split manifests are shipped in the Zenodo artefact.

---

## 8. Baselines

**Attribution baselines.**

- Leave-one-out (LOO) on $\mathcal{G}$ — the industry default and the target of Property 2.
- Forward stepwise selection over $\mathcal{G}$.
- Permutation importance over $\mathcal{G}$.
- Monte-Carlo Shapley at matched budget — to demonstrate that exact Shapley is not merely correct but *cheaper* at equal accuracy in this player-count regime.

**Recommender baselines.**

- Each individual source in isolation.
- Uniform-weight fusion.
- Globally-tuned fusion (single weight vector for all users).
- LightGCN (reference, GPU-trained once).
- SASRec (reference, GPU-trained once, results reported in Appendix B).

**Evaluation protocol — full catalog for every method (new in v1.1.2, Fix R5).** v1.1.1 left unstated whether LightGCN and SASRec rank within $C_u$ or over the full catalogue (their standard protocol). This is not a detail: if SignalShap-Fuse's NDCG@10 is capped by candidate recall while a baseline ranks the full catalogue, the two T5 numbers are not measuring the same quantity, and the comparison differs by the **denominator**, not by the fusion mechanism.

**Resolution: T5 reports full-catalog NDCG@10 / Recall@20 / MRR@10 for every method, including SignalShap-Fuse.** SignalShap-Fuse assigns score $-\infty$ to every item outside $C_u$, so items missed by candidate generation are scored as misses rather than excluded from the denominator. Consequences, all intended:

- The candidate-recall ceiling becomes a **visible, quantified cost of the method**, consistent with E0's stated purpose, instead of a hidden advantage.
- E0's recall number and T5's headline number are finally on the same scale and can be read against each other.
- The alternative — restricting LightGCN to $C_u$ — is **rejected**. It is disclosable but it is also simply a weaker experiment: it handicaps a strong baseline by confining it to a pool built from five *other* scorers' top-lists, and invites the reviewer to ask what the unhandicapped number was.

The characteristic function $v(S)$ remains **fixed-candidate within $C_u$** — that is required for coalition-independence and is the game's definition. Only the *reporting* protocol in T5 is full-catalog. §3 and T5's caption must state this two-protocol split explicitly, with the reason.

---

## 9. Metrics

- **Ranking quality.** NDCG@10 (primary — this is the characteristic function), Recall@20, MRR@10.
- **Coverage / diversity.** Catalogue coverage, intra-list diversity, Gini of item exposure.
- **Attribution-specific.** LOO share, Shapley share, LOO–Shapley gap, redundancy indicator (Kendall $\tau$ between per-user source score vectors), segment-level Shapley heterogeneity.
- **Statistics.** See §12 for the primary/secondary test hierarchy.

---

## 10. Research Questions

- **RQ1.** Does casting hybrid recommendation as a five-player cooperative game with fixed, coalition-independent-candidate NDCG@10 as the characteristic function permit an *exact* additive decomposition of the ranking-quality uplift?
- **RQ2.** Does source-level Shapley attribution differ from LOO attribution, and is the difference explained by empirically observed redundancy between sources?

  > **Pre-registered redundancy expectation (new in v1.1.2, Fix R6).** Two of the five players overlap **by construction**, and this is declared here as a prior rather than reported later as a discovery. (a) $pop$ and $cf$: ALS on implicit feedback is strongly popularity-driven, so $pop$–$cf$ redundancy is partly baked in by scorer choice. (b) $rec$ and $ct$: recency is defined over an item's *content cluster* (§6), so it is partly a $ct$ derivative and the two are not fully architecturally distinct. We therefore **predict** high Kendall $\tau$ and large LOO–Shapley gaps for both pairs, and RQ2 tests whether Shapley *recovers* this known structure correctly — a validation of the estimator against a ground truth we can argue for independently, not a finding about the datasets. Real deployed hybrids exhibit exactly this kind of overlap, so we do not redesign the players to remove it; we disclose it. Without this pre-registration the headline result is open to the charge of circularity: redundancy "discovered" that the player definitions guaranteed. §5 of the paper restates this when interpreting F4.
- **RQ3.** Is source attribution homogeneous across users, or does the global attribution conceal opposing segment-level attributions (heavy vs. cold, dense vs. sparse, recency-driven vs. stability-driven)?
- **RQ4.** Can segment-adaptive fusion (SignalShap-Fuse) turn Shapley attribution into a measurable NDCG@10 improvement over globally-tuned fusion at negligible ($O(1)$ segment-lookup) additional inference cost?

---

## 11. Experimental Plan

- **E0-a — Candidate-set diagnostics (precondition to every downstream number).** For every dataset, report the empirical distribution of $|C_u|$ and **candidate recall** ($\Pr[\text{test}_u\in C_u]$) at the pre-registered $N_{\max}^{(d)}$. Any test user with $\text{test}_u\notin C_u$ contributes zero to NDCG@10 by construction, so candidate recall is the ceiling on all E1–E4 metrics and is stated at the top of §4 of the paper and in T2. **Run this on Amazon-Book first, in Week 1, before any other code is written** — it is the single fact most likely to invalidate the plan and it is roughly a day of work.
- **E0-b — Monotonicity audit (precondition to Property 2).** For every dataset and seed, check all $80$ pairs $(S,g)$, $g\notin S$, for $v(S\cup\{g\})\ge v(S)$. Report violation count, maximum violation magnitude, and the sources involved (T2). Property 2 and Lemma 1(ii) are only applicable where this audit passes; where it does not, negative $\varphi_g$ are reported as substantive results and §5 of the paper says so. See §5.
- **E1 — Source share by dataset (→ RQ1).** Compute $\varphi_g$ for every $g\in\mathcal{G}$ on all three datasets. **Report seed-based CIs in the main text** (T6, F2), promoted from Appendix B in v1.1.2 because $v$ is a fitted estimate (§4): Properties 1–3 are properties of the game, not verified facts about the data, so main-text $\varphi_g$ must carry its estimation error. Bootstrap CIs remain a secondary cross-check in Appendix B. Verify $\sum_g\varphi_g=v(\mathcal{G})$ to floating-point tolerance — note this holds *exactly* regardless of fit noise, since efficiency is structural.
- **E2 — LOO vs Shapley scatter (→ RQ2).** For every $(dataset, source)$ pair, report LOO share, Shapley share, and the gap. Compute Kendall $\tau$ between per-user source score vectors of every $(g_1,g_2)$ pair to quantify redundancy; correlate redundancy with the LOO–Shapley gap. **Primary test: within-user permutation test on the gap (10 000 shuffles).**
- **E3 — Segment heterogeneity (→ RQ3).** Partition users into segments by activity quantile and by recency skew. Compute segment-level Shapley shares. **Primary test: between-segment permutation (10 000 shuffles);** report Cohen's $d_z$.
- **E4 — SignalShap-Fuse (→ RQ4).** For each segment learn a fusion weight vector on validation, evaluate on test. Compare against uniform, globally-tuned, LightGCN, and (Appendix B) SASRec. **Primary test: Wilcoxon signed-rank on paired per-user NDCG@10; Holm–Bonferroni correction over the declared family of 4 comparisons per dataset (uniform, globally-tuned, LightGCN, SASRec-appendix).**
- **E5 — Robustness matrix (6 stress tests).** (i) $|C_u|\in\{0.5,1,2\}\times N_{\max}^{(d)}$ — **candidate recall must be reported per cell** (Fix R8), because changing $|C_u|$ changes the recall ceiling and hence the level of $v$; without the recall column the cells are not comparable to each other and the "robustness" reads as noise around a moving baseline; (ii) five seeds $\{42,43,44,45,46\}$; (iii) monotone rescalings (identity, log1p, rank-transform); (iv) cold-user fallback ($z_{u,g,i}=0$); (v) per-source Gaussian noise injection; (vi) **$\lambda\in\{0.1,1,10\}$ around the frozen value** (new in v1.1.2) — confirms Shapley-share orderings survive an order of magnitude either side. This is reported as sensitivity, never used to select $\lambda$.
- **E6 — Ablation.** Drop each source in turn from the game; report the redistribution of Shapley values over the remaining four.
- **E7 — Actionability case study.** Identify the lowest-Shapley source per dataset. Recompute NDCG@10 with that scorer disabled at deployment. Quantify the engineering saving and the (statistically non-significant) NDCG delta.
- **E8 — Appendix-B ablations.** (a) Regenerated-candidates (v1.0 grand-coalition candidate design) — quantifies the bias avoided by §4's fix. (b) SASRec-as-$seq$ replacement — confirms Shapley-share ordering under a Transformer sequential player. (c) Pairwise-logistic vs ridge fusion — Week-3 smoke test carried into the appendix.

---

## 12. Statistical Protocol (v1.1)

- **Unit of analysis.** The user, always.
- **Seeds.** $\{42, 43, 44, 45, 46\}$. All figures / tables report mean ± std across seeds.
- **Primary tests.**
  - Paired NDCG@10 comparisons (E4 and any recommender-vs-recommender claim): **Wilcoxon signed-rank**.
  - LOO–Shapley gap (E2): **within-user permutation test, 10 000 shuffles**.
  - Segment heterogeneity (E3): **between-segment permutation, 10 000 shuffles**.
- **Effect sizes.** Cohen's $d_z$ reported alongside every Wilcoxon result.
- **Multiplicity.** Holm–Bonferroni. **Family size *and composition* declared at the top of every table** (Fix R9, strengthened in v1.1.2). For T7 the family is $m=4$ per dataset and comprises uniform, globally-tuned, LightGCN, and SASRec — **the last of which is reported in Appendix B**. Mixing a main-text family with an appendix member is defensible (the family is the set of comparisons made, wherever printed) but must be stated once in T7's caption, or the family size looks chosen after the fact. Corrected $p$ values are what appears in the paper; raw $p$ values live in Appendix B.
- **Secondary tests (Appendix B).** Paired-$t$ for symmetry cross-checks; bootstrap 95 % CIs (10 000 resamples) for graphical intervals; sensitivity of Wilcoxon to ties.
- **Reporting rule.** Every statistical claim in the paper is traceable to a JSON in `artefacts/` that carries the raw test statistic, corrected $p$, effect size, family size, and seed manifest.

---

## 13. Paper Structure (six sections, Springer *Discover AI* research-article format, ≈ 8 500 words)

- **§1 Introduction** (≈ 900 w.) — motivation, source-attribution gap, one-paragraph thesis, contributions C1–C6, an explicit "what is *not* in this paper" paragraph (GNN players, Transformer players, causal attribution → future work).
- **§2 Literature Review** (≈ 1 400 w.) — hybrid recommenders; feature-level XAI (SHAP, LIME, IG) and why source-level Shapley is a different game; ablation practice; cooperative-game applications in ML; DyHuCoG cited only as motivation.
- **§3 Methodology** (≈ 2 200 w.) — cooperative-game formalism, coalition-independent candidate design (§4), base-scorer catalogue with ALS-vs-BPR-MF and item2vec-vs-SASRec justifications, Properties 1–3 and Remark 1 with derivations, SignalShap-Fuse algorithm.
- **§4 Experimental Results** (≈ 2 400 w.) — opens with **E0 candidate-set diagnostics** (candidate recall + $|C_u|$ distribution per dataset) as the ceiling that bounds every subsequent metric; then E1–E7 with figures F1–F7 and tables T1–T8.
- **§5 Discussion** (≈ 900 w.) — actionable interpretability, engineering implications, positioning against SHAP/LIME/IG.
- **§6 Conclusion & Future Work** (≈ 400 w.) — one paragraph covering privacy-bearing signals (demographic), feature-combination and cascade hybrids, GNN/Transformer players, causal-attribution extension.

Plus: abstract (≤ 250 w.), keywords (5–7), Declarations, References (DOIs), Appendix A (full derivations of Properties 1–3), Appendix B (regenerated-candidates ablation, SASRec results, pairwise-logistic fusion, secondary statistics, per-dataset hyperparameters).

---

## 14. Figures and Tables (final list)

**Figures (7).**
- **F1.** SignalShap workflow (five sources → 32 coalitions with coalition-independent candidates → exact Shapley → segment-adaptive fusion).
- **F2.** Per-source Shapley share bars, three datasets side by side.
- **F3.** LOO vs Shapley scatter, all sources, all datasets, with permutation-test $p$ overlaid.
- **F4.** Redundancy heatmap (Kendall $\tau$ between per-user source score vectors).
- **F5.** Segment-heterogeneity radar plots (four segments × five sources).
- **F6.** SignalShap-Fuse gain curve vs $\lambda$, and NDCG@10 lift over globally-tuned fusion.
- **F7.** Robustness matrix small-multiples grid.

**Tables (8).**
- **T1.** Positioning against SHAP, LIME, IG, DyHuCoG, LightGCN, SASRec (differentiation table).
- **T2.** Dataset statistics + split manifest + license/terms-of-use column + pre-registered $N_{\max}^{(d)}$ + **candidate recall** (fraction of true test items inside $C_u$) and $|C_u|$ mean $\pm$ std + **monotonicity-violation count and max magnitude (E0-b)**, reported per dataset — the recall column is the ceiling on every ranking metric in T5–T7, and the monotonicity column is the precondition for Property 2; both must be inspected before any attribution number is interpreted.
- **T3.** Notation.
- **T4.** Per-source computational cost (train once + cache).
- **T5.** Main NDCG@10 / Recall@20 / MRR results. **Caption must state: all methods evaluated full-catalog; SignalShap-Fuse scores items outside $C_u$ as $-\infty$, so its candidate-recall ceiling is included in the reported number** (Fix R5). Note the two-protocol split: $v(S)$ is fixed-candidate by definition of the game, T5 reporting is full-catalog.
- **T6.** LOO share vs Shapley share per (dataset, source), **with main-text seed-based CIs on $\varphi_g$** (Fix R1a).
- **T7.** SignalShap-Fuse vs baselines with Wilcoxon $p$ (Holm–Bonferroni corrected) and Cohen's $d_z$. **Caption declares family size *and composition*: $m=4$ = {uniform, globally-tuned, LightGCN, SASRec(App. B)}** (Fix R9).
- **T8.** Robustness matrix summary, **with a candidate-recall column per cell** for the $|C_u|$ sweep (Fix R8).

---

## 15. Code, Data, and Reproducibility Artefact

- **Repository.** Public GitHub `signalshap`, MIT license, created at submission.
- **Cached score matrices.** Every base scorer's per-user score matrix cached to `parquet`.
- **DOI archive.** Zenodo snapshot at submission, cited in the Data Availability Statement with its DOI.
- **Docker image.** CPU image for the Shapley game; GPU image for one-time base-scorer training.
- **One-command reproduction.** `make reproduce` from raw data to every figure/table in ≤ 60 minutes on a modern laptop (Shapley step) plus a one-time GPU pass for base scorers.
- **Determinism.** All seeds pinned; deterministic tie-breaking by `(timestamp, original_record_index)`.

---

## 16. Repository Layout

```
signalshap/
├── README.md
├── pyproject.toml
├── poetry.lock
├── Dockerfile.cpu               # Shapley game, statistics, figures
├── Dockerfile.gpu               # one-time base-scorer training
├── Makefile                     # `make reproduce`, `make figs`, `make tables`
├── LICENSE                      # MIT
├── CITATION.cff                 # points to Zenodo DOI
├── data/
│   ├── raw/                     # download scripts only
│   └── processed/               # cached splits, cached score matrices
├── src/signalshap/
│   ├── data/                    # loaders, temporal split, tie-breaking
│   ├── scorers/                 # als, tfidf, popularity, recency, item2vec
│   ├── candidates/              # union-of-top-N-per-source
│   ├── fusion/                  # ridge + segment-adaptive + pairwise-logistic (appendix)
│   ├── game/                    # coalitions, characteristic function, exact Shapley
│   ├── attribution/             # LOO, forward, permutation, MC Shapley
│   ├── segments/                # segment definitions + permutation test
│   ├── stats/                   # Wilcoxon, permutation, Holm–Bonferroni, dz, bootstrap
│   └── plots/                   # matplotlib for F1–F7
├── configs/                     # one YAML per experiment × dataset
│   ├── frozen.yaml              # N_max per dataset, frozen lambda, v_0 permutation seed
│   ├── e1_source_share.yaml
│   ├── e2_loo_vs_shapley.yaml
│   ├── e3_segments.yaml
│   ├── e4_signalshap_fuse.yaml
│   ├── e5_robustness.yaml
│   ├── e6_ablation.yaml
│   ├── e7_actionability.yaml
│   └── e8_appendix_b.yaml       # regen-candidates, SASRec, pairwise-logistic
├── tests/
│   ├── test_property2_counterexample.py   # pins the monotonicity hypothesis (v1.1.2)
│   ├── test_candidates_invariance.py      # identical C_u across 2^5 coalitions + 5 seeds + |C_u| <= N_max
│   └── test_efficiency.py                 # Property 1 to floating-point tolerance
├── artefacts/                   # figures, tables, JSON results
└── paper/                       # LaTeX sources + Springer template
```

---

## 17. *Discover AI* Submission Checklist (Springer 2025 policy)

- [x] Word doc or LaTeX source (Springer LaTeX template).
- [x] Abstract ≤ 250 words.
- [x] Consistent font, 12 pt Helvetica / Arial.
- [x] ≤ 3 heading levels.
- [x] Abbreviations defined at first mention.
- [x] Figures embedded, Arabic-numeral labels, EPS/TIFF acceptable.
- [x] Tables built with the table function.
- [x] References with DOIs, `[n]` bracket citations.
- [x] **Funding statement** (mandatory).
- [x] **Ethics statement** — *not applicable* (no human-subjects data or biological material; three public benchmarks used under the licenses listed in §7).
- [x] **Data availability statement** — points to the Zenodo DOI *and* names the license for each dataset (per Fix B7).
- [x] **Competing interests** — declared none.
- [x] **Author contributions** — CRediT taxonomy (§20).
- [x] **LLM-usage disclosure** — declared per Springer's 2024–2026 policy.
- [x] **ORCID** for corresponding author.
- [x] **SJR figure re-verified** against the live Scimago page in the 24 h before submission (per Fix B1).

---

## 18. Risk Register and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Reviewer flags v1.0's grand-coalition candidate bias | (mitigated) | Would have been high | §4 now uses union-of-top-N-per-source; v1.0 design retained only as Appendix-B ablation. |
| Reviewer requests a fourth dataset | Medium | Low | Keep a preprocessed Gowalla split ready for revision. |
| Reviewer objects "five signals is arbitrary" | Medium | Medium | Justify via Burke's hybrid-recommender taxonomy in §2. |
| Reviewer says the propositions are trivial | (mitigated) | Would have been medium | Reframed as *Formal Properties* — restatements of standard Shapley axioms, not novel theorems (Fix B2). |
| **Reviewer constructs a counterexample to Property 2** | (mitigated) | **Would have been critical** — a false theorem is a desk-reject-grade error | Monotonicity hypothesis now explicit; counterexample stated openly in §5/Appendix A and pinned in CI; E0-b discharges the assumption empirically (Fix R1a). |
| **Candidate recall on Amazon-Book fails the 0.60 gate in Week 4** | (mitigated) | Would have been high — no viable remediation existed | Per-dataset $N_{\max}^{(d)}$ pre-registered in Week 1; E0-a run on Amazon-Book first; gate remedy is raising $N_{\max}^{(d)}$, not re-tuning the growth schedule (Fix R2). |
| **Reviewer notes $\lambda$ tuned per coalition inflates $v(\mathcal{G})$** | (mitigated) | Would have been high — same pathology v1.1 was cut to remove | $\lambda$ frozen once on a pilot; E5-vi reports sensitivity without selecting (Fix R1b). |
| **Reviewer notes T5 compares candidate-restricted vs full-catalog methods** | (mitigated) | Would have been high | T5 is full-catalog for every method; SignalShap-Fuse scores outside $C_u$ as $-\infty$ (Fix R5). |
| Reviewer calls the redundancy finding circular (guaranteed by player design) | Medium | Medium | pop–cf and rec–ct overlap pre-registered in §10 as a tested hypothesis, restated in §5 (Fix R6). |
| Fitted $v$ makes negative $\varphi_g$ appear | Medium | Low | Expected and interpretable under a non-monotone game; E0-b quantifies it, main-text CIs carry the estimation error. |
| Reviewer challenges the fixed-candidate assumption | Medium | Medium | Appendix-B regenerated-candidates ablation directly addresses this (E8-a). |
| Reviewer asks about nonlinear score maps | Low | Low | Remark 1 declares invariance holds affinely only; E5(iii) reports empirical sensitivity. |
| Reviewer asks about scaling beyond 5 sources | Medium | Low | Discuss hybrid exact-plus-MC scheme in §5; frame as future work. |
| Reviewer questions "zero cost" fusion claim | (mitigated) | Would have been medium | Wording now "negligible ($O(1)$ segment-lookup)" (Fix B6). |
| Reviewer questions "laptop CPU" claim | (mitigated) | Would have been medium | Claim narrowed to the Shapley computation and cached-score refits (Fix B4); base-scorer training uses a single GPU one time (§6). |
| Cache size for Amazon-Book | Low | Low | Subsample to 50 k users; ship subsampling seed and manifest. |
| **Amazon-Book recall fails the gate even at raised $N_{\max}$** | Medium | Medium | Four-rung fallback ladder pinned in §4 (raise $N_{\max}$ → $k$-core → report ceiling and retain only the relative LOO-vs-Shapley claim → substitute Gowalla); rung 1 bounded by the §6 compute claim. |
| Springer editorial screen rejection | Low | High | Pre-apply every rule in §14 and §17; run Springer's LaTeX validator. |

---

## 19. Nine-Week Execution Timeline (extended in v1.1.2)

> **Why nine, and why this is a floor.** v1.1.1 scheduled eight experiment families across three datasets into Weeks 4–6; E5's stress grid alone is realistically a week. v1.1.2 then adds three items that did not exist before: the E0-b monotonicity audit, the frozen-$\lambda$ pilot plus the E5-vi sensitivity sweep, and the full-catalog re-run of T5. E7 and E8 move to Week 7. Nine weeks is now the floor, not the comfortable estimate.

- **Week 1 — Scaffolding, pre-registration, and the two gates.** Repo, CI, Docker (CPU + GPU), dataset download scripts, temporal split, deterministic tie-breaking. The proportional-growth candidate builder from §4 including the **truncation rule**, with three unit tests: identical $C_u$ across all $2^5$ coalition contexts, identical $C_u$ across the five seeds, and $|C_u|\le N_{\max}^{(d)}$ for every user. **Pre-register $N_{\max}^{(d)}$ per dataset and freeze it in `configs/`.** Run **E0-a candidate recall on Amazon-Book first** — highest-risk fact, ~1 day, do it before writing anything downstream. Serialise the frozen permutation $\pi_u$ for $v_0$. Synthetic 32-coalition smoke test checking Property 1 to floating-point tolerance, **plus `tests/test_property2_counterexample.py`**, which pins the three-player counterexample of §5 so the monotonicity hypothesis is enforced by CI rather than by prose.
- **Week 2 — Base scorers.** ALS, TF-IDF, popularity-with-decay, recency, item2vec. Cache score matrices for all three datasets. Ship a comparison run against BPR-MF (documented, discarded) and SASRec (documented, moved to Appendix B).
- **Week 3 — Game core, $\lambda$ freeze, fusion decision.** Fixed-candidate NDCG@10, coalition enumeration, exact Shapley in closed form, LOO/forward/permutation/MC Shapley baselines. **Run the $\lambda$ pilot on ML-1M, pick one value, freeze it in `configs/`** — $\lambda$ is never tuned per coalition (§4). Ridge vs pairwise-logistic smoke test; freeze fusion choice at end of week. **Run E0-b monotonicity audit** as soon as $v$ is computable, and record whether Property 2 is applicable per dataset. **If violations are material, decide Lemma 1(ii)'s assumption now** (monotonicity vs. bounded synergy $\ge-\delta$) rather than in Week 7 — the decision is nearly free here and collides with the writing pass if deferred.
- **Week 4 — E1 + E2** on all three datasets. Produce F2, F3, F4, T6. Main-text CIs on $\varphi_g$.
- **Week 5 — E3 + E4.** Segment heterogeneity and SignalShap-Fuse. Full-catalog T5 protocol implemented here (baselines and SignalShap-Fuse on one scale). Produce F5, F6, T5, T7.
- **Week 6 — E5 + E6.** Six-way robustness matrix (including the $\lambda$ sweep and per-cell recall) and ablations. Produce F7, T8.
- **Week 7 — E7 + E8 + Appendix A.** Actionability case study, Appendix-B experiments, and the **Lemma 1 ($\varepsilon$-redundancy) derivation**. *Budget note:* the derivation itself is ~half a day, but Lemma 1(ii)'s assumption must be **reconciled with whatever E0-b actually reported in Week 3** — if the audit found material violations, the lemma has to be restated under bounded synergy ($\ge-\delta$) with the $\delta$ term carried through, and §5's interpretation of every negative $\varphi_g$ rewritten to match. Budget **two days**, and pull the reconciliation forward to Week 3 (immediately after E0-b runs) if the audit looks bad — deciding the lemma's assumption early is nearly free, whereas discovering it in Week 7 collides with the writing pass.
- **Week 8 — Writing pass 1.** §1, §2, §3 (with derivations), §4. Cross-check every number against `artefacts/` JSON. Verify the "exact given the fitted $v$" wording is used consistently and that no §0-style internal vocabulary has leaked (§21).
- **Week 9 — Writing pass 2 + submission.** §5, §6, abstract, declarations, license/terms-of-use column in T2, LLM-usage block, Zenodo snapshot + DOI, live SJR re-check, Springer LaTeX validator. Submit.

---

## 20. Author Roles (CRediT)

- **Mouad Louhichi.** Conceptualisation, methodology, software, formal analysis, investigation, writing — original draft, visualisation, project administration.
- **Redwane Nesmaoui.** Software (base scorers, statistical package), validation, data curation, writing — review & editing.
- **Mohamed Lazaar.** Supervision, methodology, resources, writing — review & editing, funding acquisition.

---

## 21. Standing Editorial Rules (v1.1.2)

- **Never** cite DyHuCoG as a reproducibility source, only as motivation. The 63-gap audit is the reason this paper is independent of it.
- **Never** cite, quote, or import structure from the parallel AI-generated Deep Analysis brainstorming document. It is not a peer-reviewed source (Fix C1–C4). All numeric projections in it (e.g., NDCG-gain forecasts, GitHub-star forecasts, citation forecasts) are AI-generated and must not appear in the manuscript, the cover letter, or the grant materials.
- **Never** claim causal discovery. All attribution is inside the fixed candidate set and the declared game.
- **Every** quantitative claim in the text traces to a JSON in `artefacts/` and to a table cell.
- **No sampling-based Shapley** in the main results — only in E5 as a matched-budget check that exact Shapley beats sampled Shapley at equal cost. State this as a *correctness* claim, not a reviewer-defusion tactic.
- **The abstract must include the phrase "exact Shapley over 32 coalitions"** — because that is the most accurate one-line description of the method, not because it "defuses" reviewers. Delete any "review-proof" framing wherever it appears in internal materials (Fix B3).
- **The "laptop CPU, seconds" claim applies to the Shapley computation only.** Every mention in the paper must be qualified accordingly (Fix B4).
- **The SignalShap-Fuse cost claim is "negligible ($O(1)$ segment-lookup)"**, not "zero" (Fix B6). The $O(1)$ justification is that segment assignment is a table lookup on precomputed user-segment IDs.
- **Properties 1–3 are restated Shapley axioms, not novel theorems** (Fix B2). Wording in §3 of the paper must reflect this.
- **Ethics + LLM-usage + funding + competing-interests declarations must be present.** Data Availability Statement names dataset licenses explicitly (Fix B7).
- **SJR figure re-verified** against the live Scimago page in the 24 h before submission (Fix B1).
- **Candidate recall is a submission gate — with a real remediation path (revised in v1.1.2).** The gate is now evaluated at the **pre-registered per-dataset $N_{\max}^{(d)}$** of §4. If mean candidate recall falls below $0.60$, follow the **four-rung fallback ladder in §4** (raise $N_{\max}$ → $k$-core the corpus → report the ceiling as a finding and restrict Amazon-Book to the relative LOO-vs-Shapley claim → substitute Gowalla), in that order, recording the chosen rung and its compute cost in the artefact. Do *not* re-tune the growth schedule: it redistributes budget between sources and cannot create recall the base scorers' top-lists do not contain. Note that rung 1 is bounded by the §6 compute claim — if the pool needed to clear the gate breaks the laptop-CPU story for that dataset, escalate rather than keep growing. Any change to $N_{\max}^{(d)}$ after Week 1 must be recorded in the artefact with its date and reason. Restricting the evaluated user population to those with $\text{test}_u\in C_u$ is **forbidden**: it biases the population differentially by density and confounds C3. Enforced in CI; E0-a exits non-zero on breach.
- **Monotonicity is audited, never assumed.** Property 2 and Lemma 1(ii) may only be invoked for a dataset where E0-b reports negligible violations. Where violations are material, say so in §4 of the paper and interpret negative $\varphi_g$ as substantive. `tests/test_property2_counterexample.py` must stay green — it encodes the fact that redundancy alone does *not* imply positive Shapley value.
- **"Exact" always means "exact given the fitted $v$."** $v$ is estimated (ridge heads on a validation fold), so exactness is a property of the 32-coalition aggregation, not of the attribution end-to-end. Never write "no error"; write "no sampling error." Main-text $\varphi_g$ carries seed CIs.
- **$\lambda$ is frozen, never tuned per coalition.** Per-coalition tuning is optimistic bias that grows with $|S|$ and would re-create the grand-coalition inflation v1.1 was cut to remove. E5-vi reports sensitivity; it does not select.
- **T5 is full-catalog for every method.** Never compare a candidate-restricted method against full-catalog baselines, and never restrict a baseline to $C_u$ to make the comparison "fair."
- **Player overlap is pre-registered, not discovered.** $pop$–$cf$ and $rec$–$ct$ redundancy is partly guaranteed by the scorer definitions; §10 states this as a prior and §5 restates it when interpreting F4.
- **§0's internal vocabulary never reaches the manuscript.** "Reviewer attack surface," "acceptance risk," "hard-to-attack" and the four-blueprint comparison table are planning artefacts. The existing ban on "review-proof" framing extends to all of it, including the cover letter.

---

**End of implementation specification, v1.1.2.**
