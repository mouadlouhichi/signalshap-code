# SignalShap — Implementation Specification

**Canonical build, experiment, writing, and submission plan.**
Supersedes `implementation_spec_v1.1.1.md`, `implementation_spec_v1.1.2.md`, and `implementation_spec_v1.1.3.md`, which are retained only as revision history.

**Target journal:** *Discover Artificial Intelligence* (Springer Nature — open access). *SJR/CiteScore figures to be re-verified against the live Scimago page immediately before submission (§16).*
**Article type:** Research article.
**Working title:** *Game Theory Meets Recommendation: Exact Shapley Credit Assignment over Collaborative, Content, and Contextual Signals*.
**Authors:** Mouad Louhichi¹\*, Redwane Nesmaoui¹, Mohamed Lazaar¹.
**Affiliation:** ¹National Higher School of Computer Science and Systems Analysis (ENSIAS), Mohammed V University in Rabat, Morocco.
**Corresponding author:** mouad_louhichi@um5.ac.ma.
**Companion prior work:** *Game Theory Meets Explainable AI* (IJACSA 2025) — SignalShap is its direct methodological successor at the architectural-source granularity.

---

## How to read this document

This is a *specification*, not a summary. Each substantive rule is stated in three parts:

- **Rule** — what to do.
- **Why** — the failure it prevents. Most rules here exist because an earlier draft got something wrong; the reasoning is preserved so the rule is not silently reverted by someone who does not know what it was protecting against.
- **Enforcement** — the test, gate, or artefact that makes the rule survive a deadline. Rules with no enforcement mechanism are marked as such and should be treated as weaker.

Three conventions apply throughout:

1. **Every quantitative claim in the manuscript traces to a JSON file in `artefacts/`.** No number is typed into the paper by hand.
2. **Assumptions are discharged, never asserted.** Where a formal result needs a hypothesis (monotonicity, redundancy, scale invariance), the specification names an experiment that checks whether the hypothesis actually holds on the data.
3. **Internal planning vocabulary never reaches the manuscript.** See §20.

---

## 0. Thesis

Hybrid recommender systems fuse several architecturally distinct signals — collaborative filtering, content, popularity, recency, and sequential order — but current practice attributes system quality to these signals using leave-one-out (LOO) ablation, which fails whenever two signals are redundant. We recast source attribution as a five-player cooperative game with fixed-candidate NDCG@10 as its characteristic function. Because the player set has size five, the Shapley value is computed **exactly** over $2^5 = 32$ coalitions on a laptop CPU in seconds; there is no sampling error in the aggregation. We restate three standard Shapley properties in the source-attribution setting, prove one approximate lemma connecting redundancy to the LOO–Shapley gap, and show empirically on MovieLens-1M, Amazon-Book, and LastFM-2K that Shapley shares differ from LOO shares in the direction the redundancy geometry predicts. We close the loop with **SignalShap-Fuse**, a segment-adaptive fusion whose weights are tuned per Shapley-derived user segment and which improves NDCG@10 at negligible ($O(1)$ segment-lookup) additional inference cost.

### Why this design was chosen

SignalShap was selected over three alternative blueprints because it is the only one that is simultaneously: (a) computable exactly rather than by Monte-Carlo sampling, (b) executable with the Shapley game on a laptop CPU, (c) independent of the DyHuCoG codebase (audited, 63 documented reproducibility gaps, unsafe to inherit), and (d) a natural continuation of the authors' published IJACSA 2025 line. The comparative selection table lives in the revision history and is **internal only** (§20).

---

## 1. Contributions

- **C1 — Source-level cooperative game.** A hybrid-recommendation cooperative game whose players are architectural signal sources, whose characteristic function is fixed-candidate NDCG@10 on a coalition-independent candidate set, and whose small player set admits exact Shapley computation.
- **C2 — Formal restatement of three standard Shapley properties** in the source-attribution setting, plus one new approximate lemma (Lemma 1) and a scale-invariance remark. The mathematical content of Properties 1–3 is *not* novel; the contribution is careful instantiation and use of them to predict and empirically test LOO behaviour.
- **C3 — Empirical falsification of LOO under redundancy** on three benchmarks of contrasting density (dense movies, sparse books, medium music). *The density ordering in that parenthetical is a claim about the **as-used** corpora and is CI-enforced (§6); if any filter changes it, the wording is regenerated from `artefacts/dataset_stats.json`, not retained.*
- **C4 — Segment heterogeneity mapping.** Per-user Shapley attributions aggregated into behavioural segments (heavy/cold, dense/sparse history, recency-driven/stability-driven), with a permutation test for heterogeneity.
- **C5 — SignalShap-Fuse.** A closed-loop, segment-adaptive fusion mechanism whose weights come from segment-level Shapley profiles, improving NDCG@10 at negligible ($O(1)$ segment-lookup) additional inference cost.
- **C6 — Fully reproducible artefact.** Zenodo-archived code, cached score matrices, dataset-license notice, and configuration files.

---

## 2. The Cooperative Game

Let $\mathcal{G} = \{cf, ct, pop, rec, seq\}$ be the five signal sources, $|\mathcal{G}| = 5$.

### 2.1 Candidate set $C_u$ — coalition-independent by construction

**Rule.** For each user $u$ and source $g$, take the top-$N_g$ items under that single source's scorer, and set

$$
C_u \;=\; \bigcup_{g \in \mathcal{G}} \text{top-}N_g^{(g)}(u), \qquad |C_u| \le N_{\max}^{(d)},
$$

where $N_{\max}^{(d)}$ is pre-registered per dataset (§2.2). Every coalition $S \subseteq \mathcal{G}$ scores **exactly the same item set**.

**Why.** The original design drew candidates once from the grand-coalition scorer. That is subtly fatal: it hands the grand coalition a retrieval pool selected in its own favour, so $v(\mathcal{G})$ is inflated relative to every $v(S)$, $S \subsetneq \mathcal{G}$ — and since Shapley values are built entirely from differences $v(S \cup \{g\}) - v(S)$, the bias propagates into every attribution. Under the union design, differences in $v(S)$ reflect **fusion within $S$**, not retrieval from a coalition-favouring pool. The old design is retained as an Appendix-B ablation (E8-a) precisely to quantify the bias avoided.

**Enforcement.** Unit test asserting identical $C_u$ across all $2^5$ coalition contexts.

### 2.2 Pre-registered $N_{\max}^{(d)}$ and the recall gate

**Rule.** $N_{\max}^{(d)}$ is fixed per dataset in Week 1 and frozen in `configs/frozen.yaml`:

| Dataset | Catalogue size | $N_{\max}^{(d)}$ |
|---|---|---|
| MovieLens-1M | $\approx 3{,}706$ | 200 |
| LastFM-2K | $\approx 17{,}632$ | 500 |
| Amazon-Book | $\approx 90{,}000$ | 1000 |

**Candidate recall** ($\Pr[\text{test}_u \in C_u]$) must be $\ge 0.60$ on every dataset.

**Why.** A single global $N_{\max} = 200$ plus a hard $0.60$ recall gate is *jointly unsatisfiable* on a sparse catalogue: at $\approx 90{,}000$ items and $\approx 0.05\%$ density, recall@200 on Amazon-Book is realistically $0.10$–$0.25$. Candidate recall is a **ceiling on every ranking metric downstream** — a test item outside $C_u$ contributes zero to NDCG@10 by construction — so attribution numbers computed on top of a broken retrieval ceiling are meaningless.

**Enforcement.** E0-a exits non-zero on breach. Run it on **Amazon-Book first, in Week 1**, before any other code: it is the single fact most likely to invalidate the plan, and it costs about a day.

#### The fallback ladder (what to do when the gate fails)

Rungs are attempted in order. Each is preferred to the one below it.

1. **Raise $N_{\max}$ to 2000.** The only remedy that changes nothing but compute. Report wall-clock in T4 and re-verify the §4 compute claim. **Preferred.**
2. **Accept the ceiling and report it as a finding.** A sparse corpus where union-of-top-$N$ retrieval cannot reach $0.60$ is itself informative about the limits of a fixed-candidate game. Report attribution *conditional on* the stated ceiling, note the limitation in the discussion, drop Amazon-Book from absolute-NDCG comparison against LightGCN, but **retain it for the relative LOO-vs-Shapley contrast** — which is the claim C3 actually needs and which is far less ceiling-sensitive than absolute ranking quality.
3. **$k$-core the corpus** — capped and gated, see §6.2. Shrinks the catalogue instead of growing the pool.
4. **Substitute Gowalla** (preprocessed split held in reserve). Last resort: it costs the density-contrast framing.

**Why this order.** Rung 3 was originally ranked second, as "standard practice, disclosable in one sentence." It was demoted after the arithmetic in §6.2 showed it can *invert* the density ordering that C3 depends on. Rung 2 costs a weaker absolute claim but leaves C3 fully intact; rung 3 can silently invalidate C3. A weaker claim beats a false one.

**Forbidden remedies.** (i) Re-tuning the growth schedule — it redistributes budget between sources and cannot create recall that the base scorers' top-lists do not contain. (ii) Restricting evaluation to users with $\text{test}_u \in C_u$ — this restricts the population *differentially by density*, over-representing easy users precisely on the sparse datasets, which confounds C3.

### 2.3 Construction procedure for $C_u$

Overlap between sources is user-dependent, so $N_{\max}^{(d)}$ is reached by a deterministic proportional-growth loop rather than a fixed per-source constant:

1. Set $N_g^{(0)} = \lceil N_{\max}^{(d)} / |\mathcal{G}| \rceil$ for every source.
2. Materialise $C_u^{(0)} = \bigcup_g \text{top-}N_g^{(0)}(u)$; if $|C_u^{(0)}| \ge N_{\max}^{(d)}$, go to step 6.
3. Let $\Delta = N_{\max}^{(d)} - |C_u^{(0)}|$; grow every $N_g$ by $\lceil \Delta / |\mathcal{G}| \rceil$; re-materialise.
4. Iterate step 3, capping each $N_g$ at its source's catalogue limit, until $|C_u| \ge N_{\max}^{(d)}$ or every $N_g$ is capped. Hard-cap at 10 iterations for determinism.
5. Break ties inside each top-$N_g$ list by `(score, timestamp, original_record_index)`.
6. **Truncation.** The union can *overshoot* $N_{\max}^{(d)}$, because step 3 grows all five lists simultaneously and newly admitted items may not overlap. When $|C_u| > N_{\max}^{(d)}$, sort the union on `(best per-source rank across g ∈ 𝒢, source order as listed in 𝒢, original_record_index)` and keep the first $N_{\max}^{(d)}$.

**Why step 6 exists.** Without an explicit truncation rule, the Week-1 test asserting identical $C_u$ across seeds passes while $|C_u|$ silently diverges from the config — the test checks *stability*, not *conformance*. Both assertions are required.

$|C_u|$ may fall *below* $N_{\max}^{(d)}$ for users whose source lists are exhausted; it can never exceed it, and it never depends on the coalition being evaluated.

**Enforcement.** Three tests: identical $C_u$ across all 32 coalition contexts; identical across the five seeds; $|C_u| \le N_{\max}^{(d)}$ for every user.

### 2.4 Fusion score and the frozen-$\lambda$ protocol

For each coalition $S$,

$$
\hat{s}_{u,i}(S) \;=\; \sum_{g \in S} w_g^{(S)} \, z_{u,g,i},
$$

where $z_{u,g,i}$ is the per-user, per-source z-normalised score of source $g$ for item $i \in C_u$, and $\{w_g^{(S)}\}$ is a ridge head refit on the validation fold conditioned on $S$.

**Rule.** The ridge penalty $\lambda$ is **chosen once and frozen** across all 32 coalitions, all users, all segments, and all datasets. It is never tuned per coalition.

**Why.** Tuning $\lambda$ on the same fold used to evaluate $v(S)$ is not a variance problem — it is **optimistic bias that grows with $|S|$**. Larger coalitions have more weights to fit and more opportunity to overfit the held-out interaction, so $v(\mathcal{G})$ inflates relative to small coalitions. That is the *same pathology* as the grand-coalition candidate bias of §2.1, arriving by a different route; leaving it unaddressed would silently re-introduce what the candidate fix was cut to remove.

**Why not a nested split.** Under leave-last-out there is exactly one validation interaction per user, which is not meaningfully splittable further.

**Procedure.** (1) Choose $\lambda$ in Week 3 on a pilot (ML-1M validation fold, grand coalition only); document the selection curve in Appendix B. (2) Freeze in `configs/frozen.yaml` before E1. (3) Report sensitivity, never selection: E5-vi sweeps $\lambda \in \{0.1, 1, 10\}$ and confirms Shapley-share *orderings* are stable across an order of magnitude either side.

A pairwise-logistic head is trained as a Week-3 smoke test; primary results use ridge iff Shapley-share orderings agree across both.

### 2.5 Characteristic function, and the exact meaning of $v(\varnothing) = 0$

$$
v(S) \;=\; \frac{1}{|\mathcal{U}|} \sum_{u \in \mathcal{U}} \mathrm{NDCG@10}\bigl(\text{rank}_i\, \hat{s}_{u,i}(S) \,;\, \text{test}_u \cap C_u\bigr) \;-\; v_0.
$$

**Rule.** $v_0$ is the NDCG@10 of **one frozen permutation $\pi_u$ of $C_u$**, drawn once under seed 42 and reused for every coalition, user, and experiment. The empty-coalition ranking is *defined* as $\pi_u$ itself.

**Why the precision matters.** "A fixed random ranker" is ambiguous between *one frozen permutation reused everywhere* and *a fresh draw whose expectation is taken*. Under the first reading, $\mathrm{NDCG@10}(\pi_u) - v_0(u) = 0$ **exactly, per user**. Under the second it is zero only in expectation. This matters twice: Property 1 is the one claim mechanically unit-tested to floating-point tolerance, and **Property 3 requires $v(\varnothing) = 0$ per user**, not merely on the mean. The frozen permutation is serialised in the artefact.

**$\varphi_g$ is invariant to $v_0$.** Every marginal $v(S \cup \{g\}) - v(S)$ cancels the offset, so Shapley values do not depend on $v_0$ at all. Its only function is cosmetic — it lets Property 1 read $\sum_g \varphi_g = v(\mathcal{G})$ instead of $v(\mathcal{G}) - v(\varnothing)$. **The manuscript must say this explicitly**, so the random-ranker baseline is not mistaken for a substantive modelling choice.

### 2.6 Exact Shapley

$$
\varphi_g \;=\; \sum_{S \subseteq \mathcal{G} \setminus \{g\}} \frac{|S|!\,(|\mathcal{G}| - |S| - 1)!}{|\mathcal{G}|!} \bigl[v(S \cup \{g\}) - v(S)\bigr],
$$

a closed-form sum over $2^5 = 32$ coalitions. For $n = 5$ the weights by $|S|$ are $\left(\tfrac{1}{5}, \tfrac{1}{20}, \tfrac{1}{30}, \tfrac{1}{20}, \tfrac{1}{5}\right)$.

### 2.7 What "exact" does and does not mean

**Rule.** "Exact" always means **"exact given the fitted characteristic function."** Never write "no error"; write "no sampling error."

**Why.** Because $w^{(S)}$ is *fitted*, each $v(S)$ is an estimate. Exactness is a property of the **aggregation** — the 32-coalition sum has no sampling error, unlike Monte-Carlo Shapley — not of the attribution end-to-end. A reviewer will otherwise observe that Monte-Carlo error was removed and replaced with 32 correlated estimation errors that go unquantified. Consequences:

- Per-coalition $v(S)$ variance across seeds is reported in Appendix B.
- $\varphi_g$ carries seed-based CIs **in the main text** (T6, F2), not Appendix B. Properties 1–3 are properties of the game, not verified facts about the data.
- Monotonicity violations induced by refitting are counted and reported (§3.3).
- Efficiency ($\sum_g \varphi_g = v(\mathcal{G})$) holds *exactly regardless of fit noise*, because it is structural. Say so.

---

## 3. Formal Properties

Properties 1–3 are direct instantiations of standard Shapley axioms. They are **not** new theorems. Lemma 1 is new but modest. Full derivations go in Appendix A.

### 3.1 The three properties

- **Property 1 (Efficiency / additive decomposition).** $\sum_{g \in \mathcal{G}} \varphi_g = v(\mathcal{G})$. Direct from Shapley efficiency with $v(\varnothing) = 0$.

- **Property 2 (LOO redundancy collapse).** *Let $v$ be **monotone***, i.e. $v(S \cup \{g\}) \ge v(S)$ for every $S$ and every $g \notin S$. If $g_1, g_2$ satisfy $v(S \cup \{g_1\}) = v(S \cup \{g_2\}) = v(S \cup \{g_1, g_2\})$ for every $S \subseteq \mathcal{G} \setminus \{g_1, g_2\}$, then
  $$\mathrm{LOO}(g_1) = \mathrm{LOO}(g_2) = 0 \quad\text{while}\quad \varphi_{g_1} = \varphi_{g_2} \;\ge\; \frac{v(\{g_1\})}{|\mathcal{G}|} \;>\; 0$$
  whenever $v(\{g_1\}) > 0$.

- **Property 3 (Free per-user decomposition).** $\varphi_g = \frac{1}{|\mathcal{U}|}\sum_u \varphi_g(u)$. Linearity of the Shapley operator applied to a per-user mean characteristic function. Requires $v(\varnothing) = 0$ **per user** — see §2.5.

- **Remark 1 (Affine scale invariance).** Per-user z-normalisation makes $\varphi_g$ invariant under any user- and source-specific affine map $z \mapsto az + b$. Invariance does **not** extend to nonlinear monotone maps; tested empirically in E5-iii.

### 3.2 Why monotonicity is not optional — the counterexample

An earlier draft stated Property 2 **without** the monotonicity hypothesis. That statement is **false**, and the following three-player game refutes it. It satisfies every stated hypothesis: exact redundancy between $g_1, g_2$, and $v(\{g_1\}) = 1 > 0$.

| $S$ | $\varnothing$ | $g_1$ | $g_2$ | $g_3$ | $g_1g_2$ | $g_1g_3$ | $g_2g_3$ | $g_1g_2g_3$ |
|---|---|---|---|---|---|---|---|---|
| $v(S)$ | $0$ | $1.0$ | $1.0$ | $5.0$ | $1.0$ | $0.5$ | $0.5$ | $0.5$ |

Redundancy holds ($1.0 = 1.0 = 1.0$ at $S = \varnothing$; $0.5 = 0.5 = 0.5$ at $S = \{g_3\}$). LOO collapses to zero as predicted. Symmetry and efficiency both hold. And yet:

$$\varphi_{g_1} = \varphi_{g_2} = -0.4167, \qquad \varphi_{g_3} = +1.3333, \qquad \textstyle\sum = 0.5 = v(\mathcal{G}).$$

**The redundant sources receive negative credit despite positive standalone value.** Redundancy alone is therefore compatible with $\varphi < 0$; the positivity clause requires monotonicity as a separate structural assumption.

**The monotone variant — repair, shown in full.** Adding monotonicity while keeping the redundancy structure intact repairs the property. Only the three payoffs marked $\dagger$ differ from the table above:

| $S$ | $\varnothing$ | $g_1$ | $g_2$ | $g_3$ | $g_1g_2$ | $g_1g_3$ | $g_2g_3$ | $g_1g_2g_3$ |
|---|---|---|---|---|---|---|---|---|
| $v(S)$ | $0$ | $1.0$ | $1.0$ | $5.0$ | $1.0$ | $5.5^\dagger$ | $5.5^\dagger$ | $5.5^\dagger$ |

Verified mechanically: monotone ✓ (all 12 pairs), exactly redundant in $(g_1,g_2)$ ✓, $\mathrm{LOO}(g_1) = \mathrm{LOO}(g_2) = 0$ ✓. The Shapley values are

$$\varphi_{g_1} = \varphi_{g_2} = 0.4167, \qquad \varphi_{g_3} = 4.6667, \qquad \textstyle\sum = 5.5 = v(\mathcal{G}) \;\checkmark$$

and the bound holds: $\varphi_{g_1} = 0.4167 \ge v(\{g_1\})/|\mathcal{G}| = 1/3 = 0.3333$ ✓.

This game does double duty. It is also the **witness that the rejected $\tfrac12$ constant is unattainable** (§3.4): $\tfrac12 v(\{g_1\}) = 0.5 > 0.4167 = \varphi_{g_1}$, so the overstated bound fails on a game that satisfies every hypothesis of the corrected property. Both tables are reproduced in Appendix A and encoded as `NON_MONOTONE_V` and `MONOTONE_V` in `tests/test_property2_counterexample.py`.

**This couples §3 to §2.4.** The coalition-conditional ridge refit is precisely the mechanism that can break monotonicity — a head refit on $S \cup \{g\}$ may score worse than one refit on $S$. So the refit is not only a variance problem for Property 1's CIs; it is the plausible route by which Property 2's hypothesis fails on real data.

**Enforcement.** `tests/test_property2_counterexample.py`.

### 3.3 Monotonicity audit (E0-b)

**Rule.** Monotonicity is an assumption to be **discharged empirically, never asserted**. For each dataset and seed, check all $|\mathcal{G}| \cdot 2^{|\mathcal{G}|-1} = 80$ pairs $(S, g)$, $g \notin S$, for $v(S \cup \{g\}) \ge v(S)$. Report violation count, maximum magnitude, and sources involved, in T2 beside candidate recall.

**Why.** Property 2 and Lemma 1(ii) are only applicable where the audit passes. Where it does not, that is **a finding to report, not a defect to hide**: it would mean the fitted hybrid game is genuinely non-monotone, and negative $\varphi_g$ must be interpreted as real rather than as numerical error.

### 3.4 Lemma 1 ($\varepsilon$-redundancy) — and the two constants that are easy to get wrong

Exact redundancy is a measure-zero condition that will never hold on real data, so Property 2 can *motivate* E2 but can never be *instantiated* by it. Lemma 1 supplies the approximate version E2 actually tests. It necessarily has **two parts under two different assumptions**.

- **(i) LOO collapse.** If $g_1, g_2$ are $\varepsilon$-redundant, i.e. $|v(S \cup \{g_1\}) - v(S \cup \{g_1,g_2\})| \le \varepsilon$ for all $S \subseteq \mathcal{G}\setminus\{g_1,g_2\}$, then $|\mathrm{LOO}(g_2)| \le \varepsilon$. Immediate from the definition.

- **(ii) Shapley floor.** If **additionally** $v$ is monotone and $v(\{g_1\}) \ge c$, then $\varphi_{g_1} \ge c/|\mathcal{G}| - O(\varepsilon)$.

**Derivation of the constant.** Under exact redundancy $g_1$'s marginal contribution vanishes for every coalition already containing $g_2$, so $\varphi_{g_1}$ collapses to a weighted sum over $T \subseteq \mathcal{G} \setminus \{g_1, g_2\}$:

$$\varphi_{g_1} = \sum_T w(|T|)\,\bigl[v(T \cup \{g_1\}) - v(T)\bigr].$$

**Two distinct quantities must not be conflated.** The weights $w(|T|)$ over that index set sum to exactly $\tfrac{1}{2}$ — this is $\Pr[g_1 \text{ precedes } g_2]$ in a uniformly random ordering, and it holds for every $n$ (verified symbolically for $n = 3, 5, 8$). But the term producing the $v(\{g_1\})$ **anchor** is $T = \varnothing$, whose weight is $w(0) = \tfrac{0!\,(n-1)!}{n!} = 1/n$. Under monotonicity every remaining term is $\ge 0$, so the anchor alone gives $\varphi_{g_1} \ge v(\{g_1\})/n = v(\{g_1\})/|\mathcal{G}|$.

**Two rejected formulas.** Both appear in a parallel draft, both look plausible, and both fail against the counterexample of §3.2:

| Rejected | Why it is wrong |
|---|---|
| $\varphi_{g_1} \ge \tfrac{1}{2}v(\{g_1\})$ | Substitutes the total weight mass ($\tfrac12$) for the anchor weight ($1/n$). Overstates the bound by $n/2$ — **2.5× at $n=5$** — and is not recoverable by any choice of $\varepsilon$. On the monotone game of §3.2, $\varphi_{g_1} = 0.4167 < \tfrac12 v(\{g_1\}) = 0.5$: the constant is not merely weak, it is **unattainable**. |
| $\varphi_{g_1} = \tfrac{1}{2}\bigl[v(\mathcal{G}) - v(\mathcal{G}\setminus\{g_1,g_2\})\bigr]$ | Discards every sub-grand coalition. Returns $\tfrac12[0.5 - 5.0] = -2.25$ against a true $\varphi_{g_1} = -0.4167$ — wrong by $5.4\times$. |

**The constant is $1/|\mathcal{G}|$, never $1/2$.**

**Together:** the LOO–Shapley gap for an $\varepsilon$-redundant pair is at least $c/|\mathcal{G}| - O(\varepsilon)$. E2's empirical correlation between Kendall $\tau$ redundancy and the observed gap is then a **predicted consequence of a stated bound**, not a loose analogy.

Monotonicity may be weakened to bounded synergy ($v(S\cup\{g\}) - v(S) \ge -\delta$) at the cost of an additive $\delta$ term; use whichever E0-b supports, and **decide this in Week 3 when E0-b runs**, not in Week 7.

**Enforcement.** `test_pairwise_closed_form_is_wrong`, `test_shapley_floor_constant_is_one_over_n_not_one_half`.

---

## 4. Players (Base Scorers)

Each source is an off-the-shelf recommender. Nothing is invented here.

| ID | Source | Base model | Rationale |
|---|---|---|---|
| $cf$ | Collaborative filtering | **ALS** matrix factorization (implicit), 64 factors | Deterministic, closed-form updates, no learning-rate tuning, seconds on CPU. Justified over BPR-MF in the paper. |
| $ct$ | Content-based | TF-IDF cosine over item metadata (genres, titles, authors, tags) | No embedding drift; reproducible from raw files. |
| $pop$ | Popularity | Global item-frequency with time decay $\tau$ | Cheap sanity signal; also a stress-test player for redundancy against $cf$. |
| $rec$ | Recency | Exponential recency of the user's most recent interaction with an item's content cluster | Contextual, cheap. |
| $seq$ | Sequential | **item2vec** (skip-gram over interaction sequences) | Preserves the CPU-friendly narrative. **SASRec relegated to Appendix B** so the story does not depend on Transformer training. |

Each scorer trains **once** on the train split; its per-user score matrix is cached to `parquet`. All 32 coalitions reuse the cached matrices — the coalition refits are ridge heads over already-materialised tensors and complete in seconds on a laptop CPU.

**Compute-claim scope.** The **Shapley computation** — 32-coalition sweep, per-user attribution, statistics, SignalShap-Fuse — runs on a laptop CPU in seconds per dataset. **Base-scorer training** (especially item2vec) and reference baselines (LightGCN, SASRec) use a single consumer GPU for a few minutes each, one time. Every mention of "laptop CPU, seconds" in the manuscript must carry this qualification.

**Known player overlap — pre-registered, not discovered.** Two pairs overlap *by construction*: (a) $pop$–$cf$, since ALS on implicit feedback is strongly popularity-driven; (b) $rec$–$ct$, since recency is defined over content clusters and is therefore partly a $ct$ derivative. We **predict** high Kendall $\tau$ and large LOO–Shapley gaps for both, and RQ2 tests whether Shapley *recovers* this known structure — a validation of the estimator against a defensible ground truth, not a finding about the datasets. Real deployed hybrids exhibit exactly this overlap, so we disclose rather than redesign. **Without this pre-registration the headline result is open to a charge of circularity.** Note the mild tension with C1's "architecturally distinct" phrasing; resolve it in the C1 wording at drafting time.

---

## 5. Datasets

| Dataset | Domain | Users | Items | Density (as published) | Filters | Density (as used — authoritative) | Split | License |
|---|---|---|---|---|---|---|---|---|
| MovieLens-1M | Movies | 6 040 | 3 706 | ≈ 4.5 % | none | *computed* | Leave-last-out temporal | GroupLens research-use (research/education, redistribution with attribution) |
| Amazon-Book (2018) | Books | ≈ 50 000 subsampled | ≈ 90 000 | ≈ 0.05 % | seeded subsample; $k$-core **only** under §6.2 | *computed* | Leave-last-out temporal | Amazon Reviews (Ni et al., 2019), academic use per host conditions |
| LastFM-2K | Music | 1 892 | 17 632 | ≈ 0.28 % | none | *computed* | Leave-last-out temporal | HetRec 2011 / GroupLens, non-commercial research |

**Splits.** Last interaction → test, second-to-last → validation, remainder → train. Timestamp ties resolved by `(timestamp, original_record_index)`. Raw files, subsampling scripts and seed, and split manifests all ship in the Zenodo artefact.

---

## 6. Density: Reporting and the Ordering Invariant

### 6.1 Density is computed, never quoted

**Rule.** Every density figure in the manuscript is computed from the **post-split, post-filter** matrices by `src/signalshap/data/stats.py`, written to `artefacts/dataset_stats.json`, and read from there. Published figures appear only in the provenance column of T2.

**Why.** The 50k Amazon-Book subsample already moves density off its published $0.05\%$ *before* any $k$-core is considered. Quoting the source-paper figure is unsafe even on the unfiltered plan.

### 6.2 The density-inversion hazard, and the invariant

**The problem.** $k$-core repairs recall by the *same mechanism* that destroys C3: it raises density. The magnitude is not marginal. On the $\approx 50{,}000$-user / $\approx 90{,}000$-item / $\approx 2.25$M-interaction subsample:

| Filter | Users | Items | Density | vs LastFM-2K ($\approx 0.28\%$) |
|---|---|---|---|---|
| none | 50 000 | 90 000 | $\approx 0.05\%$ | sparsest ✓ narrative holds |
| $k=5$ | $\approx 27{,}500$ | $\approx 25{,}200$ | $\approx 0.25\%$ | **borderline** — $0.90\times$, essentially ties |
| $k=10$ | $\approx 15{,}000$ | $\approx 10{,}800$ | $\approx 0.76\%$ | **inverted** ✗ — $2.73\times$ *denser* than the "medium" dataset |
| $k=20$ | $\approx 7{,}500$ | $\approx 4{,}500$ | $\approx 2.33\%$ | **badly inverted** ✗ — $8.33\times$, approaches ML-1M |

> ⚠️ **These retention rates are placeholders, and the table is non-authoritative.** They are order-of-magnitude estimates written to establish that the hazard is *real and large*, not measurements. **No filter decision may be taken from this table.** The invariant of rule (b) is checked against measured post-filter statistics only.
>
> **Week-1 obligation (blocking).** `scripts/measure_kcore_sweep.py` recomputes true retention and density for every $k \in \{3,5,8,10,20\}$ on the real Amazon-Book subsample, writes `artefacts/kcore_sweep.json`, and **overwrites this table with the measured values**, replacing this warning with the measurement date and corpus hash. Until that file exists, `tests/test_density_ordering.py::test_kcore_sweep_is_measured_not_estimated` fails whenever any $k$-core is configured, so rung 3 cannot be reached on placeholder numbers.
>
> **Why an extra gate.** The ordering invariant alone is insufficient here. It validates whichever densities it is handed — so if `dataset_stats.json` were ever built from estimates, or if a filter decision were justified from *this* table while the invariant checked a different quantity, the test would pass while the reasoning rested on numbers nobody measured. The estimates and the measurements must be structurally impossible to confuse, hence a separate provenance flag rather than a comment. The direction of error also matters: these figures assume retention rates that could easily be off by a factor of two, and §6.2's whole conclusion (that $k=10$ inverts the ordering) is a claim about real corpus structure that has never been checked against the corpus.

So $k=10$ — a routine, defensible-looking choice — makes "dense movies / sparse books / medium music" **factually false**, and checkable from T2's own density column. That is worse than a blunted contrast: it is an inverted ordering presented as a finding.

**Three binding rules.**

- **(a) $k$ is capped by the ordering, not chosen for convenience.** Select the largest $k \in \{3,5,8,10\}$ whose **measured** post-filter density — from `artefacts/kcore_sweep.json`, never from the placeholder table above — preserves $\rho_{\text{Amazon-Book}} < \rho_{\text{LastFM-2K}} < \rho_{\text{ML-1M}}$ with $\ge 1.5\times$ margin between adjacent datasets. If no $k$ both clears the recall gate and preserves the ordering, **rung 3 is unavailable** — fall through to Gowalla.
- **(b) The ordering is a CI invariant, not a caution.** `tests/test_density_ordering.py` asserts the strict ordering and margins against as-used statistics. Any filter that inverts or compresses the ordering fails the build. *Prose warnings do not survive a Week-6 deadline; a red test does.* **Scope limit:** this test validates whatever densities it is given; it cannot tell measured values from estimates. Provenance is enforced separately by `test_kcore_sweep_is_measured_not_estimated` and by the `source: "measured"` field required in `dataset_stats.json`.
- **(c) Downstream claims are regenerated, not hand-edited.** If any filter is applied, recompute density and re-propagate to T2, the introduction's framing sentence, §2.2's motivating figure, and C3's wording — all from the same JSON.

**Artefact record.** The chosen rung, its date, triggering recall numbers, filter parameters, and pre/post-filter density for every dataset.

---

## 7. Baselines and the Evaluation Protocol

**Attribution baselines.** LOO on $\mathcal{G}$ (the industry default and the target of Property 2); forward stepwise selection; permutation importance; Monte-Carlo Shapley at matched budget.

**Recommender baselines.** Each source in isolation; uniform-weight fusion; globally-tuned fusion (one weight vector for all users); LightGCN (GPU, once); SASRec (GPU, once, Appendix B).

### Full-catalog reporting

**Rule.** **T5 reports full-catalog NDCG@10 / Recall@20 / MRR@10 for every method, including SignalShap-Fuse**, which assigns $-\infty$ to items outside $C_u$.

**Why.** If SignalShap-Fuse is capped by candidate recall while LightGCN ranks the full catalogue, the two numbers differ by the **denominator**, not by the fusion mechanism, and the comparison is meaningless. Scoring outside-$C_u$ items as misses makes the recall ceiling a **visible, quantified cost of the method** — consistent with E0's purpose — and puts E0's recall number and T5's headline number on the same scale.

**Why not restrict LightGCN to $C_u$.** Disclosable, but simply a weaker experiment: it handicaps a strong baseline by confining it to a pool built from five *other* scorers' top-lists, and invites the reviewer to ask what the unhandicapped number was.

**Two-protocol split.** $v(S)$ remains **fixed-candidate within $C_u$** — that is required for coalition-independence and is the game's definition. Only *reporting* in T5 is full-catalog. The methodology section and T5's caption must state this split and its reason.

---

## 8. Metrics

- **Ranking.** NDCG@10 (primary — it is the characteristic function), Recall@20, MRR@10.
- **Coverage/diversity.** Catalogue coverage, intra-list diversity, Gini of item exposure.
- **Attribution.** LOO share, Shapley share, LOO–Shapley gap, redundancy indicator (Kendall $\tau$ between per-user source score vectors), segment-level heterogeneity.
- **Preconditions.** Candidate recall; $|C_u|$ distribution; monotonicity-violation count.

---

## 9. Research Questions

- **RQ1.** Does casting hybrid recommendation as a five-player cooperative game with fixed, coalition-independent-candidate NDCG@10 as characteristic function permit an *exact* additive decomposition of ranking-quality uplift?
- **RQ2.** Does source-level Shapley attribution differ from LOO, and is the difference explained by observed redundancy? *(See the pre-registered $pop$–$cf$ and $rec$–$ct$ expectations in §4.)*
- **RQ3.** Is source attribution homogeneous across users, or does global attribution conceal opposing segment-level attributions?
- **RQ4.** Can segment-adaptive fusion turn Shapley attribution into a measurable NDCG@10 improvement over globally-tuned fusion at negligible ($O(1)$) additional inference cost?

---

## 10. Experimental Plan

- **E0-a — Candidate diagnostics (precondition to everything).** Per dataset: distribution of $|C_u|$ and candidate recall at the pre-registered $N_{\max}^{(d)}$. **Run on Amazon-Book first, Week 1.**
- **E0-b — Monotonicity audit (precondition to Property 2).** All 80 $(S,g)$ pairs per dataset per seed; violation count, max magnitude, sources. Decide Lemma 1(ii)'s assumption here.
- **E1 — Source share (→ RQ1).** $\varphi_g$ on all three datasets, **with seed-based CIs in the main text**. Verify $\sum_g \varphi_g = v(\mathcal{G})$ to floating-point tolerance.
- **E2 — LOO vs Shapley (→ RQ2).** Per $(dataset, source)$: LOO share, Shapley share, gap. Kendall $\tau$ between per-user source score vectors for every pair; correlate redundancy with the gap. **Primary test: within-user permutation, 10 000 shuffles.**
- **E3 — Segment heterogeneity (→ RQ3).** Segments by activity quantile and recency skew. **Primary test: between-segment permutation, 10 000 shuffles**; report $d_z$.
- **E4 — SignalShap-Fuse (→ RQ4).** Per-segment fusion weights learned on validation, evaluated on test, against uniform, globally-tuned, LightGCN, and (Appendix B) SASRec. **Primary test: Wilcoxon signed-rank on paired per-user NDCG@10, Holm–Bonferroni over the declared family.**
- **E5 — Robustness (6 stress tests).** (i) $|C_u| \in \{0.5, 1, 2\} \times N_{\max}^{(d)}$ — **candidate recall reported per cell**, since changing $|C_u|$ moves the ceiling and hence the level of $v$; without it the cells are not comparable; (ii) five seeds; (iii) monotone rescalings (identity, log1p, rank); (iv) cold-user fallback ($z = 0$); (v) per-source Gaussian noise; (vi) $\lambda \in \{0.1, 1, 10\}$ — sensitivity only, never selection.
- **E6 — Ablation.** Drop each source; report redistribution of Shapley values over the remaining four.
- **E7 — Actionability case study.** Disable the lowest-Shapley source at deployment; quantify engineering saving and the (expected non-significant) NDCG delta.
- **E8 — Appendix B.** (a) Regenerated-candidates ablation — quantifies the bias avoided by §2.1. (b) SASRec as $seq$. (c) Pairwise-logistic vs ridge.

---

## 11. Statistical Protocol

- **Unit of analysis.** The user, always.
- **Seeds.** $\{42,43,44,45,46\}$; figures/tables report mean ± std across seeds.
- **Primary tests.** Paired NDCG@10 → Wilcoxon signed-rank. LOO–Shapley gap → within-user permutation (10 000). Segment heterogeneity → between-segment permutation (10 000).
- **Effect sizes.** Cohen's $d_z$ beside every Wilcoxon result.
- **Multiplicity.** Holm–Bonferroni, with **family size *and composition* declared at the top of every table**. For T7 the family is $m = 4$ per dataset: uniform, globally-tuned, LightGCN, and SASRec — **the last reported in Appendix B**. Mixing a main-text family with an appendix member is defensible (the family is the set of comparisons made, wherever printed) but must be stated, or the family size looks chosen after the fact.
- **Secondary (Appendix B).** Paired $t$; bootstrap 95% CIs (10 000 resamples); Wilcoxon tie sensitivity.
- **Reporting rule.** Every statistical claim traces to a JSON carrying raw statistic, corrected $p$, effect size, family size, and seed manifest.

---

## 12. Paper Structure

Six sections, Springer *Discover AI* research-article format, ≈ 8 500 words.

- **§1 Introduction** (≈ 900 w.) — motivation, source-attribution gap, thesis, C1–C6, and an explicit "what is *not* in this paper" paragraph (GNN players, Transformer players, causal attribution → future work).
- **§2 Literature Review** (≈ 1 400 w.) — hybrid recommenders; feature-level XAI (SHAP, LIME, IG) and why source-level Shapley is a different game; ablation practice; cooperative-game applications in ML; DyHuCoG cited **only as motivation**.
- **§3 Methodology** (≈ 2 200 w.) — game formalism, coalition-independent candidates, base-scorer catalogue with ALS-vs-BPR-MF and item2vec-vs-SASRec justifications, Properties 1–3, Lemma 1, Remark 1, SignalShap-Fuse. States the "exact given the fitted $v$" qualification and the $v_0$-invariance note.
- **§4 Experimental Results** (≈ 2 400 w.) — **opens with E0 diagnostics** (candidate recall, $|C_u|$, monotonicity violations) as the ceiling bounding everything after; then E1–E7, F1–F7, T1–T8.
- **§5 Discussion** (≈ 900 w.) — actionable interpretability, engineering implications, positioning against SHAP/LIME/IG, restatement of the pre-registered redundancy expectations when interpreting F4.
- **§6 Conclusion & Future Work** (≈ 400 w.) — privacy-bearing signals, feature-combination and cascade hybrids, GNN/Transformer players, causal extension.

Plus abstract (≤ 250 w.), 5–7 keywords, Declarations, References with DOIs, **Appendix A** (derivations of Properties 1–3 and Lemma 1, including the §3.2 counterexample table), **Appendix B** (regenerated-candidates ablation, SASRec, pairwise-logistic, secondary statistics, per-dataset hyperparameters, $\lambda$ selection curve).

---

## 13. Figures and Tables

**Figures.** F1 workflow (five sources → 32 coalitions on coalition-independent candidates → exact Shapley → segment-adaptive fusion). F2 per-source Shapley shares, three datasets, **with seed CIs**. F3 LOO-vs-Shapley scatter with permutation $p$. F4 redundancy heatmap (Kendall $\tau$). F5 segment radar plots. F6 SignalShap-Fuse gain curve and lift over globally-tuned fusion. F7 robustness small-multiples.

**Tables.**

- **T1.** Positioning against SHAP, LIME, IG, DyHuCoG, LightGCN, SASRec.
- **T2.** Dataset stats + split manifest + license + $N_{\max}^{(d)}$ + **candidate recall** + $|C_u|$ mean ± std + **monotonicity violations**. *The recall column is the ceiling on every metric in T5–T7; the monotonicity column is the precondition for Property 2. Both must be inspected before any attribution number is interpreted.*
- **T3.** Notation.
- **T4.** Per-source computational cost (train once + cache), including wall-clock at the chosen $N_{\max}^{(d)}$.
- **T5.** Main ranking results. *Caption: all methods full-catalog; SignalShap-Fuse scores outside $C_u$ as $-\infty$; $v(S)$ remains fixed-candidate by definition of the game.*
- **T6.** LOO share vs Shapley share per (dataset, source), **with main-text seed CIs**.
- **T7.** SignalShap-Fuse vs baselines, Wilcoxon $p$ (Holm–Bonferroni) and $d_z$. *Caption declares family size and composition: $m=4$ = {uniform, globally-tuned, LightGCN, SASRec (App. B)}.*
- **T8.** Robustness summary, **with a candidate-recall column per cell** for the $|C_u|$ sweep.

---

## 14. Reproducibility Artefact

- **Repository.** Public GitHub `signalshap`, MIT, created at submission.
- **Cached score matrices.** Every base scorer's per-user matrix in `parquet`.
- **DOI archive.** Zenodo snapshot at submission, cited in Data Availability.
- **Docker.** CPU image for the Shapley game; GPU image for one-time base-scorer training.
- **One command.** `make reproduce` — raw data to every figure and table in ≤ 60 min on a modern laptop (Shapley step), plus a one-time GPU pass.
- **Measured-not-estimated.** `artefacts/dataset_stats.json` and `artefacts/kcore_sweep.json` each carry `source`, `measured_at`, and `corpus_hash`. Any spec table derived from them is regenerated, never hand-maintained.
- **Determinism.** All seeds pinned; tie-breaking by `(timestamp, original_record_index)`; frozen $v_0$ permutation serialised; `configs/frozen.yaml` holds $N_{\max}^{(d)}$, $\lambda$, and the $v_0$ seed.

### Repository layout

```
signalshap/
├── README.md
├── pyproject.toml / poetry.lock
├── Dockerfile.cpu               # Shapley game, statistics, figures
├── Dockerfile.gpu               # one-time base-scorer training
├── Makefile                     # make reproduce | figs | tables
├── LICENSE                      # MIT
├── CITATION.cff                 # points to Zenodo DOI
├── data/
│   ├── raw/                     # download scripts only
│   └── processed/               # cached splits, cached score matrices
├── src/signalshap/
│   ├── data/                    # loaders, temporal split, tie-breaking, stats.py (as-used density)
│   ├── scorers/                 # als, tfidf, popularity, recency, item2vec
│   ├── candidates/              # union-of-top-N-per-source + truncation rule
│   ├── fusion/                  # ridge + segment-adaptive + pairwise-logistic (appendix)
│   ├── game/                    # coalitions, characteristic function, exact Shapley
│   ├── attribution/             # LOO, forward, permutation, MC Shapley
│   ├── segments/                # segment definitions + permutation test
│   ├── stats/                   # Wilcoxon, permutation, Holm–Bonferroni, dz, bootstrap
│   └── plots/                   # matplotlib for F1–F7
├── configs/
│   ├── frozen.yaml              # N_max per dataset, frozen lambda, v_0 permutation seed
│   ├── e0_diagnostics.yaml      # candidate recall (E0-a) + monotonicity audit (E0-b)
│   ├── e1_source_share.yaml ... e7_actionability.yaml
│   └── e8_appendix_b.yaml       # regen-candidates, SASRec, pairwise-logistic
├── tests/
│   ├── test_property2_counterexample.py   # monotonicity hypothesis + 2 rejected formulas
│   ├── test_density_ordering.py           # C3 density-contrast invariant, as-used stats
│   ├── test_candidates_invariance.py      # identical C_u across 32 coalitions + 5 seeds + cap
│   └── test_efficiency.py                 # Property 1 to floating-point tolerance
├── artefacts/                   # figures, tables, JSON results, dataset_stats.json
└── paper/                       # LaTeX sources + Springer template
```

---

## 15. Nine-Week Timeline

Nine weeks is a **floor**, not a comfortable estimate.

- **Week 1 — Scaffolding, pre-registration, gates.** Repo, CI, Docker, download scripts, temporal split, tie-breaking. Candidate builder **including the truncation rule**, with its three tests. **Pre-register $N_{\max}^{(d)}$ and freeze `configs/frozen.yaml`.** **Run E0-a on Amazon-Book first.** Serialise the $v_0$ permutation. Build `artefacts/dataset_stats.json` (with `source: "measured"`) and **turn on `test_density_ordering.py` before any filter decision**. **Run `scripts/measure_kcore_sweep.py` and overwrite §6.2's placeholder table with measured values** — the estimates there have never been checked against the corpus, and §6.2's conclusion depends on them. Property-1 smoke test plus `test_property2_counterexample.py`.
- **Week 2 — Base scorers.** ALS, TF-IDF, popularity-with-decay, recency, item2vec; cache all three datasets. Documented comparison runs against BPR-MF (discarded) and SASRec (moved to Appendix B).
- **Week 3 — Game core, $\lambda$ freeze, fusion decision.** Fixed-candidate NDCG@10, coalition enumeration, exact Shapley, LOO/forward/permutation/MC baselines. **$\lambda$ pilot → freeze.** Ridge vs pairwise-logistic smoke test. **Run E0-b as soon as $v$ is computable and decide Lemma 1(ii)'s assumption now** — nearly free here, collides with the writing pass if deferred.
- **Week 4 — E1 + E2.** All three datasets. F2, F3, F4, T6, with main-text CIs.
- **Week 5 — E3 + E4.** Segments and SignalShap-Fuse; implement the full-catalog T5 protocol here. F5, F6, T5, T7.
- **Week 6 — E5 + E6.** Six-way robustness (with per-cell recall and the $\lambda$ sweep) and ablations. F7, T8.
- **Week 7 — E7 + E8 + Appendix A.** Actionability, appendix experiments, and the Lemma 1 write-up. *Budget two days, not half a day:* if E0-b found material violations, the lemma restates under bounded synergy with $\delta$ carried through, and the discussion's reading of every negative $\varphi_g$ changes with it.
- **Week 8 — Writing pass 1.** §1–§4. Cross-check every number against `artefacts/`. Verify "exact given the fitted $v$" is used consistently and no internal vocabulary has leaked.
- **Week 9 — Writing pass 2 + submission.** §5, §6, abstract, declarations, licenses in T2, LLM-usage block, Zenodo snapshot + DOI, live SJR re-check, Springer LaTeX validator. Submit.

---

## 16. Submission Checklist

- [ ] LaTeX source, Springer template; abstract ≤ 250 words; 12 pt Helvetica/Arial; ≤ 3 heading levels.
- [ ] Abbreviations defined at first mention; figures with Arabic numerals (EPS/TIFF); tables built with the table function.
- [ ] References with DOIs, `[n]` bracket citations.
- [ ] **Funding statement** (mandatory).
- [ ] **Ethics statement** — *not applicable* (no human-subjects or biological material; three public benchmarks under the licenses in §5).
- [ ] **Data availability** — Zenodo DOI **and** the license for each dataset.
- [ ] **Competing interests** — none declared.
- [ ] **Author contributions** — CRediT (§17).
- [ ] **LLM-usage disclosure** — per Springer's 2024–2026 policy.
- [ ] **ORCID** for the corresponding author.
- [ ] **SJR/CiteScore re-verified** against live Scimago within 24 h of submission.
- [ ] Abstract contains "exact Shapley over 32 coalitions".
- [ ] All CI tests green; `artefacts/` regenerated; no hand-edited numbers.

---

## 17. Author Roles (CRediT)

- **Mouad Louhichi.** Conceptualisation, methodology, software, formal analysis, investigation, writing — original draft, visualisation, project administration.
- **Redwane Nesmaoui.** Software (base scorers, statistical package), validation, data curation, writing — review & editing.
- **Mohamed Lazaar.** Supervision, methodology, resources, writing — review & editing, funding acquisition.

---

## 18. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Reviewer constructs a counterexample to Property 2 | (mitigated) | **Would have been critical** — a false theorem | Monotonicity hypothesis explicit; counterexample stated openly in §3.2 and Appendix A; pinned in CI; E0-b discharges it empirically. |
| Wrong constant or closed form re-enters Lemma 1 | (mitigated) | High | §3.4 derives $1/|\mathcal{G}|$ and names both rejected formulas; two regression tests. |
| Amazon-Book recall fails the gate even at raised $N_{\max}$ | Medium | Medium | Four-rung ladder (§2.2); rung 1 bounded by the compute claim. |
| Placeholder $k$-core estimates mistaken for measurements | Medium | Medium | §6.2 table flagged non-authoritative; `kcore_sweep.json` required with provenance fields; `test_kcore_sweep_is_measured_not_estimated` blocks rung 3 until measured (Week-1 obligation). |
| $k$-core remedy inverts the density ordering and falsifies C3 | (mitigated) | Would have been high | $k$ capped by the invariant, rung demoted, `test_density_ordering.py`, all figures regenerated (§6.2). |
| $\lambda$ tuned per coalition inflates $v(\mathcal{G})$ | (mitigated) | Would have been high | Frozen $\lambda$; E5-vi reports sensitivity without selecting (§2.4). |
| T5 compares candidate-restricted against full-catalog methods | (mitigated) | Would have been high | Full-catalog for every method; $-\infty$ outside $C_u$ (§7). |
| Grand-coalition candidate bias | (mitigated) | Would have been high | Union-of-top-N (§2.1); old design retained as E8-a. |
| Redundancy finding called circular | Medium | Medium | $pop$–$cf$ and $rec$–$ct$ overlap pre-registered in §4, restated in the discussion. |
| Fitted $v$ produces negative $\varphi_g$ | Medium | Low | Expected under a non-monotone game; E0-b quantifies, main-text CIs carry the error. |
| Reviewer requests a fourth dataset | Medium | Low | Preprocessed Gowalla split held ready. |
| "Five signals is arbitrary" | Medium | Medium | Justify via Burke's hybrid-recommender taxonomy. |
| Nonlinear score maps | Low | Low | Remark 1 declares affine-only invariance; E5-iii reports empirical sensitivity. |
| Scaling beyond five sources | Medium | Low | Discuss hybrid exact-plus-MC scheme; frame as future work. |
| Cache size for Amazon-Book | Low | Low | Subsample to 50k users; ship seed and manifest. |
| Springer editorial screen rejection | Low | High | Pre-apply §16; run the LaTeX validator. |

---

## 19. Provenance of the Current Design

Preserved so that fixes are not silently reverted. Each entry is a **real error that was made and corrected**, not a hypothetical.

| # | Error in an earlier draft | Correction | Where |
|---|---|---|---|
| 1 | Candidates drawn from the grand-coalition scorer | Union-of-top-$N$-per-source; old design becomes ablation E8-a | §2.1 |
| 2 | Property 2 stated without monotonicity — **false**; $\varphi = -0.4167$ on a game satisfying every hypothesis | Monotonicity hypothesis added; counterexample published; E0-b audit | §3.2, §3.3 |
| 3 | Floor constant given as $\tfrac12 v(\{g_1\})$ | Correct constant is $v(\{g_1\})/|\mathcal{G}|$; the $\tfrac12$ conflates total weight mass with the anchor weight; overstates by $2.5\times$ at $n=5$ and is unattainable | §3.4 |
| 4 | Pairwise closed form $\tfrac12[v(\mathcal{G}) - v(\mathcal{G}\setminus\{g_1,g_2\})]$ | Rejected: $-2.25$ vs a true $-0.4167$ | §3.4 |
| 5 | $\lambda$ tunable per coalition | Frozen once; bias grows with $|S|$ | §2.4 |
| 6 | Single $N_{\max}=200$ with an unreachable recall gate | Per-dataset pre-registration + four-rung ladder | §2.2 |
| 7 | $k$-core ranked second in the ladder | Demoted below ceiling-reporting; can invert the density ordering | §2.2, §6.2 |
| 8 | Density quoted from source papers | Computed as-used from `dataset_stats.json` | §6.1 |
| 9 | $v(\varnothing)=0$ "pinned by construction", ambiguous | Frozen permutation → exact, per user; plus $v_0$-invariance note | §2.5 |
| 10 | Baseline evaluation protocol unstated | Full-catalog for all methods | §7 |
| 11 | Redundancy presented as a discovery | Pre-registered in §4 as a tested hypothesis | §4 |
| 12 | $C_u$ overshoot unhandled | Deterministic truncation rule | §2.3 |
| 13 | "Exact Shapley" implying error-free attribution | "Exact given the fitted $v$"; main-text CIs | §2.7 |
| 14 | Eight-week timeline | Nine weeks, floor | §15 |
| 15 | Monotone-repair $\varphi$ asserted without its payoff table | Full table shown, mechanically verified, doubles as the witness that $\tfrac12$ is unattainable | §3.2 |
| 16 | $k$-core estimates presented in a table indistinguishable from measurements | Table flagged non-authoritative; measurement gated by CI and a Week-1 obligation | §6.2 |
| 17 | `ct` and `rec` reported as null on `gowalla_ts` and `amazon_video_games` when they had in fact been given no input at all (timestamped loaders built their `Dataset` with `meta=None`, so `ct` was all-zero and `rec` collapsed to one content cluster; the two players' Shapley entries were bit-identical on both corpora) | Structural nulls separated from evidential ones by `scorers/audit.py`, which measures each source's ability to reorder the candidate slices before any coalition is scored; warns by default, fatal under `SIGNALSHAP_STRICT_DATA=1`; content supplied from Gowalla lat/lon (nested offset geo-cells) and the Amazon product-metadata dump | §4 |
| 18 | Memory sizing implemented in `run_full_revision.py` only, so `run_study.py` loaded Gowalla at its full 52,985 x 121,866 (129 GB of score matrices) and was OOM-killed | Sizing extracted to `signalshap/memory.py` and shared by both entry points; corpora sized before any work begins; `check_fits` refuses to start a run that will not fit; CI asserts neither script keeps a private copy of the arithmetic | §5 |
| 19 | `gowalla_ts` and `amazon_video_games` absent from `frozen.yaml` (the config listed `gowalla`, the loader registers `gowalla_ts`), so both silently took a 200 fallback and failed the recall gate at 0.132 and 0.349 while still writing complete artefacts | `Experiment` raises on an unregistered corpus before loading anything; N_max registered for both with a dated amendment recording the reason; `test_nmax_registration.py` asserts every study corpus is registered and that rung-2 exemptions are declared rather than assumed | §2.2 |
| 20 | Gate still unmet after registration (gowalla_ts 0.355, amazon_video_games 0.588); the tempting fix — nudge amazon's N_max 600 → 800 — would clear it by moving a pre-registered parameter 6% after seeing the threshold it gates | Ladder applied per corpus on a catalogue-fraction rule fixed before the recall numbers were known: gowalla_ts takes rung 1 (2500 → 11623, since 2500 was 3.65% of catalogue against ml_1m's 16.98%, inherited from the 39k untimestamped split), amazon_video_games takes rung 2 unchanged (600 already *is* the rule's value, 597). `reportable`/`gate_passes` separated so an exempt corpus is retained for relative contrasts and excluded from absolute NDCG, never recorded as passing | §2.2 |
| 21 | `dataset_stats.json` overwritten by each single-corpus run, leaving one corpus; this silently disarmed the density-ordering invariant, which SKIPS when fewer than three corpora are present, and reduced T2 to one row | `build_dataset_stats` merges with the existing file instead of replacing it; `_meta.corpora_in_this_run` records what each run contributed | §6.1 |
| 22 | `REQUIRED_ORDER` in the density test still named the withdrawn LightGCN corpora, so the guard skipped green while guarding nothing — the exact hazard its own comment warned about | Repointed to the three timestamped corpora; invariant verified live (36× spread, 6.3×/5.7× adjacent margins) | §6.2 |
| 23 | `FrozenConfig.save()` regenerated `_note` from a hardcoded default, destroying amendments 1 and 2 — the entire audit trail for post-registration N_max changes — while leaving a well-formed file | `save()` preserves any existing note and only appends; `test_save_preserves_the_amendment_trail` pins it | §2.4 |
| 24 | Empty-coalition baseline drawn from `np.random.default_rng`, whose stream is reproducible only within a NumPy version series. Two machines with identical code, config, seed and byte-identical candidate sets produced `v0` 0.005033 vs 0.006731, propagating to `v(G)` 0.05253 vs 0.05030, flipping `phi_ct` across zero and moving monotonicity 16/80 vs 23/80 | Baseline derived by hashing `(seed, user, item)` with blake2b — stable across NumPy versions, platforms and Python builds. Also fixes a second defect: the old code advanced one Generator inside the user loop, so each user's permutation depended on how many users preceded it. Environment versions now recorded in `study_manifest.json` | §2.5 |
| 25 | Monotonicity reported as a bare count, but most violations sit far below the scale of `v` (median 4.5e-4 against NDCG ~0.05), so the headline number flips on numerical noise | Audit stratifies by magnitude and reports `violations_material` (>1e-3) alongside the raw count. Both divergent runs had **6** material violations despite raw counts of 16 and 23 — the Property 2 conclusion rests on the stable statistic | §2.6 |
| 26 | Manuscript claimed `phi` is invariant to the empty-coalition baseline "since `b_u` cancels in every marginal". FALSE: it cancels only for non-empty `S`. The marginal at `S=empty` is `v({g}) - 0`, which retains the baseline, and `w(0)=1/n`, so changing the baseline shifts every `phi_g` by exactly `-delta/n`. Two reviewers independently derived this from the published tables (predicted `-0.00021`, observed `-0.000204..-0.000212`), and it explains the constant offset between the main and retirement tables | Claim withdrawn and replaced with a measured sensitivity analysis (seed 42 vs 999: `delta v0 = -0.000796` -> uniform `+0.00015926` shift, agreeing to 8 dp). Baseline documented as a declared modelling choice; `phi_ct` explicitly disclaimed as sign-unstable. Pinned by `test_shapley_shifts_by_delta_over_n_when_baseline_changes` and the counterfactual test | §2.5 |
| 27 | Eq. (8) cited Sundararajan's Shapley--Taylor index while computing the Grabisch--Roubens Shapley interaction index. At `n=5` the weights are `0.25, 1/12, 1/12, 0.25` versus `0.4, 0.1, 1/15, 0.1` -- up to 2.5x apart | Relabelled to Grabisch--Roubens with the correct citation; the computation is a valid interaction index and is retained. Noted that it does not satisfy interaction efficiency, and that only the redundancy ranking is used. Table 4 caption corrected: only `cf-pop` of the two most-negative pairs was pre-declared, and `rec-ct` is slightly positive | §9.2 |
| 28 | `N_max` fractions quoted as 3.65% and 17% of the Gowalla catalogue; with the 82,134-item corpus finally used they are 3.04% and 14.2% | Corrected, and the discrepancy explained: 11,623 was derived from a 68,443-item extract and deliberately not re-derived after the corpus grew, since adjusting `N_max` once recall is known is the selection the ladder exists to prevent | §2.2 |
| 29 | Eq. (1) truncation tie-breaks on source order, so relabelling sources can change `C_u` | Measured over all 120 permutations (ml_1m, N_max=600, 60 probe users): only 1 reproduces the canonical sets exactly, but worst-case mean Jaccard is 0.9966 — the tie-break moves ~0.3% of candidates. Dependence disclosed, magnitude bounded, source-symmetric key recommended for a redesign | §2.3 |
| 30 | Algorithm 1 used an ambiguous `y_u` in the Gram accumulation, leaving it unclear whether heads were fitted on validation or test targets, and omitted the per-user Shapley loop | Rewritten with explicit `y^val_u` and `y^te_u`, dimensioned identity `I_{|S|}`, tie tolerance, empty-coalition scoring shown rather than asserted, and the per-user loop added | §4 |
| 31 | Empty-coalition baseline was a single sampled permutation. Because it cancels only for non-empty `S`, changing it shifted every `phi_g` by `-delta/n` and moved `phi_ct` across zero — so a sign-based finding depended on which permutation was drawn | Replaced by the closed-form **expected** random-ranking payoff, `b_u = (1/|C_u|) * sum_{r<=K} 1/log2(r+1)`. Deterministic, no seed, identical across machines. Measured seed-to-seed `max|dphi| = 0.00e+00` (was 1.6e-4). Sampled path retained as `baseline="sampled"` for reproducing archived artefacts | §2.5 |
| 32 | Paper conflated ranking-stage and end-to-end LOO. `LOO_e2e` equals the observed retirement loss **by construction**, so presenting it as a predictor of that loss is a tautology | Both defined in Eq. (loo) and distinguished throughout. Table 8's LOO column is `LOO_rank`, computed on the same fixed-candidate game as the Shapley column — a like-for-like comparison, and a non-trivial result: a quantity needing no re-retrieval predicts the expensive end-to-end outcome | §3 |
| 37 | The manuscript reported a "uniform semivalue" as a third cooperative value alongside Shapley and Banzhaf, and claimed it violates efficiency. Both were false: p_k = 1/n **is** the Shapley weighting, since \|S\|!(n-\|S\|-1)!/n! = 1/(n·C(n-1,\|S\|)). Our own artefact had `semivalue_uniform` equal to `shapley` to 0.0 in every coordinate on every corpus, and we had read that identity as evidence of robustness | Withdrawn in text and code. `binomial_semivalue(v, q)` added; comparators are now Banzhaf (q=0.5) and q ∈ {0.25, 0.75}, which genuinely differ (sums 0.05167 / 0.06992 / 0.03378 against Shapley 0.05190 on ml_1m) while all four preserve the ordering. `tests/test_semivalues_and_symmetry.py` asserts the identity for the size-uniform case and non-identity for the binomial ones | §10.2 |
| 38 | Candidate truncation broke ties by (best per-source rank, **position in SOURCES**, item index), so relabelling the players could change the game. Previous disclosure measured only candidate-set Jaccard (worst 0.9966), which is not the same quantity as attribution stability | Truncation key replaced with the source-order-invariant sum of reciprocal ranks. Measured on ml_1m seed 42: max \|Δφ\| = 2.8e-5, τ = 1.00, v(G) 0.05190 → 0.05187, recall unchanged at 0.748, same material flip on `cf`. Artefact `candidate_rule_ablation_ml_1m.json`. Tables 6-8 were produced under the legacy key and this is disclosed in §4.1; a full three-corpus regeneration was not run | §2.3 |
| 39 | Abstract and C4 said Shapley picks the observed cheapest source on 0-30% of seeds; Table 8 says 0%, 50%, 0% | Corrected to 0-50% throughout, with Wilson 95% intervals added to Table 8 ([72,100] vs [0,28] on ml_1m and gowalla; [49,94] vs [24,76] on amazon, which does **not** separate) | §11 |
| 40 | Algorithm 1 and Table 2 still carried the sampled-baseline machinery (baseline seed, π⁰_u) after Eq. (4) replaced it with the deterministic expectation, and Table 7's caption attributed a +0.00038 offset to "its own baseline permutation". Two incompatible definitions of the method in one manuscript | Baseline seed and π⁰_u removed from Algorithm 1 and Table 2; Table 7 regenerated from `e12_retirement_ml_1m.json` under the deterministic baseline, where its ranking-stage columns are **identical** to Table 6 and the offset does not exist | §2.5 |
| 41 | The grand-coalition-pool and per-coalition-λ "bias" arguments were listed in Limitations as mathematical and corpus-independent. Neither is proved: nothing shows a G-selected pool must raise v(G) for arbitrary relevance, nor that tuning optimism must grow with \|S\| | Both recast as construct-design choices that remove a confound, with the grand-pool claim now backed by the measured E8-a ablation (recall 0.748 → 0.807, v(G) +0.00411, φ_ct flips sign) rather than asserted | §2.1 |
| 42 | Appendix A retained a recall-gate-violating Friedman test on the grounds that its conclusion was negative. Admissibility cannot depend on the outcome | Test deleted. The numbers are noted in prose for the record, with the reason for removal stated | §2.2 |
| 43 | Table 6's `LOO_rank` and gap columns were seed-42 point estimates with no interval, and the caption inferred per-seed sign stability from a CI for the mean | Ten-seed intervals computed on ml_1m (`final_loo_gap_ci.json`). Material `cf` gap +0.02033 [+0.01995, +0.02071], 10/10 positive. Found that `LOO_rank(ct)` is positive on only 7/10 seeds and `LOO_rank(rec)` on 5/10, so the two negligible flips on this corpus are seed noise; now stated in the caption instead of implied stability | §11 |
| 44 | Interaction indices reported from one seed with no uncertainty | Ten-seed means, 95% CIs and negative-seed counts for all 10 pairs (`interaction_seed_ci_ml_1m.json`). Every pair keeps its sign 10/10. Seed-42 values were slightly off the mean (`cf|seq` -0.0561 vs -0.0542), so the table and all prose citing them were updated | §10.2 |
| 45 | NDCG@10 was the only ranking metric, so the attributions could have been an artefact of the cutoff/discount | All 32 coalitions re-scored with Recall@10 and MRR@10 (`metric_robustness_ml_1m.json`). Ordering identical, Kendall tau = 1.00 against NDCG in both cases. Magnitudes are not comparable, since the Recall/MRR games are not baseline-centred, so only the ordering is claimed | §2.6 |
| 46 | A 10-seed re-run on the author's machine at `--budget-gb 12.6` overwrote `final_seed_ci.json` in place. The budget DERIVES the user cap, so the run silently measured a different Gowalla: 4,652 of 8,865 users and 59,597 of 82,134 items, which also moved the frozen N_max=11,623 from 14.2% to 19.5% of the catalogue. Gowalla attributions shifted by up to 36% (phi_ct 0.00961 -> 0.01310). Nothing in the artefact recorded the corpus shape, so the numbers looked like an ordinary re-run | Reported artefact restored from git. The resized run is kept as `final_seed_ci_resized_12.6gb.json` and analysed in `gowalla_subsample_sensitivity.json`, since it is a genuine subsample-sensitivity result: ordering, all signs and the top source are preserved (tau = 1.00) while Gowalla magnitudes are not, and ml_1m / amazon_video_games, whose caps are not budget-bound, reproduce to 4.1% and 0.2% across runs. `memory.PAPER_CORPUS_SHAPE` + `check_paper_shape()` added; `run_final_revision.py` now refuses to write the reported artefact from a resized corpus unless `--allow-resize` is passed, in which case output goes to `*_resized.json`. Two tests pin the guard | §3.2 |
| 47 | Three different `v(G)` values appeared for what is nominally the same MovieLens seed-42 game: 0.05190 (source-order comparison), 0.05136 (main tables), 0.05190 (semivalues). A reviewer could not tell which defined the final result | Not a stale artefact: 0.05190 - 0.05136 = 5.4e-4, exactly the cross-platform residual of entry 36. The paired comparisons ran on x86-64, the reported tables on the M4. Both paired sets are now labelled as within-platform contrasts, and `artefacts/PROVENANCE.md` maps every table and figure to artefact, platform, candidate rule and seeds. The residual (5.4e-4) is an order of magnitude larger than the effect measured (2.8e-5), which is why that comparison had to be run twice on one machine | §3.2 |
| 48 | `mask_seen` masks only `ds.train`, and every scorer fits on `ds.train`, while the split is leave-last-TWO-out. The validation interaction is therefore neither added to the history nor masked before test scoring: the test ranking is produced from a state two events before the target, and the already-consumed validation item stays recommendable | Audited and documented rather than silently changed. Measured on the synthetic corpus: the validation item is unmasked for 100% of users and outscores the test item for 52%. Direction is provable and one-sided: an already-consumed but rankable item can only occupy a top-K slot and push the test item DOWN, so every reported v(S) is a LOWER bound and no optimistic leakage is possible. Named a two-step-ahead frozen-state protocol in §5 and listed in Limitations. Refreshing state between folds would make fitting and evaluation features come from different scorers, confounding v(S u {g}) - v(S) with a state change | §2.5 |
| 49 | The coalition head is fitted on the validation indicator, so a user whose validation positive is not retrieved into C_u contributes an all-zero target. Never measured or reported | `validation_recall()` added and wired into `e0a_candidate_diagnostics`, reporting recall, users scored, and users fitting on negatives only. Such users are RETAINED: dropping them would fit the head on a subpopulation selected for retrievability, a worse bias. Because the Gram accumulation is |C_u|-normalised they contribute to A but not to c, shrinking weights slightly rather than distorting direction | §2.4 |
| 50 | Figure 2 drew ten-seed mean bars under seed-42 `v(G)` panel labels, so the bars visibly failed to sum to the stated grand value (on Gowalla 0.0209 against 0.0169, a 24% gap) and the figure appeared to violate efficiency | Panel label now computed at the same aggregation level as the bars. Two other stale artefacts fixed alongside: Figure 7's internal title said "F6" (asset numbering is generation order, not paper order, so the prefix was removed entirely), and the segment figure's 6,035 users are now explained as the evaluable set, three users having empty candidate sets | §13 |
| 51 | Seed-level intervals used the normal quantile 1.96 with n=10, understating width by 15% (t_9 = 2.262); retirement tau was compared through two unpaired intervals although both correlations score the SAME observed loss on the SAME seed | All seed intervals recomputed with t_9. No conclusion changed: no interval spans zero on any corpus. Paired Delta tau added; recoverable exactly on ml_1m (+0.76 [+0.70,+0.82]) and gowalla (+0.20, zero variance) where Shapley's tau is seed-constant, not on amazon where per-seed values were not stored. Runner now records per-seed tau plus a percentile bootstrap and Wilcoxon on the paired differences | §13 |
| 52 | `\NDCG` expands to `NDCG@10`, so `\NDCG_K` typeset as "NDCG@10K" and `\NDCG_{10}` as "NDCG@1010" | `\NDCGat{}` added for the cutoff-parametrised form; both call sites fixed. Regression test asserts neither bare form returns | §13 |
| 53 | Claimed the frozen two-step-ahead protocol made every reported v(S) a LOWER BOUND on a refreshed one-step-ahead evaluation, so "no optimistic leakage is possible". False. The bound holds only while source scores and C_u are held fixed; a refreshed state also changes seq/rec/pop scores, can change C_u through retrieval, and changes b_u with it, none monotonically | Claim withdrawn and restated as the narrow within-fixed-state version. `scripts/run_protocol_sensitivity.py` added to measure it: fits the head in the validation state (history = train) and scores coalitions in the test state (history = train + val). On a synthetic pilot the refreshed protocol scores HIGHER (v(G) 0.147 -> 0.165) and flips two signs, i.e. the withdrawn claim is contradicted by a direct measurement, not only in principle. First implementation refit everything on train+val, which made `mask_seen` erase the fitting target and fit the head on an all-zero right-hand side; the two-state split fixes it | §2.5 |
| 54 | Claimed users whose validation positive is outside C_u "shrink the fitted weights slightly rather than distorting their direction". False: their PSD block enters A while c is unchanged, so (A+lam I)^-1 c rescales eigendirections unevenly and rotates the solution. A two-source example moves w by 12.8 degrees while shrinking its norm | Corrected in text; retention kept but now framed as a declared choice whose sensitivity is measured, with the drop-misses refit in the same script (synthetic pilot: tau = 1.00, max abs delta phi = 5.0e-4). Regression test pins the rotation | §2.4 |
| 55 | Four of five source scorers were named and hyperparameterised but never defined mathematically, so the paper could not be reimplemented without reading the code | New Section 4 subsection gives the scoring function of every source: ALS confidence-weighted alternating solve, TF-IDF profile cosine, log1p of half-life-decayed global counts, cluster-recency decay, and PPMI-SVD with a 0.8^k recency-weighted user vector | §4 |
| 56 | Table 9 listed "Shapley, or a declared semivalue" as the method for DIVIDING credit, citing efficiency, while the paper states elsewhere that Banzhaf and the binomial semivalues are not efficient | Split into two rows: efficient division is Shapley only; semivalues get their own row, explicitly "rank rather than divide" | §10.2 |
| 57 | Candidate sets described as "seed-independent" although ALS and every truncated SVD take the experiment seed, so C_u can move across seeds through the scorers | Reworded to deterministic CONDITIONAL on the fitted source models | §2.3 |
| 58 | Table 8 used 1.96*SE while the rest of the paper had moved to t_9, and the text claimed bootstrap and Wilcoxon results that appeared nowhere | Table 8 recomputed with t_9, paired Delta tau column added with its bootstrap interval, and the Wilcoxon p-values now stated (0.002, 0.004, and 1.0 on Gowalla where every difference is identical so the test is uninformative) | §13 |
| 59 | Figure 5's shared legend showed only the last panel's segment sizes while appearing to describe all three corpora, whose segment counts differ | One legend per panel; panels enlarged rather than shrinking type, since SN_FONT_MIN is already at the 8pt Springer artwork floor | §13 |
| 60 | LOO_e2e was defined as v_e2e(G) - v_e2e(G\{g}) and called the observed retirement loss "by construction". False. End to end each coalition retrieves its own C_u(S), so \|C_u\| and hence the expected-random baseline b(S) move when a source is retired, and that difference carries a spurious b(G\{g}) - b(G) term. `coalition_retrieval_game` was differencing `game.v()`, so the reported losses were contaminated | Eq. (loo) rewritten on RAW utilities U_rank and U_e2e; the paper now explains that the baseline cancels in the fixed-candidate game (common b) but not end to end. `SignalShapGame.utility()` added and the retirement simulation differences it; artefacts keep the legacy centred column plus `baseline_shift_after_removal` so the correction is auditable. Measured on the pilot: contamination <= 1.7e-4, tau(raw, centred) = 1.00, same cheapest source, so no conclusion changes | §3, §13 |
| 61 | Wilcoxon on Gowalla reported p = 1.0 for ten identical +0.20 paired differences, from a guard in `run_final_revision.py` mapping constant vectors to 1.0. Backwards: identical positive differences give the signed-rank statistic its minimum, and scipy returns the exact two-sided 2/2^10 = 0.00195, the strongest value available at n = 10 | Guard corrected to trigger only on an all-zero difference vector. All three p-values recomputed: 0.0020, 0.0039, 0.0020. Regression test pins it | §13 |
| 62 | Kendall tau seed intervals used t_9, producing [0.90, 1.02] for a statistic bounded by 1 | Replaced with a 10,000-resample percentile bootstrap in both the artefacts and the runner; a bootstrap cannot leave the convex hull of the observed values. Test asserts every reported tau interval lies in [-1, 1] | §13 |
| 63 | Split described as a temporal leave-last-out, but it is chronological only WITHIN each user: sources are fitted on the pooled training fold and `pop` decays from the GLOBAL latest training timestamp, so other users' training events can postdate a given user's held-out event | `scripts/audit_global_time.py` added and the exposure measured (pilot: ~50% of pooled training events postdate the median test event). Described in the protocol and Threats as a per-user chronological offline evaluation, not a globally causal deployment simulation. Reported, not repaired: a globally blocked replication needs one cutoff and discards much of each corpus | §5 |
| 64 | Said every source score is z-normalised "so only the induced ordering matters". False for linear multi-source fusion: standardisation removes location and positive scale, but relative spacing still drives the fused ranking, and a nonlinear monotone transform of one source changes the result | Restricted to positive affine invariance, consistent with the invariance property stated in §6 | §4 |
| 65 | Popularity described as "constant across a user's candidate row" although its own equation varies with the item. If it were item-constant, z-normalisation would zero it and it could not carry standalone value | Corrected to user-invariant but item-varying | §4 |
| 66 | Figure 3 plotted seed-42 LOO and Shapley beneath prose and a table that had moved to ten-seed means; Table 7's caption claimed its seed-42 columns were "identical" to the ten-seed Table 6 | Figure 3 regenerated from the ten-seed artefact and its internal title stripped of the asset number and em dash; Table 7 caption now says same game definition, seed-42 realisation | §13 |
| 33 | Appendix A ran a six-method Friedman across all three corpora on absolute NDCG, while §7 excludes two of them from absolute comparison for failing the recall gate | SUPERSEDED by entry 42: the test has been deleted. The earlier resolution retained it because its conclusion was negative, which makes admissibility outcome-dependent and is not defensible | §2.2 |
| 34 | The `if not coalition: return 0` early return in `v_per_user` was lost while rewriting a docstring. The empty coalition then fell through to the scoring path with an all-zero weight vector: every candidate tied, `lexsort` broke the tie by ascending item index, and the "empty" coalition was scored on an arbitrary ranking. `v(empty)` became −0.00147 on ml_1m instead of 0, propagating into every reported value and failing Property 1 on all three corpora (7.4e-04, 2.8e-03, 8.1e-05). Cost a full re-run | Early return restored with a comment marking it load-bearing. `v_empty` now written into every artefact, and `check_paper_numbers.py` gained HARD INVARIANT checks that fail the build on `efficiency.passes == False` or `\|v(empty)\| > 1e-12` — properties of the artefact itself, not paper/artefact agreement, so a broken run can no longer pass while the prose matches | §2.5 |
| 35 | `scripts/rerun_all.sh` shipped with `timeout 7200 python/run_study.py`: two faults in one line from an unverified `sed` — `timeout` does not exist on macOS, and the path had been mangled to `python/run_study.py`. `bash -n` passed because both are runtime failures, so the ml_1m stage died in 0 seconds on the user's machine | Line fixed; `tests/test_runner_script.py` added, asserting every stage's interpreter is portable, every referenced script exists, labels are unique, all three corpora are covered, `set -e` is absent and `SIGNALSHAP_STRICT_DATA=1` is set. Verified by reintroducing the exact bug: two tests fail | §20 |
| 36 | Residual cross-platform variation after removing the sampled baseline: arm64 and x86-64 runs agree on `\|C_u\|` exactly (mean 599.9985, sd 0.067, min 597, max 600) but differ in candidate CONTENTS for 2 of 6,035 users (0.03%), because ALS and truncated-SVD accumulate in different orders under different BLAS. Moves `v(G)` by 5e-4 and raw monotonicity between 16 and 23 | Quantified and disclosed in §3.2 rather than hidden. Material monotonicity count and every reported sign are unaffected — this is why the paper reports material alongside raw. `study_manifest.json` records platform and library versions. Bounds what "exact" means: the aggregation is exact, the fitted game is floating point | §2.5 |

---

## 20. Standing Editorial Rules

- **Never** cite DyHuCoG as a reproducibility source — only as motivation. The 63-gap audit is *why* this work is independent of it.
- **Never** cite, quote, or import structure from the parallel AI-generated Deep Analysis brainstorming document. All numeric projections in it (NDCG gains, GitHub stars, citations) are AI-generated and must not appear in the manuscript, cover letter, or grant materials.
- **Never** claim causal discovery. All attribution is inside the fixed candidate set and the declared game.
- **Every** quantitative claim traces to a JSON in `artefacts/` and to a table cell.
- **No sampling-based Shapley in the main results** — only in E5 as a matched-budget check that exact Shapley beats sampled Shapley at equal cost. State this as a *correctness* claim.
- **The abstract must contain "exact Shapley over 32 coalitions"** — because it is the most accurate one-line description of the method.
- **"Exact" always means "exact given the fitted $v$."** Never "no error"; write "no sampling error."
- **"Laptop CPU, seconds" applies to the Shapley computation only.** Qualify every mention.
- **SignalShap-Fuse cost is "negligible ($O(1)$ segment-lookup)", not "zero."** The $O(1)$ justification is a table lookup on precomputed user-segment IDs.
- **Properties 1–3 are restated Shapley axioms, not novel theorems.** Lemma 1 is new but modest.
- **Monotonicity is audited, never assumed.** Property 2 and Lemma 1(ii) may only be invoked where E0-b passes; where it fails, report negative $\varphi_g$ as substantive.
- **The density ordering is a CI invariant, and C3 lives or dies by it.** No corpus filter without re-running the test. The one forbidden outcome is shipping an inverted ordering under the old wording.
- **Density is computed, never quoted** — and never taken from a spec table. Placeholder estimates in this document are decision-support for *whether a hazard exists*, never inputs to a filter decision. Anything feeding a decision carries `source: "measured"`.
- **$\lambda$ is frozen, never tuned per coalition.**
- **T5 is full-catalog for every method.** Never restrict a baseline to $C_u$ to make a comparison "fair."
- **Player overlap is pre-registered, not discovered.**
- **Candidate recall is a submission gate** with the §2.2 ladder as its only remediation path. Restricting the evaluated population is forbidden.
- **Internal planning vocabulary never reaches the manuscript.** "Reviewer attack surface," "acceptance risk," "reviewer-hard-to-attack," "minimal attack surface," "review-proof," and the four-blueprint comparison table are planning artefacts — barred from the paper, the cover letter, and the response-to-reviewers.
- **Ethics, LLM-usage, funding, and competing-interests declarations must all be present.** Data Availability names each dataset's license.

---

**End of specification.**
