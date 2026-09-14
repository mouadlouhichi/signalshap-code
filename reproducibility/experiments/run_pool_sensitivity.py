#!/usr/bin/env python3
"""Does the attribution survive a candidate pool the players did not build?

    python experiments/run_pool_sensitivity.py --corpora ml_1m --budget-gb 24

The main game fixes C_u to the union of every source's own top-N list. That
construction is coalition-independent, which is the property the game needs:
every coalition ranks exactly the same items, so no coalition is handed a pool
selected in its own favour. It is NOT source-independent. The pool is still
built BY the five players, and a reviewer's residual worry is that this could
flatter the sources that shaped it: an item enters C_u because some source
ranked it highly, so the pool is enriched for exactly the things the players
are good at.

The check is to rebuild the pool from a rule that consults no player at all,
recompute the whole game on it, and ask whether the conclusions move. Three
neutral rules, none of which reads a source score matrix:

  popularity  the N globally most frequent training items, identical for
              every user. Cheap, realistic, and the usual production fallback.
              Caveat, stated rather than hidden: `pop` is itself a player, so
              this rule is neutral with respect to the OTHER four but is
              correlated with one of them. It is reported for realism, and the
              random rule is the strictly neutral one.
  random      N items drawn uniformly without replacement from the eligible
              catalogue, keyed by (seed, user) through the same BLAKE2b
              hashing the baseline permutation uses, so it is reproducible
              across platforms and NumPy versions. Strictly independent of
              every source. Recall collapses to roughly N/|I|, which is the
              point: it is a stress test, not a proposal.
  oracle      the random pool with the test item forcibly inserted. This
              separates two things the random rule confounds. Under `random`
              most users have no retrievable target, so v collapses toward
              zero for the dilution reason documented in Section 5, and a
              flat game says nothing about attribution. `oracle` restores a
              retrievable target while keeping the DISTRACTORS source-blind,
              which is the cleanest available test of whether the ranking
              conclusions depend on who picked the pool.

What we compare is the ordering and the sign pattern, not the levels. Levels
are not comparable across pools: each rule yields a different |C_u|, hence a
different expected-random baseline and a different recall ceiling.
"""
from __future__ import annotations

import argparse
import hashlib
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


def _eligible(scores: dict[str, np.ndarray], u: int) -> np.ndarray:
    """Items not masked out by the training history.

    Read off the finite entries of one source's row. `mask_seen` writes -inf
    into the SAME positions for every source, so this is a property of the
    user's history rather than of the source consulted, and no score value is
    used.
    """
    row = next(iter(scores.values()))[u]
    return np.flatnonzero(np.isfinite(row))


def popularity_pool(ds, scores, n_max: int) -> list[np.ndarray]:
    """The N globally most frequent training items, restricted to eligibles."""
    counts = np.bincount(ds.train["item"].to_numpy(), minlength=ds.n_items)
    # Ties broken by ascending item index, matching the ranking tie rule.
    order = np.lexsort((np.arange(ds.n_items), -counts))
    out = []
    for u in range(ds.n_users):
        ok = set(_eligible(scores, u).tolist())
        out.append(np.array([i for i in order if i in ok][:n_max], dtype=np.int64))
    return out


def _hash_sample(items: np.ndarray, n: int, seed: int, user: int) -> np.ndarray:
    """Uniform-without-replacement sample, deterministic across platforms.

    Sorting by a keyed digest and taking the prefix is a uniform random
    sample. A NumPy Generator would be reproducible only within a version
    series, which has already caused a real cross-machine divergence in this
    project (spec entry 36), so the same BLAKE2b construction as the baseline
    permutation is reused here.
    """
    prefix = seed.to_bytes(8, "little") + int(user).to_bytes(8, "little")
    keys = np.array(
        [int.from_bytes(hashlib.blake2b(prefix + int(i).to_bytes(8, "little"),
                                        digest_size=8).digest(), "little")
         for i in items], dtype=np.uint64)
    return items[np.lexsort((items, keys))][:n]


def random_pool(ds, scores, n_max: int, seed: int,
                test_items: dict | None = None) -> list[np.ndarray]:
    """Source-blind pool. With `test_items`, force the target in (oracle)."""
    out = []
    for u in range(ds.n_users):
        elig = _eligible(scores, u)
        pick = _hash_sample(elig, n_max, seed, u)
        if test_items is not None and u in test_items:
            t = int(test_items[u])
            if t in set(elig.tolist()) and t not in set(pick.tolist()):
                pick = np.concatenate([pick[:-1], [t]]) if len(pick) else np.array([t])
        out.append(np.sort(pick).astype(np.int64))
    return out


def _evaluate(scores, cands, valid, test, cfg) -> dict:
    game = SignalShapGame(scores, cands, valid, test,
                          ridge_lambda=cfg.ridge_lambda, k_ndcg=cfg.k_ndcg,
                          v0_seed=cfg.v0_seed)
    v = game.v_all()
    phi, loo = exact_shapley(v), loo_attribution(v)
    sizes = np.array([len(c) for c in cands])
    return {
        "shapley": phi,
        "loo": loo,
        "gap": {g: phi[g] - loo[g] for g in SOURCES},
        "v_grand": v[frozenset(SOURCES)],
        "candidate_recall": float(candidate_recall(cands, test)),
        "mean_pool_size": float(sizes.mean()),
        "ordering": sorted(SOURCES, key=lambda g: -phi[g]),
        "material_flips": sorted(
            g for g in SOURCES
            if phi[g] * loo[g] < 0 and abs(phi[g] - loo[g]) > 1e-3),
    }


def run(name: str, cfg: FrozenConfig, seed: int = 42) -> dict:
    from signalshap.data.loaders import load_dataset

    ds = load_dataset(name, seed=seed)
    n_max = cfg.n_max[name]
    scores = mask_seen(train_all_scorers(ds, seed=seed), ds)
    valid = dict(zip(ds.valid["user"].to_numpy(), ds.valid["item"].to_numpy()))
    test = dict(zip(ds.test["user"].to_numpy(), ds.test["item"].to_numpy()))

    pools = {
        "union_of_top_n": build_candidates(scores, ds.n_users, n_max,
                                           cfg.max_growth_iters),
        "popularity": popularity_pool(ds, scores, n_max),
        "random": random_pool(ds, scores, n_max, seed),
        "random_oracle": random_pool(ds, scores, n_max, seed, test),
    }

    out: dict = {"dataset": name, "seed": seed, "n_max": n_max, "pools": {}}
    for label, cands in pools.items():
        print(f"    [pool] {label}...", flush=True)
        out["pools"][label] = _evaluate(scores, cands, valid, test, cfg)

    ref = out["pools"]["union_of_top_n"]
    order = list(SOURCES)
    out["agreement"] = {}
    for label, r in out["pools"].items():
        if label == "union_of_top_n":
            continue
        t = kendalltau([ref["shapley"][g] for g in order],
                       [r["shapley"][g] for g in order]).correlation
        out["agreement"][label] = {
            "kendall_tau_vs_union": float(t) if np.isfinite(t) else None,
            "same_top_source": ref["ordering"][0] == r["ordering"][0],
            "sign_agreement": bool(all(
                (ref["shapley"][g] > 0) == (r["shapley"][g] > 0) for g in order)),
            "same_material_flips": ref["material_flips"] == r["material_flips"],
            "recall_ratio": (r["candidate_recall"] / ref["candidate_recall"]
                             if ref["candidate_recall"] else None),
        }

    out["note"] = (
        "Neutral-pool sensitivity. The main pool is coalition-independent but "
        "still built BY the players; these rules consult no source score. "
        "Compare ORDERINGS and SIGNS only: each rule gives a different |C_u|, "
        "hence a different expected-random baseline and a different recall "
        "ceiling, so absolute values are not comparable across pools. The "
        "popularity rule is neutral with respect to four of the five players "
        "but correlated with `pop`; `random` is strictly neutral but nearly "
        "all users lose a retrievable target, so `random_oracle` restores the "
        "target while keeping the distractors source-blind.")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpora", nargs="+", default=["ml_1m"])
    ap.add_argument("--budget-gb", type=float, default=None)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    cfg = FrozenConfig.load()
    budget = default_budget_gb(a.budget_gb)

    # Resume rather than overwrite: running one corpus must not delete the
    # others (the bug that once wiped ml_1m and amazon from an artefact).
    out: dict = {}
    prior = Path("artefacts") / "pool_sensitivity.json"
    if prior.exists():
        try:
            out = json.loads(prior.read_text())
            if out:
                print(f"  resuming; already have {sorted(k for k in out)}", flush=True)
        except (json.JSONDecodeError, OSError):
            out = {}

    for name in a.corpora:
        from signalshap.data.loaders import LOADERS, _register_timestamped
        _register_timestamped()
        if name in ("gowalla_ts", "amazon_video_games"):
            size_corpus(name, LOADERS[name], budget, verbose=True)
        print(f"== {name}", flush=True)
        r = run(name, cfg, a.seed)
        out[name] = r
        write_artefact("pool_sensitivity.json", out)
        for label, ag in r["agreement"].items():
            t = ag["kendall_tau_vs_union"]
            print(f"   {label:14s} tau={t if t is None else round(t, 2)} "
                  f"top_same={ag['same_top_source']} "
                  f"signs={ag['sign_agreement']} "
                  f"recall={r['pools'][label]['candidate_recall']:.3f}",
                  flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
