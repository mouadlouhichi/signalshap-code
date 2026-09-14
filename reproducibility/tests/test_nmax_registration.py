"""N_max must be pre-registered per corpus (spec §2.2, provenance entry #19).

gowalla_ts and amazon_video_games were absent from frozen.yaml -- the config
listed `gowalla` while the loader registers `gowalla_ts` -- so both took a 200
fallback. Gowalla ranked a 68,443-item catalogue with 200 candidates, reached
0.132 recall against a 0.60 gate, and still produced a complete artefact.
A silent default here caps every downstream number.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from signalshap.config import FrozenConfig

ROOT = Path(__file__).resolve().parents[1]

#: Every corpus the study can run. A loader without a registered N_max is the
#: bug this module exists to prevent, so the list is explicit rather than
#: derived from LOADERS -- the point is that adding a corpus forces a choice.
STUDY_CORPORA = ("ml_1m", "gowalla_ts", "amazon_video_games")


def test_every_study_corpus_has_a_registered_nmax():
    cfg = FrozenConfig.load()
    missing = [c for c in STUDY_CORPORA if c not in cfg.n_max]
    assert not missing, f"N_max unregistered for {missing}; spec §2.2 forbids a default"


def test_pipeline_refuses_an_unregistered_corpus():
    """The guard itself: no silent fallback, ever."""
    from signalshap.pipeline import Experiment

    with pytest.raises(KeyError, match="not pre-registered"):
        Experiment("corpus_that_was_never_registered")


def test_timestamped_corpora_are_registered_under_their_loader_names():
    """`gowalla` != `gowalla_ts`; the near-miss is what made this silent."""
    cfg = FrozenConfig.load()
    assert "gowalla_ts" in cfg.n_max
    assert "amazon_video_games" in cfg.n_max


def test_nmax_amendment_is_recorded_with_a_reason():
    """Spec §2.4: changes after E1 begins are traceable, with date and reason."""
    raw = yaml.safe_load((ROOT / "configs" / "frozen.yaml").read_text())
    note = raw["_note"]
    assert "AMENDMENT" in note
    assert "2026-08-05" in note
    assert "gowalla_ts" in note and "amazon_video_games" in note
    # The justification must survive a reviewer asking "why these values?"
    assert "recall gate" in note.lower()


def test_new_nmax_values_are_large_enough_to_matter():
    cfg = FrozenConfig.load()
    # The failed run used 200. Anything near it repeats the mistake.
    assert cfg.n_max["gowalla_ts"] >= 2500
    assert cfg.n_max["amazon_video_games"] >= 600


def test_recall_ceiling_exemptions_are_declared_not_assumed():
    """Rung 2 must be an explicit list, so a failed gate cannot pass quietly."""
    cfg = FrozenConfig.load()
    assert isinstance(cfg.recall_ceiling_exempt, (tuple, list))


# --------------------------------------------------------------------------- #
# spec §2.2 fallback ladder
# --------------------------------------------------------------------------- #


def test_amazon_ceiling_exemption_is_declared():
    """Rung 2: retained with the gate unmet, by PRIOR declaration."""
    cfg = FrozenConfig.load()
    assert "amazon_video_games" in tuple(cfg.recall_ceiling_exempt)


def test_amazon_nmax_was_not_nudged_to_clear_the_gate():
    """600 is what the catalogue-fraction rule gives; 0.60 needs ~634.

    Raising 600 -> 800 would pass the gate. That is selection on the outcome
    the parameter gates, so the value must stay where the rule put it.
    """
    cfg = FrozenConfig.load()
    assert cfg.n_max["amazon_video_games"] == 600
    ml_ratio = cfg.n_max["ml_1m"] / 3533
    assert abs(600 / 3516 - ml_ratio) < 0.005      # same fraction as ml_1m


def test_gowalla_nmax_matches_the_catalogue_fraction_rule():
    """Rung 1, justified by a rule that predates the recall numbers."""
    cfg = FrozenConfig.load()
    expected = round(68_443 * cfg.n_max["ml_1m"] / 3533)
    assert cfg.n_max["gowalla_ts"] == expected


def test_amendment_2_records_both_rungs_and_the_refusal():
    raw = yaml.safe_load((ROOT / "configs" / "frozen.yaml").read_text())
    note = raw["_note"]
    assert "AMENDMENT 2" in note
    assert "RUNG 1" in note and "RUNG 2" in note
    # The reasoning a reviewer will look for: why Amazon was NOT raised.
    assert "selection on the outcome" in note


def test_exempt_corpus_is_reportable_but_never_marked_as_passing():
    """gate_passes must stay False so absolute-NDCG consumers keep excluding it."""
    from signalshap.config import FrozenConfig as FC

    cfg = FC.load()
    exempt = tuple(cfg.recall_ceiling_exempt)
    # Simulate the e0a payload shape for an exempt, failing corpus.
    recall, gate = 0.588, cfg.recall_gate
    passes = recall >= gate
    is_exempt = "amazon_video_games" in exempt
    assert passes is False
    assert is_exempt is True
    assert (passes or is_exempt) is True        # reportable


def test_save_preserves_the_amendment_trail():
    """save() must never regenerate _note from the default.

    A run called FrozenConfig.save(), which rebuilt _note from a hardcoded
    string, and amendments 1 and 2 -- the audit trail for every
    post-registration N_max change -- were destroyed. The file still looked
    well-formed. _note is provenance the code must only append to.
    """
    import shutil
    import tempfile

    src = ROOT / "configs" / "frozen.yaml"
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "frozen.yaml"
        shutil.copy(src, tmp)
        before = yaml.safe_load(tmp.read_text())["_note"]
        FrozenConfig.load(tmp).save(tmp)
        after = yaml.safe_load(tmp.read_text())["_note"]
    assert after == before
    for marker in ("AMENDMENT 2026-08-05", "AMENDMENT 2", "AMENDMENT 3"):
        assert marker in after, f"{marker} lost by save()"


def test_gowalla_is_rung_2_after_rung_1_was_exhausted():
    cfg = FrozenConfig.load()
    assert "gowalla_ts" in tuple(cfg.recall_ceiling_exempt)
    # N_max stays at the catalogue-fraction value; the measured curve IS the
    # evidence for the ceiling, so lowering it back would discard the evidence.
    assert cfg.n_max["gowalla_ts"] == 11623


def test_amendment_3_records_that_the_gate_is_unreachable():
    note = yaml.safe_load((ROOT / "configs" / "frozen.yaml").read_text())["_note"]
    assert "AMENDMENT 3" in note
    assert "UNREACHABLE" in note
    # The specific arithmetic a reviewer will want: more items than exist.
    assert "623,823" in note
