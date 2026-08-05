"""The degenerate-player audit, and the loaders' content supply.

Regression cover for provenance entry #17: `ct` and `rec` had bit-identical
Shapley values on gowalla_ts and amazon_video_games because the timestamped
loaders built their Dataset with meta=None, leaving both players with no input.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from signalshap.data import timestamped as ts
from signalshap.scorers.audit import audit_players, enforce_player_audit


def _cands(n_users=4, n_items=6):
    return [np.arange(n_items) for _ in range(n_users)]


def test_all_zero_matrix_is_degenerate():
    rng = np.random.default_rng(0)
    scores = {
        "live": rng.normal(size=(4, 6)).astype(np.float32),
        "dead": np.zeros((4, 6), dtype=np.float32),
    }
    rep = audit_players(scores, _cands())
    assert rep["degenerate_players"] == ["dead"]
    assert rep["dead"]["all_zero"] is True
    assert rep["live"]["degenerate"] is False


def test_constant_within_user_is_degenerate():
    """The `rec` failure mode: varies across users, flat within each one."""
    per_user = np.arange(4, dtype=np.float32)[:, None]
    scores = {"rec_like": np.tile(per_user, (1, 6))}
    rep = audit_players(scores, _cands())
    assert rep["degenerate_players"] == ["rec_like"]
    # It is NOT all-zero -- only the audit's flatness test catches this one.
    assert rep["rec_like"]["all_zero"] is False


def test_variation_outside_candidates_does_not_rescue_a_player():
    """A source flat on the candidate slices cannot move NDCG@10."""
    M = np.zeros((4, 20), dtype=np.float32)
    M[:, 10:] = np.arange(10)          # lots of variation, none of it ranked
    rep = audit_players({"s": M}, [np.arange(10) for _ in range(4)])
    assert rep["s"]["degenerate"] is True


def test_enforce_raises_in_strict_mode_and_warns_otherwise():
    rep = {"degenerate_players": ["ct", "rec"]}
    with pytest.raises(ValueError, match="item_meta"):
        enforce_player_audit("gowalla_ts", rep, strict=True)
    with pytest.warns(RuntimeWarning):
        enforce_player_audit("gowalla_ts", rep, strict=False)


def test_enforce_is_silent_when_all_players_live():
    assert enforce_player_audit("x", {"degenerate_players": []}, strict=True) == {
        "degenerate_players": []
    }


# --------------------------------------------------------------------------- #
# content supply
# --------------------------------------------------------------------------- #


def test_gowalla_geo_tags_are_nested_and_distinguish_venues():
    geo = pd.DataFrame({
        "item": ["a", "b", "c"],
        "lat": [40.71, 40.715, 34.05],     # a,b same neighbourhood; c far
        "lon": [-74.00, -74.005, -118.24],
    })
    meta = ts._gowalla_meta(geo, pd.Series(["a", "b", "c"]))
    tags = dict(zip(meta["item"], meta["tags"]))
    assert all(len(t.split()) == 6 for t in tags.values())   # 3 res x 2 offsets
    a, b, c = (set(tags[k].split()) for k in "abc")
    # Straddling longitude -74.0 exactly: with a single grid these two shared
    # NOTHING. The offset grid must give them a token at every resolution.
    # A half-offset grid cannot guarantee agreement when a pair sits half a
    # cell apart in BOTH axes, which is the case here at the 1 km resolution --
    # and at that scale they genuinely are different cells. What must hold is
    # that the coarser resolutions still place them together.
    for res in ("g1", "g2"):
        assert any(t.startswith(res) for t in a & b), res
    assert not (a & c)              # different continent-scale cell
    assert a != b                   # fine cells still separate them


def test_gowalla_meta_is_not_empty_so_ct_can_score():
    geo = pd.DataFrame({"item": ["a"], "lat": [1.0], "lon": [2.0]})
    meta = ts._gowalla_meta(geo, pd.Series(["a"]))
    assert meta["tags"].str.strip().astype(bool).all()


def test_amazon_meta_reads_categories(tmp_path):
    (tmp_path / "meta_Video_Games.jsonl").write_text(
        '{"parent_asin":"A1","categories":["Video Games","PC"],"store":"Acme"}\n'
        '{"parent_asin":"A2","categories":["Video Games","Consoles"]}\n'
    )
    meta = ts._amazon_meta(tmp_path, pd.Series(["A1", "A2", "A3"]))
    tags = dict(zip(meta["item"], meta["tags"]))
    assert "video_games" in tags["A1"] and "pc" in tags["A1"]
    assert "acme" in tags["A1"]
    assert "consoles" in tags["A2"]
    assert tags["A3"] == ""         # unknown item -> empty, never invented


def test_amazon_meta_absent_returns_empty_rather_than_guessing(tmp_path):
    meta = ts._amazon_meta(tmp_path, pd.Series(["A1"]))
    assert list(meta["tags"]) == [""]


def test_prepare_relabels_meta_to_reindexed_item_ids():
    """Tags must follow items through _reindex, or ct scores the wrong rows."""
    df = pd.DataFrame({
        "user": [f"u{i // 12}" for i in range(48)],
        "item": [f"i{i % 12}" for i in range(48)],
        "timestamp": np.arange(48) * 86400 + 1_500_000_000,
    })
    src = lambda kept: pd.DataFrame({"item": kept.values,
                                     "tags": [f"tag_{k}" for k in kept.values]})
    ds = ts._prepare(df, "unit", None, 0, meta_source=src)
    assert list(ds.item_meta["item"]) == list(range(ds.n_items))
    # raw ids sort as i0, i1, i10, i11, i2, ... -- position, not numeric order
    assert ds.item_meta["tags"].iloc[0] == "tag_" + sorted(df["item"].unique())[0]
    assert ds.item_meta["tags"].str.strip().astype(bool).all()


# --------------------------------------------------------------------------- #
# Shapley axioms not covered by the duplicate-injection diagnostic
# --------------------------------------------------------------------------- #


def test_additivity_axiom_holds():
    """phi(v1+v2) = phi(v1)+phi(v2).

    Additivity is one of the four axioms giving the Shapley value its
    uniqueness, and the only one no other diagnostic exercises: efficiency is a
    sum constraint, symmetry is covered by duplicate injection, and the
    null player has its own analytic game. An implementation can pass all
    three and still mishandle superposition.
    """
    from signalshap.experiments.synthetic_games import additivity_check

    r = additivity_check()
    assert r["passes"], r
    assert r["max_abs_error"] < 1e-12
    # The summands must have DIFFERENT structure, or the test is vacuous.
    assert r["phi_v1"] != r["phi_v2"]


def test_null_player_receives_exactly_zero():
    from signalshap.experiments.synthetic_games import build_suite
    from signalshap.game.core import exact_shapley

    v, exact = build_suite()["null_player"]
    players = tuple(sorted({p for S in v for p in S}))
    got = exact_shapley({S: float(x) for S, x in v.items()}, players)
    assert abs(got["null"]) < 1e-12
    assert float(exact["null"]) == 0.0
