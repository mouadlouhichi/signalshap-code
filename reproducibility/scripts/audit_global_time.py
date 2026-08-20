#!/usr/bin/env python3
"""Is the split globally time-blocked, or only chronological per user?

    python scripts/audit_global_time.py --corpora ml_1m amazon_video_games

The split takes each user's last interaction as test and second-to-last as
validation. That is chronological WITHIN a user. It does not follow that the
pooled training fold precedes every test event in calendar time: user A's
training events can postdate user B's test event. Because ALS, the PPMI
co-occurrence matrix and the decayed popularity counts are all fitted on the
pooled training fold, and popularity decays relative to the GLOBAL latest
training timestamp, such events are visible to the scorer at prediction time.

A reviewer asked for the size of that exposure. This measures it:

  * fraction of test users whose test timestamp precedes the global t_max;
  * fraction of pooled training events that postdate a given user's test event,
    averaged over users;
  * the same for validation.

It reports rather than repairs. A globally time-blocked replication would need
a single cutoff date and would discard a large share of each corpus.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np                                          # noqa: E402

from signalshap.config import write_artefact                # noqa: E402


def audit(name: str, synthetic: bool = False) -> dict:
    from signalshap.data.loaders import load_dataset

    ds = load_dataset(name, synthetic=synthetic, seed=42)
    tr = ds.train["timestamp"].to_numpy(dtype=np.float64)
    te = ds.test["timestamp"].to_numpy(dtype=np.float64)
    va = ds.valid["timestamp"].to_numpy(dtype=np.float64)
    t_max = float(tr.max())

    tr_sorted = np.sort(tr)
    # For each held-out event, how many pooled training events postdate it?
    def _future_frac(hold: np.ndarray) -> np.ndarray:
        after = len(tr_sorted) - np.searchsorted(tr_sorted, hold, side="right")
        return after / len(tr_sorted)

    ft, fv = _future_frac(te), _future_frac(va)
    return {
        "dataset": name,
        "n_train_events": int(len(tr)),
        "global_t_max_in_train": t_max,
        "test_events_before_global_t_max": float(np.mean(te < t_max)),
        "valid_events_before_global_t_max": float(np.mean(va < t_max)),
        "future_train_fraction_vs_test": {
            "mean": float(ft.mean()), "median": float(np.median(ft)),
            "p90": float(np.percentile(ft, 90)), "max": float(ft.max()),
        },
        "future_train_fraction_vs_valid": {
            "mean": float(fv.mean()), "median": float(np.median(fv)),
        },
        "note": (
            "Non-zero values mean the split is chronological PER USER but not "
            "globally time-blocked: pooled training events postdate some users' "
            "held-out events and are visible to ALS, PPMI and the decayed "
            "popularity counts. This is standard for leave-last-out recommender "
            "evaluation and is reported, not repaired; a globally blocked "
            "replication needs one cutoff date and discards much of the corpus."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpora", nargs="+", default=["ml_1m"])
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    out = {}
    for name in a.corpora:
        out[name] = audit(name, a.synthetic)
        r = out[name]
        print(f"{name}: {100*r['test_events_before_global_t_max']:.1f}% of test "
              f"events precede global t_max; mean future-train fraction "
              f"{100*r['future_train_fraction_vs_test']['mean']:.1f}%", flush=True)
        write_artefact("global_time_audit.json", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
