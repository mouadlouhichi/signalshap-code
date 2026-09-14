#!/usr/bin/env python3
"""Comparative study: attribution rules evaluated against observed retirement.

Why this exists
---------------
The KAIS handling editor judged the comparative studies insufficient. The
manuscript compared Shapley against ranking-stage LOO and against three
semivalues, but it never asked the question a reader of an attribution paper
most wants answered: among the attribution rules actually in use, which one
best predicts what removing a source costs?

This script answers that on the released MovieLens-1M lattice. Every rule below
is a different linear functional of the SAME 32 coalition values, so no model is
refitted and no new randomness enters. The comparison is therefore exact, and
its cost is milliseconds.

Rules compared
--------------
* Shapley: coalition-size weights |S|!(n-|S|-1)!/n!.
* Banzhaf: uniform weight over coalitions, 1/2^(n-1). Drops efficiency.
* Binomial semivalues at q = 0.25 and q = 0.75: weight q^|S| (1-q)^(n-1-|S|),
  emphasising small and large coalitions respectively.
* Leave-one-out: the single marginal v(G) - v(G\\{g}).
* Leave-one-in (singleton value): v({g}) - v(empty). The opposite extreme to
  LOO, and the rule implied by "train each source alone and rank them".
* Permutation / forward-selection importance: the mean marginal gain over a
  greedy forward pass, averaged over all n! orders. At n=5 this is enumerable
  exactly, which makes it a fair comparator rather than a sampled one.
* Uniform split: v(G)/n. A deliberately trivial control. If an informative rule
  cannot beat this, the comparison says so.

Each rule is scored by Kendall tau against the OBSERVED end-to-end retirement
loss, which is the same ground truth Table 4 of the manuscript uses.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path

from scipy import stats

REPO = Path(__file__).resolve().parent.parent
ART = REPO / "artefacts"
PLAYERS = ("cf", "ct", "pop", "rec", "seq")


def load_lattice(path: Path) -> dict[frozenset[str], float]:
    raw = json.loads(path.read_text())["coalition_values"]
    out = {}
    for key, val in raw.items():
        members = frozenset() if key == "empty" else frozenset(key.split("+"))
        out[members] = float(val)
    if len(out) != 2 ** len(PLAYERS):
        raise SystemExit(f"expected 32 coalitions, got {len(out)}")
    return out


def _weighted_semivalue(v, weight) -> dict[str, float]:
    """Generic semivalue: sum_S w(|S|) [v(S + g) - v(S)]."""
    n = len(PLAYERS)
    out = {}
    for g in PLAYERS:
        others = [p for p in PLAYERS if p != g]
        total = 0.0
        for r in range(n):
            for combo in itertools.combinations(others, r):
                S = frozenset(combo)
                total += weight(r, n) * (v[S | {g}] - v[S])
        out[g] = total
    return out


def shapley(v):
    return _weighted_semivalue(
        v, lambda k, n: math.factorial(k) * math.factorial(n - k - 1) / math.factorial(n))


def banzhaf(v):
    return _weighted_semivalue(v, lambda k, n: 1.0 / 2 ** (n - 1))


def binomial(v, q):
    return _weighted_semivalue(
        v, lambda k, n: q ** k * (1 - q) ** (n - 1 - k))


def loo(v):
    grand = frozenset(PLAYERS)
    return {g: v[grand] - v[grand - {g}] for g in PLAYERS}


def leave_one_in(v):
    empty = frozenset()
    return {g: v[frozenset({g})] - v[empty] for g in PLAYERS}


def forward_selection(v):
    """Mean marginal gain over a greedy forward pass, averaged over all orders.

    At n = 5 the 120 permutations are enumerable, so this is the exact
    expectation rather than a sampled estimate. Note this is NOT Shapley:
    the greedy pass conditions on the set chosen so far by a *greedy* rule,
    not on every subset.
    """
    acc = {g: 0.0 for g in PLAYERS}
    cnt = {g: 0 for g in PLAYERS}
    for order in itertools.permutations(PLAYERS):
        S = frozenset()
        # Greedy: at each step take the surviving player with the largest gain,
        # breaking ties by the order given, so the pass is deterministic.
        remaining = list(order)
        while remaining:
            gains = {g: v[S | {g}] - v[S] for g in remaining}
            best = max(remaining, key=lambda g: (gains[g], -remaining.index(g)))
            acc[best] += gains[best]
            cnt[best] += 1
            S = S | {best}
            remaining.remove(best)
    return {g: acc[g] / cnt[g] for g in PLAYERS}


def uniform_split(v):
    grand = v[frozenset(PLAYERS)]
    return {g: grand / len(PLAYERS) for g in PLAYERS}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lattice", type=Path,
                    default=ART / "fig2_ndcg_sampling.json")
    ap.add_argument("--out", type=Path,
                    default=ART / "attribution_baselines.json")
    args = ap.parse_args()

    v = load_lattice(args.lattice)

    # Observed end-to-end retirement losses, seed 42, MovieLens-1M. These are
    # the values in Table 4 of the manuscript, from e12_retirement_ml_1m.json.
    observed = {"cf": -0.00468, "rec": -0.00128, "ct": -0.00050,
                "pop": 0.00253, "seq": 0.01702}

    rules = {
        "shapley": shapley(v),
        "banzhaf": banzhaf(v),
        "binomial_q025": binomial(v, 0.25),
        "binomial_q075": binomial(v, 0.75),
        "loo_rank": loo(v),
        "leave_one_in": leave_one_in(v),
        "forward_selection": forward_selection(v),
        "uniform_split": uniform_split(v),
    }

    order = [observed[g] for g in PLAYERS]
    results = {}
    for name, phi in rules.items():
        tau, p = stats.kendalltau([phi[g] for g in PLAYERS], order)
        # A constant vector (uniform_split) has zero variance, so Kendall tau
        # is undefined and scipy returns nan. Record that rather than letting
        # a nan propagate into a table as though it were a score. For the same
        # reason its "prediction" of the smallest source is an artefact of the
        # tie-break in min(), not a prediction, so it is withheld.
        degenerate = len(set(phi.values())) == 1
        smallest_pred = None if degenerate else min(PLAYERS, key=lambda g: phi[g])
        smallest_obs = min(PLAYERS, key=lambda g: observed[g])
        results[name] = {
            "values": phi,
            "kendall_tau_vs_observed_loss": None if degenerate else float(tau),
            "p_value": None if degenerate else float(p),
            "degenerate_constant_vector": degenerate,
            "sum": sum(phi.values()),
            "efficient": abs(sum(phi.values()) - v[frozenset(PLAYERS)]) < 1e-9,
            "identifies_smallest_loss_source": (
                None if degenerate else smallest_pred == smallest_obs),
            "predicted_smallest": smallest_pred,
        }

    payload = {
        "dataset": "ml_1m",
        "seed": 42,
        "game": "ranking_stage_ndcg10_baseline_centred",
        "note": (
            "Every rule is a different linear functional of the same 32 "
            "coalition values; no model is refitted, so the comparison "
            "introduces no additional randomness."),
        "observed_end_to_end_loss": observed,
        "observed_smallest_loss_source": min(PLAYERS, key=lambda g: observed[g]),
        "v_grand": v[frozenset(PLAYERS)],
        "rules": results,
    }
    args.out.write_text(json.dumps(payload, indent=1) + "\n")

    print(f"wrote {args.out.relative_to(REPO)}\n")
    print(f"{'rule':20s} {'tau':>7s} {'efficient':>10s}  picks-smallest")
    def sort_key(kv):
        t = kv[1]["kendall_tau_vs_observed_loss"]
        return 1.0 if t is None else -t

    for name, rec in sorted(results.items(), key=sort_key):
        t = rec["kendall_tau_vs_observed_loss"]
        tau_s = "   n/a" if t is None else f"{t:+7.2f}"
        pick = rec["predicted_smallest"] or "n/a"
        mark = "  <-- correct" if rec["identifies_smallest_loss_source"] else ""
        print(f"{name:20s} {tau_s:>7s} {str(rec['efficient']):>10s}  {pick}{mark}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
