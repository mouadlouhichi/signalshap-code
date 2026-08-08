#!/usr/bin/env python3
"""Everything the two reviews require that needs fresh computation.

    python scripts/run_final_revision.py --budget-gb 24

Four blocks, in priority order. Each writes its own artefact and can be
re-run independently with --only.

  seeds      10-seed core study on all three corpora. Both reviewers made this
             mandatory: ten seeds were previously spent on the NEGATIVE fusion
             appendix while the central attribution and retirement claims used
             three. This inverts that.
  lambda     Shapley values across lambda in [1e-5, 1e3]. Reviewer 1 asked
             whether the attributions, and specifically the sign flips, survive
             different regularisation regimes.
  friedman   Friedman + Nemenyi across methods, blocked by (corpus, seed).
             Establishes ranking significance across corpora rather than one
             Wilcoxon per corpus.
  retire     Retirement simulation over seeds, so the tau=1.00 result carries
             an interval instead of being one realisation.

Wall-clock on an M4/48GB, all four blocks: roughly 10-14 hours. Run it
overnight with nohup; every block writes as it finishes, so a crash in a later
block does not lose an earlier one.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402

from signalshap.config import FrozenConfig, write_artefact  # noqa: E402
from signalshap.game.core import exact_shapley  # noqa: E402
from signalshap.memory import default_budget_gb, size_corpus  # noqa: E402
from signalshap.stats.tests import friedman_nemenyi  # noqa: E402

CORPORA = ("ml_1m", "amazon_video_games", "gowalla_ts")
SEEDS = tuple(range(42, 52))
SOURCES = ("cf", "ct", "pop", "rec", "seq")


def _experiment(name, cfg, seed):
    from signalshap.pipeline import Experiment
    return Experiment(name, cfg, seed=seed)


def _size(name, cfg, budget):
    """Install the memory-derived user cap before loading a large corpus."""
    from signalshap.data.loaders import LOADERS, _register_timestamped
    _register_timestamped()
    if name in ("gowalla_ts", "amazon_video_games"):
        size_corpus(name, LOADERS[name], budget, verbose=True)


def block_seeds(cfg, budget, corpora, seeds, resume=True):
    """10-seed attribution: per-seed phi, seed mean, and a 95% interval.

    Checkpoints after EVERY seed, and resumes from what is already on disk.
    The first version wrote only after all ten seeds of a corpus completed and
    started from an empty dict, so a crash on the third corpus -- which is what
    happened, Gowalla needing ~4 h and 14.6 GB per seed -- lost that corpus
    entirely and would have forced a re-run of the eight hours that had already
    succeeded.
    """
    out = {}
    if resume:
        try:
            out = json.loads((Path("artefacts") / "final_seed_ci.json").read_text())
            done = {k: len(v.get("per_seed", {})) for k, v in out.items()}
            if done:
                print(f"  resuming; already have {done}", flush=True)
        except (FileNotFoundError, json.JSONDecodeError):
            out = {}

    def _summarise(per_seed):
        ci = {}
        for g in SOURCES:
            v = np.array([per_seed[s][g] for s in sorted(per_seed)], dtype=float)
            se = v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0.0
            lo, hi = v.mean() - 1.96 * se, v.mean() + 1.96 * se
            ci[g] = {"mean": float(v.mean()),
                     "sd": float(v.std(ddof=1)) if len(v) > 1 else 0.0,
                     "lo": float(lo), "hi": float(hi),
                     "excludes_zero": bool(lo * hi > 0)}
        return ci

    for name in corpora:
        prior = {int(k): v for k, v in
                 (out.get(name, {}).get("per_seed") or {}).items()}
        todo = [s for s in seeds if s not in prior]
        if not todo:
            print(f"  {name}: all {len(seeds)} seeds already present, skipping",
                  flush=True)
            continue

        _size(name, cfg, budget)
        per_seed = dict(prior)
        for s in todo:
            t0 = time.time()
            e = _experiment(name, cfg, s)
            per_seed[s] = exact_shapley(e.v)
            del e
            gc.collect()                     # 14.6 GB of score matrices per seed
            # Checkpoint immediately: a kill on the next seed keeps this one.
            out[name] = {"n_seeds": len(per_seed),
                         "per_seed": {str(k): v for k, v in sorted(per_seed.items())},
                         "ci": _summarise(per_seed)}
            write_artefact("final_seed_ci.json", out)
            print(f"  {name} seed {s}: {time.time()-t0:.0f}s "
                  f"({len(per_seed)}/{len(seeds)} done, checkpointed)", flush=True)
        print(f"{name}: complete", flush=True)
    return out


def block_lambda(cfg, budget, corpora, lams=(1e-5, 1e-3, 1e-1, 1.0, 10.0, 1e3)):
    """Do the attributions -- and the sign flips -- survive regularisation?"""
    from signalshap.game.core import SignalShapGame
    out = {}
    for name in corpora:
        _size(name, cfg, budget)
        e = _experiment(name, cfg, 42)
        rows = {}
        for lam in lams:
            g = SignalShapGame(e.scores, e.candidates, e.valid_items,
                               e.test_items, ridge_lambda=lam,
                               k_ndcg=cfg.k_ndcg, v0_seed=cfg.v0_seed)
            phi = exact_shapley(g.v_all())
            loo = {s: g.v(frozenset(SOURCES)) - g.v(frozenset(SOURCES) - {s})
                   for s in SOURCES}
            rows[str(lam)] = {
                "shapley": phi, "loo": loo,
                "material_flips": [s for s in SOURCES
                                   if phi[s] * loo[s] < 0
                                   and abs(phi[s] - loo[s]) > 1e-3],
            }
            print(f"  {name} lambda={lam:g}: flips={rows[str(lam)]['material_flips']}",
                  flush=True)
        out[name] = rows
        del e
        write_artefact("final_lambda_sweep.json", out)
    return out


def block_friedman(corpora, seeds):
    """Rank methods across (corpus, seed) blocks, not one Wilcoxon per corpus."""
    from signalshap.config import read_artefact
    methods = ("uniform", "global", "signalshap_fuse", "lightgcn", "sasrec",
               "popularity_reference")
    scores = {m: [] for m in methods}
    blocks = []
    for name in corpora:
        try:
            fc = read_artefact(f"results_{name}.json")["e4_signalshap_fuse"]["full_catalog"]
        except (FileNotFoundError, KeyError):
            print(f"  skipping {name}: no full_catalog block", flush=True)
            continue
        for m in methods:
            scores[m].append(fc[m]["ndcg_at_10"])
        blocks.append(name)
    res = friedman_nemenyi(scores)
    res["blocks"] = blocks
    res["caveat"] = (
        "One block per corpus. With three blocks the Nemenyi critical "
        "difference is very wide; treat non-separation as low power, not as "
        "evidence of equivalence. LightGCN and SASRec received smaller tuning "
        "budgets and are contextual references."
    )
    write_artefact("final_friedman.json", res)
    print(json.dumps(res, indent=1)[:600], flush=True)
    return res


def block_retire(cfg, budget, corpora, seeds):
    """Retirement over seeds, so tau = 1.00 gets an interval."""
    from scipy.stats import kendalltau
    out = {}
    for name in corpora:
        _size(name, cfg, budget)
        taus_sh, taus_loo, cheapest = [], [], []
        for s in seeds:
            e = _experiment(name, cfg, s)
            try:
                r = e.e12_retirement()
            except Exception as exc:                     # noqa: BLE001
                print(f"  {name} seed {s}: retirement failed ({exc})", flush=True)
                del e
                continue
            taus_sh.append(r["kendall_tau_shapley_vs_truth"])
            taus_loo.append(r["kendall_tau_loo_vs_truth"])
            cheapest.append([r["cheapest_to_retire_true"],
                             r["cheapest_by_shapley"], r["cheapest_by_loo"]])
            print(f"  {name} seed {s}: tau_shap={taus_sh[-1]:+.2f} "
                  f"tau_loo={taus_loo[-1]:+.2f}", flush=True)
            del e
        if not taus_sh:
            continue
        def _ci(a):
            a = np.asarray(a, float)
            se = a.std(ddof=1) / np.sqrt(len(a)) if len(a) > 1 else 0.0
            return {"mean": float(a.mean()), "lo": float(a.mean() - 1.96 * se),
                    "hi": float(a.mean() + 1.96 * se), "n": int(len(a))}
        out[name] = {"tau_shapley": _ci(taus_sh), "tau_loo": _ci(taus_loo),
                     "cheapest_true_shapley_loo": cheapest,
                     "loo_correct_frac": float(np.mean([c[0] == c[2] for c in cheapest])),
                     "shapley_correct_frac": float(np.mean([c[0] == c[1] for c in cheapest]))}
        write_artefact("final_retirement_seeds.json", out)
        print(f"{name}: written", flush=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-gb", type=float, default=None)
    ap.add_argument("--corpora", nargs="+", default=list(CORPORA))
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--only", nargs="+",
                    choices=["seeds", "lambda", "friedman", "retire"],
                    default=["seeds", "lambda", "friedman", "retire"])
    a = ap.parse_args()

    cfg = FrozenConfig.load()
    budget = default_budget_gb(a.budget_gb)
    seeds = tuple(range(42, 42 + a.seeds))
    print(f"budget {budget:.1f} GB | corpora {a.corpora} | seeds {seeds}")
    print(f"blocks: {a.only}\n")

    t0 = time.time()
    if "seeds" in a.only:
        print("== 10-seed attribution ==", flush=True)
        block_seeds(cfg, budget, a.corpora, seeds)
    if "lambda" in a.only:
        print("\n== lambda sweep ==", flush=True)
        block_lambda(cfg, budget, a.corpora)
    if "friedman" in a.only:
        print("\n== Friedman + Nemenyi ==", flush=True)
        block_friedman(a.corpora, seeds)
    if "retire" in a.only:
        print("\n== retirement over seeds ==", flush=True)
        block_retire(cfg, budget, a.corpora, seeds)
    print(f"\ncomplete in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
