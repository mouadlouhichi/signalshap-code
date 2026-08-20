#!/usr/bin/env python3
"""Do validation and test hold the same ITEM, not merely the same event?

    python data_preparation/audit_repeat_items.py --corpora ml_1m --budget-gb 24

The split takes each user's last interaction as test and the second-to-last as
validation. Those are distinct EVENTS, but nothing forces them to be distinct
ITEMS. If a user's last two events touch the same venue or product, the fusion
head is fitted with that item as the validation positive and then scored with
the same item as the test positive, so validation and test are not independent
targets for model selection. Repeat visits make this plausible on check-in
data.

A second case matters for the frozen-state argument: if the test item already
appears in training, `mask_seen` removes it from every candidate set and its
payoff is forced to zero regardless of any source's behaviour.

This reports both, per corpus, and the number of users affected. It measures;
it does not change the split.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np                                          # noqa: E402

from signalshap.config import write_artefact                # noqa: E402
from signalshap.memory import default_budget_gb, size_corpus  # noqa: E402


def audit(name: str, synthetic: bool = False) -> dict:
    from signalshap.data.loaders import load_dataset

    ds = load_dataset(name, synthetic=synthetic, seed=42)
    val = dict(zip(ds.valid["user"].to_numpy(), ds.valid["item"].to_numpy()))
    test = dict(zip(ds.test["user"].to_numpy(), ds.test["item"].to_numpy()))
    users = sorted(set(val) & set(test))

    same = [u for u in users if val[u] == test[u]]

    # Items each user already saw in training.
    seen: dict[int, set] = {}
    for u, i in zip(ds.train["user"].to_numpy(), ds.train["item"].to_numpy()):
        seen.setdefault(int(u), set()).add(int(i))
    test_in_train = [u for u in users if test[u] in seen.get(u, ())]
    val_in_train = [u for u in users if val[u] in seen.get(u, ())]

    # How repetitive is the corpus overall?
    import pandas as pd
    allev = pd.concat([ds.train, ds.valid, ds.test], ignore_index=True)
    pairs = len(allev)
    uniq = len(allev.drop_duplicates(["user", "item"]))

    n = max(len(users), 1)
    return {
        "dataset": name,
        "users_with_both_folds": len(users),
        "val_equals_test_item": len(same),
        "val_equals_test_pct": 100.0 * len(same) / n,
        "test_item_seen_in_train": len(test_in_train),
        "test_item_seen_in_train_pct": 100.0 * len(test_in_train) / n,
        "val_item_seen_in_train": len(val_in_train),
        "val_item_seen_in_train_pct": 100.0 * len(val_in_train) / n,
        "total_events": int(pairs),
        "distinct_user_item_pairs": int(uniq),
        "repeat_events": int(pairs - uniq),
        "repeat_event_pct": 100.0 * (pairs - uniq) / max(pairs, 1),
        "note": (
            "val_equals_test_item counts users whose held-out validation and "
            "test events name the SAME item, so the head is fitted on the "
            "target it is later scored against. test_item_seen_in_train counts "
            "users whose test item was already consumed in training, in which "
            "case mask_seen removes it from every candidate set and its payoff "
            "is zero for every coalition."),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpora", nargs="+", default=["ml_1m"])
    ap.add_argument("--budget-gb", type=float, default=None)
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    budget = default_budget_gb(a.budget_gb)
    out: dict = {}
    prior = Path("artefacts") / "repeat_item_audit.json"
    if prior.exists():
        try:
            out = json.loads(prior.read_text())
        except (json.JSONDecodeError, OSError):
            out = {}
    for name in a.corpora:
        from signalshap.data.loaders import LOADERS, _register_timestamped
        _register_timestamped()
        if not a.synthetic and name in ("gowalla_ts", "amazon_video_games"):
            size_corpus(name, LOADERS[name], budget, verbose=True)
        r = audit(name, a.synthetic)
        out[name] = r
        write_artefact("repeat_item_audit.json", out)
        print(f"{name}: val==test item {r['val_equals_test_item']} "
              f"({r['val_equals_test_pct']:.2f}%), test item already in train "
              f"{r['test_item_seen_in_train']} "
              f"({r['test_item_seen_in_train_pct']:.2f}%), repeat events "
              f"{r['repeat_event_pct']:.2f}%", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
