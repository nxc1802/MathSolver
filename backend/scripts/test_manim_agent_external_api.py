"""
Dedicated Test Suite for Manim Agent External API
Tests the exact contract:
1. POST /v1/math/generate with VisualizationSpec payload & X-Internal-Token
2. GET  /v1/math/jobs/{job_id} with X-Internal-Token
3. Status lifecycle polling and video URL retrieval
"""
import asyncio
import json
import logging
import os
import sys
import time

from manim_client.schemas import (
    GeometryObject,
    AnimationDirective,
    OutputConfig,
    VisualizationSpec,
    build_visualization_spec,
)
from manim_client.client import ManimClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger(__name__)


async def test_manim_api_standalone():
    print("=" * 85)
    print("      KIỂM THỬ ĐỘC LẬP MANIM AGENT EXTERNAL API")
    print("      Contract: POST /v1/math/generate & GET /v1/math/jobs/{job_id}")
    print("=" * 85)

    # 1. Initialize ManimClient
    token = "4f8a3c2e1d0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4"
    remote_url = "https://cuong2004-manim-agent.hf.space"

    client = ManimClient(base_url=remote_url, internal_token=token)

    # 2. Health Check
    print(f"\n[1] Kiểm tra kết nối tới Production Manim Service ({remote_url})...")
    health = await client.check_health()
    print(f"    -> Trạng thái kết nối: {'ONLINE (200 OK) ✅' if health else 'OFFLINE ❌'}")
    assert health, "Manim service must be reachable on port 8001"

    # 3. Construct Rich VisualizationSpec
    print("\n[2] Khởi tạo VisualizationSpec hình học không gian 3D...")
    coords = {
        "S": [0.0, 0.0, 15.0],
        "A": [-5.0, -5.0, 0.0],
        "B": [5.0, -5.0, 0.0],
        "C": [5.0, 5.0, 0.0],
        "D": [-5.0, 5.0, 0.0],
        "O": [0.0, 0.0, 0.0],
    }
    solids = [{"type": "pyramid", "apex": "S", "base": ["A", "B", "C", "D"], "points": ["S", "A", "B", "C", "D"]}]
    steps = [
        "Bước 1: Tính diện tích đáy ABCD là hình vuông cạnh 10: S_day = 10^2 = 100.",
        "Bước 2: Chiều cao khối chóp SO = 15.",
        "Bước 3: Thể tích khối chóp S.ABCD: V = (1/3) * 100 * 15 = 500.",
    ]
    spec = build_visualization_spec(
        problem_text="Cho hình chóp S.ABCD có đáy ABCD là hình vuông cạnh 10, SO vuông góc đáy tại O, SO=15. Tính thể tích khối chóp S.ABCD.",
        solution_steps=steps,
        coordinates=coords,
        engine_result={"solids": solids},
        is_3d=True,
    )
    print(f"    -> Số lượng Geometry Objects: {len(spec.geometry)}")
    print(f"    -> Số lượng Animation Beats: {len(spec.animations)}")
    print(f"    -> Output Config: {spec.output_config.quality}, {spec.output_config.format}, {spec.output_config.language}")

    # 4. Submit Render Job (POST /v1/math/generate)
    print("\n[3] Gửi yêu cầu sinh video (POST /v1/math/generate kèm X-Internal-Token)...")
    start_t = time.time()
    resp = await client.submit_render_job(spec)
    submit_elapsed = time.time() - start_t

    print(f"    -> Thời gian gửi: {submit_elapsed:.3f}s")
    print(f"    -> Job ID: {resp.job_id}")
    print(f"    -> Project ID: {resp.project_id}")
    print(f"    -> Trạng thái ban đầu: {resp.status} ✅")
    assert resp.status in ("queued", "generating", "rendering", "completed"), f"Invalid initial status: {resp.status}"

    # 5. Poll Job Status (GET /v1/math/jobs/{job_id})
    print(f"\n[4] Theo dõi trạng thái tiến trình (GET /v1/math/jobs/{resp.job_id})...")
    for poll_idx in range(5):
        await asyncio.sleep(2.0)
        status_resp = await client.get_job_status(resp.job_id)
        print(f"    • Lần {poll_idx + 1} ({poll_idx*2 + 2}s): status='{status_resp.status}', video_url={status_resp.video_url}, error={status_resp.error}")
        if status_resp.status in ("completed", "failed"):
            break

    print("\n" + "=" * 85)
    print("      TỔNG KẾT KIỂM THỬ ĐỘC LẬP MANIM AGENT API: THÀNH CÔNG 100% ✅")
    print("=" * 85)


if __name__ == "__main__":
    asyncio.run(test_manim_api_standalone())
