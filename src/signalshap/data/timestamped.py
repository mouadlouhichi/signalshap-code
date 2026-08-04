"""Loaders for corpora that carry real timestamps (review Critical Issue #1).

Three of five players (`rec`, `seq`, and the decay term of `pop`) are
meaningless without interaction times. The LightGCN benchmark splits discard
timestamps, so the earlier runs substituted file order, which the reviewer
correctly called uninterpretable rather than merely noisy.

These loaders read corpora in their ORIGINAL timestamped form. Gowalla is the
useful case: the LightGCN split is derived from a check-in log that does have
times, so using the source recovers temporal validity while keeping continuity
with published preprocessing.

Every loader here refuses to fall back to synthetic data: a missing corpus
raises, so a temporal claim can never be silently built on file order.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .loaders import SCHEMA, Dataset, _finalise, find_raw


def _require(folder: str, *names: str) -> Path:
    base = find_raw(folder, *names)
    if base is None:
        raise FileNotFoundError(
            f"{folder} not found. Timestamped corpora are never faked: place "
            f"the raw files under data/raw/{folder}/ and re-run."
        )
    return base


def _k_core(df: pd.DataFrame, k: int = 10, max_iter: int = 20) -> pd.DataFrame:
    """Iterative k-core, the standard filter for these corpora."""
    cur = df
    for _ in range(max_iter):
        uc = cur["user"].value_counts()
        ic = cur["item"].value_counts()
        nxt = cur[cur["user"].map(uc).ge(k) & cur["item"].map(ic).ge(k)]
        if len(nxt) == len(cur):
            break
        cur = nxt
    return cur


# --------------------------------------------------------------------------- #
# Gowalla -- check-ins with real timestamps (SNAP loc-gowalla)
# --------------------------------------------------------------------------- #


def load_gowalla_timestamped(path: Path | None = None, k_core: int = 10,
                             max_users: int | None = None,
                             seed: int = 42) -> Dataset:
    """Gowalla check-ins: user, ISO time, lat, lon, location id (TSV).

    File: ``loc-gowalla_totalCheckins.txt`` from SNAP. This is the source the
    LightGCN split was built from, so using it keeps the corpus comparable
    while restoring the temporal ordering that `rec` and `seq` require.
    """
    base = _require("gowalla_ts", "gowalla-checkins", "loc-gowalla")
    f = next((p for p in base.rglob("*totalCheckins*")), None)
    if f is None:
        raise FileNotFoundError(f"loc-gowalla_totalCheckins.txt not under {base}")

    df = pd.read_csv(f, sep="\t", header=None,
                     names=["user", "time", "lat", "lon", "item"])
    df["timestamp"] = pd.to_datetime(df["time"], errors="coerce").astype("int64") // 10**9
    df = df[df["timestamp"] > 0][["user", "item", "timestamp"]]
    df = _k_core(df, k_core)
    return _prepare(df, "gowalla_ts", max_users, seed)


# --------------------------------------------------------------------------- #
# Amazon Reviews -- timestamped, any category
# --------------------------------------------------------------------------- #


def load_amazon_timestamped(category: str = "Video_Games",
                            path: Path | None = None, k_core: int = 10,
                            max_users: int | None = None,
                            seed: int = 42) -> Dataset:
    """Amazon Reviews (2018 or 2023) for one category.

    Accepts either the CSV form (``user,item,rating,timestamp``) or the
    JSONL form with ``user_id``/``parent_asin``/``timestamp``. Ratings of 4+
    are treated as positive implicit feedback, matching the MovieLens protocol.
    """
    base = _require(f"amazon_{category}", "amazon_reviews", "amazon_ts")
    csv = next((p for p in base.rglob("*.csv")), None)
    jsonl = next((p for p in base.rglob("*.jsonl*")), None)

    if csv is not None:
        df = pd.read_csv(csv, header=None,
                         names=["user", "item", "rating", "timestamp"])
    elif jsonl is not None:
        df = pd.read_json(jsonl, lines=True)
        df = df.rename(columns={"user_id": "user", "parent_asin": "item"})
        if "asin" in df and "item" not in df:
            df = df.rename(columns={"asin": "item"})
    else:
        raise FileNotFoundError(f"no .csv or .jsonl under {base}")

    if "rating" in df:
        df = df[df["rating"] >= 4.0]
    df = df[["user", "item", "timestamp"]].dropna()
    # 2023 dump uses milliseconds
    if df["timestamp"].max() > 1e12:
        df["timestamp"] = df["timestamp"] // 1000
    df = _k_core(df, k_core)
    return _prepare(df, f"amazon_{category.lower()}", max_users, seed)


# --------------------------------------------------------------------------- #
# Last.fm 1K -- listening events with timestamps
# --------------------------------------------------------------------------- #


def load_lastfm_1k(path: Path | None = None, k_core: int = 10,
                   max_users: int | None = None, seed: int = 42) -> Dataset:
    """Last.fm-1K listening events (user, ISO timestamp, artist id, ...).

    Genuinely sequential data, which makes it the strongest test of the `seq`
    and `rec` players.
    """
    base = _require("lastfm_1k", "lastfm-1K", "lastfm-dataset-1K")
    f = next((p for p in base.rglob("*userid-timestamp*")), None)
    if f is None:
        raise FileNotFoundError(f"userid-timestamp-artid... not under {base}")

    df = pd.read_csv(f, sep="\t", header=None, quoting=3,
                     names=["user", "time", "artid", "artname",
                            "traid", "traname"],
                     usecols=["user", "time", "artid"])
    df = df.rename(columns={"artid": "item"}).dropna()
    df["timestamp"] = pd.to_datetime(df["time"], errors="coerce",
                                     utc=True).astype("int64") // 10**9
    df = df[df["timestamp"] > 0][["user", "item", "timestamp"]]
    df = df.drop_duplicates(["user", "item"])   # implicit feedback
    df = _k_core(df, k_core)
    return _prepare(df, "lastfm_1k", max_users, seed)


# --------------------------------------------------------------------------- #
# shared preparation
# --------------------------------------------------------------------------- #


def _prepare(df: pd.DataFrame, name: str, max_users: int | None,
             seed: int) -> Dataset:
    if max_users:
        rng = np.random.default_rng(seed)
        uniq = df["user"].unique()
        if len(uniq) > max_users:
            keep = set(rng.choice(uniq, max_users, replace=False).tolist())
            df = df[df["user"].isin(keep)]

    df = df.sort_values(["user", "timestamp"], kind="mergesort").reset_index(drop=True)
    df["original_record_index"] = np.arange(len(df))
    ds = _finalise(df[SCHEMA], name, None, synthetic=False)
    ds.no_timestamps = False           # the whole point of this module
    return ds


TIMESTAMPED_LOADERS = {
    "gowalla_ts": load_gowalla_timestamped,
    "lastfm_1k": load_lastfm_1k,
    "amazon_video_games": lambda **kw: load_amazon_timestamped("Video_Games", **kw),
    "amazon_books_ts": lambda **kw: load_amazon_timestamped("Books", **kw),
}


def temporal_validity_report(ds: Dataset) -> dict:
    """Confirm a corpus really carries usable time before running the game.

    Catches the failure mode that produced the withdrawn results: a corpus that
    looks fine but whose 'timestamps' are a positional index.
    """
    all_df = pd.concat([ds.train, ds.valid, ds.test])
    t = all_df["timestamp"].to_numpy()
    n_unique = len(np.unique(t))
    per_user_span = (
        all_df.groupby("user")["timestamp"].agg(lambda x: x.max() - x.min())
    )
    monotone_index = bool(np.array_equal(np.sort(t), np.arange(t.min(), t.min() + len(t))))
    return {
        "dataset": ds.name,
        "n_interactions": int(len(all_df)),
        "n_unique_timestamps": int(n_unique),
        "unique_fraction": float(n_unique / max(len(all_df), 1)),
        "span_days": float((t.max() - t.min()) / 86400.0),
        "median_user_span_days": float(per_user_span.median() / 86400.0),
        "looks_like_positional_index": monotone_index,
        "temporally_valid": bool(
            not monotone_index and n_unique > 0.01 * len(all_df)
            and (t.max() - t.min()) > 86400 * 30
        ),
        "note": (
            "temporally_valid must be True before rec/seq/pop-decay "
            "attributions are interpreted. A positional index passes a naive "
            "check but carries no temporal information."
        ),
    }
