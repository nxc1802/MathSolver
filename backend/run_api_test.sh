#!/bin/bash

LOG_FILE="api_test_results.log"
echo "=== Starting API E2E Test Suite ($(date)) ===" > $LOG_FILE

# 1. Start BE Server in background
echo "[INFO] Starting Backend Server..." | tee -a $LOG_FILE
export ALLOW_TEST_BYPASS=true
export LOG_LEVEL=info
export CELERY_TASK_ALWAYS_EAGER=true
export CELERY_RESULT_BACKEND=rpc://
export MOCK_VIDEO=true
PYTHONPATH=. venv/bin/python -m uvicorn app.main:app --port 8000 > server_debug.log 2>&1 &
SERVER_PID=$!

# 2. Wait for server to be ready
echo "[INFO] Waiting for server (PID: $SERVER_PID) on port 8000..." | tee -a $LOG_FILE
MAX_RETRIES=15
READY=0
for i in $(seq 1 $MAX_RETRIES); do
    if curl -s http://localhost:8000/ > /dev/null; then
        READY=1
        break
    fi
    sleep 2
done

if [ $READY -eq 0 ]; then
    echo "[ERROR] Server failed to start in time. Check server_debug.log" | tee -a $LOG_FILE
    kill $SERVER_PID
    exit 1
fi
echo "[INFO] Server is READY." | tee -a $LOG_FILE

# 3. Prepare Test Data
echo "[INFO] Preparing fresh test data..." | tee -a $LOG_FILE
PREP_OUTPUT=$(PYTHONPATH=. venv/bin/python scripts/prepare_api_test.py)
echo "$PREP_OUTPUT" >> $LOG_FILE

export TEST_USER_ID=$(echo "$PREP_OUTPUT" | grep "RESULT:USER_ID=" | cut -d'=' -f2)
export TEST_SESSION_ID=$(echo "$PREP_OUTPUT" | grep "RESULT:SESSION_ID=" | cut -d'=' -f2)

if [ -z "$TEST_USER_ID" ] || [ -z "$TEST_SESSION_ID" ]; then
    echo "[ERROR] Failed to prepare test data." | tee -a $LOG_FILE
    kill $SERVER_PID
    exit 1
fi

echo "[INFO] Test Data: User=$TEST_USER_ID, Session=$TEST_SESSION_ID" | tee -a $LOG_FILE

# 4. Run Pytest
echo "[INFO] Running API E2E Tests..." | tee -a $LOG_FILE
PYTHONPATH=. venv/bin/python -m pytest tests/test_api_real_e2e.py -m "smoke and real_api" -s \
  --junitxml=pytest_smoke.xml >> $LOG_FILE 2>&1
TEST_EXIT_CODE=$?

# 5. Cleanup
echo "[INFO] Shutting down Server..." | tee -a $LOG_FILE
kill $SERVER_PID

echo "==========================================" | tee -a $LOG_FILE
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "FINAL RESULT: ✅ ALL API TESTS PASSED" | tee -a $LOG_FILE
else
    echo "FINAL RESULT: ❌ SOME API TESTS FAILED (Code: $TEST_EXIT_CODE)" | tee -a $LOG_FILE
fi
echo "==========================================" | tee -a $LOG_FILE

exit $TEST_EXIT_CODE
