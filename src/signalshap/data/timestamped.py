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

import os
from pathlib import Path

import numpy as np
import pandas as pd

from .loaders import SCHEMA, Dataset, _finalise, find_raw


def _to_epoch_seconds(series: pd.Series) -> pd.Series:
    """Datetime column -> Unix seconds, robust to the parsed resolution.

    pandas 2.x may return datetime64[s], [ms], or [us] depending on the input,
    so the common idiom ``.astype("int64") // 10**9`` is wrong for anything but
    nanoseconds -- on a [us] column it under-reports by 1000x. That failure is
    silent: the values still look like plausible epoch integers, but every
    recency and decay computation downstream is corrupted. We normalise to
    nanoseconds first.
    """
    t = pd.to_datetime(series, errors="coerce", utc=True)
    return (t.astype("datetime64[ns, UTC]").astype("int64") // 10**9)


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
    df["timestamp"] = _to_epoch_seconds(df["time"])
    df = df[df["timestamp"] > 0]
    geo = df[["item", "lat", "lon"]].dropna()
    df = df[["user", "item", "timestamp"]]
    df = _k_core(df, k_core)
    return _prepare(df, "gowalla_ts", max_users, seed,
                    meta_source=lambda kept: _gowalla_meta(geo, kept))


def _gowalla_meta(geo: pd.DataFrame, kept: pd.Series) -> pd.DataFrame:
    """Content tags for Gowalla venues from their coordinates.

    Gowalla has no item text, which previously left `ct` an all-zero matrix
    and `rec` with a single content cluster -- both players structurally dead
    (see scorers/audit.py). But the check-in file carries lat/lon, so venues do
    have content: WHERE they are. We bin coordinates onto a nested grid and
    emit one token per resolution, which gives TF-IDF a coarse-to-fine
    geographic vocabulary: venues in the same neighbourhood share the fine
    token, venues in the same metro share only the coarse one. That is the
    natural notion of venue similarity for a location service, and it makes
    `rec` mean "how recently did this user visit this area", which is a real
    recency signal rather than a constant.

    Grid steps are in degrees and fixed a priori (roughly 100 km / 10 km /
    1 km near the equator); they are not tuned against any outcome.

    Each resolution is emitted TWICE, on grids offset by half a step. A single
    grid makes similarity discontinuous at cell edges: two venues 500 m apart
    that straddle a boundary share no token at any resolution, which a unit
    test caught on a pair either side of longitude -74.0. With the offset copy,
    a boundary in one grid falls mid-cell in the other, so genuinely nearby
    venues always agree on at least one token per resolution.
    """
    pt = geo.groupby("item")[["lat", "lon"]].median()
    steps = ((1.0, "g1"), (0.1, "g2"), (0.01, "g3"))
    tags = {}
    for item, (lat, lon) in zip(pt.index, pt.to_numpy()):
        toks = []
        for step, label in steps:
            for off, otag in ((0.0, "a"), (0.5, "b")):
                toks.append(
                    f"{label}{otag}_{int(np.floor(lat / step + off))}_"
                    f"{int(np.floor(lon / step + off))}"
                )
        tags[item] = " ".join(toks)
    return pd.DataFrame({
        "item": kept.values,
        "tags": [tags.get(i, "") for i in kept.values],
    })


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
        # convert_dates=False is essential: pandas otherwise coerces the epoch
        # column to Timestamp objects, and the millisecond check below then
        # raises "'>' not supported between Timestamp and float".
        df = pd.read_json(jsonl, lines=True, convert_dates=False)
        df = df.rename(columns={"user_id": "user", "parent_asin": "item"})
        if "asin" in df and "item" not in df:
            df = df.rename(columns={"asin": "item"})
    else:
        raise FileNotFoundError(f"no .csv or .jsonl under {base}")

    if "rating" in df:
        df = df[df["rating"] >= 4.0]
    df = df[["user", "item", "timestamp"]].dropna()

    # Normalise the time column, which arrives in three shapes across the
    # Amazon dumps: epoch seconds (2018 CSV), epoch milliseconds (2023 JSONL),
    # or an already-parsed datetime if a reader coerced it.
    ts = df["timestamp"]
    if pd.api.types.is_datetime64_any_dtype(ts) or ts.map(
            lambda x: isinstance(x, pd.Timestamp)).any():
        df["timestamp"] = _to_epoch_seconds(ts)
    else:
        df["timestamp"] = pd.to_numeric(ts, errors="coerce")
        df = df.dropna(subset=["timestamp"])
        if not df.empty and df["timestamp"].max() > 1e12:
            df["timestamp"] = df["timestamp"] // 1000   # ms -> s
        df["timestamp"] = df["timestamp"].astype("int64")
    df = _k_core(df, k_core)
    return _prepare(df, f"amazon_{category.lower()}", max_users, seed,
                    meta_source=lambda kept: _amazon_meta(base, kept))


def _amazon_meta(base: Path, kept: pd.Series) -> pd.DataFrame:
    """Item tags from the Amazon product-metadata dump, when present.

    Without this, `ct` is an all-zero matrix and `rec` collapses to one
    cluster, so both players are structurally dead and their zero Shapley
    values say nothing about content (see scorers/audit.py). The metadata file
    is a separate download (``meta_<Category>.jsonl[.gz]``); if it is absent we
    return empty tags and let the audit raise, rather than pretending the
    corpus has no content signal.

    Tokens are the category path plus the store/brand, lowercased and
    whitespace-joined so the TF-IDF vectoriser's ``\\S+`` pattern treats each
    as one term. Title words are deliberately excluded: they are mostly model
    numbers and platform boilerplate, which inflate the vocabulary without
    adding a content axis.
    """
    f = next((p for p in base.rglob("meta_*.jsonl*")), None)
    if f is None:
        f = next((p for p in base.rglob("*meta*.json*")), None)
    if f is None:
        return pd.DataFrame({"item": kept.values, "tags": ""})

    want = set(kept.tolist())
    rows: dict[str, str] = {}
    for chunk in pd.read_json(f, lines=True, convert_dates=False,
                              chunksize=50_000):
        key = "parent_asin" if "parent_asin" in chunk else "asin"
        if key not in chunk:
            break
        chunk = chunk[chunk[key].isin(want)]
        for rec in chunk.to_dict("records"):
            toks = []
            cats = rec.get("categories") or rec.get("category") or []
            if isinstance(cats, str):
                cats = [cats]
            for c in cats:
                if isinstance(c, list):
                    toks += [str(x) for x in c]
                elif c is not None:
                    toks.append(str(c))
            for extra in ("store", "brand", "main_category"):
                val = rec.get(extra)
                if isinstance(val, str) and val.strip():
                    toks.append(val)
            clean = [t.strip().lower().replace(" ", "_") for t in toks if str(t).strip()]
            if clean:
                rows[rec[key]] = " ".join(clean)

    return pd.DataFrame({
        "item": kept.values,
        "tags": [rows.get(i, "") for i in kept.values],
    })


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
    df["timestamp"] = _to_epoch_seconds(df["time"])
    df = df[df["timestamp"] > 0][["user", "item", "timestamp"]]
    df = df.drop_duplicates(["user", "item"])   # implicit feedback
    df = _k_core(df, k_core)
    return _prepare(df, "lastfm_1k", max_users, seed)


# --------------------------------------------------------------------------- #
# shared preparation
# --------------------------------------------------------------------------- #


def _prepare(df: pd.DataFrame, name: str, max_users: int | None,
             seed: int, meta_source=None) -> Dataset:
    if max_users:
        rng = np.random.default_rng(seed)
        uniq = df["user"].unique()
        if len(uniq) > max_users:
            keep = set(rng.choice(uniq, max_users, replace=False).tolist())
            df = df[df["user"].isin(keep)]

    if df.empty:
        raise ValueError(
            f"{name}: no interactions survive preprocessing. The k-core filter "
            "is the usual cause on a small or heavily subsampled extract -- "
            "lower k_core, or check that the raw file is complete."
        )

    lo, hi = int(df["timestamp"].min()), int(df["timestamp"].max())
    # 1990-01-01 .. 2035-01-01, a generous but finite window
    if not (631152000 < lo and hi < 2051222400):
        raise ValueError(
            f"{name}: timestamps span {lo}..{hi}, which is not a plausible "
            "Unix-seconds range. This usually means a resolution mismatch "
            "(datetime64[us] divided by 1e9). Refusing to build temporal "
            "players on corrupted times."
        )

    df = df.sort_values(["user", "timestamp"], kind="mergesort").reset_index(drop=True)
    df["original_record_index"] = np.arange(len(df))

    # Build item metadata BEFORE _finalise reindexes, then relabel to the
    # contiguous ids _reindex will assign (sorted order of the raw ids). Doing
    # it after would silently misalign tags with items.
    meta = None
    if meta_source is not None:
        kept = pd.Series(sorted(df["item"].unique()))
        meta = meta_source(kept).copy()
        meta["item"] = np.arange(len(kept))

    ds = _finalise(df[SCHEMA], name, meta, synthetic=False)
    ds.no_timestamps = False           # the whole point of this module
    return ds


def _env_cap(explicit: int | None = None) -> int | None:
    """Resolve the user cap, honouring SIGNALSHAP_MAX_USERS.

    Experiment() constructs corpora through the registry with no arguments, so
    a loader that ignores this variable silently loads the FULL corpus even
    after the caller has computed a memory-safe size. That is what OOM-killed
    the Gowalla run: sizing reported 14,419 users, then 52,985 were loaded.
    An explicit argument always wins over the environment.
    """
    if explicit is not None:
        return explicit
    raw = os.environ.get("SIGNALSHAP_MAX_USERS", "").strip()
    if not raw or raw.lower() in {"none", "0", "all"}:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


TIMESTAMPED_LOADERS = {
    "gowalla_ts": lambda max_users=None, **kw: load_gowalla_timestamped(
        max_users=_env_cap(max_users), **kw),
    "lastfm_1k": lambda max_users=None, **kw: load_lastfm_1k(
        max_users=_env_cap(max_users), **kw),
    "amazon_video_games": lambda max_users=None, **kw: load_amazon_timestamped(
        "Video_Games", max_users=_env_cap(max_users), **kw),
    "amazon_books_ts": lambda max_users=None, **kw: load_amazon_timestamped(
        "Books", max_users=_env_cap(max_users), **kw),
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
