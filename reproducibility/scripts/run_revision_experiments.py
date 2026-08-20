#!/usr/bin/env python3
"""Run the experiments added in response to review (E10-E13).

    python scripts/run_revision_experiments.py --dataset ml_1m [--skip-e2e]

E10  alternative cooperative values + Shapley-Taylor interactions   (fast)
E11  fixed-head vs refitted-head vs end-to-end estimands            (slow)
E12  end-to-end source-retirement simulation                        (slow)
E13  analytic games with known Shapley vectors                      (instant)

E11 and E12 rebuild candidate sets per coalition, so they cost 2^n retrieval
passes. Use --skip-e2e on a memory-constrained machine.
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from signalshap.config import FrozenConfig, write_artefact  # noqa: E402
from signalshap.pipeline import Experiment  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="ml_1m")
    ap.add_argument("--max-users", type=int, default=None)
    ap.add_argument("--skip-e2e", action="store_true",
                    help="skip the 2^n-retrieval experiments (E11 e2e, E12)")
    a = ap.parse_args()

    if a.max_users:
        os.environ["SIGNALSHAP_MAX_USERS"] = str(a.max_users)

    # E13 needs no data at all -- run it first as a smoke test.
    from signalshap.experiments.synthetic_games import validate_implementation
    e13 = validate_implementation()
    write_artefact("e13_synthetic_ground_truth.json", e13)
    print(f"E13 analytic games: {e13['_summary']}")
    if not e13["_summary"]["all_pass"]:
        sys.exit("E13 FAILED -- the estimator disagrees with a closed-form vector")

    t0 = time.time()
    exp = Experiment(a.dataset, FrozenConfig.load(), 42, synthetic=False)
    if exp.ds.synthetic:
        sys.exit(f"{a.dataset}: loader fell back to SYNTHETIC data -- aborting. "
                 "Place the raw corpus under data/raw/ first.")
    print(f"setup {time.time()-t0:.0f}s  users={exp.ds.n_users}")

    r10 = exp.e10_alternative_values()
    write_artefact(f"e10_values_{a.dataset}.json", r10)
    print(f"E10 values: shapley top={r10['shapley_top']} "
          f"banzhaf top={r10['banzhaf_top']} agree={r10['top_source_agrees']}")

    if not a.skip_e2e:
        t = time.time()
        r11 = exp.e11_estimands(include_e2e=True)
        write_artefact(f"e11_estimands_{a.dataset}.json", r11)
        print(f"E11 estimands ({time.time()-t:.0f}s): "
              + ", ".join(f"{k}={v['kendall_tau']:+.2f}"
                          for k, v in r11["agreement"].items()))

        t = time.time()
        r12 = exp.e12_retirement()
        write_artefact(f"e12_retirement_{a.dataset}.json", r12)
        print(f"E12 retirement ({time.time()-t:.0f}s): "
              f"shapley tau={r12['kendall_tau_shapley_vs_truth']:+.2f} "
              f"loo tau={r12['kendall_tau_loo_vs_truth']:+.2f} "
              f"cheapest true={r12['cheapest_to_retire_true']}")
    print("done")
