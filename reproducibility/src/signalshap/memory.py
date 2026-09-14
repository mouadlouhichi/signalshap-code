"""Corpus sizing against available RAM (spec §5, provenance entry #18).

Five dense score matrices at ``n_users x n_items x float32`` dominate peak
memory. Gowalla at its full 52,985 x 121,866 needs 129 GB for the matrices
alone and roughly 207 GB at peak -- it cannot be attempted on any laptop, so
it must be subsampled by DERIVATION from a memory budget, never by hope.

This logic previously lived inside ``experiments/run_full_revision.py``. That is
why ``experiments/run_study.py`` was OOM-killed on Gowalla: it called the pipeline
directly, never set ``SIGNALSHAP_MAX_USERS``, and so the loaders' ``_env_cap``
returned ``None`` and loaded all 53k users. Sizing that only one entry point
performs is not a safeguard; it is a coincidence. Both scripts now share this
module.
"""

from __future__ import annotations

import os
import subprocess

#: Peak resident memory is roughly this multiple of the five score matrices:
#: the robustness sweep holds a second game alive while the neural baselines
#: add two more dense matrices.
PEAK_MULTIPLIER = 1.6

#: Never subsample below this; a smaller corpus stops being informative.
MIN_USERS = 500


def free_gb() -> float:
    """Available RAM in GB. Falls back to a conservative guess."""
    try:                                    # macOS
        vm = subprocess.check_output(["vm_stat"], text=True)
        page = int(vm.split("page size of")[1].split("bytes")[0])
        free = inactive = 0
        for line in vm.splitlines():
            if line.startswith("Pages free:"):
                free = int(line.split(":")[1].strip().rstrip("."))
            elif line.startswith("Pages inactive:"):
                inactive = int(line.split(":")[1].strip().rstrip("."))
        return (free + inactive) * page / 1e9
    except Exception:
        pass
    try:                                    # Linux
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024 / 1e9
    except Exception:
        pass
    return 8.0


def default_budget_gb(explicit: float | None = None) -> float:
    """Budget for the score matrices: 60% of free RAM unless overridden."""
    return explicit if explicit else max(4.0, 0.6 * free_gb())


def fit_users(n_items: int, budget_gb: float, n_users: int = 10 ** 9) -> int:
    """Largest user count whose five score matrices fit the budget."""
    cap = int(budget_gb * 1e9 / (PEAK_MULTIPLIER * 5 * max(n_items, 1) * 4))
    return max(MIN_USERS, min(cap, n_users))


def scores_gb(n_users: int, n_items: int) -> float:
    """Size of the five float32 score matrices, in GB."""
    return 5 * n_users * n_items * 4 / 1e9


#: Corpus dimensions the manuscript's reported numbers were produced at. A run
#: whose memory budget silently resizes one of these is measuring a DIFFERENT
#: corpus, not reproducing this one. Learned the hard way: a 12.6 GB re-run
#: admitted 4,652 of 8,865 Gowalla users and 59,597 of 82,134 items, moved the
#: attributions by up to 36%, and overwrote the 24 GB artefact in place.
PAPER_CORPUS_SHAPE = {
    "ml_1m": (6038, 3533),
    "amazon_video_games": (7120, 3516),
    "gowalla_ts": (8865, 82134),
}


def check_paper_shape(name: str, n_users: int, n_items: int) -> tuple[bool, str]:
    """Does this loaded corpus match the one the manuscript describes?"""
    want = PAPER_CORPUS_SHAPE.get(name)
    if want is None:
        return True, ""
    if (n_users, n_items) == want:
        return True, ""
    return False, (
        f"{name}: loaded {n_users:,} x {n_items:,} but the manuscript reports "
        f"{want[0]:,} x {want[1]:,}. The memory budget derives the user cap, so "
        f"a smaller --budget-gb silently substitutes a different corpus. Results "
        f"from this run are valid but are NOT comparable with the paper's tables; "
        f"write them to a separate artefact. Gowalla needs about 24 GB."
    )


def size_corpus(name: str, loader, budget_gb: float,
                max_users: int | None = None, probe_users: int = 1500,
                verbose: bool = True) -> int:
    """Derive and INSTALL a user cap for one corpus.

    Loads a small probe purely to learn the catalogue size, scales that
    estimate up (a larger user sample reaches more items, so the probe
    under-counts and over-estimating is the safe direction), then sets
    ``SIGNALSHAP_MAX_USERS`` so every downstream loader honours it.

    Returns the installed cap.
    """
    os.environ["SIGNALSHAP_MAX_USERS"] = str(max_users or probe_users)
    probe = loader()
    est_items = probe.n_items * 3
    n_items_probe = probe.n_items
    del probe

    cap = fit_users(est_items, budget_gb)
    if max_users:
        cap = min(cap, max_users)
    os.environ["SIGNALSHAP_MAX_USERS"] = str(cap)
    if verbose:
        print(f"{name}: ~{est_items:,} items (est, probe saw {n_items_probe:,}) "
              f"-> {cap:,} users fit a {budget_gb:.0f} GB budget")
    return cap


def check_fits(name: str, n_users: int, n_items: int,
               budget_gb: float) -> tuple[bool, str]:
    """Post-load guard: did the derived cap actually bring us under budget?"""
    gb = scores_gb(n_users, n_items)
    if gb > budget_gb:
        return False, (
            f"{name}: {n_users:,} x {n_items:,} needs {gb:.1f} GB of score "
            f"matrices, over the {budget_gb:.1f} GB budget. Lower --budget-gb "
            f"or pass --max-users; do not run this, it will be OOM-killed."
        )
    return True, f"{name}: loaded {n_users:,} users x {n_items:,} items ({gb:.1f} GB of scores)"
