#!/usr/bin/env python3
"""Generate notebooks/SignalShap_Round8_Runs.ipynb.

The notebook is GENERATED rather than hand-edited, for the same reason the
tables are: a hand-maintained .ipynb drifts from the scripts it calls, and the
diff of a hand-edited notebook is unreadable, so drift is invisible in review.
Regenerate with:

    python scripts/make_round8_notebook.py

`tests/test_round8_notebook.py` asserts the checked-in notebook matches what
this script produces, so an edit made in Jupyter and committed without
regenerating is caught by CI.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "SignalShap_Round8_Runs.ipynb"

BUDGET = 24


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {},
            "source": text.strip("\n").splitlines(keepends=True)}


def code(text: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": text.strip("\n").splitlines(keepends=True)}


CELLS = [
    md("""
# SignalShap - Review Round 8, remaining runs

Everything the round-8 review still needs, in cost order. All the code and
tests are already on `main`; this notebook only *runs* it on the real corpora.

**Read this first.** Do not use `SignalShap_M4_FullStudy.ipynb` for these.
That notebook runs `yelp2018`, `gowalla` and `amazon_book_lgcn`, which are the
untimestamped LightGCN splits and **not** the three corpora this paper
reports. The paper's corpora are `ml_1m`, `amazon_video_games` and
`gowalla_ts`. Running the M4 notebook will produce artefacts, and they will be
the wrong ones.

| Stage | Review item | Cost | Artefact |
|---|---|---|---|
| 1 | 3 - blocked retirement | minutes | `global_timeblock.json` |
| 2 | 10 - neutral pools, ML-1M | minutes | `pool_sensitivity.json` |
| 3 | 7 - ten-seed refreshed history | ~1 h | `protocol_sensitivity.json` |
| 4 | 10 - neutral pools, Amazon | ~10 min | `pool_sensitivity.json` |
| 5-7 | 6 - regenerate legacy diagnostics | hours | `results_*.json` |
| 8 | 10 - neutral pools, Gowalla | longest | `pool_sensitivity.json` |
| 9 | manifest refresh | seconds | `MANIFEST.json` |

Every stage is independent and resumable. If one fails, the rest still run and
the ones that succeeded stay on disk.

If you would rather not babysit a notebook, the identical sequence is one
shell command:

```bash
bash scripts/run_round8_remaining.sh 24
```
"""),

    md("## 1 - Environment\n\nNo `%pip install` here: use the environment the "
       "repository declares, so the artefacts record the versions the paper "
       "was produced with."),

    code("""
import os, sys, platform, subprocess, time, json
from pathlib import Path

REPO = Path.home() / "signalshap-code"        # <-- edit if you cloned elsewhere
assert REPO.exists(), f"repo not found at {REPO}"
os.chdir(REPO)
sys.path.insert(0, str(REPO / "src"))

# A missing corpus must be a hard error, never a silent synthetic fallback.
os.environ["SIGNALSHAP_STRICT_DATA"] = "1"

print("python :", platform.python_version(), "|", platform.machine())
try:
    ram = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"]).strip()) / 1e9
    print(f"RAM    : {ram:.0f} GB")
except Exception:
    ram = None
    print("RAM    : unknown (not macOS)")

import numpy as np, pandas as pd, scipy, sklearn
print("numpy", np.__version__, "| pandas", pd.__version__,
      "| scipy", scipy.__version__, "| sklearn", sklearn.__version__)
print("cwd    :", Path.cwd())
"""),

    md("""
### The one knob

`BUDGET_GB` caps how much RAM the five dense score matrices may use. The user
count per corpus is *derived* from it, not guessed, so a corpus downsizes
instead of being OOM-killed.

**Leave it at 24 unless you have a reason.** The reported corpus shapes
(6,038 x 3,533 / 7,120 x 3,516 / 8,865 x 82,134) were produced at 24 GB, and
`check_paper_shape` will refuse to overwrite the paper's artefacts if a
different budget yields a different shape. That guard is the point: a
different budget silently means a different Gowalla.
"""),

    code(f"""
BUDGET_GB = {BUDGET}
CORPORA = ["ml_1m", "amazon_video_games", "gowalla_ts"]

from signalshap.memory import PAPER_CORPUS_SHAPE, default_budget_gb, free_gb
print(f"budget      : {{default_budget_gb(BUDGET_GB):.1f}} GB "
      f"(free: {{free_gb():.1f}} GB)")
print("paper shapes:")
for k, (u, i) in PAPER_CORPUS_SHAPE.items():
    print(f"  {{k:20s}} {{u:6,}} users x {{i:7,}} items")
"""),

    md("""
### Corpora

`ml-1m` is fetched from GroupLens rather than vendored: its README forbids
redistribution. Gowalla check-ins come from SNAP. Both scripts are idempotent,
so re-running costs nothing if the data is already there.
"""),

    code("""
need = [p for p in ["data/raw/ml-1m/ratings.dat",
                    "data/raw/gowalla_ts",
                    "data/raw/amazon_video_games"]
        if not Path(p).exists()]
print("missing:", need or "nothing, all corpora present")

if need:
    for script in ("scripts/fetch_benchmarks.sh", "scripts/fetch_timestamped.sh"):
        print(f"\\n$ bash {script}")
        r = subprocess.run(["bash", script], capture_output=True, text=True)
        print((r.stdout or "")[-2000:])
        if r.returncode != 0:
            print("STDERR:", (r.stderr or "")[-1000:])
"""),

    md("""
### A helper that does not hide failures

Long stages fail for boring reasons: a missing corpus, a full disk, a typo.
This runner streams output live, records the exit status, and *keeps going*,
so one bad stage does not discard hours of successful work in the stages after
it. That is the same reason `run_round8_remaining.sh` does not use `set -e`.
"""),

    code("""
RESULTS = {}

def run(label, *args, allow_fail=True):
    \"\"\"Run one stage, stream its output, remember whether it worked.\"\"\"
    cmd = [sys.executable, *args]
    print("=" * 72)
    print(label)
    print("  $ " + " ".join(str(c) for c in cmd))
    print("=" * 72, flush=True)
    t0 = time.time()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, bufsize=1)
    for line in p.stdout:
        print(line, end="")
    p.wait()
    dt = time.time() - t0
    ok = p.returncode == 0
    RESULTS[label] = {"ok": ok, "seconds": round(dt, 1), "returncode": p.returncode}
    print(f"\\n--- {'ok' if ok else 'FAILED'} ({label}) in {dt:.0f}s\\n", flush=True)
    if not ok and not allow_fail:
        raise RuntimeError(label)
    return ok
"""),

    md("""
## 2 - Stage 1: blocked retirement (review item 3)

The main split is leave-last-out *within* each user, which is standard but not
globally causal: up to 44% of pooled training events postdate the median test
event. The paper's central operational claim is about **retirement**, so that
claim in particular needs checking under a split where nothing is fitted on
the future.

Expect coverage to collapse (only ~8.7% of users survive a global cutoff) and
the blocked corpus to fail the paper's own recall gate at 0.464. That is a
known and disclosed property, not a bug: read this as a stress test on a
different, smaller population, not as a cleaner measurement of the same one.
"""),

    code(f"""
run("item 3: blocked retirement (ml_1m)",
    "scripts/run_global_timeblock.py", "--corpora", "ml_1m",
    "--budget-gb", "{BUDGET}", "--retirement")
"""),

    code("""
from signalshap.config import read_artefact

tb = read_artefact("global_timeblock.json").get("ml_1m", {})
print(f"users retained : {tb.get('users_retained'):,} of {tb.get('users_original'):,} "
      f"({tb.get('user_coverage', 0):.1%})")
print(f"candidate recall: {tb.get('candidate_recall', 0):.3f}  (gate 0.60)")
print(f"train events after any test event: {tb.get('train_events_after_any_test_event')}"
      "   <- must be 0, that is the whole point")
print(f"ordering        : {' > '.join(tb.get('ordering', []))}")
print(f"material flips  : {tb.get('material_flips') or 'none'}")

r = tb.get("retirement")
if r:
    print("\\nRETIREMENT UNDER THE BLOCKED SPLIT")
    print(f"  tau LOO vs truth     : {r['kendall_tau_loo_vs_truth']:+.2f}")
    print(f"  tau Shapley vs truth : {r['kendall_tau_shapley_vs_truth']:+.2f}")
    print(f"  LOO advantage        : {r['tau_advantage_loo_minus_shapley']:+.2f}")
    print(f"  cheapest truly       : {r['cheapest_to_retire_true']}")
    print(f"  LOO picks            : {r['cheapest_by_loo']} "
          f"({'correct' if r['loo_picks_correctly'] else 'WRONG'})")
    print(f"  Shapley picks        : {r['cheapest_by_shapley']} "
          f"({'correct' if r['shapley_picks_correctly'] else 'WRONG'})")
    print("\\nIf the LOO advantage is <= 0 here, that WEAKENS the paper's claim")
    print("and must be reported as such, not buried. Tell me either way.")
else:
    print("\\nno retirement block: was --retirement passed?")
"""),

    md("""
## 3 - Stage 2: neutral candidate pools (review item 10)

The candidate pool is coalition-independent, which is what the game requires,
but it is not *source*-independent: the five players build it, so it is
enriched for the items they rank highly. These runs rebuild the whole game on
pools that consult no source score at all.

Three rules. `popularity` is neutral for four players but correlated with
`pop`, which we state rather than gloss. `random` is strictly neutral, but
recall collapses to roughly N/|I|, so most users lose a retrievable target and
the game flattens; a null result there would be a null *game*, not pool
robustness. `random_oracle` restores the target while keeping the distractors
source-blind, and it is the informative one.

**Compare orderings and signs, not levels.** Each rule gives a different
`|C_u|`, hence a different baseline and recall ceiling.
"""),

    code(f"""
run("item 10: neutral pools (ml_1m)",
    "scripts/run_pool_sensitivity.py", "--corpora", "ml_1m",
    "--budget-gb", "{BUDGET}")
"""),

    code("""
def show_pools(corpus):
    # read_artefact raises if the file is absent, which is the normal state
    # before the stage above has ever succeeded. Report that, do not traceback.
    p = Path("artefacts/pool_sensitivity.json")
    if not p.exists():
        print(f"{corpus}: pool_sensitivity.json not written yet"); return
    blob = json.loads(p.read_text()).get(corpus)
    if not blob:
        print(f"{corpus}: not run yet"); return
    rows = []
    for label, p in blob["pools"].items():
        ag = blob["agreement"].get(label, {})
        rows.append({
            "pool": label,
            "recall": round(p["candidate_recall"], 3),
            "v(G)": round(p["v_grand"], 5),
            "ordering": " > ".join(p["ordering"]),
            "flips": ",".join(p["material_flips"]) or "-",
            "tau vs union": (None if label == "union_of_top_n"
                             else round(ag.get("kendall_tau_vs_union") or 0, 2)),
            "same top": ("-" if label == "union_of_top_n"
                         else ag.get("same_top_source")),
        })
    display(pd.DataFrame(rows))

show_pools("ml_1m")
"""),

    md("""
## 4 - Stage 3: ten-seed refreshed history (review item 7)

The frozen-versus-refreshed protocol contrast was seed 42 only, which cannot
separate a protocol effect from the game's own run-to-run noise. This runs the
paired contrast across the same ten seeds as the main results and reports a
percentile-bootstrap interval plus a per-source sign count.

This is the slow one on this page: ten seeds, two full games each. Roughly an
hour on MovieLens.
"""),

    code(f"""
run("item 7: ten-seed refreshed history (ml_1m)",
    "scripts/run_protocol_sensitivity.py", "--corpora", "ml_1m",
    "--budget-gb", "{BUDGET}",
    "--seeds", *[str(s) for s in range(42, 52)])
"""),

    code("""
ps = read_artefact("protocol_sensitivity.json").get("ml_1m", {}).get("temporal_seeds")
if not ps:
    print("not run yet (needs --seeds)")
else:
    rc = ps["relative_change_v_grand"]
    print(f"seeds                  : {ps['n_seeds']}")
    print(f"v(G) frozen            : {ps['v_grand_frozen']['mean']:.5f} "
          f"(sd {ps['v_grand_frozen']['sd']:.5f})")
    print(f"v(G) refreshed         : {ps['v_grand_refreshed']['mean']:.5f} "
          f"(sd {ps['v_grand_refreshed']['sd']:.5f})")
    print(f"relative change        : {rc['mean']:+.1%} "
          f"[{rc['ci']['lo']:+.1%}, {rc['ci']['hi']:+.1%}]  "
          f"({rc['n_positive']}/{ps['n_seeds']} seeds positive)")
    print(f"Kendall tau mean       : {ps['kendall_tau']['mean']:.3f}  "
          f"({ps['kendall_tau']['n_unit']}/{ps['n_seeds']} seeds preserve the ordering)")
    print(f"top source changes on  : {ps['n_seeds_top_source_changes']}/{ps['n_seeds']} seeds")
    display(pd.DataFrame([
        {"source": g,
         "mean delta": round(d["mean"], 6),
         "ci lo": round(d["ci"]["lo"], 6),
         "ci hi": round(d["ci"]["hi"], 6),
         "+/-": f"{d['n_positive']}/{d['n_negative']}",
         "sign stable": d["sign_stable"]}
        for g, d in ps["per_source_delta"].items()]))
"""),

    md("## 5 - Stage 4: neutral pools on Amazon-VG"),

    code(f"""
run("item 10: neutral pools (amazon_video_games)",
    "scripts/run_pool_sensitivity.py", "--corpora", "amazon_video_games",
    "--budget-gb", "{BUDGET}")
show_pools("amazon_video_games")
"""),

    md("""
## 6 - Stages 5-7: regenerate the legacy-rule diagnostics (review item 6)

Table 1's recall and monotonicity counts, the duplicate-injection test, the
segment profiles, the lambda and candidate-cap sweeps, the grand-pool
ablation and the estimand comparison were all produced under the *legacy*
candidate truncation key, before the source-symmetric rule became the method
of record. They are currently labelled as single-seed sensitivity analyses.
Re-running them under the final rule promotes them to confirmatory.

**One corpus per call.** `run_study.py` refuses a multi-corpus invocation when
the corpora need different user caps, because a single process-wide cap would
silently apply the smallest to all of them and substitute a different
MovieLens. That refusal is deliberate; do not work around it.

This is the expensive block. Gowalla alone can run for hours at 82,134 items.
"""),

    code(f"""
for corpus in CORPORA:
    run(f"item 6: regenerate diagnostics ({{corpus}})",
        "scripts/run_study.py", "--datasets", corpus,
        "--budget-gb", "{BUDGET}", "--seeds", "42", "43", "44")
"""),

    code("""
for corpus in CORPORA:
    p = Path(f"artefacts/results_{corpus}.json")
    if not p.exists():
        print(f"{corpus:20s} MISSING"); continue
    e0 = json.loads(p.read_text())["e0a_candidates"]
    print(f"{corpus:20s} rule={e0.get('candidate_rule')}  "
          f"recall={e0['candidate_recall']:.3f}  "
          f"{'PASS' if e0['gate_passes'] else 'below gate (rung 2)'}")
print("\\nrule should read symmetric_reciprocal_rank on all three once this finishes.")
"""),

    md("""
## 7 - Stage 8: neutral pools on Gowalla (optional, longest)

Four pool rules x 32 coalitions at `N_max = 11,623` over an 82,134-item
catalogue. Skip it if you are short on time: the ordering-invariance claim is
already supported by the two denser corpora, and Gowalla's absolute values are
diluted by half anyway (half its users have a test venue already in training,
so their payoff is identically zero in every coalition).
"""),

    code(f"""
RUN_GOWALLA_POOLS = True     # set False to skip

if RUN_GOWALLA_POOLS:
    run("item 10: neutral pools (gowalla_ts)",
        "scripts/run_pool_sensitivity.py", "--corpora", "gowalla_ts",
        "--budget-gb", "{BUDGET}")
    show_pools("gowalla_ts")
else:
    print("skipped")
"""),

    md("## 8 - Refresh the hashed manifest and verify"),

    code("""
run("manifest", "scripts/make_manifest.py")
"""),

    code("""
for checker in ("check_paper_numbers.py", "check_discover_ai.py", "check_latex.py"):
    print("=" * 72)
    r = subprocess.run([sys.executable, f"scripts/{checker}"],
                       capture_output=True, text=True)
    print(f"{checker}: exit {r.returncode}")
    print((r.stdout or "").strip()[-1500:])
    if r.stderr.strip():
        print("  stderr:", r.stderr.strip()[-600:])
"""),

    md("""
## 9 - Summary

Send me this table and the artefacts it names. If anything failed, send the
error too: a stage that fails for a boring reason is much cheaper to fix than
a stage that silently produced the wrong corpus.
"""),

    code("""
if not RESULTS:
    # An empty frame must not read as success: it means nothing ran at all,
    # which is a different situation from every stage passing.
    print("NO STAGES RAN. Did you execute the run(...) cells above?")
else:
    summary = pd.DataFrame([
        {"stage": k, "ok": v["ok"], "minutes": round(v["seconds"] / 60, 1),
         "exit": v["returncode"]}
        for k, v in RESULTS.items()])
    display(summary)

    failed = summary[~summary["ok"]]["stage"].tolist()
    print("ALL STAGES OK" if not failed else f"{len(failed)} FAILED: {failed}")
    print(f"total: {summary['minutes'].sum():.0f} min")

print("\\nartefacts touched by this notebook:")
for name in ("global_timeblock.json", "pool_sensitivity.json",
             "protocol_sensitivity.json", "results_ml_1m.json",
             "results_amazon_video_games.json", "results_gowalla_ts.json",
             "MANIFEST.json"):
    p = Path("artefacts") / name
    print(f"  {'OK  ' if p.exists() else 'MISS'} {name}"
          f"{'' if not p.exists() else f'  ({p.stat().st_size / 1024:.0f} KB)'}")
"""),

    md("""
### Committing

```bash
git add artefacts/ && git commit -m "round 8: runs from the M4" \\
  && git push origin arena/019fc2ce-signalshap-code
```

Then tell me it is pushed and I will fold the numbers into the manuscript,
including any that come out against the paper's framing.
"""),
]


def build() -> dict:
    # Stable, content-derived cell ids. nbformat >= 4.5 requires an id, and a
    # random one would make every regeneration a spurious diff.
    import hashlib

    cells = []
    for n, cell in enumerate(CELLS):
        c = dict(cell)
        body = "".join(c["source"])
        c["id"] = hashlib.blake2b(f"{n}:{body}".encode(),
                                  digest_size=8).hexdigest()
        cells.append(c)

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python",
                           "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=1) + "\n")
    nb = build()
    print(f"wrote {OUT.relative_to(ROOT)}: {len(nb['cells'])} cells "
          f"({sum(1 for c in nb['cells'] if c['cell_type'] == 'code')} code)")
