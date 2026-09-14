#!/usr/bin/env python3
"""Refresh reproducibility/ from the research repo.

    python scripts/sync_reproducibility.py [--check]

`reproducibility/` is the standalone tree cited in the paper. It must be a
byte-identical mirror of the code that produced the results, so it is synced
by a script rather than by hand: a manual copy drifts, and a drifted release
means a reviewer clones it, gets different numbers, and the reproducibility
claim collapses. `tests/test_reproducibility_release.py` fails on drift;
this script fixes it.

`--check` reports what would change without writing, for CI.
"""
from __future__ import annotations

import argparse
import filecmp
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REL = ROOT / "reproducibility"

#: Directories mirrored wholesale.
MIRROR_DIRS = ("src", "configs")

#: Entry points a reproducer needs. Deliberately a whitelist, not everything
#: in scripts/: the manuscript tooling (check_discover_ai, check_latex,
#: make_elsevier, make_round8_notebook, make_assets' paper publishing) is
#: repo-internal and would be dead weight or actively confusing in a release.
#: Runnable entry points, grouped by purpose in the release. Deliberately a
#: whitelist, not everything in scripts/: the manuscript tooling
#: (check_discover_ai, check_latex, make_elsevier, make_round8_notebook) is
#: repo-internal and would be dead weight or actively confusing in a release.
SCRIPT_DIRS = {
    "data_preparation": (
        "fetch_benchmarks.sh",
        "fetch_timestamped.sh",
        "audit_repeat_items.py",
        "audit_global_time.py",
        "measure_kcore_sweep.py",
    ),
    "experiments": (
        "run_study.py",
        "run_final_revision.py",
        "run_full_revision.py",
        "run_revision_experiments.py",
        "run_protocol_sensitivity.py",
        "run_global_timeblock.py",
        "run_pool_sensitivity.py",
        "rerun_all.sh",
        "run_round8_remaining.sh",
    ),
    "scripts": (
        "make_assets.py",
        "make_manifest.py",
        "check_paper_numbers.py",
        "check_run_valid.py",
    ),
}

#: Tests that read the manuscript or this repo's layout. Shipping them would
#: hand a reviewer 13 failures on a clean clone, which reads as a broken
#: artefact rather than as an absent manuscript.
TESTS_EXCLUDED = {
    "test_reporting_consistency.py",
    "test_elsevier_conversion.py",
    "test_round8_notebook.py",
    "test_figures_are_current.py",
    "test_reproducibility_release.py",
}

#: Files copied from the repo root.
ROOT_FILES = ("LICENSE", "requirements.txt", "pyproject.toml")


def _digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _relocated(text: str) -> str:
    """Rewrite `scripts/NAME` to the release directory that holds NAME.

    The research repo keeps every runner in scripts/; the release groups them
    by purpose. Shell drivers and docstrings invoke siblings by path, so a
    straight copy would leave `bash scripts/run_study.py` pointing at nothing.
    Applied to text files on the way in, and inverted on the way out by
    `_content_matches`, so byte-drift checks still compare like with like.
    """
    for dest_dir, names in SCRIPT_DIRS.items():
        if dest_dir == "scripts":
            continue
        for name in names:
            text = text.replace(f"scripts/{name}", f"{dest_dir}/{name}")
    return text


def _content_for(src: Path, dst: Path) -> bytes:
    """Bytes to write at `dst`, with paths relocated for text files."""
    raw = src.read_bytes()
    if src.suffix not in (".py", ".sh", ".md", ".yaml", ".yml", ".toml"):
        return raw
    try:
        return _relocated(raw.decode()).encode()
    except UnicodeDecodeError:
        return raw


def _plan() -> list[tuple[Path, Path]]:
    """(source, destination) pairs, ignoring caches."""
    pairs: list[tuple[Path, Path]] = []
    for d in MIRROR_DIRS:
        for src in sorted((ROOT / d).rglob("*")):
            if src.is_dir() or "__pycache__" in src.parts:
                continue
            pairs.append((src, REL / src.relative_to(ROOT)))
    for dest_dir, names in SCRIPT_DIRS.items():
        for name in names:
            src = ROOT / "scripts" / name
            if src.exists():
                pairs.append((src, REL / dest_dir / name))
    for src in sorted((ROOT / "tests").glob("*.py")):
        if src.name not in TESTS_EXCLUDED:
            pairs.append((src, REL / "tests" / src.name))
    for name in ROOT_FILES:
        pairs.append((ROOT / name, REL / name))
    for src in sorted((ROOT / "artefacts").glob("*.json")):
        pairs.append((src, REL / "artefacts" / src.name))
    pairs.append((ROOT / "artefacts" / "PROVENANCE.md",
                  REL / "artefacts" / "PROVENANCE.md"))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report drift without writing")
    a = ap.parse_args()

    changed, added = [], []
    for src, dst in _plan():
        if not src.exists():
            continue
        rel = dst.relative_to(REL)
        payload = _content_for(src, dst)
        if not dst.exists():
            added.append(str(rel))
        elif dst.read_bytes() != payload:
            changed.append(str(rel))
        if not a.check:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(payload)
            shutil.copymode(src, dst)

    # Orphans: present in the release, gone from the repo.
    wanted = {d for _, d in _plan()}
    orphans = []
    for d in ("src", "configs", "scripts", "tests",
              "data_preparation", "experiments"):
        for p in sorted((REL / d).rglob("*")):
            if p.is_dir() or "__pycache__" in p.parts:
                continue
            if p not in wanted:
                orphans.append(str(p.relative_to(REL)))
                if not a.check:
                    p.unlink()

    if not a.check:
        for cache in REL.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)

    for label, items in (("changed", changed), ("added", added),
                         ("removed", orphans)):
        if items:
            print(f"{label} ({len(items)}):")
            for i in items[:20]:
                print("   ", i)
            if len(items) > 20:
                print(f"    ... and {len(items) - 20} more")

    if a.check:
        if changed or added or orphans:
            print("\nreproducibility/ is STALE. Run "
                  "`python scripts/sync_reproducibility.py`.")
            return 1
        print("reproducibility/ is in sync")
        return 0

    total = len(changed) + len(added) + len(orphans)
    print(f"synced reproducibility/ ({total} file(s) touched)"
          if total else "reproducibility/ was already in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
