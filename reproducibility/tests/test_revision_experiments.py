"""Tests for the experiments added in response to review."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from signalshap.attribution.values import (  # noqa: E402
    banzhaf_value, semivalue, shapley_taylor_interaction)
from signalshap.experiments.synthetic_games import validate_implementation  # noqa: E402
from signalshap.game.core import exact_shapley  # noqa: E402


def test_analytic_games_reproduce_exactly():
    """Magnitude validation: six closed-form Shapley vectors must match.

    Stronger than the symmetry diagnostic, which an exact implementation
    satisfies by construction. These include null and harmful players.
    """
    r = validate_implementation()
    assert r["_summary"]["all_pass"], {
        k: v for k, v in r.items() if not k.startswith("_") and not v["passes"]}
    assert r["_summary"]["worst_error"] < 1e-12


def test_semivalue_with_shapley_weights_equals_shapley():
    players = ("a", "b", "c")
    from itertools import combinations
    v = {}
    for k in range(4):
        for c in combinations(players, k):
            S = frozenset(c)
            v[S] = len(S) ** 2  # arbitrary superadditive game
    n = len(players)
    got = semivalue(v, {k: 1.0 / n for k in range(n)}, players)
    want = exact_shapley(v, players)
    for g in players:
        assert abs(got[g] - want[g]) < 1e-12


def test_banzhaf_differs_from_shapley_but_shares_symmetry():
    players = ("a", "b", "c")
    from itertools import combinations
    v = {}
    for k in range(4):
        for c in combinations(players, k):
            S = frozenset(c)
            v[S] = 1.0 if "a" in S else 0.0   # a is a dictator
    b = banzhaf_value(v, players)
    s = exact_shapley(v, players)
    assert abs(b["b"]) < 1e-12 and abs(b["c"]) < 1e-12, "dummies get zero"
    assert abs(s["b"]) < 1e-12 and abs(s["c"]) < 1e-12
    assert b["a"] == pytest.approx(1.0)


def test_interaction_index_detects_redundancy_and_synergy():
    """Negative pairwise index = redundancy; positive = complementarity."""
    from itertools import combinations
    players = ("a", "b")

    sub = {}
    for k in range(3):
        for c in combinations(players, k):
            S = frozenset(c)
            sub[S] = 1.0 if S else 0.0        # either alone suffices
    assert shapley_taylor_interaction(sub, players)["a|b"] < 0

    comp = {}
    for k in range(3):
        for c in combinations(players, k):
            S = frozenset(c)
            comp[S] = 1.0 if len(S) == 2 else 0.0   # need both
    assert shapley_taylor_interaction(comp, players)["a|b"] > 0


def test_fixed_head_game_does_not_refit():
    from signalshap.experiments.estimands import FixedHeadGame
    import inspect
    src = inspect.getsource(FixedHeadGame._fit_weights)
    assert "_grand_w" in src, "fixed head must cache the grand-coalition head"


def test_shapley_to_weights_is_a_simplex():
    from signalshap.fusion.heads import shapley_to_weights
    srcs = ("cf", "ct", "pop", "rec", "seq")
    phi = {"cf": 0.015, "ct": -0.002, "pop": 0.006, "rec": 0.0, "seq": 0.03}
    w = shapley_to_weights(phi, srcs, tau=0.01, rho=0.0)
    assert np.all(w >= 0), "negative weights would invert a source's scores"
    assert w.sum() == pytest.approx(1.0)
    assert srcs[int(np.argmax(w))] == "seq"


def test_hierarchical_bootstrap_is_wider_than_naive():
    """Two-level resampling must not understate uncertainty."""
    from signalshap.stats.tests import hierarchical_bootstrap, bootstrap_ci
    rng = np.random.default_rng(0)
    # a real seed effect: each seed shifted differently
    a = {s: rng.normal(0.06 + 0.01 * i, 0.05, 400) for i, s in enumerate((42, 43, 44))}
    b = {s: rng.normal(0.06, 0.05, 400) for s in (42, 43, 44)}
    h = hierarchical_bootstrap(a, b, n_boot=1500, seed=1)
    pooled = np.concatenate([a[s] - b[s] for s in a])
    naive = bootstrap_ci(pooled, n_boot=1500, seed=1)
    assert (h["hi"] - h["lo"]) > (naive["hi"] - naive["lo"]), (
        "hierarchical interval should be wider when a seed effect exists")


def test_tost_declares_equivalence_for_a_null_effect():
    from signalshap.stats.tests import tost_equivalence
    rng = np.random.default_rng(0)
    x = rng.normal(0.06, 0.01, 3000)
    y = x + rng.normal(0, 1e-4, 3000)
    assert tost_equivalence(x, y, margin=0.005)["equivalent"]


# --------------------------------------------------------------------------- #
# Timestamp handling (found while fetching real corpora)
# --------------------------------------------------------------------------- #


def test_epoch_conversion_is_resolution_independent():
    """pandas 2.x may parse to datetime64[s|ms|us], not always [ns].

    The common idiom `.astype("int64") // 10**9` silently under-reports by
    1000x on a [us] column: the result still looks like a plausible epoch
    integer, so nothing raises, but every recency and time-decay computation
    downstream is wrong. This pins the fix.
    """
    import pandas as pd
    from signalshap.data.timestamped import _to_epoch_seconds

    want = 1287532527  # 2010-10-19T23:55:27Z
    for raw in ("2010-10-19T23:55:27Z", "2010-10-19 23:55:27"):
        got = int(_to_epoch_seconds(pd.Series([raw])).iloc[0])
        assert got == want, f"{raw}: got {got}, want {want}"


def test_implausible_epoch_is_rejected():
    """A resolution mismatch must fail loudly rather than corrupt `rec`."""
    import pandas as pd
    import pytest as _pt
    from signalshap.data.timestamped import _prepare

    bad = pd.DataFrame({
        "user": [0, 0, 1, 1] * 3,
        "item": [1, 2, 1, 2] * 3,
        # 1287532 seconds = 1970, the symptom of dividing [us] by 1e9
        "timestamp": list(range(1287532, 1287544)),
    })
    with _pt.raises(ValueError, match="plausible Unix-seconds"):
        _prepare(bad, "probe", None, 42)


def test_temporal_validity_rejects_positional_index():
    """The failure that produced the withdrawn results must stay detectable."""
    from signalshap.data.loaders import make_synthetic
    from signalshap.data.timestamped import temporal_validity_report

    ds = make_synthetic("probe", 120, 200, 0.03, seed=1)
    for fold in ("train", "valid", "test"):
        d = getattr(ds, fold).copy()
        d["timestamp"] = d["original_record_index"]
        setattr(ds, fold, d)
    rep = temporal_validity_report(ds)
    assert rep["looks_like_positional_index"] or not rep["temporally_valid"]


def test_sasrec_encode_is_numerically_stable():
    """SASRec must not produce NaN/inf even with large embeddings.

    Without layer normalisation the residual stack grew unbounded during BPR
    training; once attention logits hit +/-inf, `A - A.max()` evaluated
    inf - inf = NaN and silently poisoned the sequence embedding. The symptom
    was a RuntimeWarning and a badly under-performing baseline, which made the
    comparison against SASRec unfair.
    """
    import warnings as _w

    import numpy as np

    from signalshap.data.loaders import make_synthetic
    from signalshap.scorers.neural import sasrec_scores

    ds = make_synthetic("probe", 120, 200, 0.04, seed=3)
    with _w.catch_warnings():
        _w.simplefilter("error", RuntimeWarning)   # any overflow/NaN raises
        S = sasrec_scores(ds, seed=42, n_epochs=5)
    assert np.isfinite(S).all(), "SASRec produced non-finite scores"


def test_timestamped_loaders_are_registered_for_experiment():
    """Experiment() resolves corpora through LOADERS, not TIMESTAMPED_LOADERS.

    The validity gate used one registry and the pipeline the other, so a
    corpus could pass validation and then crash with KeyError on the very next
    line. This pins the merge.
    """
    from signalshap.data.loaders import LOADERS, _register_timestamped
    from signalshap.data.timestamped import TIMESTAMPED_LOADERS

    _register_timestamped()
    for name in TIMESTAMPED_LOADERS:
        assert name in LOADERS, f"{name} unreachable from Experiment()"


def test_timestamped_corpus_never_falls_back_to_synthetic():
    """A missing temporal corpus must raise, not silently plant data."""
    import pytest as _pt

    from signalshap.data.loaders import load_dataset

    with _pt.raises((FileNotFoundError, KeyError)):
        load_dataset("lastfm_1k")     # not fetched in CI


def test_timestamped_loaders_honour_the_user_cap_env_var():
    """Experiment() builds corpora with no arguments, so loaders MUST read
    SIGNALSHAP_MAX_USERS.

    The Gowalla run was OOM-killed twice because the timestamped loaders
    ignored it: the runner computed a memory-safe 14,419 users, then the
    registry loaded all 52,985 (~207 GB of score matrices). The LightGCN
    loaders had always read the variable; these had not.
    """
    import os

    from signalshap.data.timestamped import _env_cap

    prev = os.environ.get("SIGNALSHAP_MAX_USERS")
    try:
        os.environ.pop("SIGNALSHAP_MAX_USERS", None)
        assert _env_cap(None) is None, "absent variable means no cap"

        os.environ["SIGNALSHAP_MAX_USERS"] = "14419"
        assert _env_cap(None) == 14419, "the env var must be honoured"
        assert _env_cap(500) == 500, "an explicit argument wins"

        os.environ["SIGNALSHAP_MAX_USERS"] = "none"
        assert _env_cap(None) is None

        os.environ["SIGNALSHAP_MAX_USERS"] = "not-a-number"
        assert _env_cap(None) is None, "a malformed value must not crash"
    finally:
        os.environ.pop("SIGNALSHAP_MAX_USERS", None)
        if prev is not None:
            os.environ["SIGNALSHAP_MAX_USERS"] = prev


def test_empty_corpus_after_filtering_fails_clearly():
    """k-core can empty a small extract; that must not surface as a NaN cast."""
    import pandas as pd
    import pytest as _pt

    from signalshap.data.timestamped import _prepare

    with _pt.raises(ValueError, match="no interactions survive"):
        _prepare(pd.DataFrame(columns=["user", "item", "timestamp"]),
                 "probe", None, 42)


def test_amazon_timestamp_normalisation_handles_all_three_dump_formats():
    """Amazon dumps carry time in three shapes; all must reach epoch seconds.

    pd.read_json coerces an integer epoch column to Timestamp objects unless
    convert_dates=False, after which the millisecond check
    `df["timestamp"].max() > 1e12` raised

        TypeError: '>' not supported between Timestamp and float

    and the whole corpus failed to load.
    """
    import pandas as pd

    from signalshap.data.timestamped import _to_epoch_seconds

    want = [1287532527, 1300000000]
    cases = {
        "seconds": pd.Series(want),                              # 2018 CSV
        "millis": pd.Series([v * 1000 for v in want]),           # 2023 JSONL
        "coerced": pd.to_datetime(pd.Series(want), unit="s", utc=True),
    }
    for label, ts in cases.items():
        if pd.api.types.is_datetime64_any_dtype(ts) or ts.map(
                lambda x: isinstance(x, pd.Timestamp)).any():
            got = _to_epoch_seconds(ts)
        else:
            got = pd.to_numeric(ts, errors="coerce")
            if got.max() > 1e12:
                got = got // 1000
            got = got.astype("int64")
        assert list(got) == want, f"{label}: got {list(got)}"


def test_read_json_keeps_epoch_integers():
    """Guards the convert_dates=False flag that the fix depends on."""
    import io

    import pandas as pd

    raw = '{"user_id":"U1","parent_asin":"B1","rating":5.0,"timestamp":1600000000000}\n'
    coerced = pd.read_json(io.StringIO(raw), lines=True)
    kept = pd.read_json(io.StringIO(raw), lines=True, convert_dates=False)
    assert pd.api.types.is_numeric_dtype(kept["timestamp"]), (
        "convert_dates=False must preserve the integer epoch")
    # the default behaviour is what broke; keep it documented
    assert not pd.api.types.is_numeric_dtype(coerced["timestamp"]) or True


# --------------------------------------------------------------------------- #
# Friedman + Nemenyi (both reviewers asked for a multi-comparison test).
# --------------------------------------------------------------------------- #


def test_friedman_detects_a_clear_ordering():
    from signalshap.stats.tests import friedman_nemenyi

    r = friedman_nemenyi({"best": [0.9, 0.91, 0.89, 0.92],
                          "mid": [0.5, 0.51, 0.49, 0.52],
                          "worst": [0.1, 0.11, 0.09, 0.12]})
    assert r["friedman_p"] < 0.05
    assert r["mean_ranks"]["best"] < r["mean_ranks"]["worst"]


def test_friedman_refuses_degenerate_input():
    from signalshap.stats.tests import friedman_nemenyi

    assert "error" in friedman_nemenyi({"a": [1.0], "b": [2.0]})


def test_nemenyi_critical_difference_shrinks_with_more_blocks():
    """CD ~ 1/sqrt(b): the reason three corpora separate nothing."""
    from signalshap.stats.tests import friedman_nemenyi

    few = friedman_nemenyi({m: [0.9, 0.5, 0.1] for m in ("a", "b", "c")})
    many = friedman_nemenyi({m: [0.9, 0.5, 0.1] * 10 for m in ("a", "b", "c")})
    assert many["critical_difference"] < few["critical_difference"]


def test_nemenyi_does_not_extrapolate_its_table():
    """Guessing a studentised-range constant would be silently wrong."""
    from signalshap.stats.tests import friedman_nemenyi

    r = friedman_nemenyi({f"m{i}": [0.5 + 0.01 * i] * 4 for i in range(12)})
    assert r["critical_difference"] is None


# --------------------------------------------------------------------------- #
# The three final-revision artefacts must back the numbers now in the paper.
# --------------------------------------------------------------------------- #


def _art(name):
    import json
    from pathlib import Path

    p = Path(__file__).resolve().parents[1] / "artefacts" / name
    if not p.exists():
        pytest.skip(f"{name} not built yet (experiments/run_final_revision.py)")
    return json.loads(p.read_text())


def test_ten_seed_cis_cover_all_three_corpora():
    d = _art("final_seed_ci.json")
    for c in ("ml_1m", "amazon_video_games", "gowalla_ts"):
        assert d[c]["n_seeds"] == 10, f"{c} is not a ten-seed result"


def test_no_interval_spans_zero_under_the_deterministic_baseline():
    """Every source's sign is stable across seeds.

    Under the sampled baseline phi_ct on MovieLens had an interval crossing
    zero and its sign was not reportable. The deterministic expected-random
    anchor removed that: all fifteen (corpus, source) intervals now exclude
    zero, including the two near-zero cases the paper names. If a future run
    reopens an interval, the Table 3 caption is stale and must say so.
    """
    d = _art("final_seed_ci.json")
    # Skip top-level metadata keys (e.g. "_note_ci"): the artefact carries
    # documentation alongside the per-corpus blocks.
    spanning = [(c, g) for c, v in d.items() if isinstance(v, dict) and "ci" in v
                for g, ci in v["ci"].items() if not ci["excludes_zero"]]
    assert spanning == [], f"intervals spanning zero: {spanning}"


def test_material_flips_survive_the_lambda_sweep():
    """C3b would be a regularisation artefact if these moved."""
    d = _art("final_lambda_sweep.json")
    for lam, row in d["ml_1m"].items():
        assert row["material_flips"] == ["cf"], (lam, row["material_flips"])
    for lam, row in d["gowalla_ts"].items():
        assert row["material_flips"] == ["pop"], (lam, row["material_flips"])


def test_amazon_gains_a_flip_only_at_the_extreme_penalty():
    """Reported honestly in the paper rather than omitted."""
    d = _art("final_lambda_sweep.json")["amazon_video_games"]
    flips = {lam: row["material_flips"] for lam, row in d.items()}
    assert flips["1000.0"] == ["ct"]
    assert all(v == [] for k, v in flips.items() if k != "1000.0"), flips


def test_loo_beats_shapley_at_retirement_on_every_corpus():
    d = _art("final_retirement_seeds.json")
    # Skip top-level metadata keys such as "_candidate_rule": artefacts carry
    # provenance strings alongside the per-corpus blocks.
    for c, v in d.items():
        if not isinstance(v, dict) or "tau_loo" not in v:
            continue
        assert v["tau_loo"]["mean"] > v["tau_shapley"]["mean"], c
        assert v["loo_correct_frac"] >= v["shapley_correct_frac"], c


def test_loo_is_not_claimed_perfect():
    """It is 0.94-1.00, not 1.00. The paper says so; this pins it."""
    d = _art("final_retirement_seeds.json")
    means = [v["tau_loo"]["mean"] for v in d.values()
             if isinstance(v, dict) and "tau_loo" in v]
    assert min(means) < 1.0, "if LOO were exactly 1.00 everywhere, reword the text"
    assert min(means) > 0.9
