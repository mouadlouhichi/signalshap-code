#!/usr/bin/env python3
"""Run the full E0-E8 study and write artefacts/ (spec §10).

Corpora are sized to available RAM BEFORE loading. Skipping that step is what
OOM-killed this script on Gowalla: at 52,985 x 121,866 the five score matrices
need 129 GB. The sizing lives in signalshap.memory and is shared with
run_full_revision.py so the two entry points cannot drift apart again.
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from signalshap.data.loaders import LOADERS, _register_timestamped  # noqa: E402
from signalshap.memory import (  # noqa: E402
    check_fits, check_paper_shape, default_budget_gb, free_gb, size_corpus)
from signalshap.pipeline import run_full_study  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true",
                    help="use planted synthetic corpora instead of raw files")
    ap.add_argument("--datasets", nargs="+",
                    default=["ml_1m", "lastfm_2k", "amazon_book"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    ap.add_argument("--budget-gb", type=float, default=None,
                    help="RAM the score matrices may use; default is 60%% of "
                         "free memory. Users per corpus are DERIVED from this, "
                         "so a large corpus downsizes instead of being killed.")
    ap.add_argument("--max-users", type=int, default=None,
                    help="hard cap, applied on top of the memory budget")
    a = ap.parse_args()

    budget = default_budget_gb(a.budget_gb)
    print(f"memory budget: {budget:.1f} GB (free: {free_gb():.1f} GB)")

    # Size every corpus first, so an unaffordable one is reported up front
    # rather than after an hour of work on the corpora before it.
    _register_timestamped()
    if not a.synthetic:
        caps: dict[str, int] = {}
        for name in a.datasets:
            loader = LOADERS.get(name)
            if loader is None:
                continue
            cap = size_corpus(name, loader, budget, a.max_users)
            ds = loader()
            ok, msg = check_fits(name, ds.n_users, ds.n_items, budget)
            print("  " + msg)
            shape_ok, why = check_paper_shape(name, ds.n_users, ds.n_items)
            del ds
            if not ok:
                sys.exit(1)
            if not shape_ok:
                sys.exit("REFUSING to overwrite the reported artefacts.\n  "
                         + why + "\n  Raise --budget-gb, or run one corpus at "
                         "a time so each gets its own cap.")
            caps[name] = cap
        if len(set(caps.values())) > 1:
            # One process-wide env var cannot hold two different caps. Taking
            # the smallest silently shrinks the other corpora, which is how a
            # multi-corpus run would quietly substitute a different MovieLens.
            # Refuse instead: the caller can run one corpus per invocation.
            sys.exit(
                f"corpora need different user caps {caps}. Running them "
                f"together would apply the smallest to all of them and change "
                f"the corpora the manuscript reports. Run them one at a time:\n"
                + "\n".join(f"  python scripts/run_study.py --datasets {k} "
                             f"--budget-gb {budget:.0f}" for k in caps))

    t0 = time.time()
    study = run_full_study(tuple(a.datasets), a.synthetic, tuple(a.seeds))
    print(f"\ncomplete in {time.time() - t0:.0f}s")
    for n, r in study["results"].items():
        d, m = r["e0a_candidates"], r["e0b_monotonicity"]
        flag = "PASS" if d["gate_passes"] else "FAIL <- see spec §2.2 ladder"
        print(f"  {n:12s} recall={d['candidate_recall']:.3f} {flag}  "
              f"monotonicity {m['violations']}/{m['pairs_checked']}")
        dead = (r.get("player_audit") or {}).get("degenerate_players") or []
        if dead:
            print(f"  {'':12s} DEGENERATE PLAYERS {dead} -- structurally "
                  f"zero, not evidence of redundancy")
