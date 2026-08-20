"""Degenerate-player audit (spec §4, provenance entry #17).

A source can be null for two very different reasons:

  (a) it carries real information that the other sources already subsume, or
      that simply does not help the ranking -- an EVIDENTIAL null, which is a
      legitimate finding; or
  (b) it was never given any input, so its score matrix cannot reorder any
      candidate list -- a STRUCTURAL null, which is a data-plumbing bug wearing
      a result's clothing.

Shapley values cannot distinguish the two: both yield phi ~ 0. This module
does, by inspecting the score matrices directly.

This exists because case (b) actually happened. ``timestamped._prepare``
called ``_finalise(..., meta=None)``, which fabricates an ``item_meta`` frame
with empty ``tags``. On ``gowalla_ts`` and ``amazon_video_games`` that made
``score_ct`` return an all-zero matrix and forced ``score_rec`` into a single
content cluster, so its weights were constant within each user. The two
players' Shapley entries came out BIT-IDENTICAL on both corpora -- two nulls
that looked like a cross-corpus regularity and were in fact the same missing
metadata twice. Reported as null evidence, that would have been a fabricated
finding.

The audit is cheap (one pass over the candidate slices) and runs before any
Shapley computation, so a structurally dead player is caught at the point it
is created rather than inferred from the shape of the output table.
"""

from __future__ import annotations

import os
import warnings

import numpy as np

#: A player is flagged when at least this fraction of users see a candidate
#: slice with no usable variation. Not 1.0: a handful of users can legitimately
#: have a tied slice (e.g. every candidate in the same content cluster).
DEGENERATE_USER_FRACTION = 0.99

#: Range below which a user's candidate scores are treated as tied. Absolute
#: rather than relative because score scales differ by source and a constant
#: offset is exactly what we are looking for.
TIE_TOL = 1e-12


def _slice_is_flat(row: np.ndarray) -> bool:
    finite = row[np.isfinite(row)]
    if finite.size < 2:
        return True
    return bool(finite.max() - finite.min() <= TIE_TOL)


def audit_players(scores: dict[str, np.ndarray],
                  candidates: dict[int, np.ndarray] | None = None,
                  user_fraction: float = DEGENERATE_USER_FRACTION) -> dict:
    """Measure each source's ability to reorder the candidate sets.

    Parameters
    ----------
    scores
        Source name -> user x item score matrix, already seen-masked.
    candidates
        User -> candidate item ids. When given, the audit looks only at the
        slices the characteristic function actually ranks, which is the honest
        test: a source may vary over the full catalogue and still be flat on
        every candidate list, in which case it cannot move NDCG@10 either.
        When ``None``, the whole row is used.

    Returns
    -------
    dict with, per source, the fraction of users whose slice is flat, whether
    the matrix is identically zero, and a ``degenerate`` verdict; plus the
    sorted list of degenerate sources under ``degenerate_players``.
    """
    report: dict[str, dict] = {}
    for name, M in scores.items():
        if candidates is None:
            rows = (M[u] for u in range(M.shape[0]))
            n_users = M.shape[0]
        else:
            # Accept both shapes the pipeline uses: a list indexed by user and
            # a sparse {user: items} mapping.
            pairs = (list(enumerate(candidates))
                     if isinstance(candidates, (list, tuple))
                     else [(u, candidates[u]) for u in sorted(candidates)])
            rows = (M[u, np.asarray(c, dtype=int)] for u, c in pairs)
            n_users = len(pairs)

        flat = sum(_slice_is_flat(np.asarray(r, dtype=np.float64)) for r in rows)
        frac = flat / max(n_users, 1)
        finite = M[np.isfinite(M)]
        all_zero = bool(finite.size == 0 or np.all(finite == 0.0))
        report[name] = {
            "flat_user_fraction": float(frac),
            "all_zero": all_zero,
            "n_users_checked": int(n_users),
            "degenerate": bool(all_zero or frac >= user_fraction),
        }

    report["degenerate_players"] = sorted(
        k for k, v in report.items() if isinstance(v, dict) and v["degenerate"]
    )
    return report


def _explain(ds_name: str, dead: list[str]) -> str:
    hint = ""
    if {"ct", "rec"} & set(dead):
        hint = (
            " `ct` and `rec` both read ds.item_meta['tags']; an empty tags "
            "column kills both at once, which is the signature of a loader "
            "that built its Dataset with meta=None."
        )
    return (
        f"{ds_name}: sources {dead} cannot reorder any candidate list, so "
        f"their Shapley values are structurally zero and carry NO evidence "
        f"about the source's usefulness.{hint} Fix the feature supply or drop "
        f"the players from the game; do not report them as null results."
    )


def enforce_player_audit(ds_name: str, report: dict,
                         strict: bool | None = None) -> dict:
    """Warn -- or raise under strict mode -- when a player is structurally dead.

    Mirrors the synthetic-fallback guard: loud by default, fatal when
    ``SIGNALSHAP_STRICT_DATA=1``, so a headline run cannot quietly ship a
    table of nulls that are really missing inputs.
    """
    dead = report.get("degenerate_players", [])
    if not dead:
        return report
    msg = _explain(ds_name, dead)
    if strict is None:
        strict = os.environ.get("SIGNALSHAP_STRICT_DATA") == "1"
    if strict:
        raise ValueError(msg)
    warnings.warn(msg, RuntimeWarning, stacklevel=2)
    return report
