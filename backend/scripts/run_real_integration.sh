#!/usr/bin/env bash
# Run backend integration tests. Usage:
#   ./scripts/run_real_integration.sh           # profile ci (default)
#   ./scripts/run_real_integration.sh ci
#   ./scripts/run_real_integration.sh real      # heavy: workers, manim, OCR, full API suite
set -euo pipefail

PROFILE="${1:-ci}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi

export PYTHONPATH="$ROOT"
LOG_FILE="${LOG_FILE:-integration_run.log}"
JUNIT="${JUNIT:-pytest_integration.xml}"
REPORT_MD="${REPORT_MD:-integration_report.md}"
JSON_RESULTS="${JSON_RESULTS:-temp_suite_results.json}"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

log "Profile=$PROFILE working_dir=$ROOT"

if [[ "$PROFILE" == "ci" ]]; then
  export ALLOW_TEST_BYPASS="${ALLOW_TEST_BYPASS:-true}"
  export LOG_LEVEL="${LOG_LEVEL:-info}"
  export CELERY_TASK_ALWAYS_EAGER="${CELERY_TASK_ALWAYS_EAGER:-true}"
  export CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-rpc://}"
  export MOCK_VIDEO="${MOCK_VIDEO:-true}"

  set +e
  log "Phase A: default pytest (unit / mocked; excludes real_* markers per pytest.ini)"
  "$PY" -m pytest tests/ -q --tb=short -p no:cacheprovider 2>&1 | tee -a "$LOG_FILE"
  P1=${PIPESTATUS[0]}
  set -e

  log "Starting uvicorn for API phase..."
  "$PY" -m uvicorn app.main:app --port 8000 >>uvicorn_integration.log 2>&1 &
  SERVER_PID=$!
  trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

  for i in $(seq 1 25); do
    if curl -sf "http://localhost:8000/" >/dev/null; then
      log "API ready"
      break
    fi
    sleep 2
    if [[ "$i" -eq 25 ]]; then
      log "ERROR: API did not start"
      exit 1
    fi
  done

  PREP="$("$PY" scripts/prepare_api_test.py)"
  echo "$PREP" | tee -a "$LOG_FILE"
  export TEST_USER_ID="$(echo "$PREP" | grep "RESULT:USER_ID=" | cut -d'=' -f2)"
  export TEST_SESSION_ID="$(echo "$PREP" | grep "RESULT:SESSION_ID=" | cut -d'=' -f2)"
  if [[ -z "${TEST_USER_ID:-}" || -z "${TEST_SESSION_ID:-}" ]]; then
    log "ERROR: prepare_api_test did not emit USER_ID / SESSION_ID"
    exit 1
  fi

  set +e
  log "Phase B: API smoke + full suite (real_api)"
  "$PY" -m pytest tests/test_api_real_e2e.py tests/test_api_full_suite.py \
    -m "real_api" -s --tb=short --junitxml="$JUNIT" -p no:cacheprovider 2>&1 | tee -a "$LOG_FILE"
  P2=${PIPESTATUS[0]}
  set -e

  if [[ -f "$JSON_RESULTS" ]]; then
    log "Generating Markdown report"
    "$PY" scripts/generate_report.py "$JSON_RESULTS" "$REPORT_MD" "$JUNIT"
  else
    log "WARN: $JSON_RESULTS missing (suite may have failed before write)"
  fi

  if [[ "$P1" -ne 0 || "$P2" -ne 0 ]]; then
    log "FAIL: phase A exit=$P1 phase B exit=$P2"
    exit 1
  fi

  log "Done CI profile. See $REPORT_MD and $LOG_FILE"
  exit 0
fi

if [[ "$PROFILE" == "real" ]]; then
  unset CELERY_TASK_ALWAYS_EAGER || true
  export CELERY_TASK_ALWAYS_EAGER="${CELERY_TASK_ALWAYS_EAGER:-false}"
  export MOCK_VIDEO="${MOCK_VIDEO:-false}"
  export RUN_REAL_WORKER_OCR="${RUN_REAL_WORKER_OCR:-0}"
  export RUN_REAL_WORKER_MANIM="${RUN_REAL_WORKER_MANIM:-0}"

  log "Phase A: default pytest (fast)"
  "$PY" -m pytest tests/ -q --tb=short -p no:cacheprovider 2>&1 | tee -a "$LOG_FILE"

  log "Phase B: real agents + orchestrator smoke (requires OpenRouter keys)"
  "$PY" -m pytest tests/integration/test_agents_real.py tests/integration/test_orchestrator_smoke.py \
    -m "real_agents" -q --tb=short --junitxml="$JUNIT" -p no:cacheprovider 2>&1 | tee -a "$LOG_FILE" || true

  if [[ "${RUN_REAL_WORKER_OCR:-0}" == "1" ]] || [[ "${RUN_REAL_WORKER_OCR:-0}" =~ ^(true|yes)$ ]]; then
    log "Phase C: OCR worker task (RUN_REAL_WORKER_OCR enabled)"
    "$PY" -m pytest tests/integration/test_worker_ocr_real.py \
      -m "real_worker_ocr" -q --tb=short -p no:cacheprovider 2>&1 | tee -a "$LOG_FILE" || true
  else
    log "Skipping OCR worker (set RUN_REAL_WORKER_OCR=1 to enable)"
  fi

  if [[ "${RUN_REAL_WORKER_MANIM:-0}" == "1" ]]; then
    log "Phase D: Manim + storage (RUN_REAL_WORKER_MANIM=1, MOCK_VIDEO=false)"
    "$PY" -m pytest tests/integration/test_worker_manim_real.py -m "real_worker_manim" -s --tb=short \
      -p no:cacheprovider 2>&1 | tee -a "$LOG_FILE" || true
  else
    log "Skipping Manim integration (set RUN_REAL_WORKER_MANIM=1 to enable)"
  fi

  log "Phase E: API real (expects TEST_BASE_URL or localhost:8000 with server already up)"
  if curl -sf "http://localhost:8000/" >/dev/null 2>&1; then
    PREP="$("$PY" scripts/prepare_api_test.py)"
    export TEST_USER_ID="$(echo "$PREP" | grep "RESULT:USER_ID=" | cut -d'=' -f2)"
    export TEST_SESSION_ID="$(echo "$PREP" | grep "RESULT:SESSION_ID=" | cut -d'=' -f2)"
    "$PY" -m pytest tests/test_api_real_e2e.py tests/test_api_full_suite.py tests/test_api_metadata_real.py \
      -m "real_api" -q --tb=short -p no:cacheprovider 2>&1 | tee -a "$LOG_FILE" || true
  else
    log "WARN: No server on :8000 — skip API real phase (start backend first)"
  fi

  log "Done REAL profile. Review $LOG_FILE"
  exit 0
fi

echo "Unknown profile: $PROFILE (use ci or real)"
exit 1
