#!/usr/bin/env python3
"""Build F1-F7 and T1-T8 from artefacts/ JSON only (spec §13)."""
import sys, warnings
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
warnings.filterwarnings("ignore")

from signalshap.config import ARTEFACTS, read_artefact
from signalshap.plots.assets import generate_all_assets

if __name__ == "__main__":
    names = [p.stem.replace("results_", "")
             for p in sorted(ARTEFACTS.glob("results_*.json"))]
    if not names:
        raise SystemExit("no artefacts/results_*.json -- run scripts/run_study.py first")
    results = {n: read_artefact(f"results_{n}.json") for n in names}
    out = generate_all_assets(results, read_artefact("dataset_stats.json"))
    for k, v in out["figures"].items():
        print(f"  {k}: {v}")
    print(f"  tables -> {ARTEFACTS / 'tables'}")
