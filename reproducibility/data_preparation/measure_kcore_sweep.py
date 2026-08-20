#!/usr/bin/env python3
"""Week-1 obligation (spec §6.2): measure real k-core retention and density.

The k-core table in §6.2 is PLACEHOLDER. Until this script has run,
tests/test_density_ordering.py::test_kcore_sweep_is_measured_not_estimated
blocks rung 3 of the fallback ladder -- no filter decision may rest on
estimates nobody checked against the corpus.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from signalshap.config import write_artefact
from signalshap.data.loaders import corpus_hash, load_dataset


def k_core(df: pd.DataFrame, k: int) -> pd.DataFrame:
    """Iteratively drop users and items with fewer than k interactions."""
    cur = df
    while True:
        uc, ic = cur["user"].value_counts(), cur["item"].value_counts()
        nxt = cur[cur["user"].map(uc).ge(k) & cur["item"].map(ic).ge(k)]
        if len(nxt) == len(cur):
            return nxt
        cur = nxt


if __name__ == "__main__":
    synthetic = "--synthetic" in sys.argv
    out = {}
    for name in ("amazon_book", "lastfm_2k", "ml_1m"):
        ds = load_dataset(name, synthetic=synthetic)
        full = pd.concat([ds.train, ds.valid, ds.test])
        per = {}
        for k in (0, 3, 5, 8, 10, 20):
            sub = full if k == 0 else k_core(full, k)
            u, i = sub["user"].nunique(), sub["item"].nunique()
            per[f"k={k}"] = {
                "users": int(u), "items": int(i), "interactions": int(len(sub)),
                "density": float(len(sub) / (u * i)) if u and i else 0.0,
            }
        out[name] = per
        print(f"{name}: " + "  ".join(
            f"k={k.split('=')[1]}:{v['density']*100:.3f}%" for k, v in per.items()))

    out |= {
        "source": "measured",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "corpus_hash": corpus_hash(load_dataset("amazon_book", synthetic=synthetic)),
        "synthetic": synthetic,
    }
    print("->", write_artefact("kcore_sweep.json", out))
