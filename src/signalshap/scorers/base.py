"""The five base scorers (spec §4). Each trains once; scores are cached.

    cf   ALS matrix factorization (implicit feedback), 64 factors
    ct   TF-IDF cosine over item metadata
    pop  global item frequency with time decay
    rec  exponential recency over the item's content cluster
    seq  item2vec-style skip-gram over interaction sequences

Nothing here is invented -- these are off-the-shelf components, chosen so the
Shapley story does not depend on any of them being novel.

Two overlaps are deliberate and PRE-REGISTERED in spec §4: pop-cf (ALS on
implicit feedback chases popularity) and rec-ct (recency is defined over
content clusters). RQ2 tests whether Shapley recovers them; they are not
presented as discoveries.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from ..config import SOURCES
from ..data.loaders import Dataset


def _csr(df: pd.DataFrame, n_users: int, n_items: int) -> sparse.csr_matrix:
    return sparse.csr_matrix(
        (np.ones(len(df), dtype=np.float32), (df["user"].values, df["item"].values)),
        shape=(n_users, n_items),
    )


def canonical_svd_sign(emb: np.ndarray, components: np.ndarray) -> np.ndarray:
    """Fix the arbitrary per-component sign of a truncated SVD.

    A singular triplet is determined only up to a simultaneous sign flip of
    its left and right vectors: (u, v) and (-u, -v) are equally valid, and
    which one a randomised solver returns depends on its start vector, hence
    on `random_state`. Anything invariant to that flip is unaffected, which is
    why `seq` does not care: it uses inner products of embeddings, and a sign
    flip cancels between the two factors.

    `rec` is NOT invariant. It takes `emb.argmax(axis=1)` to assign each item
    to a content cluster, and argmax is destroyed by negating a column: items
    that loaded strongly negative on a component load strongly positive after
    the flip and change cluster. So the cluster partition, and every `rec`
    score built on it, silently depended on the solver's seed.

    The convention here is the standard one (`sklearn.utils.extmath.svd_flip`,
    applied to the right singular vectors): flip each component so that its
    largest-magnitude loading is positive. Ties in magnitude are broken by the
    lowest index, so the rule is a total function of the decomposition and
    reproduces across solvers, BLAS builds and platforms.
    """
    k = components.shape[0]
    pivot = np.argmax(np.abs(components), axis=1)
    signs = np.sign(components[np.arange(k), pivot])
    # A component that is exactly zero has no orientation to fix; leave it.
    signs[signs == 0] = 1.0
    return emb * signs[None, :]


# --------------------------------------------------------------------------- #
# cf -- ALS (implicit), deterministic
# --------------------------------------------------------------------------- #


def score_cf(ds: Dataset, n_factors: int = 64, reg: float = 0.1,
             iters: int = 15, seed: int = 42) -> np.ndarray:
    """Implicit-feedback ALS. Closed-form alternating updates, no LR tuning."""
    R = _csr(ds.train, ds.n_users, ds.n_items)
    rng = np.random.default_rng(seed)
    f = min(n_factors, max(2, min(ds.n_users, ds.n_items) - 1))
    X = 0.01 * rng.normal(size=(ds.n_users, f)).astype(np.float32)
    Y = 0.01 * rng.normal(size=(ds.n_items, f)).astype(np.float32)
    Rt = R.T.tocsr()
    eye = np.eye(f, dtype=np.float32)

    def _solve(mat: sparse.csr_matrix, fixed: np.ndarray, out: np.ndarray) -> None:
        gram = fixed.T @ fixed + reg * eye
        for row in range(mat.shape[0]):
            s, e = mat.indptr[row], mat.indptr[row + 1]
            if s == e:
                out[row] = 0.0
                continue
            idx = mat.indices[s:e]
            sub = fixed[idx]
            # confidence weighting: alpha=1 on observed entries
            A = gram + sub.T @ sub
            b = sub.sum(axis=0) * 2.0
            out[row] = np.linalg.solve(A, b)

    for _ in range(iters):
        _solve(R, Y, X)
        _solve(Rt, X, Y)
    return (X @ Y.T).astype(np.float32)


# --------------------------------------------------------------------------- #
# ct -- TF-IDF content similarity
# --------------------------------------------------------------------------- #


def score_ct(ds: Dataset, max_features: int = 5000) -> np.ndarray:
    """User profile = mean TF-IDF of consumed items; score = cosine similarity."""
    meta = ds.item_meta.set_index("item").reindex(range(ds.n_items))
    tags = meta["tags"].fillna("").astype(str).values
    if not any(t.strip() for t in tags):
        return np.zeros((ds.n_users, ds.n_items), dtype=np.float32)
    V = TfidfVectorizer(max_features=max_features, token_pattern=r"\S+")
    M = V.fit_transform(tags)  # items x vocab, L2-normalised
    R = _csr(ds.train, ds.n_users, ds.n_items)
    counts = np.asarray(R.sum(axis=1)).ravel()
    counts[counts == 0] = 1.0
    P = sparse.diags(1.0 / counts) @ (R @ M)  # users x vocab
    P = sparse.csr_matrix(P)
    norms = sparse.linalg.norm(P, axis=1)
    norms[norms == 0] = 1.0
    P = sparse.diags(1.0 / norms) @ P
    return np.asarray((P @ M.T).todense(), dtype=np.float32)


# --------------------------------------------------------------------------- #
# pop -- time-decayed global frequency
# --------------------------------------------------------------------------- #


def score_pop(ds: Dataset, half_life_days: float = 180.0) -> np.ndarray:
    """Global popularity with exponential time decay (spec §4)."""
    t = ds.train["timestamp"].values.astype(np.float64)
    if len(t) == 0:
        return np.zeros((ds.n_users, ds.n_items), dtype=np.float32)
    age_days = (t.max() - t) / 86400.0
    w = np.power(0.5, age_days / max(half_life_days, 1e-9))
    counts = np.bincount(ds.train["item"].values, weights=w, minlength=ds.n_items)
    counts = np.log1p(counts).astype(np.float32)
    return np.tile(counts, (ds.n_users, 1))


# --------------------------------------------------------------------------- #
# rec -- recency over content clusters
# --------------------------------------------------------------------------- #


def score_rec(ds: Dataset, n_clusters: int = 20, half_life_days: float = 30.0,
              seed: int = 42) -> np.ndarray:
    """Exponential recency of the user's last interaction with an item's cluster.

    NOTE (spec §4): clusters come from item content, so `rec` is partly a `ct`
    derivative. This overlap is pre-registered, not discovered.
    """
    meta = ds.item_meta.set_index("item").reindex(range(ds.n_items))
    tags = meta["tags"].fillna("").astype(str).values
    if any(t.strip() for t in tags):
        V = TfidfVectorizer(max_features=2000, token_pattern=r"\S+")
        M = V.fit_transform(tags)
        k = min(n_clusters, max(2, min(M.shape) - 1))
        svd = TruncatedSVD(n_components=k, random_state=seed)
        emb = svd.fit_transform(M)
        # The argmax below is NOT invariant to an SVD component sign flip, and
        # the flip is a function of the solver's random start. Canonicalise
        # first, so the cluster partition depends on the data alone.
        emb = canonical_svd_sign(emb, svd.components_)
        cluster = emb.argmax(axis=1)
    else:
        cluster = np.zeros(ds.n_items, dtype=int)
    n_c = int(cluster.max()) + 1

    if len(ds.train) == 0:
        return np.zeros((ds.n_users, ds.n_items), dtype=np.float32)
    t_max = ds.train["timestamp"].max()
    last = np.zeros((ds.n_users, n_c), dtype=np.float64)
    np.maximum.at(
        last,
        (ds.train["user"].values, cluster[ds.train["item"].values]),
        ds.train["timestamp"].values.astype(np.float64),
    )
    age_days = (t_max - last) / 86400.0
    w = np.where(last > 0, np.power(0.5, age_days / max(half_life_days, 1e-9)), 0.0)
    return w[:, cluster].astype(np.float32)


# --------------------------------------------------------------------------- #
# seq -- item2vec (skip-gram over sequences, SVD-factorised PMI)
# --------------------------------------------------------------------------- #


def score_seq(ds: Dataset, dim: int = 64, window: int = 5, seed: int = 42) -> np.ndarray:
    """item2vec next-item scorer.

    Implemented as SVD of the shifted positive PMI of the co-occurrence matrix
    within a sliding window -- the standard closed-form equivalent of SGNS
    (Levy & Goldberg, 2014). Deterministic and CPU-only, which preserves the
    compute story of spec §4; SASRec is the Appendix-B alternative.
    """
    df = ds.train.sort_values(["user", "timestamp", "original_record_index"], kind="mergesort")
    rows, cols = [], []
    for _, seq in df.groupby("user")["item"]:
        s = seq.values
        for i in range(len(s)):
            for j in range(i + 1, min(i + window + 1, len(s))):
                rows += [s[i], s[j]]
                cols += [s[j], s[i]]
    if not rows:
        return np.zeros((ds.n_users, ds.n_items), dtype=np.float32)

    C = sparse.csr_matrix(
        (np.ones(len(rows), dtype=np.float32), (rows, cols)),
        shape=(ds.n_items, ds.n_items),
    )
    total = C.sum()
    r = np.asarray(C.sum(axis=1)).ravel() + 1e-9
    Cc = C.tocoo()
    pmi = np.log((Cc.data * total) / (r[Cc.row] * r[Cc.col]) + 1e-12)
    ppmi = sparse.csr_matrix(
        (np.maximum(pmi, 0.0), (Cc.row, Cc.col)), shape=C.shape
    )
    k = min(dim, max(2, min(ppmi.shape) - 1))
    emb = TruncatedSVD(n_components=k, random_state=seed).fit_transform(ppmi)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9

    # user vector = recency-weighted mean of the last `window` items
    U = np.zeros((ds.n_users, emb.shape[1]), dtype=np.float32)
    for u, seq in df.groupby("user")["item"]:
        s = seq.values[-window:]
        if len(s):
            w = np.power(0.8, np.arange(len(s))[::-1])
            U[u] = (emb[s] * w[:, None]).sum(axis=0) / w.sum()
    return (U @ emb.T).astype(np.float32)


SCORERS = {
    "cf": score_cf, "ct": score_ct, "pop": score_pop,
    "rec": score_rec, "seq": score_seq,
}


def train_all_scorers(ds: Dataset, seed: int = 42) -> dict[str, np.ndarray]:
    """Train every source once and return raw score matrices (spec §4)."""
    out = {}
    for g in SOURCES:
        fn = SCORERS[g]
        out[g] = fn(ds, seed=seed) if "seed" in fn.__code__.co_varnames else fn(ds)
    return out


def mask_seen(scores: dict[str, np.ndarray], ds: Dataset) -> dict[str, np.ndarray]:
    """Remove training items from candidate consideration."""
    u, i = ds.train["user"].values, ds.train["item"].values
    for m in scores.values():
        m[u, i] = -np.inf
    return scores
