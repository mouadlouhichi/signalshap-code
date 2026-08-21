#!/usr/bin/env python3
"""Generate notebooks/SignalShap_Semivalues_Gowalla.ipynb.

The one run still worth doing before submission: semivalues on Gowalla, which
closes review item H14/#4 completely. Generated rather than hand-written for
the same reason as the round-8 notebook: a hand-maintained .ipynb drifts from
the scripts it calls and its diff hides the drift.

    python scripts/make_semivalues_notebook.py

`tests/test_semivalues_notebook.py` asserts the committed notebook matches
what this produces.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "SignalShap_Semivalues_Gowalla.ipynb"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {},
            "source": text.strip("\n").splitlines(keepends=True)}


def code(text: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": text.strip("\n").splitlines(keepends=True)}


CELLS = [
    md("""
# Semivalues on Gowalla

The one run still worth doing before submission. It closes review item
H14 / #4, which asked why Banzhaf and the binomial semivalues are reported on
MovieLens only.

**Why this matters more than it looks.** While auditing the review we found
that the Amazon-VG artefact already existed and *disagrees* with Shapley:
Kendall tau = 0.60, and the two pick a different leading source (Shapley says
`cf`, Banzhaf says `seq`). That was an unreported negative result in our own
artefacts, and it is now in the manuscript. So Gowalla is no longer a
formality: it is the tiebreaker between "MovieLens was the exception" and
"MovieLens was the lucky case".

Whatever it returns, we report it. If Gowalla agrees with Shapley the claim
becomes "robust on two of three corpora, with Amazon-VG the exception"; if it
disagrees the claim becomes "not robust in general, and a reported ordering
must state which value produced it". Both are publishable; only silence is not.

| | |
|---|---|
| Cost | one 32-coalition game on 8,865 x 82,134. Tens of minutes |
| Writes | `artefacts/e10_values_gowalla_ts.json` |
| Needs | the Gowalla corpus under `data/raw/`, and about 15 GB free RAM |
"""),

    md("## 1 - Environment and repo"),

    code("""
import os, sys, platform, subprocess, time, json
from pathlib import Path


def _find_repo():
    \"\"\"Locate the repo by CONTENTS, not by a guessed path.

    A stale empty directory at a guessed path once passed an `.exists()`
    check, the notebook chdir'd into it, and every stage died instantly.
    \"\"\"
    MARKERS = ("scripts/run_revision_experiments.py",
               "src/signalshap/config.py", "configs/frozen.yaml")

    def ok(p):
        return p and all((p / m).exists() for m in MARKERS)

    here = Path.cwd().resolve()
    for cand in (here, *here.parents):
        if ok(cand):
            return cand
    for cand in (Path.home() / "signalshap-code", Path.home() / "signalshap"):
        if ok(cand):
            return cand
    return None


REPO = _find_repo()
if REPO is None:
    raise SystemExit(
        "Could not locate the repo. Set it explicitly and re-run this cell:\\n"
        "    REPO = Path('/full/path/to/signalshap-code')\\n"
        "    os.chdir(REPO); sys.path.insert(0, str(REPO/'src'))")

os.chdir(REPO)
sys.path.insert(0, str(REPO / "src"))

# A missing corpus must be a hard error, never a silent synthetic fallback.
os.environ["SIGNALSHAP_STRICT_DATA"] = "1"

_venv = REPO / ".venv" / "bin" / "python"
if _venv.exists() and Path(sys.executable).resolve() != _venv.resolve():
    print(f"WARNING: kernel is {sys.executable}")
    print(f"         repo venv is {_venv}")
    print("         The run uses the KERNEL. Select the .venv kernel if that "
          "is not what you want.\\n")

print("repo   :", REPO)
print("python :", platform.python_version(), "|", platform.machine())
import numpy as np, scipy, sklearn
print("numpy", np.__version__, "| scipy", scipy.__version__,
      "| sklearn", sklearn.__version__)
"""),

    md("""
## 2 - Preflight

Three things are checked before committing to a long run, because each has
actually gone wrong before: a missing corpus that silently becomes synthetic
data, a memory budget that gets ignored, and an existing artefact that would
be overwritten without anyone noticing.
"""),

    code("""
# 2a. Is the Gowalla corpus actually present?
from signalshap.data.loaders import LOADERS, _register_timestamped
_register_timestamped()

candidates = [REPO / "data" / "raw" / "gowalla_ts", REPO / "data" / "raw" / "gowalla"]
present = [p for p in candidates if p.exists()]
print("gowalla corpus:", present[0] if present else "MISSING")
if not present:
    print("  fetch it first:  bash scripts/fetch_timestamped.sh")

# 2b. Will it fit? Five dense float32 score matrices at the reported shape.
users, items = 8865, 82134
gb = 5 * users * items * 4 / 1e9
print(f"score matrices at {users:,} x {items:,}: {gb:.1f} GB before the game allocates")
try:
    vm = subprocess.check_output(["vm_stat"]).decode()
    page = 4096
    free = sum(int(l.split()[-1].rstrip('.')) for l in vm.splitlines()
               if l.startswith(("Pages free", "Pages inactive"))) * page / 1e9
    print(f"free RAM: {free:.1f} GB   ->", "OK" if free > gb * 1.5 else "TIGHT, close other apps")
except Exception:
    print("free RAM: unknown (not macOS)")

# 2c. Would we overwrite an existing artefact?
target = REPO / "artefacts" / "e10_values_gowalla_ts.json"
print("target artefact:", "EXISTS, will be overwritten" if target.exists() else "absent, will be created")
"""),

    md("""
## 3 - The run

Two flags matter and both are deliberate.

`--max-users 8865` is **required**. Unlike `run_study.py`, this script has no
`--budget-gb` and performs no memory sizing, so a bare call would load the
full 52,985 x 121,866 corpus and be OOM-killed exactly as `run_study.py` was.
The value matches the corpus shape the manuscript reports.

`--skip-e2e` skips E11 and E12, which rebuild candidate sets for each of the
32 coalitions. That is 32 retrieval passes over an 82,134-item catalogue and
is not needed here: semivalues are computed from the same 32 coalition values
that E10 already has.
"""),

    code("""
cmd = [sys.executable, "scripts/run_revision_experiments.py",
       "--dataset", "gowalla_ts", "--max-users", "8865", "--skip-e2e"]
print("$ " + " ".join(cmd), flush=True)

t0 = time.time()
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                     text=True, bufsize=1)
for line in p.stdout:
    print(line, end="")
p.wait()
print(f"\\n--- exit {p.returncode} in {(time.time()-t0)/60:.1f} min")
if p.returncode != 0:
    print("FAILED. If the message mentions a synthetic fallback, the corpus is "
          "missing: run  bash scripts/fetch_timestamped.sh")
"""),

    md("""
## 4 - Read the result

The question is whether the *ordering* is robust to the choice of cooperative
value, not whether the totals match. Only Shapley sums to `v(G)`; the others
rank rather than divide, so their magnitudes are not comparable.
"""),

    code("""
from scipy.stats import kendalltau

order = ["cf", "ct", "pop", "rec", "seq"]
path = Path("artefacts/e10_values_gowalla_ts.json")

if not path.exists():
    print("artefact not written; the run above did not finish")
else:
    d = json.loads(path.read_text())
    shap = d["shapley"]
    print("Gowalla, seed 42\\n")
    print(f"{'value':28s} {'top':>5s}  {'tau vs Shapley':>15s}")
    print("-" * 52)
    print(f"{'Shapley':28s} {max(shap, key=shap.get):>5s}  {'1.00':>15s}")
    for key, label in (("banzhaf", "Banzhaf"),
                       ("semivalue_binomial_q025", "binomial semivalue q=0.25"),
                       ("semivalue_binomial_q075", "binomial semivalue q=0.75")):
        if key not in d:
            continue
        v = d[key]
        t = kendalltau([shap[g] for g in order], [v[g] for g in order]).correlation
        print(f"{label:28s} {max(v, key=v.get):>5s}  {t:>15.2f}")

    print("\\nper-source values")
    print(f"{'src':5s} " + "".join(f"{k:>12s}" for k in
          ("shapley", "banzhaf", "q=0.25", "q=0.75")))
    for g in order:
        row = [shap[g], d.get("banzhaf", {}).get(g),
               d.get("semivalue_binomial_q025", {}).get(g),
               d.get("semivalue_binomial_q075", {}).get(g)]
        print(f"{g:5s} " + "".join(f"{x:+12.5f}" if x is not None else f"{'-':>12s}"
                                   for x in row))

    # The implementation check that must always hold.
    diff = d.get("size_uniform_equals_shapley_max_abs_diff")
    if diff is not None:
        print(f"\\nsize-uniform semivalue equals Shapley to {diff:.2e} "
              f"({'OK' if diff < 1e-12 else 'INVESTIGATE'})")
"""),

    md("""
## 5 - What this means for the manuscript

Compare against the two corpora already reported. The manuscript currently
says the ordering is robust to the choice of semivalue on MovieLens-1M but
**not** on Amazon-VG, and that Gowalla was not computed.
"""),

    code("""
rows = []
for corpus, fname in (("MovieLens-1M", "e10_values_ml_1m_symmetric_candidates.json"),
                      ("Amazon-VG", "e10_values_amazon_video_games.json"),
                      ("Gowalla", "e10_values_gowalla_ts.json")):
    p = Path("artefacts") / fname
    if not p.exists():
        rows.append((corpus, "not run", "-", "-")); continue
    d = json.loads(p.read_text())
    shap, banz = d["shapley"], d["banzhaf"]
    t = kendalltau([shap[g] for g in order], [banz[g] for g in order]).correlation
    rows.append((corpus, f"{t:+.2f}", max(shap, key=shap.get), max(banz, key=banz.get)))

print(f"{'corpus':14s} {'tau S-vs-B':>11s} {'Shapley top':>12s} {'Banzhaf top':>12s}  verdict")
print("-" * 68)
for c, t, st, bt in rows:
    verdict = ("-" if t in ("not run",)
               else "ordering robust" if st == bt else "DISAGREES on top source")
    print(f"{c:14s} {t:>11s} {st:>12s} {bt:>12s}  {verdict}")

print(\"\"\"
How to read this:
  all three agree      -> Amazon-VG is the exception; say so and keep the claim
                          narrow, since one of three still disagrees.
  Gowalla disagrees    -> the ordering is NOT robust to the choice of value in
                          general. That is a stronger and more useful finding
                          than robustness, and it must be reported as such.
Either way the sentence in Section 'Alternative values' needs updating, and
the wording 'We did not compute these values on Gowalla' must be removed.\"\"\")
"""),

    md("""
## 6 - Refresh the manifest and verify

The artefact manifest records a SHA-256 per file with the commit and
environment that produced it, so it must be regenerated whenever an artefact
changes. The number checker then confirms the manuscript still agrees with
`artefacts/`.
"""),

    code("""
for step in (["scripts/make_manifest.py"], ["scripts/check_paper_numbers.py"]):
    print("$", " ".join(step))
    r = subprocess.run([sys.executable, *step], capture_output=True, text=True)
    print((r.stdout or r.stderr).strip()[-800:])
    print()
"""),

    md("""
## 7 - Send me

1. The table from section 5.
2. `artefacts/e10_values_gowalla_ts.json`.

I will fold the numbers into the manuscript, including a result that
contradicts the current wording if that is what comes back.

```bash
git add artefacts/ && git commit -m "gowalla semivalues" \\
  && git push origin arena/019fc2ce-signalshap-code
```
"""),
]


def build() -> dict:
    cells = []
    for n, cell in enumerate(CELLS):
        c = dict(cell)
        body = "".join(c["source"])
        c["id"] = hashlib.blake2b(f"{n}:{body}".encode(), digest_size=8).hexdigest()
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
