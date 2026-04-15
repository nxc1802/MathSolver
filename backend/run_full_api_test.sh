#!/bin/bash
# Full API integration (CI-style): eager Celery + mock video + full HTTP suite.
LOG_FILE="full_api_suite.log"
REPORT_FILE="full_api_test_report.md"
JSON_RESULTS="temp_suite_results.json"
JUNIT="pytest_api_suite.xml"

echo "=== Starting Full API Suite Test ($(date)) ===" >"$LOG_FILE"

trap 'echo "[INFO] Cleaning up processes..."; kill $SERVER_PID 2>/dev/null; sleep 1' EXIT

echo "[INFO] Starting Backend Server (EAGER + MOCK_VIDEO)..." | tee -a "$LOG_FILE"
export ALLOW_TEST_BYPASS=true
export LOG_LEVEL=info
export CELERY_TASK_ALWAYS_EAGER=true
export CELERY_RESULT_BACKEND=rpc://
export MOCK_VIDEO=true
PYTHONPATH=. venv/bin/python -m uvicorn app.main:app --port 8000 >server_debug.log 2>&1 &
SERVER_PID=$!

echo "[INFO] Waiting for server (PID: $SERVER_PID)..." | tee -a "$LOG_FILE"
for i in {1..20}; do
  if curl -s http://localhost:8000/ >/dev/null; then
    echo "[INFO] Server is READY." | tee -a "$LOG_FILE"
    break
  fi
  sleep 2
done

echo "[INFO] Preparing fresh test data..." | tee -a "$LOG_FILE"
PREP_OUTPUT=$(PYTHONPATH=. venv/bin/python scripts/prepare_api_test.py)
export TEST_USER_ID=$(echo "$PREP_OUTPUT" | grep "RESULT:USER_ID=" | cut -d'=' -f2)
export TEST_SESSION_ID=$(echo "$PREP_OUTPUT" | grep "RESULT:SESSION_ID=" | cut -d'=' -f2)

if [ -z "$TEST_USER_ID" ]; then
  echo "[ERROR] Failed to prepare test data." | tee -a "$LOG_FILE"
  exit 1
fi

echo "[INFO] Executing API tests (smoke + full suite)..." | tee -a "$LOG_FILE"
PYTHONPATH=. venv/bin/python -m pytest tests/test_api_real_e2e.py tests/test_api_full_suite.py \
  -m "real_api" -s --tb=short --junitxml="$JUNIT" >>"$LOG_FILE" 2>&1
TEST_EXIT_CODE=$?

echo "[INFO] Generating Markdown Report..." | tee -a "$LOG_FILE"
if [ -f "$JSON_RESULTS" ]; then
  PYTHONPATH=. venv/bin/python scripts/generate_report.py "$JSON_RESULTS" "$REPORT_FILE" "$JUNIT"
else
  echo "[WARN] $JSON_RESULTS not found" | tee -a "$LOG_FILE"
fi

echo "==========================================" | tee -a "$LOG_FILE"
echo "DONE. Check $REPORT_FILE for results." | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"

exit $TEST_EXIT_CODE
