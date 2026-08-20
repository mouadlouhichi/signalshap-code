"""Three competing estimands for source credit (review Issues #5 and #7).

The reviewer's sharpest structural point: our game holds the candidate set
fixed at the union of ALL sources' top-N lists, so every coalition ranks items
that absent sources helped retrieve. That measures *ranking-stage* credit and
cannot justify an end-to-end retirement decision, because retiring a source in
production also removes its retrieved candidates.

Rather than argue the scope, we make the difference measurable. Three games:

  v_fixed(S)  the DEPLOYED head is held fixed and simply restricted to S.
              Answers: "what does this source contribute to the system as
              currently configured?"
  v_refit(S)  the head is refitted per coalition (our main game).
              Answers: "what does this source contribute when the fusion is
              allowed to adapt?" -- this mixes source value with
              reoptimisation value, which is a real interpretive cost.
  v_e2e(S)    each coalition retrieves its OWN candidates and refits.
              Answers: "what would we lose end-to-end if this source were
              removed?" -- the estimand the retirement decision needs.

Reporting all three lets a reader see which conclusions are estimand-specific.
"""

from __future__ import annotations

import numpy as np

from ..candidates.builder import build_candidates_for_user, candidate_recall
from ..config import SOURCES
from ..game.core import SignalShapGame, exact_shapley, ndcg_at_k


class FixedHeadGame(SignalShapGame):
    """Coalition game with the grand-coalition head held fixed.

    The head is fitted once on the full source set and then simply masked to
    the coalition; no refitting occurs. This isolates the source's direct
    contribution under the deployed fusion policy from the extra value that
    refitting recovers.
    """

    def _fit_weights(self, coalition: frozenset) -> np.ndarray:
        if not hasattr(self, "_grand_w"):
            self._grand_w = super()._fit_weights(frozenset(self.sources))
        w = np.zeros(len(self.sources))
        for i, g in enumerate(self.sources):
            if g in coalition:
                w[i] = self._grand_w[i]
        return w


def coalition_retrieval_game(exp, coalition: frozenset, n_max: int) -> dict:
    """Evaluate one coalition with its OWN candidate set (end-to-end).

    Candidates are rebuilt from only the sources present in the coalition, so
    a removed source no longer contributes retrieval. Returns the coalition
    value and the candidate recall it achieves, since recall now varies by
    coalition and is part of what the source contributes.
    """
    if not coalition:
        return {"v": 0.0, "utility": 0.0, "recall": 0.0}

    sub_scores = {g: exp.scores[g] for g in coalition}
    cands = [
        build_candidates_for_user(sub_scores, u, n_max)
        for u in range(exp.ds.n_users)
    ]
    game = SignalShapGame(
        sub_scores, cands, exp.valid_items, exp.test_items,
        ridge_lambda=exp.cfg.ridge_lambda, k_ndcg=exp.cfg.k_ndcg,
        v0_seed=exp.cfg.v0_seed, sources=tuple(sorted(coalition)),
    )
    return {
        # v is baseline-centred; utility is raw NDCG. Retirement loss must be
        # differenced on `utility`: each coalition retrieves its own candidate
        # set, so |C_u| and hence b_u differ, and differencing `v` adds a
        # baseline term that has nothing to do with the observed change.
        "v": game.v(frozenset(coalition)),
        "utility": game.utility(frozenset(coalition)),
        "recall": float(candidate_recall(cands, exp.test_items)),
        "mean_baseline": game.v0,
    }


def compare_estimands(exp, include_e2e: bool = True, verbose: bool = True) -> dict:
    """Compute Shapley values under all three estimands and compare rankings.

    The end-to-end game is far more expensive: it rebuilds candidates for every
    coalition rather than once, so it costs 2^n retrieval passes. It can be
    disabled on large corpora.
    """
    out: dict = {"dataset": exp.name}

    # 1. refitted head -- the paper's main game (already computed)
    phi_refit = exact_shapley(exp.v)
    out["refit_head"] = {"shapley": phi_refit, "v_grand": exp.v[frozenset(SOURCES)]}

    # 2. fixed deployed head
    if verbose:
        print("    [estimands] fixed-head game...", flush=True)
    fixed = FixedHeadGame(
        exp.scores, exp.candidates, exp.valid_items, exp.test_items,
        ridge_lambda=exp.cfg.ridge_lambda, k_ndcg=exp.cfg.k_ndcg,
        v0_seed=exp.cfg.v0_seed,
    )
    v_fixed = fixed.v_all()
    phi_fixed = exact_shapley(v_fixed)
    out["fixed_head"] = {"shapley": phi_fixed, "v_grand": v_fixed[frozenset(SOURCES)]}

    # 3. end-to-end: coalition-specific retrieval
    if include_e2e:
        if verbose:
            print("    [estimands] end-to-end game (2^n retrieval passes)...",
                  flush=True)
        from ..game.core import all_coalitions

        v_e2e, recalls = {}, {}
        for S in all_coalitions(SOURCES):
            r = coalition_retrieval_game(exp, S, exp.n_max)
            v_e2e[S] = r["v"]
            recalls[",".join(sorted(S)) or "empty"] = r["recall"]
        phi_e2e = exact_shapley(v_e2e)
        out["end_to_end"] = {
            "shapley": phi_e2e,
            "v_grand": v_e2e[frozenset(SOURCES)],
            "coalition_recall": recalls,
        }

    # rank agreement across estimands
    from scipy.stats import kendalltau

    def _rank(d):
        return [d[g] for g in SOURCES]

    pairs = {"refit_vs_fixed": ("refit_head", "fixed_head")}
    if include_e2e:
        pairs["refit_vs_e2e"] = ("refit_head", "end_to_end")
        pairs["fixed_vs_e2e"] = ("fixed_head", "end_to_end")

    out["agreement"] = {}
    for name, (a, b) in pairs.items():
        t = kendalltau(_rank(out[a]["shapley"]), _rank(out[b]["shapley"])).correlation
        out["agreement"][name] = {
            "kendall_tau": float(t) if np.isfinite(t) else 0.0,
            "top_source_a": max(out[a]["shapley"], key=out[a]["shapley"].get),
            "top_source_b": max(out[b]["shapley"], key=out[b]["shapley"].get),
        }

    out["note"] = (
        "refit_head mixes source value with the value of re-optimising the "
        "fusion; fixed_head isolates the deployed contribution; end_to_end is "
        "the only one that includes retrieval and therefore the only one that "
        "speaks to a retirement decision."
    )
    return out


def retirement_simulation(exp, verbose: bool = True) -> dict:
    """Do the attributions actually predict what removing a source costs?

    This is the decision experiment the reviewer asked for. For each source we
    remove it ENTIRELY -- from retrieval and from fusion -- rebuild candidates
    from the survivors, refit, and measure the true end-to-end NDCG loss. We
    then ask which attribution method ranks the sources in the order that loss
    implies.

    This is the test that would justify the paper's engineering motivation, and
    it is the one that can falsify it.
    """
    from scipy.stats import kendalltau

    from ..attribution.baselines import loo_attribution

    full = coalition_retrieval_game(exp, frozenset(SOURCES), exp.n_max)
    losses, recall_after = {}, {}
    losses_centred, baseline_shift = {}, {}
    for g in SOURCES:
        kept = frozenset(s for s in SOURCES if s != g)
        if verbose:
            print(f"    [retirement] removing {g}...", flush=True)
        r = coalition_retrieval_game(exp, kept, exp.n_max)
        # RAW utilities, not baseline-centred values (reviewer, round 6).
        losses[g] = full["utility"] - r["utility"]
        losses_centred[g] = full["v"] - r["v"]
        baseline_shift[g] = r["mean_baseline"] - full["mean_baseline"]
        recall_after[g] = r["recall"]

    phi = exact_shapley(exp.v)
    loo = loo_attribution(exp.v)
    order = list(SOURCES)
    true_vec = [losses[g] for g in order]

    def _tau(pred):
        t = kendalltau(true_vec, [pred[g] for g in order]).correlation
        return float(t) if np.isfinite(t) else 0.0

    cheapest_true = min(losses, key=losses.get)
    return {
        "dataset": exp.name,
        "v_full_e2e": full["v"],
        "utility_full_e2e": full["utility"],
        "recall_full": full["recall"],
        "true_retirement_loss": losses,
        "retirement_loss_centred_legacy": losses_centred,
        "baseline_shift_after_removal": baseline_shift,
        "baseline_contamination_note": (
            "true_retirement_loss now differences RAW utility. The legacy "
            "column differences baseline-centred v and equals the raw loss "
            "plus baseline_shift_after_removal, which is non-zero because "
            "retiring a source changes |C_u| and hence the expected-random "
            "baseline. Only the raw difference is the observed removal cost."),
        "recall_after_removal": recall_after,
        "shapley": phi,
        "loo": loo,
        "kendall_tau_shapley_vs_truth": _tau(phi),
        "kendall_tau_loo_vs_truth": _tau(loo),
        "cheapest_to_retire_true": cheapest_true,
        "cheapest_by_shapley": min(phi, key=phi.get),
        "cheapest_by_loo": min(loo, key=loo.get),
        "shapley_picks_correctly": min(phi, key=phi.get) == cheapest_true,
        "loo_picks_correctly": min(loo, key=loo.get) == cheapest_true,
        "note": (
            "True loss is measured END-TO-END: the retired source is removed "
            "from retrieval as well as fusion. Attribution methods are scored "
            "by rank agreement with that loss, which is the operational "
            "question the paper's motivation raises."
        ),
    }
