import asyncio
import copy
import json
import os
import time

import httpx
import pytest

from tests.cases.pipeline_cases import (
    Q10_FOLLOW_UP,
    Q13_HISTORY_STEPS,
    QUERIES,
    validate_q10_step2_dsl,
    validate_query_result,
)

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
USER_ID = os.getenv("TEST_USER_ID")
SESSION_ID = os.getenv("TEST_SESSION_ID")

test_stats: list[dict] = []


_SOLVER_TRANSIENT = "Solver failed after multiple attempts"


async def run_single_api_query(client, q, headers, default_session_id: str | None):
    print(f"\n🚀 [RUNNING] {q['id']}: {q['text']}")
    start_time = time.time()

    payload = {
        "text": q["text"],
        "request_video": q.get("request_video", False),
    }

    max_rounds = 3

    try:
        for round_idx in range(max_rounds):
            if q.get("isolate", True):
                session_resp = await client.post("/api/v1/sessions", headers=headers)
                if session_resp.status_code != 200:
                    return {
                        "id": q["id"],
                        "query": q["text"],
                        "success": False,
                        "error": f"Session creation failed: {session_resp.text}",
                    }
                session_id = session_resp.json()["id"]
            else:
                session_id = q.get("session_id", default_session_id)

            res = await client.post(
                f"/api/v1/sessions/{session_id}/solve",
                json=payload,
                headers=headers,
            )
            if res.status_code != 200:
                print(f"   ❌ FAILED: Status {res.status_code} - {res.text}")
                return {
                    "id": q["id"],
                    "query": q["text"],
                    "success": False,
                    "error": f"HTTP {res.status_code}: {res.text}",
                }

            job_id = res.json()["job_id"]
            print(f"   ✅ Job Created: {job_id}")

            max_attempts = 45
            result_data = None
            last_error = None
            for i in range(max_attempts):
                await asyncio.sleep(4)
                res = await client.get(f"/api/v1/solve/{job_id}", headers=headers)
                data = res.json()
                status = data.get("status")
                print(f"      - Polling ({i + 1}): {status}")

                if status == "success":
                    result_data = data["result"]
                    break
                if status == "error":
                    last_error = data.get("result", {}).get("error")
                    print(f"   ❌ ERROR: {last_error}")
                    err_s = str(last_error or "")
                    if _SOLVER_TRANSIENT in err_s and round_idx < max_rounds - 1:
                        print(
                            f"   ↻ Retry {round_idx + 2}/{max_rounds} (transient solver/LLM flake)"
                        )
                        result_data = None
                        break
                    return {
                        "id": q["id"],
                        "query": q["text"],
                        "success": False,
                        "error": last_error,
                    }

                if i == max_attempts - 1:
                    print("   ❌ TIMEOUT")
                    return {"id": q["id"], "query": q["text"], "success": False, "error": "Timeout"}

            if result_data is None:
                continue

            elapsed = time.time() - start_time
            errors = validate_query_result(q, result_data)

            if q.get("request_video") and not result_data.get("video_url"):
                print("      ⚠️ Video requested but no URL found (Expected in some test envs)")

            if errors:
                print(f"   ❌ VALIDATION FAILED: {', '.join(errors)}")
                return {
                    "id": q["id"],
                    "query": q["text"],
                    "success": False,
                    "error": "; ".join(errors),
                    "elapsed": elapsed,
                    "result": result_data,
                }

            print(f"   ✅ PASS ({elapsed:.2f}s)")
            return {
                "id": q["id"],
                "query": q["text"],
                "success": True,
                "elapsed": elapsed,
                "job_id": job_id,
                "result": result_data,
            }

        raise RuntimeError("run_single_api_query: retry loop fell through (bug)")

    except Exception as e:
        print(f"   ❌ EXCEPTION: {str(e)}")
        return {"id": q["id"], "query": q["text"], "success": False, "error": str(e)}


@pytest.mark.real_api
@pytest.mark.slow
@pytest.mark.asyncio
async def test_full_api_suite():
    if not USER_ID or not SESSION_ID:
        pytest.fail("TEST_USER_ID and TEST_SESSION_ID must be set")

    global test_stats
    test_stats = []

    headers = {"Authorization": f"Test {USER_ID}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        for q in QUERIES:
            if q["id"] == "Q10-Step1":
                continue
            qc = copy.deepcopy(q)
            res = await run_single_api_query(client, qc, headers, SESSION_ID)
            test_stats.append(res)

        print("\n--- Testing Multi-turn API Flow (Q10) ---")
        shared_session_resp = await client.post("/api/v1/sessions", headers=headers)
        assert shared_session_resp.status_code == 200
        shared_session = shared_session_resp.json()["id"]

        q10_1 = copy.deepcopy(next(q for q in QUERIES if q["id"] == "Q10-Step1"))
        q10_1["session_id"] = shared_session
        q10_1["isolate"] = False
        res10_1 = await run_single_api_query(client, q10_1, headers, SESSION_ID)
        test_stats.append(res10_1)

        if res10_1["success"]:
            q10_2 = copy.deepcopy(Q10_FOLLOW_UP)
            q10_2["session_id"] = shared_session
            q10_2["isolate"] = False
            res10_2 = await run_single_api_query(client, q10_2, headers, SESSION_ID)

            if res10_2["success"]:
                dsl = res10_2.get("result", {}).get("geometry_dsl", "") or ""
                if not validate_q10_step2_dsl(dsl):
                    res10_2["success"] = False
                    res10_2["error"] = "DSL did not merge history correctly"

            test_stats.append(res10_2)

        print("\n--- Testing Multi-turn API Flow (Q13 history in one session) ---")
        q13_session_resp = await client.post("/api/v1/sessions", headers=headers)
        assert q13_session_resp.status_code == 200
        q13_session = q13_session_resp.json()["id"]

        prev_ok = True
        for step in Q13_HISTORY_STEPS:
            if not prev_ok:
                test_stats.append(
                    {
                        "id": step["id"],
                        "query": step["text"],
                        "success": False,
                        "error": "Skipped: previous step in Q13 failed",
                    }
                )
                continue
            sc = copy.deepcopy(step)
            sc["session_id"] = q13_session
            sc["isolate"] = False
            out = await run_single_api_query(client, sc, headers, SESSION_ID)
            test_stats.append(out)
            prev_ok = bool(out.get("success"))

    with open("temp_suite_results.json", "w", encoding="utf-8") as f:
        json.dump(test_stats, f, ensure_ascii=False, indent=2)

    failures = [r for r in test_stats if not r.get("success")]
    if failures:
        pytest.fail(
            "Suite failures: "
            + "; ".join(f"{r.get('id')}: {r.get('error')}" for r in failures[:5])
            + (f" (+{len(failures) - 5} more)" if len(failures) > 5 else "")
        )


if __name__ == "__main__":
    asyncio.run(test_full_api_suite())
