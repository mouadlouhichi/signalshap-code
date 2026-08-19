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
        # Prefer the ten-seed artefact, which is what the tables now quote.
        # results_*.json predates the symmetric candidate rule, so comparing
        # the paper against it flagged a phantom drift in Shapley(seq).
        e2 = res["ml_1m"]["e2_loo_vs_shapley"]
        _sc = ART / "final_seed_ci.json"
        seed_ci = json.loads(_sc.read_text()) if _sc.exists() else None
        if seed_ci and isinstance(seed_ci.get("ml_1m"), dict):
            blk = seed_ci["ml_1m"]
            if "ci" in blk and "loo_ci" in blk:
                e2 = {"shapley": {g: blk["ci"][g]["mean"] for g in blk["ci"]},
                      "loo": {g: blk["loo_ci"][g]["mean"] for g in blk["loo_ci"]}}
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
        # The table now reports "material / raw" per corpus. Check BOTH against
        # the artefact, per corpus row, rather than pattern-matching "n/80":
        # the raw count is not reproducible across machines (17 here, 23 on
        # another box for the same data), so quoting it alone would be a
        # promise the artefact cannot keep.
        det = m.get("detail", [])
        material = m.get(
            "violations_material",
            sum(1 for x in det if abs(x["delta"]) > m.get("material_threshold", 1e-3)),
        )
        if len(det) < v and "violations_material" not in m:
            # Only fatal when the artefact ALSO lacks a recorded material
            # count. Older artefacts capped detail at 20 but do record
            # violations_material, so the number the paper quotes is still
            # traceable -- it just cannot be independently recomputed here.
            bad.append(f"{name}: monotonicity detail truncated "
                       f"({len(det)} of {v}) and no violations_material "
                       f"recorded; material count not verifiable")
        elif len(det) < v:
            print(f"  [note] {name}: detail capped at {len(det)} of {v}; "
                  f"material count read from the artefact, not recomputed",
                  file=sys.stderr)
        label = {"ml_1m": "MovieLens", "amazon_video_games": "Amazon-VG",
                 "gowalla_ts": "Gowalla"}.get(name)
        if label:
            for line in tex.splitlines():
                if not line.startswith(label):
                    continue
                cells = re.findall(r"\$(\d+)\$\s*/\s*\$(\d+)\$", line)
                for mat_q, raw_q in cells:
                    if int(mat_q) != material or int(raw_q) != v:
                        bad.append(
                            f"monotonicity {label}: paper says "
                            f"{mat_q}/{raw_q} (material/raw), artefact gives "
                            f"{material}/{v}")

    # 6. candidate recall quoted per corpus
    for name, r in res.items():
        rec = r["e0a_candidates"]["candidate_recall"]
        if name == "ml_1m" and f"{rec:.3f}" not in tex:
            bad.append(f"ml_1m candidate recall {rec:.3f} not found in prose")

    # 6b. HARD INVARIANTS. These are not paper/artefact agreement checks --
    # they are properties the artefact must satisfy on its own. A broken
    # invariant means the run is invalid, and no amount of prose agreement
    # rescues it. Added after a refactor silently made v(empty) non-zero,
    # which failed Property 1 on all three corpora while every other check
    # stayed green.
    for name, r in res.items():
        eff = (r.get("e1_source_share") or {}).get("efficiency") or {}
        if eff and not eff.get("passes", True):
            bad.append(
                f"INVALID RUN: {name} fails efficiency (Property 1), "
                f"|sum phi - v(G)| = {eff.get('abs_error', float('nan')):.2e}"
            )
        v_empty = (r.get("e1_source_share") or {}).get("v_empty")
        if v_empty is not None and abs(v_empty) > 1e-12:
            bad.append(f"INVALID RUN: {name} has v(empty) = {v_empty:.2e}, "
                       f"must be exactly 0 (Property 3)")

    # 7. self-contradiction guard
    #
    # A reviewer found five places where the manuscript asserted something in
    # one section and its negation in another: the abstract claimed six
    # analytic games while Threats called them future work; Related Work said
    # interaction indices were not evaluated while two sections reported them;
    # Threats said no equivalence test was run while Segments reported a TOST.
    # Every one described work that HAD been done -- the text was a fossil of
    # an earlier draft. No numeric check catches that, so the pairs are pinned
    # here. Two rule shapes, kept separate because conflating them produced
    # false positives the first time this was written:
    #
    #   FORBIDDEN  -- the phrase must never appear.
    #   REQUIRES   -- if the first phrase appears, the second must too.
    flat = " ".join(tex.lower().split())

    forbidden = [
        ("would go further", "Threats still calls analytic games future work"),
        ("we do not evaluate here",
         "Related Work still disclaims interaction indices"),
        ("neither of which we conducted",
         "Threats still denies conducting the equivalence test"),
        ("three sparse corpora", "only two sparse corpora exist"),
        ("margin is positive but within noise",
         "C5 claims a positive fusion margin; measured value is negative"),
        ("d_z = 0.006", "stale effect size; measured value is -0.003"),
    ]
    for phrase, why in forbidden:
        if phrase.lower() in flat:
            bad.append(f"stale text: {why}")

    requires = [
        # This claim was once an unsupported extrapolation of the log recall
        # fit, and the guard demanded its retraction. The repeat audit now
        # establishes it directly: recall is bounded by rho, the fraction of
        # users whose test item is not already masked out of every candidate
        # set by mask_seen. So the guard now demands the EVIDENCE instead --
        # the claim may stand only where the ceiling is stated.
        (r"unreachable at any pool size", r"\rho = 0.501",
         "impossibility claim must cite the measured retrievability ceiling"),
        ("six analytic", "table~\\ref{tab:analytic}",
         "analytic-games claim must cite the table that reports them"),
    ]
    for phrase, needed, why in requires:
        if phrase.lower() in flat and needed.lower() not in flat:
            bad.append(f"self-contradiction: {why}")

    # 7b. the repeat-event audit table must match its artefact
    ra = ART / "repeat_item_audit.json"
    if ra.exists():
        audit = json.loads(ra.read_text())
        label = {"ml_1m": "MovieLens-1M", "amazon_video_games": "Amazon-VG",
                 "gowalla_ts": "Gowalla"}
        for name, row in audit.items():
            pretty = label.get(name, name)
            for key, field in (("val_equals_test_pct", "val==test"),
                               ("test_item_seen_in_train_pct", "test-in-train"),
                               ("repeat_event_pct", "repeat events")):
                want = row[key]
                # Every percentage the table quotes for this corpus.
                if f"{want:.2f}\\%" not in tex and f"${want:.2f}\\%$" not in tex:
                    bad.append(
                        f"repeat audit: {pretty} {field} = {want:.2f}% "
                        f"is not present in the manuscript")
        # rho is quoted in three places and drives the impossibility claim.
        g = audit.get("gowalla_ts")
        if g:
            rho = 1.0 - g["test_item_seen_in_train_pct"] / 100.0
            if f"\\rho = {rho:.3f}" not in tex:
                bad.append(f"repeat audit: Gowalla retrievability ceiling "
                           f"rho = {rho:.3f} is not quoted in the manuscript")

    # 8. efficiency bound must not understate the artefact
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
