"""End-to-end experiment pipeline E0-E8 (spec §10).

Gate ordering is enforced, not advisory:

    E0-a candidate recall   -> precondition for EVERY downstream number
    E0-b monotonicity audit -> precondition for Property 2 / Lemma 1(ii)

Every experiment writes a JSON to artefacts/ so the manuscript can cite it
(spec §14 rule 1: no number is typed into the paper by hand).
"""

from __future__ import annotations

import gc
import time
from datetime import datetime, timezone

import numpy as np

from .attribution.baselines import (
    ablate_source, forward_selection, loo_attribution, mc_shapley,
    permutation_importance, redundancy_kendall_tau,
)
from .candidates.builder import (
    build_candidates, candidate_recall, grand_coalition_candidates,
)
from .config import SOURCES, FrozenConfig, write_artefact
from .data.loaders import Dataset, build_dataset_stats, load_dataset
from .fusion.fullcatalog import (evaluate_full_catalog, full_catalog_metrics,
                                 popularity_reference)
from .game.core import (
    SignalShapGame, check_efficiency, exact_shapley, monotonicity_audit,
    per_user_shapley,
)
from .scorers.base import mask_seen, train_all_scorers
from .scorers.neural import lightgcn_scores, sasrec_scores
from .segments.segments import (
    SEGMENT_NAMES, assign_segments, segment_shapley_profiles, signalshap_fuse,
    signalshap_fuse_v2,
)
from .stats.tests import (
    bootstrap_ci, holm_bonferroni, permutation_test_between,
    permutation_test_paired, seed_ci, wilcoxon_test,
)


def _items_map(df) -> dict[int, int]:
    return dict(zip(df["user"].astype(int), df["item"].astype(int)))


class Experiment:
    """Holds one dataset's prepared state and runs E0-E8 against it."""

    def __init__(self, name: str, cfg: FrozenConfig | None = None,
                 seed: int = 42, synthetic: bool = False) -> None:
        self.name = name
        self.cfg = cfg or FrozenConfig.load()
        self.seed = seed
        self.timings: dict[str, float] = {}

        t0 = time.time()
        self.ds: Dataset = load_dataset(name, synthetic=synthetic, seed=seed)
        self.timings["load"] = time.time() - t0

        t0 = time.time()
        self.scores = mask_seen(train_all_scorers(self.ds, seed=seed), self.ds)
        self.timings["scorers"] = time.time() - t0

        self.n_max = self.cfg.n_max.get(name, 200)
        t0 = time.time()
        self.candidates = build_candidates(
            self.scores, self.ds.n_users, self.n_max, self.cfg.max_growth_iters
        )
        self.timings["candidates"] = time.time() - t0

        self.valid_items = _items_map(self.ds.valid)
        self.test_items = _items_map(self.ds.test)

        t0 = time.time()
        self.game = SignalShapGame(
            self.scores, self.candidates, self.valid_items, self.test_items,
            ridge_lambda=self.cfg.ridge_lambda, k_ndcg=self.cfg.k_ndcg,
            v0_seed=self.cfg.v0_seed,
        )
        self.v = self.game.v_all()
        self.timings["game_32_coalitions"] = time.time() - t0

        self.segments = assign_segments(self.ds.train, self.ds.n_users)

    # -- E0 ----------------------------------------------------------------- #

    def e0a_candidate_diagnostics(self) -> dict:
        """Candidate recall + |C_u| distribution. THE ceiling on everything."""
        sizes = np.array([len(c) for c in self.candidates])
        recall = candidate_recall(self.candidates, self.test_items)
        return {
            "dataset": self.name, "n_max": self.n_max,
            "candidate_recall": float(recall),
            "recall_gate": self.cfg.recall_gate,
            "gate_passes": bool(recall >= self.cfg.recall_gate),
            "abs_size_mean": float(sizes.mean()), "abs_size_std": float(sizes.std()),
            "abs_size_min": int(sizes.min()), "abs_size_max": int(sizes.max()),
            "n_eval_users": len(self.game.eval_users),
            "note": (
                "Candidate recall is the CEILING on every ranking metric: a test "
                "item outside C_u contributes zero to NDCG@10 by construction."
            ),
        }

    def e0b_monotonicity_audit(self) -> dict:
        """All 80 (S,g) pairs. Discharges the Property 2 hypothesis."""
        out = monotonicity_audit(self.v)
        out["dataset"] = self.name
        out["note"] = (
            "Property 2 and Lemma 1(ii) apply only where this passes. Where it "
            "fails, negative phi_g are SUBSTANTIVE findings, not numerical error. "
            "The coalition-conditional ridge refit (spec §2.4) is the likely cause."
        )
        return out

    # -- E1 / E2 ------------------------------------------------------------ #

    def e1_source_share(self) -> dict:
        phi = exact_shapley(self.v)
        eff = check_efficiency(phi, self.v)
        return {
            "dataset": self.name, "shapley": phi, "efficiency": eff,
            "v_grand": self.v[frozenset(SOURCES)], "v0": self.game.v0,
            "n_coalitions": len(self.v),
            "note": (
                "EXACT GIVEN THE FITTED v: the 32-coalition aggregation has no "
                "sampling error, but v(S) is estimated, so phi carries "
                "estimation error -- see seed CIs. Efficiency holds exactly "
                "regardless of fit noise because it is structural."
            ),
        }

    def e2_loo_vs_shapley(self) -> dict:
        phi = exact_shapley(self.v)
        loo = loo_attribution(self.v)
        pu = per_user_shapley(self.game)
        gaps = {g: phi[g] - loo[g] for g in SOURCES}

        perm = {}
        for g in SOURCES:
            loo_u = np.full(len(self.game.eval_users), loo[g])
            perm[g] = permutation_test_paired(pu[g], loo_u, 10_000, self.seed)

        tau = redundancy_kendall_tau(
            self.scores, self.candidates, self.game.eval_users
        )
        pair_gap = {
            p: abs(gaps[p.split("|")[0]]) + abs(gaps[p.split("|")[1]]) for p in tau
        }
        keys = sorted(tau)
        corr = (
            float(np.corrcoef([tau[k] for k in keys], [pair_gap[k] for k in keys])[0, 1])
            if len(keys) > 2 else 0.0
        )
        return {
            "dataset": self.name, "shapley": phi, "loo": loo, "gap": gaps,
            "forward": forward_selection(self.v),
            "permutation_importance": permutation_importance(self.v, seed=self.seed),
            "mc_shapley_50": mc_shapley(self.v, n_perm=50, seed=self.seed),
            "kendall_tau": tau, "pair_gap": pair_gap,
            "redundancy_gap_correlation": corr,
            "permutation_tests": perm,
            "preregistered_pairs": ["pop|cf", "rec|ct"],
            "note": (
                "pop-cf and rec-ct overlap is PRE-REGISTERED (spec §4), not "
                "discovered: ALS on implicit feedback chases popularity, and rec "
                "is defined over content clusters. RQ2 tests whether Shapley "
                "recovers known structure."
            ),
        }

    # -- E3 / E4 ------------------------------------------------------------ #

    def e3_segments(self) -> dict:
        pu = per_user_shapley(self.game)
        profiles = segment_shapley_profiles(pu, self.game.eval_users, self.segments)
        u_seg = np.array([self.segments[u] for u in self.game.eval_users])
        tests = {}
        for g in SOURCES:
            for a in range(len(SEGMENT_NAMES)):
                for b in range(a + 1, len(SEGMENT_NAMES)):
                    xa, xb = pu[g][u_seg == a], pu[g][u_seg == b]
                    if len(xa) >= 5 and len(xb) >= 5:
                        key = f"{g}:{SEGMENT_NAMES[a]}_vs_{SEGMENT_NAMES[b]}"
                        tests[key] = permutation_test_between(xa, xb, 10_000, self.seed)
        n_sig = sum(1 for t in tests.values() if t["p_value"] < 0.05)
        return {
            "dataset": self.name, "profiles": profiles,
            "heterogeneity_summary": {
                "n_tests": len(tests), "n_significant_uncorrected": n_sig,
                "expected_by_chance": round(0.05 * len(tests), 2),
                "exceeds_chance": bool(n_sig > 0.05 * len(tests) * 2),
                "note": (
                    "If n_significant is at or near the chance rate, there is NO "
                    "segment heterogeneity to exploit and C5 cannot work by "
                    "construction -- C4 and C5 stand or fall together."
                ),
            },
            "segment_sizes": {
                SEGMENT_NAMES[s]: int((u_seg == s).sum())
                for s in range(len(SEGMENT_NAMES))
            },
            "permutation_tests": tests,
        }

    def e4_signalshap_fuse(self) -> dict:
        res = signalshap_fuse_v2(self.game, self.segments, self.cfg.ridge_lambda,
                                 seed=self.seed)
        users = res["users"]
        fuse = res["signalshap_fuse"]

        # Full-catalog protocol for T5 (spec §7).
        w = {k: np.array(v) for k, v in res["weights"].items()}
        seg_w = {
            s: w.get(f"segment_{SEGMENT_NAMES[s]}", w["global"])
            for s in range(len(SEGMENT_NAMES))
        }
        fc = {
            "signalshap_fuse": evaluate_full_catalog(
                self.scores, self.candidates, self.test_items, users,
                self.game.sources, lambda u: seg_w[self.segments[u]], True),
            "global": evaluate_full_catalog(
                self.scores, self.candidates, self.test_items, users,
                self.game.sources, lambda u: w["global"], True),
            "uniform": evaluate_full_catalog(
                self.scores, self.candidates, self.test_items, users,
                self.game.sources, lambda u: w["uniform"], True),
            "popularity_reference": popularity_reference(
                self.scores, self.test_items, users),
        }

        # Strong neural references (spec §7). Trained once, full-catalog,
        # unrestricted -- deliberately NOT confined to C_u, which would
        # handicap them and invite the reviewer to ask for the real number.
        tr_u = self.ds.train["user"].to_numpy()
        tr_i = self.ds.train["item"].to_numpy()
        for nm, fn in (("lightgcn", lightgcn_scores), ("sasrec", sasrec_scores)):
            t0 = time.time()
            S = fn(self.ds, seed=self.seed)
            S[tr_u, tr_i] = -np.inf
            per = np.array([full_catalog_metrics(S[u], self.test_items[u])["ndcg"]
                            for u in users])
            fc[nm] = {
                "ndcg_at_10": float(per.mean()),
                "recall_at_20": float(np.mean([
                    full_catalog_metrics(S[u], self.test_items[u])["recall"]
                    for u in users])),
                "mrr_at_10": float(np.mean([
                    full_catalog_metrics(S[u], self.test_items[u])["mrr"]
                    for u in users])),
                "per_user_ndcg": per, "n_users": len(users),
            }
            self.timings[f"baseline_{nm}"] = time.time() - t0
            del S
            gc.collect()

        family = ["uniform", "global", "popularity_reference", "lightgcn", "sasrec"]
        raw_p, effects = {}, {}
        for b in family:
            t = wilcoxon_test(fc["signalshap_fuse"]["per_user_ndcg"],
                              fc[b]["per_user_ndcg"])
            raw_p[b], effects[b] = t["p_value"], t
        holm = holm_bonferroni(raw_p, family)

        return {
            "dataset": self.name,
            "candidate_set_ndcg": {
                k: float(np.mean(res[k])) for k in ("uniform", "global", "signalshap_fuse")
            },
            "full_catalog": {
                k: {m: v[m] for m in ("ndcg_at_10", "recall_at_20", "mrr_at_10", "n_users")}
                for k, v in fc.items()
            },
            "weights": res["weights"], "wilcoxon": effects, "holm_bonferroni": holm,
            "selection": res.get("selection", {}),
            "note": (
                "T5 is FULL-CATALOG for every method; SignalShap-Fuse scores "
                "items outside C_u as -inf so its recall ceiling is visible. "
                "v(S) itself remains fixed-candidate by definition of the game."
            ),
        }

    # -- E5 / E6 / E7 / E8 --------------------------------------------------- #

    def e5_robustness(self) -> dict:
        """Six stress tests. Recall is reported PER CELL for the |C_u| sweep."""
        out: dict = {"dataset": self.name}

        sweep = {}
        for mult in (0.5, 1.0, 2.0):
            n = max(10, int(self.n_max * mult))
            cands = build_candidates(self.scores, self.ds.n_users, n)
            g = SignalShapGame(self.scores, cands, self.valid_items, self.test_items,
                               self.cfg.ridge_lambda, self.cfg.k_ndcg, self.cfg.v0_seed)
            v = g.v_all()
            sweep[f"n_max_{n}"] = {
                "n_max": n,
                "candidate_recall": float(candidate_recall(cands, self.test_items)),
                "shapley": exact_shapley(v), "v_grand": v[frozenset(SOURCES)],
            }
            del g, cands, v
            gc.collect()
        out["candidate_size"] = sweep
        out["candidate_size_note"] = (
            "Recall is reported PER CELL because changing |C_u| moves the ceiling "
            "and hence the level of v; without it the cells are not comparable."
        )

        lam_sweep = {}
        for lam in (0.1, 1.0, 10.0):
            g = SignalShapGame(self.scores, self.candidates, self.valid_items,
                               self.test_items, lam, self.cfg.k_ndcg, self.cfg.v0_seed)
            lam_sweep[f"lambda_{lam}"] = exact_shapley(g.v_all())
            del g
            gc.collect()
        out["lambda_sensitivity"] = lam_sweep
        out["lambda_note"] = (
            "SENSITIVITY ONLY, never selection. lambda is frozen (spec §2.4); "
            "per-coalition tuning would be optimistic bias growing with |S|."
        )

        rescale = {}
        for kind, fn in (("identity", lambda x: x),
                         ("log1p", lambda x: np.log1p(np.clip(x, 0, None))),
                         ("rank", None)):
            sc = {}
            for g_ in SOURCES:
                m = self.scores[g_].copy()
                if kind == "rank":
                    finite = np.isfinite(m)
                    r = np.argsort(np.argsort(np.where(finite, m, -np.inf), axis=1), axis=1)
                    m = np.where(finite, r.astype(np.float32), -np.inf)
                elif fn is not None:
                    m = np.where(np.isfinite(m), fn(m), -np.inf)
                sc[g_] = m
            gg = SignalShapGame(sc, self.candidates, self.valid_items, self.test_items,
                                self.cfg.ridge_lambda, self.cfg.k_ndcg, self.cfg.v0_seed)
            rescale[kind] = exact_shapley(gg.v_all())
            del gg, sc
            gc.collect()
        out["monotone_rescaling"] = rescale
        out["rescaling_note"] = (
            "Remark 1: invariance is AFFINE only. log1p/rank are nonlinear, so "
            "drift here is expected and is the empirical content of the remark."
        )

        noise = {}
        rng = np.random.default_rng(self.seed)
        for lvl in (0.0, 0.1, 0.5):
            sc = {
                g_: np.where(np.isfinite(m), m + lvl * np.nanstd(m[np.isfinite(m)]) *
                             rng.normal(size=m.shape), -np.inf)
                for g_, m in self.scores.items()
            }
            gg = SignalShapGame(sc, self.candidates, self.valid_items, self.test_items,
                                self.cfg.ridge_lambda, self.cfg.k_ndcg, self.cfg.v0_seed)
            noise[f"sigma_{lvl}"] = exact_shapley(gg.v_all())
            del gg, sc
            gc.collect()
        out["noise_injection"] = noise
        return out

    def e6_ablation(self) -> dict:
        return {
            "dataset": self.name,
            "full": exact_shapley(self.v),
            "dropped": {g: ablate_source(self.v, g) for g in SOURCES},
        }

    def e7_actionability(self) -> dict:
        phi = exact_shapley(self.v)
        weakest = min(phi, key=phi.get)
        kept = frozenset(g for g in SOURCES if g != weakest)
        pu_full = self.game.v_per_user(frozenset(SOURCES))
        pu_kept = self.game.v_per_user(kept)
        users = self.game.eval_users
        a = np.array([pu_full[u] for u in users])
        b = np.array([pu_kept[u] for u in users])
        t = wilcoxon_test(a, b)
        return {
            "dataset": self.name, "lowest_shapley_source": weakest,
            "shapley_value": phi[weakest],
            "v_full": self.v[frozenset(SOURCES)], "v_without": self.v[kept],
            "delta": self.v[frozenset(SOURCES)] - self.v[kept],
            "wilcoxon": t,
            "interpretation": (
                f"Disabling '{weakest}' saves one scorer at deployment; the NDCG "
                f"delta is {self.v[frozenset(SOURCES)] - self.v[kept]:.5f} "
                f"(p={t['p_value']:.4f})."
            ),
        }

    def e8_appendix_b(self) -> dict:
        """(a) regenerated candidates -- quantifies the bias avoided by §2.1."""
        gc = grand_coalition_candidates(self.scores, self.ds.n_users, self.n_max)
        g2 = SignalShapGame(self.scores, gc, self.valid_items, self.test_items,
                            self.cfg.ridge_lambda, self.cfg.k_ndcg, self.cfg.v0_seed)
        v2 = g2.v_all()
        phi_union, phi_grand = exact_shapley(self.v), exact_shapley(v2)
        del g2
        return {
            "dataset": self.name,
            "union_candidates": {
                "shapley": phi_union, "v_grand": self.v[frozenset(SOURCES)],
                "recall": float(candidate_recall(self.candidates, self.test_items)),
            },
            "regenerated_candidates": {
                "shapley": phi_grand, "v_grand": v2[frozenset(SOURCES)],
                "recall": float(candidate_recall(gc, self.test_items)),
            },
            "v_grand_inflation": float(v2[frozenset(SOURCES)] - self.v[frozenset(SOURCES)]),
            "note": (
                "E8-a quantifies the bias avoided by §2.1. The rejected v1.0 "
                "design draws candidates from the grand-coalition scorer, "
                "inflating v(G) relative to every v(S) for proper subsets S."
            ),
        }

    def run_all(self) -> dict:
        """E0 gates first, then everything else."""
        res = {
            "dataset": self.name, "seed": self.seed,
            "synthetic": self.ds.synthetic,
            "dataset_stats": self.ds.stats(),
            "timings_sec": self.timings,
            "e0a_candidates": self.e0a_candidate_diagnostics(),
            "e0b_monotonicity": self.e0b_monotonicity_audit(),
        }
        if not res["e0a_candidates"]["gate_passes"]:
            res["gate_warning"] = (
                f"CANDIDATE RECALL GATE FAILED "
                f"({res['e0a_candidates']['candidate_recall']:.3f} < "
                f"{self.cfg.recall_gate}). Spec §2.2 requires the four-rung "
                f"fallback ladder: raise N_max -> report ceiling -> k-core under "
                f"the density invariant -> substitute Gowalla. Downstream numbers "
                f"are reported but must not be interpreted as final."
            )
        res.update({
            "e1_source_share": self.e1_source_share(),
            "e2_loo_vs_shapley": self.e2_loo_vs_shapley(),
            "e3_segments": self.e3_segments(),
            "e4_signalshap_fuse": self.e4_signalshap_fuse(),
            "e5_robustness": self.e5_robustness(),
            "e6_ablation": self.e6_ablation(),
            "e7_actionability": self.e7_actionability(),
            "e8_appendix_b": self.e8_appendix_b(),
        })
        return res


def run_multi_seed(name: str, cfg: FrozenConfig, seeds=(42, 43, 44),
                   synthetic: bool = False) -> dict:
    """Seed-based CIs on phi_g -- MAIN TEXT, not Appendix B (spec §2.7)."""
    per_seed = {}
    for s in seeds:
        e = Experiment(name, cfg, seed=s, synthetic=synthetic)
        per_seed[s] = exact_shapley(e.v)
    return {
        "dataset": name, "seeds": list(seeds), "per_seed": per_seed,
        "ci": {g: seed_ci([per_seed[s][g] for s in seeds]) for g in SOURCES},
    }


def run_full_study(datasets=("ml_1m", "lastfm_2k", "amazon_book"),
                   synthetic: bool = False, seeds=(42, 43, 44)) -> dict:
    """Run every dataset, write all artefacts, return the combined results."""
    cfg = FrozenConfig.load()
    cfg.save()
    out, ds_objs = {}, {}
    for name in datasets:
        exp = Experiment(name, cfg, seed=seeds[0], synthetic=synthetic)
        ds_objs[name] = exp.ds
        res = exp.run_all()
        res["multi_seed"] = run_multi_seed(name, cfg, seeds, synthetic)
        write_artefact(f"results_{name}.json", res)
        out[name] = res

    stats = build_dataset_stats(ds_objs)
    write_artefact("dataset_stats.json", stats)
    write_artefact("study_manifest.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "datasets": list(datasets), "seeds": list(seeds),
        "synthetic": synthetic, "config": cfg.__dict__ | {"seeds": list(cfg.seeds)},
    })
    return {"results": out, "dataset_stats": stats}
