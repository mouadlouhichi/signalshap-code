#!/usr/bin/env python3
"""Rebuild manuscript Figure 2 on the seed-42 MovieLens NDCG game.

The released ``results_ml_1m.json`` contains exact Shapley, Banzhaf,
binomial-semivalue, singleton, pair-interaction, leave-one-out, grand-value,
and monotonicity diagnostics.  These are linear functionals of the 32-point
coalition lattice.  Together they form a full-rank system, so this script first
recovers the lattice and checks every released diagnostic before sampling it.

No recommender is refit here: the experiment is conditional on the already
fitted, baseline-centred ranking-stage NDCG@10 characteristic function, which
is exactly the aggregation question studied in the paper.
"""

from __future__ import annotations

import json
from itertools import combinations
from math import comb, factorial
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
FIGURE = ROOT / "figures" / "Fig8.png"
ARTEFACT = ROOT / "artefacts" / "fig2_ndcg_sampling.json"

SOURCES = ("cf", "ct", "pop", "rec", "seq")
N = len(SOURCES)
BUDGETS = (50, 100, 500, 2000)
REPEATS = 20
MASTER_SEED = 42
SEED_SPREAD_PCT = 2.22


PUBLISHED = {
    "v_empty": 0.0,
    "v_grand": 0.0516886486597282,
    "singletons": {
        "cf": 0.03474634171427221,
        "ct": -0.00011662752236713077,
        "pop": 0.012624310078245635,
        "rec": 0.0022985123145158087,
        "seq": 0.04144347949957896,
    },
    "shapley": {
        "cf": 0.015381831033907892,
        "ct": 2.4768641547751004e-05,
        "pop": 0.006478655122434057,
        "rec": 0.0005308012954656567,
        "seq": 0.029272592566372845,
    },
    "banzhaf": {
        "cf": 0.015607202178567902,
        "ct": -0.00019790156843463294,
        "pop": 0.0062851257703321756,
        "rec": 0.0001609586982754994,
        "seq": 0.029389280803890624,
    },
    "q025": {
        "cf": 0.02505142410261055,
        "ct": -0.0004158543938787098,
        "pop": 0.008915701610801073,
        "rec": 0.0008192517439912649,
        "seq": 0.03522431756010868,
    },
    "q075": {
        "cf": 0.00580544168706628,
        "ct": 0.00033457472151405773,
        "pop": 0.003925362107547135,
        "rec": 3.794769787600798e-05,
        "seq": 0.023359729840926935,
    },
    "loo": {
        "cf": -0.00479510433723835,
        "ct": 0.0011459055332502799,
        "pop": 0.0011961774628881094,
        "rec": 0.0003315205530342452,
        "seq": 0.016724012570953704,
    },
    "pair_interactions": {
        "cf|ct": 0.002206283404872061,
        "cf|pop": -0.02526323790965032,
        "cf|rec": -0.0011946212227713449,
        "cf|seq": -0.05483131637547152,
        "ct|pop": -0.002151920343487122,
        "ct|rec": 0.0013361246310605375,
        "ct|seq": 0.0011345784187893442,
        "pop|rec": -0.0018871990041307947,
        "pop|seq": 0.006446092026553186,
        "rec|seq": -0.002188287927121526,
    },
    # Every negative one-player marginal reported by the monotonicity audit.
    "negative_marginals": [
        ((), "ct", -0.00011662752236713077),
        (("cf",), "pop", -2.5646895682004955e-05),
        (("cf",), "rec", -7.900944097591345e-05),
        (("pop",), "ct", -0.004354887044792373),
        (("pop",), "rec", -0.0017435302808715587),
        (("seq",), "ct", -0.0005122388582045403),
        (("seq",), "rec", -0.0009119517009301276),
        (("cf", "ct"), "pop", -6.05769405241513e-05),
        (("cf", "ct"), "rec", -5.214321732328886e-05),
        (("cf", "seq"), "rec", -0.00024452169687717157),
        (("ct", "seq"), "rec", -0.0008604145555227011),
        (("pop", "rec"), "ct", -0.0020692836086818045),
        (("pop", "seq"), "cf", -0.006047137653081847),
        (("pop", "seq"), "ct", -0.000178257300277207),
        (("pop", "seq"), "rec", -0.00011630291416737243),
        (("rec", "seq"), "ct", -0.00046070171279711386),
        (("cf", "ct", "pop"), "rec", -4.6759769024115605e-05),
        (("cf", "ct", "rec"), "pop", -5.519349222497805e-05),
        (("cf", "ct", "seq"), "rec", -0.000366694616688909),
        (("cf", "pop", "rec"), "ct", -3.5603555702291845e-05),
        (("cf", "pop", "seq"), "rec", -0.0001743875441524781),
        (("ct", "pop", "seq"), "cf", -0.005228882916741083),
        (("ct", "pop", "seq"), "rec", -0.00010225802646848803),
        (("pop", "rec", "seq"), "cf", -0.006105222283066952),
        (("pop", "rec", "seq"), "ct", -0.00016421241257832259),
        (("ct", "pop", "rec", "seq"), "cf", -0.00479510433723835),
    ],
}


def all_coalitions() -> list[frozenset[str]]:
    return [
        frozenset(c)
        for k in range(N + 1)
        for c in combinations(SOURCES, k)
    ]


def reconstruct_game() -> tuple[dict[frozenset[str], float], dict]:
    coalitions = all_coalitions()
    index = {coalition: i for i, coalition in enumerate(coalitions)}
    rows: list[np.ndarray] = []
    targets: list[float] = []
    names: list[str] = []

    def add(terms: dict[frozenset[str] | tuple[str, ...], float],
            target: float, name: str) -> None:
        row = np.zeros(len(coalitions), dtype=float)
        for coalition, coefficient in terms.items():
            row[index[frozenset(coalition)]] += coefficient
        rows.append(row)
        targets.append(float(target))
        names.append(name)

    empty = frozenset()
    grand = frozenset(SOURCES)
    add({empty: 1.0}, PUBLISHED["v_empty"], "v(empty)")
    add({grand: 1.0}, PUBLISHED["v_grand"], "v(G)")
    for source, value in PUBLISHED["singletons"].items():
        add({frozenset({source}): 1.0}, value, f"v({source})")

    for family in ("shapley", "banzhaf", "q025", "q075"):
        for source, target in PUBLISHED[family].items():
            terms: dict[frozenset[str], float] = {}
            others = tuple(g for g in SOURCES if g != source)
            for k in range(N):
                for members in combinations(others, k):
                    coalition = frozenset(members)
                    if family == "shapley":
                        weight = factorial(k) * factorial(N - k - 1) / factorial(N)
                    elif family == "banzhaf":
                        weight = 1.0 / (2 ** (N - 1))
                    else:
                        q = 0.25 if family == "q025" else 0.75
                        weight = q ** k * (1.0 - q) ** (N - 1 - k)
                    terms[coalition | {source}] = terms.get(
                        coalition | {source}, 0.0) + weight
                    terms[coalition] = terms.get(coalition, 0.0) - weight
            add(terms, target, f"{family}:{source}")

    for source, target in PUBLISHED["loo"].items():
        add({grand: 1.0, grand - {source}: -1.0}, target, f"loo:{source}")

    for pair, target in PUBLISHED["pair_interactions"].items():
        first, second = pair.split("|")
        rest = tuple(g for g in SOURCES if g not in (first, second))
        terms: dict[frozenset[str], float] = {}
        for k in range(len(rest) + 1):
            for members in combinations(rest, k):
                coalition = frozenset(members)
                weight = (
                    2.0 * factorial(k) * factorial(N - k - 2)
                    / factorial(N - 1)
                )
                for cell, sign in (
                    (coalition | {first, second}, 1.0),
                    (coalition | {first}, -1.0),
                    (coalition | {second}, -1.0),
                    (coalition, 1.0),
                ):
                    terms[cell] = terms.get(cell, 0.0) + weight * sign
        add(terms, target, f"interaction:{pair}")

    for members, source, target in PUBLISHED["negative_marginals"]:
        coalition = frozenset(members)
        add(
            {coalition | {source}: 1.0, coalition: -1.0},
            target,
            f"negative:{'+'.join(members) or 'empty'}->{source}",
        )

    matrix = np.asarray(rows)
    vector = np.asarray(targets)
    solution, _, rank, _ = np.linalg.lstsq(matrix, vector, rcond=None)
    residuals = matrix @ solution - vector
    game = {coalition: float(value) for coalition, value in zip(coalitions, solution)}

    violations = []
    for coalition in coalitions:
        for source in SOURCES:
            if source in coalition:
                continue
            delta = game[coalition | {source}] - game[coalition]
            if delta < 0:
                violations.append(delta)

    audit = {
        "linear_system_shape": list(matrix.shape),
        "rank": int(rank),
        "max_constraint_residual": float(np.max(np.abs(residuals))),
        "negative_marginals": len(violations),
        "material_negative_marginals": int(
            sum(abs(delta) > 1e-3 for delta in violations)
        ),
        "max_negative_marginal_magnitude": float(max(abs(x) for x in violations)),
        "constraint_names": names,
    }
    if rank != len(coalitions):
        raise RuntimeError(f"coalition recovery is not unique: rank={rank}")
    if audit["max_constraint_residual"] > 1e-12:
        raise RuntimeError(f"coalition recovery residual is too large: {audit}")
    if (audit["negative_marginals"], audit["material_negative_marginals"]) != (26, 7):
        raise RuntimeError(f"monotonicity audit did not reproduce: {audit}")
    return game, audit


def exact_shapley(game: dict[frozenset[str], float]) -> np.ndarray:
    values = np.zeros(N)
    for j, source in enumerate(SOURCES):
        others = tuple(g for g in SOURCES if g != source)
        for k in range(N):
            weight = factorial(k) * factorial(N - k - 1) / factorial(N)
            for members in combinations(others, k):
                coalition = frozenset(members)
                values[j] += weight * (
                    game[coalition | {source}] - game[coalition]
                )
    return values


def permutation_sample(
    game: dict[frozenset[str], float], rng: np.random.Generator, budget: int
) -> np.ndarray:
    estimate = np.zeros(N)
    for _ in range(budget):
        coalition = frozenset()
        for j in rng.permutation(N):
            source = SOURCES[j]
            estimate[j] += game[coalition | {source}] - game[coalition]
            coalition = coalition | {source}
    return estimate / budget


def kernelshap_sample(
    game: dict[frozenset[str], float], rng: np.random.Generator, budget: int
) -> np.ndarray:
    """KernelSHAP WLS with exact empty/grand constraints.

    Nontrivial coalitions are drawn with replacement in proportion to the
    Shapley kernel.  Because the sampling distribution already contains the
    kernel weight, the sampled regression is unweighted; the equality
    constraint enforces efficiency exactly.
    """
    coalitions = [c for c in all_coalitions() if 0 < len(c) < N]
    kernel = np.asarray([
        (N - 1) / (comb(N, len(c)) * len(c) * (N - len(c)))
        for c in coalitions
    ])
    probability = kernel / kernel.sum()
    draws = rng.choice(len(coalitions), size=budget, replace=True, p=probability)
    design = np.asarray([
        [source in coalitions[j] for source in SOURCES] for j in draws
    ], dtype=float)
    response = np.asarray([game[coalitions[j]] - game[frozenset()] for j in draws])

    hessian = design.T @ design
    score = design.T @ response
    ones = np.ones(N)
    kkt = np.block([
        [hessian, ones[:, None]],
        [ones[None, :], np.zeros((1, 1))],
    ])
    rhs = np.r_[score, game[frozenset(SOURCES)] - game[frozenset()]]
    return np.linalg.lstsq(kkt, rhs, rcond=None)[0][:N]


def run_sampling(game: dict[frozenset[str], float]) -> dict:
    exact = exact_shapley(game)
    grand = game[frozenset(SOURCES)]
    children = np.random.SeedSequence(MASTER_SEED).spawn(
        len(BUDGETS) * 2 * REPEATS
    )
    child = iter(children)
    output = {"permutation": {}, "kernelshap": {}}
    methods = (
        ("permutation", permutation_sample),
        ("kernelshap", kernelshap_sample),
    )
    for budget in BUDGETS:
        for name, estimator in methods:
            errors = []
            for _ in range(REPEATS):
                rng = np.random.default_rng(next(child))
                estimate = estimator(game, rng, budget)
                errors.append(float(np.max(np.abs(estimate - exact)) / abs(grand) * 100))
            output[name][str(budget)] = {
                "errors_pct_v_grand": errors,
                "mean_pct_v_grand": float(np.mean(errors)),
                "p95_pct_v_grand": float(np.percentile(errors, 95)),
            }
    return {
        "master_seed": MASTER_SEED,
        "repeats": REPEATS,
        "budgets": list(BUDGETS),
        "error_norm": "max absolute source error divided by abs(v(G))",
        "exact_shapley": dict(zip(SOURCES, map(float, exact))),
        "v_grand": float(grand),
        "materiality_pct_v_grand": float(1e-3 / abs(grand) * 100),
        "seed_spread_pct_v_grand": SEED_SPREAD_PCT,
        "methods": output,
    }


def draw(sampling: dict) -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 9,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "axes.grid": True,
        "grid.alpha": 0.25,
    })
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    styles = {
        "permutation": ("#0072B2", "o", "Permutation sampling"),
        "kernelshap": ("#E69F00", "s", "KernelSHAP"),
    }
    x = np.asarray(BUDGETS)
    for name, (colour, marker, label) in styles.items():
        cells = sampling["methods"][name]
        mean = np.asarray([cells[str(m)]["mean_pct_v_grand"] for m in BUDGETS])
        p95 = np.asarray([cells[str(m)]["p95_pct_v_grand"] for m in BUDGETS])
        ax.plot(
            x, mean, color=colour, marker=marker, markersize=6.5,
            linewidth=1.6, label=f"{label} (mean)", zorder=3,
        )
        ax.fill_between(x, mean, p95, color=colour, alpha=0.16, linewidth=0)

    spread = sampling["seed_spread_pct_v_grand"]
    materiality = sampling["materiality_pct_v_grand"]
    ax.axhline(spread, color="black", linestyle="--", linewidth=1.1)
    ax.axhline(materiality, color="black", linestyle=":", linewidth=1.1)
    ax.text(50, spread * 1.08, f"seed-to-seed spread ({spread:.2f}%)", fontsize=8)
    ax.text(50, materiality / 1.25, f"materiality 1e-3 ({materiality:.2f}%)", fontsize=8)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(BUDGETS, [str(m) for m in BUDGETS])
    ax.set_xlabel("Sampling budget $M$ (coalitions or permutations)")
    ax.set_ylabel(r"$\|\widehat{\varphi}-\varphi\|_\infty$ as \% of $v(\mathcal{G})$")
    ax.legend(loc="upper right", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=300, bbox_inches="tight")
    plt.close(fig)


def coalition_name(coalition: frozenset[str]) -> str:
    return "+".join(g for g in SOURCES if g in coalition) or "empty"


def main() -> None:
    game, recovery = reconstruct_game()
    sampling = run_sampling(game)
    draw(sampling)
    ARTEFACT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "dataset": "ml_1m",
        "seed": 42,
        "payoff": "ranking-stage baseline-centred NDCG@10",
        "candidate_rule": "symmetric_reciprocal_rank",
        "source_artefact": "results_ml_1m.json",
        "recovery": recovery,
        "coalition_values": {
            coalition_name(c): value
            for c, value in sorted(game.items(), key=lambda item: (len(item[0]), coalition_name(item[0])))
        },
        "sampling": sampling,
    }
    ARTEFACT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    p500 = sampling["methods"]["permutation"]["500"]
    print(f"wrote {FIGURE}")
    print(f"wrote {ARTEFACT}")
    print(
        "M=500 permutation: "
        f"mean={p500['mean_pct_v_grand']:.4f}%, "
        f"p95={p500['p95_pct_v_grand']:.4f}%"
    )


if __name__ == "__main__":
    main()