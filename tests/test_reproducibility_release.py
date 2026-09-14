"""The reproducibility/ release must stay in sync with the research repo.

`reproducibility/` is the standalone tree cited in the paper. It mirrors
`src/`, `tests/`, `configs/` and a selected set of `scripts/`, plus the
released artefacts. A copy that silently drifts from the code that produced
the results is worse than no copy: a reviewer clones it, gets different
numbers, and the paper's reproducibility claim collapses.

These tests check the properties that would break that claim. They compare
file CONTENT, not timestamps.
"""
from __future__ import annotations

import hashlib
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REL = ROOT / "reproducibility"

pytestmark = pytest.mark.skipif(
    not REL.exists(), reason="reproducibility release not present")


def _digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _same(a: Path, b: Path) -> bool:
    """Compare content, allowing for the release's relocated runner paths.

    The research repo keeps every runner in scripts/; the release groups them
    into data_preparation/ and experiments/, and the sync rewrites intra-repo
    invocations accordingly. That rewrite is intentional, so compare the
    rewritten form rather than raw bytes.
    """
    if _digest(a) == _digest(b):
        return True
    spec = importlib.util.spec_from_file_location(
        "_syncmod", ROOT / "scripts" / "sync_reproducibility.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        return mod._relocated(a.read_text()) == b.read_text()
    except UnicodeDecodeError:
        return False


def test_source_tree_is_byte_identical():
    """src/ is the implementation; a fork here changes the results."""
    drift = []
    for a in sorted((ROOT / "src").rglob("*.py")):
        rel = a.relative_to(ROOT)
        b = REL / rel
        if not b.exists():
            drift.append(f"missing in release: {rel}")
        elif not _same(a, b):
            drift.append(f"differs: {rel}")
    assert not drift, "\n".join(drift)


def test_configs_are_byte_identical():
    """frozen.yaml carries N_max and the recall gate; a fork changes outcomes."""
    for a in sorted((ROOT / "configs").glob("*.yaml")):
        b = REL / "configs" / a.name
        assert b.exists(), f"missing: {a.name}"
        assert _same(a, b), f"differs: {a.name}"


#: The release groups runners by purpose; the research repo keeps them all in
#: scripts/. Content must still match exactly.
RUNNER_DIRS = ("scripts", "data_preparation", "experiments")


def test_shipped_scripts_are_byte_identical():
    """A release script must behave exactly like the one that made the numbers."""
    drift = []
    for d in RUNNER_DIRS:
        if not (REL / d).exists():
            continue
        for b in sorted((REL / d).iterdir()):
            if b.is_dir() or b.suffix not in (".py", ".sh"):
                continue
            a = ROOT / "scripts" / b.name
            if not a.exists():
                drift.append(f"release has an orphan script: {d}/{b.name}")
            elif not _same(a, b):
                drift.append(f"differs: {d}/{b.name}")
    assert not drift, "\n".join(drift)


def test_release_has_the_documented_directory_layout():
    """The structure the README and the paper describe."""
    for entry in ("README.md", "requirements.txt", "environment.yml",
                  "configs", "src", "scripts", "data_preparation",
                  "experiments", "tables", "figures"):
        assert (REL / entry).exists(), f"release is missing {entry}"


def test_generated_outputs_are_present():
    """figures/ and tables/ are committed so a fresh run can be compared."""
    assert len(list((REL / "figures").glob("*.png"))) >= 7
    assert len(list((REL / "tables").glob("*.md"))) >= 8


def test_shipped_tests_are_byte_identical():
    drift = []
    for b in sorted((REL / "tests").glob("*.py")):
        a = ROOT / "tests" / b.name
        if not a.exists():
            drift.append(f"release has an orphan test: {b.name}")
        elif not _same(a, b):
            drift.append(f"differs: tests/{b.name}")
    assert not drift, "\n".join(drift)


def test_manuscript_only_tests_are_excluded():
    """They read paper/, which the standalone release does not ship.

    Shipping them would give a reviewer 13 failures on a clean clone, which
    reads as a broken artefact rather than as a missing manuscript.
    """
    for name in ("test_reporting_consistency.py", "test_elsevier_conversion.py",
                 "test_round8_notebook.py", "test_figures_are_current.py",
                 "test_reproducibility_release.py"):
        assert not (REL / "tests" / name).exists(), (
            f"{name} depends on the manuscript or on this repo's layout and "
            f"must not ship in the standalone release")


def test_release_ships_no_manuscript_or_review_material():
    for forbidden in ("paper", "paper-kbs", "paper-reviews", "notebooks",
                      "SUBMISSION_CHECKLIST.md"):
        assert not (REL / forbidden).exists(), (
            f"{forbidden} is repo-internal and must not ship")


def test_release_is_self_contained():
    """Everything a clone needs to run without the parent repo."""
    for f in ("README.md", "LICENSE", "requirements.txt", "pyproject.toml",
              "Makefile", ".gitignore"):
        assert (REL / f).exists(), f"release is missing {f}"
    assert (REL / "artefacts" / "MANIFEST.json").exists()
    assert (REL / "artefacts" / "PROVENANCE.md").exists()


def test_no_script_reaches_outside_the_release():
    """A `../` path would break the moment the folder becomes its own repo."""
    bad = []
    for p in sorted((REL / "scripts").iterdir()):
        if p.is_dir() or p.suffix not in (".py", ".sh"):
            continue
        body = p.read_text(errors="ignore")
        for m in re.findall(r'["\'](\.\./[^"\']*)["\']', body):
            # parents[1] climbs to the release root, which is correct.
            bad.append(f"{p.name}: {m}")
    assert not bad, "\n".join(bad)


def test_readme_references_only_files_that_exist():
    r = (REL / "README.md").read_text()
    missing = []
    for m in set(re.findall(r"scripts/[\w.]+\.(?:py|sh)", r)):
        if not (REL / m).exists():
            missing.append(m)
    for m in set(re.findall(r"src/signalshap/[\w/]+\.py", r)):
        if not (REL / m).exists():
            missing.append(m)
    for m in set(re.findall(r"artefacts/[\w.]+", r)):
        if not (REL / m).exists():
            missing.append(m)
    assert not missing, f"README points at missing files: {sorted(missing)}"


def test_readme_follows_house_style():
    r = (REL / "README.md").read_text()
    assert "\u2014" not in r, "no em dashes in rendered text"
    assert "pre-registered" not in r.lower(), "banned phrase; use 'frozen'"


def test_readme_does_not_claim_pytorch_or_gpu():
    """The implementation is NumPy/SciPy and the paper leans on that."""
    r = (REL / "README.md").read_text().lower()
    assert "pytorch" not in r or "no pytorch" in r
    for claim in ("requires a gpu", "cuda-enabled", "gpu required"):
        assert claim not in r


def test_headline_numbers_in_the_readme_match_the_artefact():
    """The README quotes results; they must come from the shipped artefact."""
    import json

    ci = json.loads((REL / "artefacts" / "final_seed_ci.json").read_text())
    r = (REL / "README.md").read_text()
    for corpus, source in (("ml_1m", "cf"), ("gowalla_ts", "pop")):
        phi = ci[corpus]["ci"][source]["mean"]
        loo = ci[corpus]["loo_ci"][source]["mean"]
        assert f"{phi:+.5f}" in r, f"{corpus}/{source} Shapley {phi:+.5f} absent"
        assert f"{loo:+.5f}" in r, f"{corpus}/{source} LOO {loo:+.5f} absent"
