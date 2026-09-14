"""The cooperative game: v(S), exact Shapley, and the monotonicity audit.

Spec §2.4 (frozen lambda), §2.5 (v_0), §2.6 (exact Shapley), §2.7 (what
"exact" means), §3.3 (E0-b audit).

KEY CLAIM DISCIPLINE (spec §2.7): "exact" means exact GIVEN THE FITTED v.
The 32-coalition aggregation has no sampling error, unlike Monte-Carlo
Shapley. But v(S) is itself estimated -- ridge heads fitted on a validation
fold -- so phi_g carries estimation error and is reported with seed-based
CIs in the main text. Never write "no error"; write "no sampling error".
"""

from __future__ import annotations

from itertools import combinations
from math import factorial

import hashlib

import numpy as np

from ..config import SOURCES


# --------------------------------------------------------------------------- #
# Coalitions
# --------------------------------------------------------------------------- #


def all_coalitions(sources: tuple[str, ...] = SOURCES) -> list[frozenset]:
    """All 2^|G| = 32 coalitions, ordered by size then lexicographically."""
    return [
        frozenset(c)
        for k in range(len(sources) + 1)
        for c in combinations(sources, k)
    ]


def shapley_weight(s: int, n: int) -> float:
    """|S|!(n-|S|-1)!/n!  --  for n=5: (1/5, 1/20, 1/30, 1/20, 1/5)."""
    return factorial(s) * factorial(n - s - 1) / factorial(n)


# --------------------------------------------------------------------------- #
# Per-user normalisation and NDCG
# --------------------------------------------------------------------------- #


def z_normalise(row: np.ndarray) -> np.ndarray:
    """Per-user, per-source z-normalisation.

    Remark 1 (spec §3.1): this makes phi_g invariant under any user- and
    source-specific AFFINE map. Invariance does NOT extend to nonlinear
    monotone maps -- E5-iii tests that empirically.
    """
    finite = np.isfinite(row)
    if not finite.any():
        return np.zeros_like(row)
    out = np.zeros_like(row)
    vals = row[finite]
    sd = vals.std()
    out[finite] = (vals - vals.mean()) / sd if sd > 1e-12 else 0.0
    return out


def ndcg_at_k(ranked: np.ndarray, target: int, k: int = 10) -> float:
    """Binary-relevance NDCG@k with a single relevant item (leave-last-out)."""
    top = ranked[:k]
    hit = np.flatnonzero(top == target)
    return float(1.0 / np.log2(hit[0] + 2)) if hit.size else 0.0


# --------------------------------------------------------------------------- #
# Game construction
# --------------------------------------------------------------------------- #


def expected_random_ndcg(n_candidates: int, k: int = 10) -> float:
    """E[NDCG@k] of a uniformly random ranking with ONE relevant item.

    The held-out item is equally likely to occupy any of the |C_u| positions,
    and IDCG = 1, so

        E[NDCG@k] = (1/|C_u|) * sum_{r=1}^{min(k,|C_u|)} 1/log2(r+1).

    This replaces the sampled permutation as the empty-coalition anchor. The
    sampled version was a single Monte-Carlo draw, and because the baseline
    enters only the empty-to-singleton marginal it shifted every phi_g by
    -Delta/n -- enough to move a near-zero source across zero. A reviewer
    correctly objected that a sign-based finding should not depend on which
    permutation happened to be drawn. The expectation removes that degree of
    freedom entirely: it is deterministic, closed-form, identical on every
    machine, and needs no seed.
    """
    import math

    if n_candidates <= 0:
        return 0.0
    return sum(1.0 / math.log2(r + 1)
               for r in range(1, min(k, n_candidates) + 1)) / n_candidates


def _hash_permute(items: np.ndarray, seed: int, user: int) -> np.ndarray:
    """Deterministic pseudo-random permutation of `items`, keyed by (seed, user).

    Sorts by a BLAKE2b digest of (seed, user, item). blake2b is used rather
    than Python's builtin hash(), which is randomised per process by PYTHONHASHSEED
    and would reintroduce exactly the nondeterminism this replaces. The digest
    is truncated to 8 bytes and read as a uint64 sort key; collisions are broken
    by item id so the result is a total order.
    """
    keys = np.empty(len(items), dtype=np.uint64)
    prefix = seed.to_bytes(8, "little", signed=False)
    ubytes = int(user).to_bytes(8, "little", signed=False)
    for i, it in enumerate(items):
        d = hashlib.blake2b(
            prefix + ubytes + int(it).to_bytes(8, "little", signed=False),
            digest_size=8,
        ).digest()
        keys[i] = int.from_bytes(d, "little")
    # lexsort is stable and breaks digest ties by item id, giving a total order.
    order = np.lexsort((items, keys))
    return items[order]


class SignalShapGame:
    """Cooperative game over the five signal sources.

    Builds per-user z-normalised feature matrices over the fixed candidate set,
    then evaluates v(S) for every coalition using a ridge head fitted on the
    validation fold with a FROZEN lambda (spec §2.4).
    """

    def __init__(
        self,
        scores: dict[str, np.ndarray],
        candidates: list[np.ndarray],
        valid_items: dict[int, int],
        test_items: dict[int, int],
        ridge_lambda: float = 1.0,
        k_ndcg: int = 10,
        v0_seed: int = 42,
        sources: tuple[str, ...] = SOURCES,
        baseline: str = "expected",
    ) -> None:
        self.sources = tuple(g for g in sources if g in scores)
        self.k = k_ndcg
        self.lam = ridge_lambda
        self.candidates = candidates
        #: "expected" (default, deterministic) or "sampled" (legacy, seeded).
        self.baseline = baseline
        self.valid_items = valid_items
        self.test_items = test_items

        # Users evaluated on test must have a non-empty candidate set.
        self.eval_users = [
            u for u in sorted(test_items) if u < len(candidates) and len(candidates[u])
        ]
        self.fit_users = [
            u for u in sorted(valid_items) if u < len(candidates) and len(candidates[u])
        ]

        # Z-normalised features per user: (|C_u| x |sources|)
        self.feat: dict[int, np.ndarray] = {}
        for u in set(self.eval_users) | set(self.fit_users):
            c = candidates[u]
            # float32 halves the largest resident structure; the ridge solve
            # promotes to float64 via the Gram accumulation, so precision of
            # the fitted weights is unaffected.
            self.feat[u] = np.column_stack(
                [z_normalise(scores[g][u][c]) for g in self.sources]
            ).astype(np.float32)

        self._v0 = self._frozen_baseline(v0_seed)
        self._cache: dict[frozenset, float] = {}
        self._gram_cache: tuple[np.ndarray, np.ndarray] | None = None

    # -- v_0 ---------------------------------------------------------------- #

    def _frozen_baseline(self, seed: int) -> dict[int, float]:
        """ONE frozen permutation per user, reused everywhere (spec §2.5).

        Not a fresh draw whose expectation is taken. Under this reading
        v(empty) = 0 EXACTLY and PER USER, which Property 3 requires -- it
        needs per-user v(empty)=0, not merely on the mean.

        The permutation is derived by HASHING (seed, user, item) rather than by
        drawing from a NumPy Generator, for two reasons, both of which caused
        real divergence:

        1. NumPy guarantees Generator reproducibility only within a version
           series. Two machines running identical code, identical config and
           byte-identical candidate sets produced v0 = 0.005033 and 0.006731,
           which propagated into every coalition value (v(G) 0.05253 vs
           0.05030), shifted phi_ct across zero, and moved the monotonicity
           count from 16/80 to 23/80. Nothing in the method depends on the
           permutation coming from a particular RNG stream -- it only has to be
           an arbitrary order fixed once -- so relying on one was a gratuitous
           reproducibility hazard.
        2. The previous implementation advanced a single Generator inside the
           user loop, so each user's permutation depended on how many users
           preceded it. Any change to eval_users membership -- a different
           k-core, a user with an empty candidate set -- silently reshuffled the
           baseline for every subsequent user.

        Hashing fixes both: each user's order depends only on (seed, user), and
        each item's rank only on (seed, user, item). The result is stable
        across NumPy versions, platforms, Python builds, and user orderings.
        """
        out = {}
        for u in self.eval_users:
            c = self.candidates[u]
            if self.baseline == "expected":
                # Deterministic: no permutation is drawn at all.
                out[u] = (expected_random_ndcg(len(c), self.k)
                          if self.test_items[u] in set(c.tolist()) else 0.0)
            else:
                out[u] = ndcg_at_k(_hash_permute(c, seed, u),
                                   self.test_items[u], self.k)
        return out

    @property
    def v0(self) -> float:
        return float(np.mean([self._v0[u] for u in self.eval_users])) if self.eval_users else 0.0

    # -- ridge head --------------------------------------------------------- #

    def _gram(self) -> tuple[np.ndarray, np.ndarray]:
        """Accumulate X^T X and X^T y ONCE over all sources, cached.

        Ridge needs only these sufficient statistics, and the versions for a
        sub-coalition S are simply the corresponding SUBMATRICES. Rebuilding
        and stacking the full design matrix per coalition -- as this did
        originally -- costs O(2^|G|) passes over a matrix that can run to
        several GB, which dominates runtime on large corpora and thrashes
        memory. Accumulating once and slicing is algebraically identical and
        removes a 2^|G| factor.
        """
        if self._gram_cache is None:
            n = len(self.sources)
            XtX = np.zeros((n, n))
            Xty = np.zeros(n)
            for u in self.fit_users:
                F = self.feat[u].astype(np.float64, copy=False)
                y = (self.candidates[u] == self.valid_items[u]).astype(np.float64)
                # Per-user normalisation by |C_u|. Candidate sets differ in
                # size across users; without this factor users with larger
                # pools would contribute proportionally more rows and dominate
                # the fitted head.
                inv = 1.0 / max(len(self.candidates[u]), 1)
                XtX += inv * (F.T @ F)
                Xty += inv * (F.T @ y)
            self._gram_cache = (XtX, Xty)
        return self._gram_cache

    def _fit_weights(self, coalition: frozenset) -> np.ndarray:
        """Ridge head fitted on the validation fold, conditioned on S.

        lambda is FROZEN (spec §2.4). Tuning it per coalition would be
        optimistic bias growing with |S| -- larger coalitions have more weights
        and more chance to overfit the single held-out interaction -- which
        inflates v(G) relative to small coalitions. That is the same pathology
        as the grand-coalition candidate bias, arriving by another route.
        """
        idx = [i for i, g in enumerate(self.sources) if g in coalition]
        if not idx:
            return np.zeros(len(self.sources))
        if not self.fit_users:
            w = np.zeros(len(self.sources))
            w[idx] = 1.0
            return w

        XtX, Xty = self._gram()
        ii = np.ix_(idx, idx)
        A = XtX[ii] + self.lam * np.eye(len(idx))
        try:
            sol = np.linalg.solve(A, Xty[idx])
        except np.linalg.LinAlgError:
            # Singular Gram: happens when lam = 0 and two sources are exactly
            # collinear, which is precisely the duplicate-injection diagnostic.
            # lstsq returns the MINIMUM-NORM solution, which splits a shared
            # coefficient evenly between duplicated columns and is therefore
            # replication-invariant in its predictions -- the property the
            # diagnostic needs.
            sol = np.linalg.lstsq(A, Xty[idx], rcond=None)[0]
        w = np.zeros(len(self.sources))
        w[idx] = sol
        return w

    # -- characteristic function ------------------------------------------- #

    def v_per_user(self, coalition: frozenset) -> dict[int, float]:
        """Per-user v, needed for Property 3 and for paired statistics.

        NOTE ON BASELINE SENSITIVITY. This implements Eq. (2) faithfully:
        v_u(S) = NDCG(pi_u(S); y_u) - b_u for non-empty S, and v_u(empty) = 0
        because ranking by the baseline permutation gives exactly b_u.

        The manuscript previously claimed phi is invariant to b_u "since b_u
        cancels in every marginal difference". That is FALSE, and two reviewers
        derived it independently from the tables. b_u cancels in
        v(S u {g}) - v(S) only when S is non-empty. For S = empty the marginal
        is v({g}) - 0 = mean_u[NDCG_u({g}) - b_u], which retains the baseline.
        Since the empty set carries Shapley weight w(0) = 1/n, changing the
        baseline shifts EVERY phi_g by exactly -delta/n.

        Verified numerically: re-running the identical game with v0_seed 999
        instead of 42 changed v0 by -0.000796 and shifted all five MovieLens
        phi by +0.00015926 = 0.000796/5, agreeing to eight decimals, and moved
        phi_ct across zero.

        The baseline is therefore a declared modelling choice that sets the
        game's reference point, not a normalisation that washes out. Efficiency
        is unaffected (sum phi = v(G) - v(empty)). We disclose the sensitivity
        and report it rather than repeating the invariance claim.
        """
        if not coalition:
            # v_u(empty) = 0 EXACTLY, per Eq. (2) and Property 3.
            #
            # This early return is load-bearing and was briefly lost in a
            # refactor, which cost a full re-run. Without it the empty
            # coalition falls through to the scoring path below with an
            # all-zero weight vector: every candidate then ties, lexsort breaks
            # the tie by ascending item index, and the "empty" coalition is
            # scored on an arbitrary-but-not-random ranking. On MovieLens that
            # gave v(empty) = -0.00147 instead of 0, which propagates into
            # every reported value and makes check_efficiency (which compares
            # sum phi against v(G), not v(G) - v(empty)) report a 7.4e-04
            # violation of Property 1.
            return {u: 0.0 for u in self.eval_users}

        w = self._fit_weights(coalition)
        out = {}
        for u in self.eval_users:
            s = self.feat[u] @ w
            order = np.lexsort((self.candidates[u], -s))
            ranked = self.candidates[u][order]
            out[u] = ndcg_at_k(ranked, self.test_items[u], self.k) - self._v0[u]
        return out

    def utility(self, coalition: frozenset) -> float:
        """RAW mean NDCG@k, with no baseline subtracted.

        The end-to-end retirement experiment must difference THIS, not v().
        Each coalition retrieves its own candidate set there, so |C_u| and
        therefore b_u differ between the full system and the survivors; a
        reviewer showed that v(G) - v(G\{g}) then carries a spurious
        B(G\{g}) - B(G) term and is not the observed removal loss. In the main
        fixed-candidate game the baseline is common to every coalition and
        cancels in that difference, which is why v() is the right object there
        and the wrong one here.
        """
        coalition = frozenset(coalition)
        if not coalition:
            return 0.0
        w = self._fit_weights(coalition)
        tot = 0.0
        for u in self.eval_users:
            s_u = self.feat[u] @ w
            order = np.lexsort((self.candidates[u], -s_u))
            tot += ndcg_at_k(self.candidates[u][order], self.test_items[u], self.k)
        return tot / len(self.eval_users) if self.eval_users else 0.0

    def v(self, coalition: frozenset) -> float:
        """v(S) = mean per-user NDCG@10 - v_0, with v(empty) = 0 exactly."""
        coalition = frozenset(coalition)
        if coalition not in self._cache:
            pu = self.v_per_user(coalition)
            self._cache[coalition] = float(np.mean(list(pu.values()))) if pu else 0.0
        return self._cache[coalition]

    def v_all(self) -> dict[frozenset, float]:
        """Evaluate all 2^|G| coalitions."""
        return {S: self.v(S) for S in all_coalitions(self.sources)}


# --------------------------------------------------------------------------- #
# Exact Shapley (spec §2.6)
# --------------------------------------------------------------------------- #


def exact_shapley(v: dict[frozenset, float], sources: tuple[str, ...] = SOURCES) -> dict[str, float]:
    """Closed-form sum over all 2^n coalitions. No sampling error."""
    n = len(sources)
    phi = {}
    for g in sources:
        others = [s for s in sources if s != g]
        total = 0.0
        for k in range(len(others) + 1):
            for c in combinations(others, k):
                S = frozenset(c)
                total += shapley_weight(len(S), n) * (v[S | {g}] - v[S])
        phi[g] = total
    return phi


def per_user_shapley(game: SignalShapGame) -> dict[str, np.ndarray]:
    """Property 3: phi_g = mean_u phi_g(u), free by linearity (spec §3.1)."""
    coalitions = all_coalitions(game.sources)
    pu = {S: game.v_per_user(S) for S in coalitions}
    users = game.eval_users
    n = len(game.sources)
    out = {}
    for g in game.sources:
        others = [s for s in game.sources if s != g]
        acc = np.zeros(len(users))
        for k in range(len(others) + 1):
            for c in combinations(others, k):
                S = frozenset(c)
                w = shapley_weight(len(S), n)
                acc += w * np.array([pu[S | {g}][u] - pu[S][u] for u in users])
        out[g] = acc
    return out


# --------------------------------------------------------------------------- #
# Property 1 and the E0-b monotonicity audit (spec §3.3)
# --------------------------------------------------------------------------- #


def check_efficiency(phi: dict[str, float], v: dict[frozenset, float],
                     sources: tuple[str, ...] = SOURCES, tol: float = 1e-9) -> dict:
    """Property 1. Holds EXACTLY regardless of fit noise -- it is structural."""
    lhs, rhs = sum(phi.values()), v[frozenset(sources)]
    return {
        "sum_phi": float(lhs), "v_grand": float(rhs),
        "abs_error": float(abs(lhs - rhs)), "passes": bool(abs(lhs - rhs) < tol),
    }


def monotonicity_audit(v: dict[frozenset, float],
                       sources: tuple[str, ...] = SOURCES) -> dict:
    """E0-b: check all n*2^(n-1) = 80 pairs (S, g) for v(S u {g}) >= v(S).

    Monotonicity is an assumption to be DISCHARGED, never asserted. Property 2
    and Lemma 1(ii) are only applicable where this passes. Where it fails that
    is a FINDING to report -- the fitted hybrid game is genuinely non-monotone
    and negative phi_g must be read as real, not as numerical error.

    Note the coupling to spec §2.4: the coalition-conditional ridge refit is
    precisely the mechanism that can break monotonicity, since a head fitted on
    S u {g} may score worse than one fitted on S.
    """
    violations = []
    for S in all_coalitions(sources):
        for g in sources:
            if g in S:
                continue
            delta = v[S | {g}] - v[S]
            if delta < 0:
                violations.append(
                    {"S": sorted(S), "g": g, "delta": float(delta)}
                )
    n = len(sources)
    mags = sorted(abs(x["delta"]) for x in violations)
    # Stratify by magnitude. A bare count is NOT a stable statistic: most
    # violations sit far below the scale of v itself (NDCG ~ 0.05), so a
    # negligible numerical perturbation flips them across zero and changes the
    # headline number. Two machines running identical code reported 16/80 and
    # 23/80 for exactly this reason. The QUALITATIVE conclusion -- that the
    # fitted game is non-monotone, so Property 2 does not apply -- rests on the
    # violations that survive a meaningful threshold, and those are reported
    # separately so a reader can see which is which.
    strata = {f"gt_{t:g}": int(sum(1 for m in mags if m > t))
              for t in (0.0, 1e-4, 1e-3, 1e-2)}
    return {
        "pairs_checked": n * 2 ** (n - 1),
        "violations": len(violations),
        "violations_by_magnitude": strata,
        "violations_material": strata["gt_0.001"],
        "material_threshold": 1e-3,
        "max_magnitude": float(max(mags, default=0.0)),
        "median_magnitude": float(mags[len(mags) // 2]) if mags else 0.0,
        "sources_involved": sorted({x["g"] for x in violations}),
        # ALL violations, not a truncated 20. The magnitudes are the evidence
        # for the material count the paper quotes, and at 80 audited pairs the
        # full list is tiny. Truncation silently made that count unverifiable
        # from the artefact -- check_paper_numbers.py now refuses to verify a
        # material count when detail is shorter than the violation count.
        "detail": violations,
        "property2_applicable": len(violations) == 0,
        "stability_note": (
            "Report violations_material (|delta| > 1e-3) alongside the raw "
            "count. The raw count is sensitive to floating-point ordering; the "
            "material count is not, and it is what the Property 2 argument "
            "actually depends on."
        ),
    }
