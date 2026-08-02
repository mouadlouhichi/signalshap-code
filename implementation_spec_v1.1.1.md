# SignalShap — Implementation Specification (v1.1.1, Q1-Ready, Post-Fix-Review)

**Target journal:** *Discover Artificial Intelligence* (Springer Nature — open access, CiteScore 6.0, Q1 in Artificial Intelligence). *SJR value to be re-verified against the live Scimago page immediately before submission (see §17).*
**Article type:** Research article.
**Working title:** *Game Theory Meets Recommendation: Exact Shapley Credit Assignment over Collaborative, Content, and Contextual Signals*.
**Authors:** Mouad Louhichi¹\*, Redwane Nesmaoui¹, Mohamed Lazaar¹.
**Affiliation:** ¹National Higher School of Computer Science and Systems Analysis (ENSIAS), Mohammed V University in Rabat, Morocco.
**Corresponding author:** mouad_louhichi@um5.ac.ma.
**Companion prior work:** *Game Theory Meets Explainable AI* (IJACSA 2025) — SignalShap is its direct methodological successor at the architectural-source granularity.

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

## 4. Cooperative Game Definition (v1.1 — corrected candidate generation)

Let $\mathcal{G}=\{cf,ct,pop,rec,seq\}$ be the five signal sources.

**Candidate set $C_u$ (coalition-independent).** For each user $u$ and each source $g$, take the top-$N_g$ items under that single source's scorer. Set

$$
C_u \;=\; \bigcup_{g\in\mathcal{G}} \text{top-}N_g^{(g)}(u),\qquad |C_u|\le N_{\max}=200,
$$

so that every coalition $S\subseteq\mathcal{G}$ scores exactly the same $\le 200$ items and differences in $v(S)$ reflect fusion within $S$, not retrieval from a coalition-favoring pool. The v1.0 alternative (candidates drawn once from the grand-coalition scorer) is retained as **Appendix-B ablation "regenerated candidates"** because it systematically inflates $v(\mathcal{G})$ relative to $v(S)$ for $S\subsetneq\mathcal{G}$.

**Construction procedure for $C_u$ (pinned in Week 1).** Because overlap between sources is user-dependent, the target $|C_u|\le N_{\max}$ is reached by a deterministic proportional-growth loop, not a global constant $N_g$:

1. Set $N_g^{(0)} = \lceil N_{\max} / |\mathcal{G}|\rceil = 40$ for every source.
2. Materialise $C_u^{(0)} \;=\; \bigcup_{g} \text{top-}N_g^{(0)}(u)$; if $|C_u^{(0)}| = N_{\max}$ (no overlap), stop.
3. Otherwise let $\Delta = N_{\max} - |C_u^{(0)}|$ and grow every $N_g$ by $\lceil \Delta / |\mathcal{G}|\rceil$; re-materialise the union.
4. Iterate step 3, capping $N_g$ at each source's catalogue-size limit, until either $|C_u| = N_{\max}$ or every $N_g$ is capped (i.e., no source has more items to offer). Cap the total loop at $10$ iterations for determinism.
5. Break ties inside every $\text{top-}N_g^{(g)}(u)$ by `(score, timestamp, original_record_index)` so the union is identical across seeds.

Under this procedure, $|C_u|$ can be *below* $N_{\max}$ for tiny users whose source top-lists are exhausted before the union grows to 200, but it can never exceed $N_{\max}$ and it never depends on which coalition is being evaluated. The empirical distribution of $|C_u|$ across users is reported per dataset in T2, so reviewers can compute Recall@$N$ by hand if they wish. The full loop is implemented in `src/signalshap/candidates/` and covered by a unit test that asserts identical $C_u$ across all $2^5$ coalition contexts.

**Fusion score.** For each coalition $S$,

$$
\hat s_{u,i}(S) \;=\; \sum_{g\in S} w_g^{(S)}\, z_{u,g,i},
$$

where $z_{u,g,i}$ is the per-user, per-source z-normalised raw score of source $g$ for item $i\in C_u$, and $\{w_g^{(S)}\}_{g\in S}$ is a ridge-regularized linear head refit on the validation fold *conditioned on the coalition* $S$. A pairwise-logistic head is trained in parallel as a Week-3 smoke test; the primary results use ridge iff Shapley-share orderings are stable across both.

**Characteristic function.**

$$
v(S) \;=\; \frac{1}{|\mathcal{U}|}\sum_{u\in\mathcal{U}}\mathrm{NDCG@10}\bigl(\text{rank}_i\hat s_{u,i}(S)\,;\,\text{test}_u\cap C_u\bigr) \;-\; v_0,
$$

with $v(\varnothing)=0$ pinned by construction (baseline $v_0$ = NDCG@10 of a fixed random ranker over $C_u$).

**Exact Shapley.**

$$
\varphi_g \;=\; \sum_{S\subseteq\mathcal{G}\setminus\{g\}}\frac{|S|!\,(|\mathcal{G}|-|S|-1)!}{|\mathcal{G}|!}\bigl[v(S\cup\{g\})-v(S)\bigr],
$$

a closed-form sum over $2^5=32$ coalitions.

---

## 5. Formal Properties (Restatements)

These are direct instantiations of standard Shapley axioms in the source-attribution setting. They are *not* claimed as new theorems; they are stated here so the paper can reason about LOO failure precisely.

- **Property 1 (Efficiency / additive decomposition).** $\sum_{g\in\mathcal{G}}\varphi_g = v(\mathcal{G})$. *Instantiation.* Direct from Shapley efficiency for $(\mathcal{G},v)$ with $v(\varnothing)=0$.
- **Property 2 (LOO redundancy collapse).** If two sources $g_1,g_2$ satisfy $v(S\cup\{g_1\})=v(S\cup\{g_2\})=v(S\cup\{g_1,g_2\})$ for every $S\subseteq\mathcal{G}\setminus\{g_1,g_2\}$, then $\mathrm{LOO}(g_1)=\mathrm{LOO}(g_2)=0$ while $\varphi_{g_1}=\varphi_{g_2}>0$ whenever $v(\{g_1\})>0$. *Instantiation.* Combine the LOO definition $\mathrm{LOO}(g)=v(\mathcal{G})-v(\mathcal{G}\setminus\{g\})$ with the redundancy hypothesis and Shapley symmetry.
- **Property 3 (Free per-user decomposition).** $\varphi_g=\frac{1}{|\mathcal{U}|}\sum_u\varphi_g(u)$. *Instantiation.* Linearity of the Shapley operator applied to a per-user mean characteristic function.
- **Remark 1 (Affine scale invariance).** Per-user z-normalisation makes $\varphi_g$ invariant under any user- and source-specific affine map $z\mapsto az+b$. Invariance does *not* extend to nonlinear monotone maps; this is verified empirically in §11-E5(iii).

Full derivations are in Appendix A.

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
- **RQ3.** Is source attribution homogeneous across users, or does the global attribution conceal opposing segment-level attributions (heavy vs. cold, dense vs. sparse, recency-driven vs. stability-driven)?
- **RQ4.** Can segment-adaptive fusion (SignalShap-Fuse) turn Shapley attribution into a measurable NDCG@10 improvement over globally-tuned fusion at negligible ($O(1)$ segment-lookup) additional inference cost?

---

## 11. Experimental Plan

- **E0 — Candidate-set diagnostics (precondition to every downstream number).** For every dataset, report the empirical distribution of $|C_u|$ and **candidate recall** ($\Pr[\text{test}_u\in C_u]$). Any test user with $\text{test}_u\notin C_u$ contributes zero to NDCG@10 by construction, so candidate recall is the ceiling on all E1–E4 metrics and is stated at the top of §4 of the paper and in T2.
- **E1 — Source share by dataset (→ RQ1).** Compute $\varphi_g$ for every $g\in\mathcal{G}$ on all three datasets. Report bootstrap 95 % CIs (secondary — in Appendix B). Verify $\sum_g\varphi_g=v(\mathcal{G})$ to floating-point tolerance.
- **E2 — LOO vs Shapley scatter (→ RQ2).** For every $(dataset, source)$ pair, report LOO share, Shapley share, and the gap. Compute Kendall $\tau$ between per-user source score vectors of every $(g_1,g_2)$ pair to quantify redundancy; correlate redundancy with the LOO–Shapley gap. **Primary test: within-user permutation test on the gap (10 000 shuffles).**
- **E3 — Segment heterogeneity (→ RQ3).** Partition users into segments by activity quantile and by recency skew. Compute segment-level Shapley shares. **Primary test: between-segment permutation (10 000 shuffles);** report Cohen's $d_z$.
- **E4 — SignalShap-Fuse (→ RQ4).** For each segment learn a fusion weight vector on validation, evaluate on test. Compare against uniform, globally-tuned, LightGCN, and (Appendix B) SASRec. **Primary test: Wilcoxon signed-rank on paired per-user NDCG@10; Holm–Bonferroni correction over the declared family of 4 comparisons per dataset (uniform, globally-tuned, LightGCN, SASRec-appendix).**
- **E5 — Robustness matrix (5 stress tests).** (i) $|C_u|\in\{100, 200, 500\}$; (ii) five seeds $\{42, 43, 44, 45, 46\}$; (iii) monotone rescalings (identity, log1p, rank-transform); (iv) cold-user fallback ($z_{u,g,i}=0$); (v) per-source Gaussian noise injection.
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
- **Multiplicity.** Holm–Bonferroni. **Family size declared at the top of every table** (e.g., "$m=4$ comparisons per dataset" for T7). Corrected $p$ values are what appears in the paper; raw $p$ values live in Appendix B.
- **Secondary tests (Appendix B).** Paired-$t$ for symmetry cross-checks; bootstrap 95 % CIs (10 000 resamples) for graphical intervals; sensitivity of Wilcoxon to ties.
- **Reporting rule.** Every statistical claim in the paper is traceable to a JSON in `artefacts/` that carries the raw test statistic, corrected $p$, effect size, family size, and seed manifest.

---

## 13. Paper Structure (six-section IJACSA layout, ≈ 8 500 words)

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
- **T2.** Dataset statistics + split manifest + license/terms-of-use column + **candidate recall** (fraction of true test items inside $C_u$) and $|C_u|$ mean $\pm$ std, reported per dataset — this is the ceiling on every ranking metric in T5–T7 and must be inspected before any attribution number is interpreted.
- **T3.** Notation.
- **T4.** Per-source computational cost (train once + cache).
- **T5.** Main NDCG@10 / Recall@20 / MRR results.
- **T6.** LOO share vs Shapley share per (dataset, source).
- **T7.** SignalShap-Fuse vs baselines with Wilcoxon $p$ (Holm–Bonferroni corrected, $m=4$) and Cohen's $d_z$.
- **T8.** Robustness matrix summary.

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
│   ├── e1_source_share.yaml
│   ├── e2_loo_vs_shapley.yaml
│   ├── e3_segments.yaml
│   ├── e4_signalshap_fuse.yaml
│   ├── e5_robustness.yaml
│   ├── e6_ablation.yaml
│   ├── e7_actionability.yaml
│   └── e8_appendix_b.yaml       # regen-candidates, SASRec, pairwise-logistic
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
| Reviewer challenges the fixed-candidate assumption | Medium | Medium | Appendix-B regenerated-candidates ablation directly addresses this (E8-a). |
| Reviewer asks about nonlinear score maps | Low | Low | Remark 1 declares invariance holds affinely only; E5(iii) reports empirical sensitivity. |
| Reviewer asks about scaling beyond 5 sources | Medium | Low | Discuss hybrid exact-plus-MC scheme in §5; frame as future work. |
| Reviewer questions "zero cost" fusion claim | (mitigated) | Would have been medium | Wording now "negligible ($O(1)$ segment-lookup)" (Fix B6). |
| Reviewer questions "laptop CPU" claim | (mitigated) | Would have been medium | Claim narrowed to the Shapley computation and cached-score refits (Fix B4); base-scorer training uses a single GPU one time (§6). |
| Cache size for Amazon-Book | Low | Low | Subsample to 50 k users; ship subsampling seed and manifest. |
| Springer editorial screen rejection | Low | High | Pre-apply every rule in §14 and §17; run Springer's LaTeX validator. |

---

## 19. Eight-Week Execution Timeline

- **Week 1 — Scaffolding + A5 decision locked.** Repo, CI, Docker (CPU + GPU), dataset download scripts, temporal split, deterministic tie-breaking, the proportional-growth union-of-top-N-per-source candidate builder from §4 (with a unit test asserting identical $C_u$ across all $2^5$ coalition contexts and another asserting reproducibility across the five seeds), an **E0 candidate-recall report** per dataset before any downstream experiment is allowed to run, and a synthetic 32-coalition smoke test that mechanically checks Property 1 to floating-point tolerance.
- **Week 2 — Base scorers.** ALS, TF-IDF, popularity-with-decay, recency, item2vec. Cache score matrices for all three datasets. Ship a comparison run against BPR-MF (documented, discarded) and SASRec (documented, moved to Appendix B).
- **Week 3 — Game core + fusion decision.** Fixed-candidate NDCG@10, coalition enumeration, exact Shapley in closed form, LOO/forward/permutation/MC Shapley baselines, ridge vs pairwise-logistic fusion smoke test. Freeze fusion choice at end of week.
- **Week 4 — E1 + E2** on all three datasets. Produce F2, F3, F4, T5, T6.
- **Week 5 — E3 + E4.** Segment heterogeneity and SignalShap-Fuse. Produce F5, F6, T7.
- **Week 6 — E5 + E6 + E7 + E8.** Robustness matrix, ablations, actionability case study, Appendix-B experiments. Produce F7, T8.
- **Week 7 — Writing pass 1.** §1, §2, §3 (with derivations), §4. Cross-check every number against `artefacts/` JSON.
- **Week 8 — Writing pass 2 + submission.** §5, §6, abstract, declarations, license/terms-of-use column in T2, LLM-usage block, Zenodo snapshot + DOI, live SJR re-check, Springer LaTeX validator. Submit.

---

## 20. Author Roles (CRediT)

- **Mouad Louhichi.** Conceptualisation, methodology, software, formal analysis, investigation, writing — original draft, visualisation, project administration.
- **Redwane Nesmaoui.** Software (base scorers, statistical package), validation, data curation, writing — review & editing.
- **Mohamed Lazaar.** Supervision, methodology, resources, writing — review & editing, funding acquisition.

---

## 21. Standing Editorial Rules (v1.1)

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
- **Candidate recall is a submission gate.** If mean candidate recall on any of the three datasets falls below $0.60$, stop, re-tune the top-$N_g$ growth schedule, and rebuild the cache — do not report attribution numbers on top of a broken retrieval ceiling. This rule is enforced in CI: the E0 script exits non-zero when the threshold is breached.

---

**End of implementation specification, v1.1.1.**
