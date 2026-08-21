#!/usr/bin/env python3
"""P1: measure what exact enumeration buys over sampled Shapley estimation.

Motivation
----------
The manuscript calls its aggregation "exact" and treats that as a virtue. A
reviewer is entitled to ask how large the error would have been had we sampled
instead. If sampling at a realistic budget already lands below the seed-to-seed
spread, then exactness is a convenience rather than a load-bearing property,
and the paper should say so. Either outcome is reportable; the absent
measurement is not.

Honest scope limitation
-----------------------
The only complete 32-coalition characteristic function persisted in artefacts/
is `e11_estimands_*.json -> end_to_end.coalition_recall`, which is the
END-TO-END RECALL game, not the ranking-stage NDCG@10 game whose Shapley values
the paper reports. We therefore measure sampling error on that game and report
the error RELATIVE to its own v(G), which is the scale-free quantity that
transfers. We do not claim these are the NDCG game's absolute errors, and the
output records this.

Estimators
----------
Two, because they fail differently:

* Permutation sampling. Draw M permutations, average each player's marginal
  contribution along each. Unbiased; error decays as M^{-1/2}.
* KernelSHAP. Draw M coalitions from the Shapley kernel, solve the
  efficiency-constrained weighted least squares. Biased at small M but often
  lower variance.

Both are given the SAME per-coalition oracle, so this isolates aggregation
error and nothing else.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
ART = REPO / "artefacts"
PLAYERS = ["cf", "ct", "pop", "rec", "seq"]


def load_game(dataset: str) -> dict[frozenset[str], float]:
    path = ART / f"e11_estimands_{dataset}.json"
    raw = json.loads(path.read_text())["end_to_end"]["coalition_recall"]
    game = {}
    for key, val in raw.items():
        members = frozenset() if key == "empty" else frozenset(key.split(","))
        game[members] = float(val)
    if len(game) != 32:
        raise SystemExit(f"expected 32 coalitions, got {len(game)}")
    return game


def exact_shapley(v: dict[frozenset[str], float]) -> dict[str, float]:
    n = len(PLAYERS)
    phi = {}
    for g in PLAYERS:
        others = [p for p in PLAYERS if p != g]
        total = 0.0
        for r in range(n):
            for combo in itertools.combinations(others, r):
                S = frozenset(combo)
                w = math.factorial(r) * math.factorial(n - r - 1) / math.factorial(n)
                total += w * (v[S | {g}] - v[S])
        phi[g] = total
    return phi


def permutation_shapley(v, M: int, rng) -> dict[str, float]:
    acc = {g: 0.0 for g in PLAYERS}
    for _ in range(M):
        order = list(rng.permutation(PLAYERS))
        S = frozenset()
        base = v[S]
        for g in order:
            S2 = S | {g}
            acc[g] += v[S2] - base
            base = v[S2]
            S = S2
    return {g: acc[g] / M for g in PLAYERS}


def kernel_shap(v, M: int, rng) -> dict[str, float]:
    """Shapley-kernel weighted least squares with the efficiency constraint.

    Sizes 0 and n carry infinite kernel weight and are the constraint, not
    sampled rows, so we draw only from sizes 1..n-1.
    """
    n = len(PLAYERS)
    sizes = np.arange(1, n)
    # Shapley kernel, up to a constant, aggregated over coalitions of a size.
    p = np.array([(n - 1) / (k * (n - k)) for k in sizes], dtype=float)
    p = p / p.sum()

    rows, ys, ws = [], [], []
    for _ in range(M):
        k = int(rng.choice(sizes, p=p))
        members = frozenset(rng.choice(PLAYERS, size=k, replace=False))
        z = np.array([1.0 if g in members else 0.0 for g in PLAYERS])
        rows.append(z)
        ys.append(v[members])
        ws.append(1.0)

    Z = np.array(rows)
    y = np.array(ys)
    W = np.diag(ws)

    v0, vN = v[frozenset()], v[frozenset(PLAYERS)]
    # Eliminate phi_last via efficiency: sum(phi) = vN - v0.
    y_adj = y - v0 - Z[:, -1] * (vN - v0)
    Z_adj = Z[:, :-1] - Z[:, -1:][:, [0] * (n - 1)]

    A = Z_adj.T @ W @ Z_adj
    b = Z_adj.T @ W @ y_adj
    phi_head = np.linalg.solve(A + 1e-12 * np.eye(n - 1), b)
    phi_last = (vN - v0) - phi_head.sum()
    vals = list(phi_head) + [phi_last]
    return dict(zip(PLAYERS, vals))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="ml_1m")
    ap.add_argument("--repeats", type=int, default=20)
    ap.add_argument("--budgets", type=int, nargs="+",
                    default=[50, 100, 500, 2000])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path,
                    default=ART / "sampling_error.json")
    args = ap.parse_args()

    v = load_game(args.dataset)
    exact = exact_shapley(v)
    v_grand = v[frozenset(PLAYERS)] - v[frozenset()]

    resid = abs(sum(exact.values()) - v_grand)
    if resid > 1e-12:
        raise SystemExit(f"enumeration failed efficiency: {resid}")

    rng = np.random.default_rng(args.seed)
    out = {
        "dataset": args.dataset,
        "game": "end_to_end.coalition_recall",
        "caveat": (
            "This is the end-to-end recall game, the only complete "
            "32-coalition characteristic function persisted in artefacts/. "
            "It is NOT the ranking-stage NDCG@10 game whose Shapley values "
            "the paper reports. Absolute errors do not transfer; errors "
            "relative to v(G) do."),
        "v_grand": v_grand,
        "exact_shapley": exact,
        "efficiency_residual": resid,
        "repeats": args.repeats,
        "budgets": {},
    }

    for M in args.budgets:
        rec = {}
        for name, fn in (("permutation", permutation_shapley),
                         ("kernelshap", kernel_shap)):
            errs = []
            for _ in range(args.repeats):
                est = fn(v, M, rng)
                errs.append(max(abs(est[g] - exact[g]) for g in PLAYERS))
            errs = np.array(errs)
            rec[name] = {
                "max_abs_error_mean": float(errs.mean()),
                "max_abs_error_p95": float(np.percentile(errs, 95)),
                "max_abs_error_worst": float(errs.max()),
                "relative_to_v_grand_mean": float(errs.mean() / abs(v_grand)),
                "relative_to_v_grand_p95": float(
                    np.percentile(errs, 95) / abs(v_grand)),
            }
        out["budgets"][str(M)] = rec

    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {args.out.relative_to(REPO)}")
    print(f"  v(G) = {v_grand:.6f}   efficiency residual {resid:.2e}")
    for M, rec in out["budgets"].items():
        p = rec["permutation"]
        k = rec["kernelshap"]
        print(f"  M={M:>5}  perm rel p95 {p['relative_to_v_grand_p95']:.4%}"
              f"   kernel rel p95 {k['relative_to_v_grand_p95']:.4%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
