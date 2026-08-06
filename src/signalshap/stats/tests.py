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


# --------------------------------------------------------------------------- #
# Hierarchical inference (review Issue #6: pseudoreplication)
# --------------------------------------------------------------------------- #


def hierarchical_bootstrap(per_seed_user_scores: dict[int, np.ndarray],
                           per_seed_user_baseline: dict[int, np.ndarray],
                           n_boot: int = 10_000, seed: int = 42,
                           alpha: float = 0.05) -> dict:
    """Two-level bootstrap over (seed, user), for paired NDCG differences.

    Users are NOT independent replicates: they share the same fitted source
    models and the same coalition heads, so a user-level test conditions on one
    draw of the training procedure and understates uncertainty. This resamples
    seeds first, then users within the selected seed, which propagates both
    sources of variation.

    With few seeds the interval is necessarily wide -- that width is the honest
    answer, not a defect of the method.
    """
    rng = np.random.default_rng(seed)
    seeds = sorted(per_seed_user_scores)
    if not seeds:
        return {"mean_diff": 0.0, "lo": 0.0, "hi": 0.0, "n_seeds": 0}

    diffs = {s: np.asarray(per_seed_user_scores[s], float)
                - np.asarray(per_seed_user_baseline[s], float) for s in seeds}
    obs = float(np.mean([d.mean() for d in diffs.values()]))

    boot = np.empty(n_boot)
    for b in range(n_boot):
        picked = rng.choice(seeds, size=len(seeds), replace=True)
        vals = []
        for s in picked:
            d = diffs[s]
            idx = rng.integers(0, len(d), size=len(d))
            vals.append(d[idx].mean())
        boot[b] = np.mean(vals)

    lo, hi = np.percentile(boot, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {
        "mean_diff": obs,
        "lo": float(lo), "hi": float(hi),
        "n_seeds": len(seeds),
        "n_boot": n_boot,
        "excludes_zero": bool(lo > 0 or hi < 0),
        "note": (
            "Two-level bootstrap over seeds then users. Compare against the "
            "user-level Wilcoxon p: if the interval spans zero where Wilcoxon "
            "reports p<0.001, the discrepancy is pseudoreplication."
        ),
    }


def tost_equivalence(a: np.ndarray, b: np.ndarray, margin: float,
                     alpha: float = 0.05) -> dict:
    """Two one-sided tests for practical equivalence (review Issue: fusion).

    A non-significant difference is not evidence of equivalence. TOST inverts
    the question: can we reject that the true difference exceeds +/- `margin`?
    `margin` must be a pre-specified smallest meaningful difference, not chosen
    after seeing the data.
    """
    from scipy import stats as _st

    d = np.asarray(a, float) - np.asarray(b, float)
    n = len(d)
    if n < 2:
        return {"equivalent": False, "note": "insufficient data"}
    m, se = d.mean(), d.std(ddof=1) / np.sqrt(n)
    if se < 1e-15:
        return {"equivalent": bool(abs(m) < margin), "note": "zero variance"}
    t_lo = (m + margin) / se
    t_hi = (m - margin) / se
    p_lo = 1 - _st.t.cdf(t_lo, n - 1)   # H0: diff <= -margin
    p_hi = _st.t.cdf(t_hi, n - 1)       # H0: diff >= +margin
    p = max(p_lo, p_hi)
    return {
        "mean_diff": float(m),
        "margin": float(margin),
        "p_tost": float(p),
        "equivalent": bool(p < alpha),
        "ci_90": [float(m - 1.645 * se), float(m + 1.645 * se)],
        "note": ("Equivalent means we can reject a true difference larger than "
                 "the margin; the margin must be pre-specified."),
    }


def rank_biserial(a: np.ndarray, b: np.ndarray) -> float:
    """Rank-biserial correlation: a better effect size than d_z here.

    Paired NDCG@10 with one relevant item is discrete and zero-inflated, which
    makes a standardised mean difference hard to interpret. Rank-biserial is
    the proportion of pairs favouring a, minus the proportion favouring b.
    """
    d = np.asarray(a, float) - np.asarray(b, float)
    nz = d[d != 0]
    if nz.size == 0:
        return 0.0
    return float((np.sum(nz > 0) - np.sum(nz < 0)) / nz.size)


def friedman_nemenyi(scores: dict[str, list[float]], alpha: float = 0.05) -> dict:
    """Friedman omnibus test with a Nemenyi post-hoc critical difference.

    Both reviewers asked for a multi-comparison test across methods. The
    Wilcoxon tests we report elsewhere are per-method-pair and per-corpus; they
    establish that a difference exists on a given corpus, not that a method
    ranks above another *across* corpora and seeds. Friedman ranks the methods
    within each (corpus, seed) block and asks whether the mean ranks differ
    more than chance; Nemenyi then gives the critical difference two mean ranks
    must exceed to be separable.

    Parameters
    ----------
    scores
        method name -> list of scores, one per (corpus, seed) block, all
        methods evaluated on the same blocks in the same order.

    Notes
    -----
    Nemenyi's critical value is tabulated, not closed-form. We include the
    studentised-range constants for the method counts we actually use and
    refuse to guess beyond them, rather than silently interpolating.
    """
    from scipy import stats as sps

    methods = sorted(scores)
    mat = np.asarray([scores[m] for m in methods], dtype=float)   # k x b
    k, b = mat.shape
    if b < 2 or k < 3:
        return {"error": f"Friedman needs >=3 methods and >=2 blocks, got {k}, {b}"}

    # Rank within each block; rank 1 = best (highest score).
    ranks = np.empty_like(mat)
    for j in range(b):
        ranks[:, j] = sps.rankdata(-mat[:, j])
    mean_ranks = ranks.mean(axis=1)

    stat, p = sps.friedmanchisquare(*[mat[i] for i in range(k)])

    #: q_alpha for Nemenyi at alpha=0.05, indexed by number of methods.
    Q05 = {3: 2.343, 4: 2.569, 5: 2.728, 6: 2.850, 7: 2.949, 8: 3.031}
    cd = None
    if alpha == 0.05 and k in Q05:
        cd = Q05[k] * np.sqrt(k * (k + 1) / (6.0 * b))

    out = {
        "methods": methods,
        "n_blocks": int(b),
        "mean_ranks": {m: float(r) for m, r in zip(methods, mean_ranks)},
        "friedman_statistic": float(stat),
        "friedman_p": float(p),
        "critical_difference": float(cd) if cd is not None else None,
        "alpha": alpha,
        "note": (
            "Rank 1 is best. Two methods are separable only if their mean ranks "
            "differ by more than the critical difference. With few blocks the "
            "CD is wide, which is a property of the design, not a failure."
        ),
    }
    if cd is not None:
        out["separable_pairs"] = [
            [methods[i], methods[j]]
            for i in range(k) for j in range(i + 1, k)
            if abs(mean_ranks[i] - mean_ranks[j]) > cd
        ]
    return out
