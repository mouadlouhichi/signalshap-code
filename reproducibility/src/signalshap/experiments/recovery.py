"""Controlled redundancy intervention on REAL data (the E9 recovery study).

The central claim of this work is that LOO misattributes under redundancy. On
observational data that claim can only ever be *suggested*: we see LOO and
Shapley disagree, but we have no ground truth telling us which is right.

This experiment supplies the ground truth by intervention. We take the real
corpus and inject a duplicate of an existing source:

    cf_2  =  cf  +  eta * noise

Because we built it, we KNOW the correct attribution:

  * cf and cf_2 are (near-)exchangeable, so a correct attributor must give
    them approximately EQUAL credit -- this is the Shapley symmetry axiom;
  * the pair jointly does the work that cf did alone before injection, so
    their SUM should approximate the original phi_cf -- a conservation
    property that follows from efficiency;
  * LOO, by contrast, must collapse toward zero for BOTH, because removing
    either one alone leaves the other to cover for it.

That gives a falsifiable prediction with a known answer, on real data. If
exact Shapley fails to recover it, the method is wrong and this experiment
says so.
"""

from __future__ import annotations

import numpy as np

from ..attribution.baselines import loo_attribution
from ..game.core import SignalShapGame, exact_shapley


def inject_duplicate(scores: dict[str, np.ndarray], source: str,
                     eta: float = 0.01, seed: int = 42) -> tuple[dict, str]:
    """Return scores augmented with a near-duplicate of `source`.

    `eta` is the relative noise scale. eta=0 gives an exact clone (perfect
    redundancy); small positive eta gives the epsilon-redundancy of Lemma 1
    without the degeneracy of identical columns.
    """
    rng = np.random.default_rng(seed)
    base = scores[source]
    finite = np.isfinite(base)
    sd = base[finite].std() if finite.any() else 1.0
    dup = base + eta * sd * rng.normal(size=base.shape).astype(base.dtype)
    dup[~finite] = -np.inf
    name = f"{source}_dup"
    return {**scores, name: dup}, name


def coalition_redundancy_deviation(v, sources, g1: str, g2: str) -> dict:
    """Max deviation from EXACT redundancy across all background coalitions.

    Duplicating a source guarantees exchangeability, but under ridge it does
    NOT structurally guarantee redundancy: two identical columns share the
    penalty, so the effective regularisation on their common direction is
    halved and the fitted predictions can move. LOO collapse is therefore an
    empirical outcome to be measured, not a theorem to be assumed. This
    function measures it directly:

        max_S max(|v(S+g1) - v(S+g2)|,
                  |v(S+g1) - v(S+g1+g2)|,
                  |v(S+g2) - v(S+g1+g2)|)
    """
    from itertools import combinations as _c

    rest = [s for s in sources if s not in (g1, g2)]
    devs = []
    for k in range(len(rest) + 1):
        for c in _c(rest, k):
            S = frozenset(c)
            a, b, ab = v[S | {g1}], v[S | {g2}], v[S | {g1, g2}]
            devs.append(max(abs(a - b), abs(a - ab), abs(b - ab)))
    return {
        "max_deviation": float(max(devs)) if devs else 0.0,
        "mean_deviation": float(sum(devs) / len(devs)) if devs else 0.0,
        "n_background_coalitions": len(devs),
        "exactly_redundant": bool(max(devs) < 1e-12) if devs else True,
    }


def recovery_experiment(exp, source: str = "cf", etas=(0.0, 0.01, 0.1, 0.5),
                        seed: int = 42, verbose: bool = True,
                        diagnostic_lambda: float | None = None) -> dict:
    """Run the intervention at several redundancy strengths.

    `exp` is a prepared Experiment. Candidates are held FIXED at the
    pre-injection set so that the only thing changing is the player set --
    otherwise the duplicate would also alter retrieval and the comparison
    would confound two effects.

    `diagnostic_lambda` overrides the frozen ridge penalty for this diagnostic
    only. Setting it to 0 makes duplication provably prediction-invariant
    (least squares is invariant to a repeated column), which turns the
    redundancy prediction into a structural guarantee rather than an empirical
    observation. We report BOTH settings: the frozen lambda answers "what does
    the deployed game do?", lambda=0 answers "is the axiom recovered when the
    estimator is replication-invariant by construction?".
    """
    baseline_phi = exact_shapley(exp.v)
    baseline_loo = loo_attribution(exp.v)
    out = {
        "dataset": exp.name,
        "injected_source": source,
        "baseline_shapley": baseline_phi,
        "baseline_loo": baseline_loo,
        "conditions": {},
        "design": (
            "A duplicate of the named source is injected into the player set on "
            "REAL data, with the candidate set held fixed. Ground truth follows "
            "by construction: symmetry requires equal credit for the pair, and "
            "efficiency requires their sum to approximate the pre-injection "
            "value of the original source. LOO must collapse for both."
        ),
    }

    import time as _t
    for n_done, eta in enumerate(etas, 1):
        _t0 = _t.time()
        if verbose:
            print(f"    [E9 {exp.name}] eta={eta} ({n_done}/{len(etas)}) "
                  f"-- 2^6=64 coalitions...", flush=True)
        sc, dup = inject_duplicate(exp.scores, source, eta, seed)
        srcs = tuple(list(exp.game.sources) + [dup])
        lam = (exp.cfg.ridge_lambda if diagnostic_lambda is None
               else diagnostic_lambda)
        g = SignalShapGame(
            sc, exp.candidates, exp.valid_items, exp.test_items,
            ridge_lambda=lam, k_ndcg=exp.cfg.k_ndcg,
            v0_seed=exp.cfg.v0_seed, sources=srcs,
        )
        v = g.v_all()
        phi = exact_shapley(v, srcs)
        loo = loo_attribution(v, srcs)

        pair_sum = phi[source] + phi[dup]
        # Symmetry error, normalised by the pair's own scale.
        denom = abs(pair_sum) if abs(pair_sum) > 1e-12 else 1.0
        out["conditions"][f"eta={eta}"] = {
            "eta": eta,
            "shapley": phi,
            "loo": loo,
            "phi_original": phi[source],
            "phi_duplicate": phi[dup],
            "pair_sum": pair_sum,
            "baseline_phi_original": baseline_phi[source],
            "conservation_ratio": (
                pair_sum / baseline_phi[source]
                if abs(baseline_phi[source]) > 1e-12 else float("nan")
            ),
            "symmetry_abs_error": abs(phi[source] - phi[dup]),
            "symmetry_rel_error": abs(phi[source] - phi[dup]) / denom,
            "loo_original": loo[source],
            "loo_duplicate": loo[dup],
            "diagnostic_lambda": lam,
            "coalition_redundancy": coalition_redundancy_deviation(
                v, srcs, source, dup),
            "loo_collapse_ratio": (
                loo[source] / baseline_loo[source]
                if abs(baseline_loo[source]) > 1e-12 else float("nan")
            ),
        }
        if verbose:
            print(f"    [E9 {exp.name}] eta={eta} done in {_t.time()-_t0:.1f}s  "
                  f"symmetry_err={abs(phi[source]-phi[dup]):.2e}", flush=True)
    return out


def summarise(rec: dict) -> str:
    """Human-readable verdict, for the notebook and the log."""
    lines = [f"Redundancy recovery on {rec['dataset']}, "
             f"injected duplicate of '{rec['injected_source']}'", ""]
    lines.append(f"{'eta':>6} {'phi_orig':>10} {'phi_dup':>10} {'sym.err':>9} "
                 f"{'pair_sum':>10} {'conserv':>8} {'LOO_orig':>10} {'LOO_dup':>10}")
    for k, c in rec["conditions"].items():
        lines.append(
            f"{c['eta']:>6.2f} {c['phi_original']:>10.5f} {c['phi_duplicate']:>10.5f} "
            f"{c['symmetry_abs_error']:>9.5f} {c['pair_sum']:>10.5f} "
            f"{c['conservation_ratio']:>8.3f} {c['loo_original']:>10.5f} "
            f"{c['loo_duplicate']:>10.5f}"
        )
    b = rec["baseline_shapley"][rec["injected_source"]]
    lines.append("")
    lines.append(f"pre-injection phi_{rec['injected_source']} = {b:.5f}; "
                 f"pre-injection LOO = {rec['baseline_loo'][rec['injected_source']]:.5f}")
    return "\n".join(lines)
