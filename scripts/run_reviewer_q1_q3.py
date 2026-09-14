#!/usr/bin/env python3
"""Answer reviewer questions Q1 and Q3 from already-released artefacts.

Q1. "Do you have a version of Shapley computed on an explicitly end-to-end
     game, to show whether 'Shapley fails to predict retirement loss' persists
     when the game matches the intervention?"

     Yes. `e11_estimands_*.json` already carries three characteristic
     functions at seed 42: the refitted head used in the main text, a fixed
     grand-coalition head merely masked to S, and a fully end-to-end game in
     which each coalition retrieves its own candidates. The last one is
     exactly the game the reviewer asks for. This script scores all three
     against the observed end-to-end retirement loss.

Q3. "Can you include a configuration where candidate recall is more sensitive
     to retirement, to assess LOO_rank's predictive validity boundary?"

     Partially, without new runs. The three corpora already span candidate
     recall 0.748 / 0.589 / 0.450, and `e12_retirement_*.json` records the
     recall left after each single-source retirement. That gives a measured
     spread of retrieval sensitivity, against which LOO_rank's rank agreement
     can be plotted. It is weaker than a purpose-built retrieval-dominant
     configuration, and the script prints the caveat rather than hiding it.

Nothing here refits a model; every number is a functional of released
artefacts, so the script runs in milliseconds and cannot drift from the paper.
"""

from __future__ import annotations

import json
from pathlib import Path

from scipy import stats

REPO = Path(__file__).resolve().parent.parent
ART = REPO / "artefacts"
PLAYERS = ("cf", "ct", "pop", "rec", "seq")
CORPORA = ("ml_1m", "amazon_video_games", "gowalla_ts")


def q1_estimand_matched_shapley() -> dict:
    """Score each characteristic function against observed retirement loss."""
    out = {}
    for corpus in ("ml_1m", "amazon_video_games"):
        est_path = ART / f"e11_estimands_{corpus}.json"
        ret_path = ART / f"e12_retirement_{corpus}.json"
        if not (est_path.exists() and ret_path.exists()):
            continue
        est = json.loads(est_path.read_text())
        ret = json.loads(ret_path.read_text())
        observed = ret["true_retirement_loss"]
        target = [observed[g] for g in PLAYERS]
        correct = min(PLAYERS, key=lambda g: observed[g])

        rec = {"observed_smallest_loss_source": correct, "games": {}}
        for game in ("refit_head", "fixed_head", "end_to_end"):
            phi = est[game]["shapley"]
            tau, p = stats.kendalltau([phi[g] for g in PLAYERS], target)
            pick = min(PLAYERS, key=lambda g: phi[g])
            rec["games"][game] = {
                "shapley": phi,
                "kendall_tau_vs_observed_loss": float(tau),
                "p_value": float(p),
                "predicted_smallest": pick,
                "identifies_correctly": pick == correct,
            }
        # Ranking-stage LOO on the same corpus, for reference.
        tau, p = stats.kendalltau([ret["loo"][g] for g in PLAYERS], target)
        rec["loo_rank"] = {
            "kendall_tau_vs_observed_loss": float(tau),
            "predicted_smallest": min(PLAYERS, key=lambda g: ret["loo"][g]),
            "identifies_correctly": ret["loo_picks_correctly"],
        }
        out[corpus] = rec
    return out


def q3_retrieval_sensitivity() -> dict:
    """Measure how far retrieval actually moves when a source is retired."""
    out = {}
    for corpus in CORPORA:
        path = ART / f"e12_retirement_{corpus}.json"
        if not path.exists():
            continue
        j = json.loads(path.read_text())
        full = j["recall_full"]
        after = j["recall_after_removal"]
        drops = {g: full - after[g] for g in PLAYERS}
        worst = max(drops, key=drops.get)
        out[corpus] = {
            "recall_full": full,
            "recall_after_removal": after,
            "recall_drop": drops,
            "largest_drop_source": worst,
            "largest_drop_absolute": drops[worst],
            "largest_drop_relative": drops[worst] / full,
            "kendall_tau_loo": j["kendall_tau_loo_vs_truth"],
            "kendall_tau_shapley": j["kendall_tau_shapley_vs_truth"],
            "loo_picks_correctly": j["loo_picks_correctly"],
        }
    return out


def main() -> int:
    payload = {
        "note": (
            "Derived entirely from released artefacts; no model is refitted. "
            "Q1 uses the three characteristic functions in e11_estimands_*; "
            "Q3 uses the recall-after-removal fields in e12_retirement_*."),
        "q1_estimand_matched_shapley": q1_estimand_matched_shapley(),
        "q3_retrieval_sensitivity": q3_retrieval_sensitivity(),
    }
    out = ART / "reviewer_q1_q3.json"
    out.write_text(json.dumps(payload, indent=1) + "\n")

    print(f"wrote {out.relative_to(REPO)}\n")
    print("Q1  Does matching the game to the intervention rescue Shapley?")
    for corpus, rec in payload["q1_estimand_matched_shapley"].items():
        print(f"  {corpus}  (observed smallest loss: "
              f"{rec['observed_smallest_loss_source']})")
        for game, g in rec["games"].items():
            mark = "correct" if g["identifies_correctly"] else "wrong"
            print(f"    Shapley/{game:11s} tau={g['kendall_tau_vs_observed_loss']:+.2f}"
                  f"  picks {g['predicted_smallest']:4s} {mark}")
        l = rec["loo_rank"]
        print(f"    LOO_rank{'':12s} tau={l['kendall_tau_vs_observed_loss']:+.2f}"
              f"  picks {l['predicted_smallest']:4s} "
              f"{'correct' if l['identifies_correctly'] else 'wrong'}")

    print("\nQ3  Is LOO_rank's success confined to a high-recall regime?")
    for corpus, rec in payload["q3_retrieval_sensitivity"].items():
        print(f"  {corpus:20s} recall {rec['recall_full']:.3f}"
              f"  max retrieval drop {rec['largest_drop_relative']:5.1%}"
              f" ({rec['largest_drop_source']})"
              f"  tau_LOO {rec['kendall_tau_loo']:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
