"""Blocked retirement: does the LOO-versus-Shapley claim survive a causal split?

The main study splits leave-last-out WITHIN each user, which is standard but
not globally causal: `data_preparation/audit_global_time.py` measures up to 44% of
pooled training events postdating the median test event. The paper's central
operational claim is about retirement (LOO tracks removal cost, Shapley does
not), so that claim in particular needs checking under a globally blocked
split, where nothing is fitted on the future.

`run_global_timeblock.py --retirement` does this by handing the blocked state
to the same `retirement_simulation` the main study uses. These tests pin the
plumbing -- especially the duck-typed experiment, which is the fragile part,
since a stale attribute there would silently mix the blocked split with
leave-last-out state and produce a plausible wrong number.
"""
from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

for _d in ("scripts", "experiments"):          # flat repo, grouped release
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / _d))

from signalshap.config import SOURCES, FrozenConfig       # noqa: E402
from signalshap.data.loaders import Dataset               # noqa: E402

import run_global_timeblock as G                          # noqa: E402


def _overlapping_corpus(n_users=60, n_items=40, per_user=14, seed=0) -> Dataset:
    """A corpus whose users share a calendar window.

    The synthetic fixture gives each user a disjoint time window, so a single
    global cutoff retains nobody and the blocked split is undefined for it --
    the script raises on exactly that. Real corpora overlap, so the test needs
    a corpus that does too.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for u in range(n_users):
        ts = np.sort(rng.integers(0, 10_000, size=per_user))
        items = rng.choice(n_items, size=per_user, replace=False)
        for t, i in zip(ts, items):
            rows.append((u, int(i), int(t)))
    df = pd.DataFrame(rows, columns=["user", "item", "timestamp"])
    df = df.sort_values(["user", "timestamp"], kind="mergesort").reset_index(drop=True)
    df["original_record_index"] = np.arange(len(df))

    last = df.groupby("user", as_index=False).tail(1)
    rest = df.drop(last.index)
    val = rest.groupby("user", as_index=False).tail(1)
    train = rest.drop(val.index)

    meta = pd.DataFrame({
        "item": range(n_items),
        "tags": [f"g{i % 5} g{i % 7}" for i in range(n_items)],
    })
    return Dataset(
        name="blocked_fixture",
        train=train.reset_index(drop=True),
        valid=val.reset_index(drop=True),
        test=last.reset_index(drop=True),
        n_users=n_users, n_items=n_items, item_meta=meta, synthetic=True,
    )


def test_the_duck_typed_experiment_supplies_every_attribute_read():
    """A field added to the estimands code must not silently read stale state."""
    from signalshap.experiments import estimands

    src = inspect.getsource(estimands)
    used = set(re.findall(r"\bexp\.([a-zA-Z_]\w*)", src))
    provided = set(G._BlockedExperiment.__slots__)
    missing = used - provided
    assert not missing, (
        f"retirement_simulation/coalition_retrieval_game read {sorted(missing)} "
        f"off the experiment, which _BlockedExperiment does not supply")


def test_global_split_is_causal_and_loses_coverage():
    ds = _overlapping_corpus()
    blocked, stats = G.global_split(ds)

    assert stats["users_retained"] > 0
    # The property the whole exercise exists for.
    assert stats["train_events_after_any_test_event"] == 0
    t_train = blocked.train["timestamp"].to_numpy()
    t_test = blocked.test["timestamp"].to_numpy()
    assert t_train.max() <= t_test.min()
    # And the price it pays.
    assert stats["users_retained"] < stats["users_original"]
    # One held-out event per user per fold.
    assert blocked.valid["user"].is_unique
    assert blocked.test["user"].is_unique


def test_validation_precedes_test_for_every_retained_user():
    ds = _overlapping_corpus()
    blocked, _ = G.global_split(ds)
    v = blocked.valid.set_index("user")["timestamp"]
    t = blocked.test.set_index("user")["timestamp"]
    common = v.index.intersection(t.index)
    assert len(common)
    assert (v.loc[common] < t.loc[common]).all()


def test_blocked_retirement_runs_and_reports_the_contrast(monkeypatch):
    """End to end on a small overlapping corpus, with --retirement semantics."""
    ds = _overlapping_corpus()
    cfg = FrozenConfig.load()
    monkeypatch.setitem(cfg.n_max, "blocked_fixture", 25)
    monkeypatch.setattr(
        "signalshap.data.loaders.load_dataset",
        lambda name, seed=42, **kw: ds)

    r = G.run("blocked_fixture", cfg, seed=42, retirement=True)

    assert r["retirement"] is not None
    t = r["retirement"]
    for key in ("kendall_tau_loo_vs_truth", "kendall_tau_shapley_vs_truth",
                "true_retirement_loss", "cheapest_to_retire_true",
                "tau_advantage_loo_minus_shapley"):
        assert key in t
    assert t["blocked_split"] is True
    assert set(t["true_retirement_loss"]) == set(SOURCES)
    assert t["tau_advantage_loo_minus_shapley"] == pytest.approx(
        t["kendall_tau_loo_vs_truth"] - t["kendall_tau_shapley_vs_truth"])


def test_retirement_is_opt_in():
    """It costs extra retrieval passes, so it must not run by default."""
    ds = _overlapping_corpus()
    cfg = FrozenConfig.load()
    cfg.n_max["blocked_fixture"] = 25
    import signalshap.data.loaders as L
    orig = L.load_dataset
    L.load_dataset = lambda name, seed=42, **kw: ds
    try:
        r = G.run("blocked_fixture", cfg, seed=42)
    finally:
        L.load_dataset = orig
        cfg.n_max.pop("blocked_fixture", None)
    assert r["retirement"] is None
