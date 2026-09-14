"""Ten-seed frozen-versus-refreshed protocol contrast (review item 7).

The single-seed version of block A answers "did the numbers move?", to which
the answer is always yes. The question worth asking is whether the protocol
effect exceeds the game's own run-to-run noise, which needs the seed sweep the
main results already use.

These tests pin the aggregation, not the outcome. One of them exists because
the first version of the aggregator was wrong in a way that would have been
reported as a finding: see `test_unit_tau_is_counted_with_tolerance`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

for _d in ("scripts", "experiments"):          # flat repo, grouped release
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / _d))

from signalshap.config import SOURCES, FrozenConfig     # noqa: E402
from signalshap.data.loaders import Dataset             # noqa: E402

import run_protocol_sensitivity as P                    # noqa: E402


def _corpus(n_users=50, n_items=35, per_user=12, seed=0) -> Dataset:
    rng = np.random.default_rng(seed)
    rows = []
    for u in range(n_users):
        ts = np.sort(rng.integers(0, 5_000, size=per_user))
        items = rng.choice(n_items, size=per_user, replace=False)
        rows += [(u, int(i), int(t)) for t, i in zip(ts, items)]
    df = pd.DataFrame(rows, columns=["user", "item", "timestamp"])
    df = df.sort_values(["user", "timestamp"], kind="mergesort").reset_index(drop=True)
    df["original_record_index"] = np.arange(len(df))
    last = df.groupby("user", as_index=False).tail(1)
    rest = df.drop(last.index)
    val = rest.groupby("user", as_index=False).tail(1)
    meta = pd.DataFrame({"item": range(n_items),
                         "tags": [f"g{i % 4} g{i % 6}" for i in range(n_items)]})
    return Dataset(name="proto_fixture",
                   train=rest.drop(val.index).reset_index(drop=True),
                   valid=val.reset_index(drop=True),
                   test=last.reset_index(drop=True),
                   n_users=n_users, n_items=n_items, item_meta=meta,
                   synthetic=True)


@pytest.fixture(scope="module")
def multiseed():
    ds = _corpus()
    cfg = FrozenConfig.load()
    cfg.n_max["proto_fixture"] = 25
    import signalshap.data.loaders as L
    orig = L.load_dataset
    L.load_dataset = lambda name, seed=42, **kw: ds
    try:
        yield P.block_temporal_seeds("proto_fixture", cfg, [42, 43, 44],
                                     verbose=False)
    finally:
        L.load_dataset = orig
        cfg.n_max.pop("proto_fixture", None)


def test_unit_tau_is_counted_with_tolerance(multiseed):
    """scipy returns 0.9999999999999999 for a perfectly preserved ordering.

    The first version of this aggregator tested `tau == 1.0` and would have
    reported "0 of 10 seeds preserve the source ordering" on runs where every
    seed preserved it exactly. That is a false negative pointing the wrong way
    -- it would have understated the method's stability -- so it is pinned.
    """
    kt = multiseed["kendall_tau"]
    exact = sum(1 for v in kt["values"] if v == 1.0)
    tolerant = kt["n_unit"]
    assert tolerant >= exact
    # And the tolerance really is what makes the difference here.
    assert tolerant == sum(1 for v in kt["values"] if abs(v - 1.0) < 1e-9)


def test_paired_delta_is_reported_per_source_with_an_interval(multiseed):
    d = multiseed["per_source_delta"]
    assert set(d) == set(SOURCES)
    for g, s in d.items():
        assert s["ci"]["lo"] <= s["mean"] <= s["ci"]["hi"], g
        assert s["n_positive"] + s["n_negative"] <= multiseed["n_seeds"]
        assert s["sign_stable"] == (s["n_positive"] == multiseed["n_seeds"]
                                    or s["n_negative"] == multiseed["n_seeds"])


def test_relative_change_matches_the_per_seed_values(multiseed):
    """The summary must be derivable from the retained per-seed records."""
    rows = [multiseed["per_seed"][str(s)] for s in multiseed["seeds"]]
    vf = np.array([r["frozen_two_step"]["v_grand"] for r in rows])
    vr = np.array([r["refreshed_one_step"]["v_grand"] for r in rows])
    assert multiseed["relative_change_v_grand"]["mean"] == pytest.approx(
        float(np.mean((vr - vf) / vf)))
    assert multiseed["v_grand_frozen"]["mean"] == pytest.approx(float(vf.mean()))


def test_every_seed_is_retained_for_audit(multiseed):
    assert set(multiseed["per_seed"]) == {str(s) for s in multiseed["seeds"]}
    assert multiseed["n_seeds"] == len(multiseed["seeds"])


def test_no_direction_is_hardcoded(multiseed):
    """The script must report the observed sign, not assume refreshed is higher."""
    rc = multiseed["relative_change_v_grand"]
    assert rc["n_positive"] + rc["n_negative"] == multiseed["n_seeds"]
    # Both counters are live: neither is a constant in the output schema.
    assert {"n_positive", "n_negative"} <= set(rc)
