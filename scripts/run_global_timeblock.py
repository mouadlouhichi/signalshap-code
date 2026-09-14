#!/usr/bin/env python3
"""Globally time-blocked replication of the main claim.

    python scripts/run_global_timeblock.py --corpora ml_1m --budget-gb 24

The main study splits chronologically WITHIN each user: each user's last
interaction is test, the second-to-last validation. That is standard
leave-last-out, but it is not globally causal, and
`scripts/audit_global_time.py` measures the exposure: 44.2% of pooled training
events postdate the median MovieLens test event, 27.1% on Amazon-VG, 19.4% on
Gowalla.

This block replicates the central Shapley-versus-LOO and retirement result
under a single global cutoff T instead:

    train      = every event with t <= T_val
    validation = events in (T_val, T_test]
    test       = events after T_test

so no training event postdates any evaluated event. Nothing is fitted on the
future. The cost is coverage, which is exactly why the main study does not use
it: users with no interaction after T_test drop out entirely, and the surviving
population is biased toward heavy, late-active users. We therefore report this
as a robustness replication of the ORDERING and the LOO-versus-Shapley
contrast, not as a replacement for the main numbers.

The comparison that matters is whether the two conclusions survive:
  * the material sign disagreements, and
  * tau(LOO) > tau(Shapley) against observed retirement loss.

The second of those needs the end-to-end retirement simulation, not just the
attribution vectors, because the paper's central claim is a statement about
retirement: LOO tracks removal cost and Shapley does not. Running it under the
blocked split is the only way to know whether that claim depends on the
leave-last-out protocol's mild lookahead. `--retirement` turns it on. It costs
2^1 * 5 extra retrieval passes rather than 2^5, since only the five
leave-one-out coalitions are needed, but each pass rebuilds candidates.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np                                          # noqa: E402
from scipy.stats import kendalltau                          # noqa: E402

from signalshap.attribution.baselines import loo_attribution  # noqa: E402
from signalshap.candidates.builder import (                 # noqa: E402
    build_candidates, candidate_recall,
)
from signalshap.config import SOURCES, FrozenConfig, write_artefact  # noqa: E402
from signalshap.game.core import SignalShapGame, exact_shapley       # noqa: E402
from signalshap.memory import default_budget_gb, size_corpus         # noqa: E402
from signalshap.scorers.base import mask_seen, train_all_scorers     # noqa: E402


def global_split(ds, q_val: float = 0.90, q_test: float = 0.95):
    """One cutoff for everyone, by global timestamp quantile.

    Returns a shallow copy of `ds` whose train/valid/test folds are separated
    by calendar time rather than per-user position, plus coverage statistics.
    """
    import copy

    import pandas as pd

    allev = pd.concat([ds.train, ds.valid, ds.test], ignore_index=True)
    t = allev["timestamp"].to_numpy(dtype=np.float64)
    t_val, t_test = np.quantile(t, [q_val, q_test])

    tr = allev[allev["timestamp"] <= t_val]
    va = allev[(allev["timestamp"] > t_val) & (allev["timestamp"] <= t_test)]
    te = allev[allev["timestamp"] > t_test]

    # One held-out event per user, and only users present in every fold.
    def _last(df):
        return (df.sort_values(["user", "timestamp", "original_record_index"],
                               kind="mergesort")
                  .groupby("user", as_index=False).tail(1))

    va, te = _last(va), _last(te)
    keep = set(tr["user"]) & set(va["user"]) & set(te["user"])
    tr = tr[tr["user"].isin(keep)].reset_index(drop=True)
    va = va[va["user"].isin(keep)].reset_index(drop=True)
    te = te[te["user"].isin(keep)].reset_index(drop=True)

    out = copy.copy(ds)
    out.train, out.valid, out.test = tr, va, te
    stats = {
        "t_val_cutoff": float(t_val), "t_test_cutoff": float(t_test),
        "users_retained": int(len(keep)),
        "users_original": int(ds.n_users),
        "user_coverage": float(len(keep) / max(ds.n_users, 1)),
        "train_events": int(len(tr)),
        # The property the whole exercise is for.
        "train_events_after_any_test_event": int(
            (tr["timestamp"].to_numpy() > te["timestamp"].min()).sum())
        if len(te) else 0,
    }
    return out, stats


class _BlockedExperiment:
    """Minimal duck-typed stand-in for `Experiment`, on the blocked split.

    `retirement_simulation` and `coalition_retrieval_game` read exactly seven
    attributes. Rather than construct a real `Experiment` -- which would reload
    the corpus and rebuild the per-user leave-last-out folds, discarding the
    global cutoff this whole script exists to impose -- we hand them the
    blocked state directly. The attribute list is asserted in
    `tests/test_blocked_retirement.py`, so a future field added to the
    estimands code cannot silently read a stale value off this object.
    """

    __slots__ = ("name", "cfg", "ds", "n_max", "scores", "candidates",
                 "valid_items", "test_items", "v")

    def __init__(self, name, cfg, ds, n_max, scores, candidates,
                 valid_items, test_items, v):
        self.name = name
        self.cfg = cfg
        self.ds = ds
        self.n_max = n_max
        self.scores = scores
        self.candidates = candidates
        self.valid_items = valid_items
        self.test_items = test_items
        self.v = v


def run(name: str, cfg: FrozenConfig, seed: int = 42,
        retirement: bool = False) -> dict:
    from signalshap.data.loaders import load_dataset

    G = frozenset(SOURCES)
    ds = load_dataset(name, seed=seed)
    blocked, stats = global_split(ds)
    n_max = cfg.n_max[name]

    def _items(df):
        return dict(zip(df["user"].to_numpy(), df["item"].to_numpy()))

    scores = mask_seen(train_all_scorers(blocked, seed=seed), blocked)
    cands = build_candidates(scores, blocked.n_users, n_max,
                             cfg.max_growth_iters)
    valid, test = _items(blocked.valid), _items(blocked.test)
    game = SignalShapGame(scores, cands, valid, test,
                          ridge_lambda=cfg.ridge_lambda, k_ndcg=cfg.k_ndcg,
                          v0_seed=cfg.v0_seed)
    v = game.v_all()
    phi, loo = exact_shapley(v), loo_attribution(v)
    order = list(SOURCES)

    flips = [g for g in SOURCES
             if phi[g] * loo[g] < 0 and abs(phi[g] - loo[g]) > 1e-3]

    retire = None
    if retirement:
        from signalshap.experiments.estimands import retirement_simulation
        exp = _BlockedExperiment(name, cfg, blocked, n_max, scores, cands,
                                 valid, test, v)
        retire = retirement_simulation(exp, verbose=True)
        # The headline contrast, lifted out so no reader has to recompute it.
        retire["tau_advantage_loo_minus_shapley"] = (
            retire["kendall_tau_loo_vs_truth"]
            - retire["kendall_tau_shapley_vs_truth"])
        retire["blocked_split"] = True

    return {
        "dataset": name, "seed": seed, "split": "global time block",
        **stats,
        "candidate_recall": float(candidate_recall(cands, test)),
        "shapley": phi, "loo": loo,
        "gap": {g: phi[g] - loo[g] for g in SOURCES},
        "v_grand": v[G],
        "ordering": sorted(order, key=lambda g: -phi[g]),
        "material_flips": flips,
        "retirement": retire,
        "note": (
            "Single global cutoff at the 0.90/0.95 timestamp quantiles, so no "
            "training event postdates any evaluated event. Coverage falls "
            "because users inactive after the cutoff drop out, and the "
            "survivors skew heavy and late-active; this is a robustness "
            "replication of the ordering and the LOO-versus-Shapley contrast, "
            "not a replacement for the main numbers."),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpora", nargs="+", default=["ml_1m"])
    ap.add_argument("--budget-gb", type=float, default=None)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--retirement", action="store_true",
                    help="also run the end-to-end retirement simulation under "
                         "the blocked split (review item 3)")
    a = ap.parse_args()
    cfg = FrozenConfig.load()
    budget = default_budget_gb(a.budget_gb)
    out: dict = {}
    prior = Path("artefacts") / "global_timeblock.json"
    if prior.exists():
        try:
            out = json.loads(prior.read_text())
        except (json.JSONDecodeError, OSError):
            out = {}
    for name in a.corpora:
        from signalshap.data.loaders import LOADERS, _register_timestamped  # noqa: F811
        _register_timestamped()
        if name in ("gowalla_ts", "amazon_video_games"):
            size_corpus(name, LOADERS[name], budget, verbose=True)
        r = run(name, cfg, a.seed, retirement=a.retirement)
        if r["users_retained"] == 0:
            # Every user fell entirely on one side of the cutoff. On real
            # corpora users overlap in calendar time so this cannot happen;
            # it does on the synthetic fixture, whose users occupy disjoint
            # windows. Fail loudly rather than write an empty result.
            raise SystemExit(
                f"{name}: a global cutoff retained no user. This corpus has no "
                f"calendar overlap between users, so a globally blocked split "
                f"is not defined for it.")
        out[name] = r
        write_artefact("global_timeblock.json", out)
        print(f"{name}: {r['users_retained']:,}/{r['users_original']:,} users "
              f"retained, recall {r['candidate_recall']:.3f}, "
              f"order {' > '.join(r['ordering'])}, "
              f"flips {r['material_flips'] or 'none'}", flush=True)
        if r.get("retirement"):
            t = r["retirement"]
            print(f"   retirement: tau_LOO={t['kendall_tau_loo_vs_truth']:+.2f} "
                  f"tau_Shapley={t['kendall_tau_shapley_vs_truth']:+.2f} "
                  f"(advantage {t['tau_advantage_loo_minus_shapley']:+.2f}); "
                  f"cheapest truly {t['cheapest_to_retire_true']}, "
                  f"LOO says {t['cheapest_by_loo']}, "
                  f"Shapley says {t['cheapest_by_shapley']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
