#!/usr/bin/env bash
# Review round 8: every remaining run, in cost order, resumable.
#
#     bash scripts/run_round8_remaining.sh [BUDGET_GB]
#
# Each stage writes its own artefact and every underlying script resumes from
# what is already on disk, so an interrupted run can be restarted and a stage
# that already succeeded is cheap to repeat. Stages are INDEPENDENT: a failure
# in one does not abort the rest, because a six-hour sweep should not be lost
# to a typo in the stage after it. Failures are collected and reported at the
# end with a non-zero exit.
#
# `set -e` is deliberately NOT used, for that reason. `timeout` is deliberately
# not used either: it does not exist on macOS, and this is run on an M4.
#
# Corpora are passed ONE PER INVOCATION to run_study.py. It refuses a
# multi-corpus call whose corpora need different user caps, because a single
# process-wide cap would silently substitute a different MovieLens.

BUDGET="${1:-24}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

export PYTHONPATH="$ROOT/src:${PYTHONPATH}"
export SIGNALSHAP_STRICT_DATA=1

FAILED=()
STAGE=0

run_stage () {
  local label="$1"; shift
  STAGE=$((STAGE + 1))
  echo ""
  echo "======================================================================"
  echo "[$STAGE] $label"
  echo "    $*"
  echo "======================================================================"
  local t0=$SECONDS
  if "$@"; then
    echo "--- ok (${label}) in $((SECONDS - t0))s"
  else
    echo "!!! FAILED (${label}) after $((SECONDS - t0))s"
    FAILED+=("$label")
  fi
}

PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python

# -- cheap, and closes the two remaining Essential items ---------------------

run_stage "item 3: blocked retirement (ml_1m)" \
  "$PY" scripts/run_global_timeblock.py --corpora ml_1m \
        --budget-gb "$BUDGET" --retirement

run_stage "item 10: neutral candidate pools (ml_1m)" \
  "$PY" scripts/run_pool_sensitivity.py --corpora ml_1m --budget-gb "$BUDGET"

# -- moderate ----------------------------------------------------------------

run_stage "item 7: ten-seed refreshed history (ml_1m)" \
  "$PY" scripts/run_protocol_sensitivity.py --corpora ml_1m \
        --budget-gb "$BUDGET" --seeds 42 43 44 45 46 47 48 49 50 51

run_stage "item 10: neutral candidate pools (amazon_video_games)" \
  "$PY" scripts/run_pool_sensitivity.py --corpora amazon_video_games \
        --budget-gb "$BUDGET"

# -- expensive: legacy-rule diagnostics, one corpus per call -----------------

run_stage "item 6: regenerate diagnostics (ml_1m)" \
  "$PY" scripts/run_study.py --datasets ml_1m --budget-gb "$BUDGET" \
        --seeds 42 43 44

run_stage "item 6: regenerate diagnostics (amazon_video_games)" \
  "$PY" scripts/run_study.py --datasets amazon_video_games \
        --budget-gb "$BUDGET" --seeds 42 43 44

run_stage "item 6: regenerate diagnostics (gowalla_ts)" \
  "$PY" scripts/run_study.py --datasets gowalla_ts --budget-gb "$BUDGET" \
        --seeds 42 43 44

# -- optional, largest: Gowalla neutral pools --------------------------------
# 11,623 candidates x 4 pool rules x 32 coalitions. Skip with SKIP_GOWALLA=1.

if [ "${SKIP_GOWALLA:-0}" != "1" ]; then
  run_stage "item 10: neutral candidate pools (gowalla_ts)" \
    "$PY" scripts/run_pool_sensitivity.py --corpora gowalla_ts \
          --budget-gb "$BUDGET"
fi

# -- refresh the hashed manifest so the release stays checkable --------------

run_stage "manifest" "$PY" scripts/make_manifest.py

echo ""
echo "======================================================================"
if [ ${#FAILED[@]} -eq 0 ]; then
  echo "all $STAGE stages ok"
  echo ""
  echo "next: python scripts/check_paper_numbers.py --strict"
  exit 0
fi
echo "${#FAILED[@]} of $STAGE stages FAILED:"
for f in "${FAILED[@]}"; do echo "  - $f"; done
echo ""
echo "Artefacts from the stages that succeeded are on disk and every script"
echo "resumes, so rerunning this file only repeats what is missing."
exit 1
