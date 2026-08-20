#!/usr/bin/env python3
"""Is an artefact from a valid run? Fast, dependency-free, safe to run anytime.

    python scripts/check_run_valid.py [corpus ...]

Checks the hard invariants -- properties the artefact must satisfy on its own,
independent of anything the paper says:

  * efficiency (Property 1): sum_g phi_g == v(G), since v(empty) == 0
  * v(empty) == 0 exactly (Property 3)
  * no structurally degenerate player
  * the candidate-recall gate, or a declared rung-2 exemption

Exists because the obvious one-liner

    python -c "...['v_empty']..."

raises KeyError on an artefact written before v_empty was recorded, which looks
like a broken tool rather than what it is: proof the run predates the fix.
A check that crashes on the case it is meant to detect is not a check.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "artefacts"

#: v_empty was introduced with the Property 1 fix. Its absence dates the run.
FIX_COMMIT = "9d87120"


def check(corpus: str) -> tuple[bool, list[str]]:
    p = ART / f"results_{corpus}.json"
    if not p.exists():
        return False, [f"{corpus}: no artefact yet ({p.name})"]

    blob = json.loads(p.read_text())
    e1 = blob.get("e1_source_share") or {}
    e0 = blob.get("e0a_candidates") or {}
    notes: list[str] = []
    ok = True

    eff = e1.get("efficiency") or {}
    if not eff:
        ok = False
        notes.append("no efficiency block")
    elif not eff.get("passes", False):
        ok = False
        notes.append(f"FAILS Property 1: |sum phi - v(G)| = "
                     f"{eff.get('abs_error', float('nan')):.2e} (want < 1e-9)")
    else:
        notes.append(f"efficiency {eff['abs_error']:.1e} OK")

    if "v_empty" not in e1:
        ok = False
        notes.append(f"v_empty ABSENT -- this run predates commit {FIX_COMMIT} "
                     f"and is invalid; re-run it")
    elif abs(e1["v_empty"]) > 1e-12:
        ok = False
        notes.append(f"FAILS Property 3: v(empty) = {e1['v_empty']:.2e}, must be 0")
    else:
        notes.append("v(empty) = 0 OK")

    dead = (blob.get("player_audit") or {}).get("degenerate_players")
    if dead:
        ok = False
        notes.append(f"degenerate players {dead}: structurally zero, not evidence")

    recall, gate = e0.get("candidate_recall"), e0.get("recall_gate", 0.6)
    if recall is not None:
        if e0.get("gate_passes"):
            notes.append(f"recall {recall:.3f} passes gate")
        elif e0.get("ceiling_exempt") or e0.get("reportable"):
            notes.append(f"recall {recall:.3f} below gate, rung-2 exemption declared")
        else:
            ok = False
            notes.append(f"recall {recall:.3f} below gate, NO exemption declared")

    return ok, notes


def main() -> int:
    corpora = sys.argv[1:] or ["ml_1m", "amazon_video_games", "gowalla_ts"]
    try:
        gen = json.loads((ART / "study_manifest.json").read_text())["generated_at"]
        age = datetime.now(timezone.utc) - datetime.fromisoformat(gen)
        print(f"manifest generated {gen}  ({age.total_seconds()/3600:.1f} h ago)\n")
    except Exception:                                    # noqa: BLE001
        pass

    all_ok = True
    for c in corpora:
        ok, notes = check(c)
        all_ok &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {c}")
        for n in notes:
            print(f"        {n}")
    print("\n" + ("all runs valid" if all_ok else
                  "INVALID RUNS PRESENT -- regenerate before using these numbers"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
