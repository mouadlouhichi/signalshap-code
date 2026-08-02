"""Pins the density-ordering invariant that C3 depends on (spec v1.1.3, §4 Fix R10).

C3 claims LOO falsification "on three benchmarks of contrasting density
(dense movies, sparse books, medium music)". That claim is only true while

    rho(Amazon-Book) < rho(LastFM-2K) < rho(ML-1M)

holds with a real margin. Rung 3 of the recall fallback ladder (k-core the
Amazon-Book corpus) repairs candidate recall by *raising density*, i.e. by the
same mechanism that destroys the ordering. A k=10 core is estimated to land
Amazon-Book near 0.76% against LastFM's 0.28% -- not a blunted contrast but an
inverted one, presented as a finding.

These tests fail the build if any filter inverts or compresses the ordering, so
the constraint survives a Week-6 deadline. Prose warnings do not.
"""

from __future__ import annotations

import json
import os

import pytest

# Strict ordering required by C3, sparsest first.
REQUIRED_ORDER = ("amazon_book", "lastfm_2k", "ml_1m")

# Each adjacent pair must differ by at least this factor, so the contrast is
# reportable rather than a rounding artefact.
MIN_MARGIN = 1.5

STATS_PATH = os.environ.get(
    "SIGNALSHAP_DATASET_STATS", "artefacts/dataset_stats.json"
)


def density(users: int, items: int, interactions: int) -> float:
    """Density of the as-used, post-split, post-filter interaction matrix."""
    if users <= 0 or items <= 0:
        raise ValueError("empty dataset")
    return interactions / (users * items)


def check_ordering(densities: dict[str, float], min_margin: float = MIN_MARGIN):
    """Return the list of invariant violations; empty list means the build passes."""
    problems = []
    missing = [d for d in REQUIRED_ORDER if d not in densities]
    if missing:
        problems.append(f"missing datasets in stats: {missing}")
        return problems

    for sparser, denser in zip(REQUIRED_ORDER, REQUIRED_ORDER[1:]):
        lo, hi = densities[sparser], densities[denser]
        if not lo < hi:
            problems.append(
                f"ORDERING INVERTED: {sparser} ({lo:.5%}) is not sparser than "
                f"{denser} ({hi:.5%}) -- C3's density-contrast narrative is false as written"
            )
        elif hi / lo < min_margin:
            problems.append(
                f"MARGIN TOO THIN: {denser} ({hi:.5%}) is only {hi / lo:.2f}x "
                f"{sparser} ({lo:.5%}); require >= {min_margin}x"
            )
    return problems


# --------------------------------------------------------------------------- #
# Unit tests on the invariant itself (always run, no data required).
# --------------------------------------------------------------------------- #

# Unfiltered plan of record: ordering holds comfortably.
UNFILTERED = {"amazon_book": 0.0005, "lastfm_2k": 0.0028, "ml_1m": 0.045}

# Estimated post-k-core densities from the §4 hazard table.
K5_CORE = {"amazon_book": 0.00253, "lastfm_2k": 0.0028, "ml_1m": 0.045}
K10_CORE = {"amazon_book": 0.00764, "lastfm_2k": 0.0028, "ml_1m": 0.045}
K20_CORE = {"amazon_book": 0.02333, "lastfm_2k": 0.0028, "ml_1m": 0.045}


def test_unfiltered_plan_satisfies_the_invariant():
    assert check_ordering(UNFILTERED) == []


def test_k10_core_inverts_the_ordering():
    """The k=10 that v1.1.2 offered as an option is exactly the one that breaks C3."""
    problems = check_ordering(K10_CORE)
    assert problems, "k=10 core must be rejected by the invariant"
    assert any("ORDERING INVERTED" in p for p in problems)


def test_k20_core_inverts_the_ordering():
    assert any("ORDERING INVERTED" in p for p in check_ordering(K20_CORE))


def test_k5_core_fails_on_margin_not_inversion():
    """k=5 keeps the sign but ties LastFM -- rejected for a thin margin, correctly."""
    problems = check_ordering(K5_CORE)
    assert problems, "k=5 core ties LastFM and must be rejected"
    assert any("MARGIN TOO THIN" in p for p in problems)
    assert not any("ORDERING INVERTED" in p for p in problems)


def test_margin_rule_is_strict_about_ties():
    tied = {"amazon_book": 0.0028, "lastfm_2k": 0.0028, "ml_1m": 0.045}
    assert any("ORDERING INVERTED" in p for p in check_ordering(tied))


def test_density_helper():
    assert density(100, 200, 1000) == pytest.approx(0.05)
    with pytest.raises(ValueError):
        density(0, 10, 5)


# --------------------------------------------------------------------------- #
# The gate that runs against real, as-used statistics (spec §7, Fix R11).
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(
    not os.path.exists(STATS_PATH),
    reason=f"{STATS_PATH} not built yet (created in Week 1 by data/stats.py)",
)
def test_as_used_densities_preserve_the_ordering():
    """Guards C3's cross-density claim -- but only when that claim is IN SCOPE.

    The manuscript was narrowed to a single corpus plus a controlled
    intervention, and it no longer asserts a density contrast. With fewer than
    all three corpora present this test therefore has nothing to guard and
    skips, rather than failing on a claim the paper does not make. The moment a
    third corpus appears the invariant becomes live again automatically.
    """
    """Authoritative check: computed post-filter densities, never published figures."""
    with open(STATS_PATH) as fh:
        stats = json.load(fh)

    densities = {
        name: density(d["users"], d["items"], d["interactions"])
        for name, d in stats.items()
        if name in REQUIRED_ORDER
    }
    if len(densities) < len(REQUIRED_ORDER):
        pytest.skip(
            f"cross-density claim out of scope: only {sorted(densities)} present. "
            "The invariant re-arms automatically once all three corpora exist."
        )
    problems = check_ordering(densities)
    assert not problems, (
        "density-ordering invariant violated; C3 and the §1 framing must be "
        "rewritten or the filter reverted:\n  " + "\n  ".join(problems)
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))


# --------------------------------------------------------------------------- #
# Provenance gate: the ordering invariant validates whatever numbers it is
# handed, so it cannot distinguish a measurement from an estimate. These tests
# close that gap (spec §6.2, Week-1 obligation).
# --------------------------------------------------------------------------- #

SWEEP_PATH = os.environ.get("SIGNALSHAP_KCORE_SWEEP", "artefacts/kcore_sweep.json")

REQUIRED_PROVENANCE = ("source", "measured_at", "corpus_hash")


def kcore_configured() -> bool:
    """True when rung 3 of the fallback ladder is active for any dataset."""
    cfg = os.environ.get("SIGNALSHAP_KCORE_K", "").strip()
    return bool(cfg) and cfg.lower() not in {"none", "0", "false"}


def has_provenance(blob: dict) -> list:
    """Missing-or-non-measured provenance fields; empty list means trustworthy."""
    problems = [f for f in REQUIRED_PROVENANCE if not blob.get(f)]
    if blob.get("source") not in (None, "measured"):
        problems.append(
            f"source is {blob['source']!r}, must be 'measured' before informing a decision"
        )
    return problems


def test_kcore_sweep_is_measured_not_estimated():
    """Rung 3 must not be reachable on the spec's placeholder retention rates.

    §6.2's k-core table is explicitly non-authoritative: the retention rates are
    order-of-magnitude estimates that establish the hazard is real, not
    measurements of the corpus. Selecting k from them would mean the whole
    density-inversion conclusion rests on numbers nobody checked.
    """
    if not kcore_configured():
        pytest.skip("no k-core configured; rung 3 inactive")

    assert os.path.exists(SWEEP_PATH), (
        f"k-core is configured but {SWEEP_PATH} is missing. Run "
        "scripts/measure_kcore_sweep.py first -- rung 3 may not be selected "
        "from the placeholder table in spec §6.2."
    )
    with open(SWEEP_PATH) as fh:
        sweep = json.load(fh)

    problems = has_provenance(sweep)
    assert not problems, f"{SWEEP_PATH} provenance unusable: {problems}"


@pytest.mark.skipif(
    not os.path.exists(STATS_PATH), reason=f"{STATS_PATH} not built yet"
)
def test_dataset_stats_declare_measured_provenance():
    """dataset_stats.json feeds both the ordering invariant and every density
    figure in the manuscript, so it must declare measured provenance too."""
    with open(STATS_PATH) as fh:
        stats = json.load(fh)
    blob = stats.get("_meta", stats)
    problems = has_provenance(blob)
    assert not problems, f"{STATS_PATH} provenance unusable: {problems}"


def test_provenance_helper_rejects_estimates():
    assert has_provenance(
        {"source": "measured", "measured_at": "2026-08-02", "corpus_hash": "abc123"}
    ) == []
    assert has_provenance(
        {"source": "estimated", "measured_at": "2026-08-02", "corpus_hash": "abc123"}
    )
    assert has_provenance({"source": "measured"})  # missing fields
    assert has_provenance({})
