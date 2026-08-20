#!/usr/bin/env python3
"""Full revision run: timestamped corpora, 10 seeds, matched baselines.

    python experiments/run_full_revision.py --seeds 10 --corpora ml_1m gowalla_ts

Refuses to run on a corpus whose timestamps are not genuine, and refuses to
fall back to synthetic data. Both failures produced withdrawn results before.
"""
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
from signalshap.data.timestamped import (  # noqa: E402
    TIMESTAMPED_LOADERS, temporal_validity_report)
from signalshap.game.core import exact_shapley  # noqa: E402
from signalshap.memory import (  # noqa: E402
    check_fits, default_budget_gb, free_gb, scores_gb, size_corpus)
from signalshap.pipeline import Experiment  # noqa: E402
from signalshap.stats.tests import (  # noqa: E402
    hierarchical_bootstrap, rank_biserial, tost_equivalence)

#: Players that require genuine interaction times.
TEMPORAL_PLAYERS = ("rec", "seq", "pop")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpora", nargs="+", default=["ml_1m"])
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--max-users", type=int, default=None)
    ap.add_argument("--tost-margin", type=float, default=0.002,
                    help="PRE-SPECIFY this before looking at results")
    ap.add_argument("--allow-untimestamped", action="store_true")
    ap.add_argument("--budget-gb", type=float, default=None,
                    help="RAM the score matrices may use; default is 60%% of "
                         "free memory. Users per corpus are DERIVED from this, "
                         "so a large corpus downsizes instead of being killed.")
    a = ap.parse_args()

    budget = default_budget_gb(a.budget_gb)
    print(f"memory budget: {budget:.1f} GB (free: {free_gb():.1f} GB)")

    seeds = tuple(range(42, 42 + a.seeds))
    cfg = FrozenConfig.load()
    print(f"seeds: {seeds}\nTOST margin (pre-specified): {a.tost_margin}\n")

    summary = {}
    for name in a.corpora:
        if a.max_users:
            os.environ["SIGNALSHAP_MAX_USERS"] = str(a.max_users)

        # --- gate 1: temporal validity, and size the corpus to memory -----
        if name in TIMESTAMPED_LOADERS:
            size_corpus(name, TIMESTAMPED_LOADERS[name], budget, a.max_users)
            ds = TIMESTAMPED_LOADERS[name]()
            ok, msg = check_fits(name, ds.n_users, ds.n_items, budget)
            print(msg)
            if not ok:
                continue
            rep = temporal_validity_report(ds)
            print(f"{name}: temporally_valid={rep['temporally_valid']} "
                  f"span={rep['span_days']:.0f}d "
                  f"unique_frac={rep['unique_fraction']:.3f}")
            if not rep["temporally_valid"] and not a.allow_untimestamped:
                print(f"  SKIP: {TEMPORAL_PLAYERS} would be uninterpretable. "
                      "Pass --allow-untimestamped to override.")
                continue
            write_artefact(f"temporal_validity_{name}.json", rep)

        per_seed_phi, per_seed_fuse, per_seed_global = {}, {}, {}
        for s in seeds:
            t = time.time()
            exp = Experiment(name, cfg, seed=s, synthetic=False)
            if exp.ds.synthetic:
                print(f"  ABORT: {name} fell back to synthetic data")
                return 1
            per_seed_phi[s] = exact_shapley(exp.v)
            e4 = exp.e4_signalshap_fuse()
            per_seed_fuse[s] = e4["per_user"]["signalshap_fuse"]
            per_seed_global[s] = e4["per_user"]["global"]
            print(f"  seed {s}: {time.time()-t:.0f}s", flush=True)
            del exp
            gc.collect()

        # --- hierarchical inference over (seed, user) ----------------------
        hb = hierarchical_bootstrap(per_seed_fuse, per_seed_global, seed=42)
        first = seeds[0]
        tost = tost_equivalence(per_seed_fuse[first], per_seed_global[first],
                                margin=a.tost_margin)
        rb = rank_biserial(per_seed_fuse[first], per_seed_global[first])

        sources = list(per_seed_phi[first])
        phi_ci = {
            g: {
                "mean": float(np.mean([per_seed_phi[s][g] for s in seeds])),
                "sd": float(np.std([per_seed_phi[s][g] for s in seeds], ddof=1)),
                "lo": float(np.percentile([per_seed_phi[s][g] for s in seeds], 2.5)),
                "hi": float(np.percentile([per_seed_phi[s][g] for s in seeds], 97.5)),
            } for g in sources
        }

        summary[name] = {
            "n_seeds": len(seeds),
            "shapley_seed_ci": phi_ci,
            "fuse_vs_global_hierarchical": hb,
            "fuse_vs_global_tost": tost,
            "rank_biserial": rb,
        }
        write_artefact(f"revision_{name}.json", summary[name])
        print(f"  {name}: fuse-vs-global {hb['mean_diff']:+.5f} "
              f"CI[{hb['lo']:+.5f},{hb['hi']:+.5f}] "
              f"excludes0={hb['excludes_zero']} "
              f"TOST equivalent={tost['equivalent']}\n")

    write_artefact("revision_summary.json", summary)
    print(json.dumps({k: v["fuse_vs_global_hierarchical"]["mean_diff"]
                      for k, v in summary.items()}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
