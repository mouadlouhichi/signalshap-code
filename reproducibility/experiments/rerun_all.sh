#!/usr/bin/env bash
# Regenerate every artefact under the deterministic expected-random baseline.
#
#   bash experiments/rerun_all.sh [BUDGET_GB]
#
# Runs SEQUENTIALLY -- the corpora cannot share one SIGNALSHAP_MAX_USERS, and
# running them concurrently would also contend for the same memory budget.
# Each stage writes its own artefact, so a later failure keeps earlier work.
#
# Total wall-clock on an M4/48GB: roughly 12-16 hours. Run it from a terminal,
# not a notebook: Jupyter refuses background processes, and this is far too
# long to hold a cell open.

set -u                       # undefined variable is an error
                             # deliberately NOT -e: one failed corpus should
                             # not discard the corpora that already succeeded

BUDGET="${1:-24}"
cd "$(dirname "$0")/.." || exit 1
mkdir -p logs

export SIGNALSHAP_STRICT_DATA=1     # never silently fall back to synthetic data

run () {                     # run <label> <command...>
  local label="$1"; shift
  local log="logs/${label}.log"
  printf '\n=== %s  (log: %s) ===\n' "$label" "$log"
  local t0=$SECONDS
  if "$@" > "$log" 2>&1; then
    printf '    OK in %dm%02ds\n' $(( (SECONDS-t0)/60 )) $(( (SECONDS-t0)%60 ))
  else
    printf '    FAILED after %dm%02ds -- see %s\n' \
           $(( (SECONDS-t0)/60 )) $(( (SECONDS-t0)%60 )) "$log"
    tail -5 "$log" | sed 's/^/      /'
    FAILURES="${FAILURES} ${label}"
  fi
}

FAILURES=""
START=$SECONDS
echo "budget ${BUDGET} GB | started $(date '+%H:%M:%S')"

# 1. Core study, three seeds, one corpus at a time.
run study_ml_1m      python experiments/run_study.py --datasets ml_1m \
                       --seeds 42 43 44

# Gate the remaining ~12 hours on the fastest corpus. If ml_1m comes back
# invalid the code is wrong, and every later stage would inherit the same
# defect -- better to stop after 11 minutes than after half a day.
if ! python scripts/check_run_valid.py ml_1m; then
  echo
  echo 'ml_1m is INVALID -- stopping before the long stages.'
  echo 'Fix the cause and re-run; nothing after this point would be usable.'
  exit 1
fi
run study_amazon     python experiments/run_study.py --datasets amazon_video_games \
                       --budget-gb "$BUDGET" --seeds 42 43 44
run study_gowalla    python experiments/run_study.py --datasets gowalla_ts \
                       --budget-gb "$BUDGET" --seeds 42 43 44

# 2. E10-E13 (interactions, estimands, retirement, analytic games).
run revision_ml_1m   python experiments/run_revision_experiments.py --dataset ml_1m
run revision_amazon  python experiments/run_revision_experiments.py \
                       --dataset amazon_video_games
run revision_gowalla python experiments/run_revision_experiments.py \
                       --dataset gowalla_ts

# 3. Ten-seed intervals, lambda sweep, Friedman, retirement-over-seeds.
run final_revision   python experiments/run_final_revision.py --budget-gb "$BUDGET"

# 4. Rebuild figures and tables, then check the paper against the artefacts.
run assets           python scripts/make_assets.py

printf '\n=== total %dh%02dm ===\n' $(( (SECONDS-START)/3600 )) \
       $(( ((SECONDS-START)%3600)/60 ))
if [ -n "$FAILURES" ]; then
  printf 'FAILED STAGES:%s\n' "$FAILURES"
  printf 'Re-run only those; completed artefacts are already on disk.\n'
else
  echo 'all stages OK'
fi

echo
echo '=== paper vs artefacts (drift is EXPECTED: the baseline changed) ==='
python scripts/check_paper_numbers.py || true
