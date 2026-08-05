#!/usr/bin/env python3
"""Cross-check numbers hardcoded in paper.tex against artefacts/ JSON.

Prose inevitably carries a few inline figures that no \\input{} can supply.
Those drift silently every time the study is re-run, and a reviewer who spots
one stale number starts doubting all of them. This script re-derives the key
claims and reports any that no longer match.

Usage:  python scripts/check_paper_numbers.py [--strict]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from signalshap.config import admissible  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artefacts"
# The submission manuscript on the Springer template. The earlier working
# draft (paper.tex) was removed so there is exactly one source of truth.
PAPER = ROOT / "paper" / "sn-article.tex"
TOL = 5e-5


def results(include_failed: bool = False) -> dict:
    """Load result artefacts, EXCLUDING any whose recall gate failed.

    A run behind a failed gate still writes a complete, well-formed artefact
    (gowalla_ts reached 0.132 candidate recall against a 0.60 threshold and
    produced 1,192 lines of plausible JSON). Globbing results_*.json therefore
    silently mixes reportable and unreportable corpora into the same table --
    the same way stale synthetic runs contaminated T5 earlier. Spec §2.2 makes
    a failed gate non-reportable, so it is filtered here, at the single point
    every consumer goes through, rather than trusted to each caller.
    """
    out = {}
    for p in sorted(ART.glob("results_*.json")):
        blob = json.loads(p.read_text())
        name = p.stem.replace("results_", "")
        e0a = blob.get("e0a_candidates") or {}
        # Exemption is resolved from the LIVE config, not the artefact's own
        # `reportable` field: gowalla_ts ran before it was declared, so its
        # stale snapshot says false while policy now admits it.
        ok, restriction = admissible(name, e0a)
        if not ok and not include_failed:
            print(f"  [skipped] {p.name}: {restriction}", file=sys.stderr)
            continue
        if restriction:
            print(f"  [rung 2] {name}: recall {e0a['candidate_recall']:.3f} "
                  f"below gate, exemption declared; relative contrasts only",
                  file=sys.stderr)
        blob["_reporting_restriction"] = restriction
        out[p.stem.replace("results_", "")] = blob
    return out


def check() -> list[str]:
    if not PAPER.exists():
        return ["paper.tex not found"]
    tex, res, bad = PAPER.read_text(), results(), []
    if not res:
        return ["no artefacts/results_*.json"]

    # 1. density range quoted in the corpora box
    dens = {k: r["dataset_stats"]["density"] for k, r in res.items()}
    if len(dens) > 1:
        actual = max(dens.values()) / min(dens.values())
        for m in re.findall(r"\$(\d+)\\times\$ density range", tex):
            if abs(int(m) - actual) > 2:
                bad.append(f"density range: text says {m}x, artefacts give {actual:.0f}x")

    # 2. per-source LOO / Shapley for the reference corpus
    if "ml_1m" in res:
        e2 = res["ml_1m"]["e2_loo_vs_shapley"]
        for g in ("cf", "ct", "pop", "rec", "seq"):
            for label, val in (("LOO", e2["loo"][g]), ("Shapley", e2["shapley"][g])):
                lit = f"{abs(val):.5f}"
                if lit in tex.replace("$", "").replace("+", "").replace("-", ""):
                    continue
                rounded = f"{abs(val):.4f}"
                if rounded in tex or lit in tex:
                    continue
                # only flag values the paper is likely to quote inline
                if abs(val) > 1e-3 and g in ("cf", "seq"):
                    bad.append(f"ml_1m {label}({g})={val:+.5f} not found in prose")

    # 3. fusion headline
    if "ml_1m" in res:
        e4 = res["ml_1m"]["e4_signalshap_fuse"]
        fc = e4["full_catalog"]
        for name, key in (("signalshap_fuse", "fuse"), ("global", "global")):
            v = f"{fc[name]['ndcg_at_10']:.5f}"
            if v not in tex:
                bad.append(f"{key} NDCG {v} not found in prose")
        p = e4["holm_bonferroni"]["corrected"]["global"]
        if f"{p:.2f}" not in tex:
            bad.append(f"fusion-vs-global Holm p={p:.2f} not found in prose")

    # 4. C4 heterogeneity counts
    if "ml_1m" in res:
        h = res["ml_1m"]["e3_segments"]["heterogeneity_summary"]
        n, m = h["n_significant_uncorrected"], h["n_tests"]
        # Accept plain, slashed, and math-delimited forms: "7 of 30",
        # "7/30", and Springer-style "$7$ of $30$".
        flat = tex.replace("$", "")
        if not any(f in flat for f in (f"{n} of {m}", f"{n}/{m}", f"{n} of the {m}")):
            bad.append(f"C4 heterogeneity '{n} of {m}' not found in prose")

    # 5. monotonicity violations, wherever the paper states them
    #
    # The paper claimed 26/80 for MovieLens while the artefact said 16/80, in
    # two places, and no check caught it: the fraction never appeared in any
    # rule above. Anything of the form "n/80" is now matched against the
    # measured count, in the preconditions table AND in the prose that reasons
    # from it -- Property 2's applicability turns on this number.
    for name, r in res.items():
        m = r.get("e0b_monotonicity") or {}
        if not m:
            continue
        v, pairs = m["violations"], m["pairs_checked"]
        if name != "ml_1m":
            continue    # other corpora legitimately differ; only ml_1m is quoted
        # Scope to lines that actually concern MovieLens: the preconditions
        # table row and any prose naming the corpus. A bare "n/80" search also
        # matches the Yelp2018 (0/80) and Gowalla (10/80) rows, which are
        # correct as they stand.
        for line in tex.splitlines():
            if "MovieLens" not in line:
                continue
            for q in re.findall(rf"\$?(\d+)\s*/\s*{pairs}\$?", line):
                if int(q) != v:
                    bad.append(f"monotonicity: paper says {q}/{pairs} for "
                               f"MovieLens, artefact gives {v}/{pairs}")

    # 6. candidate recall quoted per corpus
    for name, r in res.items():
        rec = r["e0a_candidates"]["candidate_recall"]
        if name == "ml_1m" and f"{rec:.3f}" not in tex:
            bad.append(f"ml_1m candidate recall {rec:.3f} not found in prose")

    # 7. efficiency bound must not understate the artefact
    worst = max(r["e1_source_share"]["efficiency"]["abs_error"] for r in res.values())
    for mant, exp in re.findall(r"([\d.]+)\s*\\times\s*10\^\{-(\d+)\}", tex):
        b = float(mant) * 10 ** (-int(exp))
        if 1e-25 < b < 1e-10 and worst > b * 1.5:
            bad.append(f"efficiency bound {b:.1e} understates artefact {worst:.1e}")
    return bad


if __name__ == "__main__":
    problems = check()
    if problems:
        print("PAPER/ARTEFACT MISMATCHES:")
        for p in problems:
            print("  -", p)
        sys.exit(1 if "--strict" in sys.argv else 0)
    print("paper.tex numbers agree with artefacts/")
