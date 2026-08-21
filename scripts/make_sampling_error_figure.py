#!/usr/bin/env python3
"""Figure for P1: sampled Shapley error against the two thresholds that matter.

The comparison the reviewer actually wants is not "is sampling error small" in
the abstract, but "is it small relative to the two yardsticks this paper
already uses": the seed-to-seed spread of the fitted values, and the 1e-3
materiality threshold that defines a material sign flip. Both are drawn.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parent.parent
ART = REPO / "artefacts"
OUT = REPO / "paper-kais" / "figures" / "Fig8.png"

# Yardsticks, both computed from the ranking-stage NDCG game on ML-1M.
V_GRAND = 0.05225
MATERIALITY = 1e-3


def seed_range_fraction() -> float:
    ci = json.loads((ART / "final_seed_ci.json").read_text())["ml_1m"]
    per_seed = ci["per_seed"]
    players = ["cf", "ct", "pop", "rec", "seq"]
    worst = 0.0
    for g in players:
        vals = np.array([per_seed[s][g] for s in per_seed])
        worst = max(worst, vals.max() - vals.min())
    return worst / V_GRAND


def main() -> int:
    data = json.loads((ART / "sampling_error.json").read_text())
    budgets = sorted(int(m) for m in data["budgets"])

    fig, ax = plt.subplots(figsize=(6.4, 4.0))

    for name, label, marker in (
        ("permutation", "Permutation sampling", "o"),
        ("kernelshap", "KernelSHAP", "s"),
    ):
        mean = [data["budgets"][str(m)][name]["relative_to_v_grand_mean"] * 100
                for m in budgets]
        p95 = [data["budgets"][str(m)][name]["relative_to_v_grand_p95"] * 100
               for m in budgets]
        ax.plot(budgets, mean, marker=marker, label=f"{label} (mean)")
        ax.fill_between(budgets, mean, p95, alpha=0.15)

    seed_pct = seed_range_fraction() * 100
    mat_pct = MATERIALITY / V_GRAND * 100

    ax.axhline(seed_pct, color="black", linestyle="--", linewidth=1.0)
    ax.text(budgets[0], seed_pct * 1.06,
            f"seed-to-seed range ({seed_pct:.1f}\\%)"
            .replace("\\%", "%"), fontsize=8, va="bottom")

    ax.axhline(mat_pct, color="black", linestyle=":", linewidth=1.0)
    ax.text(budgets[0], mat_pct * 0.80,
            f"materiality 1e-3 ({mat_pct:.1f}%)", fontsize=8, va="top")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Sampling budget $M$ (coalitions or permutations)")
    ax.set_ylabel(r"$\|\hat\varphi-\varphi\|_\infty$ as % of $v(\mathcal{G})$")
    ax.set_xticks(budgets)
    ax.set_xticklabels([str(m) for m in budgets])
    ax.legend(fontsize=8, frameon=False)
    ax.grid(alpha=0.25, which="both", linewidth=0.4)
    fig.tight_layout()
    fig.savefig(OUT, dpi=300)
    print(f"wrote {OUT.relative_to(REPO)}")
    print(f"  seed range {seed_pct:.2f}%   materiality {mat_pct:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
