"""Statistical protocol (spec §11).

Primary tests:
    paired NDCG@10          -> Wilcoxon signed-rank
    LOO-Shapley gap         -> within-user permutation, 10 000 shuffles
    segment heterogeneity   -> between-segment permutation, 10 000 shuffles

Multiplicity: Holm-Bonferroni, with family size AND COMPOSITION declared.
Effect size: Cohen's d_z beside every Wilcoxon result.
"""

from __future__ import annotations

import numpy as np
from scipy import stats


def wilcoxon_test(a: np.ndarray, b: np.ndarray) -> dict:
    """Paired Wilcoxon signed-rank with Cohen's d_z (spec §11)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = a - b
    if len(d) == 0 or np.allclose(d, 0):
        return {"statistic": 0.0, "p_value": 1.0, "d_z": 0.0, "n": int(len(d)),
                "n_ties": int(len(d)), "mean_diff": 0.0}
    try:
        st, p = stats.wilcoxon(a, b, zero_method="wilcox", alternative="two-sided")
    except ValueError:
        st, p = 0.0, 1.0
    sd = d.std(ddof=1)
    return {
        "statistic": float(st), "p_value": float(p),
        "d_z": float(d.mean() / sd) if sd > 1e-12 else 0.0,
        "n": int(len(d)), "n_ties": int((d == 0).sum()), "mean_diff": float(d.mean()),
    }


def permutation_test_paired(a: np.ndarray, b: np.ndarray, n_shuffles: int = 10_000,
                            seed: int = 42) -> dict:
    """Within-user permutation via random sign flips (spec §11, E2).

    Sign flipping is the exchangeability-correct scheme for paired data: under
    H0 the label assignment within each user is arbitrary.
    """
    rng = np.random.default_rng(seed)
    d = np.asarray(a, float) - np.asarray(b, float)
    if len(d) == 0:
        return {"observed": 0.0, "p_value": 1.0, "n_shuffles": n_shuffles}
    obs = d.mean()
    signs = rng.choice([-1.0, 1.0], size=(n_shuffles, len(d)))
    null = (signs * d).mean(axis=1)
    p = (np.sum(np.abs(null) >= abs(obs)) + 1) / (n_shuffles + 1)
    return {"observed": float(obs), "p_value": float(p), "n_shuffles": int(n_shuffles)}


def permutation_test_between(x: np.ndarray, y: np.ndarray, n_shuffles: int = 10_000,
                             seed: int = 42) -> dict:
    """Between-segment permutation on the difference of means (spec §11, E3)."""
    rng = np.random.default_rng(seed)
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) == 0 or len(y) == 0:
        return {"observed": 0.0, "p_value": 1.0, "n_shuffles": n_shuffles}
    obs = x.mean() - y.mean()
    pool = np.concatenate([x, y])
    n = len(x)
    null = np.empty(n_shuffles)
    for i in range(n_shuffles):
        p = rng.permutation(pool)
        null[i] = p[:n].mean() - p[n:].mean()
    p = (np.sum(np.abs(null) >= abs(obs)) + 1) / (n_shuffles + 1)
    return {"observed": float(obs), "p_value": float(p), "n_shuffles": int(n_shuffles)}


def holm_bonferroni(p_values: dict[str, float], family: list[str] | None = None) -> dict:
    """Holm-Bonferroni correction (spec §11).

    `family` declares the COMPOSITION, not just the size. For T7 that is
    {uniform, globally-tuned, LightGCN, SASRec(App. B)} -- mixing a main-text
    family with an appendix member is defensible but must be stated, or the
    family size looks chosen after the fact.
    """
    family = family or sorted(p_values)
    m = len(family)
    ordered = sorted(((p_values.get(k, 1.0), k) for k in family))
    out, running = {}, 0.0
    for i, (p, k) in enumerate(ordered):
        adj = min(1.0, max(running, (m - i) * p))
        running = adj
        out[k] = float(adj)
    return {
        "corrected": out, "family_size": m, "family_composition": list(family),
        "raw": {k: float(p_values.get(k, 1.0)) for k in family},
    }


def bootstrap_ci(x: np.ndarray, n_boot: int = 10_000, alpha: float = 0.05,
                 seed: int = 42) -> dict:
    """Percentile bootstrap CI (Appendix-B secondary, spec §11)."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    if len(x) == 0:
        return {"mean": 0.0, "lo": 0.0, "hi": 0.0}
    means = rng.choice(x, size=(n_boot, len(x)), replace=True).mean(axis=1)
    return {
        "mean": float(x.mean()),
        "lo": float(np.percentile(means, 100 * alpha / 2)),
        "hi": float(np.percentile(means, 100 * (1 - alpha / 2))),
    }


def seed_ci(values: list[float]) -> dict:
    """Mean +/- std across seeds -- main-text CIs on phi_g (spec §2.7).

    Promoted from Appendix B because v is a FITTED quantity: exactness is a
    property of the aggregation, not of the attribution end-to-end.
    """
    a = np.asarray(values, float)
    if a.size == 0:
        return {"mean": 0.0, "std": 0.0, "lo": 0.0, "hi": 0.0, "n_seeds": 0}
    sd = float(a.std(ddof=1)) if a.size > 1 else 0.0
    return {
        "mean": float(a.mean()), "std": sd,
        "lo": float(a.mean() - 1.96 * sd / np.sqrt(a.size)),
        "hi": float(a.mean() + 1.96 * sd / np.sqrt(a.size)),
        "n_seeds": int(a.size),
    }
