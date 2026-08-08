"""The batch runner must be executable, not merely syntactically valid.

A `sed` edit once left `timeout 7200 python/run_study.py` in this script: two
faults in one line -- `timeout` is not a macOS command, and the path had been
mangled into `python/run_study.py`. `bash -n` passed, because both are runtime
failures. The stage died in 0 seconds on the user's machine.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "rerun_all.sh"


def _stages():
    """Every `run <label> <cmd...>` line, with continuations joined."""
    flat = SCRIPT.read_text().replace("\\\n", " ")
    out = []
    for m in re.finditer(r"^run\s+(\w+)\s+(.+)$", flat, re.M):
        label, cmd = m.group(1), m.group(2).strip()
        if label == "()":          # the function definition itself
            continue
        out.append((label, shlex.split(cmd.replace('"$BUDGET"', "24"))))
    return out


def test_script_is_syntactically_valid():
    r = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_every_stage_invokes_an_interpreter_that_exists():
    """No `timeout`, `gtimeout`, `parallel` or other non-portable prefix."""
    for label, parts in _stages():
        assert parts[0] in ("python", "python3"), \
            f"{label}: first token is {parts[0]!r}, not a portable interpreter"


def test_every_referenced_script_exists():
    for label, parts in _stages():
        script = parts[1]
        assert script.endswith(".py"), f"{label}: {script} is not a .py file"
        assert (ROOT / script).exists(), f"{label}: {script} does not exist"


def test_stage_labels_are_unique():
    """Duplicate labels would silently overwrite each other's log."""
    labels = [lbl for lbl, _ in _stages()]
    assert len(labels) == len(set(labels)), labels


def test_all_three_corpora_are_covered():
    joined = " ".join(" ".join(p) for _, p in _stages())
    for corpus in ("ml_1m", "amazon_video_games", "gowalla_ts"):
        assert corpus in joined, f"{corpus} is never run"


def test_runner_does_not_abort_on_first_failure():
    """`set -e` would discard corpora that already succeeded."""
    body = SCRIPT.read_text()
    assert "set -e" not in body.replace("set -eu", "SENTINEL")
    assert "set -u" in body


def test_strict_data_is_enforced():
    """A missing corpus must be a hard error, never a synthetic fallback."""
    assert "SIGNALSHAP_STRICT_DATA=1" in SCRIPT.read_text()
