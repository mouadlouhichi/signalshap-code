"""Dataset loading, temporal split, and as-used statistics.

Spec §5 (datasets), §6.1 (density computed, never quoted).

Real loaders read the raw files. A deterministic synthetic generator is
provided so the whole pipeline is runnable end-to-end before any download --
it is clearly labelled and never mistaken for real data (every artefact
records `synthetic: true`).
"""

from __future__ import annotations

import hashlib
import json
import os
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import ARTEFACTS, PROCESSED, ROOT

RAW = ROOT / "data" / "raw"

#: Raw corpora are looked for in several plausible locations, because a
#: hand-placed download lands in data/<name>/ as often as data/raw/<name>/.
#: Silently falling back to synthetic when real files are present but
#: misplaced is the worst possible failure -- it yields a paper written on
#: planted data that the author believes is real.
RAW_SEARCH = (ROOT / "data" / "raw", ROOT / "data", ROOT)


def find_raw(*names: str) -> Path | None:
    """First existing directory matching any of `names` under RAW_SEARCH."""
    for base in RAW_SEARCH:
        for n in names:
            if (base / n).is_dir():
                return base / n
    return None

#: Columns every loader must produce, in this order.
SCHEMA = ["user", "item", "timestamp", "original_record_index"]


@dataclass
class Dataset:
    """A loaded, split dataset with contiguous integer user/item ids."""

    name: str
    train: pd.DataFrame
    valid: pd.DataFrame
    test: pd.DataFrame
    n_users: int
    n_items: int
    item_meta: pd.DataFrame  # item -> 'tags' string, for the ct scorer
    synthetic: bool = False
    #: True for corpora with no timestamps (published splits); disclosed in T2.
    no_timestamps: bool = False

    @property
    def n_interactions(self) -> int:
        return len(self.train) + len(self.valid) + len(self.test)

    def density(self) -> float:
        """As-used density (spec §6.1) -- computed, never quoted."""
        return self.n_interactions / (self.n_users * self.n_items)

    def stats(self) -> dict:
        return {
            "users": int(self.n_users),
            "items": int(self.n_items),
            "interactions": int(self.n_interactions),
            "density": float(self.density()),
            "train": int(len(self.train)),
            "valid": int(len(self.valid)),
            "test": int(len(self.test)),
            "synthetic": bool(self.synthetic),
            "no_timestamps": bool(self.no_timestamps),
        }


# --------------------------------------------------------------------------- #
# Temporal split (spec §5)
# --------------------------------------------------------------------------- #


def leave_last_out_split(df: pd.DataFrame) -> tuple[pd.DataFrame, ...]:
    """Last interaction -> test, second-to-last -> validation, rest -> train.

    Ties resolved deterministically by (timestamp, original_record_index), per
    spec §5. Users with < 3 interactions cannot furnish all three folds and are
    dropped; the count is reported.
    """
    df = df.sort_values(["user", "timestamp", "original_record_index"], kind="mergesort")
    rank_from_end = df.groupby("user").cumcount(ascending=False)
    keep = df["user"].map(df["user"].value_counts()) >= 3
    df, rank_from_end = df[keep], rank_from_end[keep]
    return (
        df[rank_from_end >= 2].reset_index(drop=True),
        df[rank_from_end == 1].reset_index(drop=True),
        df[rank_from_end == 0].reset_index(drop=True),
    )


def _reindex(df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """Map users/items to contiguous ints; keeps score matrices dense."""
    users = {u: i for i, u in enumerate(sorted(df["user"].unique()))}
    items = {v: i for i, v in enumerate(sorted(df["item"].unique()))}
    df = df.assign(user=df["user"].map(users), item=df["item"].map(items))
    return df, len(users), len(items)


def _finalise(df: pd.DataFrame, name: str, meta: pd.DataFrame | None, synthetic: bool) -> Dataset:
    df = df.copy()
    if "original_record_index" not in df:
        df["original_record_index"] = np.arange(len(df))
    df = df[SCHEMA]
    df, n_users, n_items = _reindex(df)
    train, valid, test = leave_last_out_split(df)
    if meta is None:
        meta = pd.DataFrame({"item": np.arange(n_items), "tags": ""})
    return Dataset(name, train, valid, test, n_users, n_items, meta, synthetic)


# --------------------------------------------------------------------------- #
# Real loaders (spec §5)
# --------------------------------------------------------------------------- #


def load_ml_1m(path: Path | None = None) -> Dataset:
    """MovieLens-1M. Expects ml-1m/ratings.dat and movies.dat."""
    base = Path(path) if path else find_raw("ml-1m", "ml_1m", "ml-1m/ml-1m")
    if base is None:
        raise FileNotFoundError("ml-1m not found under " + str(RAW_SEARCH))
    r = pd.read_csv(
        base / "ratings.dat", sep="::", engine="python", header=None,
        names=["user", "item", "rating", "timestamp"], encoding="latin-1",
    )
    r = r[r["rating"] >= 4].drop(columns=["rating"])  # implicit feedback
    m = pd.read_csv(
        base / "movies.dat", sep="::", engine="python", header=None,
        names=["item", "title", "genres"], encoding="latin-1",
    )
    meta = pd.DataFrame({
        "item": m["item"],
        "tags": (m["title"].fillna("") + " " + m["genres"].fillna("").str.replace("|", " ", regex=False)),
    })
    return _finalise(r, "ml_1m", meta, synthetic=False)


def load_lastfm_2k(path: Path | None = None) -> Dataset:
    """LastFM-2K (HetRec 2011). Expects user_taggedartists-timestamps.dat."""
    base = Path(path) if path else find_raw(
        "hetrec2011-lastfm-2k", "lastfm-2k", "lastfm_2k")
    if base is None:
        raise FileNotFoundError("lastfm-2k not found under " + str(RAW_SEARCH))
    r = pd.read_csv(base / "user_taggedartists-timestamps.dat", sep="\t")
    r = r.rename(columns={"userID": "user", "artistID": "item"})[["user", "item", "timestamp"]]
    tags = pd.read_csv(base / "tags.dat", sep="\t", encoding="latin-1")
    ut = pd.read_csv(base / "user_taggedartists-timestamps.dat", sep="\t")
    meta = (
        ut.merge(tags, on="tagID", how="left")
        .groupby("artistID")["tagValue"].apply(lambda s: " ".join(s.dropna().astype(str)[:40]))
        .reset_index().rename(columns={"artistID": "item", "tagValue": "tags"})
    )
    return _finalise(r, "lastfm_2k", meta, synthetic=False)


def load_amazon_book(path: Path | None = None, n_users: int = 50_000, seed: int = 42) -> Dataset:
    """Amazon-Book 2018, subsampled to n_users (spec §5, seeded + manifested)."""
    base = Path(path) if path else find_raw(
        "amazon_book", "amazon-book", "amazon_books")
    if base is None:
        raise FileNotFoundError("amazon_book not found under " + str(RAW_SEARCH))
    r = pd.read_csv(base / "ratings_Books.csv", header=None,
                    names=["user", "item", "rating", "timestamp"])
    r = r[r["rating"] >= 4.0].drop(columns=["rating"])
    uniq = np.sort(r["user"].unique())
    if len(uniq) > n_users:
        rng = np.random.default_rng(seed)
        keep = set(rng.choice(uniq, size=n_users, replace=False).tolist())
        r = r[r["user"].isin(keep)]
    return _finalise(r, "amazon_book", None, synthetic=False)


# --------------------------------------------------------------------------- #
# Synthetic corpora -- runnable pipeline before any download
# --------------------------------------------------------------------------- #


def make_synthetic(
    name: str, n_users: int, n_items: int, target_density: float, seed: int = 42,
) -> Dataset:
    """Deterministic synthetic corpus with planted structure.

    Plants exactly the structure the experiments look for, so the pipeline can
    be validated before real data arrives:

    * popularity skew (Zipf) -- makes `pop` informative and, because ALS on
      implicit feedback chases popularity, induces the pop-cf redundancy that
      spec §4 pre-registers;
    * latent user/item factors -- makes `cf` informative;
    * item content clusters aligned to those factors -- makes `ct` informative
      and induces the rec-ct overlap, also pre-registered;
    * temporal drift over clusters -- makes `rec` and `seq` informative.
    """
    rng = np.random.default_rng(seed)
    target = int(round(target_density * n_users * n_items))

    n_clusters = max(4, n_items // 200)
    item_cluster = rng.integers(0, n_clusters, size=n_items)
    pop_w = 1.0 / np.power(np.arange(1, n_items + 1), 0.9)
    pop_w = pop_w[rng.permutation(n_items)]
    pop_w /= pop_w.sum()

    n_factors = 8
    user_f = rng.normal(size=(n_users, n_factors))
    clus_f = rng.normal(size=(n_clusters, n_factors))
    item_f = clus_f[item_cluster] + 0.3 * rng.normal(size=(n_items, n_factors))

    per_user = max(3, target // n_users)
    rows = []
    idx = 0
    for u in range(n_users):
        k = max(3, int(rng.poisson(per_user)))
        aff = user_f[u] @ item_f.T
        p = 0.6 * pop_w + 0.4 * _softmax(aff)
        p /= p.sum()
        k = min(k, n_items)
        picked = rng.choice(n_items, size=k, replace=False, p=p)
        # temporal drift: the user's taste walks across clusters over time
        order = np.argsort(item_cluster[picked] + rng.normal(0, 0.5, size=k))
        for t, i in enumerate(picked[order]):
            rows.append((u, int(i), 1_500_000_000 + idx * 60 + t, idx))
            idx += 1

    df = pd.DataFrame(rows, columns=SCHEMA)
    words = [f"tag{c}_{w}" for c in range(n_clusters) for w in range(6)]
    meta = pd.DataFrame({
        "item": np.arange(n_items),
        "tags": [
            " ".join(words[item_cluster[i] * 6 : item_cluster[i] * 6 + 6])
            + f" genre{item_cluster[i] % 5}"
            for i in range(n_items)
        ],
    })
    return _finalise(df, name, meta, synthetic=True)


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


#: Synthetic stand-ins whose densities preserve the C3 ordering (spec §6.2).
SYNTHETIC_SPECS = {
    "gowalla": dict(n_users=900, n_items=1800, target_density=0.004),
    "yelp2018": dict(n_users=900, n_items=1500, target_density=0.006),
    "amazon_book_lgcn": dict(n_users=900, n_items=2400, target_density=0.003),
    "ml_1m": dict(n_users=900, n_items=700, target_density=0.045),
    "lastfm_2k": dict(n_users=700, n_items=1600, target_density=0.010),
    "amazon_book": dict(n_users=1200, n_items=3000, target_density=0.003),
}

def load_lightgcn_split(name: str, path: Path | None = None,
                        max_users: int | None = None, seed: int = 42) -> Dataset:
    """Load a standard LightGCN benchmark split (Gowalla / Yelp2018 / Amazon-Book).

    These are the canonical preprocessed splits distributed with LightGCN
    (He et al., SIGIR 2020) and reused across the recommender literature, which
    makes them directly comparable to published work.

    IMPORTANT -- these files carry NO timestamps. We therefore cannot apply the
    leave-last-out TEMPORAL protocol used for MovieLens-1M. Instead we honour
    the corpus's own published train/test partition and carve a validation fold
    out of train. The absence of temporal ordering is a real protocol
    difference and must be disclosed in the manuscript, not glossed: `rec` and
    `seq` are handicapped here because interaction order is arbitrary, so their
    attributions are lower bounds rather than estimates.
    """
    folder = {"gowalla": "gowalla", "yelp2018": "yelp2018",
              "amazon_book_lgcn": "amazon-book"}[name]
    base = Path(path) if path else find_raw(folder)
    if base is None:
        raise FileNotFoundError(f"{folder} not found under {RAW_SEARCH}")

    def _read(fn):
        rows = []
        for line in (base / fn).read_text().splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            u = int(parts[0])
            rows.extend((u, int(i)) for i in parts[1:])
        return rows

    train_rows, test_rows = _read("train.txt"), _read("test.txt")
    if max_users is not None:
        rng = np.random.default_rng(seed)
        uniq = np.unique([u for u, _ in train_rows])
        if len(uniq) > max_users:
            keep = set(rng.choice(uniq, max_users, replace=False).tolist())
            train_rows = [r for r in train_rows if r[0] in keep]
            test_rows = [r for r in test_rows if r[0] in keep]

    # Synthesise a stable ordering: no timestamps exist, so position in the
    # published file is the only ordering available. Recorded explicitly.
    rows = [(u, i, idx, idx) for idx, (u, i) in enumerate(train_rows)]
    off = len(rows)
    rows += [(u, i, off + idx, off + idx) for idx, (u, i) in enumerate(test_rows)]
    df = pd.DataFrame(rows, columns=SCHEMA)

    df, n_users, n_items = _reindex(df)
    n_train = len(train_rows)
    tr_all = df.iloc[:n_train]
    te = df.iloc[n_train:].groupby("user", as_index=False).first()

    # One held-out validation interaction per user, drawn from train.
    last = tr_all.groupby("user").tail(1)
    tr = tr_all.drop(index=last.index)
    va = last.groupby("user", as_index=False).first()

    common = set(tr["user"]) & set(va["user"]) & set(te["user"])
    tr = tr[tr["user"].isin(common)].reset_index(drop=True)
    va = va[va["user"].isin(common)].reset_index(drop=True)
    te = te[te["user"].isin(common)].reset_index(drop=True)

    meta = pd.DataFrame({"item": np.arange(n_items), "tags": ""})
    ds = Dataset(name, tr, va, te, n_users, n_items, meta, synthetic=False)
    ds.no_timestamps = True
    return ds


LOADERS = {
    "ml_1m": load_ml_1m,
    "lastfm_2k": load_lastfm_2k,
    "amazon_book": load_amazon_book,
    "gowalla": lambda: load_lightgcn_split("gowalla", max_users=int(os.environ.get("SIGNALSHAP_MAX_USERS", 3000))),
    "yelp2018": lambda: load_lightgcn_split("yelp2018", max_users=int(os.environ.get("SIGNALSHAP_MAX_USERS", 3000))),
    "amazon_book_lgcn": lambda: load_lightgcn_split("amazon_book_lgcn", max_users=int(os.environ.get("SIGNALSHAP_MAX_USERS", 3000))),
}


def _register_timestamped() -> None:
    """Merge the timestamped loaders into LOADERS.

    Done lazily and once: timestamped.py imports helpers from this module, so
    a top-level import would be circular. Without this, Experiment() cannot
    see corpora like gowalla_ts even though the validity gate can, which is
    exactly the mismatch that crashed the first full run.
    """
    if getattr(_register_timestamped, "_done", False):
        return
    _register_timestamped._done = True
    try:
        from .timestamped import TIMESTAMPED_LOADERS
    except Exception:
        return
    for k, fn in TIMESTAMPED_LOADERS.items():
        LOADERS.setdefault(k, fn)


def load_dataset(name: str, synthetic: bool = False, seed: int = 42,
                 strict: bool = False) -> Dataset:
    """Load `name`; fall back to synthetic only when raw files are truly absent.

    The fallback WARNS LOUDLY. A silent fallback is dangerous: real files that
    are merely misplaced would be ignored and the study would report planted
    numbers as if they were benchmark results. Pass `strict=True` (or set
    SIGNALSHAP_STRICT_DATA=1) to make a missing corpus a hard error instead.
    """
    _register_timestamped()

    if synthetic:
        if name not in SYNTHETIC_SPECS:
            raise KeyError(
                f"{name}: no synthetic specification. Timestamped corpora are "
                "never faked -- supply the real files under data/raw/."
            )
        return make_synthetic(name, seed=seed, **SYNTHETIC_SPECS[name])
    try:
        if name not in LOADERS:
            raise FileNotFoundError(f"no loader registered for {name!r}")
        ds = LOADERS[name]()
        print(f"[signalshap] {name}: loaded REAL data "
              f"({ds.n_users:,} users x {ds.n_items:,} items, "
              f"{ds.n_interactions:,} interactions)")
        return ds
    except (FileNotFoundError, OSError, KeyError) as exc:
        if strict or os.environ.get("SIGNALSHAP_STRICT_DATA") == "1":
            raise FileNotFoundError(
                f"{name}: raw files not found and strict mode is on ({exc})"
            ) from exc
        if name not in SYNTHETIC_SPECS:
            # Temporal corpora have no synthetic stand-in by design: a planted
            # substitute would silently invalidate rec/seq/pop-decay, which is
            # the precise failure this whole module exists to prevent.
            raise FileNotFoundError(
                f"{name}: raw files not found ({exc}). This corpus has no "
                "synthetic fallback -- run data_preparation/fetch_timestamped.sh, or "
                "check that the extracted files are under data/raw/."
            ) from exc
        warnings.warn(
            f"\n{'!' * 74}\n"
            f"[signalshap] {name}: RAW FILES NOT FOUND -> FALLING BACK TO SYNTHETIC.\n"
            f"  reason    : {exc}\n"
            f"  searched  : {[str(b) for b in RAW_SEARCH]}\n"
            f"  Results will be a PLANTED PILOT, not benchmark numbers. Every\n"
            f"  artefact is tagged synthetic=true. Do NOT report these as\n"
            f"  MovieLens/LastFM/Amazon results.\n"
            f"{'!' * 74}",
            RuntimeWarning, stacklevel=2,
        )
        return make_synthetic(name, seed=seed, **SYNTHETIC_SPECS[name])


# --------------------------------------------------------------------------- #
# As-used statistics with provenance (spec §6.1, §6.2 rule (b))
# --------------------------------------------------------------------------- #


def corpus_hash(ds: Dataset) -> str:
    h = hashlib.sha256()
    for part in (ds.train, ds.valid, ds.test):
        h.update(pd.util.hash_pandas_object(part[["user", "item"]], index=False).values.tobytes())
    return h.hexdigest()[:16]


def build_dataset_stats(datasets: dict[str, Dataset]) -> dict:
    """Write artefacts/dataset_stats.json with measured provenance.

    The `source: "measured"` field is required by
    tests/test_density_ordering.py -- the ordering invariant validates whatever
    densities it is handed and cannot tell a measurement from an estimate.
    """
    # MERGE with any existing file rather than overwrite it. Running one corpus
    # at a time -- which the memory budget forces, since two corpora cannot
    # share a single SIGNALSHAP_MAX_USERS -- otherwise leaves this file holding
    # only the last corpus run. That silently disarmed the density-ordering
    # invariant (it skips when fewer than three corpora are present) and made
    # T2 a one-row table, while the underlying runs were all fine.
    blob: dict = {}
    existing = ARTEFACTS / "dataset_stats.json"
    if existing.exists():
        try:
            prior = json.loads(existing.read_text())
            blob = {k: v for k, v in prior.items() if k != "_meta"}
        except (json.JSONDecodeError, OSError):
            blob = {}
    blob.update({name: ds.stats() for name, ds in datasets.items()})
    blob["_meta"] = {
        "corpora_in_this_run": sorted(datasets),
        "source": "measured",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "corpus_hash": hashlib.sha256(
            "|".join(f"{n}:{corpus_hash(d)}" for n, d in sorted(datasets.items())).encode()
        ).hexdigest()[:16],
        "synthetic": any(d.synthetic for d in datasets.values()),
    }
    return blob


def save_processed(ds: Dataset) -> Path:
    out = PROCESSED / ds.name
    out.mkdir(parents=True, exist_ok=True)
    for fold in ("train", "valid", "test"):
        getattr(ds, fold).to_parquet(out / f"{fold}.parquet", index=False)
    ds.item_meta.to_parquet(out / "item_meta.parquet", index=False)
    return out
