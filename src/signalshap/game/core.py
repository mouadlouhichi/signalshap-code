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
    ) -> None:
        self.sources = tuple(g for g in sources if g in scores)
        self.k = k_ndcg
        self.lam = ridge_lambda
        self.candidates = candidates
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
        """
        rng = np.random.default_rng(seed)
        out = {}
        for u in self.eval_users:
            c = self.candidates[u]
            perm = c[rng.permutation(len(c))]
            out[u] = ndcg_at_k(perm, self.test_items[u], self.k)
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
        """Per-user v, needed for Property 3 and for paired statistics."""
        if not coalition:
            return {u: 0.0 for u in self.eval_users}
        w = self._fit_weights(coalition)
        out = {}
        for u in self.eval_users:
            s = self.feat[u] @ w
            order = np.lexsort((self.candidates[u], -s))
            ranked = self.candidates[u][order]
            out[u] = ndcg_at_k(ranked, self.test_items[u], self.k) - self._v0[u]
        return out

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
    return {
        "pairs_checked": n * 2 ** (n - 1),
        "violations": len(violations),
        "max_magnitude": float(max((abs(x["delta"]) for x in violations), default=0.0)),
        "sources_involved": sorted({x["g"] for x in violations}),
        "detail": violations[:20],
        "property2_applicable": len(violations) == 0,
    }
