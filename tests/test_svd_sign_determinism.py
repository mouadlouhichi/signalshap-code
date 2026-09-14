"""Is the `rec` cluster partition reproducible across SVD solver seeds?

The manuscript carried a caveat saying the argmax cluster assignment in `rec`
"is not invariant to an arbitrary sign reversal of an SVD component", so that
reproduction needed the exact cached decomposition. Checking it turned up two
things, and only one of them supports the caveat.

1. The SIGN mechanism named in the caveat is already neutralised, and not by
   us: `sklearn.decomposition.TruncatedSVD` calls
   `svd_flip(U, VT, u_based_decision=False)` on both code paths, which is
   exactly the "largest-magnitude loading is positive" convention. So the
   partition never depended on the component signs. `canonical_svd_sign` is
   retained as an explicit guard, because that behaviour is an sklearn
   implementation detail rather than a documented API promise, and the
   property we need is ours to enforce.

2. The mechanism that DOES break reproducibility is different: rotation inside
   a degenerate (tied or near-tied) singular subspace. Sign canonicalisation
   cannot fix it, because there is no sign to fix -- any orthonormal basis of
   the tied subspace is a valid answer, and which one a randomised solver
   lands on depends on its start vector. `test_tied_singular_values_*` below
   exhibits the failure, so the paper's residual caveat is stated against the
   real cause.
"""
from __future__ import annotations

import numpy as np
import pytest
from scipy import sparse
from sklearn.decomposition import TruncatedSVD

from signalshap.data.loaders import load_dataset
from signalshap.scorers.base import canonical_svd_sign, score_rec


def test_canonical_sign_makes_every_component_pivot_positive():
    rng = np.random.default_rng(0)
    comps = rng.normal(size=(6, 40))
    emb = rng.normal(size=(100, 6))
    flipped = canonical_svd_sign(emb, comps)

    signs = np.sign(comps[np.arange(6), np.argmax(np.abs(comps), axis=1)])
    # The returned embedding is the input with each column oriented.
    assert np.allclose(flipped, emb * signs[None, :])


def test_canonical_sign_is_idempotent_and_flip_invariant():
    """Negating a component must not change the canonicalised embedding."""
    rng = np.random.default_rng(1)
    comps = rng.normal(size=(5, 30))
    emb = rng.normal(size=(60, 5))

    a = canonical_svd_sign(emb, comps)
    # Flip components 1 and 3, and the embedding columns with them, exactly as
    # a different solver run would.
    s = np.array([1.0, -1.0, 1.0, -1.0, 1.0])
    b = canonical_svd_sign(emb * s[None, :], comps * s[:, None])
    assert np.allclose(a, b)

    # Applying the rule twice changes nothing.
    pivot = np.argmax(np.abs(comps), axis=1)
    oriented = comps * np.sign(comps[np.arange(5), pivot])[:, None]
    assert np.allclose(canonical_svd_sign(a, oriented), a)


def test_a_zero_component_is_left_alone():
    """np.sign(0) is 0 and would silently annihilate a column."""
    comps = np.zeros((3, 10))
    comps[0, 2] = -0.5
    emb = np.ones((4, 3))
    out = canonical_svd_sign(emb, comps)
    assert np.allclose(out[:, 0], -1.0)      # oriented
    assert np.allclose(out[:, 1:], 1.0)      # untouched, not zeroed


@pytest.mark.parametrize("seed", [43, 44, 7, 999])
def test_rec_scores_are_identical_across_solver_seeds(seed):
    """The property the manuscript needs: `rec` does not depend on the seed."""
    ds = load_dataset("ml_1m", synthetic=True, seed=42)
    assert np.array_equal(score_rec(ds, seed=42), score_rec(ds, seed=seed))


def test_tied_singular_values_break_reproducibility_and_signs_cannot_fix_it():
    """The real residual hazard, exhibited rather than asserted.

    With an exactly repeated singular value the corresponding subspace has no
    preferred basis, so different solver seeds return different rotations and
    the argmax partition genuinely moves. This is why the manuscript keeps a
    reproducibility caveat for `rec`, now stated against degeneracy rather
    than against component signs.
    """
    rng = np.random.default_rng(0)
    n = 200
    Q, _ = np.linalg.qr(rng.normal(size=(n, n)))
    P, _ = np.linalg.qr(rng.normal(size=(n, n)))
    s = np.array([10.0, 5.0, 5.0] + [1.0 / (i + 2) for i in range(n - 3)])
    M = sparse.csr_matrix((Q * s) @ P.T)

    parts = []
    for seed in (42, 43, 44, 7, 999):
        svd = TruncatedSVD(n_components=6, random_state=seed)
        emb = canonical_svd_sign(svd.fit_transform(M), svd.components_)
        parts.append(emb.argmax(axis=1))

    moved = max(int((p != parts[0]).sum()) for p in parts)
    assert moved > 0, (
        "expected a tied singular subspace to move the argmax partition; "
        "if this now passes, the degeneracy caveat can be dropped")
