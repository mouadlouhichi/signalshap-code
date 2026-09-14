"""The Gowalla semivalues notebook must stay in sync with the script it drives.

This notebook launches a multi-tens-of-minutes run on the user's machine, so a
mistyped flag or a stale corpus name costs real time before anyone notices.
Two specific hazards are pinned here because both have already happened once
in this project:

  * `run_revision_experiments.py` has no `--budget-gb` and performs no memory
    sizing, so omitting `--max-users` loads the full 52,985 x 121,866 corpus
    and gets OOM-killed, exactly as `run_study.py` was;
  * a hardcoded repo path matched a stale empty directory, the notebook
    chdir'd into it, and every stage failed instantly.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks" / "SignalShap_Semivalues_Gowalla.ipynb"
GEN = ROOT / "scripts" / "make_semivalues_notebook.py"
TARGET = ROOT / "scripts" / "run_revision_experiments.py"

pytestmark = pytest.mark.skipif(not NB.exists(), reason="notebook absent")


@pytest.fixture(scope="module")
def nb() -> dict:
    return json.loads(NB.read_text())


@pytest.fixture(scope="module")
def code_src(nb) -> str:
    return "\n".join("".join(c["source"])
                     for c in nb["cells"] if c["cell_type"] == "code")


def test_notebook_matches_its_generator():
    spec = importlib.util.spec_from_file_location("_gen_sv", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    expected = json.dumps(mod.build(), indent=1) + "\n"
    assert NB.read_text() == expected, (
        "notebook differs from scripts/make_semivalues_notebook.py; edit the "
        "generator and re-run it")


def test_every_code_cell_parses(nb):
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] != "code":
            continue
        src = "".join(c["source"])
        if src.lstrip().startswith("%"):
            continue
        try:
            ast.parse(src)
        except SyntaxError as e:
            pytest.fail(f"cell {i} does not parse: {e}")


def test_cells_have_unique_ids(nb):
    ids = [c["id"] for c in nb["cells"]]
    assert all(ids) and len(set(ids)) == len(ids)


def test_the_invoked_script_exists(code_src):
    assert "experiments/run_revision_experiments.py" in code_src
    assert TARGET.exists()


def test_max_users_is_passed_because_the_script_cannot_size_itself(code_src):
    """The load-bearing guard: this script has no --budget-gb."""
    body = TARGET.read_text()
    assert '"--budget-gb"' not in body, (
        "run_revision_experiments.py grew a --budget-gb flag; the notebook's "
        "--max-users workaround and its explanation should be revisited")
    assert '"--max-users", "8865"' in code_src, (
        "without --max-users the full corpus is loaded and the run is "
        "OOM-killed")


def test_every_flag_is_defined_by_the_target_script(code_src):
    """Every --flag the notebook passes must exist in the target parser."""
    body = TARGET.read_text()
    # Anchor on the actual command list and read to the MATCHING bracket.
    # Two earlier versions of this test were fooled: searching for the script
    # name alone first matched the MARKERS tuple in _find_repo, and taking the
    # first "]" truncated a cmd list that spans lines.
    i = code_src.index("cmd = [")
    depth, j = 0, code_src.index("[", i)
    for j in range(j, len(code_src)):
        if code_src[j] == "[":
            depth += 1
        elif code_src[j] == "]":
            depth -= 1
            if depth == 0:
                break
    call = code_src[i:j + 1]
    assert "run_revision_experiments.py" in call
    flags = re.findall(r'"(--[a-z0-9-]+)"', call)
    assert flags, "no flags extracted; the anchor or the regex is wrong"
    for flag in flags:
        assert f'"{flag}"' in body, f"target script does not define {flag}"


def test_skip_e2e_is_used(code_src):
    """E11/E12 cost 2^n retrieval passes and are not needed for semivalues."""
    assert '"--skip-e2e"' in code_src


def test_repo_is_found_by_contents_not_a_guessed_path(code_src):
    assert "_find_repo" in code_src and "MARKERS" in code_src
    assert "experiments/run_revision_experiments.py" in code_src


def test_strict_data_is_enforced(code_src):
    """A missing corpus must be a hard error, never a synthetic fallback."""
    assert 'SIGNALSHAP_STRICT_DATA"] = "1"' in code_src


def test_readout_uses_the_real_artefact_schema(code_src):
    """Keys must match what run_revision_experiments.py actually writes."""
    for key in ("shapley", "banzhaf", "semivalue_binomial_q025",
                "semivalue_binomial_q075",
                "size_uniform_equals_shapley_max_abs_diff"):
        assert key in code_src, f"readout does not reference {key}"
    ref = ROOT / "artefacts" / "e10_values_ml_1m_symmetric_candidates.json"
    if ref.exists():
        have = set(json.loads(ref.read_text()))
        for key in ("shapley", "banzhaf", "semivalue_binomial_q025",
                    "semivalue_binomial_q075"):
            assert key in have, f"{key} missing from a real e10 artefact"


def test_notebook_states_both_outcomes(nb):
    """It must not presuppose that Gowalla will agree."""
    md = "\n".join("".join(c["source"])
                   for c in nb["cells"] if c["cell_type"] == "markdown")
    assert "disagrees" in md.lower()
    assert "Whatever it returns, we report it" in md


def test_output_artefact_name_matches_the_script(code_src):
    body = TARGET.read_text()
    assert 'e10_values_{a.dataset}.json' in body
    assert "e10_values_gowalla_ts.json" in code_src
