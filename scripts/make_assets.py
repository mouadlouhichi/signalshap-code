#!/usr/bin/env python3
"""Build F1-F7 and T1-T8 from artefacts/ JSON only (spec §13).

Corpora whose candidate-recall gate failed are EXCLUDED. Such a run still
writes a complete artefact, so globbing results_*.json would place
unreportable numbers in the same table as reportable ones (spec §2.2) --
the failure mode that put synthetic and real runs in T5 together.
Pass --include-failed only for diagnostics, never for the manuscript.
"""
import argparse, sys, warnings
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
warnings.filterwarnings("ignore")

from signalshap.config import ARTEFACTS, admissible, read_artefact
from signalshap.plots.assets import generate_all_assets

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-failed", action="store_true",
                    help="DIAGNOSTIC ONLY: include corpora that failed the "
                         "recall gate. Never use for submission assets.")
    a = ap.parse_args()

    results, skipped, rung2 = {}, [], []
    for p in sorted(ARTEFACTS.glob("results_*.json")):
        name = p.stem.replace("results_", "")
        blob = read_artefact(p.name)
        e0a = blob.get("e0a_candidates") or {}
        # Live config, not the artefact snapshot -- see signalshap.config.admissible.
        ok, restriction = admissible(name, e0a)
        if not ok and not a.include_failed:
            skipped.append((name, e0a.get("candidate_recall", float("nan"))))
            continue
        if restriction:
            rung2.append((name, e0a["candidate_recall"]))
        blob["_reporting_restriction"] = restriction
        results[name] = blob

    for name, recall in skipped:
        print(f"  [skipped] {name}: recall gate FAILED ({recall:.3f}), no "
              f"rung-2 exemption declared, not reportable under spec 2.2")
    for name, recall in rung2:
        print(f"  [rung 2] {name}: recall {recall:.3f} below gate, exemption "
              f"declared; RELATIVE contrasts only, excluded from absolute NDCG")
    if not results:
        raise SystemExit("no usable artefacts/results_*.json -- "
                         "run scripts/run_study.py first")
    if a.include_failed:
        print("  WARNING: --include-failed set; these assets are DIAGNOSTIC "
              "and must not be used in the manuscript.")

    out = generate_all_assets(results, read_artefact("dataset_stats.json"))
    for k, v in out["figures"].items():
        print(f"  {k}: {v}")
    print(f"  tables -> {ARTEFACTS / 'tables'}")
