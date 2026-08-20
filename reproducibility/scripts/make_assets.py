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
    ap.add_argument("--no-publish", action="store_true",
                    help="generate into artefacts/ but do not copy into "
                         "paper/figures/")
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
                         "run experiments/run_study.py first")
    if a.include_failed:
        print("  WARNING: --include-failed set; these assets are DIAGNOSTIC "
              "and must not be used in the manuscript.")

    out = generate_all_assets(results, read_artefact("dataset_stats.json"))
    for k, v in out["figures"].items():
        print(f"  {k}: {v}")
    print(f"  tables -> {ARTEFACTS / 'tables'}")

    # Publish into paper/figures/ as Fig<N>.png, which is what sn-article.tex
    # \includegraphics actually reads.
    #
    # This copy used to be manual, and it silently rotted: the figures in
    # paper/ were eleven days older than the artefacts, so Figure 6 printed a
    # fusion comparison from the legacy candidate rule while the prose beside
    # it quoted the regenerated numbers -- including one that had changed
    # SIGN. A reviewer comparing the two would have found the figure
    # contradicting the text. Copying here makes the two impossible to
    # separate, and `--no-publish` exists for genuine diagnostic runs.
    if a.include_failed:
        print("  [not published] --include-failed assets are diagnostic; "
              "paper/figures/ left untouched")
    elif a.no_publish:
        print("  [not published] --no-publish set")
    else:
        import re
        import shutil

        dest = Path(__file__).resolve().parents[1] / "paper" / "figures"
        # Only publish where a manuscript actually exists. The standalone
        # reproducibility release ships the code and artefacts without paper/,
        # and creating an empty paper/figures/ there is confusing clutter that
        # implies a manuscript is present when none is.
        if not dest.parent.exists():
            print("  [not published] no paper/ directory here; "
                  "figures remain in artefacts/figures/")
        else:
            dest.mkdir(parents=True, exist_ok=True)
            for k, v in sorted(out["figures"].items()):
                n = re.fullmatch(r"F(\d+)", k)
                if not n:
                    continue
                target = dest / f"Fig{n.group(1)}.png"
                shutil.copyfile(v, target)
                print(f"  published {k} -> paper/figures/{target.name}")
