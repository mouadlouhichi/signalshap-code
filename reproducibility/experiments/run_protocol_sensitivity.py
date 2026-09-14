#!/usr/bin/env python3
"""Two protocol sensitivity experiments a reviewer made mandatory.

    python experiments/run_protocol_sensitivity.py --corpora ml_1m --budget-gb 24

A. TEMPORAL STATE. The main protocol freezes the source state at the training
   fold, so the validation interaction is neither appended to the user's
   history nor masked before test scoring (Section 5). That is a two-step-ahead
   evaluation. This block builds the refreshed one-step-ahead alternative,
   where the validation event joins the history and is masked at test, and
   reports what changes. We do NOT assume a direction: an earlier draft claimed
   the frozen values were lower bounds, which is false once the refreshed state
   also moves the scores and the candidate set.

B. VALIDATION MISSES. The head is fitted on the validation indicator, so a user
   whose validation positive is unretrieved contributes an all-zero target: it
   adds a PSD block to A but nothing to c, which rotates as well as shrinks the
   solution. The main study retains those users. This block reports validation
   recall and refits with them dropped, so the sensitivity is measured rather
   than argued.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np                                          # noqa: E402
import pandas as pd                                         # noqa: E402
from scipy.stats import kendalltau                          # noqa: E402

from signalshap.candidates.builder import (                 # noqa: E402
    build_candidates, candidate_recall, validation_recall,
)
from signalshap.config import SOURCES, FrozenConfig, write_artefact  # noqa: E402
from signalshap.memory import (                            # noqa: E402
    check_paper_shape, default_budget_gb, size_corpus,
)
from signalshap.game.core import SignalShapGame, exact_shapley       # noqa: E402
from signalshap.scorers.base import mask_seen, train_all_scorers     # noqa: E402


def _items_map(df):
    return dict(zip(df["user"].to_numpy(), df["item"].to_numpy()))


def refreshed_dataset(ds):
    """Move the validation interaction into the training history.

    Sources are refitted on train + validation, so `seq`, `rec` and the decay
    term of `pop` all see the event they previously could not, and `mask_seen`
    then masks it out of the test ranking.
    """
    import copy
    out = copy.copy(ds)
    out.train = (pd.concat([ds.train, ds.valid], ignore_index=True)
                 .sort_values(["user", "timestamp", "original_record_index"],
                              kind="mergesort")
                 .reset_index(drop=True))
    return out


def _game_from(ds, cfg, n_max, seed):
    scores = mask_seen(train_all_scorers(ds, seed=seed), ds)
    cands = build_candidates(scores, ds.n_users, n_max, cfg.max_growth_iters)
    valid, test = _items_map(ds.valid), _items_map(ds.test)
    g = SignalShapGame(scores, cands, valid, test,
                       ridge_lambda=cfg.ridge_lambda, k_ndcg=cfg.k_ndcg,
                       v0_seed=cfg.v0_seed)
    return g, cands, valid, test


def _two_state_game(ds, cfg, n_max, seed):
    """Refreshed one-step-ahead: fit in the validation state, score in the test state.

    Naively refitting everything on train+val does NOT work, and the first
    version of this script got it wrong: `mask_seen` then masks the validation
    item, the fitting target vanishes for every user, and the head is fitted on
    an all-zero right-hand side. The two folds need two states.

      validation state: history = train,        target = val
      test state:       history = train + val,  target = test

    The Gram matrix comes from the validation state and the coalition values
    from the test state, so the head never sees the event it is evaluated after.
    """
    from signalshap.game.core import all_coalitions

    val_scores = mask_seen(train_all_scorers(ds, seed=seed), ds)
    val_cands = build_candidates(val_scores, ds.n_users, n_max,
                                 cfg.max_growth_iters)
    ds_te = refreshed_dataset(ds)
    te_scores = mask_seen(train_all_scorers(ds_te, seed=seed), ds_te)
    te_cands = build_candidates(te_scores, ds_te.n_users, n_max,
                                cfg.max_growth_iters)

    valid, test = _items_map(ds.valid), _items_map(ds.test)
    fit = SignalShapGame(val_scores, val_cands, valid, valid,
                         ridge_lambda=cfg.ridge_lambda, k_ndcg=cfg.k_ndcg,
                         v0_seed=cfg.v0_seed)
    ev = SignalShapGame(te_scores, te_cands, valid, test,
                        ridge_lambda=cfg.ridge_lambda, k_ndcg=cfg.k_ndcg,
                        v0_seed=cfg.v0_seed)

    # Transplant the validation-state head into the test-state evaluator.
    ev._gram_cache = fit._gram()
    ev._cache = {}
    v = {S: ev.v(S) for S in all_coalitions(SOURCES)}
    return v, te_cands, test


def block_temporal(name, cfg, seed=42):
    from signalshap.data.loaders import load_dataset
    G = frozenset(SOURCES)
    ds = load_dataset(name, seed=seed)
    n_max = cfg.n_max[name]

    frozen, cands_f, valid_f, test_f = _game_from(ds, cfg, n_max, seed)
    v_f = frozen.v_all()
    phi_f = exact_shapley(v_f)

    v_r, cands_r, test_r = _two_state_game(ds, cfg, n_max, seed)
    shape = (ds.n_users, ds.n_items)
    phi_r = exact_shapley(v_r)

    order = list(SOURCES)
    a = [phi_f[g] for g in order]
    b = [phi_r[g] for g in order]
    tau = kendalltau(a, b).correlation
    return {
        "dataset": name, "seed": seed, "corpus_shape": shape,
        "frozen_two_step": {"shapley": phi_f, "v_grand": v_f[G],
                            "test_recall": candidate_recall(cands_f, test_f)},
        "refreshed_one_step": {"shapley": phi_r, "v_grand": v_r[G],
                               "test_recall": candidate_recall(cands_r, test_r)},
        "kendall_tau": float(tau) if np.isfinite(tau) else None,
        "max_abs_delta_phi": float(max(abs(x - y) for x, y in zip(a, b))),
        "sign_agreement": bool(all((x > 0) == (y > 0) for x, y in zip(a, b))),
        "top_frozen": order[int(np.argmax(a))],
        "top_refreshed": order[int(np.argmax(b))],
        "v_grand_direction": ("refreshed higher" if v_r[G] > v_f[G]
                              else "frozen higher"),
        "note": ("Refreshed fits the head in the validation state (history = "
                 "train) and scores coalitions in the test state (history = "
                 "train + val, so the consumed validation item is masked and "
                 "seq/rec/pop see it). v(G) is NOT ordered a priori between the "
                 "two protocols: the refreshed state moves the source scores and "
                 "the candidate set as well as removing the consumed item. This "
                 "reports the observed direction only."),
    }


def block_validation_miss(name, cfg, seed=42):
    from signalshap.data.loaders import load_dataset
    G = frozenset(SOURCES)
    ds = load_dataset(name, seed=seed)
    n_max = cfg.n_max[name]
    game, cands, valid, test = _game_from(ds, cfg, n_max, seed)
    vr = validation_recall(cands, valid)

    phi_keep = exact_shapley(game.v_all())

    # Drop users whose validation positive is unretrieved, then refit.
    kept = {u: i for u, i in valid.items()
            if u < len(cands) and len(cands[u]) and i in set(cands[u].tolist())}
    scores = mask_seen(train_all_scorers(ds, seed=seed), ds)
    dropped = SignalShapGame(scores, cands, kept, test,
                             ridge_lambda=cfg.ridge_lambda, k_ndcg=cfg.k_ndcg,
                             v0_seed=cfg.v0_seed)
    phi_drop = exact_shapley(dropped.v_all())

    order = list(SOURCES)
    a = [phi_keep[g] for g in order]
    b = [phi_drop[g] for g in order]
    return {
        "dataset": name, "seed": seed, **vr,
        "shapley_retaining_misses": phi_keep,
        "shapley_dropping_misses": phi_drop,
        "kendall_tau": float(kendalltau(a, b).correlation),
        "max_abs_delta_phi": float(max(abs(x - y) for x, y in zip(a, b))),
        "sign_agreement": bool(all((x > 0) == (y > 0) for x, y in zip(a, b))),
        "note": ("Users whose validation positive is outside C_u contribute a "
                 "PSD block to A but nothing to c, which can rotate as well as "
                 "shrink the ridge solution. The main study retains them; this "
                 "measures what dropping them does."),
    }


def block_temporal_seeds(name, cfg, seeds, verbose: bool = True) -> dict:
    """Block A across seeds, so the protocol effect gets an interval.

    The single-seed version answers "did the numbers move?" and the honest
    answer to that is always yes. The question worth asking is whether the
    MOVEMENT is larger than the run-to-run noise of the game itself, and that
    needs the same seed sweep the main results use.

    Paired by seed: the frozen and refreshed games share the corpus, the
    split, and the scorer seed, so the difference is attributable to the
    protocol and a paired interval is the right summary. Intervals are
    percentile bootstrap over seeds rather than t_9, because the ratio and
    Kendall-tau statistics here are bounded and t intervals on them ran past
    the admissible range (spec entry: Kendall tau t_9 intervals exceeded 1.0).
    """
    from signalshap.stats.tests import bootstrap_ci

    per_seed, rows = {}, []
    for s in seeds:
        if verbose:
            print(f"    [temporal] seed {s}...", flush=True)
        r = block_temporal(name, cfg, s)
        per_seed[str(s)] = r
        rows.append(r)

    order = list(SOURCES)

    def _col(f):
        return np.array([f(r) for r in rows], dtype=float)

    v_f = _col(lambda r: r["frozen_two_step"]["v_grand"])
    v_r = _col(lambda r: r["refreshed_one_step"]["v_grand"])
    rel = (v_r - v_f) / np.where(np.abs(v_f) > 0, v_f, np.nan)

    out = {
        "dataset": name,
        "seeds": list(seeds),
        "n_seeds": len(seeds),
        "per_seed": per_seed,
        "v_grand_frozen": {"mean": float(v_f.mean()), "sd": float(v_f.std(ddof=1))},
        "v_grand_refreshed": {"mean": float(v_r.mean()), "sd": float(v_r.std(ddof=1))},
        "relative_change_v_grand": {
            "mean": float(np.nanmean(rel)),
            "ci": bootstrap_ci(rel[~np.isnan(rel)]),
            "n_positive": int((rel > 0).sum()),
            "n_negative": int((rel < 0).sum()),
        },
        "kendall_tau": {
            "values": [r["kendall_tau"] for r in rows],
            "mean": float(np.mean([r["kendall_tau"] for r in rows])),
            # Tolerance, not equality: a perfectly preserved ordering comes
            # back from scipy as 0.9999999999999999, so `== 1.0` reported
            # "0 of 10 seeds agree" when in fact all ten did.
            "n_unit": int(sum(1 for r in rows
                              if abs(r["kendall_tau"] - 1.0) < 1e-9)),
        },
        "top_source_frozen": {r["top_frozen"] for r in rows},
        "top_source_refreshed": {r["top_refreshed"] for r in rows},
        "n_seeds_top_source_changes": int(
            sum(1 for r in rows if r["top_frozen"] != r["top_refreshed"])),
        "sign_agreement_all_seeds": bool(all(r["sign_agreement"] for r in rows)),
    }

    # Per-source paired delta, which is what a reader needs to judge whether
    # any individual attribution is protocol-robust.
    out["per_source_delta"] = {}
    for g in order:
        d = np.array([r["refreshed_one_step"]["shapley"][g]
                      - r["frozen_two_step"]["shapley"][g] for r in rows])
        out["per_source_delta"][g] = {
            "mean": float(d.mean()),
            "sd": float(d.std(ddof=1)),
            "ci": bootstrap_ci(d),
            "n_positive": int((d > 0).sum()),
            "n_negative": int((d < 0).sum()),
            "sign_stable": bool((d > 0).all() or (d < 0).all()),
        }

    # Sets are not JSON-serialisable and, more usefully, a set collapses the
    # count a reader wants.
    out["top_source_frozen"] = sorted(out["top_source_frozen"])
    out["top_source_refreshed"] = sorted(out["top_source_refreshed"])
    out["note"] = (
        "Ten-seed version of the frozen-versus-refreshed protocol contrast. "
        "Paired by seed: both protocols share the corpus, split and scorer "
        "seed, so the difference is the protocol. Percentile bootstrap over "
        "seeds; no direction is assumed a priori, because the refreshed state "
        "moves the source scores, the candidate set and the baseline as well "
        "as removing the consumed validation item.")
    return out


def _size(name: str, budget: float) -> None:
    """Install the memory-derived user cap BEFORE loading a large corpus.

    This was missing in the first version: --budget-gb was accepted and then
    ignored, so a Gowalla run loaded the full 52,985 x 121,866 corpus instead
    of the sized 8,865 x 82,134 and was killed. The flag looked honoured
    because the argument parsed.
    """
    from signalshap.data.loaders import LOADERS, _register_timestamped
    _register_timestamped()
    if name in ("gowalla_ts", "amazon_video_games"):
        size_corpus(name, LOADERS[name], budget, verbose=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpora", nargs="+", default=["ml_1m"])
    ap.add_argument("--budget-gb", type=float, default=None)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--seeds", type=int, nargs="+", default=None,
                    help="run block A across these seeds and report a paired "
                         "interval (review item 7). Default is the single "
                         "--seed run.")
    a = ap.parse_args()
    cfg = FrozenConfig.load()
    budget = default_budget_gb(a.budget_gb)
    print(f"budget {budget:.1f} GB | corpora {a.corpora}", flush=True)
    # Resume from what is already on disk. Starting from {} meant running one
    # corpus silently deleted the others: a --corpora gowalla_ts pass wiped the
    # ml_1m and amazon results. This is the same non-resumable bug that once
    # cost eight hours in block_seeds, reintroduced here.
    out: dict = {}
    prior = Path("artefacts") / "protocol_sensitivity.json"
    if prior.exists():
        try:
            out = json.loads(prior.read_text())
            if out:
                print(f"  resuming; already have {sorted(out)}", flush=True)
        except (json.JSONDecodeError, OSError):
            out = {}
    for name in a.corpora:
        _size(name, budget)
        print(f"== {name}: temporal state", flush=True)
        t = block_temporal(name, cfg, a.seed)
        shape = t.get("corpus_shape")
        if shape:
            ok, why = check_paper_shape(name, *shape)
            if not ok:
                raise SystemExit("REFUSING to report a resized corpus.\n  " + why)
        out.setdefault(name, {})["temporal"] = t
        write_artefact("protocol_sensitivity.json", out)
        print(f"   tau={t['kendall_tau']:.2f} maxdelta={t['max_abs_delta_phi']:.2e} "
              f"top {t['top_frozen']}->{t['top_refreshed']}", flush=True)

        if a.seeds:
            print(f"== {name}: temporal state across {len(a.seeds)} seeds",
                  flush=True)
            ms = block_temporal_seeds(name, cfg, a.seeds)
            out[name]["temporal_seeds"] = ms
            write_artefact("protocol_sensitivity.json", out)
            rc = ms["relative_change_v_grand"]
            print(f"   v(G) relative change {rc['mean']:+.1%} "
                  f"[{rc['ci']['lo']:+.1%}, {rc['ci']['hi']:+.1%}], "
                  f"{rc['n_positive']}/{ms['n_seeds']} seeds positive; "
                  f"tau mean {ms['kendall_tau']['mean']:.2f}, "
                  f"top source changes on {ms['n_seeds_top_source_changes']}"
                  f"/{ms['n_seeds']} seeds", flush=True)

        print(f"== {name}: validation misses", flush=True)
        out[name]["validation_miss"] = block_validation_miss(name, cfg, a.seed)
        write_artefact("protocol_sensitivity.json", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
