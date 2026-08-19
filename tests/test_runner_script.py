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


def test_runner_gates_the_long_stages_on_ml1m():
    """A 12-hour run must not proceed past an invalid 11-minute corpus."""
    body = SCRIPT.read_text()
    i_check = body.index("check_run_valid.py ml_1m")
    i_gowalla = body.index("--datasets gowalla_ts")
    i_final = body.index("run_final_revision.py")
    assert i_check < i_gowalla, "validity gate must precede the Gowalla stage"
    assert i_check < i_final, "validity gate must precede the final-revision stage"
    assert "exit 1" in body[i_check:i_check + 400], "gate must actually abort"


def test_validity_checker_survives_a_pre_fix_artefact():
    """It must diagnose a missing v_empty, not raise KeyError on it.

    The obvious one-liner crashed on exactly the artefact it was meant to
    reject, which reads as a broken tool rather than a broken run.
    """
    import json
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        art = Path(td) / "artefacts"
        art.mkdir()
        (art / "results_ml_1m.json").write_text(json.dumps({
            "e1_source_share": {                    # no v_empty: pre-fix shape
                "efficiency": {"abs_error": 7.4e-4, "passes": False},
            },
            "e0a_candidates": {"candidate_recall": 0.748, "gate_passes": True},
        }))
        script = art.parent / "check.py"
        script.write_text(
            SCRIPT.parent.joinpath("check_run_valid.py").read_text()
            .replace('Path(__file__).resolve().parents[1] / "artefacts"',
                     f'Path({str(art)!r})'))
        r = subprocess.run(["python3", str(script), "ml_1m"],
                           capture_output=True, text=True)
    assert r.returncode == 1, "must report failure"
    assert "KeyError" not in r.stderr, f"crashed instead of diagnosing: {r.stderr}"
    assert "v_empty ABSENT" in r.stdout
    assert "Property 1" in r.stdout


# --------------------------------------------------------------------------- #
# block_seeds must checkpoint and resume (the Gowalla 10-seed block died after
# ~8 h of successful work and would otherwise have discarded all of it).
# --------------------------------------------------------------------------- #

FINAL = ROOT / "scripts" / "run_final_revision.py"


def test_block_seeds_checkpoints_inside_the_seed_loop():
    """Writing only after all 10 seeds means a crash at seed 9 loses 9 seeds."""
    body = FINAL.read_text()
    block = body[body.index("def block_seeds"):body.index("def block_lambda")]
    seed_loop = block.index("for s in todo:")
    # The artefact name is now chosen at the call site (resized runs go to a
    # separate file), so match the call rather than the literal filename.
    write = block.index("write_artefact(")
    corpus_loop_end = block.index('print(f"{name}: complete"')
    assert seed_loop < write < corpus_loop_end, \
        "the checkpoint write must be inside the per-seed loop"


def test_block_seeds_resumes_from_disk():
    body = FINAL.read_text()
    block = body[body.index("def block_seeds"):body.index("def block_lambda")]
    assert "resume" in block
    assert "final_seed_ci.json" in block.split("for name in corpora")[0], \
        "must read the existing checkpoint before starting"
    assert "todo" in block, "must compute which seeds remain"


def test_resume_arithmetic_skips_completed_and_continues_partial():
    def todo_for(out, name, seeds):
        prior = {int(k): v for k, v in
                 (out.get(name, {}).get("per_seed") or {}).items()}
        return [s for s in seeds if s not in prior]

    seeds = list(range(42, 52))
    complete = {"ml_1m": {"per_seed": {str(s): {} for s in seeds}}}
    assert todo_for(complete, "ml_1m", seeds) == []
    assert todo_for(complete, "gowalla_ts", seeds) == seeds

    partial = {"gowalla_ts": {"per_seed": {str(s): {} for s in (42, 43, 44)}}}
    assert todo_for(partial, "gowalla_ts", seeds) == list(range(45, 52))


def test_block_seeds_frees_memory_between_seeds():
    """Gowalla holds 14.6 GB of score matrices per seed."""
    body = FINAL.read_text()
    block = body[body.index("def block_seeds"):body.index("def block_lambda")]
    assert "del e" in block and "gc.collect()" in block


# --------------------------------------------------------------------------- #
# The round-8 remaining-runs driver. Same failure modes as rerun_all.sh, so it
# gets the same guards: a non-portable prefix or a mistyped path here would
# waste a multi-hour run on the user's machine before anyone noticed.
# --------------------------------------------------------------------------- #

ROUND8 = ROOT / "scripts" / "run_round8_remaining.sh"


def _round8_stages():
    """Every `run_stage "<label>" <cmd...>` line, with continuations joined."""
    flat = ROUND8.read_text().replace("\\\n", " ")
    out = []
    for m in re.finditer(r'^\s*run_stage\s+"([^"]+)"\s+(.+)$', flat, re.M):
        cmd = m.group(2).strip()
        cmd = cmd.replace('"$BUDGET"', "24").replace('"$PY"', "python3")
        out.append((m.group(1), shlex.split(cmd)))
    return out


def test_round8_script_is_syntactically_valid():
    r = subprocess.run(["bash", "-n", str(ROUND8)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_round8_has_stages():
    assert len(_round8_stages()) >= 8


def test_round8_every_stage_is_portable_and_real():
    for label, parts in _round8_stages():
        assert parts[0] in ("python", "python3"), \
            f"{label}: {parts[0]!r} is not a portable interpreter"
        script = parts[1]
        assert script.endswith(".py"), f"{label}: {script} is not a .py file"
        assert (ROOT / script).exists(), f"{label}: {script} does not exist"


def test_round8_flags_are_accepted_by_their_scripts():
    """A flag the target script does not define kills the stage instantly.

    `run_protocol_sensitivity.py --budget-gb` was once accepted and silently
    ignored; the inverse, passing a flag that does not exist, aborts the run.
    Both are cheap to catch by reading the target's parser.
    """
    for label, parts in _round8_stages():
        body = (ROOT / parts[1]).read_text()
        for tok in parts[2:]:
            if tok.startswith("--"):
                assert f'"{tok}"' in body, \
                    f"{label}: {parts[1]} does not define {tok}"


def test_round8_never_batches_corpora_into_one_run_study_call():
    """run_study.py refuses corpora with different caps; do not tempt it."""
    for label, parts in _round8_stages():
        if parts[1].endswith("run_study.py"):
            i = parts.index("--datasets")
            rest = parts[i + 1:]
            names = [t for t in rest[:len(rest)]
                     if not t.startswith("--")]
            # Stop at the next flag.
            corpora = []
            for t in rest:
                if t.startswith("--"):
                    break
                corpora.append(t)
            assert len(corpora) == 1, \
                f"{label}: {corpora} in one call; run_study.py needs one corpus"
            assert names  # the list really was parsed


def test_round8_does_not_abort_on_first_failure():
    """Check executable lines only; the file discusses `set -e` in a comment."""
    code = [l for l in ROUND8.read_text().splitlines()
            if not l.lstrip().startswith("#")]
    assert not any(re.match(r"\s*set\s+-\w*e", l) for l in code), \
        "a failed stage must not discard the later ones"
    body = ROUND8.read_text()
    assert "FAILED" in body and "exit 1" in body, "failures must be reported"


def test_round8_enforces_strict_data():
    assert "SIGNALSHAP_STRICT_DATA=1" in ROUND8.read_text()


def test_round8_uses_no_timeout_command():
    """`timeout` does not exist on macOS; this is run on an M4."""
    body = ROUND8.read_text()
    assert not re.search(r"^\s*(g?timeout)\s", body, re.M)
    for _, parts in _round8_stages():
        assert parts[0] not in ("timeout", "gtimeout")


def test_round8_covers_every_open_review_item():
    body = ROUND8.read_text()
    for script in ("run_global_timeblock.py", "run_pool_sensitivity.py",
                   "run_protocol_sensitivity.py", "run_study.py",
                   "make_manifest.py"):
        assert script in body, f"{script} is never run"
    # The blocked retirement is the point of stage 1, not just the split.
    assert "--retirement" in body
    # The ten-seed refresh needs ten seeds, not the default single seed.
    m = re.search(r"--seeds((?:\s+\d+)+)", body)
    assert m and len(m.group(1).split()) >= 10, "item 7 needs ten seeds"
