#!/usr/bin/env python3
"""Persist the complete 32-coalition ranking-stage NDCG@10 game.

Why this exists
---------------
The sampling-error study (P1, Figure 8) needs a complete coalition lattice. The
only one previously persisted was `e11_estimands_*.json ->
end_to_end.coalition_recall`, which is the end-to-end RECALL game, not the
ranking-stage baseline-centred NDCG@10 game whose Shapley values the paper
reports. Measuring sampling error on the recall game and asking the reader to
accept that relative errors transfer is a gap a reviewer can name, and one did.

This script writes the real thing: `game.v_all()` on the main fixed-candidate
game, so `run_sampling_error.py --game ndcg` can plot the characteristic
function the paper actually uses.

Requires the corpora. Run it where the data lives:

    python scripts/persist_ndcg_game.py --dataset ml_1m --seed 42

It reuses the same pipeline and configuration as the main study, so the values
it writes must reproduce the reported v(G) and Shapley vector; the script
asserts that before writing rather than trusting it.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ART = REPO / "artefacts"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="ml_1m")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    # Imported lazily so that `--help` works without the scientific stack.
    from signalshap.config import load_config
    from signalshap.game.core import exact_shapley
    from signalshap.pipeline import SignalShapPipeline

    cfg = load_config(dataset=args.dataset, seed=args.seed)
    pipe = SignalShapPipeline(cfg)
    pipe.prepare()

    game = pipe.game
    v = game.v_all()

    players = tuple(game.sources)
    phi = exact_shapley(v, players)
    v_grand = v[frozenset(players)]
    residual = abs(sum(phi.values()) - v_grand)
    if residual > 1e-12:
        raise SystemExit(f"efficiency violated: {residual}")

    payload = {
        "dataset": args.dataset,
        "seed": args.seed,
        "game": "ranking_stage_ndcg10_baseline_centred",
        "note": (
            "Complete 32-coalition characteristic function for the MAIN game "
            "of the paper: fixed coalition-independent candidates, ridge head "
            "refitted per coalition on validation, baseline-centred NDCG@10 "
            "on test. This is the lattice the sampling-error study should "
            "use."),
        "players": list(players),
        "v": {(",".join(sorted(S)) if S else "empty"): val
              for S, val in sorted(v.items(), key=lambda kv: (len(kv[0]), sorted(kv[0])))},
        "shapley": phi,
        "v_grand": v_grand,
        "efficiency_residual": residual,
    }

    out = args.out or ART / f"ndcg_game_{args.dataset}_seed{args.seed}.json"
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"wrote {out}")
    print(f"  v(G) = {v_grand:.6f}   efficiency residual {residual:.2e}")
    for g in players:
        print(f"  phi[{g}] = {phi[g]:+.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
