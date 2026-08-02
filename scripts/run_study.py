#!/usr/bin/env python3
"""Run the full E0-E8 study and write artefacts/ (spec §10)."""
import argparse, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from signalshap.pipeline import run_full_study

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true",
                    help="use planted synthetic corpora instead of raw files")
    ap.add_argument("--datasets", nargs="+",
                    default=["ml_1m", "lastfm_2k", "amazon_book"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    a = ap.parse_args()

    t0 = time.time()
    study = run_full_study(tuple(a.datasets), a.synthetic, tuple(a.seeds))
    print(f"\ncomplete in {time.time() - t0:.0f}s")
    for n, r in study["results"].items():
        d, m = r["e0a_candidates"], r["e0b_monotonicity"]
        flag = "PASS" if d["gate_passes"] else "FAIL <- see spec §2.2 ladder"
        print(f"  {n:12s} recall={d['candidate_recall']:.3f} {flag}  "
              f"monotonicity {m['violations']}/{m['pairs_checked']}")
