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
