"""Frozen configuration. Spec §2.2 (N_max), §2.4 (lambda), §2.5 (v_0 seed).

Everything here is pre-registered in Week 1 and must not be tuned afterwards.
Loaded from configs/frozen.yaml so the values live in one place and the
manuscript can cite the file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIGS = ROOT / "configs"
ARTEFACTS = ROOT / "artefacts"
PROCESSED = ROOT / "data" / "processed"

#: The five players. Order is fixed and used for deterministic tie-breaking.
SOURCES: tuple[str, ...] = ("cf", "ct", "pop", "rec", "seq")

#: Spec §11: all figures/tables report mean +/- std across these seeds.
SEEDS: tuple[int, ...] = (42, 43, 44, 45, 46)

#: Spec §2.5: the frozen v_0 permutation is drawn once under this seed.
V0_SEED = 42

#: Spec §2.2: candidate recall gate.
RECALL_GATE = 0.60

#: Spec §6.2: strict density ordering required by C3, sparsest first.
DENSITY_ORDER = ("gowalla_ts", "amazon_video_games", "ml_1m")
DENSITY_MARGIN = 1.5


@dataclass(frozen=True)
class FrozenConfig:
    """Pre-registered values. Frozen at end of Week 1 (spec §15)."""

    #: Spec §2.2 -- pre-registered per dataset, never a single global constant.
    n_max: dict[str, int] = field(
        default_factory=lambda: {"ml_1m": 200, "lastfm_2k": 500, "amazon_book": 1000}
    )
    #: Spec §2.2 rung 2 -- corpora whose recall gate is knowingly unmet at the
    #: largest affordable N_max. Reported as a disclosed ceiling, never hidden.
    recall_ceiling_exempt: tuple[str, ...] = ()
    #: Spec §2.4 -- chosen once on an ML-1M pilot, then frozen. NEVER per-coalition.
    ridge_lambda: float = 1.0
    v0_seed: int = V0_SEED
    seeds: tuple[int, ...] = SEEDS
    recall_gate: float = RECALL_GATE
    #: Growth loop (spec §2.3).
    max_growth_iters: int = 10
    #: NDCG cutoff -- this is the characteristic function (spec §2.5).
    k_ndcg: int = 10

    @classmethod
    def load(cls, path: Path | None = None) -> "FrozenConfig":
        path = path or CONFIGS / "frozen.yaml"
        if not path.exists():
            return cls()
        raw = yaml.safe_load(path.read_text()) or {}
        raw.pop("_note", None)
        if "seeds" in raw:
            raw["seeds"] = tuple(raw["seeds"])
        return cls(**raw)

    def save(self, path: Path | None = None) -> Path:
        path = path or CONFIGS / "frozen.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        blob = asdict(self)
        blob["seeds"] = list(self.seeds)
        # PRESERVE the existing note. It accumulates dated amendments that are
        # the audit trail for every post-registration parameter change, and
        # regenerating it from the default silently destroyed amendments 1 and
        # 2 the first time a run happened to call save(). _note is provenance,
        # not a field the code owns; only append to it, never overwrite.
        note = None
        target = path
        if target.exists():
            try:
                prior = yaml.safe_load(target.read_text()) or {}
                note = prior.get("_note")
            except (yaml.YAMLError, OSError):
                note = None
        blob["_note"] = note or (
            "PRE-REGISTERED, spec §2.2/§2.4/§2.5. Frozen end of Week 1. "
            "lambda is NEVER tuned per coalition; n_max changes after E1 begins "
            "must be recorded in the artefact with date and reason."
        )
        path.write_text(yaml.safe_dump(blob, sort_keys=False))
        return path


def write_artefact(name: str, payload: dict) -> Path:
    """Every quantitative claim traces to a JSON here (spec §14, rule 1)."""
    ARTEFACTS.mkdir(parents=True, exist_ok=True)
    p = ARTEFACTS / name
    p.write_text(json.dumps(payload, indent=2, default=str))
    return p


def read_artefact(name: str) -> dict:
    return json.loads((ARTEFACTS / name).read_text())


def admissible(name: str, e0a: dict, cfg: "FrozenConfig | None" = None) -> tuple[bool, str | None]:
    """May this corpus appear in the manuscript, and under what restriction?

    Spec §2.2 separates two things that a single boolean conflates:

      * ``gate_passes`` -- did candidate recall clear 0.60? A fact about the
        run, frozen at the moment it was written.
      * admissibility -- may the numbers be reported? A *policy* decision,
        governed by the rung-2 exemption list in ``frozen.yaml``.

    Exemption is resolved from the LIVE config, never from the artefact. A run
    predates the declaration that admits it: gowalla_ts was executed while only
    amazon_video_games was exempt, so its artefact carries
    ``reportable: false``. Trusting that stale field would have silently
    dropped a corpus that policy now admits, and re-running a three-hour job to
    change one boolean would be absurd. The artefact records measurements; the
    config records decisions.

    Returns ``(admissible, restriction)`` where restriction is None for a clean
    pass and otherwise the sentence that must accompany the corpus wherever it
    is reported.
    """
    cfg = cfg or FrozenConfig.load()
    recall = e0a.get("candidate_recall")
    if e0a.get("gate_passes", True):
        return True, None
    if name in tuple(cfg.recall_ceiling_exempt):
        return True, (
            f"RUNG 2 (spec §2.2): candidate recall {recall:.3f} < "
            f"{cfg.recall_gate} at the pre-registered N_max="
            f"{e0a.get('n_max')}. Retained for RELATIVE contrasts "
            f"(LOO-vs-Shapley); EXCLUDED from absolute-NDCG comparison. The "
            f"ceiling must be stated wherever this corpus is reported."
        )
    return False, (
        f"NOT REPORTABLE: recall gate failed ({recall:.3f}) and no rung-2 "
        f"exemption is declared for '{name}' in configs/frozen.yaml."
    )
